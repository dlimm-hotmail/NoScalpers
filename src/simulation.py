from typing import List
import numpy as np
from src.types import Agent
from src.config import build_skus, sku_priority, validate
from src.distributions import (sample_arrival_hour, sample_consumer_type,
                               get_consumer_budget, get_priority,
                               sample_desired_budgeted, sample_desperation,
                               sample_party, sample_patience, sample_markup)
from src.waitlist import Waitlist
from src.mechanisms import (turn_cap, turn_max_for_sku, min_cooloff_wait,
                            total_qty_limit)
from src.scalper_behavior import pick_behavior, build_desired


def _make_agent(aid, atype, rng, cfg, open_h, supply_snapshot):
    party, has_child, age = sample_party(rng)
    if atype == "scalper":
        party, has_child, age = 1, False, None
    if atype == "scalper":
        behavior_id = pick_behavior(rng, cfg)
        consumer_type = ""
        priority = get_priority("scalper", "", cfg)
        desired = build_desired(rng, cfg, supply_snapshot, behavior_id)
        budget = 1e12
    else:
        consumer_type = sample_consumer_type(rng, cfg)
        priority = get_priority("consumer", consumer_type, cfg)
        budget = get_consumer_budget(rng, consumer_type, cfg)
        desired = sample_desired_budgeted(rng, cfg, budget, priority, consumer_type)
    a = Agent(agent_id=aid, agent_type=atype, party_size=party,
              has_child=has_child, child_age=age)
    a.consumer_type = consumer_type
    a.priority = priority
    a.desired = desired
    a.budget = budget
    a.desperation_price = sample_desperation(rng, desired, cfg)
    a.arrival_time = sample_arrival_hour(rng, cfg, atype)
    a.effective_arrival = a.arrival_time
    a.patience_ceiling_min = sample_patience(rng, a)
    if atype == "scalper":
        a.markup = sample_markup(rng, cfg)
    return a


def _enter_time(agent: Agent, cfg: dict, open_h: float,
                present: bool) -> float:
    if present:
        return -1.0
    return max(0.0, agent.arrival_time - open_h)


def run_one(cfg: dict, seed: int):
    validate(cfg)
    rng = np.random.default_rng(seed)
    skus = build_skus(cfg)
    skus_by_id = {s.sku_id: s for s in skus}
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
        a.enter_time = _enter_time(a, cfg, open_h, present(a))

    # Collusion = network piggyback. One networked member is the sentry
    # (earliest arrival); the other networked members do NOT camp — they
    # show at defer_hour and inherit the sentry's held position. Non-
    # networked scalpers and consumers keep their natural position.
    if cfg.get("collusion_enabled", False):
        p_net = float(cfg.get("scalper_network_prob", 0.75))
        defer = float(cfg.get("network_anchor_defer_hour", 8.5))
        sc = [a for a in agents if a.agent_type == "scalper"]
        for a in sc:
            a.networked = bool(rng.random() < p_net)
        net = [a for a in sc if a.networked]
        if net:
            anchor = min(net, key=lambda a: a.arrival_time)   # the sentry
            for a in net:
                if a is not anchor:
                    # they physically show at `defer`, but hold the sentry's spot
                    a.effective_arrival = anchor.arrival_time
                    a.enter_time = anchor.enter_time            # inherit ticket presence
    pending = sorted(agents, key=lambda a: (a.enter_time, a.effective_arrival, a.arrival_time))
    if mode == "random_time" and cfg.get("ticket_assignment") == "random":
        front = [a for a in pending if a.enter_time < 0]
        back  = [a for a in pending if a.enter_time >= 0]
        rng.shuffle(front)        # lottery breaks the held-spot clustering
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

        # ---- None guard MUST come before anything touches agent ----
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
        # ---- only now is agent guaranteed non-None ----
        prev = dict(agent.items_purchased)
       
        # DEBUG: log service order
        if cfg.get("debug_service_order", False):
            print(f"  t={current_time:.0f} pos={waitlist._q.index(agent)+1} "
                  f"type={agent.agent_type:8s} id={agent.agent_id}")

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
        tot_lim = total_qty_limit(agent, cfg)
        priority = agent.priority

        # live cash = personal budget minus what they've already spent
        sku_prices = {s.sku_id: s.retail_price for s in skus}
        personal_left = agent.budget - agent.total_spend(sku_prices)
        store_cap = turn_cap(agent, cfg)
        remaining_cap = min(store_cap, personal_left)   # both constrain live       
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
            sku_max = turn_max_for_sku(agent, sku_id, cfg)   # per-SKU, dict-aware
            can = min(want, afford, sku.remaining, sku_max,
                      tot_lim - total_this_turn)
            if can <= 0:
                continue
            agent.items_purchased[sku_id] = agent.items_purchased.get(sku_id, 0) + can
            sku.remaining -= can
            remaining_cap -= can * sku.retail_price
            total_this_turn += can

        if cfg.get("debug_purchase_log", False):
            pos = waitlist._q.index(agent) + 1 if agent in waitlist._q else -1
            bought = {s: agent.items_purchased.get(s, 0) - prev.get(s, 0) for s in skus_by_id}
            rem = {s.sku_id: s.remaining for s in skus}
            log = " ".join(f"{skus_by_id[s].sku_id}={bought[s]}" for s in priority)
            logr = " ".join(f"{s}={rem[s]}" for s in skus_by_id)
            print(f"[{current_time:7.0f}] pos={pos:>3} {agent.agent_type:<8} "
                  f"{agent.agent_id:<5} buy: {log}  rem: {logr}")

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
            # Step aside: remove from current position, re-append at the back.
            # The queue wait behind the other customers IS the primary friction;
            # the cooldown is an ADDITIONAL wait on top of it.
            waitlist.remove(agent)
            waitlist.add(agent, current_time)
            cooloff = min_cooloff_wait(agent, cfg)
            agent.earliest_serve_time = current_time + cooloff
            agent.last_ready_time = current_time + cooloff
            agent.cumulative_internal_wait_min += cooloff
        else:
            waitlist.remove(agent)
            agent.exited = True

    return {"consumers": consumers, "scalpers": scalpers, "skus": skus,
            "final_clock": current_time}