# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

A social network analysis (SNA) project over the SNAP "Email-Eu-core temporal network" dataset, split by department. It analyzes email communication patterns *within* each department as an independent network — static structure, centrality, community detection, and monthly temporal dynamics (volume, structural evolution, bursts) — compares the four departments against each other, and writes up the findings in a prose conclusion.

## Data (`data/`)

- `email-Eu-core-temporal-Dept{1,2,3,4}.gz` — one gzipped edge list per department, each line is `src dst timestamp` (a single email event; timestamp is seconds from the start of observation).
- `email-Eu-core-temporal.gz` — the full undivided dataset (not currently consumed by any script in `analysis/`).
- **Node IDs are local to each department file** — the same integer in Dept1 and Dept2 refers to different, unrelated people. Never merge or compare raw node IDs across departments; the four department graphs must be built and analyzed as fully independent networks.

## Running the analysis

There's no build system, package manifest, or test suite — this is a set of standalone Python scripts run from the repo root with `python3` (each script resolves paths relative to its own file, so the working directory doesn't actually matter). Dependencies (no `requirements.txt` yet): `networkx` (>=3.0, for the built-in `nx.community.louvain_communities`/`modularity`), `pandas`, `numpy`, `matplotlib`.

Each stage reads the CSV/PKL files earlier stages wrote to `analysis/`. There are two branches that both start from the raw `data/` files, plus a conclusion stage that joins them:

```
# Static branch
stage1_build_graphs.py     (reads data/*.gz)                    -> graphs.pkl
stage2_structural.py       (reads graphs.pkl)                   -> structural_comparison.csv
stage3_centrality.py       (reads graphs.pkl)                   -> centrality_Dept*.csv, centrality_tables.pkl
stage4_community.py        (reads graphs.pkl)                   -> community_summary.csv, partitions.pkl
stage5_cross_dept.py       (reads structural_comparison.csv, community_summary.csv) -> cross_department_master.csv
stage6_visualization.py    (reads partitions.pkl, cross_department_master.csv)      -> fig_networks_2x2.png, fig_bar_comparison.png

# Temporal branch (independent of stages 1–6)
stage8_temporal_slices.py         (reads data/*.gz)                         -> temporal_slices.pkl
stage9_temporal_structural.py     (reads temporal_slices.pkl)               -> temporal_structural_evolution.csv
stage10_temporal_bursts.py        (reads temporal_structural_evolution.csv) -> temporal_bursts.csv
stage11_temporal_visualization.py (reads temporal_structural_evolution.csv, temporal_bursts.csv)
                                  -> fig_temporal_volume.png, fig_temporal_metrics.png, fig_temporal_heatmap.png

# Conclusion (joins both branches)
stage7_conclusion.py       (reads structural_comparison.csv, community_summary.csv, cross_department_master.csv,
                            temporal_structural_evolution.csv, temporal_bursts.csv) -> conclusion.txt
```

**Stage 7 must run last**, despite its number — it reads the outputs of stages 9 and 10. A full rebuild is stages 1–6, then 8–11, then 7. Re-run a single stage with `python3 analysis/stageN_*.py`. All generated CSV/PKL/PNG/TXT files in `analysis/` are build artifacts (committed to git) — regenerate them rather than hand-editing.

## Architecture notes

### Static branch

- **Stage 1** builds one `networkx.DiGraph` per department (`{"Dept1": G1, "Dept2": G2, ...}` in `graphs.pkl`). Multiple email events between the same ordered `(src, dst)` pair are collapsed into a single directed edge with `weight` = event count — this is the weighted graph every later static stage builds on.
- **Stage 2** computes density, average total (in+out) degree, and weak/strong connected components directly on the directed graphs.
- **Stage 3** computes degree, betweenness (unweighted/topological), and PageRank (weighted) per department, independently — centrality is never compared across departments since node identities don't correspond.
- **Stage 4** projects each department's `DiGraph` to an undirected weighted `Graph` (summing weight in both directions) before running Louvain, since modularity/Louvain in networkx is defined for undirected graphs. Watch for this when interpreting modularity: departments that are already split into disconnected weakly-connected components (Dept1, Dept2, Dept4) get inflated modularity almost "for free," since Louvain can't (and doesn't need to) find any cross-component structure. Dept3, which is a single connected component, is the only department whose modularity reflects genuine community structure discovered within one connected network — this distinction matters for any interpretation of "fragmentation."
- **Stage 6** follows the project's `dataviz` skill conventions: the categorical department colors (blue/orange/aqua/yellow — `#2a78d6`/`#eb6834`/`#1baf7a`/`#eda100`) come from the skill's reference palette and are validated with its palette validator script; the network small-multiples use `tab20` for community coloring (colors are local to each subplot/department and are not meant to be compared across panels).

### Temporal branch

- **Stage 8** re-reads the raw `data/` files (not `graphs.pkl`) and buckets events into fixed 30-day slices by `timestamp // (30 * 86400)`, building one weighted `DiGraph` per slice with the same edge-collapsing rule as Stage 1. Slices are labeled `M01`, `M02`, … — these are 30-day windows from the start of observation, not calendar months. `temporal_slices.pkl` is `{dept: {"graphs": [...], "event_counts": [...], "month_labels": [...]}}`.
- The observation window yields 27 slices per department, but only **M01–M18 carry real activity**: M19–M26 have zero events in every department and M27 is a short partial tail. Stages 10 and 7 drop zero-volume months before computing statistics; keep that in mind when adding new temporal metrics so the empty tail doesn't distort means, trends, or baselines.
- **Stage 9** computes per-slice active nodes, edges, email volume, density, average degree, and largest-WCC share, as a long-format CSV (one row per department × month).
- **Stage 10** flags high-/low-activity months with a z-score against a centered 5-month rolling mean/std (`WINDOW = 5`, `min_periods=3`, `Z_THRESH = 1.0`), computed per department, falling back to the department's global mean/std where the rolling window is too short. The `IsBurst` column means "high activity" (Z > 1.0); `IsQuiet` means Z < −1.0.
- **Stage 11** reuses Stage 6's department palette and chrome colors (duplicated as constants in each script — keep them in sync); burst/quiet markers use red `#d93025` and indigo `#5b5ea6`, and the heatmap uses `YlOrRd`.

### Conclusion (Stage 7)

- `stage7_conclusion.py` mixes values computed from the CSVs with **hard-coded numbers and claims in its prose** (e.g. Dept3's 89 employees and Q = 0.43, the shared M08 peak and M14 dip, the ±1.4 Z-score range, Dept3's M17 second peak). If any upstream stage changes (slice width, burst thresholds, Louvain seed, data), regenerate everything and then manually check and update those hard-coded passages against the new `conclusion.txt` / CSV outputs — the script will not flag stale text.
