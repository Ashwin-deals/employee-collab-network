"""
Stage 13: Network-, community-, node- and edge-overview metrics (the Gephi
Statistics-panel set, computed with networkx) for the temporal edge lists in
data/email-Eu-core-temporal/ (edges.csv, edges-Dept1..4.csv from prepare_temporal.py).

Each file is one independent network: a weighted DiGraph where repeated
(src, dst) email events are collapsed into one edge with weight = email count,
same rule as Stage 1.

Conventions:
  - Distances (diameter, radius, avg path length, eccentricity, betweenness,
    closeness) are unweighted hop counts on the directed graph. None of the
    networks is strongly connected, so diameter / avg path length are taken
    over reachable ordered pairs only, and radius over nodes that reach at
    least one other node.
  - Modularity uses Louvain on the undirected projection with weights summed
    over both directions, seed SEED (same as Stage 4).
  - networkx has no statistical-inference (stochastic block model) community
    detection. Greedy modularity (Clauset-Newman-Moore) and label propagation
    are reported as the alternative community methods instead.

Outputs (analysis/temporal_metrics/):
  temporal_network_summary.csv   one row per metric, one column per network
  nodes_<Network>.csv            per-node metrics and community assignments
"""
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

OUT_DIR = Path(__file__).resolve().parent / "temporal_metrics"
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "email-Eu-core-temporal"

SEED = 42
NETWORKS = {
    "Full": "edges.csv",
    "Dept1": "edges-Dept1.csv",
    "Dept2": "edges-Dept2.csv",
    "Dept3": "edges-Dept3.csv",
    "Dept4": "edges-Dept4.csv",
}


def build_graph(edges):
    G = nx.DiGraph()
    for (src, dst), w in edges.groupby(["Source", "Target"]).size().items():
        G.add_edge(src, dst, weight=int(w))
    return G


def undirected_projection(G):
    UG = nx.Graph()
    UG.add_nodes_from(G.nodes())
    for u, v, w in G.edges(data="weight"):
        if UG.has_edge(u, v):
            UG[u][v]["weight"] += w
        else:
            UG.add_edge(u, v, weight=w)
    return UG


def membership(communities):
    return {node: cid for cid, members in enumerate(communities) for node in members}


def community_metrics(prefix, UG, communities):
    sizes = sorted((len(c) for c in communities), reverse=True)
    return {
        f"{prefix}Modularity": nx.community.modularity(UG, communities, weight="weight"),
        f"{prefix}Communities": len(communities),
        f"{prefix}LargestCommunity": sizes[0],
    }


def analyse(edges):
    G = build_graph(edges)
    UG = undirected_projection(G)
    n, m = G.number_of_nodes(), G.number_of_edges()
    metrics, node_cols = {}, {}

    # --- Network Overview ---
    metrics["Nodes"] = n
    metrics["Edges"] = m
    metrics["AverageDegree"] = m / n                          # mean in-degree = mean out-degree
    metrics["AvgTotalDegree(in+out)"] = 2 * m / n
    metrics["AvgWeightedDegree"] = G.size(weight="weight") / n  # emails per node (in = out)

    # One BFS per node gives eccentricity, diameter, radius and avg path length.
    eccentricity, path_sum, path_count = {}, 0, 0
    for source, dists in nx.all_pairs_shortest_path_length(G):
        reach = [d for target, d in dists.items() if target != source]
        eccentricity[source] = max(reach, default=0)
        path_sum += sum(reach)
        path_count += len(reach)
    metrics["NetworkDiameter"] = max(eccentricity.values())
    metrics["Radius"] = min(e for e in eccentricity.values() if e > 0)
    metrics["AvgPathLength"] = path_sum / path_count
    metrics["ReachablePairsShare"] = path_count / (n * (n - 1))
    largest_scc = G.subgraph(max(nx.strongly_connected_components(G), key=len))
    metrics["LargestSCCDiameter"] = nx.diameter(largest_scc)
    metrics["LargestSCCAvgPathLength"] = nx.average_shortest_path_length(largest_scc)

    metrics["GraphDensity"] = nx.density(G)

    hubs, authorities = nx.hits(G, max_iter=1000)
    pagerank = nx.pagerank(G, alpha=0.85, weight="weight")

    wcc = list(nx.weakly_connected_components(G))
    scc = list(nx.strongly_connected_components(G))
    metrics["WeaklyConnectedComponents"] = len(wcc)
    metrics["StronglyConnectedComponents"] = len(scc)
    metrics["LargestWCCShare"] = max(map(len, wcc)) / n
    metrics["LargestSCCShare"] = max(map(len, scc)) / n

    # --- Community Detection ---
    louvain = nx.community.louvain_communities(UG, weight="weight", resolution=1.0, seed=SEED)
    greedy = nx.community.greedy_modularity_communities(UG, weight="weight")
    label_prop = list(nx.community.label_propagation_communities(UG))
    metrics.update(community_metrics("Louvain", UG, louvain))
    metrics.update(community_metrics("GreedyModularity", UG, greedy))
    metrics.update(community_metrics("LabelPropagation", UG, label_prop))

    # --- Node Overview ---
    clustering_directed = nx.clustering(G)
    clustering_undirected = nx.clustering(UG)
    metrics["AvgClusteringCoefficient"] = np.mean(list(clustering_directed.values()))
    metrics["UndirectedAvgClustering"] = np.mean(list(clustering_undirected.values()))
    metrics["UndirectedTransitivity"] = nx.transitivity(UG)
    metrics["Triangles(undirected)"] = sum(nx.triangles(UG).values()) // 3

    # In-edge eigenvector centrality (unweighted). G is not strongly connected, so the
    # numpy solver refuses it; power iteration converges, with the scores concentrated
    # in the dominant strongly connected part and ~0 for nodes that cannot reach it.
    eigenvector = nx.eigenvector_centrality(G, max_iter=10000, tol=1e-8)
    betweenness = nx.betweenness_centrality(G, normalized=True)
    closeness = nx.closeness_centrality(G)
    harmonic = nx.harmonic_centrality(G)

    # --- Extra structure / temporal context ---
    metrics["Reciprocity"] = nx.reciprocity(G)
    metrics["DegreeAssortativity(out-in)"] = nx.degree_assortativity_coefficient(G, x="out", y="in")
    metrics["MaxKCore(undirected)"] = max(nx.core_number(UG).values())
    metrics["EmailEvents"] = len(edges)
    metrics["TimeSpanDays"] = (edges["Timestamp"].max() - edges["Timestamp"].min()) / 86400
    metrics["SelfLoops"] = nx.number_of_selfloops(G)
    metrics["AvgEigenvectorCentrality"] = np.mean(list(eigenvector.values()))
    metrics["AvgBetweennessCentrality"] = np.mean(list(betweenness.values()))
    metrics["AvgClosenessCentrality"] = np.mean(list(closeness.values()))

    node_cols = {
        "in_degree": dict(G.in_degree()),
        "out_degree": dict(G.out_degree()),
        "degree": dict(G.degree()),
        "weighted_in_degree": dict(G.in_degree(weight="weight")),
        "weighted_out_degree": dict(G.out_degree(weight="weight")),
        "weighted_degree": dict(G.degree(weight="weight")),
        "eccentricity": eccentricity,
        "closeness": closeness,
        "harmonic_closeness": {v: c / (n - 1) for v, c in harmonic.items()},
        "betweenness": betweenness,
        "hub": hubs,
        "authority": authorities,
        "pagerank": pagerank,
        "eigenvector": eigenvector,
        "clustering_directed": clustering_directed,
        "clustering_undirected": clustering_undirected,
        "wcc": membership(sorted(wcc, key=len, reverse=True)),
        "scc": membership(sorted(scc, key=len, reverse=True)),
        "louvain_community": membership(louvain),
        "greedy_modularity_community": membership(greedy),
        "label_propagation_community": membership(label_prop),
    }
    nodes = pd.DataFrame(node_cols).sort_index()
    nodes.index.name = "Id"
    return pd.Series(metrics), nodes


def main():
    OUT_DIR.mkdir(exist_ok=True)
    columns = {}
    for name, fname in NETWORKS.items():
        summary, nodes = analyse(pd.read_csv(DATA_DIR / fname))
        nodes.to_csv(OUT_DIR / f"nodes_{name}.csv")
        columns[name] = summary
        print(f"{name}: {int(summary['Nodes'])} nodes, {int(summary['Edges'])} edges")

    summary = pd.DataFrame(columns)
    summary.index.name = "Metric"
    summary.to_csv(OUT_DIR / "temporal_network_summary.csv")
    print()
    print(summary.to_string(float_format=lambda v: f"{v:.4f}"))


if __name__ == "__main__":
    main()
