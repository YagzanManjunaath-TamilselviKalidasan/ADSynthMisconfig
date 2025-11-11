import json
import os
from datetime import datetime
import tempfile
import networkx as nx
from igraph import Graph
import matplotlib.pyplot as plt

from adsynth.EXPERIMENT_DATABASE import EXP_NODES, EXP_EDGES, EXP_COMPUTERS, EXP_MISCONFIGURED_SESSION_USERS


def draw_graph(nx_attack_graph):
    plt.figure(figsize=(8, 6))
    nx.draw_networkx(nx_attack_graph, with_labels=True, node_color="lightblue")
    plt.show()


def create_networkx_graph():
    nx_attack_graph = nx.DiGraph()

    for n in EXP_NODES:
        node_id = n["id"]
        props = n.get("properties", {})
        labels = n.get("labels", [])
        nx_attack_graph.add_node(node_id, labels=labels, **props)

    for e in EXP_EDGES:
        src = e["start"]["id"]
        src_labels = e["start"].get("labels", [])
        target = e["end"]["id"]
        target_labels = e["end"].get("labels", [])
        props = e.get("properties", {})
        rel_label = e.get("label")
        nx_attack_graph.add_edge(
            src,
            target,
            label=rel_label,
            start_labels=src_labels,
            end_labels=target_labels,
            **props,
        )

    return nx_attack_graph

def create_networkx_graph_fast():
    nodes = [
        (n["id"], {"labels": n.get("labels", []), **n.get("properties", {})})
        for n in EXP_NODES
    ]
    edges = [
        (
            e["start"]["id"],
            e["end"]["id"],
            {
                "label": e.get("label"),
                "start_labels": e["start"].get("labels", []),
                "end_labels": e["end"].get("labels", []),
                **e.get("properties", {}),
            },
        )
        for e in EXP_EDGES
    ]

    G = nx.DiGraph()
    G.add_nodes_from(nodes)
    G.add_edges_from(edges)
    return G

def print_all_nodes(graph):
    print("All nodes in graph:")
    for node_id, attrs in graph.nodes(data=True):
        print(f"ID: {node_id}, name: {attrs.get('name')}, displayname: {attrs.get('displayname')}")


def get_id_from_name(graph, name):
    for node_id, attrs in graph.nodes(data=True):
        if attrs.get("name") == name:
            return node_id
    return None

def get_id_from_name_ig(g, name):
    """Return node ID (vertex 'id') given its 'name' property in igraph."""
    matches = g.vs.select(name_eq=name)
    if len(matches) == 0:
        return None
    return matches[0]["id"]


def find_user_count_with_path_to_DA(networkx_graph, domain_grp_name, misconfig_session_count, misconfig_growth_metrics):
    domain_grp_id = get_id_from_name(networkx_graph, domain_grp_name)
    if domain_grp_id not in networkx_graph:
        return

    lengths = nx.single_target_shortest_path_length(networkx_graph, domain_grp_id)
    reachable_nodes = set(lengths.keys())

    comp_id_map = {c: get_id_from_name(networkx_graph, c) for c in EXP_COMPUTERS}
    reachable_comps = {cid for cid in comp_id_map.values() if cid in reachable_nodes}
    reachable_comps_names = [
        networkx_graph.nodes[cid].get("name", cid)
        for cid in comp_id_map.values()
        if cid in reachable_nodes
    ]

    reachable_users = set()

    exploitable_permissions = ["AdminTo", "CanRDP", "CanPSRemote", "ExecuteDCOM", "AllowedToDelegate",
                               "ReadLAPSPassword", "SQLAdmin",
                               "AllowedToAct"]

    for comp_id in reachable_comps:
        # ---------- predecessors: users who have exploitable permissions TO the computer ----------
        for u in networkx_graph.predecessors(comp_id):
            if "User" not in networkx_graph.nodes[u].get("labels", []):
                continue


            exploit_types = []
            edge_data = networkx_graph.get_edge_data(u, comp_id) or {}

            if isinstance(edge_data, dict) and any(isinstance(k, (int, str)) for k in edge_data):

                if any(isinstance(v, dict) and "label" in v for v in edge_data.values()):
                    for v in edge_data.values():
                        label = v.get("label")
                        if label and label in exploitable_permissions:
                            exploit_types.append(label)
                else:

                    label = edge_data.get("label")
                    if label and label in exploitable_permissions:
                        exploit_types.append(label)
            else:
                # simple DiGraph edge
                label = networkx_graph.edges[u, comp_id].get("label")
                if label and label in exploitable_permissions:
                    exploit_types.append(label)

            if exploit_types:
                node_data = networkx_graph.nodes[u]
                user_name = node_data.get("displayname") or node_data.get("name") or u
                member_of = []
                for g in networkx_graph.successors(u):
                    if (
                            networkx_graph.edges[u, g].get("label") == "MemberOf"
                            and "Group" in networkx_graph.nodes[g].get("labels", [])
                    ):
                        member_of.append(networkx_graph.nodes[g].get("name", g))

                exploit_label = ", ".join(sorted(set(exploit_types)))
                meta_str = f"{user_name} - {member_of} - predecessor({exploit_label})"
                reachable_users.add(meta_str)

        # ---------- successors: users who have sessions ON the computer ----------
        for v in networkx_graph.successors(comp_id):
            if "User" not in networkx_graph.nodes[v].get("labels", []):
                continue

            session_labels = []
            edge_data = networkx_graph.get_edge_data(comp_id, v) or {}
            if isinstance(edge_data, dict) and any(isinstance(k, (int, str)) for k in edge_data):
                if any(isinstance(val, dict) and "label" in val for val in edge_data.values()):
                    for val in edge_data.values():
                        label = val.get("label")
                        if label == "HasSession":
                            session_labels.append(label)
                else:
                    label = edge_data.get("label")
                    if label == "HasSession":
                        session_labels.append(label)
            else:
                if networkx_graph.edges[comp_id, v].get("label") == "HasSession":
                    session_labels.append("HasSession")

            if session_labels:
                node_data = networkx_graph.nodes[v]
                user_name = node_data.get("displayname") or node_data.get("name") or v
                member_of = []
                for g in networkx_graph.successors(v):
                    if (
                            networkx_graph.edges[v, g].get("label") == "MemberOf"
                            and "Group" in networkx_graph.nodes[g].get("labels", [])
                    ):
                        member_of.append(networkx_graph.nodes[g].get("name", g))

                exploit_label = ", ".join(sorted(set(session_labels)))
                meta_str = f"{user_name} - {member_of} - successor({exploit_label})"
                reachable_users.add(meta_str)

    if misconfig_session_count not in misconfig_growth_metrics:
        misconfig_growth_metrics[misconfig_session_count] = {}

    available_keys = sorted(k for k in misconfig_growth_metrics.keys() if k < misconfig_session_count)
    prev_key = available_keys[-1] if available_keys else None

    if prev_key is not None:
        prev_reachable_comps_names = set(misconfig_growth_metrics[prev_key].get("reachable_comps_names", []))
        prev_reachable_users = set(misconfig_growth_metrics[prev_key].get("reachable_users", []))
    else:
        prev_reachable_comps_names = set()
        prev_reachable_users = set()

    # prev_reachable_comps_names = set(
    #         misconfig_growth_metrics[misconfig_session_count - 1]["reachable_comps_names"]
    #     ) if misconfig_session_count -1 > 0 else set()

    new_reachable_comps_names = set(reachable_comps_names) - prev_reachable_comps_names

    # prev_reachable_users = set(
    #     misconfig_growth_metrics[misconfig_session_count - 1]["reachable_users"]
    # ) if misconfig_session_count - 1 > 0 else set()

    new_reachable_users = set(reachable_users) - prev_reachable_users

    misconfig_growth_metrics[misconfig_session_count]["reachable_users"] = list(reachable_users)
    misconfig_growth_metrics[misconfig_session_count]["new_reachable_users"] = list(new_reachable_users)
    misconfig_growth_metrics[misconfig_session_count]["reachable_comps"] = list(reachable_comps)
    misconfig_growth_metrics[misconfig_session_count]["new_reachable_comps_names"] = list(new_reachable_comps_names)
    misconfig_growth_metrics[misconfig_session_count]["reachable_comps_names"] = list(reachable_comps_names)
    misconfig_growth_metrics[misconfig_session_count]["reachable_users_count"] = len(reachable_users)
    misconfig_growth_metrics[misconfig_session_count]["reachable_comps_count"] = len(reachable_comps)



def find_user_count_with_path_to_DA_fast(networkx_graph, domain_grp_name, misconfig_session_count, misconfig_growth_metrics):
    domain_grp_id = get_id_from_name(networkx_graph, domain_grp_name)
    if domain_grp_id not in networkx_graph:
        return

    # ---- Pre-cache attributes for speed ----
    node_labels = nx.get_node_attributes(networkx_graph, "labels")
    node_names = nx.get_node_attributes(networkx_graph, "name")
    node_display = nx.get_node_attributes(networkx_graph, "displayname")
    edge_labels = nx.get_edge_attributes(networkx_graph, "label")

    exploitable_permissions = {
        "AdminTo", "CanRDP", "CanPSRemote", "ExecuteDCOM", "AllowedToDelegate",
        "ReadLAPSPassword", "SQLAdmin", "AllowedToAct"
    }

    # ---- Build membership map once ----
    user_groups = {}
    for u, v, lbl in networkx_graph.edges(data="label"):
        if lbl == "MemberOf" and "Group" in node_labels.get(v, []):
            user_groups.setdefault(u, []).append(node_names.get(v, v))

    # ---- Compute reachability (fast) ----
    reachable_nodes = nx.ancestors(networkx_graph, domain_grp_id) | {domain_grp_id}

    comp_id_map = {c: get_id_from_name(networkx_graph, c) for c in EXP_COMPUTERS}
    reachable_comps = {cid for cid in comp_id_map.values() if cid in reachable_nodes}
    reachable_comps_names = [
        node_names.get(cid, cid)
        for cid in reachable_comps
    ]

    # ---- Precompute exploitable edges ----
    exploitable_edges = {
        (u, v): lbl for (u, v, lbl) in networkx_graph.edges(data="label")
        if lbl in exploitable_permissions
    }

    # ---- Precompute session edges ----
    session_edges = {
        (u, v) for (u, v, lbl) in networkx_graph.edges(data="label")
        if lbl == "HasSession"
    }

    reachable_users = set()

    # ---- Find users linked to each reachable computer ----
    for comp_id in reachable_comps:
        # --- Users with exploitable permissions (predecessors) ---
        preds = [u for u in networkx_graph.predecessors(comp_id)
                 if "User" in node_labels.get(u, []) and (u, comp_id) in exploitable_edges]
        for u in preds:
            user_name = node_display.get(u) or node_names.get(u, u)
            member_of = user_groups.get(u, [])
            label = exploitable_edges[(u, comp_id)]
            meta_str = f"{user_name} - {member_of} - predecessor({label})"
            reachable_users.add(meta_str)

        # --- Users with sessions (successors) ---
        succs = [v for v in networkx_graph.successors(comp_id)
                 if "User" in node_labels.get(v, []) and (comp_id, v) in session_edges]
        for v in succs:
            user_name = node_display.get(v) or node_names.get(v, v)
            member_of = user_groups.get(v, [])
            meta_str = f"{user_name} - {member_of} - successor(HasSession)"
            reachable_users.add(meta_str)

    # ---- Compute growth metrics ----
    if misconfig_session_count not in misconfig_growth_metrics:
        misconfig_growth_metrics[misconfig_session_count] = {}

    prev_metrics = misconfig_growth_metrics.get(misconfig_session_count - 1, {})
    prev_reachable_comps_names = set(prev_metrics.get("reachable_comps_names", []))
    prev_reachable_users = set(prev_metrics.get("reachable_users", []))

    new_reachable_comps_names = set(reachable_comps_names) - prev_reachable_comps_names
    new_reachable_users = set(reachable_users) - prev_reachable_users

    # ---- Store results ----
    metrics = misconfig_growth_metrics[misconfig_session_count]
    metrics["reachable_users"] = list(reachable_users)
    metrics["new_reachable_users"] = list(new_reachable_users)
    metrics["reachable_comps"] = list(reachable_comps)
    metrics["new_reachable_comps_names"] = list(new_reachable_comps_names)
    metrics["reachable_comps_names"] = list(reachable_comps_names)
    metrics["reachable_users_count"] = len(reachable_users)
    metrics["reachable_comps_count"] = len(reachable_comps)

import networkx as nx
from collections import defaultdict

def count_paths_between_tiers(networkx_graph: nx.DiGraph, tier_nodes: list[list[str]], max_depth: int = 3):
    """
    Count how many paths exist from nodes in one tier to nodes in another tier.

    Args:
        networkx_graph: The attack graph (directed).
        tier_nodes: A list of lists, e.g. PAW_TIERS or S_TIERS, where each sublist represents a tier.
        max_depth: Optional limit to path length to avoid combinatorial explosion.

    Returns:
        paths_summary: dict[(int,int)] = count of paths from tier_i to tier_j
    """
    paths_summary = defaultdict(int)

    n_tiers = len(tier_nodes)
    for i in range(n_tiers):
        for src in tier_nodes[i]:
            src_node = src if src in networkx_graph else f"{src}_Computer"
            if not networkx_graph.has_node(src_node):
                continue

            for j in range(n_tiers):
                if i == j:
                    continue
                for dst in tier_nodes[j]:
                    dst_node = dst if dst in networkx_graph else f"{dst}_Computer"
                    if not networkx_graph.has_node(dst_node):
                        continue

                    try:
                        # check existence of path up to max_depth
                        if nx.has_path(networkx_graph, src_node, dst_node):
                            if max_depth:
                                for path in nx.all_simple_paths(networkx_graph, src_node, dst_node, cutoff=max_depth):
                                    paths_summary[(i, j)] += 1
                            else:
                                for path in nx.all_simple_paths(networkx_graph, src_node, dst_node):
                                    paths_summary[(i, j)] += 1
                    except nx.NetworkXNoPath:
                        continue

    return dict(paths_summary)


def find_user_count_with_path_to_DA_(networkx_graph, domain_grp_name, misconfig_session_count, misconfig_growth_metrics):
    domain_grp_id = get_id_from_name(networkx_graph, domain_grp_name)
    if domain_grp_id not in networkx_graph:
        return

    lengths = nx.single_source_shortest_path_length(networkx_graph, domain_grp_id)
    reachable_nodes = set(lengths.keys())

    comp_id_map = {c: get_id_from_name(networkx_graph, c) for c in EXP_COMPUTERS}
    reachable_comps = {cid for cid in comp_id_map.values() if cid in reachable_nodes}
    reachable_comps_names = [
        networkx_graph.nodes[cid].get("name", cid)
        for cid in comp_id_map.values()
        if cid in reachable_nodes
    ]

    reachable_users = set()

    exploitable_permissions = [
        "AdminTo", "CanRDP", "CanPSRemote", "ExecuteDCOM",
        "AllowedToDelegate", "ReadLAPSPassword", "SQLAdmin", "AllowedToAct"
    ]

    for comp_id in reachable_comps:
        for u in networkx_graph.predecessors(comp_id):
            if "User" not in networkx_graph.nodes[u].get("labels", []):
                continue

            exploit_types = []
            edge_data = networkx_graph.get_edge_data(u, comp_id) or {}
            if isinstance(edge_data, dict):
                for v in (edge_data.values() if all(isinstance(v, dict) for v in edge_data.values()) else [edge_data]):
                    label = v.get("label")
                    if label and label in exploitable_permissions:
                        exploit_types.append(label)

            if exploit_types:
                node_data = networkx_graph.nodes[u]
                user_name = node_data.get("displayname") or node_data.get("name") or u
                member_of = [
                    networkx_graph.nodes[g].get("name", g)
                    for g in networkx_graph.successors(u)
                    if (
                        networkx_graph.edges[u, g].get("label") == "MemberOf"
                        and "Group" in networkx_graph.nodes[g].get("labels", [])
                    )
                ]
                exploit_label = ", ".join(sorted(set(exploit_types)))
                meta_str = f"{user_name} - {member_of} - predecessor({exploit_label})"
                reachable_users.add(meta_str)

        for v in networkx_graph.successors(comp_id):
            if "User" not in networkx_graph.nodes[v].get("labels", []):
                continue

            session_labels = []
            edge_data = networkx_graph.get_edge_data(comp_id, v) or {}
            if isinstance(edge_data, dict):
                for val in (edge_data.values() if all(isinstance(val, dict) for val in edge_data.values()) else [edge_data]):
                    label = val.get("label")
                    if label == "HasSession":
                        session_labels.append(label)

            if session_labels:
                node_data = networkx_graph.nodes[v]
                user_name = node_data.get("displayname") or node_data.get("name") or v
                member_of = [
                    networkx_graph.nodes[g].get("name", g)
                    for g in networkx_graph.successors(v)
                    if (
                        networkx_graph.edges[v, g].get("label") == "MemberOf"
                        and "Group" in networkx_graph.nodes[g].get("labels", [])
                    )
                ]
                exploit_label = ", ".join(sorted(set(session_labels)))
                meta_str = f"{user_name} - {member_of} - successor({exploit_label})"
                reachable_users.add(meta_str)


    if misconfig_session_count not in misconfig_growth_metrics:
        misconfig_growth_metrics[misconfig_session_count] = {}

    misconfig_growth_metrics[misconfig_session_count]["reachable_users"] = list(reachable_users)
    misconfig_growth_metrics[misconfig_session_count]["reachable_comps"] = list(reachable_comps)
    misconfig_growth_metrics[misconfig_session_count]["reachable_comps_names"] = list(reachable_comps_names)
    misconfig_growth_metrics[misconfig_session_count]["reachable_users_count"] = len(reachable_users)
    misconfig_growth_metrics[misconfig_session_count]["reachable_comps_count"] = len(reachable_comps)

def find_user_count_with_path_to_DA_undirected(networkx_graph, domain_grp_name, misconfig_session_count,
                                               misconfig_growth_metrics):
    g_undirected = networkx_graph.to_undirected(as_view=True)

    domain_grp_id = get_id_from_name(networkx_graph, domain_grp_name)
    if domain_grp_id not in g_undirected:
        return

    lengths = nx.single_target_shortest_path_length(g_undirected, domain_grp_id)
    reachable_nodes = set(lengths.keys())

    comp_id_map = {c: get_id_from_name(networkx_graph, c) for c in EXP_COMPUTERS}
    reachable_comps = {cid for cid in comp_id_map.values() if cid in reachable_nodes}

    exploitable_permissions = ["AdminTo", "CanRDP", "CanPSRemote", "ExecuteDCOM", "AllowedToDelegate",
                               "ReadLAPSPassword", "SQLAdmin",
                               "AllowedToAct", "HasSession"]

    reachable_users = set()
    for comp_id in reachable_comps:
        for v in networkx_graph.successors(comp_id):
            if (
                    "User" in networkx_graph.nodes[v].get("labels", [])
                    and networkx_graph.edges[comp_id, v].get("label") in exploitable_permissions
            ):
                reachable_users.add(v)

    misconfig_growth_metrics.setdefault(misconfig_session_count, {})
    misconfig_growth_metrics[misconfig_session_count]["reachable_users"] = list(reachable_users)
    misconfig_growth_metrics[misconfig_session_count]["reachable_comps"] = list(reachable_comps)
    misconfig_growth_metrics[misconfig_session_count]["reachable_users_count"] = len(reachable_users)
    misconfig_growth_metrics[misconfig_session_count]["reachable_comps_count"] = len(reachable_comps)


def find_shortest_paths_from_misconfig_users(networkx_graph, misconfig_user_count, domain_grp_name, user_level_metrics):
    domain_grp_id = get_id_from_name(networkx_graph, domain_grp_name)
    for user in EXP_MISCONFIGURED_SESSION_USERS:
        # print((f"Finding shortest path {user} and {domain_grp_name}"))
        user_id = get_id_from_name(networkx_graph, user)

        if user_id not in networkx_graph or domain_grp_id not in networkx_graph:
            continue

        try:

            path_nodes = nx.shortest_path(networkx_graph, source=user_id, target=domain_grp_id)

            path_len = nx.shortest_path_length(networkx_graph, source=user_id, target=domain_grp_id)

            path_str = " -> ".join(path_nodes)

            if user not in user_level_metrics:
                user_level_metrics[user] = {}
            user_level_metrics[user]["shortest_path_length"] = path_len
            user_level_metrics[user]["shortest_path_nodes"] = path_str
            user_level_metrics[user]["shortest_path_nodes_list"] = path_nodes



        except nx.NetworkXNoPath:
            if user not in user_level_metrics:
                user_level_metrics[user] = {}
            user_level_metrics[user]["shortest_path_length"] = None
            user_level_metrics[user]["shortest_path_nodes"] = "No path"
            user_level_metrics[user]["shortest_path_nodes_list"] = []


def calculate_total_paths_to_domain_admins(networkx_graph, misconfig_user_count, domain_grp_name, rows):
    # print("Users to check:", domain_grp_name not in networkx_graph)

    for user in EXP_MISCONFIGURED_SESSION_USERS:
        user_id = get_id_from_name(networkx_graph, user)
        domain_grp_id = get_id_from_name(networkx_graph, domain_grp_name)
        print((f" total path {user} and {domain_grp_name}"))
        if user_id not in networkx_graph or domain_grp_id not in networkx_graph:
            continue

        try:
            # Get all simple paths (non-repeating nodes)
            print((f" start {user} and {domain_grp_name}"))
            paths = list(nx.all_simple_paths(networkx_graph, source=user_id, target=domain_grp_id))
            print((f" paths {user} and {domain_grp_name} {paths}"))
            path_count = len(paths)
            print(path_count)
            if user not in rows:
                rows[user] = {}

            # rows[user][f"paths  {misconfig_user_count}"] = [" -> ".join(p) for p in paths]
            rows[user][f"Total paths  {misconfig_user_count} "] = path_count
        except nx.NetworkXNoPath:
            if user not in rows:
                rows[user] = {}
            rows[user][f"Total paths  {misconfig_user_count} "] = 0
            # rows[user][f"paths  {misconfig_user_count}"] = []





def create_igraph_from_adsynth():
    """Fast igraph builder for ADSynth node/edge export."""
    node_ids = [n["id"] for n in EXP_NODES]
    node_idx = {nid: i for i, nid in enumerate(node_ids)}

    g = Graph(directed=True)
    g.add_vertices(len(node_ids))

    # ---- Node attributes ----
    g.vs["id"] = node_ids
    g.vs["name"] = [n.get("properties", {}).get("name", nid) for nid, n in zip(node_ids, EXP_NODES)]
    g.vs["labels"] = [n.get("labels", []) for n in EXP_NODES]

    # ---- Edges ----
    edges = [(node_idx[e["start"]["id"]], node_idx[e["end"]["id"]]) for e in EXP_EDGES]
    g.add_edges(edges)
    g.es["label"] = [e.get("label", "") for e in EXP_EDGES]

    return g, node_idx

def find_user_count_with_path_to_DA_igraph(g, node_idx, domain_grp_name, misconfig_session_count,
                                               misconfig_growth_metrics):
        # ---- Find domain group vertex ----
        domain_grp_id = get_id_from_name_ig(g, domain_grp_name)
        if domain_grp_id not in node_idx:
            return

        domain_vid = node_idx[domain_grp_id]

        # ---- Compute all vertices that can reach Domain Admin ----
        reachable_vertices = set(g.subcomponent(domain_vid, mode="in"))
        reachable_nodes = {g.vs[v]["id"] for v in reachable_vertices}

        # ---- Prepare maps for labels / names ----
        vertex_labels = g.vs["labels"]
        vertex_names = g.vs["name"]
        id_to_name = {g.vs[i]["id"]: vertex_names[i] for i in range(len(g.vs))}

        # ---- Identify reachable computers ----
        comp_ids = [get_id_from_name_ig(g, c) for c in EXP_COMPUTERS]
        reachable_comps = [cid for cid in comp_ids if cid in reachable_nodes]
        reachable_comps_names = [id_to_name[cid] for cid in reachable_comps if cid in id_to_name]

        # ---- Collect reachable users ----
        exploitable_permissions = {
            "AdminTo", "CanRDP", "CanPSRemote", "ExecuteDCOM",
            "AllowedToDelegate", "ReadLAPSPassword", "SQLAdmin", "AllowedToAct"
        }

        reachable_users = set()

        for comp_id in reachable_comps:
            comp_vid = node_idx.get(comp_id)
            if comp_vid is None:
                continue

            # -- Predecessors (users with exploitable permissions to this computer)
            for e in g.incident(comp_vid, mode="in"):
                src_vid = g.es[e].source
                if "User" not in vertex_labels[src_vid]:
                    continue
                if g.es[e]["label"] in exploitable_permissions:
                    uname = vertex_names[src_vid]
                    reachable_users.add(f"{uname} - predecessor({g.es[e]['label']})")

            # -- Successors (users with sessions on this computer)
            for e in g.incident(comp_vid, mode="out"):
                tgt_vid = g.es[e].target
                if "User" not in vertex_labels[tgt_vid]:
                    continue
                if g.es[e]["label"] == "HasSession":
                    uname = vertex_names[tgt_vid]
                    reachable_users.add(f"{uname} - successor(HasSession)")

        # ---- Compute deltas vs previous iteration ----
        prev_metrics = misconfig_growth_metrics.get(misconfig_session_count - 1, {})
        prev_users = set(prev_metrics.get("reachable_users", []))
        prev_comps = set(prev_metrics.get("reachable_comps_names", []))

        new_users = reachable_users - prev_users
        new_comps = set(reachable_comps_names) - prev_comps

        # ---- Store metrics ----
        m = misconfig_growth_metrics.setdefault(misconfig_session_count, {})
        m["reachable_users"] = list(reachable_users)
        m["new_reachable_users"] = list(new_users)
        m["reachable_comps"] = list(reachable_comps)
        m["reachable_comps_names"] = list(reachable_comps_names)
        m["new_reachable_comps_names"] = list(new_comps)
        m["reachable_users_count"] = len(reachable_users)
        m["reachable_comps_count"] = len(reachable_comps)
