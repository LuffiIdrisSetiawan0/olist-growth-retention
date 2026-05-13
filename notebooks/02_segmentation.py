# ---
# jupyter:
#   jupytext:
#     formats: py:percent,ipynb
#     text_representation:
#       extension: .py
#       format_name: percent
# ---

# %% [markdown]
# # 02 — RFM + KMeans customer segmentation
#
# We already have a rule-based segment label in `customer_rfm`. Here we refine it with KMeans on log-transformed RFM features, then compare clusters to the rule-based labels.

# %%
import sys
from pathlib import Path

try:
    HERE = Path(__file__).resolve().parent
except NameError:
    HERE = Path.cwd()
ROOT = HERE if HERE.name != "notebooks" else HERE.parent
sys.path.insert(0, str(ROOT / "src"))

import matplotlib  # noqa: E402

if "ipykernel" not in sys.modules:
    matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import seaborn as sns  # noqa: E402
from sklearn.cluster import KMeans  # noqa: E402
from sklearn.metrics import silhouette_score  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

from olist.io import read_mart  # noqa: E402

sns.set_theme(style="whitegrid")
pd.set_option("display.max_columns", 50)

FIGURES_DIR = ROOT / "reports" / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)
INTERACTIVE = "ipykernel" in sys.modules


def save(fig: plt.Figure, name: str) -> None:
    fig.savefig(FIGURES_DIR / f"{name}.png", dpi=150, bbox_inches="tight")
    if not INTERACTIVE:
        plt.close(fig)


# %% [markdown]
# ## Load the RFM mart

# %%
rfm = read_mart("customer_rfm")
n_before = len(rfm)
rfm = rfm.dropna(subset=["recency_days", "frequency", "monetary"]).reset_index(drop=True)
print(f"customers: {len(rfm):,}  (dropped {n_before - len(rfm)} rows with NaN R/F/M)")
print(rfm[["recency_days", "frequency", "monetary"]].describe().round(2))

# %% [markdown]
# Frequency and monetary are heavily right-skewed (most customers buy once for ~100 BRL). Log-transform both.

# %%
X = pd.DataFrame(
    {
        "recency_days": rfm["recency_days"],
        "log_frequency": np.log1p(rfm["frequency"]),
        "log_monetary": np.log1p(rfm["monetary"]),
    }
)
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X.values)

# %% [markdown]
# ## Pick `k` — elbow + silhouette

# %%
ks = list(range(2, 9))
inertias = []
silhouettes = []
rng = np.random.default_rng(42)
sample_idx = rng.choice(len(X_scaled), size=min(10_000, len(X_scaled)), replace=False)

for k in ks:
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = km.fit_predict(X_scaled)
    inertias.append(km.inertia_)
    silhouettes.append(silhouette_score(X_scaled[sample_idx], labels[sample_idx]))
    print(f"k={k}  inertia={km.inertia_:>12,.0f}  silhouette={silhouettes[-1]:.4f}")

# %%
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
axes[0].plot(ks, inertias, marker="o", color="#1f77b4")
axes[0].set_xlabel("k")
axes[0].set_ylabel("Inertia")
axes[0].set_title("Elbow")

axes[1].plot(ks, silhouettes, marker="o", color="#ff7f0e")
axes[1].set_xlabel("k")
axes[1].set_ylabel("Silhouette")
axes[1].set_title("Silhouette (10k sample)")
plt.tight_layout()
save(fig, "06_kmeans_elbow")

# %% [markdown]
# Pick **k = 4** as a portfolio-friendly default — elbow flattens after k=4, silhouette stays comparable.

# %%
K = 4
final_km = KMeans(n_clusters=K, random_state=42, n_init=20)
rfm["kmeans_cluster"] = final_km.fit_predict(X_scaled)

# Sort clusters by mean monetary for stable labeling across re-runs
order = (
    rfm.groupby("kmeans_cluster")["monetary"].mean().sort_values(ascending=False).index.tolist()
)
label_map = {old: f"C{rank}" for rank, old in enumerate(order)}
rfm["cluster"] = rfm["kmeans_cluster"].map(label_map)

profile = (
    rfm.groupby("cluster")
    .agg(
        n=("customer_unique_id", "count"),
        recency_mean=("recency_days", "mean"),
        recency_median=("recency_days", "median"),
        frequency_mean=("frequency", "mean"),
        monetary_mean=("monetary", "mean"),
        monetary_median=("monetary", "median"),
    )
    .round(2)
    .sort_index()
)
print("Cluster profile (sorted by mean monetary value desc):")
print(profile)

# %% [markdown]
# ## Cross-tab with the rule-based labels

# %%
xtab = pd.crosstab(rfm["cluster"], rfm["rfm_segment_label"])
xtab_pct = (xtab.T / xtab.sum(axis=1)).T * 100
print("\nCluster x rule-based label (counts):")
print(xtab)
print("\nCluster x rule-based label (% of cluster):")
print(xtab_pct.round(1))

# %% [markdown]
# Most KMeans clusters correspond loosely to a rule-based label but with smoother boundaries. The KMeans view is preferred for downstream targeting because it doesn't depend on hand-picked R/F/M thresholds.

# %% [markdown]
# ## Visualize clusters in 2D
#
# Two scatter views: (recency, log_frequency) and (log_frequency, log_monetary). With ~95k points, draw a 5k sample.

# %%
plot_df = rfm.sample(5_000, random_state=42).copy()
plot_df["log_frequency"] = np.log1p(plot_df["frequency"])
plot_df["log_monetary"] = np.log1p(plot_df["monetary"])

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
palette = sns.color_palette("Set2", K)
sns.scatterplot(
    data=plot_df,
    x="recency_days",
    y="log_frequency",
    hue="cluster",
    palette=palette,
    s=8,
    alpha=0.6,
    ax=axes[0],
)
axes[0].set_title("Clusters in (recency, log frequency)")

sns.scatterplot(
    data=plot_df,
    x="log_frequency",
    y="log_monetary",
    hue="cluster",
    palette=palette,
    s=8,
    alpha=0.6,
    ax=axes[1],
    legend=False,
)
axes[1].set_title("Clusters in (log frequency, log monetary)")
plt.tight_layout()
save(fig, "07_kmeans_clusters_2d")

# %% [markdown]
# ## Save cluster assignments

# %%
OUT_DIR = ROOT / "data" / "exports"
OUT_DIR.mkdir(parents=True, exist_ok=True)
rfm[["customer_unique_id", "cluster", "kmeans_cluster"]].to_csv(
    OUT_DIR / "customer_clusters.csv", index=False
)
print(f"Saved {len(rfm):,} cluster assignments -> data/exports/customer_clusters.csv")

# %% [markdown]
# ## Next step
#
# In `03_repeat_purchase.py` we model the binary outcome "did this customer buy again within 180 days of first purchase".
