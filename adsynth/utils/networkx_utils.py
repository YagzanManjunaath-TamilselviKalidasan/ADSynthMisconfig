import json
import os
from datetime import datetime
import tempfile
import networkx as nx

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


def print_all_nodes(graph):
    print("All nodes in graph:")
    for node_id, attrs in graph.nodes(data=True):
        print(f"ID: {node_id}, name: {attrs.get('name')}, displayname: {attrs.get('displayname')}")


def get_id_from_name(graph, name):
    for node_id, attrs in graph.nodes(data=True):
        if attrs.get("name") == name:
            return node_id
    return None


def find_user_count_with_path_to_DA(networkx_graph, domain_grp_name, misconfig_session_count, misconfig_growth_metrics):
    domain_grp_id = get_id_from_name(networkx_graph, domain_grp_name)
    if domain_grp_id not in networkx_graph:
        return

    lengths = nx.single_target_shortest_path_length(networkx_graph, domain_grp_id)
    reachable_nodes = set(lengths.keys())


    comp_id_map = {c: get_id_from_name(networkx_graph, c) for c in EXP_COMPUTERS}
    reachable_comps = {cid for cid in comp_id_map.values() if cid in reachable_nodes}

    reachable_users = set()

    exploitable_permissions = ["AdminTo", "CanRDP", "CanPSRemote", "ExecuteDCOM", "AllowedToDelegate",
                               "ReadLAPSPassword", "SQLAdmin",
                               "AllowedToAct"]

    for comp_id in reachable_comps:
        for u in networkx_graph.predecessors(comp_id):
            if ("User" in networkx_graph.nodes[u].get("labels", [])
                    and networkx_graph.edges[u, comp_id].get("label") in exploitable_permissions):
                reachable_users.add(u)
        for v in networkx_graph.successors(comp_id):
            if (
                "User" in networkx_graph.nodes[v].get("labels", [])
                and networkx_graph.edges[comp_id, v].get("label") == "HasSession"
            ):
                reachable_users.add(v)



    if misconfig_session_count not in misconfig_growth_metrics:
        misconfig_growth_metrics[misconfig_session_count] = {}

    misconfig_growth_metrics[misconfig_session_count]["reachable_users"] = list(reachable_users)
    misconfig_growth_metrics[misconfig_session_count]["reachable_comps"] = list(reachable_comps)
    misconfig_growth_metrics[misconfig_session_count]["reachable_users_count"] = len(reachable_users)
    misconfig_growth_metrics[misconfig_session_count]["reachable_comps_count"] = len(reachable_comps)




def find_user_count_with_path_to_DA_undirected(networkx_graph, domain_grp_name, misconfig_session_count, misconfig_growth_metrics):
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
