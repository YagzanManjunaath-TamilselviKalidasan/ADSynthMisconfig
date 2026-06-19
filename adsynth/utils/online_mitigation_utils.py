import logging

import adsynth.DATABASE as DB
from adsynth.EXPERIMENT_DATABASE import EXP_EDGES

from adsynth.utils.ablation_study_utils import (
    indicators_hci_csm_tbs,
    exposure_X,
    exposure_users,
    exposure_computers,
    compute_delta_X,
    compute_rise_metrics,
    pbcc_bounded_bfs_tier2_computers,
)

from adsynth.utils.networkx_utils import (
    create_networkx_graph,
    find_user_count_with_path_to_DA,
)


ACTION_SETS = {
    "sessions_only": {"HasSession"},

    "permissions_only": {
        "AdminTo",
        "CanRDP",
        "CanPSRemote",
        "ExecuteDCOM",
        "AllowedToDelegate",
        "ReadLAPSPassword",
        "SQLAdmin",
        "AllowedToAct",
        "GenericAll",
        "GenericWrite",
        "WriteDacl",
        "WriteOwner",
        "AllExtendedRights",
        "Owns",
    },

    "nesting_only": {"MemberOf"},
}


EDGE_COST_PROFILE = {
    "HasSession": {
        "operational": 1,
        "impact": 1,
        "base_advantage": 3,
    },

    "MemberOf": {
        "operational": 4,
        "impact": 4,
        "base_advantage": 5,
    },

    "AdminTo": {
        "operational": 3,
        "impact": 4,
        "base_advantage": 5,
    },

    "GenericAll": {
        "operational": 3,
        "impact": 4,
        "base_advantage": 5,
    },

    "WriteDacl": {
        "operational": 3,
        "impact": 4,
        "base_advantage": 5,
    },

    "WriteOwner": {
        "operational": 3,
        "impact": 4,
        "base_advantage": 5,
    },

    "CanRDP": {
        "operational": 2,
        "impact": 2,
        "base_advantage": 3,
    },

    "CanPSRemote": {
        "operational": 2,
        "impact": 2,
        "base_advantage": 3,
    },

    "ExecuteDCOM": {
        "operational": 2,
        "impact": 2,
        "base_advantage": 3,
    },

    "AllowedToDelegate": {
        "operational": 3,
        "impact": 3,
        "base_advantage": 4,
    },

    "AllowedToAct": {
        "operational": 3,
        "impact": 3,
        "base_advantage": 4,
    },

    "ReadLAPSPassword": {
        "operational": 3,
        "impact": 3,
        "base_advantage": 4,
    },

    "SQLAdmin": {
        "operational": 3,
        "impact": 3,
        "base_advantage": 4,
    },

    "GenericWrite": {
        "operational": 3,
        "impact": 3,
        "base_advantage": 4,
    },

    "AllExtendedRights": {
        "operational": 3,
        "impact": 3,
        "base_advantage": 4,
    },

    "Owns": {
        "operational": 3,
        "impact": 3,
        "base_advantage": 4,
    },
}


def edge_label(edge):
    return (
        edge.get("label")
        or edge.get("relationship")
        or edge.get("type")
    )


def node_name(node):
    if isinstance(node, dict):
        return str(node.get("name", ""))
    return str(node)


def node_labels(node):
    if isinstance(node, dict):
        return str(node.get("labels", ""))
    return str(node)


def is_direct_da_path_edge(edge, high_value_target_name):
    start_name = node_name(edge.get("start", {}))
    end_name = node_name(edge.get("end", {}))

    return (
        high_value_target_name in start_name
        or high_value_target_name in end_name
    )


def is_group_based_permission(edge):
    start_labels = node_labels(edge.get("start", {}))
    end_labels = node_labels(edge.get("end", {}))

    return (
        "Group" in start_labels
        or "Group" in end_labels
    )


def action_cost(edge):
    label = edge_label(edge)
    profile = EDGE_COST_PROFILE.get(label)

    if profile is None:
        return 1

    return profile["operational"] + profile["impact"]


def mitigation_advantage(edge, high_value_target_name):
    label = edge_label(edge)
    profile = EDGE_COST_PROFILE.get(label)

    if profile is None:
        return 1

    advantage = profile["base_advantage"]

    if is_direct_da_path_edge(edge, high_value_target_name):
        advantage += 3

    if label == "MemberOf":
        advantage += 2

    if label != "MemberOf" and is_group_based_permission(edge):
        advantage += 1

    return advantage


def score_candidate(edge, high_value_target_name):
    return mitigation_advantage(edge, high_value_target_name) / max(
        action_cost(edge),
        1,
    )


def labels_for_condition(condition):
    if condition == "greedy_combined":
        return (
            ACTION_SETS["sessions_only"]
            | ACTION_SETS["permissions_only"]
            | ACTION_SETS["nesting_only"]
        )

    if condition not in ACTION_SETS:
        raise ValueError(f"Unknown mitigation condition: {condition}")

    return ACTION_SETS[condition]


def infer_mitigation_condition(injection_family):
    if injection_family == "session":
        return "sessions_only"

    if injection_family in {
        "individual_permission",
        "group_permission",
        "permission",
    }:
        return "permissions_only"

    if injection_family in {
        "group_nesting",
        "nesting",
    }:
        return "nesting_only"

    if injection_family == "mixed":
        return "greedy_combined"

    raise ValueError(f"Unknown injection_family: {injection_family}")


def get_candidate_edges(condition, high_value_target_name):
    labels = labels_for_condition(condition)

    candidates = [
        edge for edge in EXP_EDGES
        if edge_label(edge) in labels
    ]

    return sorted(
        candidates,
        key=lambda edge: score_candidate(edge, high_value_target_name),
        reverse=True,
    )


def remove_edge_safely(edge):
    if edge in EXP_EDGES:
        EXP_EDGES.remove(edge)
        return True

    return False


def online_alarm_triggered(
        metrics,
        step,
        rise_streak_k=2,
):
    row = metrics.get(step, {})

    # If alarm columns already exist, consider them.
    if (
        row.get("A_HCI", 0)
        or row.get("A_CSM", 0)
        or row.get("A_TBS", 0)
        or row.get("A_PBCC", 0)
    ):
        return True

    # Online fallback before final jump labels are computed.
    return bool(
        row.get("rise_streak_HCI", 0) >= rise_streak_k
        or row.get("rise_streak_CSM", 0) >= rise_streak_k
        or row.get("rise_streak_TBS", 0) >= rise_streak_k
    )


def compute_step_metrics(
        step,
        p,
        metrics,
        high_value_target_name,
        num_users,
        num_computers,
):
    networkx_graph = create_networkx_graph()

    find_user_count_with_path_to_DA(
        networkx_graph,
        high_value_target_name,
        step,
        metrics,
    )

    row = metrics[step]

    row["step"] = step
    row["p"] = p

    row["X"] = exposure_X(
        row["reachable_users_count"],
        row["reachable_comps_count"],
        num_users,
        num_computers,
    )

    row["X_users"] = exposure_users(
        row["reachable_users_count"],
        num_users,
    )

    row["X_comps"] = exposure_computers(
        row["reachable_comps_count"],
        num_computers,
    )

    indicators_hci_csm_tbs(
        EXP_EDGES,
        metrics,
        step,
        num_users,
        DB.TOTAL_T0_USERS,
        {2},
        1.0,
    )

    pbcc_result = pbcc_bounded_bfs_tier2_computers(
        networkx_graph,
        high_value_target_name,
        L=4,
    )

    row["PBCC"] = pbcc_result["pbcc"]

    return networkx_graph, row


def apply_online_mitigation_if_triggered(
        metrics,
        step,
        p,
        injection_family,
        high_value_target_name,
        num_users,
        num_computers,
        mitigation_enabled=False,
        mitigation_condition=None,
        mitigation_budget=25,
        used_cost=0,
        removed_count=0,
        rise_streak_k=2,
):
    """
    Generic online mitigation hook.

    Called  after one injection step has already been applied
    and the first version of that step's metrics has been computed.

    If alarm triggers:
        1. select candidate edge according to condition
        2. remove it from EXP_EDGES
        3. recompute metrics for the same step
    """

    if mitigation_condition is None:
        mitigation_condition = infer_mitigation_condition(injection_family)

    # Update online deltas / rise streaks before deciding.
    metrics = compute_delta_X(metrics)

    metrics = compute_rise_metrics(
        metrics,
        metric_keys=("HCI", "CSM", "TBS"),
    )

    alarm_now = online_alarm_triggered(
        metrics,
        step,
        rise_streak_k=rise_streak_k,
    )

    action = {
        "alarm_triggered": int(alarm_now),
        "mitigation_enabled": int(mitigation_enabled),
        "mitigation_condition": mitigation_condition,
        "mitigation_budget": mitigation_budget,
        "mitigation_removed": 0,
        "last_removed_edge_label": None,
        "last_removed_edge_cost": None,
        "last_removed_edge_advantage": None,
        "last_removed_edge_score": None,
        "used_mitigation_cost": used_cost,
        "removed_mitigation_count": removed_count,
    }

    if not mitigation_enabled or not alarm_now:
        metrics[step].update(action)
        return metrics, used_cost, removed_count

    candidates = get_candidate_edges(
        mitigation_condition,
        high_value_target_name,
    )

    selected_edge = None

    for candidate in candidates:
        c = action_cost(candidate)

        if used_cost + c <= mitigation_budget:
            selected_edge = candidate
            break

    if selected_edge is None:
        metrics[step].update(action)
        return metrics, used_cost, removed_count

    removed = remove_edge_safely(selected_edge)

    if not removed:
        metrics[step].update(action)
        return metrics, used_cost, removed_count

    c = action_cost(selected_edge)
    used_cost += c
    removed_count += 1

    # Recompute the same step after mitigation changed EXP_EDGES.
    compute_step_metrics(
        step=step,
        p=p,
        metrics=metrics,
        high_value_target_name=high_value_target_name,
        num_users=num_users,
        num_computers=num_computers,
    )

    metrics = compute_delta_X(metrics)

    metrics = compute_rise_metrics(
        metrics,
        metric_keys=("HCI", "CSM", "TBS"),
    )

    action.update({
        "mitigation_removed": 1,
        "last_removed_edge_label": edge_label(selected_edge),
        "last_removed_edge_cost": c,
        "last_removed_edge_advantage": mitigation_advantage(
            selected_edge,
            high_value_target_name,
        ),
        "last_removed_edge_score": score_candidate(
            selected_edge,
            high_value_target_name,
        ),
        "used_mitigation_cost": used_cost,
        "removed_mitigation_count": removed_count,
    })

    metrics[step].update(action)

    logging.info(
        "Mitigation step=%d condition=%s removed=%s cost=%s used_cost=%s removed_count=%s",
        step,
        mitigation_condition,
        action["last_removed_edge_label"],
        action["last_removed_edge_cost"],
        used_cost,
        removed_count,
    )

    return metrics, used_cost, removed_count