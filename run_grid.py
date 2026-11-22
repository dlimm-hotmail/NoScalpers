import json
from src.config import load_config, validate
from src.simulation import run_one
from src.metrics import compute_metrics
from src.scalper_network import this_store_rate, displacement_factor

SCENARIOS = [
    "S1_no_limit",
    "S2_timeout",
    "S3_cap",
    "S4_collusion_no_limit",
    "S5_collusion_timeout",
    "S6_collusion_cap",
    "S7_lottery_no_limit",
    "S8_lottery_timeout",
    "S9_lottery_cap",
    "S10_lottery_collusion_timeout",
    "T_cap_only",
    "T_cooldown_only",
    "T_per_sku_only",
    "T_total_only",
]

SEEDS = 30


def run_scenario(path: str, seeds: int = SEEDS) -> dict:
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
    return {k: sum(v) / len(v) for k, v in agg.items()}


def main():
    results = {}
    for name in SCENARIOS:
        path = f"config/scenarios/{name}.yaml"
        print(f"Running {name}...")
        results[name] = run_scenario(path)

    # Print formatted table
    cols = [
        ("Scalper Share", "scalper_share", ".3f"),
        ("Fulfill Mean", "fulfillment_mean", ".3f"),
        ("Fulfill p90", "fulfillment_p90", ".3f"),
        ("Zero Rate", "fulfillment_zero_rate", ".3f"),
        ("Friction p90", "friction_p90_min", ".0f"),
        ("Patience Exits", "patience_exits", ".0f"),
        ("Scalper Rate", "this_store_rate", ".2f"),
        ("Displacement", "displacement_factor", ".3f"),
    ]

    header = f"{'Scenario':<28}" + "".join(f"{c[0]:>14}" for c in cols)
    sep = "-" * len(header)
    print(f"\n{sep}")
    print(header)
    print(sep)

    for name in SCENARIOS:
        r = results[name]
        row = f"{name:<28}"
        for _, key, fmt in cols:
            spec = f">14{fmt}"          # e.g. ">14.3f"
            row += f"{r[key]:{spec}}"
        print(row)
        
    # Save raw JSON for further analysis
    with open("grid_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nSaved: grid_results.json")

    # Quick Pareto print
    print("\nPareto frontier (scalper_share vs fulfillment_mean):")
    pairs = [(results[n]["scalper_share"], results[n]["fulfillment_mean"], n)
             for n in SCENARIOS]
    pairs.sort(key=lambda x: x[0])
    best_fulfill = -1
    for share, fulfill, name in pairs:
        if fulfill > best_fulfill:
            print(f"  {name:<28} share={share:.3f}  fulfill={fulfill:.3f}")
            best_fulfill = fulfill


if __name__ == "__main__":
    main()