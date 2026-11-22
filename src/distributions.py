from typing import List, Dict
import numpy as np
from src.types import Agent


# ---- Arrival ----
# Placeholder: a ramped distribution over pre-open hours (1am..open).
# More weight near opening = the big general cluster; low weight early
# = the hardcore campers. Replace with a real mixture once calibrated.
def sample_arrival_hour(rng: np.random.Generator, cfg: dict,
                        agent_type: str) -> float:
    open_h = cfg["store_open_hour"]
    if agent_type == "scalper":
        mode = cfg.get("scalper_arrival_mode", "uniform_late")
        if mode == "camp":
            # hardcore campers: 1am-3am cluster, the seat-holders
            return float(rng.uniform(1, 3))
        return float(rng.uniform(cfg.get("ticket_window_start", 7), open_h))
    hours = list(range(open_h - 8, open_h + 1))   # e.g. 1..9
    weights = np.array([h - (open_h - 8) + 1 for h in hours], dtype=float)
    weights /= weights.sum()
    h = int(rng.choice(hours, p=weights))
    # 15% of consumers trickle in after opening (walk-ins, late comers).
    if rng.random() < 0.15:
        return float(rng.uniform(open_h, open_h + 4))
    return float(h)


# ---- Desired purchase vectors ----
# Per-SKU discrete demand: (qty, probability). Calibrate from basket data.
SKU_DEMAND: Dict[str, List[tuple]] = {
    "ETB":    [(0, 0.30), (1, 0.30), (2, 0.20), (3, 0.10), (4, 0.05), (5, 0.05)],
    "Tin":    [(0, 0.45), (1, 0.30), (2, 0.15), (3, 0.10)],
    "Bundle": [(0, 0.30), (1, 0.25), (2, 0.25), (3, 0.15), (4, 0.05)],
    "UPC":    [(0, 0.40), (1, 0.30), (2, 0.20), (3, 0.10)],
}


def sample_desired(rng: np.random.Generator, cfg: dict) -> Dict[str, int]:
    out = {}
    for sku, table in SKU_DEMAND.items():
        qs = [q for q, _ in table]
        ps = [p for _, p in table]
        ps = np.array(ps, dtype=float); ps /= ps.sum()
        out[sku] = int(rng.choice(qs, p=ps))
    return out


def sample_budget(rng: np.random.Generator, desired: Dict[str, int],
                  cfg: dict) -> float:
    base = sum(q * cfg["sku_prices"][s] for s, q in desired.items())
    # Some buyers are budget-tight, some flush.
    return float(base * rng.uniform(1, 1.3))


def sample_desperation(rng: np.random.Generator, desired: Dict[str, int],
                       cfg: dict) -> Dict[str, float]:
    return {s: float(cfg["sku_prices"][s] * rng.uniform(1.0, 1.8))
            for s, q in desired.items() if q > 0}


# ---- Party composition ----
def sample_party(rng: np.random.Generator) -> tuple:
    r = rng.random()
    if r < 0.70:
        return (1, False, None)            # solo
    if r < 0.85:
        return (2, False, None)            # couple (2 adults)
    age = int(rng.integers(2, 12))
    return (2, True, age)                  # parent + child


# ---- Patience ceilings (minutes of store-process time) ----
def sample_patience(rng: np.random.Generator, agent: Agent) -> float:
    if agent.agent_type == "scalper":
        return float(rng.uniform(240, 480))
    if agent.has_child:
        if agent.child_age is not None and agent.child_age <= 6:
            return float(rng.uniform(60, 120))
        return float(rng.uniform(90, 180))
    return float(rng.uniform(180, 300))    # solo adult or couple


# ---- Scalper markup ----
def sample_markup(rng: np.random.Generator, cfg: dict) -> float:
    return float(max(0.05, rng.normal(cfg["scalper_markup_mean"],
                                      cfg["scalper_markup_std"])))