"""
Stage 4: Within-department community detection (Louvain), run separately
on each department graph. Louvain modularity is defined for undirected
graphs, so we run it on the undirected, weighted projection of each
department's DiGraph (weight = sum of emails in either direction).

Louvain is randomised, so it is also re-run with N_SEEDS different seeds to
report how stable Q and the number of communities are. The partition saved
for later stages is the one from SEED.
"""
import pickle
from pathlib import Path

import networkx as nx
import pandas as pd

OUT_DIR = Path(__file__).resolve().parent

with open(OUT_DIR / "graphs.pkl", "rb") as f:
    graphs = pickle.load(f)

SEED = 42
N_SEEDS = 20
partitions = {}
undirected_graphs = {}
rows = []

for dept, G in graphs.items():
    UG = nx.Graph()
    UG.add_nodes_from(G.nodes())
    for u, v, w in G.edges(data="weight"):
        if UG.has_edge(u, v):
            UG[u][v]["weight"] += w
        else:
            UG.add_edge(u, v, weight=w)
    undirected_graphs[dept] = UG

    communities = nx.community.louvain_communities(UG, weight="weight", seed=SEED)
    modularity = nx.community.modularity(UG, communities, weight="weight")

    partition = {}
    for cid, members in enumerate(communities):
        for node in members:
            partition[node] = cid
    partitions[dept] = partition

    sizes = sorted((len(c) for c in communities), reverse=True)
    reruns = [nx.community.louvain_communities(UG, weight="weight", seed=s) for s in range(N_SEEDS)]
    q_reruns = [nx.community.modularity(UG, c, weight="weight") for c in reruns]
    n_reruns = [len(c) for c in reruns]
    # people with at least one tie into a different community ("bridges")
    n_bridging = sum(1 for v in UG if any(partition[u] != partition[v] for u in UG[v]))
    rows.append({
        "Department": dept,
        "Num sub-communities": len(communities),
        "Modularity (Q)": round(modularity, 4),
        "Largest community size": sizes[0],
        "Largest community (% nodes)": round(100 * sizes[0] / UG.number_of_nodes(), 1),
        "Nodes with cross-community ties (%)": round(100 * n_bridging / UG.number_of_nodes(), 1),
        f"Q min over {N_SEEDS} seeds": round(min(q_reruns), 4),
        f"Q max over {N_SEEDS} seeds": round(max(q_reruns), 4),
        f"Communities min over {N_SEEDS} seeds": min(n_reruns),
        f"Communities max over {N_SEEDS} seeds": max(n_reruns),
        "Community size distribution": sizes,
    })

    print(f"\n=== {dept} ===")
    print(f"Sub-communities found: {len(communities)}")
    print(f"Modularity: {modularity:.4f}")
    print(f"Community sizes (largest->smallest): {sizes}")

df = pd.DataFrame(rows).set_index("Department")
pd.set_option("display.width", 140)
print("\n--- Community detection summary ---")
print(df.drop(columns=["Community size distribution"]).to_string())

df.to_csv(OUT_DIR / "community_summary.csv")
with open(OUT_DIR / "partitions.pkl", "wb") as f:
    pickle.dump({"partitions": partitions, "undirected_graphs": undirected_graphs}, f)

print("\nSaved analysis/community_summary.csv and analysis/partitions.pkl")
