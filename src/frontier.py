from typing import List


def pareto_frontier(rows: List[dict]) -> List[dict]:
    """Keep rows where no other row has BOTH lower scalper_share
    AND higher fulfillment."""
    def better(a, b):  # a dominates b
        return (a["scalper_share"] <= b["scalper_share"] and
                a["fulfillment_mean"] >= b["fulfillment_mean"] and
                (a["scalper_share"] < b["scalper_share"] or
                 a["fulfillment_mean"] > b["fulfillment_mean"]))
    front = []
    for r in rows:
        if not any(better(o, r) for o in rows if o is not r):
            front.append(r)
    return sorted(front, key=lambda r: r["scalper_share"])