import matplotlib.pyplot as plt


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
