"""
Stage 6: Visualization
  (A) 2x2 small-multiples figure: each department's undirected network,
      nodes colored by their own Louvain community, sized by weighted degree.
  (B) A 3-panel bar chart comparing density, avg degree, and modularity
      side-by-side across the 4 departments (small multiples instead of a
      dual/triple axis, consistent department color across panels).
"""
import pickle
from math import sqrt
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd

OUT_DIR = Path(__file__).resolve().parent
DEPTS = ["Dept1", "Dept2", "Dept3", "Dept4"]

# ---- chrome / palette (dataviz skill reference palette) ----
SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"

DEPT_COLOR = {
    "Dept1": "#2a78d6",  # blue
    "Dept2": "#eb6834",  # orange
    "Dept3": "#1baf7a",  # aqua
    "Dept4": "#eda100",  # yellow
}

plt.rcParams.update({
    "font.family": "sans-serif",
    "text.color": TEXT_PRIMARY,
    "axes.edgecolor": GRID,
    "axes.labelcolor": TEXT_SECONDARY,
    "xtick.color": TEXT_SECONDARY,
    "ytick.color": TEXT_SECONDARY,
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
})

with open(OUT_DIR / "partitions.pkl", "rb") as f:
    pdata = pickle.load(f)
partitions = pdata["partitions"]
undirected_graphs = pdata["undirected_graphs"]

master = pd.read_csv(OUT_DIR / "cross_department_master.csv", index_col="Department")

# ---------------------------------------------------------------
# Figure A: 2x2 network small multiples colored by community
# ---------------------------------------------------------------
fig, axes = plt.subplots(2, 2, figsize=(13, 13))
cmap = plt.get_cmap("tab20")

for ax, dept in zip(axes.flat, DEPTS):
    UG = undirected_graphs[dept]
    part = partitions[dept]
    n_comms = len(set(part.values()))

    pos = nx.spring_layout(UG, weight="weight", seed=42, k=1.6 / sqrt(UG.number_of_nodes()))

    node_colors = [cmap(part[n] % 20) for n in UG.nodes()]
    wdeg = dict(UG.degree(weight="weight"))
    max_wdeg = max(wdeg.values())
    node_sizes = [30 + 500 * sqrt(wdeg[n] / max_wdeg) for n in UG.nodes()]

    edge_weights = np.array([UG[u][v]["weight"] for u, v in UG.edges()])
    edge_widths = 0.2 + 1.0 * (edge_weights / edge_weights.max())

    nx.draw_networkx_edges(UG, pos, ax=ax, width=edge_widths, edge_color=GRID, alpha=0.6)
    nx.draw_networkx_nodes(UG, pos, ax=ax, node_size=node_sizes, node_color=node_colors,
                            linewidths=0.4, edgecolors="white")

    row = master.loc[dept]
    ax.set_title(
        f"{dept}  —  {int(row['Nodes'])} people, {n_comms} sub-communities, "
        f"Q={row['Modularity (Q)']:.2f}",
        fontsize=11, color=TEXT_PRIMARY, loc="left"
    )
    ax.set_axis_off()

fig.suptitle("Within-department networks colored by detected sub-community",
             fontsize=14, color=TEXT_PRIMARY, y=0.995)
fig.text(0.5, 0.005,
         "Node size = weighted degree (email volume) · color = Louvain community "
         "(colors are local to each department, not comparable across panels)",
         ha="center", fontsize=9, color=MUTED)
fig.tight_layout(rect=[0, 0.02, 1, 0.97])
fig.savefig(OUT_DIR / "fig_networks_2x2.png", dpi=170)
print("Saved analysis/fig_networks_2x2.png")
plt.close(fig)

# ---------------------------------------------------------------
# Figure B: 3-panel bar chart, density / avg degree / modularity
# ---------------------------------------------------------------
metrics = [
    ("Density", "Density"),
    ("Avg degree (in+out)", "Avg. degree (in+out)"),
    ("Modularity (Q)", "Louvain modularity (Q)"),
]

fig2, axes2 = plt.subplots(1, 3, figsize=(13, 4.5))
x = np.arange(len(DEPTS))

for ax, (col, label) in zip(axes2, metrics):
    vals = master.loc[DEPTS, col].values
    colors = [DEPT_COLOR[d] for d in DEPTS]
    bars = ax.bar(x, vals, color=colors, width=0.62)
    ax.set_xticks(x)
    ax.set_xticklabels(DEPTS, fontsize=10)
    ax.set_title(label, fontsize=11, color=TEXT_PRIMARY, loc="left")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(left=False)
    ax.set_yticks([])
    ax.grid(False)

    for rect, v in zip(bars, vals):
        ax.text(rect.get_x() + rect.get_width() / 2, rect.get_height(),
                f"{v:.3f}" if v < 1 else f"{v:.1f}",
                ha="center", va="bottom", fontsize=9.5, color=TEXT_PRIMARY)

fig2.suptitle("Cross-department comparison: cohesion, connectivity, fragmentation",
              fontsize=13, color=TEXT_PRIMARY)
fig2.tight_layout(rect=[0, 0, 1, 0.93])
fig2.savefig(OUT_DIR / "fig_bar_comparison.png", dpi=170)
print("Saved analysis/fig_bar_comparison.png")
plt.close(fig2)
