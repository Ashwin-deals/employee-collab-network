"""
Collect every number the report quotes into report_data.json, read from the
analysis outputs. build_report.js only formats these values, so the report
always matches the latest pipeline run.

    python3 report/report_data.py && node report/build_report.js
"""
import ast
import json
import pickle
from pathlib import Path

import matplotlib.image as mpimg
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
A = ROOT / "analysis"
DEPTS = ["Dept1", "Dept2", "Dept3", "Dept4"]

master = pd.read_csv(A / "cross_department_master.csv", index_col="Department")
cent_sum = pd.read_csv(A / "centrality_summary.csv", index_col="Department")
bursts = pd.read_csv(A / "temporal_bursts.csv")
evol = pd.read_csv(A / "temporal_structural_evolution.csv")
low_weeks = pd.read_csv(A / "low_weeks.csv")
offsets = pd.read_csv(A / "clock_offsets.csv", index_col="Department")
rhythm = pd.read_csv(A / "rhythm_summary.csv", index_col=0)["Value"]
sync = pd.read_csv(A / "temporal_synchrony.csv", index_col=0)["Value"]
with open(A / "centrality_tables.pkl", "rb") as f:
    centrality = pickle.load(f)
with open(A / "partitions.pkl", "rb") as f:
    partitions = pickle.load(f)["partitions"]


def num(v):
    """JSON-safe Python number."""
    return v.item() if hasattr(v, "item") else v


# ── per-department metrics ──────────────────────────────────────────────────
depts = {}
for d in DEPTS:
    r = master.loc[d]
    c = cent_sum.loc[d]
    t = centrality[d]
    pr = t["pagerank"].sort_values(ascending=False)
    btw = t["betweenness"].sort_values(ascending=False)
    depts[d] = {
        "nodes": int(r["Nodes"]),
        "edges": int(r["Edges (directed)"]),
        "emails": int(r["Total emails (weight sum)"]),
        "per_channel": r["Total emails (weight sum)"] / r["Edges (directed)"],
        "per_person": r["Total emails (weight sum)"] / r["Nodes"],
        "density": num(r["Density"]),
        "contacts": num(r["Avg distinct contacts"]),
        "wcc": int(r["Weakly conn. components"]),
        "largest_wcc_pct": num(r["Largest WCC (% nodes)"]),
        "scc": int(r["Strongly conn. components"]),
        "largest_scc_pct": num(r["Largest SCC (% nodes)"]),
        "single_scc": int(r["Single-person SCCs"]),
        "receive_only": int(r["Receive-only people"]),
        "reciprocity": num(r["Reciprocity"]),
        "reciprocity_random": num(r["Reciprocity (random baseline)"]),
        "clustering": num(r["Avg clustering"]),
        "clustering_random": num(r["Clustering (random baseline)"]),
        "clustering_ratio": num(r["Clustering vs random (x)"]),
        "communities": int(r["Num sub-communities"]),
        "q": num(r["Modularity (Q)"]),
        "largest_comm_pct": num(r["Largest community (% nodes)"]),
        "cross_comm_pct": num(r["Nodes with cross-community ties (%)"]),
        "comms_per_wcc": num(r["Communities per WCC"]),
        "q_min": num(r["Q min over 20 seeds"]),
        "q_max": num(r["Q max over 20 seeds"]),
        "comms_min": int(r["Communities min over 20 seeds"]),
        "comms_max": int(r["Communities max over 20 seeds"]),
        "top_pr_node": int(pr.index[0]),
        "top_pr": num(pr.iloc[0]),
        "pr_lead": num(pr.iloc[0] / pr.iloc[1]),
        "pr_lead5": num(pr.iloc[0] / pr.iloc[4]),
        "top_btw_node": int(btw.index[0]),
        "top_btw": num(btw.iloc[0]),
        "top5_btw_share": num(c["Top-5 share of betweenness"]),
        "top5_email_share": num(c["Top-5 share of email volume"]),
        "zero_btw_pct": num(c["Zero-betweenness nodes (%)"]),
        "in_all_three": ast.literal_eval(c["In top-5 of degree, betweenness and PageRank"]),
        "top_pr_node_emails": int(t.loc[pr.index[0], "weighted_degree"]),
        "clock_offset_h": int(offsets.loc[d, "OffsetHours"]),
    }

# Dept1: are all top brokers inside the largest community?
sizes = pd.Series(partitions["Dept1"]).value_counts()
top5_btw = centrality["Dept1"]["betweenness"].sort_values(ascending=False).head(5).index
depts["Dept1"]["brokers_in_largest_comm"] = all(partitions["Dept1"][n] == sizes.index[0] for n in top5_btw)
depts["Dept1"]["largest_comm_size"] = int(sizes.iloc[0])

# ── temporal ────────────────────────────────────────────────────────────────
main = bursts[bursts["InMainWindow"]]
main_evol = evol[evol["MonthIdx"].isin(main["MonthIdx"].unique())]
month_mean = main_evol.groupby("Department")["EmailVolume"].mean()
temporal = {
    "first_month": int(main["MonthIdx"].min()),
    "last_month": int(main["MonthIdx"].max()),
    "z_min": num(main["ZScore"].min()),
    "z_max": num(main["ZScore"].max()),
    "high": {d: list(main[(main["Department"] == d) & main["IsBurst"]]["Month"]) for d in DEPTS},
    "low": {d: list(main[(main["Department"] == d) & main["IsQuiet"]]["Month"]) for d in DEPTS},
    "dept3_m13_z": num(main[(main["Department"] == "Dept3") & (main["Month"] == "M13")]["ZScore"].iloc[0]),
    "monthly_mean": {d: num(month_mean[d]) for d in DEPTS},
    "m14": {d: int(main_evol[(main_evol["Department"] == d) & (main_evol["Month"] == "M14")]["EmailVolume"].iloc[0])
            for d in DEPTS},
    "sync_observed": int(float(sync["SharedFlaggedMonthsObserved"])),
    "sync_expected": float(sync["SharedFlaggedMonthsExpected"]),
    "sync_p": float(sync["PValue"]),
    "sync_perms": int(float(sync["Permutations"])),
    "flagged_share": float(sync["ShareOfMonthsFlagged"]),
    "main_end": int(rhythm["MainWindowLastDay"]),
    "resume_day": int(float(rhythm["DataResumesDay"])),
    "clock_spread_h": int(rhythm["DeptClockSpreadHours"]),
    "weekend_pct": float(rhythm["WeekendPctOfWeekday"]),
    "peak_day": int(rhythm["PeakWeekCentreDay"]),
    "peak_month": rhythm["PeakWeekMonth"],
    "peak_ratio": float(rhythm["PeakWeekVsMedian"]),
    "median_week": int(rhythm["MedianWeekEmails"]),
    "annual_pairs": ast.literal_eval(rhythm["LowPeriodsAboutOneYearApart"]),
    "low_weeks": [
        {"start": int(r.StartDay), "end": int(r.EndDay), "months": ast.literal_eval(r.Months),
         "pct": float(r.PctOfTypicalDay)}
        for r in low_weeks.itertuples()
    ],
}

# ── figures ─────────────────────────────────────────────────────────────────
figures = {}
for name in ["fig_networks_2x2", "fig_bar_comparison", "fig_centrality_top",
             "fig_temporal_heatmap", "fig_temporal_volume", "fig_daily_rhythm"]:
    path = A / f"{name}.png"
    h, w = mpimg.imread(path).shape[:2]
    figures[name] = {"path": str(path), "width": int(w), "height": int(h)}

data = {
    "depts": depts,
    "totals": {"nodes": int(master["Nodes"].sum()),
               "emails": int(master["Total emails (weight sum)"].sum())},
    "temporal": temporal,
    "figures": figures,
}
out = Path(__file__).resolve().parent / "report_data.json"
out.write_text(json.dumps(data, indent=2, default=num))
print(f"Saved {out.relative_to(ROOT)}")
