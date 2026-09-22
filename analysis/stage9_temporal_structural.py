"""
Stage 9: Temporal Structural Evolution
For every monthly slice compute key structural metrics and write them to a
long-format CSV suitable for time-series plotting.

Reads:   temporal_slices.pkl
Outputs: temporal_structural_evolution.csv
         columns: Department, Month, MonthIdx, ActiveNodes, Edges,
                  EmailVolume, Density, AvgDegree, LargestWCC_pct
"""
import pickle
from pathlib import Path

import networkx as nx
import pandas as pd

OUT_DIR = Path(__file__).resolve().parent

with open(OUT_DIR / "temporal_slices.pkl", "rb") as f:
    slices = pickle.load(f)

rows = []

for dept, data in slices.items():
    graphs       = data["graphs"]
    event_counts = data["event_counts"]
    month_labels = data["month_labels"]

    for idx, (G, vol, label) in enumerate(zip(graphs, event_counts, month_labels)):
        n = G.number_of_nodes()
        e = G.number_of_edges()

        if n > 1 and e > 0:
            density   = nx.density(G)
            avg_deg   = sum(d for _, d in G.degree()) / n
            wccs      = list(nx.weakly_connected_components(G))
            wcc_pct   = 100.0 * max(len(c) for c in wccs) / n
        else:
            density = avg_deg = wcc_pct = 0.0

        rows.append({
            "Department":    dept,
            "Month":         label,
            "MonthIdx":      idx + 1,
            "ActiveNodes":   n,
            "Edges":         e,
            "EmailVolume":   vol,
            "Density":       round(density, 6),
            "AvgDegree":     round(avg_deg, 4),
            "LargestWCC_pct": round(wcc_pct, 2),
        })

df = pd.DataFrame(rows)
df.to_csv(OUT_DIR / "temporal_structural_evolution.csv", index=False)

print(df.groupby("Department")[["EmailVolume", "ActiveNodes", "Density"]].describe().round(4))
print("\nSaved analysis/temporal_structural_evolution.csv")
