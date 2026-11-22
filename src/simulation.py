from typing import List
import numpy as np
from src.types import Agent
from src.config import build_skus, sku_priority, validate
from src.distributions import (sample_arrival_hour, sample_desired,
                               sample_budget, sample_desperation,
                               sample_party, sample_patience, sample_markup)
from src.waitlist import Waitlist
from src.mechanisms import (turn_cap, turn_max_per_sku, min_cooloff_wait,
                            per_sku_limit, total_qty_limit)
from src.scalper_behavior import pick_behavior, build_desired


def _make_agent(aid, atype, rng, cfg, open_h, supply_snapshot):
    party, has_child, age = sample_party(rng)
    if atype == "scalper":
        party, has_child, age = 1, False, None
    if atype == "scalper":
        behavior_id = pick_behavior(rng, cfg)
        desired = build_desired(rng, cfg, supply_snapshot, behavior_id)
    else:
        behavior_id = "consumer"
        desired = sample_desired(rng, cfg)
    a = Agent(agent_id=aid, agent_type=atype, party_size=party,
              has_child=has_child, child_age=age)
    a.desired = desired
    a.budget = sample_budget(rng, desired, cfg)
    a.desperation_price = sample_desperation(rng, desired, cfg)
    a.arrival_time = sample_arrival_hour(rng, cfg, atype)
    a.effective_arrival = a.arrival_time
    a.patience_ceiling_min = sample_patience(rng, a)
    if atype == "scalper":
        a.markup = sample_markup(rng, cfg)
    return a


def _enter_time(agent: Agent, cfg: dict, open_h: float,
                event_time: float, present: bool) -> float:
    if present:
        return -1.0
    return max(0.0, agent.arrival_time - open_h)


def _scalper_priority(cfg: dict) -> List[str]:
    """Scalpers buy in ROI order: highest dollar-ROI SKU first.
    If they get 45% ROI on ETB, buying a 30% Tin first is a
    relative loss. Sort by retail * markup_mean descending."""
    skus = list(cfg["sku_prices"].keys())
    def roi(s):
        mm = cfg.get("sku_markup_mean", {}).get(s, cfg["scalper_markup_mean"])
        return cfg["sku_prices"][s] * mm
    return sorted(skus, key=roi, reverse=True)


def run_one(cfg: dict, seed: int):
    validate(cfg)
    rng = np.random.default_rng(seed)
    skus = build_skus(cfg)
    skus_by_id = {s.sku_id: s for s in skus}
    consumer_priority = sku_priority(cfg)
    scalper_priority = _scalper_priority(cfg)
    open_h = float(cfg["store_open_hour"])
    interaction = float(cfg.get("interaction_time_min", 1))

    supply_snapshot = {s.sku_id: s.supply for s in skus}
    consumers = [_make_agent(f"c{i}", "consumer", rng, cfg, open_h, supply_snapshot)
                 for i in range(cfg["num_consumers"])]
    scalpers = [_make_agent(f"s{i}", "scalper", rng, cfg, open_h, supply_snapshot)
                for i in range(cfg["num_scalper_recruits"])]
    agents = consumers + scalpers

    mode = cfg.get("ticket_distribution_mode", "arrival")
    event_time = None
    if mode == "random_time":
        event_time = float(rng.uniform(cfg["ticket_window_start"],
                                       cfg["ticket_window_end"]))

    def present(a):
        if mode == "arrival":
            return False
        if mode == "random_time":
            return a.arrival_time <= event_time
        if mode == "waves":
            return a.arrival_time <= cfg["ticket_window_end"]
        return False

    for a in agents:
        a.enter_time = _enter_time(a, cfg, open_h, event_time, present(a))

    # Collusion regroup: scalper recruits within a group get the
    # earliest member's effective_arrival, teleporting them to the
    # front of their group in the queue.
    if cfg.get("collusion_enabled", False):
        group_size = int(cfg.get("collusion_group_size", 5))
        sc = sorted([a for a in agents if a.agent_type == "scalper"],
                    key=lambda a: a.arrival_time)
        for i in range(0, len(sc), group_size):
            grp = sc[i:i + group_size]
            min_at = grp[0].arrival_time
            min_et = grp[0].enter_time
            for a in grp:
                a.effective_arrival = min_at
                a.enter_time = min_et
    pending = sorted(agents, key=lambda a: (a.enter_time, a.effective_arrival, a.arrival_time))
    if mode == "random_time" and cfg.get("ticket_assignment") == "random":
        front = [a for a in pending if a.enter_time < 0]
        back = [a for a in pending if a.enter_time >= 0]
        # Collusion still applies: group members stay together in the shuffle
        if cfg.get("collusion_enabled", False):
            group_size = int(cfg.get("collusion_group_size", 5))
            sc = [a for a in front if a.agent_type == "scalper"]
            co = [a for a in front if a.agent_type == "consumer"]
            rng.shuffle(sc)
            # regroup: within each shuffled chunk, keep group members adjacent
            grouped = []
            for i in range(0, len(sc), group_size):
                grp = sc[i:i + group_size]
                grp.sort(key=lambda a: a.effective_arrival)
                grouped.extend(grp)
            front = grouped + co
            rng.shuffle(front)
        else:
            rng.shuffle(front)
        pending = front + back

    waitlist = Waitlist()
    current_time = 0.0
    pi = 0

    while pi < len(pending) or not waitlist.is_empty():
        # 1. Admit arrivals whose enter_time has arrived (append to back)
        while pi < len(pending) and pending[pi].enter_time <= current_time:
            waitlist.add(pending[pi], current_time)
            pi += 1

        # 2. Serve the first agent in position order whose timer has opened.
        #    Gated agents (timer not open) keep their position and are skipped;
        #    people behind them get served instead.
        agent = waitlist.first_ready(current_time)
        if agent is None:
            # nobody ready: advance clock to next arrival or next timer opening
            candidates = []
            if pi < len(pending):
                candidates.append(pending[pi].enter_time)
            nxt = waitlist.min_eligible(current_time)
            if nxt is not None:
                candidates.append(nxt)
            if not candidates:
                break
            current_time = max(current_time, min(candidates))
            continue

        # External wait this turn = time since their timer opened
        ext = current_time - agent.last_ready_time
        if ext > 0:
            agent.cumulative_external_wait_min += ext

        # Patience check at start of turn (cooldown already counted in total)
        if agent.total_time_in_store_min() > agent.patience_ceiling_min:
            waitlist.remove(agent)
            agent.exited = True
            continue

        # 3. Process the turn
        cap = turn_cap(agent, cfg)
        sku_turn_max = turn_max_per_sku(agent, cfg)
        sku_lim = per_sku_limit(agent, cfg)
        tot_lim = total_qty_limit(agent, cfg)
        priority = scalper_priority if agent.agent_type == "scalper" else consumer_priority

        remaining_cap = cap
        total_this_turn = 0

        for sku_id in priority:
            want = agent.desired.get(sku_id, 0) - agent.items_purchased.get(sku_id, 0)
            if want <= 0:
                continue
            sku = skus_by_id[sku_id]
            if sku.remaining <= 0:
                continue
            if remaining_cap < sku.retail_price:
                continue
            afford = int(remaining_cap // sku.retail_price)
            can = min(want, afford, sku.remaining, sku_turn_max,
                      tot_lim - total_this_turn)
            if can <= 0:
                continue
            agent.items_purchased[sku_id] = agent.items_purchased.get(sku_id, 0) + can
            sku.remaining -= can
            remaining_cap -= can * sku.retail_price
            total_this_turn += can

        agent.cumulative_interaction_min += interaction
        agent.turns_completed += 1
        current_time += interaction

        # 4. Re-enter (stay in place, set gate timer) or exit
        spent = agent.total_spend({s.sku_id: s.retail_price for s in skus})
        budget_left = agent.budget - spent

        can_progress = False
        for sku_id in priority:
            if agent.desired.get(sku_id, 0) - agent.items_purchased.get(sku_id, 0) > 0:
                if skus_by_id[sku_id].remaining > 0 and budget_left >= skus_by_id[sku_id].retail_price:
                    can_progress = True
                    break

        if agent.still_wants() and can_progress and \
           agent.total_time_in_store_min() <= agent.patience_ceiling_min:
            cooloff = min_cooloff_wait(agent, cfg)
            # Agent keeps its position in the queue; only the timer moves.
            agent.earliest_serve_time = current_time + cooloff
            agent.last_ready_time = current_time + cooloff
            # The cooldown is the agent's own wait (off to the side).
            agent.cumulative_internal_wait_min += cooloff
        else:
            waitlist.remove(agent)
            agent.exited = True

    return {"consumers": consumers, "scalpers": scalpers, "skus": skus,
            "final_clock": current_time}