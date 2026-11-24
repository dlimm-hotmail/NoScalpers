from typing import Dict, List
import numpy as np
from src.types import Agent


def compute_metrics(consumers, scalpers, skus, cfg):
    sku_prices = {s.sku_id: s.retail_price for s in skus}

    # ---- Singles exclusion (fairness metrics only) ----
    exclude = {"Single"} if not cfg.get("include_singles_in_metrics", True) else set()
    def _included(units_dict):
        return sum(v for k, v in units_dict.items() if k not in exclude)

    full_supply  = sum(s.supply for s in skus)                                   # throughput
    total_supply = sum(s.supply for s in skus if s.sku_id not in exclude)        # fairness denominator

    # ---- consumer fulfillment ----
    rates = []
    zero_count = 0
    for a in consumers:
        d = _included(a.desired)                       # << changed (was a.total_desired())
        if d == 0:
            continue
        u = _included(a.items_purchased)               # << changed (was a.total_units())
        r = min(1.0, u / d)
        rates.append(r)
        if u == 0:
            zero_count += 1
    rates_arr = np.array(rates) if rates else np.array([0.0])

    # ---- consumer friction ----
    times = [a.total_time_in_store_min() for a in consumers]
    t_arr = np.array(times) if times else np.array([0.0])
    patience_exits = sum(1 for a in consumers                # << changed (now _included)
                         if a.total_time_in_store_min() > a.patience_ceiling_min
                         and _included(a.items_purchased) < _included(a.desired))

    # ---- scalper extraction ----
    scalper_units = sum(_included(a.items_purchased) for a in scalpers)   # << changed
    scalper_hours = sum(a.total_time_in_store_min() for a in scalpers) / 60.0

    # ---- store revenue (keep Singles: throughput) ----
    revenue = 0.0
    for s in skus:
        sold = s.supply - s.remaining
        revenue += sold * s.retail_price

    return {
        "fulfillment_mean": float(rates_arr.mean()),
        "fulfillment_p90": float(np.percentile(rates_arr, 90)),
        "fulfillment_zero_rate": zero_count / max(1, len(rates)),
        "friction_mean_min": float(t_arr.mean()),
        "friction_p90_min": float(np.percentile(t_arr, 90)),
        "patience_exits": patience_exits,
        "scalper_units": scalper_units,
        "scalper_share": scalper_units / max(1, total_supply),            # filtered
        "scalper_hours": scalper_hours,
        "store_revenue": revenue,
        "units_sold": full_supply - sum(s.remaining for s in skus),       # full (throughput)
    }