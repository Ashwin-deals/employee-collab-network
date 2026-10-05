# Employee Collaboration Network

A social network analysis of internal email across a large European research institution, using SNAP's [email-Eu-core](https://snap.stanford.edu/data/email-Eu-core.html) network. Every person belongs to one of 42 departments, so the analysis covers both the institution as a whole and how communication flows within and between departments.

## Research questions

1. **Structure:** how connected, cohesive and reciprocal is the institution's email network?
2. **Key people:** who are the hubs and brokers, and how concentrated is influence?
3. **Departments:** does email stay inside departments, and do the communities found in the network match the real departments?

## Main findings

- **A small world.** Between people who are connected by some email path, the average distance is **2.65 hops** (diameter 7). 98% of people sit in one connected component.
- **Communication is two-way.** 71% of email ties are reciprocated.
- **Most email crosses department lines.** Only **35%** of emails stay inside the sender's department, but same-department contact is still well above chance (department assortativity 0.31).
- **Bigger departments are more self-contained.** Department size and the share of email kept internal are strongly correlated (r = 0.75). Department 14 keeps 74% of its email internal; most departments with fewer than 15 members keep under 20%.
- **One small department is the institution's hub.** Department 36 has only 22 members, yet holds the top 5 people by PageRank and degree and 4 of the top 5 by betweenness. It sends 2,110 cross-department emails (more than any other department) and talks to 40 of the other 41 departments. Person 160 in Department 36 ranks first by PageRank, degree and betweenness.
- **Influence is concentrated.** The 10 highest-betweenness people (1% of staff) carry 21% of all brokerage.
- **Communities only partly follow the org chart.** Louvain finds 28 communities with modularity 0.41, a better split than the departments themselves (0.29). Agreement with departments is moderate (NMI 0.59, ARI 0.35). The large communities mix many departments (the largest spans 27), so collaboration groups often cut across formal units.

## Results

### Network overview

Directed graph of 1,005 people and 24,929 email ties (642 self-emails removed). Edges are unweighted: the dataset lists each sender–recipient pair once.

| Metric | Value |
|---|---|
| Nodes / edges | 1,005 / 24,929 |
| Average degree (edges ÷ nodes) | 24.81 |
| Average total degree (in + out) | 49.61 |
| Graph density | 0.0247 |
| Network diameter / radius | 7 / 1 |
| Average path length (reachable pairs) | 2.65 |
| Share of ordered pairs that can reach each other | 78.5% |
| Weakly / strongly connected components | 20 / 203 |
| Largest weakly / strongly connected component | 98.1% / 79.9% of nodes |
| Isolated nodes | 19 |
| Reciprocity | 0.711 |
| Degree assortativity (out → in) | −0.014 |
| Average clustering (directed / undirected) | 0.366 / 0.399 |
| Transitivity (undirected) | 0.267 |
| Triangles (undirected) | 105,461 |
| Max k-core (undirected) | 34 |

### Communities vs departments

| Partition | Communities | Modularity | NMI vs departments | ARI vs departments |
|---|---|---|---|---|
| Real departments | 42 | 0.288 | 1 | 1 |
| Louvain (seed 42) | 28 | 0.413 | 0.595 | 0.351 |
| Greedy modularity | 27 | 0.347 | 0.433 | 0.152 |
| Label propagation | 20 | 0.000 | 0.033 | −0.001 |

Label propagation collapses 986 of the 1,005 people into one community, so it is reported for completeness only.

### Largest departments

| Department | Members | Internal emails | Cross-dept emails out | Share kept internal | Internal density | Partner departments |
|---|---|---|---|---|---|---|
| 4 | 109 | 1,167 | 1,417 | 45% | 0.099 | 38 |
| 14 | 92 | 1,506 | 538 | 74% | 0.180 | 38 |
| 1 | 65 | 502 | 608 | 45% | 0.121 | 39 |
| 21 | 61 | 601 | 714 | 46% | 0.164 | 34 |
| 15 | 55 | 357 | 714 | 33% | 0.120 | 39 |
| 7 | 51 | 679 | 503 | 57% | 0.266 | 33 |
| 36 | 22 | 208 | 2,110 | 9% | 0.450 | 40 |

The busiest department-to-department flows are 36 → 4 (229 emails), 4 → 5 (170) and the two-way pair 21 ↔ 22 (159 / 154).

## Outputs

All in `analysis/email_eu_core/`:

| File | Contents |
|---|---|
| `network_summary.csv` | every network-level metric |
| `department_summary.csv` | one row per department: size, internal vs cross-department email, density, conductance, clustering, partner departments, top PageRank person |
| `department_matrix.csv` | 42 × 42 table of emails from each department (row) to each department (column) |
| `nodes.csv` | one row per person: department, in/out degree, eccentricity, closeness, harmonic closeness, betweenness, HITS hub/authority, PageRank, eigenvector, clustering, component and community assignments |

## Method notes

- Built with **networkx**. Self-loops are dropped because they carry no communication between people.
- Distances are hop counts on the directed graph. The graph is not strongly connected, so diameter and average path length use only pairs that can reach each other, and the radius ignores nodes that reach no one.
- Community detection runs on the undirected version of the graph.
- Eigenvector centrality uses power iteration. Nodes outside the dominant strongly connected part score about 0.

## Repository layout

```
data/email-Eu-core/           SNAP edge list, department labels, and edges.csv / nodes.csv made from them by prepare.py
analysis/email_eu_core_analysis.py   the analysis script
analysis/email_eu_core/       generated results (CSV)
```

## Reproducing the analysis

```bash
pip install -r requirements.txt
python3 analysis/email_eu_core_analysis.py
```

## Data source

Data from the [Stanford Network Analysis Project](https://snap.stanford.edu/data/email-Eu-core.html):

- H. Yin, A. R. Benson, J. Leskovec and D. F. Gleich. *Local Higher-order Graph Clustering.* KDD 2017.
- J. Leskovec, J. Kleinberg and C. Faloutsos. *Graph Evolution: Densification and Shrinking Diameters.* ACM TKDD 2007.
