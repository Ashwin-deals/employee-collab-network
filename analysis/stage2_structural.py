"""
Stage 2: Structural comparison table across the 4 department graphs.
Node count, edge count, density, average degree, weakly/strongly connected
components.
"""
import pickle
from pathlib import Path

import networkx as nx
import pandas as pd

OUT_DIR = Path(__file__).resolve().parent

with open(OUT_DIR / "graphs.pkl", "rb") as f:
    graphs = pickle.load(f)

rows = []
for dept, G in graphs.items():
    n = G.number_of_nodes()
    m = G.number_of_edges()
    density = nx.density(G)
    avg_degree = sum(dict(G.degree()).values()) / n  # total (in+out) degree avg
    wcc = nx.number_weakly_connected_components(G)
    scc = nx.number_strongly_connected_components(G)
    largest_wcc_frac = max(len(c) for c in nx.weakly_connected_components(G)) / n
    largest_scc_frac = max(len(c) for c in nx.strongly_connected_components(G)) / n
    total_weight = sum(w for _, _, w in G.edges(data="weight"))
    rows.append({
        "Department": dept,
        "Nodes": n,
        "Edges (directed)": m,
        "Total emails (weight sum)": total_weight,
        "Density": round(density, 4),
        "Avg degree (in+out)": round(avg_degree, 2),
        "Weakly conn. components": wcc,
        "Largest WCC (% nodes)": round(100 * largest_wcc_frac, 1),
        "Strongly conn. components": scc,
        "Largest SCC (% nodes)": round(100 * largest_scc_frac, 1),
    })

df = pd.DataFrame(rows).set_index("Department")
pd.set_option("display.width", 140)
print(df.to_string())

df.to_csv(OUT_DIR / "structural_comparison.csv")
print("\nSaved analysis/structural_comparison.csv")
