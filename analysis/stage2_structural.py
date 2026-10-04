"""
Stage 2: Structural comparison table across the 4 department graphs.
Node count, edge count, density, average degree, weakly/strongly connected
components, reciprocity and clustering.

Reciprocity (share of directed edges u->v whose reverse v->u also exists)
measures two-way exchange directly; SCC size does not, since an SCC only
needs a directed cycle, not mutual replies. Clustering is computed on the
undirected, unweighted projection (do my contacts email each other?).

Null models: clustering is compared with degree-preserving random rewirings
of the same undirected graph (everyone keeps their number of contacts, but
who they are is randomised), so a high value can be read as real team
structure rather than a side effect of density. The baseline for
reciprocity is the density: in a random directed graph with that density,
the chance a tie is answered equals the density.
"""
import pickle
from pathlib import Path

import networkx as nx
import pandas as pd

OUT_DIR = Path(__file__).resolve().parent
N_RANDOM = 10   # random rewirings per department for the clustering baseline
SEED = 42


def random_clustering(UG, runs=N_RANDOM, seed=SEED):
    """Mean clustering over degree-preserving rewirings of UG."""
    values = []
    for r in range(runs):
        R = nx.Graph(UG)
        nx.double_edge_swap(R, nswap=4 * R.number_of_edges(), max_tries=10**6, seed=seed + r)
        values.append(nx.average_clustering(R))
    return sum(values) / len(values)

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
    UG = nx.Graph(G.to_undirected())
    clustering = nx.average_clustering(UG)
    clustering_random = random_clustering(UG)
    avg_contacts = 2 * UG.number_of_edges() / n   # distinct people emailed or emailed by
    rows.append({
        "Department": dept,
        "Nodes": n,
        "Edges (directed)": m,
        "Total emails (weight sum)": total_weight,
        "Density": round(density, 4),
        "Avg degree (in+out)": round(avg_degree, 2),
        "Avg distinct contacts": round(avg_contacts, 2),
        "Weakly conn. components": wcc,
        "Largest WCC (% nodes)": round(100 * largest_wcc_frac, 1),
        "Strongly conn. components": scc,
        "Largest SCC (% nodes)": round(100 * largest_scc_frac, 1),
        "Single-person SCCs": sum(1 for c in nx.strongly_connected_components(G) if len(c) == 1),
        "Receive-only people": sum(1 for v in G if G.out_degree(v) == 0),
        "Send-only people": sum(1 for v in G if G.in_degree(v) == 0),
        "Reciprocity": round(nx.reciprocity(G), 4),
        "Reciprocity (random baseline)": round(density, 4),
        "Avg clustering": round(clustering, 4),
        "Clustering (random baseline)": round(clustering_random, 4),
        "Clustering vs random (x)": round(clustering / clustering_random, 2),
        "Transitivity": round(nx.transitivity(UG), 4),
    })

df = pd.DataFrame(rows).set_index("Department")
pd.set_option("display.width", 140)
print(df.to_string())

df.to_csv(OUT_DIR / "structural_comparison.csv")
print("\nSaved analysis/structural_comparison.csv")
