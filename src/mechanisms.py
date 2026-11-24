from src.types import Agent


def authority_multiplier(agent: Agent, cfg: dict) -> int:
    if cfg.get("parent_child_authority", True) and agent.party_size >= 2:
        return 2
    return 1


def turn_cap(agent: Agent, cfg: dict) -> float:
    if not cfg.get("spend_cap_enabled", False):
        return 10 ** 12
    return float(cfg["spend_cap_dollars"]) * authority_multiplier(agent, cfg)


def _cap_value(cfg: dict, sku_id: str) -> int:
    """Read a per-SKU cap that may be a dict (per-SKU) or a scalar (uniform)."""
    lim = cfg.get("per_sku_qty_limit", {})
    if isinstance(lim, dict):
        return int(lim.get(sku_id, 10 ** 9))
    return int(lim)


def turn_max_for_sku(agent: Agent, sku_id: str, cfg: dict) -> int:
    """Per-SKU per-turn cap (dict-aware). Called inside the SKU loop."""
    if not cfg.get("per_sku_qty_limit_enabled", False):
        return 10 ** 9
    return _cap_value(cfg, sku_id) * authority_multiplier(agent, cfg)


def turn_max_per_sku(agent: Agent, cfg: dict) -> int:
    """Back-compat fallback: max across all SKUs, so a dict never crashes it."""
    if not cfg.get("per_sku_qty_limit_enabled", False):
        return 10 ** 9
    lim = cfg.get("per_sku_qty_limit", {})
    if isinstance(lim, dict):
        return max(lim.values()) * authority_multiplier(agent, cfg)
    return int(lim) * authority_multiplier(agent, cfg)


def per_sku_limit(agent: Agent, cfg: dict) -> int:
    """Back-compat fallback: max across SKUs (dict-aware, never crashes)."""
    if not cfg.get("per_sku_qty_limit_enabled", False):
        return 10 ** 9
    lim = cfg.get("per_sku_qty_limit", {})
    if isinstance(lim, dict):
        return max(lim.values())
    return int(lim)


def total_qty_limit(agent: Agent, cfg: dict) -> int:
    if not cfg.get("total_qty_limit_enabled", False):
        return 10 ** 9
    return int(cfg["total_qty_limit"])


def min_cooloff_wait(agent: Agent, cfg: dict) -> float:
    if not cfg.get("cooldown_enabled", False):
        return 0.0
    increment = float(cfg.get("timeout_increment_minutes", 10))
    turn = agent.turns_completed
    if turn == 0:
        return 0.0
    return increment * turn


def timeout_wait_for_nth_item(item_number: int, free_allowance: int,
                              increment: float) -> float:
    if item_number <= free_allowance:
        return 0.0
    return (item_number - free_allowance) * increment