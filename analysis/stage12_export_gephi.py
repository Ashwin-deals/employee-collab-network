"""
Stage 12: Export each department graph as a Gephi-ready GEXF file.

The raw edge lists (src dst timestamp, space-separated, no header) do not
import cleanly into Gephi: its CSV importer reads each line as an adjacency
list, so every timestamp becomes a bogus node, and one edge per email event
renders as a solid block. This stage writes the aggregated weighted graphs
instead (one edge per ordered pair, weight = email count), with node
attributes for Louvain community and centrality, plus a precomputed layout,
community colour and PageRank-based size so the file opens already readable.
"""
import pickle
from pathlib import Path

import matplotlib
import networkx as nx

OUT_DIR = Path(__file__).resolve().parent
GEPHI_DIR = OUT_DIR / "gephi"
GEPHI_DIR.mkdir(exist_ok=True)

SEED = 42
LAYOUT_SCALE = 1000          # Gephi coordinates are in screen-ish units
MIN_SIZE, MAX_SIZE = 4, 40   # node size range, scaled by PageRank

with open(OUT_DIR / "graphs.pkl", "rb") as f:
    graphs = pickle.load(f)
with open(OUT_DIR / "partitions.pkl", "rb") as f:
    partitions = pickle.load(f)["partitions"]
with open(OUT_DIR / "centrality_tables.pkl", "rb") as f:
    centrality = pickle.load(f)

cmap = matplotlib.colormaps["tab20"]

for dept, G in graphs.items():
    part = partitions[dept]
    cent = centrality[dept]
    pr_min, pr_max = cent["pagerank"].min(), cent["pagerank"].max()

    # Layout on the unweighted undirected projection: email counts are very
    # skewed and would collapse heavy pairs onto one point.
    UG = G.to_undirected()
    pos = nx.spring_layout(UG, weight=None, seed=SEED, scale=LAYOUT_SCALE,
                           k=2 / (UG.number_of_nodes() ** 0.5))

    H = nx.DiGraph()
    for node in G.nodes():
        row = cent.loc[node]
        pr = float(row["pagerank"])
        r, g, b, _ = cmap(part[node] % cmap.N)
        size = MIN_SIZE + (MAX_SIZE - MIN_SIZE) * (pr - pr_min) / (pr_max - pr_min)
        H.add_node(
            node,
            label=str(node),
            community=int(part[node]),
            degree=int(row["degree"]),
            weighted_degree=int(row["weighted_degree"]),
            betweenness=float(row["betweenness"]),
            pagerank=pr,
            viz={
                "position": {"x": float(pos[node][0]), "y": float(pos[node][1]), "z": 0.0},
                "size": float(size),
                "color": {"r": int(r * 255), "g": int(g * 255), "b": int(b * 255), "a": 1.0},
            },
        )
    for u, v, w in G.edges(data="weight"):
        H.add_edge(u, v, weight=int(w))

    out = GEPHI_DIR / f"{dept}.gexf"
    nx.write_gexf(H, out)
    print(f"{dept}: {H.number_of_nodes()} nodes, {H.number_of_edges()} edges -> {out.relative_to(OUT_DIR.parent)}")

print("\nOpen in Gephi via File > Open (not Import Spreadsheet).")

# Also write plain Source,Target,Weight edge tables for Gephi's Import
# Spreadsheet, straight from the raw files (including the full dataset,
# which is not part of graphs.pkl).
DATA_DIR = OUT_DIR.parent / "data" / "email-Eu-core-temporal"
for name in ["Dept1", "Dept2", "Dept3", "Dept4", None]:
    stem = f"email-Eu-core-temporal-{name}" if name else "email-Eu-core-temporal"
    weights = {}
    with open(DATA_DIR / f"{stem}.csv") as f:
        for line in f:
            parts = line.split()
            if parts:
                pair = (int(parts[0]), int(parts[1]))
                weights[pair] = weights.get(pair, 0) + 1

    out = GEPHI_DIR / f"{name or 'Full'}_edges.csv"
    with open(out, "w") as f:
        f.write("Source,Target,Weight,Type\n")
        for (src, dst), w in sorted(weights.items()):
            f.write(f"{src},{dst},{w},Directed\n")
    print(f"{name or 'Full'}: {len(weights)} weighted edges -> {out.relative_to(OUT_DIR.parent)}")
