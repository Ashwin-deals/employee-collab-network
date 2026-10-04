# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

A social network analysis (SNA) project over the SNAP "Email-Eu-core temporal network" dataset, split by department. It analyzes email communication patterns *within* each department as an independent network (structure, centrality, community detection) and compares the four departments against each other.

## Data (`data/`)

- `email-Eu-core-temporal/email-Eu-core-temporal-Dept{1,2,3,4}.csv` — one edge list per department, each line is `src dst timestamp` (a single email event). Despite the `.csv` extension these are space-separated with no header (identical to SNAP's original `.gz` contents).
- `email-Eu-core-temporal/email-Eu-core-temporal.csv` — the full undivided temporal dataset. Only used by stage 14 (clock alignment, weekday profile) and the Gephi exports (stages 12–13); the network analysis itself is per department.
- `email-Eu-core/` — SNAP's static email-Eu-core network with department labels (`email-Eu-core.txt`, `email-Eu-core-department-labels.txt`) and `edges.csv`/`nodes.csv` made from them by `prepare.py` (which has hardcoded Windows paths). Not used by the pipeline yet.
- **Node IDs are local to each department file** — the same integer in Dept1 and Dept2 refers to different, unrelated people. Never merge or compare raw node IDs across departments; the four department graphs must be built and analyzed as fully independent networks.

## Running the analysis

There's no build system or test suite — this is a sequence of standalone Python scripts run from the repo root with `python3`. Dependencies are in `requirements.txt` (`networkx` >=3.0 for the built-in `nx.community.louvain_communities`/`modularity`, `pandas`, `numpy`, `matplotlib`). `python3 run_pipeline.py` runs every stage in dependency order.

The pipeline in `analysis/` is a strict sequential chain — each stage loads the pickle(s) the previous stage wrote, so they must be run in order after any change to an earlier stage:

```
stage1_build_graphs.py     -> graphs.pkl
stage2_structural.py       (reads graphs.pkl)                  -> structural_comparison.csv
stage3_centrality.py       (reads graphs.pkl)                  -> centrality_Dept*.csv, centrality_tables.pkl
stage4_community.py        (reads graphs.pkl)                  -> community_summary.csv, partitions.pkl
stage5_cross_dept.py       (reads structural_comparison.csv, community_summary.csv) -> cross_department_master.csv
stage6_visualization.py    (reads partitions.pkl, cross_department_master.csv, centrality_tables.pkl) -> fig_networks_2x2.png, fig_bar_comparison.png, fig_centrality_top.png
stage8_temporal_slices.py  (reads data/email-Eu-core-temporal/)                       -> temporal_slices.pkl
stage9_temporal_structural.py (reads temporal_slices.pkl)      -> temporal_structural_evolution.csv
stage10_temporal_bursts.py (reads temporal_structural_evolution.csv) -> temporal_bursts.csv
stage11_temporal_visualization.py (reads the two temporal CSVs) -> fig_temporal_{volume,metrics,heatmap}.png
stage14_daily_rhythm.py    (reads data/email-Eu-core-temporal/)                       -> clock_offsets.csv, daily_volume.csv, low_weeks.csv, rhythm_summary.csv, fig_daily_rhythm.png
stage7_conclusion.py       (reads the CSV/PKL outputs above)   -> conclusion.txt
stage12_export_gephi.py    (reads graphs.pkl, partitions.pkl, centrality_tables.pkl, data/) -> gephi/Dept*.gexf, gephi/*_edges.csv
stage13_export_gephi_dynamic.py (same inputs)                  -> gephi/*_dynamic.gexf
```

Re-run a single stage with `python3 analysis/stageN_*.py`; re-run the whole pipeline in the order listed above. Stage 7 must run after stages 8–11 and 14 despite its number, because the conclusion reads their outputs. All generated CSV/PKL/PNG files in `analysis/` are build artifacts, not source of truth — regenerate them rather than hand-editing.

## Architecture notes

- **Stage 1** builds one `networkx.DiGraph` per department (`{"Dept1": G1, "Dept2": G2, ...}` in `graphs.pkl`). Multiple email events between the same ordered `(src, dst)` pair are collapsed into a single directed edge with `weight` = event count — this is the weighted graph every later stage builds on.
- **Stage 2** computes density, average total (in+out) degree, and weak/strong connected components directly on the directed graphs, plus reciprocity and clustering with random baselines (density for reciprocity; degree-preserving rewiring for clustering).
- **Stage 3** computes degree, betweenness (unweighted/topological), and PageRank (weighted) per department, independently — centrality is never compared across departments since node identities don't correspond.
- **Stage 4** projects each department's `DiGraph` to an undirected weighted `Graph` (summing weight in both directions) before running Louvain, since modularity/Louvain in networkx is defined for undirected graphs. Watch for this when interpreting modularity: departments that are already split into disconnected weakly-connected components (Dept1, Dept2, Dept4) get inflated modularity almost "for free," since Louvain can't (and doesn't need to) find any cross-component structure. Dept3, which is a single connected component, is the only department whose modularity reflects genuine community structure discovered within one connected network — this distinction matters for any interpretation of "fragmentation."
- **Timestamps**: each department file's clock starts at its own first email (all start at 0). Stage 14 measures the offsets against the full dataset; departments agree with each other to within ~6 hours, so day/month comparisons across departments are valid. The data is continuous for days 0–527, then empty until a 7-day fragment at days 797–803. Monthly slice M18 is partial and M27 is that fragment, so stages 10/11 only use complete months (`InMainWindow` in `temporal_bursts.csv`).
- **Stage 7** writes the conclusion from computed values — don't hardcode numbers in its text, read them from the stage outputs.
- **Stage 6** follows the project's `dataviz` skill conventions: the categorical department colors (blue/orange/aqua/green) come from the skill's reference palette and are validated with its palette validator script; the network small-multiples use `tab20` for community coloring (colors are local to each subplot/department and are not meant to be compared across panels).

## Report

`report/` builds the Word case-study report: `report_data.py` collects every quoted number from the analysis outputs into `report_data.json`, and `build_report.js` (Node, `docx` package; `npm install` in `report/`) formats it into `SNA_Case_Study_Report.docx`. Rerun both after any pipeline change; never type numbers into the report text directly.
