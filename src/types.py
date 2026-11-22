from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Sku:
    sku_id: str
    retail_price: float
    supply: int

    def __post_init__(self):
        self.remaining = self.supply


@dataclass
class TurnConstraint:
    """What a single mechanism says about buying one SKU this turn."""
    max_qty: int = 10 ** 9
    additional_wait_min: float = 0.0


@dataclass
class Agent:
    agent_id: str
    agent_type: str                 # "consumer" | "scalper"
    party_size: int = 1
    has_child: bool = False
    child_age: Optional[int] = None
    effective_arrival: float = 0.0   # queue sort key; defaults to arrival_time

    # Demand
    desired: Dict[str, int] = field(default_factory=dict)
    budget: float = 0.0
    desperation_price: Dict[str, float] = field(default_factory=dict)

    # Arrival / queue
    arrival_time: float = 0.0       # wall-clock hour (1.0 = 1am)
    enter_time: float = 0.0         # process-time they join the queue
    waitlist_position: int = 0
    time_entered_queue: float = 0.0 # process-time of most recent enqueue

    # Purchase state
    turns_completed: int = 0
    items_purchased: Dict[str, int] = field(default_factory=dict)

    # Friction tracking
    cumulative_internal_wait_min: float = 0.0
    cumulative_external_wait_min: float = 0.0
    cumulative_interaction_min: float = 0.0

    # Patience
    patience_ceiling_min: float = 9999.0

    # Scalper-only
    markup: float = 0.0

    # State
    exited: bool = False

    # ---- helpers ----
    def total_time_in_store_min(self) -> float:
        return (self.cumulative_internal_wait_min
                + self.cumulative_external_wait_min
                + self.cumulative_interaction_min)

    def total_spend(self, sku_prices: Dict[str, float]) -> float:
        return sum(self.items_purchased.get(s, 0) * p
                   for s, p in sku_prices.items())

    def total_units(self) -> int:
        return sum(self.items_purchased.values())

    def total_desired(self) -> int:
        return sum(self.desired.values())

    def still_wants(self) -> bool:
        return any(self.desired.get(s, 0) - self.items_purchased.get(s, 0) > 0
                   for s in self.desired)