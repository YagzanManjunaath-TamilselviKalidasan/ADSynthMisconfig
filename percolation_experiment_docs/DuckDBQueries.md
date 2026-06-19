## 1. Experiment details 


```sql
SELECT * from experiments where experiment_id = 'exp_session_20260430_230429';
```
---

## 2. Experiment metrics per iteration


```sql

SELECT
    experiment_id,
    iteration_id,

    MIN(CASE WHEN J_k5_z2p0 = 1 THEN p END) AS first_jump_p,
    MIN(CASE WHEN J_k5_z2p0 = 1 THEN step END) AS first_jump_step,

    SUM(J_k5_z2p0) AS jump_count,

    MAX(delta_X) AS max_delta_X,

    MAX(HCI) AS max_HCI,
    MAX(CSM) AS max_CSM,
    MAX(TBS) AS max_TBS,
    MAX(PBCC) AS max_PBCC

FROM metric_steps
WHERE experiment_id = 'exp_session_20260429_144452'
  AND iteration_id = 'iter_0'
GROUP BY experiment_id, iteration_id;


```



## 3. Experiment statistics


```sql
select * from experiment_summary_stats  where experiment_id = 'exp_session_20260429_144452' and is_p_star = true;
```

## 4. Prediction statistics

```sql
select * from prediction_model_metrics where experiment_id = 'exp_mixed_20260429_111301';
```

## 5. Reachable users

```sql
select step,new_reachable_users from metric_steps WHERE experiment_id = 'exp_session_20260505_043555'
  AND iteration_id = 'iter_0' order by step;

```

## 6. Rank Best models
```sql

WITH model_summary AS (

    SELECT
        experiment_id,
        model_name,
        features,

        SUM(tp) AS total_tp,
        SUM(fp) AS total_fp,
        SUM(fn) AS total_fn,
        SUM(tn) AS total_tn,

        AVG(precision) AS avg_precision,
        AVG(recall) AS avg_recall,
        AVG(f1) AS avg_f1,
        AVG(pr_auc) AS avg_pr_auc,
        AVG(roc_auc) AS avg_roc_auc,
        AVG(detection_rate) AS avg_detection_rate,

        SUM(tp + fp) AS total_alerts

    FROM prediction_model_metrics

    WHERE status = 'completed'
      AND experiment_id LIKE '%session_seed%'

    GROUP BY
        experiment_id,
        model_name,
        features
)

SELECT
    model_name,
    features,

    COUNT(*) AS total_runs,

    SUM(total_fp) AS fp_total,
    ROUND(AVG(total_fp), 2) AS avg_fp,

    SUM(total_tp) AS tp_total,
    ROUND(AVG(total_tp), 2) AS avg_tp,

    ROUND(
        1.0 * SUM(total_fp)
        / NULLIF(SUM(total_alerts), 0),
        4
    ) AS false_positive_ratio,

    ROUND(
        1.0 * SUM(total_fp)
        / NULLIF(SUM(total_tp), 0),
        4
    ) AS fp_per_tp,

    ROUND(AVG(avg_precision), 4) AS precision,
    ROUND(AVG(avg_recall), 4) AS recall,
    ROUND(AVG(avg_f1), 4) AS f1,
    ROUND(AVG(avg_pr_auc), 4) AS pr_auc,
    ROUND(AVG(avg_detection_rate), 4) AS detection_rate

FROM model_summary

GROUP BY
    model_name,
    features

ORDER BY
    false_positive_ratio DESC,
    fp_per_tp DESC,
    precision ASC,
    pr_auc ASC;
```

## 7. Rank Worst Models

```sql

WITH model_summary AS (

    SELECT
        experiment_id,
        model_name,
        features,

        SUM(tp) AS total_tp,
        SUM(fp) AS total_fp,
        SUM(fn) AS total_fn,
        SUM(tn) AS total_tn,

        AVG(precision) AS avg_precision,
        AVG(recall) AS avg_recall,
        AVG(f1) AS avg_f1,
        AVG(pr_auc) AS avg_pr_auc,
        AVG(roc_auc) AS avg_roc_auc,
        AVG(detection_rate) AS avg_detection_rate,

        SUM(tp + fp) AS total_alerts

    FROM prediction_model_metrics

    WHERE status = 'completed'
      AND experiment_id LIKE '%session_seed%'

    GROUP BY
        experiment_id,
        model_name,
        features
)

SELECT
    model_name,
    features,

    COUNT(*) AS total_runs,

    SUM(total_fp) AS fp_total,
    ROUND(AVG(total_fp), 2) AS avg_fp,

    SUM(total_tp) AS tp_total,
    ROUND(AVG(total_tp), 2) AS avg_tp,

    ROUND(
        1.0 * SUM(total_fp)
        / NULLIF(SUM(total_alerts), 0),
        4
    ) AS false_positive_ratio,

    ROUND(
        1.0 * SUM(total_fp)
        / NULLIF(SUM(total_tp), 0),
        4
    ) AS fp_per_tp,

    ROUND(AVG(avg_precision), 4) AS precision,
    ROUND(AVG(avg_recall), 4) AS recall,
    ROUND(AVG(avg_f1), 4) AS f1,
    ROUND(AVG(avg_pr_auc), 4) AS pr_auc,
    ROUND(AVG(avg_detection_rate), 4) AS detection_rate

FROM model_summary

GROUP BY
    model_name,
    features

ORDER BY
    false_positive_ratio DESC,
    fp_per_tp DESC,
    precision ASC,
    pr_auc ASC;
```

## 8. Group transition buckets

```sql


CREATE VIEW v_percolation_seed_classification_range_norm AS
WITH seed_features AS (
  SELECT
    c.experiment_id,
    c.base_graph_name,
    c.seed_number,
    c.injection_type,
    c."mode",
    c.J_mu_g,
    c.J_mu_slope_g,
    c.p_jump_from,
    c.p_jump,
    c.p_star,
    MAX(ms.sigma2_X) AS sigma2_peak,
    ABS((
      c.p_jump - c.p_star
    )) AS jump_pstar_distance,
    MIN(ms.mu_X) AS min_mu_X,
    MAX(ms.mu_X) AS max_mu_X,
    AVG(ms.mu_X) AS avg_mu_X,
    (
      MAX(ms.mu_X) - MIN(ms.mu_X)
    ) AS mu_X_range,
    CASE
      WHEN (
        (
          (
            MAX(ms.mu_X) - MIN(ms.mu_X)
          ) > 0
        )
      )
      THEN (
        (
          c.J_mu_g / (
            MAX(ms.mu_X) - MIN(ms.mu_X)
          )
        )
      )
      ELSE NULL
    END AS range_normalised_jump,
    CASE
      WHEN (
        (
          AVG(ms.mu_X) > 0
        )
      )
      THEN (
        (
          c.J_mu_g / AVG(ms.mu_X)
        )
      )
      ELSE NULL
    END AS relative_jump_ratio,
    c.created_at
  FROM v_percolation_jump_marker AS c
  INNER JOIN v_percolation_mu_sigma AS ms
    ON (
      (
        c.experiment_id = ms.experiment_id
      )
    )
  GROUP BY
    c.experiment_id,
    c.base_graph_name,
    c.seed_number,
    c.injection_type,
    c."mode",
    c.J_mu_g,
    c.J_mu_slope_g,
    c.p_jump_from,
    c.p_jump,
    c.p_star,
    c.created_at
), thresholds AS (
  SELECT
    base_graph_name,
    injection_type,
    "mode",
    QUANTILE_CONT(sigma2_peak, 0.90) AS var_extreme
  FROM seed_features
  GROUP BY
    base_graph_name,
    injection_type,
    "mode"
)
SELECT
  s.experiment_id,
  s.base_graph_name,
  s.seed_number,
  s.injection_type,
  s."mode",
  s.J_mu_g,
  s.J_mu_slope_g,
  s.sigma2_peak,
  s.p_star,
  s.p_jump_from,
  s.p_jump,
  s.jump_pstar_distance,
  s.min_mu_X,
  s.max_mu_X,
  s.avg_mu_X,
  s.mu_X_range,
  s.range_normalised_jump,
  s.relative_jump_ratio,
  CASE
    WHEN (
      (
        (
          s.J_mu_g >= 0.05
        )
        AND (
          s.range_normalised_jump >= 0.30
        )
        AND (
          s.sigma2_peak >= t.var_extreme
        )
        AND (
          s.jump_pstar_distance <= 0.01
        )
      )
    )
    THEN (
      'Strong percolation-like transition'
    )
    WHEN (
      (
        s.range_normalised_jump < 0.05
      )
    )
    THEN (
      'Weak transition behaviour'
    )
    ELSE 'Moderate transition behaviour'
  END AS transition_bucket,
  t.var_extreme,
  s.created_at
FROM seed_features AS s
INNER JOIN thresholds AS t
  ON (
    (
      (
        s.base_graph_name = t.base_graph_name
      )
      AND (
        s.injection_type = t.injection_type
      )
      AND (
        s."mode" = t."mode"
      )
    )
  );


CREATE VIEW v_percolation_seed_classification_range_norm_one AS
WITH ranked AS (
  SELECT
    *,
    ROW_NUMBER() OVER (
      PARTITION BY base_graph_name, injection_type, "mode", seed_number
      ORDER BY created_at DESC, experiment_id DESC
    ) AS rn
  FROM v_percolation_seed_classification_range_norm
)
SELECT
  *
FROM ranked
WHERE
  (
    rn = 1
  )
```


```sql
SELECT
    base_graph_name,
    injection_type,
    mode,
    transition_bucket,
    COUNT(*) AS seed_count,
    AVG(J_mu_g) AS avg_J_mu_g,
    AVG(range_normalised_jump) AS avg_range_normalised_jump,
    AVG(sigma2_peak) AS avg_sigma2_peak
FROM v_percolation_seed_classification_range_norm_one
GROUP BY
    base_graph_name,
    injection_type,
    mode,
    transition_bucket
ORDER BY
    base_graph_name,
    injection_type,
    mode,
    transition_bucket;
```
---

## 9. Mitigation activity over steps


```sql

CREATE VIEW v_metric_steps_with_mitigation AS SELECT v.*, ms.mitigation_enabled, ms.mitigation_condition, ms.mitigation_budget, ms.alarm_triggered, ms.mitigation_removed, ms.used_mitigation_cost, ms.removed_mitigation_count, ms.last_removed_edge_label, ms.last_removed_edge_cost, ms.last_removed_edge_advantage, ms.last_removed_edge_score FROM v_metric_steps AS v LEFT JOIN online_mitigation_steps AS ms ON (((v.experiment_id = ms.experiment_id) AND (v.injection_type = ms.injection_type) AND (v.iteration_id = ms.iteration_id) AND (v.step = ms.step)));

	
	SELECT
    experiment_id,
    injection_type,
    iteration_id,
    step,
    p,
    X,
    HCI,
    CSM,
    TBS,
    PBCC,
    alarm_triggered,
    mitigation_removed,
    used_mitigation_cost,
    removed_mitigation_count,
    last_removed_edge_label
FROM v_metric_steps_with_mitigation
WHERE experiment_id = 'exp_session_20260602_003825'
ORDER BY iteration_id, step;
```
---
## 10. Alarm and mitigation count per step

```sql
SELECT
    experiment_id,
    injection_type,
    step,
    p,
    SUM(alarm_triggered) AS alarm_count,
    SUM(mitigation_removed) AS mitigation_removed_count,
    AVG(X) AS avg_X,
    AVG(HCI) AS avg_HCI,
    AVG(CSM) AS avg_CSM,
    AVG(TBS) AS avg_TBS,
    AVG(PBCC) AS avg_PBCC
FROM v_metric_steps_with_mitigation
WHERE experiment_id = 'exp_session_20260602_003825'
GROUP BY
    experiment_id,
    injection_type,
    step,
    p
ORDER BY step;
```

---
## 11. Cumulative mitigation cost

```sql
SELECT
    experiment_id,
    injection_type,
    iteration_id,
    step,
    p,
    used_mitigation_cost,
    removed_mitigation_count,
    X
FROM v_metric_steps_with_mitigation
WHERE experiment_id = 'exp_session_20260602_003825'
ORDER BY iteration_id, step;
```
---
## 12. Compare unmitigated vs mitigated mean exposure

```sql
WITH base AS (
    SELECT
        p,
        mu_X AS mu_X_unmitigated,
        sigma2_X AS sigma2_X_unmitigated,
        p_star AS p_star_unmitigated
    FROM experiment_summary_stats
    WHERE experiment_id = 'exp_session_20260526_094504'
),

mit AS (
    SELECT
        p,
        mu_X AS mu_X_mitigated,
        sigma2_X AS sigma2_X_mitigated,
        p_star AS p_star_mitigated
    FROM experiment_summary_stats
    WHERE experiment_id = 'exp_session_20260602_003825'
)

SELECT
    COALESCE(base.p, mit.p) AS p,

    base.mu_X_unmitigated,
    mit.mu_X_mitigated,
    base.mu_X_unmitigated - mit.mu_X_mitigated AS exposure_reduction,

    base.sigma2_X_unmitigated,
    mit.sigma2_X_mitigated,
    base.sigma2_X_unmitigated - mit.sigma2_X_mitigated AS variance_reduction,

    base.p_star_unmitigated,
    mit.p_star_mitigated,
    mit.p_star_mitigated - base.p_star_unmitigated AS delta_p_star

FROM base
FULL OUTER JOIN mit
    ON base.p = mit.p
ORDER BY p;
```

---
## 13. Variance peak

```sql
WITH base AS (
    SELECT
        p,
        sigma2_X AS sigma2_X_unmitigated,
        is_p_star AS is_p_star_unmitigated
    FROM experiment_summary_stats
    WHERE experiment_id = 'exp_session_20260526_094504'
),

mit AS (
    SELECT
        p,
        sigma2_X AS sigma2_X_mitigated,
        is_p_star AS is_p_star_mitigated
    FROM experiment_summary_stats
    WHERE experiment_id = 'exp_session_20260602_003825'
)

SELECT
    COALESCE(base.p, mit.p) AS p,
    base.sigma2_X_unmitigated,
    mit.sigma2_X_mitigated,
    base.sigma2_X_unmitigated - mit.sigma2_X_mitigated AS variance_reduction,
    base.is_p_star_unmitigated,
    mit.is_p_star_mitigated
FROM base
FULL OUTER JOIN mit
    ON base.p = mit.p
ORDER BY p;
```

---
## 14. Variance peak intensity

```
WITH base AS (
    SELECT
        p,
        sigma2_X AS sigma2_X_unmitigated,
        is_p_star AS is_p_star_unmitigated
    FROM experiment_summary_stats
    WHERE experiment_id = 'exp_session_20260526_094504'
),

mit AS (
    SELECT
        p,
        sigma2_X AS sigma2_X_mitigated,
        is_p_star AS is_p_star_mitigated
    FROM experiment_summary_stats
    WHERE experiment_id = 'exp_session_20260602_003825'
)

SELECT
    COALESCE(base.p, mit.p) AS p,
    base.sigma2_X_unmitigated,
    mit.sigma2_X_mitigated,
    base.sigma2_X_unmitigated - mit.sigma2_X_mitigated AS variance_reduction,
    base.is_p_star_unmitigated,
    mit.is_p_star_mitigated
FROM base
FULL OUTER JOIN mit
    ON base.p = mit.p
ORDER BY p;
```
---

## 15. Compare unmitigated vs mitigated
```
SELECT
    experiment_id,
    injection_type,
    COUNT(*) AS total_steps,
    SUM(alarm_triggered) AS alarm_steps,
    SUM(mitigation_removed) AS mitigation_action_steps,
    MAX(used_mitigation_cost) AS final_used_cost,
    MAX(removed_mitigation_count) AS total_removed_edges,
    AVG(X) AS avg_X,
    MAX(X) AS max_X,
    AVG(HCI) AS avg_HCI,
    AVG(CSM) AS avg_CSM,
    AVG(TBS) AS avg_TBS,
    AVG(PBCC) AS avg_PBCC
FROM v_metric_steps_with_mitigation
WHERE experiment_id = 'exp_session_20260602_003825'
GROUP BY
    experiment_id,
    injection_type;
```

```

WITH base AS (
  SELECT
    p,
    mu_X AS value,
    'Unmitigated' AS policy
  FROM experiment_summary_stats
  WHERE
    experiment_id = 'exp_session_20260602_004901'
), mit AS (
  SELECT
    p,
    mu_X AS value,
    'Mitigated' AS policy
  FROM experiment_summary_stats
  WHERE
    experiment_id = 'exp_session_20260602_004352'
)
SELECT
  *
FROM base
UNION ALL
SELECT
  *
FROM mit
ORDER BY
  p
```

```
WITH base AS (
    SELECT
        p,
        sigma2_X AS value,
        'Unmitigated' AS policy
    FROM experiment_summary_stats
    WHERE experiment_id = 'exp_session_20260602_004901'
),

mit AS (
    SELECT
        p,
        sigma2_X AS value,
        'Mitigated' AS policy
    FROM experiment_summary_stats
    WHERE experiment_id = 'exp_session_20260602_004352'
)

SELECT * FROM base
UNION ALL
SELECT * FROM mit
ORDER BY p;
```





