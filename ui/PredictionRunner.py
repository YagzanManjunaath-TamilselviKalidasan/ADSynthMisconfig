import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading

from adsynth.ADSynth import MainMenu


class PredictionRunner:
    def __init__(self,parent):
        self.parent = parent
        self.menu = MainMenu()

        self.frame = ttk.LabelFrame(parent, text="Prediction / Model Suite from CSV", padding=12)
        self.frame.pack(fill="both", expand=True)

        self.csv_path_var = tk.StringVar()
        self.label_var = tk.StringVar(value="J_k5_z2p0")

        self._build_ui()

    def _build_ui(self):
        frame = ttk.Frame(self.frame, padding=16)
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame,
            text="Run Prediction Models from CSV",
            font=("Arial", 16, "bold")
        ).pack(anchor="w", pady=(0, 12))

        ttk.Label(frame, text="CSV File").pack(anchor="w")

        csv_row = ttk.Frame(frame)
        csv_row.pack(fill="x", pady=(4, 12))

        ttk.Entry(
            csv_row,
            textvariable=self.csv_path_var,
            width=60
        ).pack(side="left", fill="x", expand=True)

        ttk.Button(
            csv_row,
            text="Browse",
            command=self._browse_csv_file
        ).pack(side="left", padx=(8, 0))

        ttk.Label(frame, text="Label Column").pack(anchor="w")

        ttk.Combobox(
            frame,
            textvariable=self.label_var,
            state="readonly",
            values=[
                "J_k5_z2p0",
                "J_k10_z2p0",
                "J_k5_d0p1",
                "J_k10_d0p1",
            ],
        ).pack(fill="x", pady=(4, 12))

        button_row = ttk.Frame(frame)
        button_row.pack(fill="x", pady=(10, 0))

        ttk.Button(
            button_row,
            text="Run Prediction",
            command=self.run_prediction_from_csv
        ).pack(side="left")

        ttk.Button(
            button_row,
            text="Close",
            command=self.frame.destroy
        ).pack(side="left", padx=8)

    def _browse_csv_file(self):
        path = filedialog.askopenfilename(
            title="Select CSV File",
            initialdir='/Users/yagzanmanjunaath/UniWorkspace/ResearchMethods/Part2/ADSynth/analysis/csv',
            filetypes=[("CSV files", "*.csv")]
        )

        if path:
            self.csv_path_var.set(path)

    def run_prediction_from_csv(self):
        csv_path = self.csv_path_var.get().strip()
        label_col = self.label_var.get().strip()

        if not csv_path:
            messagebox.showerror("Missing CSV File", "Please choose a CSV file.")
            return

        def worker():
            try:
                self.menu.run_model_suite_from_csv(
                    csv_path=csv_path,
                    label_col=label_col,
                )

                self.parent.after(
                    0,
                    lambda: messagebox.showinfo(
                        "Success",
                        f"Prediction completed.\nLabel: {label_col}"
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
    root.title("Prediction Runner")
    root.geometry("750x350")

    app = PredictionRunner(root)

    root.mainloop()