"""
Stage 3: Within-department centrality (degree, betweenness, PageRank).
Identify top 3-5 most central people per department for each measure.

Also summarises how concentrated centrality is in each department (share
held by the top 5 people). Shares are comparable across departments even
though node identities are not. Betweenness is normalised over all node
pairs, so departments split into disconnected components score lower
mechanically: no shortest paths cross between components.
"""
import pickle
from pathlib import Path

import networkx as nx
import pandas as pd

OUT_DIR = Path(__file__).resolve().parent

with open(OUT_DIR / "graphs.pkl", "rb") as f:
    graphs = pickle.load(f)

TOP_N = 5
all_tables = {}
summary_rows = []

for dept, G in graphs.items():
    deg = dict(G.degree(weight=None))          # total in+out degree (# distinct contacts)
    wdeg = dict(G.degree(weight="weight"))      # weighted degree (# emails)
    btw = nx.betweenness_centrality(G, weight=None, normalized=True)  # topology-based (unweighted)
    pr = nx.pagerank(G, weight="weight")

    df = pd.DataFrame({
        "degree": deg,
        "weighted_degree": wdeg,
        "betweenness": btw,
        "pagerank": pr,
    })
    df.index.name = "node"
    all_tables[dept] = df

    print(f"\n=== {dept} ===")
    print(f"-- Top {TOP_N} by degree --")
    print(df["degree"].sort_values(ascending=False).head(TOP_N).to_string())
    print(f"-- Top {TOP_N} by betweenness --")
    print(df["betweenness"].sort_values(ascending=False).head(TOP_N).to_string())
    print(f"-- Top {TOP_N} by PageRank --")
    print(df["pagerank"].sort_values(ascending=False).head(TOP_N).to_string())

    df.sort_values("pagerank", ascending=False).to_csv(OUT_DIR / f"centrality_{dept}.csv")

    top = {col: df[col].sort_values(ascending=False).head(TOP_N) for col in
           ["degree", "weighted_degree", "betweenness", "pagerank"]}
    in_all_three = (set(top["degree"].index) & set(top["betweenness"].index)
                    & set(top["pagerank"].index))
    summary_rows.append({
        "Department": dept,
        "Top PageRank node": top["pagerank"].index[0],
        "Top betweenness node": top["betweenness"].index[0],
        "Max betweenness": round(top["betweenness"].iloc[0], 4),
        f"Top-{TOP_N} share of betweenness": round(top["betweenness"].sum() / df["betweenness"].sum(), 3),
        f"Top-{TOP_N} share of PageRank": round(top["pagerank"].sum() / df["pagerank"].sum(), 3),
        f"Top-{TOP_N} share of email volume": round(top["weighted_degree"].sum() / df["weighted_degree"].sum(), 3),
        "Zero-betweenness nodes (%)": round(100 * (df["betweenness"] == 0).mean(), 1),
        f"In top-{TOP_N} of degree, betweenness and PageRank": sorted(in_all_three),
    })

print("\nSaved per-department centrality CSVs (analysis/centrality_DeptN.csv)")

summary = pd.DataFrame(summary_rows).set_index("Department")
pd.set_option("display.width", 200)
print("\n--- Centrality concentration ---")
print(summary.to_string())
summary.to_csv(OUT_DIR / "centrality_summary.csv")
print("Saved analysis/centrality_summary.csv")

with open(OUT_DIR / "centrality_tables.pkl", "wb") as f:
    pickle.dump(all_tables, f)
