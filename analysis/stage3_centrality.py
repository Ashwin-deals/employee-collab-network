"""
Stage 3: Within-department centrality (degree, betweenness, PageRank).
Identify top 3-5 most central people per department for each measure.
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

print("\nSaved per-department centrality CSVs (analysis/centrality_DeptN.csv)")

with open(OUT_DIR / "centrality_tables.pkl", "wb") as f:
    pickle.dump(all_tables, f)
