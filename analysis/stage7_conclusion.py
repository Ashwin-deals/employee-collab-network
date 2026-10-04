"""
Stage 7: Descriptive Conclusion
Reads all generated metrics and writes a human-readable analysis conclusion
to analysis/conclusion.txt (and prints it to stdout).

Run after stages 1-6 and 8-11 and 14 (it reads their CSV/PKL outputs).
Numbers quoted in the text are read from those outputs rather than typed
in, so the conclusion stays correct when an earlier stage changes.
"""
import ast
import pickle
import textwrap
from pathlib import Path

import pandas as pd

OUT_DIR = Path(__file__).resolve().parent
DEPTS = ["Dept1", "Dept2", "Dept3", "Dept4"]

master     = pd.read_csv(OUT_DIR / "cross_department_master.csv", index_col="Department")
cent_sum   = pd.read_csv(OUT_DIR / "centrality_summary.csv",      index_col="Department")
tdf        = pd.read_csv(OUT_DIR / "temporal_structural_evolution.csv")
bdf        = pd.read_csv(OUT_DIR / "temporal_bursts.csv")
low_weeks  = pd.read_csv(OUT_DIR / "low_weeks.csv")
offsets    = pd.read_csv(OUT_DIR / "clock_offsets.csv",           index_col="Department")
rhythm     = pd.read_csv(OUT_DIR / "rhythm_summary.csv", index_col=0)["Value"]
sync       = pd.read_csv(OUT_DIR / "temporal_synchrony.csv", index_col=0)["Value"]
with open(OUT_DIR / "centrality_tables.pkl", "rb") as f:
    centrality = pickle.load(f)
with open(OUT_DIR / "partitions.pkl", "rb") as f:
    partitions = pickle.load(f)["partitions"]

# ── helpers ──────────────────────────────────────────────────────────────────
def _rank(col, ascending=True):
    """Return departments ordered by col value, with the ranked value."""
    s = master[col].sort_values(ascending=ascending)
    return [(d, v) for d, v in s.items()]

def _wrap(text, indent=0):
    prefix = " " * indent
    return textwrap.fill(text, width=90, initial_indent=prefix,
                         subsequent_indent=prefix)

def _range(col, fmt="{:.2f}", depts=DEPTS):
    vals = master.loc[depts, col]
    return f"{fmt.format(vals.min())}–{fmt.format(vals.max())}"

fragmented = [d for d in DEPTS if master.loc[d, "Weakly conn. components"] > 1]
connected  = [d for d in DEPTS if d not in fragmented]

# temporal: complete months only
main_bdf  = bdf[bdf["InMainWindow"]]
main_tdf  = tdf[tdf["MonthIdx"].isin(main_bdf["MonthIdx"].unique())]
first_m, last_m = main_bdf["MonthIdx"].min(), main_bdf["MonthIdx"].max()
z_min, z_max = main_bdf["ZScore"].min(), main_bdf["ZScore"].max()
month_mean = main_tdf.groupby("Department")["EmailVolume"].mean()

def _months(dept, flag):
    return list(main_bdf[(main_bdf["Department"] == dept) & main_bdf[flag]]["Month"])

high = {d: _months(d, "IsBurst") for d in DEPTS}
low  = {d: _months(d, "IsQuiet") for d in DEPTS}
shared_high = sorted(set.intersection(*(set(v) for v in high.values())))
shared_low  = sorted(set.intersection(*(set(v) for v in low.values())))

main_end      = int(rhythm["MainWindowLastDay"])
resume_day    = int(float(rhythm["DataResumesDay"]))
clock_spread  = int(rhythm["DeptClockSpreadHours"])
weekend_pct   = float(rhythm["WeekendPctOfWeekday"])
peak_day      = int(rhythm["PeakWeekCentreDay"])
peak_month    = rhythm["PeakWeekMonth"]
peak_ratio    = float(rhythm["PeakWeekVsMedian"])
annual_pairs  = ast.literal_eval(rhythm["LowPeriodsAboutOneYearApart"])
longest_low   = low_weeks.loc[(low_weeks["EndDay"] - low_weeks["StartDay"]).idxmax()]

# ── build the conclusion ──────────────────────────────────────────────────────
lines = []
add = lines.append

add("=" * 90)
add("  SOCIAL NETWORK ANALYSIS — EMAIL-EU-CORE TEMPORAL DATASET")
add("  Descriptive Conclusion: Cross-Department Communication Patterns")
add("=" * 90)

# ---------- 1. Dataset & source ----------
add("")
add("1. DATASET & SOURCE")
add("-" * 90)
add(_wrap(
    "Source: the 'email-Eu-core-temporal' dataset from the Stanford Network Analysis "
    "Project (SNAP), introduced in A. Paranjape, A. R. Benson and J. Leskovec, 'Motifs in "
    "Temporal Networks', WSDM 2017. It records anonymised emails between members of a "
    "large European research institution. The four department files (Dept1–Dept4) each "
    "contain only emails sent between members of the same department; each line is one "
    "email: sender, recipient, and seconds since that file's first email."
))
add("")
add(_wrap(
    "Each department is treated as an independent directed weighted graph: nodes are "
    "employees, a directed edge u → v means u emailed v, and edge weight is the number of "
    "emails along that channel. Node IDs are local to each department and cannot be "
    "compared across them."
))
add("")
total_nodes  = master["Nodes"].sum()
total_emails = master["Total emails (weight sum)"].sum()
add(_wrap(
    f"Across all four departments the data covers {total_nodes} employees and "
    f"{total_emails:,} emails."
))
add("")
add(_wrap(
    "Time alignment: every department file starts its clock at its own first email, so "
    "the four clocks are offset from each other. Cross-correlating each department's hourly "
    "email counts against the full dataset shows the departments agree with each other to "
    f"within {clock_spread} hours. That is negligible at the day and month scales used "
    "below, so comparing departments month by month is valid."
))

# ---------- 2. Methods ----------
add("")
add("2. METHODS AND WHY THEY WERE CHOSEN")
add("-" * 90)
methods = [
    ("Weighted directed graphs",
     "email has a sender and a recipient, and repeated emails mean a stronger tie, so "
     "direction and weight are both kept."),
    ("Density and distinct contacts",
     "measure cohesion: how much of the possible communication actually happens, and how "
     "many different colleagues each person deals with."),
    ("Weakly / strongly connected components",
     "measure fragmentation (groups that never email each other at all) and directed "
     "reachability (whether information can flow round and back)."),
    ("Reciprocity",
     "measures two-way exchange directly: the share of ties u → v that are answered by "
     "v → u. Component size cannot show this, since a strong component only needs a "
     "directed cycle, not mutual replies."),
    ("Clustering coefficient",
     "measures whether a person's contacts also email each other, distinguishing tight "
     "closed teams from broad hub-and-spoke networks."),
    ("Degree, betweenness and PageRank centrality",
     "identify the most active people, the brokers who sit on paths between others "
     "(unweighted, because weights are counts, not distances), and the most influential "
     "people by weighted email flow."),
    ("Louvain community detection",
     "finds sub-teams by maximising modularity. Run on the undirected weighted projection, "
     "since modularity is defined for undirected graphs, with a fixed seed for "
     "reproducibility."),
    ("Monthly slices with rolling Z-scores",
     "find months that are unusually high or low relative to their neighbours (centred "
     "5-month window), so slow trends do not mask short swings."),
    ("Daily counts",
     "check the monthly view: 30-day bins with an arbitrary start can split or dilute "
     "week-long events."),
    ("Random baselines and permutation tests",
     "check that results are not what chance alone would produce: clustering is compared "
     "with degree-preserving random rewirings of each network, reciprocity with the "
     "density (its value in a random graph), and the shared high/low months with "
     "randomly shifted versions of each department's monthly series."),
]
for name, why in methods:
    add(_wrap(f"• {name}: {why}", indent=2))

# ---------- 3. Network size & email volume ----------
add("")
add("3. NETWORK SIZE & EMAIL VOLUME")
add("-" * 90)
per_channel = master["Total emails (weight sum)"] / master["Edges (directed)"]
per_person  = master["Total emails (weight sum)"] / master["Nodes"]
for dept in DEPTS:
    r = master.loc[dept]
    add(_wrap(
        f"  {dept}: {int(r['Nodes'])} employees, {int(r['Edges (directed)'])} directed edges, "
        f"{int(r['Total emails (weight sum)']):,} emails "
        f"({per_person[dept]:.0f} per person, {per_channel[dept]:.1f} per channel).",
        indent=2
    ))
add("")
largest = master["Nodes"].idxmax()
busiest = master["Total emails (weight sum)"].idxmax()
heavy   = per_channel.idxmax()
light   = per_channel.idxmin()
add(_wrap(
    f"{largest} is both the largest department ({int(master.loc[largest, 'Nodes'])} people) "
    f"and the busiest ({int(master.loc[busiest, 'Total emails (weight sum)']):,} emails), so "
    "total volume broadly follows headcount. Intensity is what differs: "
    f"{heavy} averages {per_channel[heavy]:.0f} emails per channel and "
    f"{per_person[heavy]:.0f} per person, while {light} averages only "
    f"{per_channel[light]:.0f} per channel. {heavy} concentrates its email in a few heavily "
    f"used channels; {light} spreads lighter traffic across many contacts."
))

# ---------- 4. Density & connectivity ----------
add("")
add("4. DENSITY & CONNECTIVITY")
add("-" * 90)
add(_wrap(
    "Density is the fraction of all possible directed edges that actually exist (0–1)."
))
add("")
for dept, v in _rank("Density", ascending=False):
    add(f"  {dept}: density = {v:.4f}")
add("")
densest  = master["Density"].idxmax()
sparsest = master["Density"].idxmin()
add(_wrap(
    f"{densest} has the highest density ({master.loc[densest, 'Density']:.4f}): about one in "
    f"{1 / master.loc[densest, 'Density']:.0f} possible email channels is used. {sparsest} is "
    f"the sparsest ({master.loc[sparsest, 'Density']:.4f}). Part of this is size, since "
    "possible edges grow with n² while each person's contacts do not, so density is best "
    "read together with connectivity below."
))
add("")
add("Weak connectivity (ignoring edge direction):")
for dept in DEPTS:
    r = master.loc[dept]
    wcc = int(r["Weakly conn. components"])
    if wcc == 1:
        desc = "fully connected (single component)"
    else:
        desc = f"{wcc} components; largest covers {r['Largest WCC (% nodes)']:.1f}% of employees"
    add(f"  {dept}: {desc}")
add("")
add(_wrap(
    f"{', '.join(connected)} is the only department where everyone is connected to everyone "
    "else, directly or indirectly. "
    f"{', '.join(fragmented)} each split into "
    f"{_range('Weakly conn. components', '{:.0f}', fragmented)} separate groups that never "
    "email each other within the department; the largest group covers only "
    f"{_range('Largest WCC (% nodes)', '{:.0f}', fragmented)}% of people."
))

# ---------- 5. Reachability & reciprocity ----------
add("")
add("5. DIRECTED REACHABILITY & RECIPROCITY")
add("-" * 90)
add(_wrap(
    "A strongly connected component (SCC) is a set of people who can all reach each other "
    "following the direction of email. Reciprocity is the share of ties that are answered."
))
add("")
for dept in DEPTS:
    r = master.loc[dept]
    add(f"  {dept}: {int(r['Strongly conn. components'])} SCCs "
        f"({int(r['Single-person SCCs'])} of them single people), largest = "
        f"{r['Largest SCC (% nodes)']:.1f}% of employees; reciprocity = {r['Reciprocity']:.2f}; "
        f"{int(r['Receive-only people'])} people only receive")
add("")
d1 = master.loc["Dept1"]
recip_ratio = master["Reciprocity"] / master["Reciprocity (random baseline)"]
add(_wrap(
    f"Reciprocity is high in every department ({_range('Reciprocity')}): most email "
    "relationships are two-way everywhere. In a random network with the same density, only "
    f"{_range('Reciprocity (random baseline)')} of ties would be answered, so reciprocity is "
    f"{recip_ratio.min():.0f}–{recip_ratio.max():.0f}× what chance would give. The many SCCs in "
    f"{', '.join(fragmented)} therefore do not mean email is mostly one-way. They come from "
    f"the fragmentation above plus peripheral members: in Dept1, "
    f"{int(d1['Single-person SCCs'])} of its {int(d1['Strongly conn. components'])} SCCs are "
    f"single people, and {int(d1['Receive-only people'])} people receive email from colleagues "
    "but never send any within the department (consistent with distribution lists, or with "
    "people whose work happens outside it). "
    f"{', '.join(connected)}'s large SCC ({master.loc[connected[0], 'Largest SCC (% nodes)']:.0f}%) "
    "follows from it being one connected group."
))

# ---------- 6. Breadth & clustering ----------
add("")
add("6. COMMUNICATION BREADTH & CLUSTERING")
add("-" * 90)
for dept in DEPTS:
    r = master.loc[dept]
    add(f"  {dept}: {r['Avg distinct contacts']:.1f} distinct contacts per person; "
        f"avg clustering = {r['Avg clustering']:.2f} "
        f"(random baseline {r['Clustering (random baseline)']:.2f}, "
        f"{r['Clustering vs random (x)']:.1f}× random)")
add("")
top_contacts = master["Avg distinct contacts"].idxmax()
cliquey = master["Avg clustering"].sort_values(ascending=False).index[:2].tolist()
least_cliquey = master["Avg clustering"].idxmin()
add(_wrap(
    f"{top_contacts} people each deal with about {master.loc[top_contacts, 'Avg distinct contacts']:.0f} "
    "different colleagues, against roughly "
    f"{master.drop(top_contacts)['Avg distinct contacts'].mean():.0f} elsewhere. Yet "
    f"{least_cliquey} has the lowest clustering ({master.loc[least_cliquey, 'Avg clustering']:.2f}): "
    "its contacts span the whole department, so many of a person's contacts do not email each "
    f"other. {' and '.join(cliquey)} have the highest clustering "
    f"({_range('Avg clustering', depts=cliquey)}): their groups are tight teams where nearly "
    "everyone emails everyone, but the teams are cut off from each other."
))
add("")
add(_wrap(
    "The random baselines confirm this. In "
    f"{', '.join(fragmented)} clustering is "
    f"{_range('Clustering vs random (x)', '{:.1f}', fragmented)}× what randomly rewired networks "
    "with the same contact counts produce, so their tight teams are real structure. In "
    f"{', '.join(connected)} it is only "
    f"{master.loc[connected[0], 'Clustering vs random (x)']:.2f}× random: its clustering is "
    "almost entirely explained by its high density, with little extra closed-team structure."
))

# ---------- 7. Community structure ----------
add("")
add("7. COMMUNITY STRUCTURE — LOUVAIN MODULARITY")
add("-" * 90)
add(_wrap(
    "Modularity Q measures how strongly a network divides into communities; values above "
    "about 0.3 are commonly taken to indicate meaningful community structure "
    "(Newman & Girvan, 2004)."
))
add("")
for dept in DEPTS:
    r = master.loc[dept]
    add(f"  {dept}: {int(r['Num sub-communities'])} communities, Q = {r['Modularity (Q)']:.4f}, "
        f"largest = {r['Largest community (% nodes)']:.1f}% of employees, "
        f"{r['Nodes with cross-community ties (%)']:.0f}% of people have ties to another community")
add("")
add(_wrap(
    f"Interpretive caveat: {', '.join(fragmented)} are split into disconnected components, and "
    "Louvain assigns each component to its own community at no cost, so their high Q "
    f"({_range('Modularity (Q)', depts=fragmented)}) mostly reflects that disconnection. Their "
    f"communities-per-component ratios ({_range('Communities per WCC', depts=fragmented)}) "
    "confirm that almost every community is simply one component; in Dept4 the match is "
    f"exact, with {master.loc['Dept4', 'Nodes with cross-community ties (%)']:.0f}% of people "
    "tied to another community."
))
add("")
c = master.loc[connected[0]]
add(_wrap(
    f"{connected[0]} is the analytically meaningful case: one connected network in which Louvain "
    f"still finds {int(c['Num sub-communities'])} communities with Q = {c['Modularity (Q)']:.2f}, "
    f"above the 0.3 rule of thumb. {c['Nodes with cross-community ties (%)']:.0f}% of its people "
    "have ties into another community, so these are distinct sub-teams that stay in contact "
    "with each other."
))

# ---------- 8. Centrality ----------
add("")
add("8. KEY PEOPLE — CENTRALITY")
add("-" * 90)
add(_wrap(
    "PageRank (weighted) ranks influence through email flow; betweenness ranks brokers on "
    "the shortest paths between others; degree counts distinct ties. Node IDs are local, so "
    "only patterns, not people, are compared across departments."
))
add("")
for dept in DEPTS:
    r = cent_sum.loc[dept]
    add(f"  {dept}: top PageRank = node {int(r['Top PageRank node'])}, "
        f"top betweenness = node {int(r['Top betweenness node'])} ({r['Max betweenness']:.3f}); "
        f"top 5 hold {100 * r['Top-5 share of betweenness']:.0f}% of betweenness, "
        f"{100 * r['Top-5 share of email volume']:.0f}% of email volume; "
        f"{r['Zero-betweenness nodes (%)']:.0f}% are never on a shortest path")
add("")

def _pr_lead(dept):
    pr = centrality[dept]["pagerank"].sort_values(ascending=False)
    return pr.index[0], pr.iloc[0], pr.iloc[0] / pr.iloc[1], pr.iloc[0] / pr.iloc[4]

hub, hub_pr, hub_lead, _ = _pr_lead("Dept1")
top5_btw = centrality["Dept1"]["betweenness"].sort_values(ascending=False).head(5).index
d1_comms = {partitions["Dept1"][n] for n in top5_btw}
d1_sizes = pd.Series(partitions["Dept1"]).value_counts()
add(_wrap(
    f"Dept1 has one dominant hub: node {hub} is first on degree, betweenness and PageRank, "
    f"with a PageRank {hub_lead:.1f}× the next person's. "
    + (f"All five top brokers sit in the department's largest community "
       f"({d1_sizes.iloc[0]} people), so brokerage happens inside that group, not between "
       "groups. " if d1_comms == {d1_sizes.index[0]} else "")
    + "This is a single point of failure for Dept1's main group."
))
add("")
d2_all = ast.literal_eval(cent_sum.loc["Dept2", "In top-5 of degree, betweenness and PageRank"])
d2_top = int(cent_sum.loc["Dept2", "Top PageRank node"])
add(_wrap(
    f"Dept2 is led by a small core: nodes {', '.join(map(str, d2_all))} are in the top five "
    f"on all three measures, and node {d2_top} handles "
    f"{int(centrality['Dept2'].loc[d2_top, 'weighted_degree']):,} emails sent and received, "
    "the most in the department."
))
add("")
d3_max = cent_sum.loc["Dept3", "Max betweenness"]
others_max = cent_sum.drop("Dept3")["Max betweenness"].max()
d3_all = ast.literal_eval(cent_sum.loc["Dept3", "In top-5 of degree, betweenness and PageRank"])
add(_wrap(
    f"Dept3 has real brokers: its top betweenness ({d3_max:.3f}) is {d3_max / others_max:.0f}× "
    f"the highest anywhere else, and nodes {', '.join(map(str, d3_all))} rank top five on all "
    "three measures. These are the people connecting its sub-teams. Only "
    f"{cent_sum.loc['Dept3', 'Zero-betweenness nodes (%)']:.0f}% of Dept3 is never on a "
    "shortest path, versus "
    f"{cent_sum.drop('Dept3')['Zero-betweenness nodes (%)'].min():.0f}–"
    f"{cent_sum.drop('Dept3')['Zero-betweenness nodes (%)'].max():.0f}% elsewhere, so most "
    "people take some part in passing information on."
))
add("")
_, d4_pr, d4_lead, d4_lead5 = _pr_lead("Dept4")
add(_wrap(
    f"Dept4 has no single leader: its top five PageRank scores are nearly equal (the first is "
    f"only {d4_lead5:.1f}× the fifth), matching a set of self-contained teams of similar weight."
))
add("")
add(_wrap(
    "Caveat: betweenness is normalised over all pairs of people, and no shortest paths cross "
    f"between disconnected groups, so {', '.join(fragmented)} score lower partly by "
    "construction. The comparison of shares and patterns above is more reliable than the "
    "raw values."
))

# ---------- 9. Temporal analysis ----------
add("")
add("9. TEMPORAL ANALYSIS")
add("-" * 90)
add(_wrap(
    f"The data is continuous from day 0 to day {main_end}, then has no email at all until day "
    f"{resume_day}, after which only 7 more days are recorded. Events were split into "
    "30-day slices (M01, M02, …). Only complete months are analysed "
    f"(M{first_m:02d}–M{last_m:02d}): the slice the data stops in (M{last_m + 1:02d}) and the "
    "7-day fragment at the end are partial, and their low counts reflect missing days, not "
    "quiet periods."
))
add("")
add("  Monthly email volume (complete months):")
for dept in DEPTS:
    d = main_tdf[main_tdf["Department"] == dept]["EmailVolume"]
    add(f"  {dept}: mean={d.mean():.0f}, std={d.std():.0f}, "
        f"min={int(d.min())}, max={int(d.max())} emails/month")
add("")
add("  High / low months (Z-score beyond ±1.0 against a centred 5-month rolling mean):")
for dept in DEPTS:
    add(f"  {dept}: high → {high[dept]}   low → {low[dept]}")
add("")
near_miss = main_bdf[(main_bdf["Month"] == "M13") & ~main_bdf["IsBurst"]]
add(_wrap(
    f"All four departments rise and fall together: {', '.join(shared_high)} is high in every "
    f"department and {', '.join(shared_low)} are low in every department. "
    + (f"M13 is high in three departments; in {near_miss.iloc[0]['Department']} it scores "
       f"Z = {near_miss.iloc[0]['ZScore']:.3f}, just under the cut-off. "
       if len(near_miss) == 1 else "")
    + "Since the departments are separate networks, this shared rhythm points to "
    "institution-wide causes such as calendars, deadlines and holidays."
))
add("")
m14 = main_tdf[main_tdf["Month"] == "M14"].set_index("Department")["EmailVolume"]
add(_wrap(
    f"This synchrony is statistically significant. The ±1 cut-off flags "
    f"{100 * float(sync['ShareOfMonthsFlagged']):.0f}% of department-months, so any single "
    "department's flags could be chance. But "
    f"{int(float(sync['SharedFlaggedMonthsObserved']))} months are flagged the same way in all four "
    "departments, against "
    f"{float(sync['SharedFlaggedMonthsExpected']):.2f} expected when each department's series is "
    f"shifted at random (p = {float(sync['PValue']):.4f}, "
    f"{int(float(sync['Permutations'])):,} permutations)."
))
add("")
add(_wrap(
    "In M14 every department drops sharply: "
    + ", ".join(f"{d} falls to {int(m14[d]):,} emails ({100 * m14[d] / month_mean[d]:.0f}% of its "
                f"monthly average)" for d in DEPTS)
    + "."
))
add("")
add(_wrap(
    f"Monthly Z-scores stay between {z_min:.2f} and +{z_max:.2f}: month to month, volume moves "
    "within a moderate band. The large swings are week-scale, as the daily view shows."
))

add("")
add("  Daily rhythm:")
add(_wrap(
    f"Weekend days carry only {weekend_pct:.0f}% of a weekday's email, confirming this is "
    "work communication. The weekly view reveals what monthly bins blur:", indent=2
))
add(_wrap(
    f"• {peak_month}'s peak is one intense week: the 7 days around day {peak_day} carry "
    f"{peak_ratio:.1f}× a median week's email.", indent=4
))
flagged_low = set().union(*low.values())
missed = sorted({m for r in low_weeks.itertuples() for m in ast.literal_eval(r.Months)
                 if len(ast.literal_eval(r.Months)) == 1} - flagged_low)
low_desc = "; ".join(f"days {int(r.StartDay)}–{int(r.EndDay)} ({'/'.join(ast.literal_eval(r.Months))}, "
                     f"{r.PctOfTypicalDay:.0f}% of normal)" for r in low_weeks.itertuples())
add(_wrap(f"• Low periods (below half the median week): {low_desc}.", indent=4))
add(_wrap(
    f"• The longest break lasts {int(longest_low.EndDay - longest_low.StartDay + 1)} days and "
    f"straddles {' and '.join(ast.literal_eval(longest_low.Months))}, so monthly bins split it."
    + (f" The low period{'s' if len(missed) > 1 else ''} in {', '.join(missed)} "
       f"{'do' if len(missed) > 1 else 'does'} not show up in the monthly analysis at all."
       if missed else ""), indent=4
))
if annual_pairs:
    a, b = annual_pairs[0]
    add(_wrap(
        f"• Breaks starting on days {a} and {b} are {b - a} days apart, which suggests a "
        "recurring annual holiday. The actual calendar dates cannot be recovered, because "
        "timestamps are relative.", indent=4
    ))

add("")
add("  Structural metrics over time (complete months):")
for dept in DEPTS:
    d = main_tdf[main_tdf["Department"] == dept]
    first = d[d["MonthIdx"] == first_m].iloc[0]
    last = d[d["MonthIdx"] == last_m].iloc[0]
    add(f"  {dept}: avg active people/month={d['ActiveNodes'].mean():.0f} "
        f"(of {int(master.loc[dept, 'Nodes'])}), avg degree/month={d['AvgDegree'].mean():.2f}, "
        f"density M{first_m:02d}={first['Density']:.4f} → M{last_m:02d}={last['Density']:.4f}")
add("")
add(_wrap(
    "In any given month only part of each department is active, so the static networks above "
    "combine people whose activity is spread across the whole period."
))

# ---------- 10. Summary table ----------
add("")
add("10. CROSS-DEPARTMENT COMPARISON SUMMARY")
add("-" * 90)
pr_leads = {d: _pr_lead(d) for d in DEPTS}
hub_dept = max(pr_leads, key=lambda d: pr_leads[d][2])
hub_node, _, hub_ratio, _ = pr_leads[hub_dept]
rows = [
    ("Most employees",              master["Nodes"].idxmax(),                     f"{int(master['Nodes'].max())} people"),
    ("Fewest employees",            master["Nodes"].idxmin(),                     f"{int(master['Nodes'].min())} people"),
    ("Most emails (total)",         master["Total emails (weight sum)"].idxmax(), f"{int(master['Total emails (weight sum)'].max()):,} emails"),
    ("Most emails per channel",     per_channel.idxmax(),                         f"{per_channel.max():.1f}"),
    ("Highest density",             master["Density"].idxmax(),                   f"{master['Density'].max():.4f}"),
    ("Most distinct contacts",      master["Avg distinct contacts"].idxmax(),     f"{master['Avg distinct contacts'].max():.1f} per person"),
    ("Highest reciprocity",         master["Reciprocity"].idxmax(),               f"{master['Reciprocity'].max():.2f}"),
    ("Highest clustering",          master["Avg clustering"].idxmax(),            f"{master['Avg clustering'].max():.2f}"),
    ("Fully connected",             ", ".join(connected),                         "1 component"),
    ("Most fragmented",             master["Weakly conn. components"].idxmax(),   f"{int(master['Weakly conn. components'].max())} components"),
    ("Meaningful modularity",       ", ".join(connected),                         f"Q={master.loc[connected[0], 'Modularity (Q)']:.2f} in one connected network"),
    ("Most dominant hub",           hub_dept,                                     f"node {hub_node}, PageRank {hub_ratio:.1f}× the next"),
    ("Strongest broker",            cent_sum["Max betweenness"].idxmax(),         f"max betweenness {cent_sum['Max betweenness'].max():.3f}"),
    ("Shared high month",           "All depts",                                  ", ".join(shared_high)),
    ("Shared low months",           "All depts",                                  ", ".join(shared_low)),
]
col_w = max(len(r[0]) for r in rows) + 2
for label, dept, note in rows:
    add(f"  {label:<{col_w}}  {dept}   ({note})")

# ---------- 11. Key findings ----------
add("")
add("11. KEY FINDINGS & INTERPRETATION")
add("-" * 90)
low_len = low_weeks["EndDay"] - low_weeks["StartDay"] + 1
findings = [
    ("Dept3 is the most cohesive department, organised around brokers rather than cliques.",
     f"It is the only fully connected department, with the highest density "
     f"({master.loc['Dept3', 'Density']:.2f}) and the most contacts per person "
     f"({master.loc['Dept3', 'Avg distinct contacts']:.0f}). Its low clustering and strong "
     "brokers show a broad network held together by a few well-connected people, with "
     f"{int(master.loc['Dept3', 'Num sub-communities'])} sub-teams that stay in contact."),

    ("Dept1, Dept2 and Dept4 are collections of separate tight teams.",
     f"Each splits into {_range('Weakly conn. components', '{:.0f}', fragmented)} groups that "
     "never email each other within the department. Inside those groups, clustering is "
     f"{_range('Clustering vs random (x)', '{:.1f}', fragmented)}× what random networks give: "
     "genuinely close-knit teams with little contact between them."),

    ("Two-way communication is the norm everywhere.",
     f"Reciprocity is {_range('Reciprocity')} in all four departments, "
     f"{recip_ratio.min():.0f}–{recip_ratio.max():.0f}× chance. Dept1's many strong "
     "components come from fragmentation and receive-only members, not from one-way email."),

    ("Departments differ in communication intensity.",
     f"{heavy} sends {per_channel[heavy]:.0f} emails per channel against {light}'s "
     f"{per_channel[light]:.0f}: a few heavy channels versus many light ones."),

    ("High modularity in Dept1, Dept2 and Dept4 is largely an artefact.",
     f"Their Q values ({_range('Modularity (Q)', depts=fragmented)}) mostly count already-"
     "disconnected components as communities. Dept3's lower Q is the only one reflecting "
     "community structure inside one connected network."),

    ("Influence is concentrated differently in each department.",
     f"Dept1 depends on one hub (node {hub}); Dept2 on a core of {len(d2_all)} people; Dept3 on a few "
     "brokers between sub-teams; Dept4 has no single leader."),

    ("All departments follow the same institutional calendar.",
     f"{', '.join(shared_high)} is high and {', '.join(shared_low)} are low in every department. "
     f"The department clocks agree to within {clock_spread} hours, and a permutation test puts "
     f"the chance of this much overlap at p = {float(sync['PValue']):.4f}."),

    ("The real swings are week-long.",
     f"The {peak_month} peak is a single week at {peak_ratio:.1f}× normal, and the dips are "
     f"breaks of {low_len.min()}–{low_len.max()} days where email drops to "
     f"{low_weeks['PctOfTypicalDay'].min():.0f}–{low_weeks['PctOfTypicalDay'].max():.0f}% of normal"
     + (", including one that recurs about a year later" if annual_pairs else "")
     + f". Weekends carry only {weekend_pct:.0f}% of a weekday's email."),
]
for i, (headline, detail) in enumerate(findings, 1):
    add(f"\n  {i}. {headline}")
    add(_wrap(detail, indent=5))

# ---------- 12. Limitations & future work ----------
add("")
add("12. LIMITATIONS & FUTURE WORK")
add("-" * 90)
limitations = [
    "Only email within each department is included, so links between departments are "
    "invisible. Groups that look isolated may be connected through other departments.",
    "Email is a proxy for collaboration. Volume may include distribution-list or automated "
    "messages, and without message content these cannot be separated out.",
    "The data is anonymised, with no roles or org chart, so communities and hubs cannot be "
    "checked against real teams or positions.",
    "Timestamps are relative, so calendar dates (and the cause of each peak or break) are "
    "unknown. The 30-day bins are arbitrary, and the data has a long gap after day "
    f"{main_end}.",
    "Betweenness is not directly comparable between connected and fragmented networks. "
    "Louvain is randomised; across 20 seeds Q varies by at most "
    f"{(master['Q max over 20 seeds'] - master['Q min over 20 seeds']).max():.3f} and the "
    "number of communities by at most "
    f"{int((master['Communities max over 20 seeds'] - master['Communities min over 20 seeds']).max())}, "
    "so the conclusions do not depend on the seed.",
]
for item in limitations:
    add(_wrap(f"• {item}", indent=2))
add("")
future = [
    "Analyse the full dataset to see how departments connect to each other.",
    "Study temporal motifs (recurring patterns of who emails whom in sequence), the purpose "
    "the dataset was published for.",
    "Track communities month by month to see whether teams merge, split or persist, and "
    "test how well past contact predicts future links.",
]
add("  Future work:")
for item in future:
    add(_wrap(f"• {item}", indent=2))

# ---------- 13. Conclusion ----------
add("")
add("13. CONCLUSION")
add("-" * 90)
add(_wrap(
    "This analysis combines static network structure, centrality, community detection and "
    "temporal dynamics to compare email communication in four departments of a European "
    f"research institution over {main_end + 1} days of continuous data."
))
add("")
add(_wrap(
    "Structurally, the departments follow two different models. Dept3 is one connected, "
    "broad network held together by a few brokers, with sub-teams that stay in contact. "
    "Dept1, Dept2 and Dept4 are each made up of several close-knit teams that never email "
    "each other within the department; their high modularity reflects that separation "
    "rather than well-formed sub-groups. Communication is reciprocal in all four, so the "
    "difference lies in how the teams connect, not in whether people reply."
))
add("")
add(_wrap(
    "Temporally, all four departments share one rhythm: the same high and low months, a "
    "single surge week, multi-week breaks (one recurring about a year later) and quiet "
    "weekends. Communication volume is driven by institution-wide schedules more than by "
    "anything department-specific."
))
add("")
add(_wrap(
    "Implications for the organisation: Dept1's isolated teams are the clearest candidates for "
    f"deliberate bridging, and its reliance on node {hub} is a continuity risk. Dept3 shows "
    "what a well-connected department looks like, but it too depends on a handful of brokers. "
    "The shared break periods are natural windows for planned changes, and the surge week "
    "shows when the whole institution is under the most communication load."
))
add("")
add("=" * 90)

# ── output ────────────────────────────────────────────────────────────────────
conclusion_text = "\n".join(lines)
print(conclusion_text)

out_path = OUT_DIR / "conclusion.txt"
out_path.write_text(conclusion_text, encoding="utf-8")
print(f"\nSaved analysis/conclusion.txt")
