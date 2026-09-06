"""
Stage 1: Build a weighted directed graph for each department from its
temporal edge list (src dst timestamp). Each department file uses its own
local node numbering -> treated as 4 fully independent networks.

Edge weight = number of email events (temporal edges) collapsed onto that
ordered (src -> dst) pair.
"""
import gzip
import pickle
from pathlib import Path

import networkx as nx

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUT_DIR = Path(__file__).resolve().parent
DEPTS = ["Dept1", "Dept2", "Dept3", "Dept4"]

graphs = {}

for dept in DEPTS:
    fpath = DATA_DIR / f"email-Eu-core-temporal-{dept}.gz"
    G = nx.DiGraph()
    n_events = 0
    with gzip.open(fpath, "rt") as f:
        for line in f:
            parts = line.split()
            if not parts:
                continue
            src, dst, ts = int(parts[0]), int(parts[1]), int(parts[2])
            n_events += 1
            if G.has_edge(src, dst):
                G[src][dst]["weight"] += 1
            else:
                G.add_edge(src, dst, weight=1)
    graphs[dept] = G
    print(f"{dept}: {n_events} email events -> "
          f"{G.number_of_nodes()} nodes, {G.number_of_edges()} directed edges")

with open(OUT_DIR / "graphs.pkl", "wb") as f:
    pickle.dump(graphs, f)

print("\nSaved graphs to analysis/graphs.pkl")
