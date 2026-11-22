from typing import Dict, List
import numpy as np

BEHAVIOR_A = "A"  # margin-calculating solo scalper (the baseline)
BEHAVIOR_B = "B"  # network/co-op: flat wage -> tolerates friction, Costco-style
BEHAVIOR_C = "C"  # opportunistic/impulse: loose budget, low target, quits early


def pick_behavior(rng: np.random.Generator, cfg: dict) -> str:
    weights = cfg.get("scalper_behavior_weights", {BEHAVIOR_A: 1.0})
    opts = list(weights.keys())
    ps = np.array([weights[o] for o in opts], dtype=float)
    ps /= ps.sum()
    return str(rng.choice(opts, p=ps))


def _unit_profit(sku_id: str, cfg: dict) -> float:
    """Expected resale minus retail, per unit, using per-SKU markup mean."""
    retail = cfg["sku_prices"][sku_id]
    mm = cfg.get("sku_markup_mean", {}).get(sku_id, cfg["scalper_markup_mean"])
    return retail * mm


def _roi_velocity_score(sku_id: str, cfg: dict, supply: int, qcap: int) -> float:
    """$/hr-per-capital proxy. Monopoly jump when they could corner the SKU."""
    retail = cfg["sku_prices"][sku_id]
    velocity = float(cfg.get("sku_velocity_hours", {}).get(sku_id, 1.0))
    profit = _unit_profit(sku_id, cfg)
    p_sell = 1.0
    if qcap >= supply and supply > 0:
        p_sell *= float(cfg.get("scalper_monopoly_mult", 1.5))
    return (profit * p_sell) / (velocity * retail)


def build_desired_vector(rng: np.random.Generator, cfg: dict,
                         supply: Dict[str, int]) -> Dict[str, int]:
    """Dealer-shaped VECTOR: per-SKU target qty, ordered by expected ROI,
    bounded by per-SKU sell-through ceiling AND total credit. Credit is the
    binding limit (they buy hot SKUs at full target, then run dry and the
    cold tail gets 0). This concentrated high-count vector is what makes the
    store's per-turn cap force re-entry and the timeout ramp across items
    4..N -- i.e. what makes the friction actually bite."""
    credit = float(rng.uniform(cfg["scalper_credit_min"], cfg["scalper_credit_max"]))
    sell = cfg["scalper_sell_through"]
    lo, hi = cfg["scalper_demand_share"]

    skus = list(cfg["sku_prices"].keys())
    ranked = sorted(skus, key=lambda s: _roi_velocity_score(s, cfg, supply[s], 10**9),
                    reverse=True)

    desired = {s: 0 for s in skus}
    remaining = credit
    for sku in ranked:
        price = cfg["sku_prices"][sku]
        share = float(rng.uniform(lo, hi))                 # per-SKU aggressiveness
        want = min(int(share * sell[sku]), supply[sku])    # dealer target, capped by stock
        afford = int(remaining // price)                   # can't exceed credit
        qty = max(0, min(want, afford))
        desired[sku] = qty
        remaining -= qty * price
        if remaining < price:
            break                                          # out of money: tail stays 0
    return desired


# ---- stubs for the variations you'll add next ----
def desired_vector_B(rng, cfg, supply):   # co-op: effective credit ~ Costco pool
    raise NotImplementedError("BehaviorB (network/co-op) not yet implemented")

def desired_vector_C(rng, cfg, supply):   # impulse: loose budget, tiny target
    raise NotImplementedError("BehaviorC (opportunistic) not yet implemented")

def build_desired(rng, cfg, supply, behavior_id):
    if behavior_id == BEHAVIOR_A:
        return build_desired_vector(rng, cfg, supply)
    if behavior_id == BEHAVIOR_B:
        return desired_vector_B(rng, cfg, supply)
    if behavior_id == BEHAVIOR_C:
        return desired_vector_C(rng, cfg, supply)
    return build_desired_vector(rng, cfg, supply)