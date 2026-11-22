from src.config import load_config
from src.simulation import run_one
from src.metrics import compute_metrics


def test_no_mechanism_sells_out_and_extracts():
    cfg = load_config("config/scenarios/no_mechanism.yaml")
    sim = run_one(cfg, seed=1)
    m = compute_metrics(sim["consumers"], sim["scalpers"], sim["skus"], cfg)
    assert m["units_sold"] > 0
    assert m["scalper_units"] > 0
    assert 0.0 <= m["fulfillment_mean"] <= 1.0


def test_full_stack_reduces_scalper_share_vs_baseline():
    base = load_config("config/scenarios/no_mechanism.yaml")
    full = load_config("config/scenarios/full_stack.yaml")
    mb = compute_metrics(*(lambda s: (s["consumers"], s["scalpers"], s["skus"], base))(
        run_one(base, seed=7)))
    mf = compute_metrics(*(lambda s: (s["consumers"], s["scalpers"], s["skus"], full))(
        run_one(full, seed=7)))
    # The whole thesis: mechanisms cut scalper share here.
    assert mf["scalper_share"] < mb["scalper_share"]


def test_store_revenue_roughly_constant():
    base = load_config("config/scenarios/no_mechanism.yaml")
    full = load_config("config/scenarios/full_stack.yaml")
    mb = compute_metrics(*(lambda s: (s["consumers"], s["scalpers"], s["skus"], base))(
        run_one(base, seed=11)))
    mf = compute_metrics(*(lambda s: (s["consumers"], s["scalpers"], s["skus"], full))(
        run_one(full, seed=11)))
    # Both sell out, so revenue ~ equal.
    assert abs(mb["store_revenue"] - mf["store_revenue"]) / max(1, mb["store_revenue"]) < 0.2