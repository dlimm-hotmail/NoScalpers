from typing import List, Dict
import numpy as np
from src.types import Agent


def sample_arrival_hour(rng, cfg, agent_type):
    open_h = cfg["store_open_hour"]
    if agent_type == "scalper":
        if cfg.get("scalper_arrival_mode", "uniform_late") == "camp":
            return float(rng.uniform(1, 3))
        return float(rng.uniform(cfg.get("ticket_window_start", 7), open_h))
    hours = list(range(open_h - 8, open_h + 1))
    w = np.array([h - (open_h - 8) + 1 for h in hours], dtype=float)
    w /= w.sum()
    h = int(rng.choice(hours, p=w))
    if rng.random() < 0.15:
        return float(rng.uniform(open_h, open_h + 4))
    return float(h)


def sample_consumer_type(rng, cfg):
    wt = cfg.get("consumer_type_weights", {"hardcore":.2,"enthusiast":.5,"budget":.3})
    opts = list(wt.keys()); ps = np.array([wt[o] for o in opts], float); ps/=ps.sum()
    return str(rng.choice(opts, p=ps))


def get_consumer_budget(rng, ctype, cfg):
    base = float(cfg.get("consumer_budgets", {}).get(ctype, 200))
    return float(base * rng.uniform(0.85, 1.15))


def get_priority(agent_type, ctype, cfg):
    if agent_type == "scalper":
        return list(cfg.get("scalper_priority", ["UPC","ETB","Bundle","Tin","Single"]))
    return list(cfg.get("consumer_priorities", {}).get(
        ctype, ["UPC","ETB","Bundle","Tin","Single"]))


SKU_DEMAND = {
    "ETB":    [(0,.30),(1,.30),(2,.20),(3,.10),(4,.05),(5,.05)],
    "Tin":    [(0,.45),(1,.30),(2,.15),(3,.10)],
    "Bundle": [(0,.30),(1,.25),(2,.25),(3,.15),(4,.05)],
    "UPC":    [(0,.40),(1,.30),(2,.20),(3,.10)],
    "Single": [(0,.30),(1,.20),(2,.20),(3,.15),(4,.10),(5,.05)],
}

def _sample_qty(rng, sku):
    t = SKU_DEMAND.get(sku, [(0,1.0)])
    qs=[q for q,_ in t]; ps=np.array([p for _,p in t],float); ps/=ps.sum()
    return int(rng.choice(qs, p=ps))

def sample_desired_budgeted(rng, cfg, budget, priority):
    desired = {s:0 for s in priority}
    rem = budget
    for sku in priority:
        want = _sample_qty(rng, sku)
        if want <= 0: continue
        price = cfg["sku_prices"].get(sku, 1)
        if want * price <= rem:
            desired[sku] = want; rem -= want*price
        else:
            afford = int(rem // price)
            desired[sku] = min(want, afford); rem -= desired[sku]*price
    return desired


def sample_desperation(rng, desired, cfg):
    return {s: float(cfg["sku_prices"][s]*rng.uniform(1.0,1.8))
            for s,q in desired.items() if q>0}


def sample_party(rng):
    r = rng.random()
    if r < .70: return (1, False, None)
    if r < .85: return (2, False, None)
    return (2, True, int(rng.integers(2,12)))


def sample_patience(rng, agent):
    t = agent.arrival_time
    if t <= 3: base = rng.uniform(600,1200)
    elif t <= 6: base = rng.uniform(300,500)
    elif t <= 8: base = rng.uniform(120,240)
    else: base = rng.uniform(60,150)
    if agent.has_child:
        base = min(base, 120 if (agent.child_age or 0)<=6 else 180)
    return float(base)


def sample_markup(rng, cfg):
    lo = float(cfg.get("scalper_markup_min", 0.4))
    hi = float(cfg.get("scalper_markup_max", 1.5))
    return float(rng.uniform(lo, hi))