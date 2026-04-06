import math
import os
import tempfile

import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.io as pio
import numpy as np


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

def export_metrics_to_excel(metrics_data, filename, x_axis="step",metadata=None):
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
        "reachable_comps_names"
    ]

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

    def write_dataframe(ws, df, header_fmt):
        for col_num, value in enumerate(df.columns):
            ws.write(0, col_num, value, header_fmt)
            ws.set_column(col_num, col_num, max(16, len(str(value)) + 2))

    def safe_sheet_name(name):
        invalid = ['[', ']', ':', '*', '?', '/', '\\']
        for ch in invalid:
            name = name.replace(ch, "_")
        return name[:31]

    def insert_boxplot_image(workbook, worksheet, df, metric_key, metric_label, cell):
        values = df[metric_key].dropna().tolist()
        if not values:
            return

        fig, ax = plt.subplots(figsize=(6, 4))
        ax.boxplot(values, vert=True)
        ax.set_title(metric_label)
        ax.set_ylabel(metric_label)

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        tmp_path = tmp.name
        tmp.close()

        fig.savefig(tmp_path, bbox_inches="tight")
        plt.close(fig)

        worksheet.insert_image(cell, tmp_path)

        return tmp_path

    def add_deltas_for_all_metrics(metrics_dict, metric_titles,scale = True):
        steps = sorted(metrics_dict.keys())
        prev_row = None

        for step in steps:
            row = metrics_dict[step]

            for metric_key in metric_titles.keys():
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
        if scale:
            all_keys = list(metric_titles.keys()) + [f"delta_{k}" for k in metric_titles.keys()]

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


                if math.isclose(max_val, min_val):
                    for s in steps:
                        metrics_dict[s][f"scaled_{key}"] = 0.0
                    continue

                for s in steps:
                    val = metrics_dict[s].get(key)

                    if isinstance(val, (int, float)):
                        scaled = (val - min_val) / (max_val - min_val)
                        metrics_dict[s][f"scaled_{key}"] = scaled
                    else:
                        metrics_dict[s][f"scaled_{key}"] = None
        return metrics_dict
    def build_chart_title(main_title, metadata=None):
        if not metadata:
            return main_title

        meta_parts = [f"{k}: {v}" for k, v in list(metadata.items())]
        meta_text = " | ".join(meta_parts)
        return f"{main_title}\n{meta_text}"

    metrics_to_export = add_deltas_for_all_metrics(metrics_data, metric_titles,True)
    df_full = normalize_metrics(metrics_to_export)
    for metric_key, metric_label in list(metric_titles.items()):
        metric_titles[f"delta_{metric_key}"] = f"Delta {metric_label}"
    if df_full.empty:
        print("No data to export")
        return
    if df_full.empty:
        print("No data to export")
        return

    # add delta columns per run
    if "reachable_users_count" in df_full.columns:
        df_full["delta_reachable_users_count"] = (
            df_full.groupby("run")["reachable_users_count"]
            .diff()
            .fillna(df_full["reachable_users_count"])
            .astype(int)
        )

    if "reachable_comps_count" in df_full.columns:
        df_full["delta_reachable_comps_count"] = (
            df_full.groupby("run")["reachable_comps_count"]
            .diff()
            .fillna(df_full["reachable_comps_count"])
            .astype(int)
        )
    with pd.ExcelWriter(filename, engine="xlsxwriter") as writer:
        workbook = writer.book
        header_fmt = workbook.add_format({
            "bold": True,
            "bg_color": "#D9EAF7",
            "border": 1
        })

        run_ids = sorted(df_full["run"].unique())

        for run_id in run_ids:
            df_run_full = df_full[df_full["run"] == run_id].copy()

            # main sheet excludes bulky columns
            df_main = df_run_full.drop(columns=cols_to_separate, errors="ignore")

            main_sheet = safe_sheet_name(f"run_{run_id}_data")
            df_main.to_excel(writer, sheet_name=main_sheet, index=False)
            ws_main = writer.sheets[main_sheet]
            write_dataframe(ws_main, df_main, header_fmt)

            detail_cols = ["step"] + [col for col in cols_to_separate if col in df_run_full.columns]

            if len(detail_cols) > 1:
                df_details = df_run_full[detail_cols].copy()

                # convert lists to readable strings inside Excel cells
                for col in cols_to_separate:
                    if col in df_details.columns:
                        df_details[col] = df_details[col].apply(
                            lambda x: "\n".join(map(str, x)) if isinstance(x, (list, tuple, set)) else x
                        )

                details_sheet = safe_sheet_name(f"r{run_id}_details")
                df_details.to_excel(writer, sheet_name=details_sheet, index=False)

                ws_details = writer.sheets[details_sheet]
                write_dataframe(ws_details, df_details, header_fmt)

                # widen these columns a bit more
                for col_idx, col_name in enumerate(df_details.columns):
                    if col_name != "step":
                        ws_details.set_column(col_idx, col_idx, 40)
            if df_full.empty:
                print("No data to export")
                return


            # metric sheets + charts
            for metric_key, metric_label in metric_titles.items():
                if metric_key not in df_main.columns:
                    continue

                plot_cols = ["step"]
                if x_axis == "p" and "p" in df_main.columns:
                    plot_cols = ["p"]

                plot_cols += [metric_key]

                delta_metric_key = f"delta_{metric_key}"
                if delta_metric_key in df_main.columns:
                    plot_cols.append(delta_metric_key)

                scaled_metric_key = f"scaled_{metric_key}"
                if scaled_metric_key in df_main.columns:
                    plot_cols.append(scaled_metric_key)

                if "reachable_users_count" in df_main.columns:
                    plot_cols.append("reachable_users_count")
                if "reachable_comps_count" in df_main.columns:
                    plot_cols.append("reachable_comps_count")

                if "delta_reachable_users_count" in df_main.columns:
                    plot_cols.append("delta_reachable_users_count")
                if "delta_reachable_comps_count" in df_main.columns:
                    plot_cols.append("delta_reachable_comps_count")

                metric_df = df_main[plot_cols].copy()

                sheet_name = safe_sheet_name(f"r{run_id}_{metric_label}")
                metric_df.to_excel(writer, sheet_name=sheet_name, index=False)
                ws = writer.sheets[sheet_name]
                write_dataframe(ws, metric_df, header_fmt)

                nrows = len(metric_df)
                if nrows == 0:
                    continue

                x_col = plot_cols[0]
                x_idx = metric_df.columns.get_loc(x_col)
                metric_idx = metric_df.columns.get_loc(metric_key)

                # metric chart
                chart_metric = workbook.add_chart({"type": "line"})
                chart_metric.add_series({
                    "name":       [sheet_name, 0, metric_idx],
                    "categories": [sheet_name, 1, x_idx, nrows, x_idx],
                    "values":     [sheet_name, 1, metric_idx, nrows, metric_idx],
                })
                # chart_metric.set_title({"name": f"{metric_label} vs {x_col} (run {run_id})"})
                chart_metric.set_title({
                    "name": build_chart_title(f"{metric_label} vs {x_col} (run {run_id})", metadata)
                })
                chart_metric.set_x_axis({"name": x_col})
                chart_metric.set_y_axis({"name": metric_label})
                ws.insert_chart("K2", chart_metric, {"x_scale": 1.4, "y_scale": 1.2})
                if scaled_metric_key in metric_df.columns:
                    x_idx = metric_df.columns.get_loc(x_col)
                    metric_scaled_idx = metric_df.columns.get_loc(scaled_metric_key)

                    chart_scaled_metric = workbook.add_chart({"type": "line"})
                    chart_scaled_metric.add_series({
                        "name": [sheet_name, 0, metric_scaled_idx],
                        "categories": [sheet_name, 1, x_idx, nrows, x_idx],
                        "values": [sheet_name, 1, metric_scaled_idx, nrows, metric_scaled_idx],
                    })
                    chart_scaled_metric.set_title({
                        "name": build_chart_title(f"{scaled_metric_key} vs {x_col} (run {run_id})", metadata)
                    })
                    chart_scaled_metric.set_x_axis({"name": x_col})
                    chart_scaled_metric.set_y_axis({"name": scaled_metric_key})
                    ws.insert_chart("K56", chart_scaled_metric, {"x_scale": 1.4, "y_scale": 1.2})
                # reachable users chart
                if "reachable_users_count" in metric_df.columns:
                    users_idx = metric_df.columns.get_loc("reachable_users_count")
                    chart_users = workbook.add_chart({"type": "line"})
                    chart_users.add_series({
                        "name":       [sheet_name, 0, users_idx],
                        "categories": [sheet_name, 1, x_idx, nrows, x_idx],
                        "values":     [sheet_name, 1, users_idx, nrows, users_idx],
                    })
                    chart_users.set_title({"name": f"Reachable Users vs {x_col} (run {run_id})"})
                    chart_users.set_x_axis({"name": x_col})
                    chart_users.set_y_axis({"name": "Reachable Users"})
                    ws.insert_chart("K20", chart_users, {"x_scale": 1.4, "y_scale": 1.2})

                # reachable comps chart
                if "reachable_comps_count" in metric_df.columns:
                    comps_idx = metric_df.columns.get_loc("reachable_comps_count")
                    chart_comps = workbook.add_chart({"type": "line"})
                    chart_comps.add_series({
                        "name":       [sheet_name, 0, comps_idx],
                        "categories": [sheet_name, 1, x_idx, nrows, x_idx],
                        "values":     [sheet_name, 1, comps_idx, nrows, comps_idx],
                    })
                    chart_comps.set_title({"name": f"Reachable Computers vs {x_col} (run {run_id})"})
                    chart_comps.set_x_axis({"name": x_col})
                    chart_comps.set_y_axis({"name": "Reachable Computers"})
                    ws.insert_chart("K38", chart_comps, {"x_scale": 1.4, "y_scale": 1.2})

    print(f"Dataset exported to {filename}")