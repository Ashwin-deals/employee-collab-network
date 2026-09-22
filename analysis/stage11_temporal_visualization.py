"""
Stage 11: Temporal Visualizations
Produces three figures:

  fig_temporal_volume.png   — 4-panel line chart of monthly email volume
                              with burst months highlighted in red.
  fig_temporal_metrics.png  — 3-row × 4-col small multiples: density,
                              avg degree, and active-node count over time
                              per department.
  fig_temporal_heatmap.png  — email-volume heatmap (months × departments),
                              useful for spotting shared activity peaks.

Reads:   temporal_structural_evolution.csv, temporal_bursts.csv
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

OUT_DIR = Path(__file__).resolve().parent
DEPTS   = ["Dept1", "Dept2", "Dept3", "Dept4"]

# ── palette (dataviz skill reference) ────────────────────────────────────────
SURFACE      = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SEC     = "#52514e"
MUTED        = "#898781"
GRID         = "#e1e0d9"
BURST_COLOR  = "#d93025"
QUIET_COLOR  = "#5b5ea6"

DEPT_COLOR = {
    "Dept1": "#2a78d6",
    "Dept2": "#eb6834",
    "Dept3": "#1baf7a",
    "Dept4": "#eda100",
}

plt.rcParams.update({
    "font.family":        "sans-serif",
    "text.color":         TEXT_PRIMARY,
    "axes.edgecolor":     GRID,
    "axes.labelcolor":    TEXT_SEC,
    "xtick.color":        TEXT_SEC,
    "ytick.color":        TEXT_SEC,
    "figure.facecolor":   SURFACE,
    "axes.facecolor":     SURFACE,
    "savefig.facecolor":  SURFACE,
    "axes.grid":          True,
    "grid.color":         GRID,
    "grid.linewidth":     0.6,
})

evol   = pd.read_csv(OUT_DIR / "temporal_structural_evolution.csv")
bursts = pd.read_csv(OUT_DIR / "temporal_bursts.csv")

# ── Figure A: monthly email volume with burst markers ────────────────────────
fig, axes = plt.subplots(2, 2, figsize=(14, 8), sharex=False)
fig.suptitle("Monthly email volume per department  (▲ = burst month)",
             fontsize=13, color=TEXT_PRIMARY)

for ax, dept in zip(axes.flat, DEPTS):
    d    = evol[evol["Department"] == dept].sort_values("MonthIdx")
    b    = bursts[(bursts["Department"] == dept) & bursts["IsBurst"]]
    x    = d["MonthIdx"].values
    y    = d["EmailVolume"].values
    col  = DEPT_COLOR[dept]

    ax.fill_between(x, y, alpha=0.18, color=col)
    ax.plot(x, y, color=col, linewidth=1.8, zorder=3)

    # rolling mean baseline (active months only)
    dept_b = bursts[bursts["Department"] == dept]
    rm_active = dept_b[dept_b["EmailVolume"] > 0].set_index("MonthIdx")["RollingMean"]
    if not rm_active.empty:
        ax.plot(rm_active.index, rm_active.values, color=MUTED, linewidth=1,
                linestyle="--", label="rolling mean")

    # high-activity markers
    b_high = dept_b[dept_b["IsBurst"]]
    if not b_high.empty:
        bx = b_high["MonthIdx"].values
        by = d.set_index("MonthIdx").loc[bx, "EmailVolume"].values
        ax.scatter(bx, by, color=BURST_COLOR, zorder=5, s=70,
                   marker="^", label="high activity")

    # low-activity markers (active months only)
    b_low = dept_b[dept_b["IsQuiet"] & (dept_b["EmailVolume"] > 0)]
    if not b_low.empty:
        qx = b_low["MonthIdx"].values
        qy = d.set_index("MonthIdx").loc[qx, "EmailVolume"].values
        ax.scatter(qx, qy, color=QUIET_COLOR, zorder=5, s=70,
                   marker="v", label="low activity")

    if not b_high.empty or not b_low.empty:
        ax.legend(fontsize=8, frameon=False)

    ax.set_title(dept, fontsize=11, color=col, loc="left")
    ax.set_xlabel("Month index", fontsize=9)
    ax.set_ylabel("Emails", fontsize=9)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(
        lambda v, _: f"{int(v):,}"))
    ax.spines[["top", "right"]].set_visible(False)

fig.tight_layout(rect=[0, 0, 1, 0.96])
fig.savefig(OUT_DIR / "fig_temporal_volume.png", dpi=160)
print("Saved analysis/fig_temporal_volume.png")
plt.close(fig)

# ── Figure B: density / avg degree / active nodes — small multiples ──────────
metrics = [
    ("Density",       "Network density"),
    ("AvgDegree",     "Avg. degree (in+out)"),
    ("ActiveNodes",   "Active employees"),
]

fig2, axes2 = plt.subplots(3, 4, figsize=(16, 10), sharey="row")
fig2.suptitle("Structural metrics over time — monthly snapshots",
              fontsize=13, color=TEXT_PRIMARY)

for row_i, (col, ylabel) in enumerate(metrics):
    for col_i, dept in enumerate(DEPTS):
        ax  = axes2[row_i][col_i]
        d   = evol[evol["Department"] == dept].sort_values("MonthIdx")
        clr = DEPT_COLOR[dept]

        ax.plot(d["MonthIdx"], d[col], color=clr, linewidth=1.6)
        ax.fill_between(d["MonthIdx"], d[col], alpha=0.15, color=clr)

        if row_i == 0:
            ax.set_title(dept, fontsize=11, color=clr)
        if col_i == 0:
            ax.set_ylabel(ylabel, fontsize=9)
        ax.set_xlabel("Month", fontsize=8)
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(labelsize=8)

fig2.tight_layout(rect=[0, 0, 1, 0.96])
fig2.savefig(OUT_DIR / "fig_temporal_metrics.png", dpi=160)
print("Saved analysis/fig_temporal_metrics.png")
plt.close(fig2)

# ── Figure C: email volume heatmap (departments × months) ───────────────────
pivot = evol.pivot(index="Department", columns="MonthIdx", values="EmailVolume")
pivot = pivot.loc[DEPTS]               # consistent row order
pivot = pivot.fillna(0)

fig3, ax3 = plt.subplots(figsize=(16, 3.5))
im = ax3.imshow(pivot.values, aspect="auto", cmap="YlOrRd", interpolation="nearest")

ax3.set_yticks(range(len(DEPTS)))
ax3.set_yticklabels(DEPTS, fontsize=10)
ax3.set_xlabel("Month index", fontsize=10)
ax3.set_title("Email volume heatmap — months × departments",
              fontsize=12, color=TEXT_PRIMARY, loc="left")

# activity markers on heatmap
for dept_i, dept in enumerate(DEPTS):
    for _, br in bursts[(bursts["Department"] == dept) & bursts["IsBurst"]].iterrows():
        ax3.scatter(br["MonthIdx"] - 1, dept_i,
                    marker="^", color="white", s=55, zorder=5)
    for _, br in bursts[(bursts["Department"] == dept) & bursts["IsQuiet"]
                        & (bursts["EmailVolume"] > 0)].iterrows():
        ax3.scatter(br["MonthIdx"] - 1, dept_i,
                    marker="v", color="steelblue", s=55, zorder=5)

cbar = fig3.colorbar(im, ax=ax3, orientation="vertical", pad=0.01)
cbar.set_label("Emails per month", fontsize=9)
fig3.text(0.5, -0.04,
          "▲ = high-activity month (Z > 1.0)   ▼ = low-activity month (Z < −1.0)",
          ha="center", fontsize=8, color=MUTED)

fig3.tight_layout()
fig3.savefig(OUT_DIR / "fig_temporal_heatmap.png", dpi=160, bbox_inches="tight")
print("Saved analysis/fig_temporal_heatmap.png")
plt.close(fig3)
