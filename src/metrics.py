from typing import Dict, List
import numpy as np
from src.types import Agent
from src.secondary_market import run_secondary_market


def compute_metrics(consumers: List[Agent], scalpers: List[Agent],
                    skus: list, cfg: dict) -> dict:
    sku_prices = {s.sku_id: s.retail_price for s in skus}
    total_supply = sum(s.supply for s in skus)

    # ---- consumer fulfillment ----
    rates = []
    zero_count = 0
    for a in consumers:
        d = a.total_desired()
        if d == 0:
            continue
        r = min(1.0, a.total_units() / d)
        rates.append(r)
        if a.total_units() == 0:
            zero_count += 1
    rates_arr = np.array(rates) if rates else np.array([0.0])

    # ---- consumer friction ----
    times = [a.total_time_in_store_min() for a in consumers]
    t_arr = np.array(times) if times else np.array([0.0])
    patience_exits = sum(1 for a in consumers
                         if a.total_time_in_store_min() > a.patience_ceiling_min
                         and a.total_units() < a.total_desired())

    # ---- scalper extraction ----
    scalper_units = sum(a.total_units() for a in scalpers)
    scalper_hours = sum(a.total_time_in_store_min() for a in scalpers) / 60.0
    resale = run_secondary_market(scalpers, consumers, cfg)

    # ---- store revenue ----
    revenue = 0.0
    for s in skus:
        sold = s.supply - s.remaining
        revenue += sold * s.retail_price

    return {
        "collectors_joined": len(consumers),
        "scalpers_joined": len(scalpers),
        "fulfillment_mean": float(rates_arr.mean()),
        "fulfillment_p90": float(np.percentile(rates_arr, 90)),
        "fulfillment_zero_rate": zero_count / max(1, len(rates)),
        "friction_mean_min": float(t_arr.mean()),
        "friction_p90_min": float(np.percentile(t_arr, 90)),
        "patience_exits": patience_exits,
        "scalper_units": scalper_units,
        "scalper_profit": resale["secondary_profit"] / len(scalpers) if scalpers else 0.0,
        "scalper_share": scalper_units / max(1, total_supply),
        "scalper_hours": scalper_hours,
        "store_revenue": revenue,
        "units_sold": total_supply - sum(s.remaining for s in skus),
    }
