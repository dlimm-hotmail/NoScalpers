import itertools
from typing import Dict, List
from src.config import load_config, validate
from src.simulation import run_one
from src.metrics import compute_metrics
from src.scalper_network import this_store_rate, displacement_factor


def _flatten_grid(grid: dict) -> List[dict]:
    keys = list(grid.keys())
    combos = []
    for vals in itertools.product(*[grid[k] for k in keys]):
        combos.append(dict(zip(keys, vals)))
    return combos


def run_sweep(sweep_cfg: dict) -> List[dict]:
    base = load_config()
    num_runs = int(sweep_cfg.get("num_runs", 20))
    combos = _flatten_grid(sweep_cfg["grid"])
    results = []
    for combo in combos:
        cfg = dict(base)
        cfg.update(combo)
        validate(cfg)
        agg = {}
        for r in range(num_runs):
            sim = run_one(cfg, seed=r)
            m = compute_metrics(sim["consumers"], sim["scalpers"],
                                sim["skus"], cfg)
            rate = this_store_rate(sim["scalpers"])
            m["this_store_rate"] = rate
            m["displacement_factor"] = displacement_factor(cfg, rate)
            for k, v in m.items():
                agg.setdefault(k, []).append(v)
        row = {"params": combo}
        for k, vs in agg.items():
            row[k] = sum(vs) / len(vs)
        results.append(row)
    return results