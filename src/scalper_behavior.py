from typing import Dict
import numpy as np

BEHAVIOR_A, BEHAVIOR_B, BEHAVIOR_C = "A", "B", "C"

def pick_behavior(rng, cfg):
    w = cfg.get("scalper_behavior_weights", {BEHAVIOR_A:1.0})
    opts=list(w.keys()); ps=np.array([w[o] for o in opts],float); ps/=ps.sum()
    return str(rng.choice(opts, p=ps))

def build_desired_vector(rng, cfg, supply):
    """Dealer vector in CONFIG priority order, sized by sell-through*demand_share,
    bounded by supply and credit. A unit is only wanted if resale clears the
    buy cost + transaction cost (markup -> buy decision)."""
    credit = float(rng.uniform(cfg["scalper_credit_min"], cfg["scalper_credit_max"]))
    sell   = cfg.get("scalper_sell_through", {})
    lo,hi  = cfg.get("scalper_demand_share", [0.80,1.00])
    prio   = list(cfg.get("scalper_priority", ["UPC","ETB","Bundle","Tin","Single"]))
    txn    = float(cfg.get("scalper_transaction_cost", 8))

    desired = {s:0 for s in prio}
    rem = credit
    for sku in prio:
        price = cfg["sku_prices"][sku]
        # each scalper draws a per-unit resale markup; buy only if it clears cost
        markup = float(rng.uniform(cfg.get("scalper_markup_min",0.4),
                                   cfg.get("scalper_markup_max",1.5)))
        resale = price * (1 + markup)
        if resale < price + txn:      # margin-negative -> skip this SKU entirely
            continue
        share = float(rng.uniform(lo, hi))
        want  = min(int(share * sell.get(sku,100)), supply.get(sku,0))
        afford = int(rem // price)
        qty = max(0, min(want, afford))
        desired[sku] = qty
        rem -= qty*price
        if rem < price:
            break
    return desired

def desired_vector_B(rng,cfg,supply):
    raise NotImplementedError("BehaviorB (co-op credit pool) not yet implemented")
def desired_vector_C(rng,cfg,supply):
    raise NotImplementedError("BehaviorC (opportunistic) not yet implemented")

def build_desired(rng,cfg,supply,behavior_id):
    if behavior_id==BEHAVIOR_B: return desired_vector_B(rng,cfg,supply)
    if behavior_id==BEHAVIOR_C: return desired_vector_C(rng,cfg,supply)
    return build_desired_vector(rng,cfg,supply)