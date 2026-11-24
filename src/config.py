from math import isfinite
import yaml
from numpy.random import Generator, default_rng
from typing import List
from src.types import Sku


BASE_PATH = "config/base.yaml"
MIN_CITY_POPULATION = 20_000
MAX_CITY_POPULATION = 9_000_000

# Safety net: any optional param a scenario might omit.
DEFAULTS = {
    "spend_cap_enabled": True, "spend_cap_dollars": 200,
    "timeout_increment_minutes": 10,
    "parent_child_authority": True,
    "per_sku_qty_limit_enabled": False, "per_sku_qty_limit": 5,
    "total_qty_limit_enabled": False, "total_qty_limit": 8,
    "ticket_distribution_mode": "arrival", "ticket_assignment": "sequential",
    "ticket_window_start": 7, "ticket_window_end": 9,
    "store_open_hour": 9, "store_close_hour": 17,
    "interaction_time_min": 1,
    "alt_store_acquisition_rate": 22,
    "scalper_demand_share": [0.80, 1.00],
    "scalper_behavior_weights": {"A": 1.0, "B": 0.0, "C": 0.0},
}

# Structural keys that MUST be present (no sensible default).
REQUIRED = {"sku_prices", "sku_supply", "city_population", "lineup_start_hour", "lineup_interval_minutes",
            "lineup_reference_sku", "collector_lineup", "scalper_lineup", "scalper_network_prob"}


def _read_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_config(scenario_path: str = None) -> dict:
    """Merge: DEFAULTS -> base.yaml -> scenario. Minimal scenarios work."""
    cfg = dict(DEFAULTS)
    cfg.update(_read_yaml(BASE_PATH))
    if scenario_path:
        scenario = _read_yaml(scenario_path)
        for key in ("collector_lineup", "scalper_lineup"):
            if key in scenario:
                scenario[key] = {**cfg[key], **scenario[key]}
        cfg.update(scenario)
    return cfg


def population_scaled_value(population: int, endpoints: list | tuple) -> float:
    small_city, large_city = endpoints
    fraction = (population - MIN_CITY_POPULATION) / (MAX_CITY_POPULATION - MIN_CITY_POPULATION)
    return small_city + fraction * (large_city - small_city)


def build_skus(cfg: dict, rng: Generator | None = None) -> List[Sku]:
    if rng is None:
        rng = default_rng()
    skus = []
    for sku_id, price in cfg["sku_prices"].items():
        stock = cfg["sku_supply"][sku_id]
        if isinstance(stock, (list, tuple)):
            mean = population_scaled_value(cfg["city_population"], stock)
            stock = max(0, round(rng.normal(mean, 0.10 * mean)))
        skus.append(Sku(sku_id=sku_id, retail_price=float(price), supply=int(stock)))
    return skus


def sku_priority(cfg: dict) -> List[str]:
    return sorted(cfg["sku_prices"].keys(),
                  key=lambda s: cfg["sku_prices"][s], reverse=True)


def validate(cfg: dict) -> None:
    missing = REQUIRED - set(cfg)
    if missing:
        raise KeyError(f"config missing structural keys: {missing}")
    population = cfg["city_population"]
    if type(population) is not int or not MIN_CITY_POPULATION <= population <= MAX_CITY_POPULATION:
        raise ValueError("city_population must be a whole number from 20,000 to 9,000,000")
    network_prob = cfg["scalper_network_prob"]
    if len(network_prob) != 2 or not all(0 <= p <= 1 for p in network_prob):
        raise ValueError("scalper_network_prob must have two probabilities between 0 and 1")
    if cfg["lineup_reference_sku"] not in cfg["sku_prices"]:
        raise ValueError("lineup_reference_sku must name a configured SKU")
    interval = cfg["lineup_interval_minutes"]
    if not isfinite(interval) or interval <= 0:
        raise ValueError("lineup_interval_minutes must be positive and finite")
    if not 0 <= cfg["lineup_start_hour"] < cfg["store_close_hour"] <= 24:
        raise ValueError("lineup must start before closing, within the same day")
    for key in ("collector_lineup", "scalper_lineup"):
        params = cfg[key]
        for name in ("wtp_mean_offset_dollars", "wtp_std_dollars",
                     "logit_intercept", "logit_slope_per_dollar"):
            if not isfinite(params[name]):
                raise ValueError(f"{key}.{name} must be finite")
        if params["wtp_std_dollars"] < 0:
            raise ValueError(f"{key}.wtp_std_dollars must be nonnegative")
    # Only sanity-check feature-gated numbers, and only if present.
    if cfg.get("timeout_increment_minutes", 10) < 0:
        raise ValueError("timeout_increment_minutes must be >= 0")
    if cfg.get("spend_cap_dollars", 200) <= 0:
        raise ValueError("spend_cap_dollars must be > 0")
