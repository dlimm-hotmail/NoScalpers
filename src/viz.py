import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def plot_pareto(rows, path="pareto.png"):
    front = sorted(rows, key=lambda r: r["scalper_share"])
    x = [r["scalper_share"] for r in front]
    y = [r["fulfillment_mean"] for r in front]
    c = [r["friction_p90_min"] for r in front]
    fig, ax = plt.subplots(figsize=(7, 5))
    sc = ax.scatter(x, y, c=c, cmap="viridis")
    ax.plot(x, y, "k--", alpha=0.4)
    ax.set_xlabel("Scalper share of supply")
    ax.set_ylabel("Consumer fulfillment (mean)")
    ax.set_title("Pareto frontier (color = consumer friction p90)")
    fig.colorbar(sc, label="friction p90 (min)")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    print(f"wrote {path}")


def plot_acquisition_curve(scalpers, alt_rate, path="acquisition.png"):
    from src.scalper_network import acquisition_curve
    pts = acquisition_curve(scalpers)
    x = [p[0] for p in pts]
    y = [p[1] for p in pts]
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(x, y, marker="o", label="this store")
    if alt_rate and x:
        ax.plot([0, x[-1]], [0, alt_rate * x[-1]], "r--",
                label=f"alt store ({alt_rate} u/hr)")
    ax.set_xlabel("person-hours invested")
    ax.set_ylabel("units acquired")
    ax.set_title("Naples curve: acquisition rate vs. the store next door")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    print(f"wrote {path}")