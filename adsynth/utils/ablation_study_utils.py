import re

import numpy as np

from adsynth.DATABASE import NODES, PAW_TIERS, S_TIERS_LOCATIONS, S_TIERS, ENABLED_USERS, ADMIN_USERS, WS_TIERS, \
    WS_TIERS_LOCATIONS, USER_TIER, COMPUTER_TIER, EDGES
from adsynth.EXPERIMENT_DATABASE import EXP_EDGES

from collections import Counter
from scipy.stats import t


def populate_node_tiers():
    for tier, users in enumerate(ADMIN_USERS):
        for user in users:
            USER_TIER[user] = tier
    for tier, users in enumerate(ENABLED_USERS):
        for user in users:
            USER_TIER[user] = tier

    for tier, servers in enumerate(S_TIERS):
        for server in servers:
            COMPUTER_TIER[server] = tier

    for tier, paws in enumerate(PAW_TIERS):
        for paw in paws:
            COMPUTER_TIER[paw] = tier

    for tier, ws_list in enumerate(WS_TIERS):
        for ws in ws_list:
            COMPUTER_TIER[ws] = tier


def get_baseline_from_AD(misconfig_type, TARGET_LABELS):
    if misconfig_type == "session":
        baseline_has_session = sum(1 for edge in EDGES if edge.get("label") == "HasSession")
        return baseline_has_session
    elif misconfig_type == "i_perm":
        baseline_edges = [
            edge for edge in EDGES
            if edge.get("label") in TARGET_LABELS
        ]
        return len(baseline_edges)


def comp_tier_fn(node_name_or_id: str, labels=()) -> int:
    try:
        s = next((x for x in NODES if x["id"] == node_name_or_id), None)

        name = s["properties"]["name"]
        return COMPUTER_TIER[name]
    # todo check
    except KeyError:
        return -1


def user_tier_fn(dn: str):
    if not dn:
        return None
    m = re.search(r"OU=T(\d+)\b", dn, flags=re.IGNORECASE)
    return int(m.group(1)) if m else 2


def indicators_hci_csm_tbs(EXP_EDGE, misconfig_growth_metrics, misconfig_session_count, low_tiers={2}, eps=1.0):
    has_Session_edge_count = [e for e in EXP_EDGE if e.get("label") == "HasSession"]

    d_sess = Counter(str(e["start"]["id"]) for e in has_Session_edge_count)

    C_low = {c for c in d_sess.keys() if comp_tier_fn(c) in low_tiers}

    if not C_low:
        HCI = 0.0
    else:
        dbar = sum(d_sess[c] for c in C_low) / len(C_low)
        denom = (dbar + eps) ** 2
        HCI = (1 / len(C_low)) * sum((d_sess[c] ** 2) / denom for c in C_low)

    U = {str(e["end"]["id"]) for e in has_Session_edge_count}

    cross = 0
    t0_cross = 0
    U_T0 = set()

    for e in has_Session_edge_count:
        c = str(e["start"]["id"])
        u = str(e["end"]["id"])
        t_c = comp_tier_fn(c)
        t_u = user_tier_fn(u)
        if t_u == 0:
            U_T0.add(u)

        if t_u < t_c:
            cross += 1
            if t_u == 0 and t_c > 0:
                t0_cross += 1

    CSM = cross / len(U) if U else 0.0
    TBS = t0_cross / len(U_T0) if U_T0 else 0.0

    misconfig_growth_metrics[misconfig_session_count]["HCI"] = HCI
    misconfig_growth_metrics[misconfig_session_count]["CSM"] = CSM
    misconfig_growth_metrics[misconfig_session_count]["TBS"] = TBS
    return


def exposure_X(reachable_users_count, reachable_comps_count, num_users, num_computers):
    denom = num_users + num_computers
    return (reachable_users_count + reachable_comps_count) / denom if denom else 0.0


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
        L=4,
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
            if node == target_id and seen_sess and seen_non_sess:
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


def compute_delta_X(misconfig_growth_metrics):
    steps = sorted(misconfig_growth_metrics.keys())

    for i in range(1, len(steps)):
        curr = steps[i]
        prev = steps[i - 1]

        Xi = misconfig_growth_metrics[curr]["X"]
        Xi_prev = misconfig_growth_metrics[prev]["X"]

        delta = Xi - Xi_prev

        misconfig_growth_metrics[curr]["delta_X"] = delta
    return misconfig_growth_metrics


def find_p_star(misconfig_growth_metrics):
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

    corr = np.corrcoef(HCI, deltaX)[0, 1]

    return corr


def compute_mu(all_runs, metric):
    mu = {}

    steps = sorted(all_runs[0].keys())

    for step in steps:
        p = all_runs[0][step]["p"]

        X_vals = [all_runs[r][step][metric] for r in all_runs]

        mu[p] = np.mean(X_vals)

    return mu


def compute_sigma2(all_runs, metric):
    sigma2 = {}

    steps = sorted(all_runs[0].keys())

    for step in steps:
        p = all_runs[0][step]["p"]

        X_vals = [all_runs[r][step][metric] for r in all_runs]

        sigma2[p] = np.var(X_vals, ddof=1)
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

    mean_p_star = np.mean(p_star_values)

    ci_low = np.percentile(p_star_values, 2.5)
    ci_high = np.percentile(p_star_values, 97.5)

    return mean_p_star, ci_low, ci_high
