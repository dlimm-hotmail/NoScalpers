import streamlit as st
from src.config import load_config, validate
from src.simulation import run_one
from src.metrics import compute_metrics
from src.scalper_network import this_store_rate, displacement_factor

SKUS = ["UPC", "ETB", "Bundle", "Tin", "Single"]

cfg = load_config()           # start from base.yaml

st.title("Scalper Policy Simulator")

# --- consumer budgets (per buyer type) ---
st.subheader("Consumer budgets ($)")
for ctype in ["hardcore", "enthusiast", "budget"]:
    cfg["consumer_budgets"][ctype] = int(
        st.number_input(ctype.capitalize(), value=cfg["consumer_budgets"][ctype],
                        min_value=10, max_value=2000, step=10))

# --- per-SKU cap (the dict) ---
st.subheader("Max qty per SKU per turn")
cfg["per_sku_qty_limit_enabled"] = st.checkbox("Enable per-SKU cap", True)
for s in SKUS:
    cfg["per_sku_qty_limit"][s] = int(
        st.number_input(f"{s} cap", value=cfg["per_sku_qty_limit"].get(s, 3),
                        min_value=1, max_value=50))

# --- mechanism toggles ---
st.subheader("Mechanisms")
cfg["spend_cap_enabled"] = st.checkbox("Dollar cap", cfg.get("spend_cap_enabled", True))
cfg["spend_cap_dollars"] = int(st.number_input("Dollar cap ($)", value=270, min_value=1, max_value=10000, step=10))
cfg["cooldown_enabled"] = st.checkbox("Progressive cooldown", cfg.get("cooldown_enabled", False))
cfg["ticket_distribution_mode"] = st.selectbox(
    "Ticket mode", ["arrival", "random_time", "waves"],
    index=["arrival", "random_time", "waves"].index(cfg.get("ticket_distribution_mode", "arrival")))
cfg["ticket_assignment"] = st.selectbox("Ticket assignment", ["sequential", "random"])
cfg["collusion_enabled"] = st.checkbox("Scalper collusion (piggyback)", cfg.get("collusion_enabled", False))

# --- metric toggle ---
cfg["include_singles_in_metrics"] = st.checkbox("Include Singles in metrics", cfg.get("include_singles_in_metrics", True))

# --- run ---
if st.button("Run scenario"):
    validate(cfg)
    agg = {}
    for seed in range(30):
        sim = run_one(cfg, seed=seed)
        m = compute_metrics(sim["consumers"], sim["scalpers"], sim["skus"], cfg)
        m["this_store_rate"] = this_store_rate(sim["scalpers"])
        m["displacement_factor"] = displacement_factor(cfg, m["this_store_rate"])
        for k, v in m.items():
            agg.setdefault(k, []).append(v)
    mean = {k: sum(v)/len(v) for k, v in agg.items()}
    st.json(mean)
    st.bar_chart({k: mean[k] for k in ["scalper_share","fulfillment_mean","fulfillment_zero_rate","this_store_rate","displacement_factor"]})