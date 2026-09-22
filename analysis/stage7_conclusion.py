"""
Stage 7: Descriptive Conclusion
Reads all generated metrics and writes a human-readable analysis conclusion
to analysis/conclusion.txt (and prints it to stdout).
"""
from pathlib import Path
import textwrap
import pandas as pd

OUT_DIR = Path(__file__).resolve().parent

structural = pd.read_csv(OUT_DIR / "structural_comparison.csv",          index_col="Department")
community  = pd.read_csv(OUT_DIR / "community_summary.csv",              index_col="Department")
master     = pd.read_csv(OUT_DIR / "cross_department_master.csv",        index_col="Department")

# ── helpers ──────────────────────────────────────────────────────────────────
def _rank(col, ascending=True):
    """Return departments ordered by col value, with the ranked value."""
    s = master[col].sort_values(ascending=ascending)
    return [(d, v) for d, v in s.items()]

def _fmt(v):
    return f"{v:.4f}" if isinstance(v, float) and v < 10 else f"{v:.1f}"

def _wrap(text, indent=0):
    prefix = " " * indent
    return textwrap.fill(text, width=90, initial_indent=prefix,
                         subsequent_indent=prefix)

# ── build the conclusion ──────────────────────────────────────────────────────
lines = []
add = lines.append

add("=" * 90)
add("  SOCIAL NETWORK ANALYSIS — EMAIL-EU-CORE TEMPORAL DATASET")
add("  Descriptive Conclusion: Cross-Department Communication Patterns")
add("=" * 90)

# ---------- 1. Overview ----------
add("")
add("1. DATASET OVERVIEW")
add("-" * 90)
add(_wrap(
    "The dataset captures intra-department email exchanges across four departments "
    "(Dept1–Dept4) of a European research institution. Each department is treated as an "
    "independent directed weighted graph: nodes are employees, directed edges represent "
    "email flow (src → dst), and edge weight equals the number of emails sent along that "
    "channel. Node IDs are local to each department and cannot be compared across them."
))
add("")

total_nodes  = master["Nodes"].sum()
total_emails = master["Total emails (weight sum)"].sum()
add(_wrap(
    f"Across all four departments the dataset covers {total_nodes} unique employees "
    f"and {total_emails:,} email events in total."
))

# ---------- 2. Network size & email volume ----------
add("")
add("2. NETWORK SIZE & EMAIL VOLUME")
add("-" * 90)

for dept in master.index:
    r = master.loc[dept]
    add(_wrap(
        f"  {dept}: {int(r['Nodes'])} employees, {int(r['Edges (directed)'])} directed edges, "
        f"{int(r['Total emails (weight sum)']):,} total emails "
        f"(avg {r['Total emails (weight sum)'] / r['Edges (directed)']:.1f} emails per channel).",
        indent=2
    ))
add("")

largest = master["Nodes"].idxmax()
busiest = master["Total emails (weight sum)"].idxmax()
add(_wrap(
    f"{largest} is the largest department by headcount "
    f"({int(master.loc[largest,'Nodes'])} people). "
    f"{busiest} carries the highest total email volume "
    f"({int(master.loc[busiest,'Total emails (weight sum)']):,} emails), "
    "suggesting that sheer department size does not determine communication volume — "
    f"smaller departments can sustain very high message throughput."
))

# ---------- 3. Network density & connectivity ----------
add("")
add("3. NETWORK DENSITY & CONNECTIVITY")
add("-" * 90)
add(_wrap(
    "Density measures the fraction of all possible directed edges that actually exist "
    "(range 0–1). A high density means most pairs of employees exchange email directly."
))
add("")

for dept, v in _rank("Density", ascending=False):
    add(f"  {dept}: density = {v:.4f}")
add("")

densest = master["Density"].idxmax()
sparsest = master["Density"].idxmin()
add(_wrap(
    f"{densest} has the highest density ({master.loc[densest,'Density']:.4f}) — "
    "nearly one in five possible email channels is actively used. "
    f"{sparsest}, the largest department, is the most sparse "
    f"({master.loc[sparsest,'Density']:.4f}), which is expected: as a network grows, "
    "density almost always falls because the number of possible edges scales with n²."
))
add("")

add("Weak connectivity (ignoring edge direction):")
for dept in master.index:
    r = master.loc[dept]
    wcc = int(r["Weakly conn. components"])
    pct = r["Largest WCC (% nodes)"]
    if wcc == 1:
        desc = "fully connected (single WCC)"
    else:
        desc = f"{wcc} components; largest covers {pct:.1f}% of employees"
    add(f"  {dept}: {desc}")
add("")

add(_wrap(
    "Dept3 is the only department whose members are all reachable from one another "
    "when ignoring email direction — a single weakly connected component covering 100% "
    "of its 89 employees. Dept1, Dept2, and Dept4 each fragment into multiple isolated "
    "sub-networks (6–9 WCCs), meaning some employee clusters never exchange email with "
    "the rest of the department even indirectly."
))

# ---------- 4. Directed connectivity: strong components ----------
add("")
add("4. DIRECTED REACHABILITY — STRONG COMPONENTS")
add("-" * 90)
add(_wrap(
    "A strongly connected component (SCC) is a group where every member can reach "
    "every other member following the direction of email flow. A large largest-SCC "
    "means information can circulate freely in a feedback loop across most of the "
    "department."
))
add("")

for dept in master.index:
    r = master.loc[dept]
    add(f"  {dept}: {int(r['Strongly conn. components'])} SCCs, "
        f"largest = {r['Largest SCC (% nodes)']:.1f}% of employees")
add("")

add(_wrap(
    "Dept3 stands out again: 88.8% of employees belong to a single SCC, meaning nearly "
    "all of them participate in mutual, reciprocal email exchange. In Dept1, despite "
    "being the largest department, the biggest SCC covers only 27.8% of employees, and "
    "there are 81 distinct strong components — indicating highly directional or "
    "hierarchical flows where most email is one-way."
))

# ---------- 5. Average degree ----------
add("")
add("5. COMMUNICATION BREADTH — AVERAGE DEGREE")
add("-" * 90)
add(_wrap(
    "Average total degree (in-degree + out-degree) measures how many distinct email "
    "partners each employee has on average."
))
add("")

for dept, v in _rank("Avg degree (in+out)", ascending=False):
    add(f"  {dept}: avg degree = {v:.2f}")
add("")

top_deg = master["Avg degree (in+out)"].idxmax()
add(_wrap(
    f"{top_deg} has the highest average degree ({master.loc[top_deg,'Avg degree (in+out)']:.2f}), "
    "meaning each employee communicates directly with roughly "
    f"{master.loc[top_deg,'Avg degree (in+out)']/2:.0f} distinct colleagues on average. "
    "This aligns with its very high density and tight connectivity."
))

# ---------- 6. Community structure ----------
add("")
add("6. COMMUNITY STRUCTURE — LOUVAIN MODULARITY")
add("-" * 90)
add(_wrap(
    "Louvain community detection was run on the undirected weighted projection of each "
    "department graph. Modularity Q ∈ [0, 1] quantifies how clearly the network "
    "separates into distinct sub-groups: Q > 0.6 is generally considered strong "
    "modular structure; Q < 0.4 suggests a more cohesive, integrated network."
))
add("")

for dept in master.index:
    r = master.loc[dept]
    nc  = int(r["Num sub-communities"])
    q   = r["Modularity (Q)"]
    pct = r["Largest community (% nodes)"]
    add(f"  {dept}: {nc} communities, Q = {q:.4f}, "
        f"largest community = {pct:.1f}% of employees")
add("")

add(_wrap(
    "Important interpretive caveat: Dept1, Dept2, and Dept4 each have multiple "
    "disconnected weakly connected components (WCCs). Louvain trivially assigns each "
    "isolated WCC to its own community, so their high modularity values (0.69–0.79) "
    "partly reflect pre-existing network disconnection rather than genuine internal "
    "sub-group structure. Their 'Communities per WCC' ratios of ~1.0–1.2 confirm this: "
    "almost every community maps to exactly one WCC."
))
add("")
add(_wrap(
    "Dept3 is the analytically cleaner case: all employees are in a single WCC, yet "
    "Louvain still finds 6 distinct communities (Q = 0.43, Communities per WCC = 6.0). "
    "This Q, while lower than the other departments, represents genuine internal "
    "sub-group structure discovered within one connected network — not fragmentation "
    "inherited from disconnected components. Dept3's 6 communities are organic "
    "communication clusters."
))

# ---------- 7. Temporal analysis ----------
add("")
add("7. TEMPORAL ANALYSIS — COMMUNICATION DYNAMICS OVER 27 MONTHS")
add("-" * 90)
add(_wrap(
    "The dataset spans ~803 days (~27 months). Each department's events were partitioned "
    "into 30-day slices and analysed as independent monthly snapshots. Months 19–26 have "
    "zero events across all departments (the observation window closes), and month 27 "
    "is a short partial tail; all activity-pattern analysis below covers the 18 active "
    "months only."
))

# load temporal data
tdf   = pd.read_csv(OUT_DIR / "temporal_structural_evolution.csv")
bdf   = pd.read_csv(OUT_DIR / "temporal_bursts.csv")
active_tdf = tdf[tdf["EmailVolume"] > 0]

add("")
add("  Monthly email volume statistics (active months only):")
for dept in ["Dept1", "Dept2", "Dept3", "Dept4"]:
    d = active_tdf[active_tdf["Department"] == dept]["EmailVolume"]
    add(f"  {dept}: mean={d.mean():.0f}, std={d.std():.0f}, "
        f"min={int(d.min())}, max={int(d.max())} emails/month")

add("")
add(_wrap(
    "High-activity months (Z-score > 1.0 above 5-month rolling mean):"
))
for dept in ["Dept1", "Dept2", "Dept3", "Dept4"]:
    hi = bdf[(bdf["Department"] == dept) & bdf["IsBurst"] & (bdf["EmailVolume"] > 0)]
    lo = bdf[(bdf["Department"] == dept) & bdf["IsQuiet"] & (bdf["EmailVolume"] > 0)]
    add(f"  {dept}: high → {list(hi['Month'])}   low → {list(lo['Month'])}")

add("")
add(_wrap(
    "Month 8 (M08) is a high-activity month in all four departments simultaneously — "
    "a coordinated surge roughly 8 months into the observation period. This cross-"
    "department synchrony suggests an institution-wide event (e.g. a project deadline, "
    "conference, or end-of-semester period) rather than department-specific causes."
))
add("")
add(_wrap(
    "Months 3, 10, and 14 are consistently low across all departments. M14 is the most "
    "pronounced dip: Dept4 falls to just 562 emails (vs its ~1,783 monthly average), "
    "Dept2 to 1,024, and Dept1 to 1,683 — all well below their baselines and consistent "
    "with a shared vacation or semester break. M03 and M10 show similar, milder "
    "reductions, possibly corresponding to mid-semester lulls or shorter holiday periods."
))
add("")
add(_wrap(
    "Dept3 partially diverges from the others: its second high-activity month is M17 "
    "rather than M13, suggesting its project cycle or internal calendar differs from "
    "the other three departments. This is consistent with Dept3 being the most "
    "structurally distinct department overall."
))
add("")
add(_wrap(
    "The overall Z-score range across all departments stays within [−1.4, +1.4], "
    "meaning no month shows an extreme spike. Communication is sustained and relatively "
    "steady rather than episodic, which aligns with an academic/research environment "
    "where collaboration is ongoing rather than event-driven."
))

add("")
add("  Structural metric trends over time (active months):")
for dept in ["Dept1", "Dept2", "Dept3", "Dept4"]:
    d = active_tdf[active_tdf["Department"] == dept]
    dens_first = d[d["MonthIdx"] == d["MonthIdx"].min()]["Density"].values[0]
    dens_last  = d[d["MonthIdx"] == d["MonthIdx"].max()]["Density"].values[0]
    deg_mean   = d["AvgDegree"].mean()
    node_mean  = d["ActiveNodes"].mean()
    add(f"  {dept}: avg active nodes/month={node_mean:.0f}, avg degree/month={deg_mean:.2f}, "
        f"density M01={dens_first:.4f} → M{int(d['MonthIdx'].max()):02d}={dens_last:.4f}")

add("")
add(_wrap(
    "Active node counts per month are substantially lower than the departments' total "
    "headcounts in the static graph, confirming that not every employee is active in "
    "every month — participation is spread across the observation period, not concurrent."
))

# ---------- 8. Cross-department comparison summary ----------
add("")
add("8. CROSS-DEPARTMENT COMPARISON SUMMARY")
add("-" * 90)

rows = [
    ("Most employees",            master["Nodes"].idxmax(),                       f"{int(master['Nodes'].max())} nodes"),
    ("Fewest employees",          master["Nodes"].idxmin(),                       f"{int(master['Nodes'].min())} nodes"),
    ("Most emails (total)",       master["Total emails (weight sum)"].idxmax(),   f"{int(master['Total emails (weight sum)'].max()):,} emails"),
    ("Highest density",           master["Density"].idxmax(),                     f"{master['Density'].max():.4f}"),
    ("Lowest density",            master["Density"].idxmin(),                     f"{master['Density'].min():.4f}"),
    ("Best connected (WCC)",      "Dept3",                                         "1 WCC — 100% reachable"),
    ("Highest avg degree",        master["Avg degree (in+out)"].idxmax(),         f"{master['Avg degree (in+out)'].max():.2f}"),
    ("Most genuine modularity",   "Dept3",                                         "Q=0.43 within a single WCC"),
    ("Most fragmented",           master["Weakly conn. components"].idxmax(),     f"{int(master['Weakly conn. components'].max())} WCCs"),
    ("Shared peak month",         "All depts",                                     "M08 — institution-wide high activity"),
    ("Shared low month",          "All depts",                                     "M14 — likely vacation/semester break"),
    ("Smoothest temporal profile","Dept3",                                         "max Z ≈ 1.3; no extreme spikes"),
]

col_w = max(len(r[0]) for r in rows) + 2
for label, dept, note in rows:
    add(f"  {label:<{col_w}}  {dept}   ({note})")

# ---------- 9. Key findings ----------
add("")
add("9. KEY FINDINGS & INTERPRETATION")
add("-" * 90)

findings = [
    ("Dept3 is the most cohesive department.",
     "It is the only department where every employee is reachable from every other "
     "(single WCC), 88.8% belong to a mutual-reply SCC, it has the highest density "
     "(0.19) and average degree (33.84). Despite its smaller size (89 employees), "
     "it sustains a high-bandwidth, tightly-knit communication culture."),

    ("Dept1 is the most fragmented despite being the largest.",
     "With 309 employees, 9 disconnected WCCs, and 81 strong components, most of "
     "Dept1's email flow is one-directional or siloed. The largest WCC covers only "
     "32.7% of employees, pointing to isolated sub-teams with little cross-team "
     "communication."),

    ("Email volume does not scale with headcount.",
     "Dept2 (162 employees) and Dept4 (142 employees) both send over 46,000 emails — "
     "nearly as many as Dept1 (309 employees, 61,046 emails). This suggests smaller "
     "departments can have proportionally more intense communication, possibly driven "
     "by tighter collaboration or project-based work."),

    ("High modularity in Dept1, Dept2, Dept4 is largely structural.",
     "Their Q values (0.69–0.79) are inflated because isolated WCCs are treated as "
     "separate communities by default. These departments are not 'well-structured into "
     "sub-groups'; they are simply disconnected. Dept3's Q = 0.43 is the only one "
     "reflecting true within-network community formation."),

    ("Dept3's community structure warrants further study.",
     "Six communities within a single, nearly fully-bidirectionally connected department "
     "suggests distinct functional teams or project groups that still communicate with "
     "each other — a healthy balance of specialisation and cross-functional interaction."),

    ("M08 is an institution-wide communication peak.",
     "All four departments show a high-activity spike at month 8 (Z > 1.0 above their "
     "rolling baselines). The simultaneous cross-department surge strongly points to an "
     "external institution-level event — a project deadline, conference submission, or "
     "end-of-semester period — rather than any department-internal cause."),

    ("M14 is a synchronised low-activity period across all departments.",
     "Month 14 is the most pronounced shared dip: Dept4 drops to 562 emails (vs ~1,783 "
     "average), Dept2 to 1,024, Dept1 to 1,683, and Dept3 to 155. This near-zero "
     "activity in Dept3 and steep drops elsewhere are consistent with a summer or "
     "winter holiday break. M03 and M10 show milder reductions, likely mid-semester "
     "lulls."),

    ("Communication is sustained rather than episodic.",
     "The overall Z-score range across all departments is within [−1.4, +1.4] throughout "
     "the 18 active months. There are no extreme volume spikes — email usage is a steady "
     "background coordination channel, not a burst-driven medium. This is consistent with "
     "an academic/research work environment."),

    ("Dept3's temporal rhythm diverges from the other three.",
     "While Dept1, Dept2, and Dept4 all share M08 and M13 as their two highest months, "
     "Dept3's second peak falls at M17. Combined with its distinct structural profile "
     "(single WCC, highest density, genuine modularity), Dept3 appears to operate on a "
     "different internal schedule — possibly a different research cycle or funding period."),
]

for i, (headline, detail) in enumerate(findings, 1):
    add(f"\n  {i}. {headline}")
    add(_wrap(detail, indent=5))

# ---------- 10. Conclusion ----------
add("")
add("10. CONCLUSION")
add("-" * 90)
add(_wrap(
    "This analysis combines static network structure with temporal dynamics to give a "
    "multi-dimensional picture of intra-department email communication across four "
    "university departments over 27 months (~803 days)."
))
add("")
add(_wrap(
    "Structurally, Dept3 is the standout department: the only one with full weak "
    "connectivity, the highest density (0.19) and average degree (33.84), and the only "
    "genuinely modular community structure (Q = 0.43 within a single connected network). "
    "Dept1 is its structural opposite — the largest by headcount but the most fragmented, "
    "with 9 isolated sub-networks and 81 strong components, suggesting hierarchical or "
    "siloed communication flows. Dept2 and Dept4 sit between these extremes, with "
    "moderate density and significant disconnection."
))
add("")
add(_wrap(
    "Temporally, all four departments share a common rhythm: a coordinated peak at "
    "month 8, a shared low at month 14 (consistent with a holiday break), and milder "
    "dips at months 3 and 10. The synchrony of these patterns across independent "
    "departments confirms that institution-level events — academic calendars, submission "
    "deadlines, or breaks — are the primary driver of communication volume fluctuations, "
    "not department-specific factors. The absence of extreme spikes (max Z ≈ 1.3) "
    "confirms that email is used as a steady coordination channel rather than "
    "a crisis-response medium."
))
add("")
add(_wrap(
    "For organisational interventions: Dept3 provides a model of tight, reciprocal, "
    "well-structured communication and is the best reference for what healthy intra-"
    "department network topology looks like. Dept1 is the highest-priority candidate "
    "for bridging isolated sub-networks. The shared low at M14 and the broad peak at "
    "M08 could be leveraged as natural intervention windows — quieter periods for "
    "restructuring initiatives, and peak periods for knowledge-sharing events."
))
add("")
add("=" * 90)

# ── output ────────────────────────────────────────────────────────────────────
conclusion_text = "\n".join(lines)
print(conclusion_text)

out_path = OUT_DIR / "conclusion.txt"
out_path.write_text(conclusion_text, encoding="utf-8")
print(f"\nSaved analysis/conclusion.txt")
