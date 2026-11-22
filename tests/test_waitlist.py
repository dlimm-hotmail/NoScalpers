from src.types import Agent
from src.waitlist import Waitlist


def _a(n):
    return Agent(agent_id=f"a{n}", agent_type="consumer")


def test_fifo_order():
    w = Waitlist()
    for i in range(5):
        w.enqueue(_a(i), current_time=0.0)
    order = [w.dequeue().agent_id for _ in range(5)]
    assert order == ["a0", "a1", "a2", "a3", "a4"]


def test_reentry_goes_to_back():
    w = Waitlist()
    a0 = _a(0); a1 = _a(1)
    w.enqueue(a0, 0.0)
    w.enqueue(a1, 0.0)
    first = w.dequeue()
    assert first.agent_id == "a0"
    w.enqueue(first, current_time=10.0)   # re-enter at back
    nxt = w.dequeue()
    assert nxt.agent_id == "a1"
    third = w.dequeue()
    assert third.agent_id == "a0"


def test_empty_queue_zero_wait():
    w = Waitlist()
    assert w.is_empty()
    assert w.dequeue() is None