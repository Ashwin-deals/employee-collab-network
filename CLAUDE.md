# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

A social network analysis (SNA) project over the SNAP "Email-Eu-core temporal network" dataset, split by department. It analyzes email communication patterns *within* each department as an independent network (structure, centrality, community detection) and compares the four departments against each other.

## Data (`data/`)

- `email-Eu-core-temporal-Dept{1,2,3,4}.gz` — one gzipped edge list per department, each line is `src dst timestamp` (a single email event).
- `email-Eu-core-temporal.gz` — the full undivided dataset (not currently consumed by any script in `analysis/`).
- **Node IDs are local to each department file** — the same integer in Dept1 and Dept2 refers to different, unrelated people. Never merge or compare raw node IDs across departments; the four department graphs must be built and analyzed as fully independent networks.

## Running the analysis

There's no build system, package manifest, or test suite — this is a sequence of standalone Python scripts run from the repo root with `python3`. Dependencies (no `requirements.txt` yet): `networkx` (>=3.0, for the built-in `nx.community.louvain_communities`/`modularity`), `pandas`, `numpy`, `matplotlib`.

The pipeline in `analysis/` is a strict sequential chain — each stage loads the pickle(s) the previous stage wrote, so they must be run in order after any change to an earlier stage:

```
stage1_build_graphs.py     -> graphs.pkl
stage2_structural.py       (reads graphs.pkl)                  -> structural_comparison.csv
stage3_centrality.py       (reads graphs.pkl)                  -> centrality_Dept*.csv, centrality_tables.pkl
stage4_community.py        (reads graphs.pkl)                  -> community_summary.csv, partitions.pkl
stage5_cross_dept.py       (reads structural_comparison.csv, community_summary.csv) -> cross_department_master.csv
stage6_visualization.py    (reads partitions.pkl, cross_department_master.csv)      -> fig_networks_2x2.png, fig_bar_comparison.png
```

Re-run a single stage with `python3 analysis/stageN_*.py`; re-run the whole pipeline by running stages 1 through 6 in order. All generated CSV/PKL/PNG files in `analysis/` are build artifacts, not source of truth — regenerate them rather than hand-editing.

## Architecture notes

- **Stage 1** builds one `networkx.DiGraph` per department (`{"Dept1": G1, "Dept2": G2, ...}` in `graphs.pkl`). Multiple email events between the same ordered `(src, dst)` pair are collapsed into a single directed edge with `weight` = event count — this is the weighted graph every later stage builds on.
- **Stage 2** computes density, average total (in+out) degree, and weak/strong connected components directly on the directed graphs.
- **Stage 3** computes degree, betweenness (unweighted/topological), and PageRank (weighted) per department, independently — centrality is never compared across departments since node identities don't correspond.
- **Stage 4** projects each department's `DiGraph` to an undirected weighted `Graph` (summing weight in both directions) before running Louvain, since modularity/Louvain in networkx is defined for undirected graphs. Watch for this when interpreting modularity: departments that are already split into disconnected weakly-connected components (Dept1, Dept2, Dept4) get inflated modularity almost "for free," since Louvain can't (and doesn't need to) find any cross-component structure. Dept3, which is a single connected component, is the only department whose modularity reflects genuine community structure discovered within one connected network — this distinction matters for any interpretation of "fragmentation."
- **Stage 6** follows the project's `dataviz` skill conventions: the categorical department colors (blue/orange/aqua/green) come from the skill's reference palette and are validated with its palette validator script; the network small-multiples use `tab20` for community coloring (colors are local to each subplot/department and are not meant to be compared across panels).
