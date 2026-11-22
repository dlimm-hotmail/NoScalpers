import sys
import json
from src.config import load_config, validate
from src.simulation import run_one
from src.metrics import compute_metrics
from src.scalper_network import this_store_rate, displacement_factor
from src.secondary_market import run_secondary_market


def run_scenario(path: str = None, seeds: int = 30):
    cfg = load_config(path)
    validate(cfg)
    agg = {}
    for s in range(seeds):
        sim = run_one(cfg, seed=s)
        m = compute_metrics(sim["consumers"], sim["scalpers"], sim["skus"], cfg)
        m["this_store_rate"] = this_store_rate(sim["scalpers"])
        m["displacement_factor"] = displacement_factor(cfg, m["this_store_rate"])
        for k, v in m.items():
            agg.setdefault(k, []).append(v)
    out = {k: sum(v) / len(v) for k, v in agg.items()}
    print(json.dumps(out, indent=2))
    return out


def run_sweep_demo():
    from src.sweep import run_sweep
    from src.frontier import pareto_frontier
    from src.viz import plot_pareto
    sweep_cfg = load_config("config/scenarios/sweep_grid.yaml")
    rows = run_sweep(sweep_cfg)
    front = pareto_frontier(rows)
    print(f"sweep rows: {len(rows)}, frontier points: {len(front)}")
    for r in front:
        print(f"  share={r['scalper_share']:.2f} "
              f"fulfill={r['fulfillment_mean']:.2f} "
              f"friction_p90={r['friction_p90_min']:.0f} "
              f"displace={r['displacement_factor']:.2f} "
              f"params={r['params']}")
    plot_pareto(rows, "pareto.png")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "sweep":
        run_sweep_demo()
    else:
        path = sys.argv[1] if len(sys.argv) > 1 else "config/scenarios/no_mechanism.yaml"
        run_scenario(path)