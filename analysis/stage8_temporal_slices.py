"""
Stage 8: Temporal Slice Builder
Reads the raw temporal edge lists and partitions each department's events
into monthly windows (SLICE_DAYS = 30 days each).

Outputs
-------
temporal_slices.pkl  — {dept: {"graphs": [DiGraph, ...],
                                "event_counts": [int, ...],
                                "month_labels": [str, ...]}}
"""
import gzip
import pickle
from collections import defaultdict
from pathlib import Path

import networkx as nx

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUT_DIR  = Path(__file__).resolve().parent
DEPTS    = ["Dept1", "Dept2", "Dept3", "Dept4"]
SLICE_DAYS = 30
SLICE_SEC  = SLICE_DAYS * 86_400

result = {}

for dept in DEPTS:
    fpath = DATA_DIR / f"email-Eu-core-temporal-{dept}.gz"

    # bucket events by slice index
    buckets: dict[int, list[tuple[int, int]]] = defaultdict(list)
    with gzip.open(fpath, "rt") as f:
        for line in f:
            parts = line.split()
            if not parts:
                continue
            src, dst, ts = int(parts[0]), int(parts[1]), int(parts[2])
            bucket_idx = ts // SLICE_SEC
            buckets[bucket_idx].append((src, dst))

    n_slices = max(buckets) + 1

    graphs       = []
    event_counts = []
    month_labels = []

    for i in range(n_slices):
        G = nx.DiGraph()
        events = buckets.get(i, [])
        for src, dst in events:
            if G.has_edge(src, dst):
                G[src][dst]["weight"] += 1
            else:
                G.add_edge(src, dst, weight=1)
        graphs.append(G)
        event_counts.append(len(events))
        month_labels.append(f"M{i+1:02d}")

    result[dept] = {
        "graphs":       graphs,
        "event_counts": event_counts,
        "month_labels": month_labels,
    }
    print(f"{dept}: {n_slices} monthly slices, "
          f"{sum(event_counts)} total events, "
          f"avg {sum(event_counts)/n_slices:.0f} events/month")

with open(OUT_DIR / "temporal_slices.pkl", "wb") as f:
    pickle.dump(result, f)

print("\nSaved analysis/temporal_slices.pkl")
