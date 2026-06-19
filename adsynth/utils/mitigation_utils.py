import os
from pathlib import Path
from datetime import datetime

import duckdb
import pandas as pd

import adsynth.DATABASE as DB
from adsynth.ADSynth import DUCKDB_FILE_NAME
from adsynth.EXPERIMENT_DATABASE import EXP_EDGES

from adsynth.utils.ablation_study_utils import (
    indicators_hci_csm_tbs,
    exposure_X,
    exposure_users,
    exposure_computers,
    compute_delta_X,
    compute_rise_metrics,
    compute_sigma2,
    populate_node_tiers,
    pbcc_bounded_bfs_tier2_computers,
)

from adsynth.utils.database_utils import load_all_experiment_states_from_json
from adsynth.utils.networkx_utils import (
    create_networkx_graph,
    find_user_count_with_path_to_DA,
)
from adsynth.utils.parameters import get_int_param_value
from adsynth.utils.prediction_utils import calc_thresholds_and_jump_labels_for_iteration

def run_cost_aware_mitigation_from_metrics(
        self,
        filepath,
        condition="greedy_combined",
        budgets=(10, 25, 50, 100),
        x_star=0.5,
        fixed_p_values=(0.02, 0.05, 0.10),
        out_duckdb_path=None,
):
    import os
    import duckdb
    import pandas as pd
    import matplotlib.pyplot as plt

    from pathlib import Path
    from datetime import datetime

    if out_duckdb_path is None:
        out_duckdb_path = str(Path.home() / DUCKDB_FILE_NAME)
    filename = Path(filepath).stem

    # experiment_session_exp_xxx.json
    experiment_id = filename.replace("experiment_session_", "")
    high_value_target_name = "DOMAIN ADMINS@TESTLAB.LOCALE"

    mitigation_experiment_id = (
        f"mitigation_{condition}_from_{experiment_id}_"
        f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )

    action_sets = {
        "sessions_only": {"HasSession"},
        "permissions_only": {
            "AdminTo", "CanRDP", "CanPSRemote", "ExecuteDCOM",
            "AllowedToDelegate", "ReadLAPSPassword", "SQLAdmin",
            "AllowedToAct", "GenericAll", "GenericWrite",
            "WriteDacl", "WriteOwner", "AllExtendedRights", "Owns",
        },
        "nesting_only": {"MemberOf"},
    }

    # ============================================================
    # Composite Cost Model
    # ============================================================

    edge_cost_profile = {

        # Sessions
        "HasSession": {
            "operational": 1,
            "impact": 1,
            "base_advantage": 3,
        },

        # Group nesting
        "MemberOf": {
            "operational": 4,
            "impact": 4,
            "base_advantage": 5,
        },

        # High privilege permissions
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

        # Medium privilege permissions
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

    # ============================================================
    # Helpers
    # ============================================================

    def edge_label(edge):
        return edge.get("label") or edge.get("relationship") or edge.get("type")

    def fetch_original_metrics_per_itr(
            db_path,
            experiment_id,
            table_name="metric_steps"
    ):

        con = duckdb.connect(db_path)

        df = con.execute(f"""
            SELECT *
            FROM {table_name}
            WHERE experiment_id = ?
            ORDER BY iteration_id, step
        """, [experiment_id]).df()

        con.close()

        if df.empty:
            raise ValueError(
                f"No data found for experiment_id={experiment_id}"
            )

        original_metrics_per_itr = {}

        for iteration_id, grp in df.groupby("iteration_id"):

            itr = int(str(iteration_id).split("_")[1])

            original_metrics_per_itr[itr] = {
                int(row["step"]): row.to_dict()
                for _, row in grp.iterrows()
            }

        return original_metrics_per_itr

    def action_cost(edge):

        label = edge_label(edge)

        profile = edge_cost_profile.get(label)

        if profile is None:
            return 1

        return (
                profile["operational"]
                + profile["impact"]
        )

    def is_direct_da_path_edge(edge):

        start_name = str(
            edge.get("start", {}).get("name", "")
        )

        end_name = str(
            edge.get("end", {}).get("name", "")
        )

        return (
                high_value_target_name in start_name
                or high_value_target_name in end_name
        )

    def is_group_based_permission(edge):

        start_labels = str(
            edge.get("start", {}).get("labels", "")
        )

        end_labels = str(
            edge.get("end", {}).get("labels", "")
        )

        return (
                "Group" in start_labels
                or "Group" in end_labels
        )

    def mitigation_advantage(edge):

        label = edge_label(edge)

        profile = edge_cost_profile.get(label)

        if profile is None:
            return 1

        advantage = profile["base_advantage"]

        # Choke point / DA bonus
        if is_direct_da_path_edge(edge):
            advantage += 3

        # Group nesting bonus
        if label == "MemberOf":
            advantage += 2

        # Group permission bonus
        if (
                label != "MemberOf"
                and is_group_based_permission(edge)
        ):
            advantage += 1

        return advantage

    def score_candidate(edge):

        advantage = mitigation_advantage(edge)

        cost = action_cost(edge)

        return advantage / max(cost, 1)

    def get_candidate_edges(cond):

        if cond == "greedy_combined":

            labels = (
                    action_sets["sessions_only"]
                    | action_sets["permissions_only"]
                    | action_sets["nesting_only"]
            )

        else:

            labels = action_sets[cond]

        return [
            e for e in EXP_EDGES
            if edge_label(e) in labels
        ]

    def alarm_triggered(row):

        return bool(
            row.get("A_HCI", 0)
            or row.get("A_CSM", 0)
            or row.get("A_TBS", 0)
            or row.get("A_PBCC", 0)
        )

    def remove_edge_safely(edge):

        if edge in EXP_EDGES:
            EXP_EDGES.remove(edge)

    def compute_p_threshold(metrics, threshold_x):

        for step in sorted(metrics.keys()):

            if metrics[step].get("X", 0) >= threshold_x:

                return metrics[step].get("p")

        return None

    def exposure_at_fixed_p(metrics, target_p):

        for step in sorted(metrics.keys()):

            if metrics[step].get("p", 0) >= target_p:

                return metrics[step].get("X")

        return None

    # ============================================================
    # Graph Params
    # ============================================================

    num_users = get_int_param_value(
        "User",
        "nUsers",
        self.parameters
    )

    num_computers = get_int_param_value(
        "Computer",
        "nComputers",
        self.parameters
    )

    # ============================================================
    # Metric recomputation
    # ============================================================

    def recompute_metrics_for_step(
            step,
            p,
            B,
            used_cost,
            removed_count,
            cond,
            online,
    ):

        networkx_graph = create_networkx_graph()

        step_metrics = {}

        find_user_count_with_path_to_DA(
            networkx_graph,
            high_value_target_name,
            step,
            step_metrics,
        )

        row = step_metrics[step]

        row["step"] = step
        row["p"] = p

        row["B"] = B
        row["used_cost"] = used_cost
        row["removed_count"] = removed_count

        row["condition"] = cond

        row["online_mitigation"] = int(online)

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
            step_metrics,
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

        return row

    # ============================================================
    # Main loop
    # ============================================================

    original_metrics_per_itr = fetch_original_metrics_per_itr(
        db_path=out_duckdb_path,
        experiment_id=experiment_id,
        table_name="metric_steps"
    )

    all_metric_rows = []
    all_summary_rows = []

    pstar_plot_rows = []

    for B in budgets:

        no_mitigation_per_itr = {}
        online_mitigation_per_itr = {}

        for itr in range(self.R):

            original_rows = list(
                original_metrics_per_itr[itr].values()
            )

            original_by_step = {
                row["step"]: row
                for row in original_rows
            }

            load_all_experiment_states_from_json(
                filepath,
                verbose=False
            )

            populate_node_tiers()

            candidates = get_candidate_edges(condition)

            if condition == "greedy_combined":

                candidates = sorted(
                    candidates,
                    key=score_candidate,
                    reverse=True
                )

            max_steps = min(
                len(original_rows),
                len(candidates)
            )

            # ====================================================
            # Baseline
            # ====================================================

            load_all_experiment_states_from_json(
                filepath,
                verbose=False
            )

            populate_node_tiers()

            baseline_metrics = {}

            for step in range(1, max_steps + 1):

                p = original_metrics_per_itr[itr][step]["p"]

                baseline_metrics[step] = recompute_metrics_for_step(
                    step=step,
                    p=p,
                    B=B,
                    used_cost=0,
                    removed_count=0,
                    cond=condition,
                    online=False,
                )

            baseline_metrics = compute_delta_X(
                baseline_metrics
            )

            baseline_metrics = compute_rise_metrics(
                baseline_metrics,
                metric_keys=("HCI", "CSM", "TBS"),
            )

            no_mitigation_per_itr[itr] = baseline_metrics

            # ====================================================
            # Online mitigation
            # ====================================================

            load_all_experiment_states_from_json(
                filepath=filepath,
                verbose=False
            )

            populate_node_tiers()

            online_metrics = {}

            used_cost = 0
            removed_count = 0

            candidate_idx = 0

            for step in range(1, max_steps + 1):

                p = original_metrics_per_itr[itr][step]["p"]

                alarm_row = original_by_step.get(step, {})

                is_alarm = alarm_triggered(alarm_row)

                removed_label = None
                removed_cost = None
                removed_advantage = None
                removed_score = None

                if is_alarm:

                    while candidate_idx < len(candidates):

                        candidate_edge = candidates[candidate_idx]

                        candidate_idx += 1

                        c = action_cost(candidate_edge)

                        if used_cost + c <= B:

                            remove_edge_safely(candidate_edge)

                            used_cost += c

                            removed_count += 1

                            removed_label = edge_label(candidate_edge)

                            removed_cost = c

                            removed_advantage = mitigation_advantage(
                                candidate_edge
                            )

                            removed_score = score_candidate(
                                candidate_edge
                            )

                            break

                row = recompute_metrics_for_step(
                    step=step,
                    p=p,
                    B=B,
                    used_cost=used_cost,
                    removed_count=removed_count,
                    cond=condition,
                    online=True,
                )

                row["alarm_triggered"] = int(is_alarm)

                row["last_removed_edge_label"] = removed_label
                row["last_removed_edge_cost"] = removed_cost
                row["last_removed_edge_advantage"] = removed_advantage
                row["last_removed_edge_score"] = removed_score

                online_metrics[step] = row

            online_metrics = compute_delta_X(
                online_metrics
            )

            online_metrics = compute_rise_metrics(
                online_metrics,
                metric_keys=("HCI", "CSM", "TBS"),
            )

            metrics_with_jump_label, _, _ = (
                calc_thresholds_and_jump_labels_for_iteration(
                    online_metrics,
                    itr=itr,
                    baseline_fraction=0.2,
                    min_points=5,
                )
            )

            online_metrics = {
                row["step"]: row
                for row in metrics_with_jump_label
            }

            online_mitigation_per_itr[itr] = online_metrics

            # ====================================================
            # Save rows
            # ====================================================

            for row in baseline_metrics.values():

                row["itr"] = itr

                row["experiment_id"] = mitigation_experiment_id

                row["source_experiment_id"] = experiment_id

                row["policy"] = "no_mitigation"

                all_metric_rows.append(row)

            for row in online_metrics.values():

                row["itr"] = itr

                row["experiment_id"] = mitigation_experiment_id

                row["source_experiment_id"] = experiment_id

                row["policy"] = "online_mitigation"

                all_metric_rows.append(row)

            # ====================================================
            # Fixed p evaluation
            # ====================================================

            for fixed_p in fixed_p_values:

                X_no = exposure_at_fixed_p(
                    baseline_metrics,
                    fixed_p
                )

                X_mit = exposure_at_fixed_p(
                    online_metrics,
                    fixed_p
                )

                all_summary_rows.append({

                    "experiment_id": mitigation_experiment_id,

                    "source_experiment_id": experiment_id,

                    "itr": itr,

                    "condition": condition,

                    "B": B,

                    "fixed_p": fixed_p,

                    "X_no_mitigation": X_no,

                    "X_online_mitigation": X_mit,

                    "risk_reduction": (
                        None
                        if X_no is None or X_mit is None
                        else X_no - X_mit
                    ),

                    "used_cost": used_cost,

                    "removed_count": removed_count,
                })

            # ====================================================
            # Threshold p*
            # ====================================================

            p0_x = compute_p_threshold(
                baseline_metrics,
                x_star
            )

            pA_x = compute_p_threshold(
                online_metrics,
                x_star
            )

            all_summary_rows.append({

                "experiment_id": mitigation_experiment_id,

                "source_experiment_id": experiment_id,

                "itr": itr,

                "condition": condition,

                "B": B,

                "x_star": x_star,

                "p_star_no_mitigation_threshold": p0_x,

                "p_star_online_mitigation_threshold": pA_x,

                "delta_p_star_threshold": (
                    None
                    if p0_x is None or pA_x is None
                    else pA_x - p0_x
                ),

                "used_cost": used_cost,

                "removed_count": removed_count,
            })

        # ========================================================
        # Variance-based p*
        # ========================================================

        sigma2_no = compute_sigma2(
            no_mitigation_per_itr,
            "X"
        )

        sigma2_mit = compute_sigma2(
            online_mitigation_per_itr,
            "X"
        )

        p_star_no = (
            max(sigma2_no, key=sigma2_no.get)
            if sigma2_no else None
        )

        p_star_mit = (
            max(sigma2_mit, key=sigma2_mit.get)
            if sigma2_mit else None
        )

        pstar_plot_rows.append({
            "Budget": B,
            "NoMitigation": p_star_no,
            "OnlineMitigation": p_star_mit,
        })

        all_summary_rows.append({

            "experiment_id": mitigation_experiment_id,

            "source_experiment_id": experiment_id,

            "itr": "ALL",

            "condition": condition,

            "B": B,

            "variance_p_star_no_mitigation": p_star_no,

            "variance_p_star_online_mitigation": p_star_mit,

            "delta_variance_p_star": (
                None
                if p_star_no is None or p_star_mit is None
                else p_star_mit - p_star_no
            ),
        })

    # ============================================================
    # Save outputs
    # ============================================================

    metrics_df = pd.DataFrame(all_metric_rows)

    summary_df = pd.DataFrame(all_summary_rows)

    os.makedirs("analysis/csv", exist_ok=True)

    metrics_csv = (
        f"analysis/csv/{mitigation_experiment_id}_metrics.csv"
    )

    summary_csv = (
        f"analysis/csv/{mitigation_experiment_id}_summary.csv"
    )

    metrics_df.to_csv(metrics_csv, index=False)

    summary_df.to_csv(summary_csv, index=False)

    con = duckdb.connect(out_duckdb_path)

    con.execute("""
        CREATE TABLE IF NOT EXISTS mitigation_metrics
        AS SELECT * FROM metrics_df LIMIT 0
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS mitigation_summary
        AS SELECT * FROM summary_df LIMIT 0
    """)

    con.execute("""
        INSERT INTO mitigation_metrics
        SELECT * FROM metrics_df
    """)

    con.execute("""
        INSERT INTO mitigation_summary
        SELECT * FROM summary_df
    """)

    con.close()

    # ============================================================
    # Plot p*
    # ============================================================

    pstar_df = pd.DataFrame(pstar_plot_rows)

    plt.figure(figsize=(8, 5))

    plt.plot(
        pstar_df["Budget"],
        pstar_df["NoMitigation"],
        marker="o",
        label="No Mitigation"
    )

    plt.plot(
        pstar_df["Budget"],
        pstar_df["OnlineMitigation"],
        marker="o",
        label="Online Mitigation"
    )

    plt.xlabel("Budget")

    plt.ylabel("Variance-based p*")

    plt.title(
        f"Variance-based p* shift ({condition})"
    )

    plt.grid(True)

    plt.legend()

    plot_path = (
        f"analysis/csv/{mitigation_experiment_id}_pstar_plot.png"
    )

    plt.savefig(plot_path, bbox_inches="tight")

    plt.close()

    print("Saved mitigation metrics CSV:", metrics_csv)

    print("Saved mitigation summary CSV:", summary_csv)

    print("Saved mitigation DuckDB:", out_duckdb_path)

    print("Saved p* plot:", plot_path)

    return metrics_df, summary_df
