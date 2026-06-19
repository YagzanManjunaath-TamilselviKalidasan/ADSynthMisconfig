import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
from pathlib import Path

from adsynth.ADSynth import MainMenu

from adsynth.config import DUCKDB_FILE_NAME


class MitigationRunner:
    def __init__(self, parent):
        self.parent = parent
        self.menu = MainMenu()

        self.frame = ttk.LabelFrame(parent, text="Mitigation Runner from Metrics CSV", padding=12)
        self.frame.pack(fill="both", expand=True)

        self.json_path_var = tk.StringVar()
        self.condition_var = tk.StringVar(value="sessions_only")
        self.budgets_var = tk.StringVar(value="10,25,50,100")
        self.x_star_var = tk.StringVar(value="0.5")
        self.fixed_p_var = tk.StringVar(value="0.02,0.05,0.10")
        self.duckdb_path_var = tk.StringVar(
            value=str(Path.home() / DUCKDB_FILE_NAME)
        )

        self._build_ui()

    def _build_ui(self):
        frame = ttk.Frame(self.frame, padding=16)
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame,
            text="Run Cost-Aware Mitigation from Json",
            font=("Arial", 16, "bold")
        ).pack(anchor="w", pady=(0, 12))

        ttk.Label(frame, text="Experiment JSON File").pack(anchor="w")

        json_row = ttk.Frame(frame)
        json_row.pack(fill="x", pady=(4, 12))

        ttk.Entry(
            json_row,
            textvariable=self.json_path_var,
            width=60
        ).pack(side="left", fill="x", expand=True)

        ttk.Button(
            json_row,
            text="Browse",
            command=self._browse_json_file
        ).pack(side="left", padx=(8, 0))

        ttk.Label(frame, text="Mitigation Condition").pack(anchor="w")

        ttk.Combobox(
            frame,
            textvariable=self.condition_var,
            state="readonly",
            values=[
                "sessions_only",
                "permissions_only",
                "nesting_only",
                "greedy_combined",
            ],
        ).pack(fill="x", pady=(4, 12))

        ttk.Label(frame, text="Budgets comma-separated").pack(anchor="w")
        ttk.Entry(frame, textvariable=self.budgets_var).pack(fill="x", pady=(4, 12))

        ttk.Label(frame, text="X* threshold").pack(anchor="w")
        ttk.Entry(frame, textvariable=self.x_star_var).pack(fill="x", pady=(4, 12))

        ttk.Label(frame, text="Fixed p values comma-separated").pack(anchor="w")
        ttk.Entry(frame, textvariable=self.fixed_p_var).pack(fill="x", pady=(4, 12))

        ttk.Label(frame, text="DuckDB Output Path").pack(anchor="w")
        ttk.Entry(frame, textvariable=self.duckdb_path_var).pack(fill="x", pady=(4, 12))

        button_row = ttk.Frame(frame)
        button_row.pack(fill="x", pady=(10, 0))

        ttk.Button(
            button_row,
            text="Run Mitigation",
            command=self.run_mitigation_from_json
        ).pack(side="left")

        ttk.Button(
            button_row,
            text="Close",
            command=self.frame.destroy
        ).pack(side="left", padx=8)

    def _browse_json_file(self):
        path = filedialog.askopenfilename(
            title="Select Experiment JSON File",
            filetypes=[("JSON files", "*.json")]
        )

        if path:
            self.json_path_var.set(path)

    def run_mitigation_from_json(self):
        json_path = self.json_path_var.get().strip()
        condition = self.condition_var.get().strip()

        if not json_path:
            messagebox.showerror("Missing JSON File", "Please choose an experiment JSON file.")
            return

        try:
            budgets = tuple(int(x.strip()) for x in self.budgets_var.get().split(",") if x.strip())
            fixed_p_values = tuple(float(x.strip()) for x in self.fixed_p_var.get().split(",") if x.strip())
            x_star = float(self.x_star_var.get().strip())
            out_duckdb_path = self.duckdb_path_var.get().strip()
        except ValueError:
            messagebox.showerror(
                "Invalid Input",
                "Budgets must be integers, and X* / p values must be numbers."
            )
            return

        def worker():
            try:
                self.menu.run_cost_aware_mitigation_from_json(
                    json_path=json_path,
                    condition=condition,
                    budgets=budgets,
                    x_star=x_star,
                    fixed_p_values=fixed_p_values,
                    out_duckdb_path=out_duckdb_path,
                )

                self.parent.after(
                    0,
                    lambda: messagebox.showinfo(
                        "Success",
                        f"Mitigation completed.\nCondition: {condition}"
                    )
                )

            except Exception as e:
                self.parent.after(
                    0,
                    lambda: messagebox.showerror("Error", str(e))
                )

        threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Mitigation Runner")
    root.geometry("750x750")

    app = MitigationRunner(root)

    root.mainloop()