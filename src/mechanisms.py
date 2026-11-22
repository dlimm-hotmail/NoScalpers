from src.types import Agent, Sku, TurnConstraint


def authority_multiplier(agent: Agent, cfg: dict) -> int:
    """2x authority when party_size >= 2 (couple OR parent+child).
    The child's patience is the self-enforcement; the store never
    judges whether the pair is 'really' a couple."""
    if cfg.get("parent_child_authority", True) and agent.party_size >= 2:
        return 2
    return 1


def turn_cap(agent: Agent, cfg: dict) -> float:
    """Per-turn dollar cap. 2x for 2-person parties."""
    if not cfg.get("spend_cap_enabled", False):
        return 10 ** 12
    return float(cfg["spend_cap_dollars"]) * authority_multiplier(agent, cfg)


def turn_max_per_sku(agent: Agent, cfg: dict) -> int:
    """Hard per-SKU cap per turn. Independent of cooldown.
    ×2 for 2-person parties."""
    if not cfg.get("per_sku_qty_limit_enabled", False):
        return 10 ** 9
    return int(cfg["per_sku_qty_limit"]) * authority_multiplier(agent, cfg)


def min_cooloff_wait(agent: Agent, cfg: dict) -> float:
    """Escalating wait between turns. Now its OWN flag, decoupled from any cap.
    10, 20, 30... min. Agent keeps queue position; a timer gates service."""
    if not cfg.get("cooldown_enabled", False):
        return 0.0
    increment = float(cfg.get("timeout_increment_minutes", 10))
    turn = agent.turns_completed
    if turn == 0:
        return 0.0
    return increment * turn


def per_sku_limit(agent: Agent, cfg: dict) -> int:
    if not cfg.get("per_sku_qty_limit_enabled", False):
        return 10 ** 9
    return int(cfg["per_sku_qty_limit"])


def total_qty_limit(agent: Agent, cfg: dict) -> int:
    if not cfg.get("total_qty_limit_enabled", False):
        return 10 ** 9
    return int(cfg["total_qty_limit"])