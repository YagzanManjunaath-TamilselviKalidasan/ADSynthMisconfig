import math
import re
from typing import List, Optional, Dict

import numpy as np
import pandas as pd

from adsynth.DATABASE import NODES, PAW_TIERS, S_TIERS_LOCATIONS, S_TIERS, ENABLED_USERS, ADMIN_USERS, WS_TIERS, \
    WS_TIERS_LOCATIONS, USER_TIER, COMPUTER_TIER, EDGES, ALL_LOW_TIER_COMPUTERS,TOTAL_T0_USERS,ID_TO_NAME
from adsynth.EXPERIMENT_DATABASE import EXP_EDGES
import adsynth.DATABASE as DB
from collections import Counter
from scipy.stats import t

def populate_node_tiers():
    DB.USER_TIER.clear()
    DB.COMPUTER_TIER.clear()

    for tier, users in enumerate(DB.ADMIN_USERS):
        for user in users:
            DB.USER_TIER[user] = tier

    for tier, users in enumerate(DB.ENABLED_USERS):
        for user in users:
            DB.USER_TIER.setdefault(user, tier)

    for tier, servers in enumerate(DB.S_TIERS):
        for server in servers:
            DB.COMPUTER_TIER[server] = tier

    for tier, paws in enumerate(DB.PAW_TIERS):
        for paw in paws:
            DB.COMPUTER_TIER[paw] = tier

    for tier, ws_list in enumerate(DB.WS_TIERS):
        for ws in ws_list:
            DB.COMPUTER_TIER[ws] = tier
def build_tier_caches(low_tiers=None, tier0_value=0):
    if low_tiers is None:
        low_tiers = {2}

    DB.ID_TO_NAME.clear()
    DB.ALL_LOW_TIER_COMPUTERS.clear()

    seen_t0_users = set()

    for node in DB.NODES:
        node_id = node.get("id")
        props = node.get("properties", {})
        name = props.get("name")

        if not node_id or not name:
            continue

        DB.ID_TO_NAME[node_id] = name

        if name in DB.USER_TIER and DB.USER_TIER[name] == tier0_value:
            seen_t0_users.add(name)

        if name in DB.COMPUTER_TIER and DB.COMPUTER_TIER[name] in low_tiers:
            DB.ALL_LOW_TIER_COMPUTERS.add(node_id)

    DB.TOTAL_T0_USERS = len(seen_t0_users)
def get_baseline_from_AD(misconfig_type, TARGET_LABELS):



    # Modifying to choose all edges

    CP = [
        "AdminTo", "CanRDP", "CanPSRemote", "ExecuteDCOM",
        "AllowedToDelegate", "ReadLAPSPassword", "SQLAdmin", "AllowedToAct"
    ]

    ACLS_LIST = [
        "AllExtendedRights", "GenericAll", "GenericWrite", "WriteOwner",
        "WriteDacl", "ForceChangePassword", "AddSelf", "AddMember"
    ]

    NON_ACLS_LIST = [
        "CanRDP", "ExecuteDCOM", "AllowedToDelegate",
        "ReadLAPSPassword", "CanPSRemote"
    ]

    ALL_INJECTION_LABELS = set(ACLS_LIST) | set(CP) | set(NON_ACLS_LIST) | {
        "MemberOf",
        "HasSession"
    }
    return sum(
        1 for edge in EDGES
        if edge.get("label") in ALL_INJECTION_LABELS
    )
    # if misconfig_type == "session":
    #     baseline_has_session = sum(1 for edge in EDGES if edge.get("label") == "HasSession")
    #     return baseline_has_session
    # elif misconfig_type == "i_perm" or misconfig_type == "g_perm":
    #     baseline_edges = [
    #         edge for edge in EDGES
    #         if edge.get("label") in TARGET_LABELS
    #     ]
    #     return len(baseline_edges)
    # elif misconfig_type == "nesting":
    #     baseline_member_of = sum(1 for edge in EDGES if edge.get("label") == "MemberOf")
    #     return baseline_member_of


def comp_tier_fn(node_name_or_id: str, labels=()) -> int:
    try:
        s = next((x for x in NODES if x["id"] == node_name_or_id), None)

        name = s["properties"]["name"]
        return COMPUTER_TIER[name]
    # todo check
    except KeyError:
        return -1


def user_tier_fn(dn: str):

    try:
        s = next((x for x in NODES if x["id"] == dn), None)

        name = s["properties"]["name"]
        return USER_TIER[name]
    # todo check
    except KeyError:
        return -1
    # if not dn:
    #     return None
    # m = re.search(r"OU=T(\d+)\b", dn, flags=re.IGNORECASE)
    # return int(m.group(1)) if m else 2


def indicators_hci_csm_tbs(
    EXP_EDGE,
    misconfig_growth_metrics,
    misconfig_session_count,
    num_users,
    TOTAL_T0_USERS,
    low_tiers=None,
    eps=1.0,
):
    if low_tiers is None:
        low_tiers = {2}

    has_session_edges = [e for e in EXP_EDGE if e.get("label") == "HasSession"]

    d_sess = Counter(str(e["start"]["id"]) for e in has_session_edges)

    # Prefer all cached low-tier computers; fall back to active low-tier computers only
    if ALL_LOW_TIER_COMPUTERS:
        C_low = {str(c) for c in ALL_LOW_TIER_COMPUTERS if comp_tier_fn(str(c)) in low_tiers}
    else:
        C_low = {c for c in d_sess.keys() if comp_tier_fn(c) in low_tiers}

    # HCI
    if not C_low:
        HCI = 0.0
    else:
        dbar = sum(d_sess.get(c, 0) for c in C_low) / len(C_low)
        denom = (dbar + eps) ** 2
        HCI = (1 / len(C_low)) * sum((d_sess.get(c, 0) ** 2) / denom for c in C_low)

    cross = 0
    t0_cross = 0

    for e in has_session_edges:
        c = str(e["start"]["id"])
        u = str(e["end"]["id"])

        t_c = comp_tier_fn(c)
        t_u = user_tier_fn(u)

        if t_c == -1 or t_u == -1:
            continue


        if t_u < t_c:
            cross += 1
            if t_u == 0 and t_c > 0:
                t0_cross += 1

    # CSM = cross-tier session mass / total users
    CSM = cross / num_users if num_users else 0.0

    # TBS = Tier 0 boundary-violating sessions / total Tier 0 users
    TBS = t0_cross / TOTAL_T0_USERS if TOTAL_T0_USERS else 0.0

    misconfig_growth_metrics[misconfig_session_count]["HCI"] = HCI
    misconfig_growth_metrics[misconfig_session_count]["CSM"] = CSM
    misconfig_growth_metrics[misconfig_session_count]["TBS"] = TBS

def exposure_X(reachable_users_count, reachable_comps_count, num_users, num_computers):
    denom = num_users + num_computers
    return (reachable_users_count + reachable_comps_count) / denom if denom else 0.0

def exposure_users(reachable_users_count, num_users):
    return reachable_users_count / num_users if num_users else 0.0

def exposure_computers(reachable_comps_count, num_computers):
    return reachable_comps_count / num_computers if num_computers else 0.0

def exposure_parts(reachable_users_count, reachable_comps_count, num_users, num_computers):
    Xu = reachable_users_count / num_users if num_users else 0.0
    Xc = reachable_comps_count / num_computers if num_computers else 0.0
    return Xu, Xc


def exposure_per_baseline_session(X, N_baseline_session):
    return X / N_baseline_session if N_baseline_session else 0.0


from collections import deque, Counter
import networkx as nx


def get_id_from_name(G, target_name):
    """
    Return node id whose 'name' attribute matches target_name.
    """
    for node_id, data in G.nodes(data=True):
        if data.get("name") == target_name:
            return node_id
    return None


def get_edge_labels(G, u, v):
    """
    Return all edge labels between u and v.
    Supports DiGraph and MultiDiGraph.
    """
    edge_data = G.get_edge_data(u, v)
    if not edge_data:
        return []

    # MultiDiGraph case: {edge_key: {attr_dict}}
    if G.is_multigraph():
        labels = []
        for _, attrs in edge_data.items():
            if isinstance(attrs, dict):
                label = attrs.get("label")
                if label:
                    labels.append(label)
        return labels

    # DiGraph case: {attr_dict}
    label = edge_data.get("label")
    return [label] if label else []


def pbcc_bounded_bfs_footholds(
        networkx_graph,
        foothold_names,
        high_value_target_name,
        L=10,
        allowed_edge_labels=None,
        session_edge_labels=None,
):
    if allowed_edge_labels is None:
        allowed_edge_labels = {
            "HasSession",
            "AdminTo",
            "CanRDP",
            "CanPSRemote",
            "ExecuteDCOM",
            "AllowedToDelegate",
            "ReadLAPSPassword",
            "SQLAdmin",
            "AllowedToAct",
            "MemberOf",
        }

    if session_edge_labels is None:
        session_edge_labels = {"HasSession"}

    target_id = get_id_from_name(networkx_graph, high_value_target_name)
    if target_id is None or target_id not in networkx_graph:
        return {
            "pbcc": 0.0,
            "b": {},
            "bridge_hits": {},
            "successful_paths": 0,
            "target_id": None,
            "foothold_ids": [],
            "error": f"Target not found: {high_value_target_name}",
        }

    foothold_ids = []
    for name in foothold_names:
        nid = get_id_from_name(networkx_graph, name)
        if nid is not None and nid in networkx_graph:
            foothold_ids.append(nid)

    if not foothold_ids:
        return {
            "pbcc": 0.0,
            "b": {},
            "bridge_hits": {},
            "successful_paths": 0,
            "target_id": target_id,
            "foothold_ids": [],
            "error": "No valid footholds found",
        }

    bridge_counter = Counter()
    successful_paths = 0

    for src in foothold_ids:
        # state: (node, depth, seen_session, seen_non_session, path_nodes)
        q = deque([(src, 0, False, False, [src])])

        # compact dedup state to avoid explosion
        visited = {(src, 0, False, False)}

        while q:
            node, depth, seen_sess, seen_non_sess, path_nodes = q.popleft()

            # successful mixed-type bounded foothold -> target path
            if (node == target_id) :
                    # and seen_sess and seen_non_sess)\

                successful_paths += 1

                # interior nodes only: exclude foothold and target
                interior_nodes = path_nodes[1:-1]
                for n in set(interior_nodes):
                    bridge_counter[n] += 1
                continue

            if depth >= L:
                continue

            for nbr in networkx_graph.successors(node):
                edge_labels = get_edge_labels(networkx_graph, node, nbr)
                if not edge_labels:
                    continue

                valid_labels = [lab for lab in edge_labels if lab in allowed_edge_labels]
                if not valid_labels:
                    continue

                # explore state transition for each relevant edge label
                for lab in valid_labels:
                    next_seen_sess = seen_sess or (lab in session_edge_labels)
                    next_seen_non_sess = seen_non_sess or (lab not in session_edge_labels)

                    state = (nbr, depth + 1, next_seen_sess, next_seen_non_sess)
                    if state in visited:
                        continue

                    visited.add(state)
                    q.append(
                        (
                            nbr,
                            depth + 1,
                            next_seen_sess,
                            next_seen_non_sess,
                            path_nodes + [nbr],
                        )
                    )

    if successful_paths == 0:
        return {
            "pbcc": 0.0,
            "b": {},
            "bridge_hits": {},
            "successful_paths": 0,
            "target_id": target_id,
            "foothold_ids": foothold_ids,
        }

    b = {node: cnt / successful_paths for node, cnt in bridge_counter.items()}
    pbcc = sum(val * val for val in b.values())

    return {
        "pbcc": pbcc,
        "b": dict(sorted(b.items(), key=lambda x: x[1], reverse=True)),
        "bridge_hits": dict(sorted(bridge_counter.items(), key=lambda x: x[1], reverse=True)),
        "successful_paths": successful_paths,
        "target_id": target_id,
        "foothold_ids": foothold_ids,
    }


from collections import Counter, deque
from collections import Counter, deque, defaultdict
from collections import Counter, deque

def pbcc_bounded_bfs_tier2_computers_debug(
    networkx_graph,
    high_value_target_name,
    L=4,
    foothold_tier=2,
    allowed_edge_labels=None,
    session_edge_labels=None,
    max_example_paths_per_type=5,
):

    if allowed_edge_labels is None:
        allowed_edge_labels = {
            "HasSession",
            "AdminTo",
            "CanRDP",
            "CanPSRemote",
            "ExecuteDCOM",
            "AllowedToDelegate",
            "ReadLAPSPassword",
            "SQLAdmin",
            "AllowedToAct",
            "MemberOf",
        }

    if session_edge_labels is None:
        session_edge_labels = {"HasSession"}

    def node_name(n):
        return networkx_graph.nodes[n].get("name", n)

    def classify_path(seen_sess, seen_non_sess):
        if seen_sess and seen_non_sess:
            return "mixed"
        elif seen_sess:
            return "session_only"
        elif seen_non_sess:
            return "non_session_only"
        return "unknown"

    def edge_labels_between(u, v):
        labs = get_edge_labels(networkx_graph, u, v)
        return labs if labs else []

    # Target
    target_id = get_id_from_name(networkx_graph, high_value_target_name)
    if target_id is None or target_id not in networkx_graph:
        return {
            "pbcc": 0.0,
            "b": {},
            "bridge_hits": {},
            "successful_paths": 0,
            "target_id": None,
            "foothold_ids": [],
            "error": f"Target not found: {high_value_target_name}",
        }

    # Tier-2 computer footholds
    foothold_ids = []
    foothold_names_valid = []

    for nid in networkx_graph.nodes:
        name = node_name(nid)
        if COMPUTER_TIER.get(name, -1) == foothold_tier:
            foothold_ids.append(nid)
            foothold_names_valid.append(name)

    if not foothold_ids:
        return {
            "pbcc": 0.0,
            "b": {},
            "bridge_hits": {},
            "successful_paths": 0,
            "target_id": target_id,
            "target_name": node_name(target_id),
            "foothold_ids": [],
            "foothold_names_valid": [],
            "error": f"No Tier-{foothold_tier} computer footholds found",
        }

    bridge_counter = Counter()
    successful_paths = 0

    path_type_counts = Counter()
    path_type_examples = {
        "mixed": [],
        "session_only": [],
        "non_session_only": [],
        "unknown": [],
    }

    foothold_debug = {}

    # Global graph label stats
    graph_label_counter = Counter()
    for u, v in networkx_graph.edges():
        for lab in edge_labels_between(u, v):
            graph_label_counter[lab] += 1

    for src in foothold_ids:
        src_name = node_name(src)

        q = deque([(src, 0, False, False, [src], [])])
        # state = (node, depth, seen_sess, seen_non_sess)
        visited = {(src, 0, False, False)}

        reached_target_any = 0
        reached_target_by_type = Counter()

        expanded_states = 0
        pruned_depth = 0
        pruned_no_labels = 0
        pruned_no_allowed_labels = 0

        seen_any_session_edge = False
        seen_any_non_session_edge = False

        max_depth_reached = 0

        while q:
            node, depth, seen_sess, seen_non_sess, path_nodes, path_edge_labels = q.popleft()
            expanded_states += 1
            max_depth_reached = max(max_depth_reached, depth)

            if node == target_id:
                ptype = classify_path(seen_sess, seen_non_sess)
                reached_target_any += 1
                reached_target_by_type[ptype] += 1
                path_type_counts[ptype] += 1

                if len(path_type_examples[ptype]) < max_example_paths_per_type:
                    path_type_examples[ptype].append({
                        "source": src_name,
                        "depth": depth,
                        "nodes": [node_name(n) for n in path_nodes],
                        "edge_labels": list(path_edge_labels),
                    })

                # PBCC counts only mixed paths as bridge-forming paths
                if ptype == "mixed":
                    successful_paths += 1
                    interior_nodes = path_nodes[1:-1]
                    for n in set(interior_nodes):
                        bridge_counter[n] += 1

                continue

            if depth >= L:
                pruned_depth += 1
                continue

            for nbr in networkx_graph.successors(node):
                edge_labels = edge_labels_between(node, nbr)
                if not edge_labels:
                    pruned_no_labels += 1
                    continue

                valid_labels = [lab for lab in edge_labels if lab in allowed_edge_labels]
                if not valid_labels:
                    pruned_no_allowed_labels += 1
                    continue

                for lab in valid_labels:
                    if lab in session_edge_labels:
                        seen_any_session_edge = True
                    else:
                        seen_any_non_session_edge = True

                    next_seen_sess = seen_sess or (lab in session_edge_labels)
                    next_seen_non_sess = seen_non_sess or (lab not in session_edge_labels)

                    state = (nbr, depth + 1, next_seen_sess, next_seen_non_sess)
                    if state in visited:
                        continue

                    visited.add(state)
                    q.append((
                        nbr,
                        depth + 1,
                        next_seen_sess,
                        next_seen_non_sess,
                        path_nodes + [nbr],
                        path_edge_labels + [lab],
                    ))

        # Explain foothold outcome
        if reached_target_any == 0:
            if max_depth_reached >= L:
                reason = f"target_not_reached_within_bound_L={L}"
            else:
                reason = "target_not_reachable_under_allowed_edges"
        elif reached_target_by_type["mixed"] == 0:
            if reached_target_by_type["session_only"] > 0 and reached_target_by_type["non_session_only"] > 0:
                reason = "target_reached_but_no_single_path_contains_both_session_and_non_session_edges"
            elif reached_target_by_type["session_only"] > 0:
                reason = "target_reached_only_via_session_only_paths"
            elif reached_target_by_type["non_session_only"] > 0:
                reason = "target_reached_only_via_non_session_only_paths"
            else:
                reason = "target_reached_but_no_mixed_path"
        else:
            reason = "success"

        foothold_debug[src_name] = {
            "src_id": src,
            "reached_target_any": reached_target_any,
            "reached_target_by_type": dict(reached_target_by_type),
            "seen_any_session_edge_during_search": seen_any_session_edge,
            "seen_any_non_session_edge_during_search": seen_any_non_session_edge,
            "expanded_states": expanded_states,
            "visited_states": len(visited),
            "max_depth_reached": max_depth_reached,
            "pruned_depth": pruned_depth,
            "pruned_no_labels": pruned_no_labels,
            "pruned_no_allowed_labels": pruned_no_allowed_labels,
            "reason": reason,
        }

    if successful_paths == 0:
        return {
            "pbcc": 0.0,
            "b": {},
            "bridge_hits": {},
            "successful_paths": 0,
            "target_id": target_id,
            "target_name": node_name(target_id),
            "foothold_ids": foothold_ids,
            "foothold_names_valid": foothold_names_valid,
            "path_type_counts": dict(path_type_counts),
            "path_type_examples": path_type_examples,
            "foothold_debug": foothold_debug,
            "graph_label_counts": dict(graph_label_counter),
            "allowed_edge_labels": sorted(allowed_edge_labels),
            "session_edge_labels": sorted(session_edge_labels),
            "failure_summary": "No mixed bounded Tier-2-computer -> target paths found, so PBCC = 0",
        }

    b = {node: cnt / successful_paths for node, cnt in bridge_counter.items()}
    pbcc = sum(val * val for val in b.values())

    return {
        "pbcc": pbcc,
        "b": {
            node_name(node): val
            for node, val in sorted(b.items(), key=lambda x: x[1], reverse=True)
        },
        "bridge_hits": {
            node_name(node): cnt
            for node, cnt in sorted(bridge_counter.items(), key=lambda x: x[1], reverse=True)
        },
        "successful_paths": successful_paths,
        "target_id": target_id,
        "target_name": node_name(target_id),
        "foothold_ids": foothold_ids,
        "foothold_names_valid": foothold_names_valid,
        "path_type_counts": dict(path_type_counts),
        "path_type_examples": path_type_examples,
        "foothold_debug": foothold_debug,
        "graph_label_counts": dict(graph_label_counter),
        "allowed_edge_labels": sorted(allowed_edge_labels),
        "session_edge_labels": sorted(session_edge_labels),
    }
def pbcc_bounded_bfs_footholds_debug(
    networkx_graph,
    foothold_names,
    high_value_target_name,
    L=4,
    allowed_edge_labels=None,
    session_edge_labels=None,
    max_example_paths_per_type=5,
):
    """
    Debug-friendly PBCC computation.

    Reports:
    - reachable target paths by type
    - session-only / non-session-only / mixed counts
    - exact top bridge nodes
    - why each foothold failed
    """

    if allowed_edge_labels is None:
        allowed_edge_labels = {
            "HasSession",
            "AdminTo",
            "CanRDP",
            "CanPSRemote",
            "ExecuteDCOM",
            "AllowedToDelegate",
            "ReadLAPSPassword",
            "SQLAdmin",
            "AllowedToAct",
            "MemberOf",
        }

    if session_edge_labels is None:
        session_edge_labels = {"HasSession"}

    def node_name(n):
        return networkx_graph.nodes[n].get("name", n)

    def classify_path(seen_sess, seen_non_sess):
        if seen_sess and seen_non_sess:
            return "mixed"
        elif seen_sess:
            return "session_only"
        elif seen_non_sess:
            return "non_session_only"
        return "unknown"

    def edge_labels_between(u, v):
        labs = get_edge_labels(networkx_graph, u, v)
        return labs if labs else []

    target_id = get_id_from_name(networkx_graph, high_value_target_name)
    if target_id is None or target_id not in networkx_graph:
        return {
            "pbcc": 0.0,
            "b": {},
            "bridge_hits": {},
            "successful_paths": 0,
            "target_id": None,
            "foothold_ids": [],
            "error": f"Target not found: {high_value_target_name}",
        }

    foothold_ids = []
    invalid_footholds = []
    for name in foothold_names:
        nid = get_id_from_name(networkx_graph, name)
        if nid is not None and nid in networkx_graph:
            foothold_ids.append(nid)
        else:
            invalid_footholds.append(name)

    if not foothold_ids:
        return {
            "pbcc": 0.0,
            "b": {},
            "bridge_hits": {},
            "successful_paths": 0,
            "target_id": target_id,
            "foothold_ids": [],
            "invalid_footholds": invalid_footholds,
            "error": "No valid footholds found",
        }

    bridge_counter = Counter()
    successful_paths = 0

    path_type_counts = Counter()
    path_type_examples = {
        "mixed": [],
        "session_only": [],
        "non_session_only": [],
        "unknown": [],
    }

    foothold_debug = {}

    # global graph label stats
    graph_label_counter = Counter()
    for u, v in networkx_graph.edges():
        for lab in edge_labels_between(u, v):
            graph_label_counter[lab] += 1

    for src in foothold_ids:
        src_name = node_name(src)

        q = deque([(src, 0, False, False, [src], [])])
        # state = (node, depth, seen_sess, seen_non_sess)
        visited = {(src, 0, False, False)}

        reached_target_any = 0
        reached_target_by_type = Counter()

        expanded_states = 0
        pruned_depth = 0
        pruned_no_labels = 0
        pruned_no_allowed_labels = 0

        seen_any_session_edge = False
        seen_any_non_session_edge = False

        max_depth_reached = 0

        while q:
            node, depth, seen_sess, seen_non_sess, path_nodes, path_edge_labels = q.popleft()
            expanded_states += 1
            max_depth_reached = max(max_depth_reached, depth)

            if node == target_id:
                ptype = classify_path(seen_sess, seen_non_sess)
                reached_target_any += 1
                reached_target_by_type[ptype] += 1
                path_type_counts[ptype] += 1

                if len(path_type_examples[ptype]) < max_example_paths_per_type:
                    path_type_examples[ptype].append({
                        "source": src_name,
                        "depth": depth,
                        "nodes": [node_name(n) for n in path_nodes],
                        "edge_labels": list(path_edge_labels),
                    })

                if ptype == "mixed":
                    successful_paths += 1
                    interior_nodes = path_nodes[1:-1]
                    for n in set(interior_nodes):
                        bridge_counter[n] += 1

                # continue is fine; no need to expand beyond target for this metric
                continue

            if depth >= L:
                pruned_depth += 1
                continue

            for nbr in networkx_graph.successors(node):
                edge_labels = edge_labels_between(node, nbr)
                if not edge_labels:
                    pruned_no_labels += 1
                    continue

                valid_labels = [lab for lab in edge_labels if lab in allowed_edge_labels]
                if not valid_labels:
                    pruned_no_allowed_labels += 1
                    continue

                for lab in valid_labels:
                    if lab in session_edge_labels:
                        seen_any_session_edge = True
                    else:
                        seen_any_non_session_edge = True

                    next_seen_sess = seen_sess or (lab in session_edge_labels)
                    next_seen_non_sess = seen_non_sess or (lab not in session_edge_labels)

                    state = (nbr, depth + 1, next_seen_sess, next_seen_non_sess)
                    if state in visited:
                        continue

                    visited.add(state)
                    q.append((
                        nbr,
                        depth + 1,
                        next_seen_sess,
                        next_seen_non_sess,
                        path_nodes + [nbr],
                        path_edge_labels + [lab],
                    ))

        # explain foothold outcome
        if reached_target_any == 0:
            if max_depth_reached >= L:
                reason = f"target_not_reached_within_bound_L={L}"
            else:
                reason = "target_not_reachable_under_allowed_edges"
        elif reached_target_by_type["mixed"] == 0:
            if reached_target_by_type["session_only"] > 0 and reached_target_by_type["non_session_only"] > 0:
                reason = "target_reached_but_no_single_path_contains_both_session_and_non_session_edges"
            elif reached_target_by_type["session_only"] > 0:
                reason = "target_reached_only_via_session_only_paths"
            elif reached_target_by_type["non_session_only"] > 0:
                reason = "target_reached_only_via_non_session_only_paths"
            else:
                reason = "target_reached_but_no_mixed_path"
        else:
            reason = "success"

        foothold_debug[src_name] = {
            "src_id": src,
            "reached_target_any": reached_target_any,
            "reached_target_by_type": dict(reached_target_by_type),
            "seen_any_session_edge_during_search": seen_any_session_edge,
            "seen_any_non_session_edge_during_search": seen_any_non_session_edge,
            "expanded_states": expanded_states,
            "visited_states": len(visited),
            "max_depth_reached": max_depth_reached,
            "pruned_depth": pruned_depth,
            "pruned_no_labels": pruned_no_labels,
            "pruned_no_allowed_labels": pruned_no_allowed_labels,
            "reason": reason,
        }

    if successful_paths == 0:
        return {
            "pbcc": 0.0,
            "b": {},
            "bridge_hits": {},
            "successful_paths": 0,
            "target_id": target_id,
            "target_name": node_name(target_id),
            "foothold_ids": foothold_ids,
            "foothold_names_valid": [node_name(n) for n in foothold_ids],
            "invalid_footholds": invalid_footholds,
            "path_type_counts": dict(path_type_counts),
            "path_type_examples": path_type_examples,
            "foothold_debug": foothold_debug,
            "graph_label_counts": dict(graph_label_counter),
            "allowed_edge_labels": sorted(allowed_edge_labels),
            "session_edge_labels": sorted(session_edge_labels),
            "failure_summary": "No mixed bounded foothold->target paths found, so PBCC = 0",
        }

    b = {node: cnt / successful_paths for node, cnt in bridge_counter.items()}
    pbcc = sum(val * val for val in b.values())

    return {
        "pbcc": pbcc,
        "b": {
            node_name(node): val
            for node, val in sorted(b.items(), key=lambda x: x[1], reverse=True)
        },
        "bridge_hits": {
            node_name(node): cnt
            for node, cnt in sorted(bridge_counter.items(), key=lambda x: x[1], reverse=True)
        },
        "successful_paths": successful_paths,
        "target_id": target_id,
        "target_name": node_name(target_id),
        "foothold_ids": foothold_ids,
        "foothold_names_valid": [node_name(n) for n in foothold_ids],
        "invalid_footholds": invalid_footholds,
        "path_type_counts": dict(path_type_counts),
        "path_type_examples": path_type_examples,
        "foothold_debug": foothold_debug,
        "graph_label_counts": dict(graph_label_counter),
        "allowed_edge_labels": sorted(allowed_edge_labels),
        "session_edge_labels": sorted(session_edge_labels),
    }
def compute_delta_X(misconfig_growth_metrics):
    steps = sorted(misconfig_growth_metrics.keys())

    misconfig_growth_metrics[steps[0]]["delta_X"] = 0.0
    for i in range(1, len(steps)):
        curr = steps[i]
        prev = steps[i - 1]

        Xi = misconfig_growth_metrics[curr]["X"]
        Xi_prev = misconfig_growth_metrics[prev]["X"]

        delta = Xi - Xi_prev

        misconfig_growth_metrics[curr]["delta_X"] = delta
    return misconfig_growth_metrics


def find_p_max_delta(misconfig_growth_metrics):
    max_jump = -float("inf")
    p_star = None

    for step, m in misconfig_growth_metrics.items():

        delta = m.get("delta_X", 0)

        if delta > max_jump:
            max_jump = delta
            p_star = m["p"]

    return p_star


def compute_hub_correlation(misconfig_growth_metrics):
    HCI = []
    deltaX = []

    for step, m in misconfig_growth_metrics.items():

        if "delta_X" not in m:
            continue

        HCI.append(m["HCI"])
        deltaX.append(m["delta_X"])

    if len(HCI) < 2 or np.std(HCI) == 0 or np.std(deltaX) == 0:
        return 0
    corr = np.corrcoef(HCI, deltaX)[0, 1]

    return corr


def compute_mu(metrics_for_all_runs, metric):
    mu = {}

    steps = sorted(metrics_for_all_runs[0].keys())

    for step in steps:
        p = metrics_for_all_runs[0][step]["p"]

        X_vals = [metrics_for_all_runs[r][step][metric] for r in metrics_for_all_runs]

        mu[p] = np.mean(X_vals)

    return mu


def compute_sigma2(metrics_for_all_runs, metric):
    sigma2 = {}

    steps = sorted(metrics_for_all_runs[0].keys())

    for step in steps:
        p = metrics_for_all_runs[0][step]["p"]

        X_vals = [metrics_for_all_runs[r][step][metric] for r in metrics_for_all_runs]

        sigma2[p] = np.var(X_vals, ddof=1) if len(X_vals) > 1 else 0.0
    return sigma2


def compute_mu_sigma_ci(values, confidence=0.95):
    values = np.array(values)
    R = len(values)

    mu = np.mean(values)
    sigma2 = np.var(values, ddof=1)

    s = np.sqrt(sigma2)

    t_val = t.ppf((1 + confidence) / 2, R - 1)

    margin = t_val * s / np.sqrt(R)

    ci_low = mu - margin
    ci_high = mu + margin

    return mu, sigma2, ci_low, ci_high


def compute_p_star_ci(p_star_values):
    p_star_values = np.array(p_star_values)

    if not p_star_values:
        mean_p_star = 0.0
    else:
        mean_p_star = float(np.mean(p_star_values))


    ci_low = np.percentile(p_star_values, 2.5)
    ci_high = np.percentile(p_star_values, 97.5)

    return mean_p_star, ci_low, ci_high


def is_valid_number(x):
    return x is not None and not (isinstance(x, float) and math.isnan(x))


def safe_mean(values: List[float]) -> Optional[float]:
    values = [float(v) for v in values if is_valid_number(v)]
    if not values:
        return None
    return float(np.mean(values))


def safe_std(values: List[float], ddof: int = 0) -> Optional[float]:
    values = [float(v) for v in values if is_valid_number(v)]
    if not values:
        return None
    if len(values) == 1:
        return 0.0
    return float(np.std(values, ddof=ddof))


def safe_var(values: List[float], ddof: int = 0) -> Optional[float]:
    values = [float(v) for v in values if is_valid_number(v)]
    if not values:
        return None
    if len(values) == 1:
        return 0.0
    return float(np.var(values, ddof=ddof))


def safe_percentile(values: List[float], q: float) -> Optional[float]:
    values = [float(v) for v in values if is_valid_number(v)]
    if not values:
        return None
    return float(np.percentile(values, q))


def get_baseline_segment(
    metrics,
    baseline_fraction: float = 0.2,
    min_points: int = 5
):
    if not metrics:
        return []

    if isinstance(metrics, dict):
        rows = [metrics[k] for k in sorted(metrics.keys())]
    else:
        rows = list(metrics)

    n = len(rows)
    cutoff = max(min_points, int(math.ceil(n * baseline_fraction)))
    cutoff = min(cutoff, n)

    return rows[:cutoff]

def estimate_indicator_thresholds(
    metrics: List[Dict],
    baseline_fraction: float = 0.2,
    min_points: int = 5
) -> Dict[str, Optional[float]]:

    # 20% of runs or 5 runs - whichever is max
    baseline = get_baseline_segment(metrics, baseline_fraction, min_points)


    hci_vals = [row.get("HCI") for row in baseline if is_valid_number(row.get("HCI"))]
    csm_vals = [row.get("CSM") for row in baseline if is_valid_number(row.get("CSM"))]
    pbcc_vals = [row.get("PBCC") for row in baseline if is_valid_number(row.get("PBCC"))]

    mu_hci = safe_mean(hci_vals)
    sigma_hci = safe_std(hci_vals, ddof=0)

    mu_pbcc = safe_mean(pbcc_vals)
    sigma_pbcc = safe_std(pbcc_vals, ddof=0)

    # as per 1.3 -> mu_hci + 2 sigma_hci

    tau_hci = None if mu_hci is None or sigma_hci is None else mu_hci + 2 * sigma_hci
    # as per 1.3 -> 90th percentile
    tau_csm = safe_percentile(csm_vals, 90)
    tau_tbs = 0.0
    tau_pbcc = None if mu_pbcc is None or sigma_pbcc is None else mu_pbcc + 2 * sigma_pbcc

    return {
        "tau_HCI": tau_hci,
        "tau_CSM": tau_csm,
        "tau_TBS": tau_tbs,
        "tau_PBCC": tau_pbcc,
        "mu_HCI": mu_hci,
        "sigma_HCI": sigma_hci,
        "mu_PBCC": mu_pbcc,
        "sigma_PBCC": sigma_pbcc,
    }
def minmax_normalize_series(series):
    s = pd.to_numeric(series, errors="coerce")
    if s.dropna().empty:
        return s
    s_min = s.min()
    s_max = s.max()
    if pd.isna(s_min) or pd.isna(s_max):
        return s
    if math.isclose(s_min, s_max):
        return pd.Series([0.0] * len(s), index=s.index)
    return (s - s_min) / (s_max - s_min)


def add_rise_period_metrics(metrics_dict, metric_keys):
    steps = sorted(metrics_dict.keys())

    streaks = {k: 0 for k in metric_keys}
    totals = {k: 0 for k in metric_keys}
    prev_vals = {k: None for k in metric_keys}

    for step in steps:
        row = metrics_dict[step]

        for k in metric_keys:
            curr = row.get(k)

            if not isinstance(curr, (int, float)):
                row[f"rise_flag_{k}"] = None
                row[f"rise_streak_{k}"] = None
                row[f"rise_total_{k}"] = totals[k]
                continue

            prev = prev_vals[k]

            if isinstance(prev, (int, float)) and curr > prev:
                streaks[k] += 1
                totals[k] += 1
                row[f"rise_flag_{k}"] = 1
            else:
                streaks[k] = 0
                row[f"rise_flag_{k}"] = 0

            row[f"rise_streak_{k}"] = streaks[k]
            row[f"rise_total_{k}"] = totals[k]
            prev_vals[k] = curr

    return metrics_dict

import os
import pandas as pd

def rows_from_run_metrics(
    run_metrics: Dict,
    itr: int,
    base_filename: str,
    seed_number: int,
    injection_type: str = "session",
    mode: str = "isolated",
):
    rows = []
    for step in sorted(run_metrics.keys()):
        row = dict(run_metrics[step])
        row["run"] = itr
        row["seed_number"] = seed_number
        row["graph_base"] = base_filename
        row["injection_type"] = injection_type
        row["mode"] = mode
        row["step"] = step
        rows.append(row)
    return rows

def save_iteration_csv(rows, out_dir, base_filename, itr):
    os.makedirs(out_dir, exist_ok=True)
    df = pd.DataFrame(rows)
    out_path = os.path.join(out_dir, f"session_{base_filename}_itr_{itr}.csv")
    df.to_csv(out_path, index=False)
    return df, out_path

def save_master_csv(all_rows, out_dir, base_filename):
    os.makedirs(out_dir, exist_ok=True)
    df = pd.DataFrame(all_rows)
    out_path = os.path.join(out_dir, f"session_{base_filename}_all_runs.csv")
    df.to_csv(out_path, index=False)
    return df, out_path

def compute_rise_metrics(metrics_dict, metric_keys=("HCI", "CSM", "TBS")):
    steps = sorted(metrics_dict.keys())

    streaks = {k: 0 for k in metric_keys}
    totals = {k: 0 for k in metric_keys}
    prev_vals = {k: None for k in metric_keys}

    for step in steps:
        row = metrics_dict[step]

        for k in metric_keys:
            curr = row.get(k)

            if not is_valid_number(curr):
                row[f"rise_flag_{k}"] = None
                row[f"rise_streak_{k}"] = None
                row[f"rise_total_{k}"] = totals[k]
                continue

            prev = prev_vals[k]

            if is_valid_number(prev) and curr > prev:
                streaks[k] += 1
                totals[k] += 1
                row[f"rise_flag_{k}"] = 1
            else:
                streaks[k] = 0
                row[f"rise_flag_{k}"] = 0

            row[f"rise_streak_{k}"] = streaks[k]
            row[f"rise_total_{k}"] = totals[k]
            prev_vals[k] = curr

    return metrics_dict