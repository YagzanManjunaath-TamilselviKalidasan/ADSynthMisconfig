import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.io as pio
import numpy as np


def plot_plot_chart(x_values, y_values, x_label, y_label, title, additional_info, plot_type):
    plt.figure(figsize=(8, 5))

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

    save_path = f"/Users/yagzanmanjunaath/UniWorkspace/ResearchMethods/CodeSpace/ADSynth/generated_datasets/{file_name}.html"

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

    save_path = f"/Users/yagzanmanjunaath/UniWorkspace/ResearchMethods/CodeSpace/ADSynth/generated_datasets/{file_name}.html"

    if file_name:
        fig.write_html(save_path)
    # fig.show()
