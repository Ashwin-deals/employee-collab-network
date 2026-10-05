"""
networkx analysis of SNAP's static email-Eu-core network (data/email-Eu-core/),
the whole institution with a department label for every person.

Not part of the per-department temporal pipeline: node IDs here are the
global email-Eu-core IDs (0-1004), unrelated to the local IDs in the DeptN files.

Graph: directed, unweighted (the static edge list has one row per (src, dst)
pair), all 1005 labelled people as nodes. Self-loops (people emailing
themselves) are counted and then dropped, since they carry no communication
between people and k-core / clustering are undefined with them.

Conventions:
  - Distances are hop counts on the directed graph. It is not strongly connected,
    so diameter / avg path length are over reachable ordered pairs only, and
    radius over nodes that reach at least one other node.
  - Community detection runs on the undirected projection (Louvain seed SEED).
  - Department-vs-community agreement uses NMI and the adjusted Rand index.

Outputs (analysis/email_eu_core/):
  network_summary.csv       one row per network-level metric
  department_summary.csv    one row per department (size, internal/cross email, density, ...)
  department_matrix.csv     emails from department (row) to department (column)
  nodes.csv                 per-node metrics, department and community assignments
"""
from math import comb
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "email-Eu-core"
OUT_DIR = Path(__file__).resolve().parent / "email_eu_core"

SEED = 42


def membership(communities):
    return {node: cid for cid, members in enumerate(communities) for node in members}


def nmi(a, b):
    """Normalized mutual information (arithmetic mean normalization) of two labelings."""
    table = pd.crosstab(a, b).to_numpy().astype(float)
    p = table / table.sum()
    pa, pb = p.sum(axis=1), p.sum(axis=0)
    nz = p > 0
    mi = (p[nz] * np.log(p[nz] / np.outer(pa, pb)[nz])).sum()
    ha, hb = -(pa * np.log(pa)).sum(), -(pb * np.log(pb)).sum()
    return 2 * mi / (ha + hb)


def adjusted_rand(a, b):
    table = pd.crosstab(a, b).to_numpy()
    sum_cells = sum(comb(int(x), 2) for x in table.ravel())
    sum_rows = sum(comb(int(x), 2) for x in table.sum(axis=1))
    sum_cols = sum(comb(int(x), 2) for x in table.sum(axis=0))
    expected = sum_rows * sum_cols / comb(int(table.sum()), 2)
    return (sum_cells - expected) / ((sum_rows + sum_cols) / 2 - expected)


def main():
    OUT_DIR.mkdir(exist_ok=True)
    edges = pd.read_csv(DATA_DIR / "edges.csv")
    labels = pd.read_csv(DATA_DIR / "nodes.csv").set_index("Id")["Department"]

    G = nx.DiGraph()
    G.add_nodes_from(labels.index)
    G.add_edges_from(edges[["Source", "Target"]].itertuples(index=False))
    self_loops = nx.number_of_selfloops(G)
    G.remove_edges_from(list(nx.selfloop_edges(G)))
    nx.set_node_attributes(G, labels.to_dict(), "department")
    UG = G.to_undirected()
    n, m = G.number_of_nodes(), G.number_of_edges()
    s = {}

    # --- Network overview ---
    s["Nodes"] = n
    s["Edges"] = m
    s["SelfLoopsRemoved"] = self_loops
    s["IsolatedNodes"] = nx.number_of_isolates(G)
    s["AverageDegree"] = m / n                      # mean in-degree = mean out-degree
    s["AvgTotalDegree(in+out)"] = 2 * m / n

    eccentricity, path_sum, path_count = {}, 0, 0
    for source, dists in nx.all_pairs_shortest_path_length(G):
        reach = [d for target, d in dists.items() if target != source]
        eccentricity[source] = max(reach, default=0)
        path_sum += sum(reach)
        path_count += len(reach)
    s["NetworkDiameter"] = max(eccentricity.values())
    s["Radius"] = min(e for e in eccentricity.values() if e > 0)
    s["AvgPathLength"] = path_sum / path_count
    s["ReachablePairsShare"] = path_count / (n * (n - 1))
    largest_scc = G.subgraph(max(nx.strongly_connected_components(G), key=len))
    s["LargestSCCDiameter"] = nx.diameter(largest_scc)
    s["LargestSCCAvgPathLength"] = nx.average_shortest_path_length(largest_scc)

    s["GraphDensity"] = nx.density(G)
    wcc = list(nx.weakly_connected_components(G))
    scc = list(nx.strongly_connected_components(G))
    s["WeaklyConnectedComponents"] = len(wcc)
    s["StronglyConnectedComponents"] = len(scc)
    s["LargestWCCShare"] = max(map(len, wcc)) / n
    s["LargestSCCShare"] = max(map(len, scc)) / n
    s["Reciprocity"] = nx.reciprocity(G)
    s["DegreeAssortativity(out-in)"] = nx.degree_assortativity_coefficient(G, x="out", y="in")

    hubs, authorities = nx.hits(G, max_iter=1000)
    pagerank = nx.pagerank(G, alpha=0.85)
    # G is not strongly connected, so the numpy eigenvector solver refuses it;
    # power iteration converges (scores ~0 outside the dominant strongly connected part).
    eigenvector = nx.eigenvector_centrality(G, max_iter=10000, tol=1e-8)
    betweenness = nx.betweenness_centrality(G, normalized=True)
    closeness = nx.closeness_centrality(G)
    harmonic = nx.harmonic_centrality(G)

    # --- Node overview ---
    clustering_directed = nx.clustering(G)
    clustering_undirected = nx.clustering(UG)
    s["AvgClusteringCoefficient"] = np.mean(list(clustering_directed.values()))
    s["UndirectedAvgClustering"] = np.mean(list(clustering_undirected.values()))
    s["UndirectedTransitivity"] = nx.transitivity(UG)
    s["Triangles(undirected)"] = sum(nx.triangles(UG).values()) // 3
    s["MaxKCore(undirected)"] = max(nx.core_number(UG).values())
    s["AvgEigenvectorCentrality"] = np.mean(list(eigenvector.values()))
    s["AvgBetweennessCentrality"] = np.mean(list(betweenness.values()))
    s["AvgClosenessCentrality"] = np.mean(list(closeness.values()))

    # --- Community detection, and how well it recovers the real departments ---
    departments = [set(labels.index[labels == d]) for d in sorted(labels.unique())]
    louvain = nx.community.louvain_communities(UG, resolution=1.0, seed=SEED)
    greedy = nx.community.greedy_modularity_communities(UG)
    label_prop = list(nx.community.label_propagation_communities(UG))
    dept_labels = labels.loc[sorted(G.nodes())].to_numpy()

    s["Departments"] = len(departments)
    s["DepartmentPartitionModularity"] = nx.community.modularity(UG, departments)
    for name, communities in [("Louvain", louvain), ("GreedyModularity", greedy),
                              ("LabelPropagation", label_prop)]:
        comm = membership(communities)
        comm_labels = np.array([comm[v] for v in sorted(G.nodes())])
        s[f"{name}Modularity"] = nx.community.modularity(UG, communities)
        s[f"{name}Communities"] = len(communities)
        s[f"{name}LargestCommunity"] = max(map(len, communities))
        s[f"{name}VsDepartmentNMI"] = nmi(dept_labels, comm_labels)
        s[f"{name}VsDepartmentARI"] = adjusted_rand(dept_labels, comm_labels)

    # --- Department mixing ---
    src_dept = edges.loc[edges.Source != edges.Target, "Source"].map(labels)
    dst_dept = edges.loc[edges.Source != edges.Target, "Target"].map(labels)
    s["WithinDepartmentEmailShare"] = (src_dept == dst_dept).mean()
    s["DepartmentAssortativity"] = nx.attribute_assortativity_coefficient(G, "department")

    matrix = pd.crosstab(src_dept, dst_dept).reindex(
        index=sorted(labels.unique()), columns=sorted(labels.unique()), fill_value=0)
    matrix.index.name, matrix.columns.name = "FromDepartment", "ToDepartment"
    matrix.to_csv(OUT_DIR / "department_matrix.csv")

    rows = []
    for members in departments:
        dept = labels[next(iter(members))]
        sub = G.subgraph(members)
        out_edges = sum(G.out_degree(v) for v in members)
        in_edges = sum(G.in_degree(v) for v in members)
        internal = sub.number_of_edges()
        top = max(members, key=pagerank.get)
        rows.append({
            "Department": dept,
            "Members": len(members),
            "InternalEmails": internal,
            "OutgoingCrossDeptEmails": out_edges - internal,
            "IncomingCrossDeptEmails": in_edges - internal,
            "InternalShareOfOutgoing": internal / out_edges if out_edges else np.nan,
            "InternalDensity": nx.density(sub),
            "Conductance": nx.conductance(UG, members) if 0 < len(members) < n else np.nan,
            "AvgTotalDegree": np.mean([G.degree(v) for v in members]),
            "AvgUndirectedClustering": np.mean([clustering_undirected[v] for v in members]),
            "PartnerDepartments": int((matrix.loc[dept].drop(dept) > 0).sum()),
            "TopPageRankNode": top,
            "TopPageRank": pagerank[top],
        })
    dept_summary = pd.DataFrame(rows).set_index("Department").sort_values("Members", ascending=False)
    dept_summary.to_csv(OUT_DIR / "department_summary.csv")

    nodes = pd.DataFrame({
        "department": labels.to_dict(),
        "in_degree": dict(G.in_degree()),
        "out_degree": dict(G.out_degree()),
        "degree": dict(G.degree()),
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
    }).sort_index()
    nodes.index.name = "Id"
    nodes.to_csv(OUT_DIR / "nodes.csv")

    summary = pd.Series(s, name="Value")
    summary.index.name = "Metric"
    summary.to_csv(OUT_DIR / "network_summary.csv")

    pd.set_option("display.width", 160)
    print(summary.to_string(float_format=lambda v: f"{v:.4f}"))
    print("\n--- Departments (largest 10) ---")
    print(dept_summary.head(10).to_string(float_format=lambda v: f"{v:.3f}"))


if __name__ == "__main__":
    main()
