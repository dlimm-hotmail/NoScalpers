from typing import List
from src.types import Agent


def this_store_rate(scalpers: List[Agent]) -> float:
    """Units acquired per person-hour invested AT THIS STORE."""
    total_units = sum(a.total_units() for a in scalpers)
    total_hours = sum(a.total_time_in_store_min() for a in scalpers) / 60.0
    if total_hours <= 0:
        return 0.0
    return total_units / total_hours


def displacement_factor(cfg: dict, rate: float) -> float:
    """How much of the network would leave for the alt store.
    0 = they stay; 1 = they all relocate."""
    alt = float(cfg.get("alt_store_acquisition_rate", 22))
    if rate >= alt or alt <= 0:
        return 0.0
    return max(0.0, 1.0 - (rate / alt))


def acquisition_curve(scalpers: List[Agent]) -> List[tuple]:
    """(cumulative_person_hours, cumulative_units) for plotting.
    Uses total store-time per agent as the x-axis proxy."""
    pts = []
    cum_hours = 0.0
    for a in sorted(scalpers, key=lambda x: x.total_time_in_store_min()):
        cum_hours += a.total_time_in_store_min() / 60.0
        pts.append((cum_hours, sum(b.total_units() for b in scalpers
                                   if b.total_time_in_store_min()
                                   <= a.total_time_in_store_min())))
    return pts