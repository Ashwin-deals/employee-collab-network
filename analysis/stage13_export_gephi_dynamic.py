"""
Stage 13: Export dynamic GEXF files for Gephi's timeline.

Same graphs as stage 12, but every node and edge also carries the days on
which it was active, so Gephi's timeline can play the network forward in
time. Raw timestamps are seconds since the first email; they are bucketed
into whole days (day 0 = first email) to keep the files a manageable size.

Uses GEXF 1.3 with timerepresentation="timestamp": each node/edge gets one
<spell timestamp="day"/> per active day, and each edge has a dynamic
"emails" attribute with the number of emails sent on that day. Node layout,
community colour and PageRank size are static, so nodes stay in place while
edges appear and disappear.
"""
import pickle
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
import networkx as nx

OUT_DIR = Path(__file__).resolve().parent
DATA_DIR = OUT_DIR.parent / "data" / "email-Eu-core-temporal"
GEPHI_DIR = OUT_DIR / "gephi"
GEPHI_DIR.mkdir(exist_ok=True)

SEED = 42
LAYOUT_SCALE = 1000
MIN_SIZE, MAX_SIZE = 4, 40
SECONDS_PER_DAY = 86400

cmap = matplotlib.colormaps["tab20"]


def read_daily_events(path):
    """(src, dst, day) -> number of emails sent that day."""
    counts = Counter()
    with open(path) as f:
        for line in f:
            parts = line.split()
            if parts:
                src, dst, ts = int(parts[0]), int(parts[1]), int(parts[2])
                counts[(src, dst, ts // SECONDS_PER_DAY)] += 1
    return counts


def undirected_weighted(G):
    """Undirected projection summing weight in both directions (as in stage 4)."""
    UG = nx.Graph()
    UG.add_nodes_from(G.nodes())
    for u, v, w in G.edges(data="weight"):
        if UG.has_edge(u, v):
            UG[u][v]["weight"] += w
        else:
            UG.add_edge(u, v, weight=w)
    return UG


def write_dynamic_gexf(path, daily, part, pagerank):
    G = nx.DiGraph()
    edge_days = defaultdict(dict)   # (src, dst) -> {day: emails}
    node_days = defaultdict(set)
    for (src, dst, day), n in daily.items():
        edge_days[(src, dst)][day] = n
        node_days[src].add(day)
        node_days[dst].add(day)
    for (src, dst), days in edge_days.items():
        G.add_edge(src, dst, weight=sum(days.values()))

    UG = G.to_undirected()
    pos = nx.spring_layout(UG, weight=None, seed=SEED, scale=LAYOUT_SCALE,
                           k=2 / (UG.number_of_nodes() ** 0.5))
    pr_min, pr_max = min(pagerank.values()), max(pagerank.values())

    with open(path, "w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<gexf xmlns="http://gexf.net/1.3" xmlns:viz="http://gexf.net/1.3/viz" version="1.3">\n')
        f.write('  <graph mode="dynamic" defaultedgetype="directed" timeformat="double" timerepresentation="timestamp">\n')
        f.write('    <attributes class="node" mode="static">\n')
        f.write('      <attribute id="community" title="community" type="integer"/>\n')
        f.write('      <attribute id="pagerank" title="pagerank" type="double"/>\n')
        f.write('    </attributes>\n')
        f.write('    <attributes class="edge" mode="dynamic">\n')
        f.write('      <attribute id="emails" title="emails" type="integer"/>\n')
        f.write('    </attributes>\n')

        f.write('    <nodes>\n')
        for node in sorted(G.nodes()):
            pr = pagerank[node]
            r, g, b, _ = cmap(part[node] % cmap.N)
            size = MIN_SIZE + (MAX_SIZE - MIN_SIZE) * (pr - pr_min) / (pr_max - pr_min)
            x, y = pos[node]
            f.write(f'      <node id="{node}" label="{node}">\n')
            f.write('        <attvalues>\n')
            f.write(f'          <attvalue for="community" value="{part[node]}"/>\n')
            f.write(f'          <attvalue for="pagerank" value="{pr}"/>\n')
            f.write('        </attvalues>\n')
            f.write('        <spells>\n')
            for day in sorted(node_days[node]):
                f.write(f'          <spell timestamp="{day}.0"/>\n')
            f.write('        </spells>\n')
            f.write(f'        <viz:color r="{int(r * 255)}" g="{int(g * 255)}" b="{int(b * 255)}"/>\n')
            f.write(f'        <viz:position x="{x}" y="{y}" z="0.0"/>\n')
            f.write(f'        <viz:size value="{size}"/>\n')
            f.write('      </node>\n')
        f.write('    </nodes>\n')

        f.write('    <edges>\n')
        for eid, ((src, dst), days) in enumerate(sorted(edge_days.items())):
            f.write(f'      <edge id="{eid}" source="{src}" target="{dst}" weight="{sum(days.values())}">\n')
            f.write('        <attvalues>\n')
            for day, n in sorted(days.items()):
                f.write(f'          <attvalue for="emails" value="{n}" timestamp="{day}.0"/>\n')
            f.write('        </attvalues>\n')
            f.write('        <spells>\n')
            for day in sorted(days):
                f.write(f'          <spell timestamp="{day}.0"/>\n')
            f.write('        </spells>\n')
            f.write('      </edge>\n')
        f.write('    </edges>\n')
        f.write('  </graph>\n')
        f.write('</gexf>\n')

    n_days = len({d for (_, _, d) in daily})
    print(f"{path.name}: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges, "
          f"{len(daily)} edge-days over {n_days} active days")


with open(OUT_DIR / "partitions.pkl", "rb") as f:
    partitions = pickle.load(f)["partitions"]
with open(OUT_DIR / "centrality_tables.pkl", "rb") as f:
    centrality = pickle.load(f)

# Departments: reuse stage 3/4 communities and PageRank so colours and sizes
# match the static exports.
for dept in ["Dept1", "Dept2", "Dept3", "Dept4"]:
    daily = read_daily_events(DATA_DIR / f"email-Eu-core-temporal-{dept}.csv")
    pagerank = {n: float(v) for n, v in centrality[dept]["pagerank"].items()}
    write_dynamic_gexf(GEPHI_DIR / f"{dept}_dynamic.gexf", daily, partitions[dept], pagerank)

# Full dataset is not part of the earlier stages, so compute its communities
# and PageRank here the same way.
daily = read_daily_events(DATA_DIR / "email-Eu-core-temporal.csv")
G_full = nx.DiGraph()
for (src, dst, _), n in daily.items():
    if G_full.has_edge(src, dst):
        G_full[src][dst]["weight"] += n
    else:
        G_full.add_edge(src, dst, weight=n)
communities = nx.community.louvain_communities(undirected_weighted(G_full), weight="weight", seed=SEED)
part_full = {node: cid for cid, members in enumerate(communities) for node in members}
pagerank_full = nx.pagerank(G_full, weight="weight")
write_dynamic_gexf(GEPHI_DIR / "Full_dynamic.gexf", daily, part_full, pagerank_full)

print("\nOpen in Gephi via File > Open, then enable the Timeline (bottom of the window).")
