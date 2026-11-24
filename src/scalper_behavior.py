from typing import Dict
import numpy as np

BEHAVIOR_A, BEHAVIOR_B, BEHAVIOR_C = "A", "B", "C"

def pick_behavior(rng, cfg):
    w = cfg.get("scalper_behavior_weights", {BEHAVIOR_A:1.0})
    opts=list(w.keys()); ps=np.array([w[o] for o in opts],float); ps/=ps.sum()
    return str(rng.choice(opts, p=ps))

def build_desired_vector(rng, cfg, supply):
    """Desire = what they'd flip, capped only by supply (and sell_through).
    NO credit truncation here: a real scalper doesn't pre-commit their cash
    to one SKU at build time. Budget is enforced live at the register."""
    sell  = cfg.get("scalper_sell_through", {})
    lo,hi = cfg.get("scalper_demand_share", [0.80,1.00])
    prio  = list(cfg.get("scalper_priority", ["UPC","ETB","Bundle","Tin","Single"]))

    desired = {s:0 for s in prio}
    for sku in prio:
        share = float(rng.uniform(lo, hi))
        want  = min(int(share * sell.get(sku,100)), supply.get(sku,0))
        desired[sku] = max(0, want)
    return desired

def desired_vector_B(rng,cfg,supply):
    raise NotImplementedError("BehaviorB (co-op credit pool) not yet implemented")
def desired_vector_C(rng,cfg,supply):
    raise NotImplementedError("BehaviorC (opportunistic) not yet implemented")

def build_desired(rng,cfg,supply,behavior_id):
    if behavior_id==BEHAVIOR_B: return desired_vector_B(rng,cfg,supply)
    if behavior_id==BEHAVIOR_C: return desired_vector_C(rng,cfg,supply)
    return build_desired_vector(rng,cfg,supply)