import pandas as pd

edges = pd.read_csv(r"C:\Users\jayad\Desktop\SEMESTER-7\23CSE2356-SOCIAL NETWORK ANALYSIS\Dataset\Email-Eu-Core\email-Eu-core.txt", sep=" ", header=None, names=["Source","Target"])
nodes = pd.read_csv(r"C:\Users\jayad\Desktop\SEMESTER-7\23CSE2356-SOCIAL NETWORK ANALYSIS\Dataset\Email-Eu-Core\email-Eu-core-department-labels.txt", sep=" ", header=None, names=["Id","Department"])

nodes = nodes.drop_duplicates(subset="Id")

all_nodes = set(edges["Source"]).union(set(edges["Target"]))
labeled_nodes = set(nodes["Id"])

edges.to_csv(r"C:\Users\jayad\Desktop\SEMESTER-7\23CSE2356-SOCIAL NETWORK ANALYSIS\Dataset\Email-Eu-Core\edges.csv", index=False)
nodes.to_csv(r"C:\Users\jayad\Desktop\SEMESTER-7\23CSE2356-SOCIAL NETWORK ANALYSIS\Dataset\Email-Eu-Core\nodes.csv", index=False)

missing = all_nodes - labeled_nodes
print(f"Nodes in edge list: {len(all_nodes)}")
print(f"Nodes with dept label: {len(labeled_nodes)}")
print(f"Missing labels: {len(missing)}")
print(sorted(missing)[:20])  # first 20 missing IDs