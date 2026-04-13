import logging
import math
import re
from typing import List, Optional, Dict

import numpy as np
import pandas as pd

from adsynth.DATABASE import NODES, PAW_TIERS, S_TIERS_LOCATIONS, S_TIERS, ENABLED_USERS, ADMIN_USERS, WS_TIERS, \
    WS_TIERS_LOCATIONS, USER_TIER, COMPUTER_TIER, EDGES
from adsynth.EXPERIMENT_DATABASE import EXP_EDGES

from collections import Counter
from scipy.stats import t

from adsynth.utils.ablation_study_utils import get_baseline_segment, is_valid_number, safe_mean, safe_std, \
    safe_percentile

from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.metrics import roc_auc_score, average_precision_score


def estimate_indicator_thresholds(
        metrics: List[Dict],
        baseline_fraction: float = 0.2,
        min_points: int = 5
) -> Dict[str, Optional[float]]:
    # 20% of runs or 5 runs - whichever is max
    baseline = get_baseline_segment(metrics, baseline_fraction, min_points)

    hci_vals = [row.get("HCI") for row in baseline if is_valid_number(row.get("HCI"))]
    csm_vals = [row.get("CSM") for row in baseline if is_valid_number(row.get("CSM"))]
    tbs_vals = [row.get("TBS") for row in baseline if is_valid_number(row.get("TBS"))]
    pbcc_vals = [row.get("PBCC") for row in baseline if is_valid_number(row.get("PBCC"))]

    mu_hci = safe_mean(hci_vals)
    sigma_hci = safe_std(hci_vals, ddof=0)

    mu_pbcc = safe_mean(pbcc_vals)
    sigma_pbcc = safe_std(pbcc_vals, ddof=0)

    # as per 1.3 -> mu_hci + 2 sigma_hci

    tau_hci = None if mu_hci is None or sigma_hci is None else mu_hci + 2 * sigma_hci
    # tau_hci = safe_percentile(hci_vals,95)
    # as per 1.3 -> 90th percentile
    tau_csm = safe_percentile(csm_vals, 90)

    tau_tbs = 0.0
    # tau_tbs = safe_percentile(tbs_vals,90)

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


def apply_indicator_alarms(
        metrics: List[Dict],
        thresholds: Dict[str, Optional[float]]
) -> List[Dict]:
    tau_hci = thresholds.get("tau_HCI")
    tau_csm = thresholds.get("tau_CSM")
    tau_tbs = thresholds.get("tau_TBS", 0.0)
    tau_pbcc = thresholds.get("tau_PBCC")

    out = []

    for row in metrics:
        new_row = dict(row)

        hci = row.get("HCI")
        csm = row.get("CSM")
        tbs = row.get("TBS")
        pbcc = row.get("PBCC", row.get("pbcc"))

        new_row["A_HCI"] = int(tau_hci is not None and is_valid_number(hci) and hci >= tau_hci)
        new_row["A_CSM"] = int(tau_csm is not None and is_valid_number(csm) and csm >= tau_csm)
        new_row["A_TBS"] = int(tau_tbs is not None and is_valid_number(tbs) and tbs >= tau_tbs)
        new_row["A_PBCC"] = int(tau_pbcc is not None and is_valid_number(pbcc) and pbcc >= tau_pbcc)

        out.append(new_row)

    return out




def compute_jump_labels(metrics: List[Dict]) -> List[Dict]:
    # Planned jump settings: 10% or 20% absolute increase over next 5 or 10 steps
    configs = [
        (5, 0.10),
        (5, 0.20),
        (10, 0.10),
        (10, 0.20),
    ]

    out = [dict(row) for row in metrics]
    n = len(out)

    for k, delta in configs:
        label_name = f"J_k{k}_d{str(delta).replace('.', 'p')}"

        for i in range(n):
            if i + k >= n:
                out[i][label_name] = None
                continue

            x_i = out[i].get("X")
            x_future = out[i + k].get("X")

            if not is_valid_number(x_i) or not is_valid_number(x_future):
                out[i][label_name] = None
            else:
                out[i][label_name] = int((x_future - x_i) >= delta)

    return out

def prepare_prediction_pipeline_for_iteration(
        run_metrics: Dict,
        itr: int,
        baseline_fraction: float = 0.2,
        min_points: int = 5,
        export_csv: bool = True,
):
    # Convert step-keyed dict to sorted row list
    rows = []
    for step in sorted(run_metrics.keys()):
        row = dict(run_metrics[step])
        row.setdefault("step", step)
        rows.append(row)

    thresholds = estimate_indicator_thresholds(
        rows,
        baseline_fraction=baseline_fraction,
        min_points=min_points,
    )
    logging.info("Iteration %d thresholds: %s", itr, thresholds)

    # Binary alarms from thresholds
    metrics_with_alarms = apply_indicator_alarms(rows, thresholds)

    # Future jump labels
    metrics_with_labels = compute_jump_labels(metrics_with_alarms)

    if export_csv:
        export_metrics_to_csv(
            metrics_with_labels,
            f"misconfig_metrics_with_alarms_labels_itr_{itr}.csv",
        )

    return metrics_with_labels, thresholds


def calc_thresholds_and_jump_labels_for_iteration(
        run_metrics: Dict,
        itr: int,
        baseline_fraction: float = 0.2,
        min_points: int = 5,
        evaluate: bool = True,
):
    metrics_ready, thresholds = prepare_prediction_pipeline_for_iteration(
        run_metrics,
        itr=itr,
        baseline_fraction=baseline_fraction,
        min_points=min_points,
        export_csv=True,
    )

    print(f"\nIteration {itr} thresholds:")
    for k, v in thresholds.items():
        print(f"{k}: {v}")

    label_specs = ["J_k5_d0.1", "J_k5_d0.2", "J_k10_d0.1", "J_k10_d0.2"]
    datasets = {}

    # for label_name in label_specs:
    #     X, y = build_prediction_dataset(metrics_ready, label_name)
    #     datasets[label_name] = {"X": X, "y": y}
    #
    #     print(f"Iteration {itr} | {label_name}: X={X.shape}, y={y.shape}")
    #
    #     if evaluate and X.shape[0] > 0 and len(np.unique(y)) > 1:
    #         print(f"Evaluating logistic regression for iteration {itr}, label {label_name}")
    #         evaluate_logreg(X, y)

    return metrics_ready, thresholds, datasets




def build_prediction_dataset(
        metrics: List[Dict],
        label_name: str,
        feature_names: List[str] = None,
):
    if feature_names is None:
        feature_names = ["HCI", "CSM", "TBS", "PBCC", "p", "X"]

    X, y = [], []

    for row in metrics:
        label = row.get(label_name)

        if label is None:
            continue

        feature_values = []
        valid = True

        for feat in feature_names:
            # Allow lowercase pbcc fallback
            if feat == "PBCC":
                val = row.get("PBCC", row.get("pbcc"))
            else:
                val = row.get(feat)

            if not is_valid_number(val):
                valid = False
                break

            feature_values.append(float(val))

        if not valid:
            continue

        X.append(feature_values)
        y.append(int(label))

    return np.asarray(X, dtype=float), np.asarray(y, dtype=int)


def evaluate_logreg(X, y):
    if len(np.unique(y)) < 2:
        raise ValueError("Label vector has only one class; ROC-AUC / PR-AUC are undefined.")

    clf = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("model", LogisticRegression(
            penalty="l2",
            solver="liblinear",
            class_weight="balanced",
            max_iter=1000,
            random_state=31197
        ))
    ])

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=31197)
    y_score = cross_val_predict(clf, X, y, cv=cv, method="predict_proba")[:, 1]

    return {
        "roc_auc": roc_auc_score(y, y_score),
        "pr_auc": average_precision_score(y, y_score),
        "y_score": y_score
    }


def export_metrics_to_csv(metrics, filename):
    rows = []

    for step, row in enumerate(metrics):
        new_row = dict(row)
        new_row["step"] = step
        rows.append(new_row)

    df = pd.DataFrame(rows)
    cols_to_remove = [
        "reachable_users",
        "new_reachable_users",
        "reachable_comps",
        "new_reachable_comps_names",
        "reachable_comps_names"
    ]

    df = df.drop(columns=cols_to_remove, errors="ignore")
    df = df.sort_values("step")

    df.to_csv(filename, index=False)

    print(f"Dataset exported to {filename}")


def add_high_exposure_label(df, exposure_col="X", quantile=0.8):
    df = df.copy()
    threshold = df[exposure_col].quantile(quantile)
    df["high_exposure_label"] = (df[exposure_col] >= threshold).astype(int)
    return df, threshold


import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
)


def misconfig_metrics_to_df(misconfig_metrics_per_itr):
    rows = []

    if isinstance(misconfig_metrics_per_itr, dict):
        first_val = next(iter(misconfig_metrics_per_itr.values()), None)

        # case 1: step -> row
        if isinstance(first_val, dict) and (
                "HCI" in first_val or "CSM" in first_val or "TBS" in first_val
        ):
            for step, row in misconfig_metrics_per_itr.items():
                r = dict(row)
                r["run"] = 0
                r["step"] = step
                rows.append(r)

        # case 2: run -> step -> row
        else:
            for run_id, step_dict in misconfig_metrics_per_itr.items():
                if not isinstance(step_dict, dict):
                    continue
                for step, row in step_dict.items():
                    r = dict(row)
                    r["run"] = run_id
                    r["step"] = step
                    rows.append(r)

    elif isinstance(misconfig_metrics_per_itr, list):
        for step, row in enumerate(misconfig_metrics_per_itr, start=1):
            r = dict(row)
            r["run"] = 0
            r["step"] = step
            rows.append(r)
    else:
        raise TypeError("Unsupported type for misconfig_metrics_per_itr")

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(["run", "step"]).reset_index(drop=True)
    return df


def add_target_from_x(df, x_col="X", quantile=0.8):
    df = df.copy()
    threshold = df[x_col].quantile(quantile)
    df["high_exposure_label"] = (df[x_col] >= threshold).astype(int)
    return df, threshold


def run_logreg_df(df, target_col="high_exposure_label", feature_cols=None):
    if feature_cols is None:
        feature_cols = ["HCI", "CSM", "TBS"]

    needed = feature_cols + [target_col]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    data = df[needed].dropna().copy()
    X = data[feature_cols]
    y = data[target_col].astype(int)

    if len(data) < 4:
        raise ValueError("Not enough rows after dropna()")

    if y.nunique() < 2:
        raise ValueError(f"Target column '{target_col}' has only one class")

    # Produces overfit data
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.3,
        random_state=42,
        stratify=y,
    )

    # split_idx = int(len(data) * 0.7)
    # train_df = data.iloc[:split_idx]
    # test_df = data.iloc[split_idx:]
    # X_train = train_df[feature_cols]
    # y_train = train_df[target_col].astype(int)
    #
    # X_test = test_df[feature_cols]
    # y_test = test_df[target_col].astype(int)

    model = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(max_iter=2000, class_weight="balanced"))
    ])

    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    results = {
        "n_rows_used": len(data),
        "class_0": int((y == 0).sum()),
        "class_1": int((y == 1).sum()),
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred, zero_division=0),
        "recall": recall_score(y_test, y_pred, zero_division=0),
        "f1": f1_score(y_test, y_pred, zero_division=0),
        "roc_auc": roc_auc_score(y_test, y_prob),
    }

    clf = model.named_steps["clf"]
    coef_df = pd.DataFrame({
        "feature": feature_cols,
        "coefficient": clf.coef_[0]
    }).sort_values("coefficient", ascending=False)

    return model, results, coef_df


def run_logreg_all_iterations_to_excel(
        misconfig_metrics_per_itr,
        output_excel="logreg_all_iterations.xlsx",
        feature_cols=None,
        x_col="X",
        quantile=0.8,
):
    if feature_cols is None:
        feature_cols = ["HCI", "CSM", "TBS"]

    summary_rows = []
    coef_rows = []
    skipped_rows = []

    for i in range(len(misconfig_metrics_per_itr)):
        try:
            df_all = misconfig_metrics_to_df(misconfig_metrics_per_itr[i])

            if df_all.empty:
                skipped_rows.append({
                    "iteration": i,
                    "reason": "empty dataframe"
                })
                continue

            if x_col not in df_all.columns:
                skipped_rows.append({
                    "iteration": i,
                    "reason": f"missing {x_col}"
                })
                continue

            df_all, thr = add_target_from_x(df_all, x_col=x_col, quantile=quantile)

            model, results, coef_df = run_logreg_df(
                df_all,
                target_col="high_exposure_label",
                feature_cols=feature_cols
            )

            summary_rows.append({
                "iteration": i,
                "x_threshold": thr,
                **results
            })

            coef_df = coef_df.copy()
            coef_df["iteration"] = i
            coef_df["x_threshold"] = thr
            coef_rows.append(coef_df)

        except Exception as e:
            skipped_rows.append({
                "iteration": i,
                "reason": str(e)
            })

    df_summary = pd.DataFrame(summary_rows)
    df_coefs = pd.concat(coef_rows, ignore_index=True) if coef_rows else pd.DataFrame()
    df_skipped = pd.DataFrame(skipped_rows)

    # wide coefficient table: one row per iteration
    if not df_coefs.empty:
        df_coef_wide = (
            df_coefs.pivot(index="iteration", columns="feature", values="coefficient")
            .reset_index()
        )
        df_coef_wide.columns.name = None
    else:
        df_coef_wide = pd.DataFrame()

    with pd.ExcelWriter(output_excel, engine="xlsxwriter") as writer:
        if not df_summary.empty:
            df_summary.to_excel(writer, sheet_name="summary", index=False)

        if not df_coefs.empty:
            df_coefs.to_excel(writer, sheet_name="coefficients_long", index=False)

        if not df_coef_wide.empty:
            df_coef_wide.to_excel(writer, sheet_name="coefficients_wide", index=False)

        if not df_skipped.empty:
            df_skipped.to_excel(writer, sheet_name="skipped", index=False)

    print(f"Saved logistic regression results to: {output_excel}")
    return df_summary, df_coefs, df_coef_wide, df_skipped


# unused
def create_jump_labels(
        metrics: List[Dict],
        k: int,
        delta: float,
        x_key: str = "X"
) -> List[Dict]:
    out = []

    n = len(metrics)
    metrics_list = list(metrics.values())

    for i, row in enumerate(metrics_list):

        new_row = dict(row)

        if i + k >= n:
            new_row[f"J_k{k}_d{delta}"] = None
        else:
            x_i = row.get(x_key)
            x_future = metrics[i + k].get(x_key)

            if not is_valid_number(x_i) or not is_valid_number(x_future):
                new_row[f"J_k{k}_d{delta}"] = None
            else:
                new_row[f"J_k{k}_d{delta}"] = int((x_future - x_i) >= delta)

        out.append(new_row)

    return out


# unused
def calc_thresholds_and_jump_labels(misconfig_metrics_per_itr):
    # Calc thresholds, apply alarms and create j    ump labels
    metrics_ready, thresholds = prepare_prediction_pipeline(
        misconfig_metrics_per_itr,
        baseline_fraction=0.2,
        min_points=5
    )

    print("Thresholds:")
    for k, v in thresholds.items():
        print(f"{k}: {v}")

    # X_5_10, y_5_10 = build_prediction_dataset(metrics_ready, "J_k5_d0p1")
    # X_5_20, y_5_20 = build_prediction_dataset(metrics_ready, "J_k5_d0p2")
    # X_10_10, y_10_10 = build_prediction_dataset(metrics_ready, "J_k10_d0p1")
    # X_10_20, y_10_20 = build_prediction_dataset(metrics_ready, "J_k10_d0p2")
    #
    # print("Shapes:")
    # print("k=5, d=0.10:", X_5_10.shape, y_5_10.shape)
    # print("k=5, d=0.20:", X_5_20.shape, y_5_20.shape)
    # print("k=10, d=0.10:", X_10_10.shape, y_10_10.shape)
    # print("k=10, d=0.20:", X_10_20.shape, y_10_20.shape)
    #
    # if X_5_10.shape[0] > 0:
    #     evaluate_logreg(X_5_10, y_5_10)



# unused
def prepare_prediction_pipeline(
        misconfig_metrics_per_itr: List[Dict],
        baseline_fraction: float = 0.2,
        min_points: int = 5
):
    # based om 1.3 - tau estimation from metrics
    thresholds = estimate_indicator_thresholds(
        misconfig_metrics_per_itr,
        baseline_fraction=baseline_fraction,
        min_points=min_points
    )
    logging.info("Thresholds : %s", thresholds)
    print("Thresholds : %s", thresholds)
    # based om 1.3 - tau based binary alarms
    metrics_with_alarms = apply_indicator_alarms(
        misconfig_metrics_per_itr,
        thresholds
    )
    export_metrics_to_csv(metrics_with_alarms, "misconfig_metrics_with_alarms.csv")
    # a 10–20% absolute increase in exposed nodes within the next 5 or 10 misconfiguration events.
    metrics_with_labels = compute_jump_labels(metrics_with_alarms)

    return metrics_with_alarms, thresholds

