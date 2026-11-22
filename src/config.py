import yaml
from typing import List
from src.types import Sku


BASE_PATH = "config/base.yaml"

# Safety net: any optional param a scenario might omit.
DEFAULTS = {
    "waitlist_enabled": True,
    "spend_cap_enabled": True, "spend_cap_dollars": 200,
    "timeout_enabled": True, "free_allowance_per_sku": 3,
    "timeout_increment_minutes": 10,
    "id_required": True, "parent_child_authority": True,
    "per_sku_qty_limit_enabled": False, "per_sku_qty_limit": 5,
    "total_qty_limit_enabled": False, "total_qty_limit": 8,
    "ticket_distribution_mode": "arrival", "ticket_assignment": "sequential",
    "ticket_window_start": 7, "ticket_window_end": 9,
    "store_open_hour": 9, "store_close_hour": 17,
    "interaction_time_min": 1,
    "num_consumers": 200, "num_scalper_recruits": 40,
    "scalper_markup_mean": 0.40, "scalper_markup_std": 0.15,
    "scalper_opportunity_cost_per_hour": 15,
    "scalper_recruitment_cost_per_person": 20,
    "scalper_show_probability": 0.75, "scalper_coordination_decay": 0.85,
    "alt_store_acquisition_rate": 22, "alt_store_total_time_hours": 2,
    "scalper_demand_share": [0.80, 1.00],
    "scalper_monopoly_mult": 1.5,
    "scalper_behavior_weights": {"A": 1.0, "B": 0.0, "C": 0.0},
}

# Structural keys that MUST be present (no sensible default).
REQUIRED = {"sku_prices", "sku_supply", "num_consumers", "num_scalper_recruits"}


def _read_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_config(scenario_path: str = None) -> dict:
    """Merge: DEFAULTS -> base.yaml -> scenario. Minimal scenarios work."""
    cfg = dict(DEFAULTS)
    cfg.update(_read_yaml(BASE_PATH))
    if scenario_path:
        cfg.update(_read_yaml(scenario_path))
    return cfg


def build_skus(cfg: dict) -> List[Sku]:
    skus = []
    for sku_id, price in cfg["sku_prices"].items():
        skus.append(Sku(sku_id=sku_id, retail_price=float(price),
                        supply=int(cfg["sku_supply"][sku_id])))
    return skus


def sku_priority(cfg: dict) -> List[str]:
    return sorted(cfg["sku_prices"].keys(),
                  key=lambda s: cfg["sku_prices"][s], reverse=True)


def validate(cfg: dict) -> None:
    missing = REQUIRED - set(cfg)
    if missing:
        raise KeyError(f"config missing structural keys: {missing}")
    # Only sanity-check feature-gated numbers, and only if present.
    if cfg.get("free_allowance_per_sku", 3) < 1:
        raise ValueError("free_allowance_per_sku must be >= 1")
    if cfg.get("timeout_increment_minutes", 10) < 0:
        raise ValueError("timeout_increment_minutes must be >= 0")
    if cfg.get("spend_cap_dollars", 200) <= 0:
        raise ValueError("spend_cap_dollars must be > 0")