from pathlib import Path

import pandas as pd

TEMPORAL_DIR = Path(__file__).resolve().parent / "data" / "email-Eu-core-temporal"

# (input file, output suffix) -- "" is the full undivided dataset
SOURCES = [
    ("email-Eu-core-temporal.csv", ""),
    ("email-Eu-core-temporal-Dept1.csv", "-Dept1"),
    ("email-Eu-core-temporal-Dept2.csv", "-Dept2"),
    ("email-Eu-core-temporal-Dept3.csv", "-Dept3"),
    ("email-Eu-core-temporal-Dept4.csv", "-Dept4"),
]

for fname, suffix in SOURCES:
    edges = pd.read_csv(TEMPORAL_DIR / fname, sep=" ", header=None, names=["Source", "Target", "Timestamp"])

    all_nodes = sorted(set(edges["Source"]).union(set(edges["Target"])))
    nodes = pd.DataFrame({"Id": all_nodes})

    edges.to_csv(TEMPORAL_DIR / f"edges{suffix}.csv", index=False)
    nodes.to_csv(TEMPORAL_DIR / f"nodes{suffix}.csv", index=False)

    print(f"--- {fname}")
    print(f"Events: {len(edges)}")
    print(f"Nodes in edge list: {len(all_nodes)}")
