from src.types import Agent


class Waitlist:
    """Persistent position-ordered queue with a per-agent serve timer.
    A gated agent keeps its position; the register skips it and serves
    the next ready agent behind it. No one is demoted on cooldown."""

    def __init__(self):
        self._q: list = []

    def add(self, agent: Agent, now: float):
        agent.earliest_serve_time = now
        agent.last_ready_time = now
        agent.time_entered_queue = now
        self._q.append(agent)

    def first_ready(self, now: float):
        """First agent in position order whose timer has opened."""
        for a in self._q:
            if a.earliest_serve_time <= now:
                return a
        return None

    def remove(self, agent: Agent):
        self._q = [a for a in self._q if a.agent_id != agent.agent_id]

    def min_eligible(self, now: float):
        """Earliest future timer among queued agents (for clock advance)."""
        future = [a.earliest_serve_time for a in self._q if a.earliest_serve_time > now]
        return min(future) if future else None

    def is_empty(self) -> bool:
        return not self._q

    def size(self) -> int:
        return len(self._q)

    def __len__(self):
        return len(self._q)