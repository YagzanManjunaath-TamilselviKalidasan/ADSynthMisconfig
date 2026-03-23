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

    # tau_hci = None if mu_hci is None or sigma_hci is None else mu_hci + 2 * sigma_hci
    tau_hci = safe_percentile(hci_vals,95)
    # as per 1.3 -> 90th percentile
    tau_csm = safe_percentile(csm_vals, 90)
    tau_tbs = safe_percentile(tbs_vals,90)
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

    for step, row in metrics.items():
        new_row = dict(row)

        hci = row.get("HCI")
        csm = row.get("CSM")
        tbs = row.get("TBS")
        pbcc = row.get("PBCC")

        new_row["A_HCI"] = int(
            tau_hci is not None and is_valid_number(hci) and hci >= tau_hci
        )
        new_row["A_CSM"] = int(
            tau_csm is not None and is_valid_number(csm) and csm >= tau_csm
        )
        new_row["A_TBS"] = int(
            tau_tbs is not None and is_valid_number(tbs) and tbs >= tau_tbs
        )
        new_row["A_PBCC"] = int(
            tau_pbcc is not None and is_valid_number(pbcc) and pbcc >= tau_pbcc
        )

        out.append(new_row)

    return out

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


def compute_jump_labels(metrics: List[Dict]) -> List[Dict]:
    configs = [(5, 0.005),
(5, 0.01),
(10, 0.01),
(10, 0.02)]

    out = [dict(row) for row in metrics]

    for k, delta in configs:
        n = len(out)
        label_name = f"J_k{k}_d{delta}"

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


def build_prediction_dataset(
    metrics: List[Dict],
    label_name: str
):
    X, y = [], []

    for row in metrics:
        label = row.get(label_name)

        feature_values = [
            row.get("HCI"),
            row.get("CSM"),
            row.get("TBS"),
            row.get("PBCC"),
            row.get("p"),
            row.get("X"),
        ]

        if label is None:
            continue
        if not all(is_valid_number(v) for v in feature_values):
            continue

        X.append(feature_values)
        y.append(int(label))

    return np.asarray(X, dtype=float), np.asarray(y, dtype=int)


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
    logging.info("Thresholds : %s",thresholds)
    print("Thresholds : %s", thresholds)
    # based om 1.3 - tau based binary alarms
    metrics_with_alarms = apply_indicator_alarms(
        misconfig_metrics_per_itr,
        thresholds
    )
    export_metrics_to_csv(metrics_with_alarms,"misconfig_metrics_with_alarms.csv")
    # a 10–20% absolute increase in exposed nodes within the next 5 or 10 misconfiguration events.
    metrics_with_labels = compute_jump_labels(metrics_with_alarms)

    return metrics_with_alarms, thresholds


def calc_thresholds_and_jump_labels(misconfig_metrics_per_itr):
    metrics_ready, thresholds = prepare_prediction_pipeline(
        misconfig_metrics_per_itr,
        baseline_fraction=0.2,
        min_points=5
    )

    print("Thresholds:")
    for k, v in thresholds.items():
        print(f"{k}: {v}")

    X_5_10, y_5_10 = build_prediction_dataset(metrics_ready, "J_k5_d0.1")
    X_5_20, y_5_20 = build_prediction_dataset(metrics_ready, "J_k5_d0.2")
    X_10_10, y_10_10 = build_prediction_dataset(metrics_ready, "J_k10_d0.1")
    X_10_20, y_10_20 = build_prediction_dataset(metrics_ready, "J_k10_d0.2")

    print("Shapes:")
    print("k=5, d=0.10:", X_5_10.shape, y_5_10.shape)
    print("k=5, d=0.20:", X_5_20.shape, y_5_20.shape)
    print("k=10, d=0.10:", X_10_10.shape, y_10_10.shape)
    print("k=10, d=0.20:", X_10_20.shape, y_10_20.shape)

    if X_5_10.shape[0] > 0:
        evaluate_logreg(X_5_10,y_5_10)



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