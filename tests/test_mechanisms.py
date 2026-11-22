from src.types import Agent
from src.mechanisms import (turn_cap, turn_free_allowance,
                            timeout_wait_for_nth_item)


def _cfg(**over):
    base = {"spend_cap_enabled": True, "spend_cap_dollars": 200,
            "timeout_enabled": True, "free_allowance_per_sku": 3,
            "per_sku_qty_limit_enabled": False, "total_qty_limit_enabled": False,
            "parent_child_authority": True}
    base.update(over)
    return base


def test_solo_cap_is_200():
    a = Agent(agent_id="s", agent_type="consumer", party_size=1)
    assert turn_cap(a, _cfg()) == 200


def test_two_person_party_gets_double_cap():
    a = Agent(agent_id="s", agent_type="consumer", party_size=2)
    assert turn_cap(a, _cfg()) == 400


def test_timeout_starts_after_free_allowance():
    # free=3, increment=10 -> item4=10, item5=20, item6=30
    assert timeout_wait_for_nth_item(4, 3, 10) == 10
    assert timeout_wait_for_nth_item(5, 3, 10) == 20
    assert timeout_wait_for_nth_item(6, 3, 10) == 30
    assert timeout_wait_for_nth_item(3, 3, 10) == 0


def test_free_allowance_doubles_for_two_person_party():
    a = Agent(agent_id="s", agent_type="consumer", party_size=2)
    assert turn_free_allowance(a, _cfg()) == 6