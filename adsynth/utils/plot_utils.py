import math
import os
import tempfile

import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.io as pio
import numpy as np
import os
from filelock import FileLock
import pandas as pd
import duckdb

import pandas as pd
import duckdb
from adsynth.utils.ablation_study_utils import add_rise_period_metrics


def plot_plot_chart(x_values, y_values, x_label, y_label, title, additional_info, plot_type):
    plt.figure(figsize=(8, 5))
    try:
        match plot_type:
            case "line":
                plt.plot(x_values, y_values, linestyle='-', linewidth=1, color='tab:blue')
            case "bar":
                plt.bar(x_values, y_values, color='tab:green')
            case "scatter":
                plt.scatter(x_values, y_values, color='tab:red', s=60)
            case _:
                return "Error"

        text = "\n".join([f"{k} = {v}" for k, v in additional_info.items()])
        plt.gca().text(
            0.02, 0.98, text,
            transform=plt.gca().transAxes,  # relative to axes
            fontsize=8, color="black",
            ha="left", va="top",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="wheat", alpha=0.5)
        )
        plt.title(title)
        plt.xlabel(x_label)
        plt.ylabel(y_label)
        plt.grid(True, linestyle='--', alpha=0.6)
        plt.show()
    except Exception as e:
        print(e)


import plotly.graph_objects as go
import plotly.io as pio


def plot_chart_using_plotly(
        x_values,
        y_values,
        x_label,
        y_label,
        title,
        file_name,
        additional_info: dict[str, str],
        plot_type: str = "line",
        hover_texts: list[str] | None = None,

):
    # pio.renderers.default = "browser"
    fig = go.Figure()

    match plot_type:
        case "line":
            fig.add_trace(go.Scatter(
                x=x_values,
                y=y_values,
                mode="lines+markers",
                line=dict(color="royalblue", width=2),
                marker=dict(size=8),
                # customdata=hover_texts if hover_texts else ["No extra info"] * len(x_values),
                hovertemplate=(
                    f"{x_label}: %{{x}}<br>"
                    f"{y_label}: %{{y}}<br>"
                    # "<b>Details:</b><br>%{customdata}<extra></extra>"
                )
            ))
        case "bar":
            fig.add_trace(go.Bar(
                x=x_values,
                y=y_values,
                marker_color="mediumseagreen",
                customdata=hover_texts if hover_texts else ["No extra info"] * len(x_values),
                hovertemplate=(
                    f"{x_label}: %{{x}}<br>"
                    f"{y_label}: %{{y}}<br>"
                    "<b>Details:</b><br>%{customdata}<extra></extra>"
                )
            ))
        case "scatter":
            fig.add_trace(go.Scatter(
                x=x_values,
                y=y_values,
                mode="markers",
                marker=dict(size=10, color="tomato"),
                customdata=hover_texts if hover_texts else ["No extra info"] * len(x_values),
                hovertemplate=(
                    f"{x_label}: %{{x}}<br>"
                    f"{y_label}: %{{y}}<br>"
                    "<b>Details:</b><br>%{customdata}<extra></extra>"
                )
            ))
        case _:
            raise ValueError(f"Unsupported plot type: {plot_type}")

    annotation_text = "<br>".join([f"{k} = {v}" for k, v in additional_info.items()])

    fig.add_annotation(
        text=annotation_text,
        xref="paper", yref="paper",
        x=0.02, y=0.98,
        showarrow=False,
        font=dict(size=12, family="Arial"),
        align="left",
        bgcolor="rgba(245,245,245,0.8)",
        bordercolor="black",
        borderwidth=1,
    )

    # --- layout styling ---
    fig.update_layout(
        title=title,
        xaxis_title=x_label,
        yaxis_title=y_label,
        template="plotly_white",
        showlegend=False,
        height=600,
        margin=dict(l=60, r=40, t=80, b=60)
    )

    save_path = f"/Users/yagzanmanjunaath/UniWorkspace/ResearchMethods/Part2/ADSynth/generated_datasets/{file_name}.html"

    if file_name:
        fig.write_html(save_path)

    # fig.show()


def plot_bar_graph_per_itr_using_plotty(itr, misconfig_metrics_per_itr):
    exp_data = misconfig_metrics_per_itr[itr]

    steps = np.array([int(k) for k in exp_data.keys()])
    user_counts = np.array([v["reachable_users_count"] for v in exp_data.values()])

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=steps,
        y=user_counts,
        name="Reachable Users",
        marker_color="steelblue",
        hovertemplate="Step %{x}<br>Users: %{y}<extra></extra>"
    ))

    fig.update_layout(
        title="Number of Reachable Users per Misconfiguration Step",
        xaxis_title="Misconfiguration Step",
        yaxis_title="Reachable Users Count",
        template="plotly_white",
        hovermode="x unified",
        height=600,
        bargap=0.2,
        legend=dict(orientation="h", y=-0.2)
    )

    fig.show()


def plot_box_plot_using_plotty(
        misconfig_metrics_per_itr,
        title,
        x_axis_title,
        y_axis_title,
        file_name,
        additional_info: dict[str, str],
        user_map: dict[int, dict[int, list[str]]] | None = None,  # optional mapping
):
    # pio.renderers.default = "browser"
    all_misconfigs = list(range(1, 65))

    fig = go.Figure()

    for misconfig in all_misconfigs:
        counts = []
        hover_users = []
        for it in misconfig_metrics_per_itr:
            if misconfig in misconfig_metrics_per_itr[it]:
                val = misconfig_metrics_per_itr[it][misconfig]["reachable_users_count"]
                counts.append(val)

                if user_map and it in user_map and misconfig in user_map[it]:
                    current_users = set(user_map[it][misconfig])

                    prev_misconfigs = sorted([m for m in user_map[it].keys() if m < misconfig])
                    if prev_misconfigs:
                        last_prev = prev_misconfigs[-1]
                        prev_users = set(user_map[it][last_prev])
                        new_users = current_users - prev_users
                    else:
                        new_users = current_users

                    if new_users:
                        hover_text = "<br>".join(list(new_users)[:10])
                    else:
                        hover_text = "No new users added"
                else:
                    hover_text = "No users listed"

                hover_users.append(hover_text)

        if not counts:
            continue

        fig.add_trace(go.Box(
            y=counts,
            name=str(misconfig),
            boxmean=True,
            fillcolor='rgba(100,149,237,0.4)',
            line_color='royalblue',
            marker_color='royalblue',
            boxpoints='outliers',
            jitter=0.3,
            whiskerwidth=0.2,
            customdata=hover_users,
            hovertemplate=(
                "Misconfig %{x}<br>"
                "Reachable Users: %{y}<br>"
                # "<b>Users:</b><br>%{customdata}<extra></extra>"
            ),
        )
        )

    annotation_text = "<br>".join([f"{k} = {v}" for k, v in additional_info.items()])

    fig.add_annotation(
        text=annotation_text,
        xref="paper", yref="paper",
        x=0.02, y=0.98,
        showarrow=False,
        font=dict(size=12, family="Arial"),
        align="left",
        bgcolor="rgba(245,245,245,0.8)",
        bordercolor="black",
        borderwidth=1,
    )

    fig.update_layout(
        title=title,
        xaxis_title=x_axis_title,
        yaxis_title=y_axis_title,
        template="plotly_white",
        showlegend=False,
        height=700
    )

    save_path = f"/Users/yagzanmanjunaath/UniWorkspace/ResearchMethods/Part2/ADSynth/generated_datasets/{file_name}.html"

    if file_name:
        fig.write_html(save_path)
    # fig.show()


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


def plot_metrics(num_users, num_computers, num_misconfig, base_filename, misconfig_growth_metrics):
    steps = sorted(misconfig_growth_metrics.keys())

    # x axis
    x_values = [misconfig_growth_metrics[s]["p"] for s in steps]

    additional_info = {
        "Total users": num_users,
        "Total computers": num_computers,
        "Num misconfigs": num_misconfig,
        "Base file": base_filename,
    }

    metrics = {
        "X": "Exposure X(p)",
        "HCI": "HCI",
        "CSM": "CSM",
        "TBS": "TBS",
        "pbcc": "PBCC",

    }

    for metric_key, metric_name in metrics.items():
        y_values = [misconfig_growth_metrics[s][metric_key] for s in steps]

        plot_plot_chart(
            x_values=x_values,
            y_values=y_values,
            x_label="p",
            y_label=metric_name,
            title=f"{metric_name} vs Misconfiguration Level",
            additional_info=additional_info,
            plot_type="line"
        )

    steps = sorted(misconfig_growth_metrics.keys())
    p_values = [misconfig_growth_metrics[s]["p"] for s in steps]
    y_values = [len(misconfig_growth_metrics[s]["reachable_comps"]) for s in steps]
    y_values = [len(misconfig_growth_metrics[s]["reachable_users"]) for s in steps]
    # choose a few ticks so labels do not overlap
    tick_positions = np.linspace(min(steps), max(steps), 6, dtype=int)
    tick_positions = sorted(set(tick_positions))

    p_map = dict(zip(steps, p_values))
    ticktext_top = [f"{p_map[t]:.3f}" for t in tick_positions]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=steps,
        y=y_values,
        mode="lines+markers",
        name="reachable_comps"
    ))

    fig.update_layout(
        title="Reachable Comps",
        xaxis=dict(
            title="step",
            tickmode="array",
            tickvals=tick_positions
        ),
        xaxis2=dict(
            title="p",
            overlaying="x",
            side="top",
            tickmode="array",
            tickvals=tick_positions,
            ticktext=ticktext_top
        ),
        yaxis=dict(title="reachable_comps"),
        template="plotly_white"
    )

    fig.show()

    fig.update_layout(
        title="Reachable Users",
        xaxis=dict(
            title="step",
            tickmode="array",
            tickvals=tick_positions
        ),
        xaxis2=dict(
            title="p",
            overlaying="x",
            side="top",
            tickmode="array",
            tickvals=tick_positions,
            ticktext=[f"{p_map[t]:.3f}" for t in tick_positions]
        ),
        yaxis=dict(title="reachable_users"),
        template="plotly_white"
    )

    fig.show()


import pandas as pd
import numbers

import pandas as pd
import numbers

import pandas as pd

import math
import tempfile
from collections import defaultdict

import pandas as pd
import matplotlib.pyplot as plt

import math
import tempfile
from collections import defaultdict

import pandas as pd
import matplotlib.pyplot as plt


def export_metrics_to_excel(metrics_data, filename, x_axis="step", metadata=None):
    metric_titles = {
        "X": "Exposure X(p)",
        "HCI": "HCI",
        "CSM": "CSM",
        "TBS": "TBS",
        "pbcc": "PBCC",
    }

    cols_to_separate = [
        "reachable_users",
        "new_reachable_users",
        "reachable_comps",
        "new_reachable_comps_names",
        "reachable_comps_names",
    ]

    rise_metric_keys = ["HCI", "CSM", "TBS"]

    # --------------------------------------------------
    # Helpers
    # --------------------------------------------------
    def safe_sheet_name(name):
        invalid = ['[', ']', ':', '*', '?', '/', '\\']
        for ch in invalid:
            name = name.replace(ch, "_")
        return name[:31]

    def write_dataframe(ws, df, header_fmt):
        for col_num, value in enumerate(df.columns):
            ws.write(0, col_num, value, header_fmt)
            width = max(16, len(str(value)) + 2)
            ws.set_column(col_num, col_num, width)

    def build_chart_title(main_title, metadata=None):
        if not metadata:
            return main_title
        meta_parts = [f"{k}: {v}" for k, v in metadata.items()]
        return f"{main_title}\n" + " | ".join(meta_parts)

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

    def normalize_metrics(metrics_data):
        """
        Supports:
        1. list of dicts
        2. dict of step -> row
        3. dict of run -> dict(step -> row)
        """
        rows = []

        if isinstance(metrics_data, list):
            for step, row in enumerate(metrics_data, start=1):
                new_row = dict(row)
                new_row["run"] = 0
                new_row["step"] = step
                rows.append(new_row)

        elif isinstance(metrics_data, dict):
            if not metrics_data:
                return pd.DataFrame()

            first_val = next(iter(metrics_data.values()))

            if isinstance(first_val, dict) and ("X" in first_val or "HCI" in first_val):
                for step, row in metrics_data.items():
                    new_row = dict(row)
                    new_row["run"] = 0
                    new_row["step"] = step
                    rows.append(new_row)
            else:
                for run_id, step_dict in metrics_data.items():
                    if not isinstance(step_dict, dict):
                        continue
                    for step, row in step_dict.items():
                        new_row = dict(row)
                        new_row["run"] = run_id
                        new_row["step"] = step
                        rows.append(new_row)
        else:
            raise TypeError("metrics_data must be a list or dict")

        df = pd.DataFrame(rows)
        if not df.empty:
            df = df.sort_values(["run", "step"]).reset_index(drop=True)
        return df

    def add_deltas_and_scaled(metrics_dict, metric_keys):
        steps = sorted(metrics_dict.keys())
        prev_row = None

        for step in steps:
            row = metrics_dict[step]
            for metric_key in metric_keys:
                curr_val = row.get(metric_key, 0)

                if prev_row is None:
                    row[f"delta_{metric_key}"] = 0
                else:
                    prev_val = prev_row.get(metric_key, 0)
                    if isinstance(curr_val, (int, float)) and isinstance(prev_val, (int, float)):
                        row[f"delta_{metric_key}"] = curr_val - prev_val
                    else:
                        row[f"delta_{metric_key}"] = None
            prev_row = row

        all_keys = list(metric_keys) + [f"delta_{k}" for k in metric_keys]

        for key in all_keys:
            values = [
                metrics_dict[s].get(key)
                for s in steps
                if isinstance(metrics_dict[s].get(key), (int, float))
            ]
            if not values:
                continue

            min_val = min(values)
            max_val = max(values)

            if math.isclose(min_val, max_val):
                for s in steps:
                    metrics_dict[s][f"scaled_{key}"] = 0.0
                continue

            for s in steps:
                val = metrics_dict[s].get(key)
                if isinstance(val, (int, float)):
                    metrics_dict[s][f"scaled_{key}"] = (val - min_val) / (max_val - min_val)
                else:
                    metrics_dict[s][f"scaled_{key}"] = None

        return metrics_dict

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

    def add_run_level_deltas(df):
        if "reachable_users_count" in df.columns:
            df["delta_reachable_users_count"] = (
                df.groupby("run")["reachable_users_count"]
                .diff()
                .fillna(df["reachable_users_count"])
            )

        if "reachable_comps_count" in df.columns:
            df["delta_reachable_comps_count"] = (
                df.groupby("run")["reachable_comps_count"]
                .diff()
                .fillna(df["reachable_comps_count"])
            )
        return df

    def insert_correlation_heatmap(worksheet, df, cell="J2", title="Correlation Heatmap"):
        numeric_df = df.select_dtypes(include=["number"]).copy()
        if numeric_df.empty or numeric_df.shape[1] < 2:
            return

        corr = numeric_df.corr(method="pearson")

        fig, ax = plt.subplots(figsize=(10, 8))
        im = ax.imshow(corr.values, aspect="auto", interpolation="nearest")
        ax.set_xticks(range(len(corr.columns)))
        ax.set_xticklabels(corr.columns, rotation=90)
        ax.set_yticks(range(len(corr.index)))
        ax.set_yticklabels(corr.index)
        ax.set_title(title)

        for i in range(len(corr.index)):
            for j in range(len(corr.columns)):
                ax.text(j, i, f"{corr.iloc[i, j]:.2f}", ha="center", va="center", fontsize=8)

        fig.colorbar(im, ax=ax)
        fig.tight_layout()

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        tmp_path = tmp.name
        tmp.close()

        fig.savefig(tmp_path, bbox_inches="tight", dpi=180)
        plt.close(fig)
        worksheet.insert_image(cell, tmp_path)

    def make_line_chart(workbook, sheet_name, df, x_col, y_cols, title, y_axis_name):
        chart = workbook.add_chart({"type": "line"})
        x_idx = df.columns.get_loc(x_col)
        nrows = len(df)

        for y_col in y_cols:
            if y_col not in df.columns:
                continue
            y_idx = df.columns.get_loc(y_col)
            chart.add_series({
                "name": [sheet_name, 0, y_idx],
                "categories": [sheet_name, 1, x_idx, nrows, x_idx],
                "values": [sheet_name, 1, y_idx, nrows, y_idx],
            })

        chart.set_title({"name": title})
        chart.set_x_axis({"name": x_col})
        chart.set_y_axis({"name": y_axis_name})
        return chart

    def make_scatter_chart(workbook, sheet_name, df, x_col, y_cols, title, y_axis_name):
        chart = workbook.add_chart({"type": "scatter", "subtype": "straight"})
        x_idx = df.columns.get_loc(x_col)
        nrows = len(df)

        for y_col in y_cols:
            if y_col not in df.columns:
                continue
            y_idx = df.columns.get_loc(y_col)
            chart.add_series({
                "name": [sheet_name, 0, y_idx],
                "categories": [sheet_name, 1, x_idx, nrows, x_idx],
                "values": [sheet_name, 1, y_idx, nrows, y_idx],
            })

        chart.set_title({"name": title})
        chart.set_x_axis({"name": x_col})
        chart.set_y_axis({"name": y_axis_name})
        return chart

    def compute_correlation_table(df, exposure_col, metric_cols):
        rows = []
        if exposure_col not in df.columns:
            return pd.DataFrame()

        for col in metric_cols:
            if col not in df.columns:
                continue

            pair_df = df[[exposure_col, col]].dropna()
            if len(pair_df) < 2:
                continue

            rows.append({
                "metric": col,
                "n": len(pair_df),
                "pearson_corr_with_X": pair_df[exposure_col].corr(pair_df[col], method="pearson"),
                "spearman_corr_with_X": pair_df[exposure_col].corr(pair_df[col], method="spearman"),
                "kendall_corr_with_X": pair_df[exposure_col].corr(pair_df[col], method="kendall"),
            })

        if not rows:
            return pd.DataFrame()

        return pd.DataFrame(rows).sort_values(
            by="pearson_corr_with_X",
            key=lambda s: s.abs(),
            ascending=False
        )

    def write_details_sheet(writer, df_run_full, run_id, header_fmt):
        detail_cols = ["step"] + [col for col in cols_to_separate if col in df_run_full.columns]
        if len(detail_cols) <= 1:
            return

        df_details = df_run_full[detail_cols].copy()
        for col in cols_to_separate:
            if col in df_details.columns:
                df_details[col] = df_details[col].apply(
                    lambda x: "\n".join(map(str, x)) if isinstance(x, (list, tuple, set)) else x
                )

        details_sheet = safe_sheet_name(f"r{run_id}_details")
        df_details.to_excel(writer, sheet_name=details_sheet, index=False)
        ws = writer.sheets[details_sheet]
        write_dataframe(ws, df_details, header_fmt)

        for col_idx, col_name in enumerate(df_details.columns):
            if col_name != "step":
                ws.set_column(col_idx, col_idx, 40)

    def write_summary_sheet(writer, workbook, df_main, run_id, x_plot_col, header_fmt):
        summary_cols = [c for c in [
            x_plot_col, "X", "HCI", "CSM", "TBS", "pbcc",
            "rise_streak_HCI", "rise_streak_CSM", "rise_streak_TBS"
        ] if c in df_main.columns]

        if len(summary_cols) < 2:
            return

        df_summary = df_main[summary_cols].copy()
        sheet_name = safe_sheet_name(f"r{run_id}_summary")
        df_summary.to_excel(writer, sheet_name=sheet_name, index=False)
        ws = writer.sheets[sheet_name]
        write_dataframe(ws, df_summary, header_fmt)

        chart = make_line_chart(
            workbook,
            sheet_name,
            df_summary,
            x_plot_col,
            [c for c in ["X", "HCI", "CSM", "TBS"] if c in df_summary.columns],
            f"Core metrics vs {x_plot_col} (run {run_id})",
            "Metric value",
        )
        ws.insert_chart("J2", chart, {"x_scale": 1.6, "y_scale": 1.3})

    def write_normalized_comparison_sheet(writer, workbook, df_main, run_id, x_plot_col, header_fmt):
        needed = [c for c in ["X", "HCI", "CSM", "TBS"] if c in df_main.columns]
        if len(needed) < 2:
            return

        df_compare = df_main[[x_plot_col] + needed].copy()
        for c in needed:
            df_compare[f"norm_{c}"] = minmax_normalize_series(df_compare[c])

        export_cols = [x_plot_col] + [f"norm_{c}" for c in needed]
        sheet_name = safe_sheet_name(f"r{run_id}_norm_compare")
        df_compare[export_cols].to_excel(writer, sheet_name=sheet_name, index=False)

        ws = writer.sheets[sheet_name]
        write_dataframe(ws, df_compare[export_cols], header_fmt)

        # all three + X in same graph
        chart = make_line_chart(
            workbook,
            sheet_name,
            df_compare[export_cols],
            x_plot_col,
            [c for c in ["norm_X", "norm_HCI", "norm_CSM", "norm_TBS"] if c in df_compare.columns],
            f"Normalised X, HCI, CSM, TBS vs {x_plot_col} (run {run_id})",
            "Normalised value (0-1)",
        )
        chart.set_y_axis({"name": "Normalised value (0-1)", "min": 0, "max": 1})
        ws.insert_chart("H2", chart, {"x_scale": 1.7, "y_scale": 1.4})

    def write_rise_sheet(writer, workbook, df_main, run_id, x_plot_col, header_fmt):
        rise_cols = [c for c in [
            x_plot_col,
            "HCI", "CSM", "TBS",
            "rise_flag_HCI", "rise_flag_CSM", "rise_flag_TBS",
            "rise_streak_HCI", "rise_streak_CSM", "rise_streak_TBS",
            "rise_total_HCI", "rise_total_CSM", "rise_total_TBS",
            "X",
        ] if c in df_main.columns]

        if len(rise_cols) <= 1:
            return

        df_rise = df_main[rise_cols].copy()
        sheet_name = safe_sheet_name(f"r{run_id}_rise")
        df_rise.to_excel(writer, sheet_name=sheet_name, index=False)

        ws = writer.sheets[sheet_name]
        write_dataframe(ws, df_rise, header_fmt)

        streak_chart = make_line_chart(
            workbook,
            sheet_name,
            df_rise,
            x_plot_col,
            [c for c in ["rise_streak_HCI", "rise_streak_CSM", "rise_streak_TBS"] if c in df_rise.columns],
            f"Rise streaks vs {x_plot_col} (run {run_id})",
            "Rise streak",
        )
        ws.insert_chart("S2", streak_chart, {"x_scale": 1.5, "y_scale": 1.2})

        if "X" in df_rise.columns:
            xp_cols = ["X"] + [c for c in ["rise_streak_HCI", "rise_streak_CSM", "rise_streak_TBS"] if
                               c in df_rise.columns]
            df_xp = df_rise[xp_cols].copy()

            scatter = make_scatter_chart(
                workbook,
                sheet_name,
                df_xp,
                "X",
                [c for c in ["rise_streak_HCI", "rise_streak_CSM", "rise_streak_TBS"] if c in df_xp.columns],
                f"Rise streaks vs X(p) (run {run_id})",
                "Rise streak",
            )
            ws.insert_chart("S22", scatter, {"x_scale": 1.5, "y_scale": 1.2})

    def write_correlation_sheet(writer, workbook, df_main, run_id, header_fmt):
        corr_targets = [
            "HCI", "CSM", "TBS", "pbcc",
            "delta_HCI", "delta_CSM", "delta_TBS", "delta_pbcc",
            "scaled_HCI", "scaled_CSM", "scaled_TBS", "scaled_pbcc",
            "rise_flag_HCI", "rise_flag_CSM", "rise_flag_TBS",
            "rise_streak_HCI", "rise_streak_CSM", "rise_streak_TBS",
            "rise_total_HCI", "rise_total_CSM", "rise_total_TBS",
            "reachable_users_count", "reachable_comps_count",
            "delta_reachable_users_count", "delta_reachable_comps_count",
        ]

        df_corr = compute_correlation_table(df_main, "X", corr_targets)
        if df_corr.empty:
            return

        sheet_name = safe_sheet_name(f"r{run_id}_corr")
        df_corr.to_excel(writer, sheet_name=sheet_name, index=False)
        ws = writer.sheets[sheet_name]
        write_dataframe(ws, df_corr, header_fmt)

        chart = workbook.add_chart({"type": "column"})
        nrows = len(df_corr)

        metric_idx = df_corr.columns.get_loc("metric")
        pearson_idx = df_corr.columns.get_loc("pearson_corr_with_X")
        spearman_idx = df_corr.columns.get_loc("spearman_corr_with_X")
        kendall_idx = df_corr.columns.get_loc("kendall_corr_with_X")

        for idx in [pearson_idx, spearman_idx, kendall_idx]:
            chart.add_series({
                "name": [sheet_name, 0, idx],
                "categories": [sheet_name, 1, metric_idx, nrows, metric_idx],
                "values": [sheet_name, 1, idx, nrows, idx],
            })

        chart.set_title({"name": f"Correlation of metrics with Exposure X (run {run_id})"})
        chart.set_x_axis({"name": "Metric"})
        chart.set_y_axis({"name": "Correlation Coefficient", "min": -1, "max": 1})
        ws.insert_chart("G2", chart, {"x_scale": 1.6, "y_scale": 1.4})

    def write_heatmap_sheet(writer, df_main, run_id, header_fmt):
        heatmap_cols = [c for c in [
            "X", "HCI", "CSM", "TBS", "pbcc",
            "delta_HCI", "delta_CSM", "delta_TBS", "delta_pbcc",
            "rise_streak_HCI", "rise_streak_CSM", "rise_streak_TBS",
            "rise_total_HCI", "rise_total_CSM", "rise_total_TBS",
        ] if c in df_main.columns]

        if len(heatmap_cols) < 2:
            return

        df_heat = df_main[heatmap_cols].copy()
        sheet_name = safe_sheet_name(f"r{run_id}_heatmap")
        df_heat.to_excel(writer, sheet_name=sheet_name, index=False)

        ws = writer.sheets[sheet_name]
        write_dataframe(ws, df_heat, header_fmt)
        insert_correlation_heatmap(ws, df_heat, cell="P2", title=f"X-focused Correlation Heatmap (run {run_id})")

    def write_metric_sheets(writer, workbook, df_main, run_id, x_plot_col, header_fmt):
        # core sheets only
        for metric_key in ["X", "HCI", "CSM", "TBS", "pbcc"]:
            if metric_key not in df_main.columns:
                continue

            plot_cols = [x_plot_col, metric_key]
            for extra in [f"delta_{metric_key}", f"scaled_{metric_key}"]:
                if extra in df_main.columns:
                    plot_cols.append(extra)

            plot_cols = list(dict.fromkeys(plot_cols))
            metric_df = df_main[plot_cols].copy()

            sheet_name = safe_sheet_name(f"r{run_id}_{metric_key}")
            metric_df.to_excel(writer, sheet_name=sheet_name, index=False)

            ws = writer.sheets[sheet_name]
            write_dataframe(ws, metric_df, header_fmt)

            # main chart against step or p
            chart_main = make_line_chart(
                workbook,
                sheet_name,
                metric_df,
                x_plot_col,
                [c for c in metric_df.columns if c != x_plot_col],
                build_chart_title(f"{metric_key} vs {x_plot_col} (run {run_id})", metadata),
                metric_key,
            )
            ws.insert_chart("H2", chart_main, {"x_scale": 1.5, "y_scale": 1.2})

            # NEW: actual-value graph against X(p)
            # only for non-X metrics, and only if X exists
            if metric_key != "X" and "X" in df_main.columns:
                xp_cols = ["X", metric_key]
                if f"delta_{metric_key}" in df_main.columns:
                    xp_cols.append(f"delta_{metric_key}")
                if f"scaled_{metric_key}" in df_main.columns:
                    xp_cols.append(f"scaled_{metric_key}")

                df_xp = df_main[xp_cols].copy()

                xp_sheet_name = safe_sheet_name(f"r{run_id}_{metric_key}_xp")
                df_xp.to_excel(writer, sheet_name=xp_sheet_name, index=False)

                ws_xp = writer.sheets[xp_sheet_name]
                write_dataframe(ws_xp, df_xp, header_fmt)

                # actual value vs X(p)
                scatter_actual = make_scatter_chart(
                    workbook,
                    xp_sheet_name,
                    df_xp,
                    "X",
                    [metric_key],
                    build_chart_title(f"{metric_key} actual vs X(p) (run {run_id})", metadata),
                    metric_key,
                )
                ws_xp.insert_chart("H2", scatter_actual, {"x_scale": 1.5, "y_scale": 1.2})

                # optional delta/scaled against X(p) in same sheet
                extra_y_cols = [c for c in [f"delta_{metric_key}", f"scaled_{metric_key}"] if c in df_xp.columns]
                if extra_y_cols:
                    scatter_extra = make_scatter_chart(
                        workbook,
                        xp_sheet_name,
                        df_xp,
                        "X",
                        extra_y_cols,
                        build_chart_title(f"{metric_key} derived series vs X(p) (run {run_id})", metadata),
                        f"{metric_key} derived",
                    )
                    ws_xp.insert_chart("H22", scatter_extra, {"x_scale": 1.5, "y_scale": 1.2})

    # --------------------------------------------------
    # Prepare data
    # --------------------------------------------------
    metrics_to_export = add_deltas_and_scaled(metrics_data, list(metric_titles.keys()))
    metrics_to_export = add_rise_period_metrics(metrics_to_export, rise_metric_keys)

    df_full = normalize_metrics(metrics_to_export)
    if df_full.empty:
        print("No data to export")
        return

    df_full = add_run_level_deltas(df_full)

    # --------------------------------------------------
    # Write workbook
    # --------------------------------------------------
    with pd.ExcelWriter(filename, engine="xlsxwriter") as writer:
        workbook = writer.book
        header_fmt = workbook.add_format({
            "bold": True,
            "bg_color": "#D9EAF7",
            "border": 1,
        })

        run_ids = sorted(df_full["run"].unique())

        for run_id in run_ids:
            df_run_full = df_full[df_full["run"] == run_id].copy()
            df_main = df_run_full.drop(columns=cols_to_separate, errors="ignore")
            x_plot_col = "p" if (x_axis == "p" and "p" in df_main.columns) else "step"

            main_sheet = safe_sheet_name(f"run_{run_id}_data")
            df_main.to_excel(writer, sheet_name=main_sheet, index=False)
            ws_main = writer.sheets[main_sheet]
            write_dataframe(ws_main, df_main, header_fmt)

            write_details_sheet(writer, df_run_full, run_id, header_fmt)
            write_summary_sheet(writer, workbook, df_main, run_id, x_plot_col, header_fmt)
            write_normalized_comparison_sheet(writer, workbook, df_main, run_id, x_plot_col, header_fmt)
            write_rise_sheet(writer, workbook, df_main, run_id, x_plot_col, header_fmt)
            write_correlation_sheet(writer, workbook, df_main, run_id, header_fmt)
            write_heatmap_sheet(writer, df_main, run_id, header_fmt)
            write_metric_sheets(writer, workbook, df_main, run_id, x_plot_col, header_fmt)

    print(f"Dataset exported to {filename}")


def insert_correlation_heatmap(workbook, worksheet, df, cell="J2", title="Correlation Heatmap"):
    import tempfile
    import os

    numeric_df = df.select_dtypes(include=["number"]).copy()
    if numeric_df.empty or numeric_df.shape[1] < 2:
        return None

    corr = numeric_df.corr(method="pearson")

    fig, ax = plt.subplots(figsize=(10, 8))
    im = ax.imshow(corr.values, aspect="auto", interpolation="nearest")

    ax.set_xticks(range(len(corr.columns)))
    ax.set_xticklabels(corr.columns, rotation=90)
    ax.set_yticks(range(len(corr.index)))
    ax.set_yticklabels(corr.index)
    ax.set_title(title)

    # annotate values
    for i in range(len(corr.index)):
        for j in range(len(corr.columns)):
            val = corr.iloc[i, j]
            ax.text(j, i, f"{val:.2f}", ha="center", va="center", fontsize=8)

    fig.colorbar(im, ax=ax)
    fig.tight_layout()

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    tmp_path = tmp.name
    tmp.close()

    fig.savefig(tmp_path, bbox_inches="tight", dpi=180)
    plt.close(fig)

    worksheet.insert_image(cell, tmp_path)
    return tmp_path


def insert_correlation_block(ws, workbook, df, start_row):
    import pandas as pd
    import numpy as np

    features = [
        "HCI", "CSM", "TBS",
        "rise_streak_HCI", "rise_streak_CSM", "rise_streak_TBS"
    ]

    target_col = "J_k5_z2p0"
    rows = []

    if target_col not in df.columns:
        return start_row

    for f in features:
        if f not in df.columns:
            continue

        sub = df[[f, target_col]].dropna()
        if len(sub) < 2:
            continue

        rows.append({
            "feature": f,
            "target": target_col,
            "pearson": sub[f].corr(sub[target_col], method="pearson"),
            "spearman": sub[f].corr(sub[target_col], method="spearman"),
        })

    if not rows:
        return start_row

    corr_df = pd.DataFrame(rows)

    # write table
    for col_idx, col in enumerate(corr_df.columns):
        ws.write(start_row, col_idx, col)
        for r in range(len(corr_df)):
            ws.write(start_row + 1 + r, col_idx, corr_df.iloc[r, col_idx])

    # chart: correlation vs jump label
    chart = workbook.add_chart({"type": "column"})

    base_row = start_row + 1
    feature_col = corr_df.columns.get_loc("feature")
    pearson_col = corr_df.columns.get_loc("pearson")
    spearman_col = corr_df.columns.get_loc("spearman")
    n = len(corr_df)

    chart.add_series({
        "name": "pearson",
        "categories": ["analysis", base_row, feature_col, base_row + n - 1, feature_col],
        "values": ["analysis", base_row, pearson_col, base_row + n - 1, pearson_col],
    })

    chart.add_series({
        "name": "spearman",
        "categories": ["analysis", base_row, feature_col, base_row + n - 1, feature_col],
        "values": ["analysis", base_row, spearman_col, base_row + n - 1, spearman_col],
    })

    chart.set_title({"name": "Correlation with Jump Label"})
    chart.set_x_axis({"name": "Feature"})
    chart.set_y_axis({"name": "Correlation", "min": -1, "max": 1})

    ws.insert_chart(start_row, 8, chart, {
        "x_scale": 2.0,
        "y_scale": 1.2
    })

    return start_row + len(corr_df) + 5


def export_single_run_analysis_sheet(metrics_dict, filename, metadata=None):
    import pandas as pd

    # ---------- Prepare dataframe ----------
    df = pd.DataFrame.from_dict(metrics_dict, orient="index")
    if "step" in df.columns:
        df = df.drop(columns=["step"])
    df = df.sort_index().reset_index().rename(columns={"index": "step"})

    plot_cols = [
        "X", "HCI", "CSM", "TBS",
        "rise_streak_HCI", "rise_streak_CSM", "rise_streak_TBS",
        "J_k5_z2p0", "step"
    ]

    for col in plot_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "J_k5_z2p0" not in df.columns:
        raise ValueError("jump_label column required")

    # ---------- Excel writer ----------
    with pd.ExcelWriter(filename, engine="xlsxwriter") as writer:
        workbook = writer.book

        header_fmt = workbook.add_format({
            "bold": True,
            "bg_color": "#D9EAF7",
            "border": 1,
        })

        sheet_name = "analysis"
        df.to_excel(writer, sheet_name=sheet_name, index=False)
        ws = writer.sheets[sheet_name]

        # column widths
        for i, col in enumerate(df.columns):
            ws.write(0, i, col, header_fmt)
            ws.set_column(i, i, 16)

        # helpers
        def make_line_chart(x_col, y_cols, title):
            chart = workbook.add_chart({"type": "line"})
            x_idx = df.columns.get_loc(x_col)
            nrows = len(df)

            for y in y_cols:
                if y not in df.columns:
                    continue
                y_idx = df.columns.get_loc(y)
                chart.add_series({
                    "name": [sheet_name, 0, y_idx],
                    "categories": [sheet_name, 1, x_idx, nrows, x_idx],
                    "values": [sheet_name, 1, y_idx, nrows, y_idx],
                })

            chart.set_title({"name": title})
            chart.set_x_axis({"name": x_col})
            return chart

        def make_boxplot(feature):
            if feature not in df.columns:
                return None

            # split by jump label
            df0 = df[df["J_k5_z2p0"] == 0][feature].dropna()
            df1 = df[df["J_k5_z2p0"] == 1][feature].dropna()

            if len(df0) == 0 or len(df1) == 0:
                return None

            tmp = pd.DataFrame({
                f"{feature}_class0": df0,
                f"{feature}_class1": df1
            })

            tmp_sheet = f"{feature}_box"
            tmp.to_excel(writer, sheet_name=tmp_sheet, index=False)

            chart = workbook.add_chart({"type": "column"})

            for i, col in enumerate(tmp.columns):
                chart.add_series({
                    "name": col,
                    "categories": [tmp_sheet, 1, i, len(tmp), i],
                    "values": [tmp_sheet, 1, i, len(tmp), i],
                })

            chart.set_title({"name": f"{feature} by jump_label"})
            return chart

        # ---------- Insert charts ----------

        CHART_X_SCALE = 2.2
        CHART_Y_SCALE = 1.1
        CHART_COL = 0
        ROW_GAP = 20

        row_cursor = len(df) + 3

        # 1. X vs step
        chart = make_line_chart("step", ["X"], "X vs step")
        if chart is not None:
            ws.insert_chart(row_cursor, CHART_COL, chart, {
                "x_scale": CHART_X_SCALE,
                "y_scale": CHART_Y_SCALE
            })
            row_cursor += ROW_GAP

        # 2. jump_label + X vs step
        chart = make_line_chart("step", ["X", "J_k5_z2p0"], "X & jump_label vs step")
        if chart is not None:
            ws.insert_chart(row_cursor, CHART_COL, chart, {
                "x_scale": CHART_X_SCALE,
                "y_scale": CHART_Y_SCALE
            })
            row_cursor += ROW_GAP

        # 3. HCI + jump label
        chart = make_line_chart("step", ["HCI", "J_k5_z2p0"], "HCI & jump_label")
        if chart is not None:
            ws.insert_chart(row_cursor, CHART_COL, chart, {
                "x_scale": CHART_X_SCALE,
                "y_scale": CHART_Y_SCALE
            })
            row_cursor += ROW_GAP

        # 4. CSM + jump label
        chart = make_line_chart("step", ["CSM", "J_k5_z2p0"], "CSM & jump_label")
        if chart is not None:
            ws.insert_chart(row_cursor, CHART_COL, chart, {
                "x_scale": CHART_X_SCALE,
                "y_scale": CHART_Y_SCALE
            })
            row_cursor += ROW_GAP

        # 5. TBS + jump label
        chart = make_line_chart("step", ["TBS", "J_k5_z2p0"], "TBS & jump_label")
        if chart is not None:
            ws.insert_chart(row_cursor, CHART_COL, chart, {
                "x_scale": CHART_X_SCALE,
                "y_scale": CHART_Y_SCALE
            })
            row_cursor += ROW_GAP

        # 6. rise streak plots
        for k in ["HCI", "CSM", "TBS"]:
            col = f"rise_streak_{k}"
            if col in df.columns:
                chart = make_line_chart("step", [col, "J_k5_z2p0"], f"{col} & jump_label")
                if chart is not None:
                    ws.insert_chart(row_cursor, CHART_COL, chart, {
                        "x_scale": CHART_X_SCALE,
                        "y_scale": CHART_Y_SCALE
                    })
                    row_cursor += ROW_GAP

        # boxplots
        box_features = ["HCI", "CSM", "TBS",
                        "rise_streak_HCI", "rise_streak_CSM", "rise_streak_TBS"]

        for f in box_features:
            chart = make_boxplot(f)
            if chart is not None:
                ws.insert_chart(row_cursor, CHART_COL, chart, {
                    "x_scale": CHART_X_SCALE,
                    "y_scale": CHART_Y_SCALE
                })
                row_cursor += ROW_GAP
        row_cursor += 2
        row_cursor = insert_correlation_block(ws, workbook, df, row_cursor)
    print(f"Exported to {filename}")


# =========================
# Global DuckDB export config
# =========================

DUCKDB_PATH = "analysis/adsynth_metrics.duckdb"
MAIN_CSV_PATH = "analysis/main_metric_steps.csv"

DEFAULT_EXPERIMENT_ID = "exp_adsynth_001"
DEFAULT_EXPERIMENT_NAME = "ADSynth misconfiguration experiment"
DEFAULT_BASE_GRAPH_ID = "base_graph_001"
DEFAULT_BASE_GRAPH_NAME = None
DEFAULT_REGIME_ID = "default_regime"


def export_experiment_to_duckdb_and_csv(
        misconfig_metrics_per_itr,
        mu,
        sigma2,
        p_star,
        duckdb_path=DUCKDB_PATH,
        main_csv_path=MAIN_CSV_PATH,

        experiment_id=DEFAULT_EXPERIMENT_ID,
        experiment_name=DEFAULT_EXPERIMENT_NAME,
        base_graph_id=DEFAULT_BASE_GRAPH_ID,
        base_graph_name=DEFAULT_BASE_GRAPH_NAME,
        regime_id=DEFAULT_REGIME_ID,

        seed_number=None,
        injection_type="session",
        injection_schedule_name="random_injection",
        initial_misconfig=False,
        mode="isolated",
        notes=None,
):
    try:
        print(f"Experiment ID : {experiment_id}")
        os.makedirs(os.path.dirname(duckdb_path), exist_ok=True)
        os.makedirs(os.path.dirname(main_csv_path), exist_ok=True)
        print("Duck db path " + duckdb_path)
        lock = FileLock(f"{duckdb_path}.lock")

        with lock:
            con = duckdb.connect(duckdb_path)
            try:
                expected_cols = [
                    "experiment_id", "iteration_id", "step", "injection_type", "injection",
                    "reachable_users", "new_reachable_users",
                    "reachable_comps", "new_reachable_comps_names", "reachable_comps_names",
                    "reachable_users_count", "reachable_comps_count",
                    "p", "X", "X_users", "X_comps",
                    "HCI", "CSM", "TBS", "PBCC", "delta_X",
                    "rise_flag_HCI", "rise_streak_HCI", "rise_total_HCI",
                    "rise_flag_CSM", "rise_streak_CSM", "rise_total_CSM",
                    "rise_flag_TBS", "rise_streak_TBS", "rise_total_TBS",
                    "A_HCI", "A_CSM", "A_TBS", "A_PBCC",
                    "future_delta_k5", "Z_k5", "J_k5_z2p0",
                    "future_delta_k10", "Z_k10", "J_k10_z2p0",
                ]

                numeric_cols = [
                    "step", "reachable_users_count", "reachable_comps_count",
                    "p", "X", "X_users", "X_comps",
                    "HCI", "CSM", "TBS", "PBCC", "delta_X",
                    "rise_flag_HCI", "rise_streak_HCI", "rise_total_HCI",
                    "rise_flag_CSM", "rise_streak_CSM", "rise_total_CSM",
                    "rise_flag_TBS", "rise_streak_TBS", "rise_total_TBS",
                    "A_HCI", "A_CSM", "A_TBS", "A_PBCC",
                    "future_delta_k5", "Z_k5", "J_k5_z2p0",
                    "future_delta_k10", "Z_k10", "J_k10_z2p0",
                ]

                all_dfs = []

                for itr, metrics_dict in sorted(misconfig_metrics_per_itr.items()):
                    df = pd.DataFrame.from_dict(metrics_dict, orient="index")

                    if "step" in df.columns:
                        df = df.drop(columns=["step"])

                    df = df.sort_index().reset_index().rename(columns={"index": "step"})

                    iteration_id = f"iter_{itr}"

                    df.insert(0, "iteration_id", iteration_id)
                    df.insert(0, "experiment_id", experiment_id)
                    df.insert(0, "injection_type", injection_type)

                    df_full = df.copy()

                    for col in expected_cols:
                        if col not in df_full.columns:
                            df_full[col] = None

                    for col in numeric_cols:
                        if col in df_full.columns:
                            df_full[col] = pd.to_numeric(df_full[col], errors="coerce")

                    all_dfs.append(df_full)

                if not all_dfs:
                    raise ValueError("No iterations found in misconfig_metrics_per_itr")

                master_full_df = pd.concat(all_dfs, ignore_index=True)

                master_df = master_full_df[expected_cols].copy()
                mitigation_cols = [
                    "experiment_id",
                    "injection_type",
                    "iteration_id",
                    "step",

                    "mitigation_enabled",
                    "mitigation_condition",
                    "mitigation_budget",

                    "alarm_triggered",
                    "mitigation_removed",

                    "used_mitigation_cost",
                    "removed_mitigation_count",

                    "last_removed_edge_label",
                    "last_removed_edge_cost",
                    "last_removed_edge_advantage",
                    "last_removed_edge_score",
                ]
                mitigation_numeric_cols = [
                    "mitigation_enabled",
                    "mitigation_budget",
                    "alarm_triggered",
                    "mitigation_removed",
                    "used_mitigation_cost",
                    "removed_mitigation_count",
                    "last_removed_edge_cost",
                    "last_removed_edge_advantage",
                    "last_removed_edge_score",
                ]

                for col in mitigation_cols:
                    if col not in master_full_df.columns:
                        master_full_df[col] = None

                mitigation_df = master_full_df[mitigation_cols].copy()

                for col in mitigation_numeric_cols:
                    if col in mitigation_df.columns:
                        mitigation_df[col] = pd.to_numeric(
                            mitigation_df[col],
                            errors="coerce",
                        )

                mitigation_df = mitigation_df[
                    mitigation_df["mitigation_enabled"].notna()
                ]

                file_exists = os.path.exists(main_csv_path)

                master_df.to_csv(
                    main_csv_path,
                    mode="a" if file_exists else "w",
                    header=not file_exists,
                    index=False
                )

                summary_rows = []

                all_p_values = sorted(set(mu.keys()) | set(sigma2.keys()))

                for p in all_p_values:
                    summary_rows.append({
                        "experiment_id": experiment_id,
                        "injection_type": injection_type,
                        "p": p,
                        "mu_X": mu.get(p),
                        "sigma2_X": sigma2.get(p),
                        "is_p_star": p == p_star,
                        "p_star": p_star,
                    })

                summary_df = pd.DataFrame(summary_rows)

                # -------------------------
                # DuckDB export
                # -------------------------

                con.execute("""
                            CREATE TABLE IF NOT EXISTS experiments
                            (
                                experiment_id
                                VARCHAR
                                PRIMARY
                                KEY,
                                experiment_name
                                VARCHAR,
                                base_graph_id
                                VARCHAR,
                                base_graph_name
                                VARCHAR,
                                regime_id
                                VARCHAR,
                                injection_type
                                VARCHAR,
                                mode
                                VARCHAR,
                                seed_number
                                INTEGER,
                                initial_misconfig
                                BOOLEAN,
                                description
                                VARCHAR,
                                created_at
                                TIMESTAMP
                                DEFAULT
                                CURRENT_TIMESTAMP
                            );
                            """)

                con.execute("""
                            CREATE TABLE IF NOT EXISTS experiment_iterations
                            (
                                experiment_id
                                VARCHAR
                                NOT
                                NULL,
                                iteration_id
                                VARCHAR
                                NOT
                                NULL,
                                seed
                                INTEGER,
                                injection_schedule_name
                                VARCHAR,
                                initial_misconfig
                                BOOLEAN,
                                notes
                                VARCHAR,
                                created_at
                                TIMESTAMP
                                DEFAULT
                                CURRENT_TIMESTAMP,
                                PRIMARY
                                KEY
                            (
                                experiment_id,
                                iteration_id
                            )
                                );
                            """)

                con.execute("""
                            CREATE TABLE IF NOT EXISTS metric_steps
                            (
                                experiment_id
                                VARCHAR
                                NOT
                                NULL,
                                iteration_id
                                VARCHAR
                                NOT
                                NULL,
                                step
                                INTEGER
                                NOT
                                NULL,
                                injection_type
                                VARCHAR
                                NOT
                                NULL,
                                reachable_users
                                VARCHAR,
                                new_reachable_users
                                VARCHAR,
                                reachable_comps
                                VARCHAR,
                                new_reachable_comps_names
                                VARCHAR,
                                reachable_comps_names
                                VARCHAR,

                                reachable_users_count
                                INTEGER,
                                reachable_comps_count
                                INTEGER,

                                p
                                DOUBLE,
                                X
                                DOUBLE,
                                X_users
                                DOUBLE,
                                X_comps
                                DOUBLE,

                                HCI
                                DOUBLE,
                                CSM
                                DOUBLE,
                                TBS
                                DOUBLE,
                                PBCC
                                DOUBLE,
                                delta_X
                                DOUBLE,

                                rise_flag_HCI
                                INTEGER,
                                rise_streak_HCI
                                INTEGER,
                                rise_total_HCI
                                INTEGER,

                                rise_flag_CSM
                                INTEGER,
                                rise_streak_CSM
                                INTEGER,
                                rise_total_CSM
                                INTEGER,

                                rise_flag_TBS
                                INTEGER,
                                rise_streak_TBS
                                INTEGER,
                                rise_total_TBS
                                INTEGER,

                                A_HCI
                                DOUBLE,
                                A_CSM
                                DOUBLE,
                                A_TBS
                                DOUBLE,
                                A_PBCC
                                DOUBLE,

                                future_delta_k5
                                DOUBLE,
                                Z_k5
                                DOUBLE,
                                J_k5_z2p0
                                INTEGER,

                                future_delta_k10
                                DOUBLE,
                                Z_k10
                                DOUBLE,
                                J_k10_z2p0
                                INTEGER,

                                created_at
                                TIMESTAMP
                                DEFAULT
                                CURRENT_TIMESTAMP,

                                PRIMARY
                                KEY
                            (
                                experiment_id,
                                injection_type,
                                iteration_id,
                                step
                            )
                                );
                            """)
                con.execute("""
                            CREATE TABLE IF NOT EXISTS online_mitigation_steps
                            (
                                experiment_id
                                VARCHAR
                                NOT
                                NULL,
                                injection_type
                                VARCHAR
                                NOT
                                NULL,
                                iteration_id
                                VARCHAR
                                NOT
                                NULL,
                                step
                                INTEGER
                                NOT
                                NULL,

                                mitigation_enabled
                                INTEGER,
                                mitigation_condition
                                VARCHAR,
                                mitigation_budget
                                DOUBLE,

                                alarm_triggered
                                INTEGER,
                                mitigation_removed
                                INTEGER,

                                used_mitigation_cost
                                DOUBLE,
                                removed_mitigation_count
                                INTEGER,

                                last_removed_edge_label
                                VARCHAR,
                                last_removed_edge_cost
                                DOUBLE,
                                last_removed_edge_advantage
                                DOUBLE,
                                last_removed_edge_score
                                DOUBLE,

                                created_at
                                TIMESTAMP
                                DEFAULT
                                CURRENT_TIMESTAMP,

                                PRIMARY
                                KEY
                            (
                                experiment_id,
                                injection_type,
                                iteration_id,
                                step
                            )
                                );
                            """)
                con.register("mitigation_df", mitigation_df)

                con.execute("""
                        INSERT OR REPLACE INTO online_mitigation_steps (
                            experiment_id,
                            injection_type,
                            iteration_id,
                            step,

                            mitigation_enabled,
                            mitigation_condition,
                            mitigation_budget,

                            alarm_triggered,
                            mitigation_removed,

                            used_mitigation_cost,
                            removed_mitigation_count,

                            last_removed_edge_label,
                            last_removed_edge_cost,
                            last_removed_edge_advantage,
                            last_removed_edge_score,

                            created_at
                        )
                        SELECT
                            experiment_id,
                            injection_type,
                            iteration_id,
                            step,

                            mitigation_enabled,
                            mitigation_condition,
                            mitigation_budget,

                            alarm_triggered,
                            mitigation_removed,

                            used_mitigation_cost,
                            removed_mitigation_count,

                            last_removed_edge_label,
                            last_removed_edge_cost,
                            last_removed_edge_advantage,
                            last_removed_edge_score,

                            CURRENT_TIMESTAMP
                        FROM mitigation_df;
                    """)
                con.execute("""
                            CREATE TABLE IF NOT EXISTS experiment_summary_stats
                            (
                                experiment_id
                                VARCHAR
                                NOT
                                NULL,
                                injection_type
                                VARCHAR
                                NOT
                                NULL,
                                p
                                DOUBLE
                                NOT
                                NULL,
                                mu_X
                                DOUBLE,
                                sigma2_X
                                DOUBLE,
                                is_p_star
                                BOOLEAN,
                                p_star
                                DOUBLE,
                                created_at
                                TIMESTAMP
                                DEFAULT
                                CURRENT_TIMESTAMP,
                                PRIMARY
                                KEY
                            (
                                experiment_id,
                                injection_type,
                                p
                            )
                                );
                            """)

                con.execute("""
                        INSERT OR REPLACE INTO experiments (
                            experiment_id, experiment_name, base_graph_id, base_graph_name,
                            regime_id, injection_type, mode, seed_number,
                            initial_misconfig, description
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """, [
                    experiment_id, experiment_name, base_graph_id, base_graph_name,
                    regime_id, injection_type, mode, seed_number,
                    initial_misconfig, notes,
                ])

                iteration_rows = []
                for itr in sorted(misconfig_metrics_per_itr.keys()):
                    iteration_rows.append({
                        "experiment_id": experiment_id,
                        "iteration_id": f"iter_{itr}",
                        "seed": seed_number,
                        "injection_schedule_name": injection_schedule_name,
                        "initial_misconfig": initial_misconfig,
                        "notes": notes,
                    })

                iteration_df = pd.DataFrame(iteration_rows)

                con.register("iteration_df", iteration_df)
                con.execute("""
                        INSERT OR REPLACE INTO experiment_iterations
                        SELECT
                            experiment_id,
                            iteration_id,
                            seed,
                            injection_schedule_name,
                            initial_misconfig,
                            notes,
                            CURRENT_TIMESTAMP
                        FROM iteration_df;
                    """)

                con.register("master_df", master_df)
                con.execute("""
                        INSERT OR REPLACE INTO metric_steps (
                experiment_id, iteration_id, step, injection_type,injection,
                reachable_users, new_reachable_users,
                reachable_comps, new_reachable_comps_names, reachable_comps_names,
                reachable_users_count, reachable_comps_count,
                p, X, X_users, X_comps,
                HCI, CSM, TBS, PBCC, delta_X,
                rise_flag_HCI, rise_streak_HCI, rise_total_HCI,
                rise_flag_CSM, rise_streak_CSM, rise_total_CSM,
                rise_flag_TBS, rise_streak_TBS, rise_total_TBS,
                A_HCI, A_CSM, A_TBS, A_PBCC,
                future_delta_k5, Z_k5, J_k5_z2p0,
                future_delta_k10, Z_k10, J_k10_z2p0,
                created_at
            )
            SELECT
                experiment_id, iteration_id, step, injection_type,injection,
                reachable_users, new_reachable_users,
                reachable_comps, new_reachable_comps_names, reachable_comps_names,
                reachable_users_count, reachable_comps_count,
                p, X, X_users, X_comps,
                HCI, CSM, TBS, PBCC, delta_X,
                rise_flag_HCI, rise_streak_HCI, rise_total_HCI,
                rise_flag_CSM, rise_streak_CSM, rise_total_CSM,
                rise_flag_TBS, rise_streak_TBS, rise_total_TBS,
                A_HCI, A_CSM, A_TBS, A_PBCC,
                future_delta_k5, Z_k5, J_k5_z2p0,
                future_delta_k10, Z_k10, J_k10_z2p0,
                CURRENT_TIMESTAMP
            FROM master_df;
                    """)

                con.register("summary_df", summary_df)
                con.execute("""
                        INSERT OR REPLACE INTO experiment_summary_stats (
                            experiment_id,
                            injection_type,
                            p,
                            mu_X,
                            sigma2_X,
                            is_p_star,
                            p_star
                        )
                        SELECT
                            experiment_id,
                            injection_type,
                            p,
                            mu_X,
                            sigma2_X,
                            is_p_star,
                            p_star
                        FROM summary_df;
                    """)

                con.execute("""
                            CREATE
                            OR REPLACE VIEW v_metric_steps AS
                            SELECT e.experiment_name,
                                   e.base_graph_id,
                                   e.base_graph_name,
                                   e.regime_id,
                                   e.injection_type,
                                   e.mode,
                                   e.seed_number,
                                   i.injection_schedule_name,
                                   i.initial_misconfig,
                                   m.*
                            FROM metric_steps m
                                     LEFT JOIN experiment_iterations i
                                               ON m.experiment_id = i.experiment_id
                                                   AND m.iteration_id = i.iteration_id
                                     LEFT JOIN experiments e
                                               ON m.experiment_id = e.experiment_id;
                            """)
                con.execute("""
                            CREATE
                            OR REPLACE VIEW v_metric_steps_with_mitigation AS
                            SELECT v.*,

                                   ms.mitigation_enabled,
                                   ms.mitigation_condition,
                                   ms.mitigation_budget,
                                   ms.alarm_triggered,
                                   ms.mitigation_removed,
                                   ms.used_mitigation_cost,
                                   ms.removed_mitigation_count,
                                   ms.last_removed_edge_label,
                                   ms.last_removed_edge_cost,
                                   ms.last_removed_edge_advantage,
                                   ms.last_removed_edge_score

                            FROM v_metric_steps v
                                     LEFT JOIN online_mitigation_steps ms
                                               ON v.experiment_id = ms.experiment_id
                                                   AND v.injection_type = ms.injection_type
                                                   AND v.iteration_id = ms.iteration_id
                                                   AND v.step = ms.step;
                            """)
                con.execute("""
                            CREATE
                            OR REPLACE VIEW v_experiment_summary_stats AS
                            SELECT e.experiment_name,
                                   e.base_graph_id,
                                   e.base_graph_name,
                                   e.regime_id,
                                   e.injection_type,
                                   e.mode,
                                   s.*
                            FROM experiment_summary_stats s
                                     LEFT JOIN experiments e
                                               ON s.experiment_id = e.experiment_id;
                            """)
            except Exception as e:
                print(f"Lock error {e}")
            finally:
                con.close()

        print(f"Exported all runs to DuckDB: {duckdb_path}")
        print(f"Exported master CSV: {main_csv_path}")
        print(f"Metric rows exported: {len(master_df)}")
        print(f"Summary rows exported: {len(summary_df)}")
    except Exception as e:
        print(e)


def classify_transition_from_delta( j_value):
    """
    Bucket transition strength from maximum exposure jump.
    j_value can be max delta X or max delta mu_X.
    """
    if j_value is None or pd.isna(j_value):
        return "unknown"

    if j_value < 0.02:
        return "no_transition"
    elif j_value < 0.05:
        return "weak_transition"
    elif j_value < 0.10:
        return "moderate_transition"
    else:
        return "strong_transition"


def analyse_percolation_from_duckdb(
        db_path,
        out_dir="analysis/csv",

        start_time=None,
        end_time=None,
        graph_name_filter=None,
        schedule_filter=None,
        injection_type_filter=None,
        initial_misconfig_filter=None,
        min_realisations=2,
):
    """
    Percolation analysis from DuckDB.

    Levels:
    1. Seed-level:
       For each graph seed, compute mu_X over injection iterations.
       Bucket that seed using max delta mu_X.

    2. Configuration-level:
       Across all seeds and iterations, compute mu_X(p), sigma2_X(p),
       delta_mu_X(p), and p_star.

    Time filtering:
       Analyse only experiments whose metric rows were created between
       start_time and end_time.
    """

    import duckdb
    import pandas as pd
    from pathlib import Path
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(db_path)

    where_clauses = ["X IS NOT NULL"]

    if start_time is not None:
        where_clauses.append(f"created_at >= TIMESTAMP '{start_time}'")

    if end_time is not None:
        where_clauses.append(f"created_at <= TIMESTAMP '{end_time}'")

    if graph_name_filter is not None:
        where_clauses.append(f"base_graph_name LIKE '%{graph_name_filter}%'")

    if schedule_filter is not None:
        where_clauses.append(f"injection_schedule_name LIKE '%{schedule_filter}%'")

    if injection_type_filter is not None:
        where_clauses.append(f"injection_type = '{injection_type_filter}'")

    if initial_misconfig_filter is not None:
        val = "TRUE" if initial_misconfig_filter else "FALSE"
        where_clauses.append(f"initial_misconfig = {val}")

    where_sql = " AND ".join(where_clauses)

    query = f"""
        SELECT
            experiment_id,
            experiment_name,
            base_graph_id,
            base_graph_name,
            regime_id,
            seed_number,
            injection_type,
            injection_schedule_name,
            initial_misconfig,
            mode,
            iteration_id,
            step,
            p,
            X,
            delta_X,
            created_at
        FROM v_metric_steps
        WHERE {where_sql}
        ORDER BY
            base_graph_name,
            initial_misconfig,
            injection_schedule_name,
            injection_type,
            seed_number,
            iteration_id,
            step
    """

    df = con.execute(query).df()
    con.close()

    if df.empty:
        print("No metric rows found for the selected filters/time window.")
        return None

    print(f"Rows selected for percolation analysis: {len(df)}")
    print(f"Start time: {start_time}")
    print(f"End time  : {end_time}")

    # Ensure numeric columns are clean
    for col in ["seed_number", "step", "p", "X", "delta_X"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["seed_number", "step", "p", "X"])

    # ------------------------------------------------------------------
    # 1. Seed-level mean exposure curve:
    #    mu_{X,g}(p_i) = mean over injection iterations for each seed
    # ------------------------------------------------------------------

    seed_group_cols = [
        "base_graph_name",
        "initial_misconfig",
        "injection_schedule_name",
        "injection_type",
        "seed_number",
        "step",
        "p",
    ]

    seed_mu = (
        df.groupby(seed_group_cols, as_index=False)
        .agg(
            mu_x_seed=("X", "mean"),
            sigma2_x_seed=("X", "var"),
            n_seed_iterations=("X", "count"),
        )
    )

    seed_mu["sigma2_x_seed"] = seed_mu["sigma2_x_seed"].fillna(0.0)

    seed_mu = seed_mu.sort_values([
        "base_graph_name",
        "initial_misconfig",
        "injection_schedule_name",
        "injection_type",
        "seed_number",
        "step",
    ])

    seed_mu["delta_mu_x_seed"] = (
        seed_mu.groupby([
            "base_graph_name",
            "initial_misconfig",
            "injection_schedule_name",
            "injection_type",
            "seed_number",
        ])["mu_x_seed"]
        .diff()
        .fillna(0.0)
    )

    # ------------------------------------------------------------------
    # 2. Seed-level bucket summary:
    #    Bucket each seed using max delta mu_X for that seed
    # ------------------------------------------------------------------

    seed_summary_rows = []

    seed_summary_group_cols = [
        "base_graph_name",
        "initial_misconfig",
        "injection_schedule_name",
        "injection_type",
        "seed_number",
    ]

    for keys, g in seed_mu.groupby(seed_summary_group_cols):
        idx_jump = g["delta_mu_x_seed"].idxmax()
        idx_var = g["sigma2_x_seed"].idxmax()

        max_delta_mu = float(g.loc[idx_jump, "delta_mu_x_seed"])
        bucket = classify_transition_from_delta(max_delta_mu)

        row = dict(zip(seed_summary_group_cols, keys))
        row.update({
            "max_delta_mu_x_seed": max_delta_mu,
            "p_jump_seed": float(g.loc[idx_jump, "p"]),
            "jump_step_seed": int(g.loc[idx_jump, "step"]),
            "seed_p_star_variance": float(g.loc[idx_var, "p"]),
            "seed_max_sigma2_x": float(g.loc[idx_var, "sigma2_x_seed"]),
            "seed_bucket": bucket,
            "seed_is_percolation_like": bucket in [
                "moderate_transition",
                "strong_transition",
            ],
            "mean_final_mu_x_seed": float(
                g[g["step"] == g["step"].max()]["mu_x_seed"].mean()
            ),
            "n_steps": int(g["step"].nunique()),
            "mean_iterations_per_step": float(g["n_seed_iterations"].mean()),
        })

        seed_summary_rows.append(row)

    seed_summary = pd.DataFrame(seed_summary_rows)

    # ------------------------------------------------------------------
    # 3. Configuration-level mu/sigma:
    #    Across all seeds and iterations for same config/schedule/type
    # ------------------------------------------------------------------

    config_group_cols = [
        "base_graph_name",
        "initial_misconfig",
        "injection_schedule_name",
        "injection_type",
        "step",
        "p",
    ]

    config_stats = (
        df.groupby(config_group_cols, as_index=False)
        .agg(
            mu_x=("X", "mean"),
            sigma2_x=("X", "var"),
            n_realisations=("X", "count"),
            n_seeds=("seed_number", "nunique"),
            n_iterations=("iteration_id", "nunique"),
        )
    )

    config_stats["sigma2_x"] = config_stats["sigma2_x"].fillna(0.0)

    config_stats = config_stats.sort_values([
        "base_graph_name",
        "initial_misconfig",
        "injection_schedule_name",
        "injection_type",
        "step",
    ])

    config_stats["delta_mu_x"] = (
        config_stats.groupby([
            "base_graph_name",
            "initial_misconfig",
            "injection_schedule_name",
            "injection_type",
        ])["mu_x"]
        .diff()
        .fillna(0.0)
    )

    # Mark whether enough realisations exist for variance interpretation
    config_stats["variance_reliable"] = (
            config_stats["n_realisations"] >= min_realisations
    )

    # ------------------------------------------------------------------
    # 4. Configuration-level summary:
    #    p_star, max delta mu, vulnerable seeds
    # ------------------------------------------------------------------

    config_summary_rows = []

    config_summary_group_cols = [
        "base_graph_name",
        "initial_misconfig",
        "injection_schedule_name",
        "injection_type",
    ]

    for keys, g in config_stats.groupby(config_summary_group_cols):
        base_graph_name, initial_misconfig, schedule, injection_type = keys

        reliable_g = g[g["variance_reliable"]].copy()
        if reliable_g.empty:
            reliable_g = g.copy()

        idx_var = reliable_g["sigma2_x"].idxmax()
        idx_mu = g["delta_mu_x"].idxmax()

        matching_seed_rows = seed_summary[
            (seed_summary["base_graph_name"] == base_graph_name) &
            (seed_summary["initial_misconfig"] == initial_misconfig) &
            (seed_summary["injection_schedule_name"] == schedule) &
            (seed_summary["injection_type"] == injection_type)
            ]

        total_seeds = matching_seed_rows["seed_number"].nunique()
        vulnerable_seeds = matching_seed_rows[
            matching_seed_rows["seed_is_percolation_like"]
        ]["seed_number"].nunique()

        max_delta_mu = float(g.loc[idx_mu, "delta_mu_x"])
        config_bucket = classify_transition_from_delta(max_delta_mu)

        config_summary_rows.append({
            "base_graph_name": base_graph_name,
            "initial_misconfig": initial_misconfig,
            "injection_schedule_name": schedule,
            "injection_type": injection_type,

            "total_seeds": int(total_seeds),
            "vulnerable_seeds": int(vulnerable_seeds),
            "seed_vulnerability_rate": (
                vulnerable_seeds / total_seeds if total_seeds else 0.0
            ),

            "p_star_variance": float(reliable_g.loc[idx_var, "p"]),
            "step_star_variance": int(reliable_g.loc[idx_var, "step"]),
            "max_sigma2_x": float(reliable_g.loc[idx_var, "sigma2_x"]),

            "p_max_delta_mu": float(g.loc[idx_mu, "p"]),
            "step_max_delta_mu": int(g.loc[idx_mu, "step"]),
            "max_delta_mu_x": max_delta_mu,
            "config_aggregate_bucket": config_bucket,

            "mean_seed_max_delta_mu": float(
                matching_seed_rows["max_delta_mu_x_seed"].mean()
            ) if not matching_seed_rows.empty else None,

            "max_seed_max_delta_mu": float(
                matching_seed_rows["max_delta_mu_x_seed"].max()
            ) if not matching_seed_rows.empty else None,

            "mean_seed_final_x": float(
                matching_seed_rows["mean_final_mu_x_seed"].mean()
            ) if not matching_seed_rows.empty else None,

            "min_n_realisations_per_p": int(g["n_realisations"].min()),
            "max_n_realisations_per_p": int(g["n_realisations"].max()),
        })

    config_summary = pd.DataFrame(config_summary_rows)

    # ------------------------------------------------------------------
    # 5. Export outputs
    # ------------------------------------------------------------------

    suffix_parts = []

    if graph_name_filter:
        suffix_parts.append(str(graph_name_filter).replace(" ", "_"))

    if schedule_filter:
        suffix_parts.append(str(schedule_filter).replace(" ", "_"))

    if injection_type_filter:
        suffix_parts.append(str(injection_type_filter).replace(" ", "_"))

    if start_time or end_time:
        suffix_parts.append("time_filtered")

    suffix = "_".join(suffix_parts) if suffix_parts else "all"

    seed_mu_path = f"{out_dir}/percolation_seed_mu_{suffix}.csv"
    seed_summary_path = f"{out_dir}/percolation_seed_buckets_{suffix}.csv"
    config_stats_path = f"{out_dir}/percolation_config_mu_sigma_{suffix}.csv"
    config_summary_path = f"{out_dir}/percolation_config_summary_{suffix}.csv"

    seed_mu.to_csv(seed_mu_path, index=False)
    seed_summary.to_csv(seed_summary_path, index=False)
    config_stats.to_csv(config_stats_path, index=False)
    config_summary.to_csv(config_summary_path, index=False)

    print(f"Saved seed mu curves: {seed_mu_path}")
    print(f"Saved seed buckets: {seed_summary_path}")
    print(f"Saved config mu/sigma: {config_stats_path}")
    print(f"Saved config summary: {config_summary_path}")

    return seed_mu, seed_summary, config_stats, config_summary
