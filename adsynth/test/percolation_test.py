import json
import networkx as nx

# Load JSON lines
nodes = []
edges = []
with open("../../generated_datasets/2025-08-08_14-46-36-607.json", "r") as f:
    for line in f:
        obj = json.loads(line)
        if obj["type"] == "node":
            nodes.append(obj)
        elif obj["type"] == "relationship":
            edges.append(obj)


G = nx.Graph()

for n in nodes:
    node_id = n["id"]
    props = n.get("properties", {})
    G.add_node(node_id, **props)


for e in edges:
    src = e["start"]["id"]
    target = e["end"]["id"]
    props = e.get("properties", {})
    G.add_edge(src, target, **props)


for node in G.nodes():
    entry_node = G.nodes[node].get("highvalue", False)
    G.nodes[node]["percolation"] = 1.0 if entry_node else 0.5

# Compute percolation centrality
pc = nx.percolation_centrality(G, attribute="percolation")

print("Percolation Centrality Results:")
for node, score in pc.items():
    print(f"{node} ({G.nodes[node].get('name')}): {score:.4f}")
