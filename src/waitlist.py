from src.types import Agent

class Waitlist:
    def __init__(self):
        self._q: list = []
    def add(self, agent, now):
        agent.earliest_serve_time = now
        agent.last_ready_time = now
        agent.time_entered_queue = now
        self._q.append(agent)
    def first_ready(self, now):
        for a in self._q:
            if a.earliest_serve_time <= now:
                return a
        return None
    def remove(self, agent):
        self._q = [a for a in self._q if a.agent_id != agent.agent_id]
    def min_eligible(self, now):
        f=[a.earliest_serve_time for a in self._q if a.earliest_serve_time>now]
        return min(f) if f else None
    def is_empty(self): return not self._q
    def size(self): return len(self._q)
    def __len__(self): return len(self._q)