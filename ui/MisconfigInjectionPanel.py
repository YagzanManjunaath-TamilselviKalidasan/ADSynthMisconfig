import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading


class MisconfigInjectionPanel:
    def __init__(self, parent, menu):
        self.parent = parent
        self.menu = menu
        self.frame = ttk.LabelFrame(parent, text="Misconfiguration Injection", padding=12)
        self.frame.pack(fill="both", expand=True)
        self.schedule_type = tk.StringVar(value="isolated")
        self.injection_schedules = []

        self.session_var = tk.BooleanVar(value=True)
        self.i_perm_var = tk.BooleanVar(value=False)
        self.g_perm_var = tk.BooleanVar(value=False)
        self.nesting_var = tk.BooleanVar(value=False)

        self.csv_path_var = tk.StringVar()
        self.logreg_label_var = tk.StringVar(value="J_k5_z2p0")
        self.run_logreg_after_injection_var = tk.BooleanVar(value=False)
        self._build_ui()

    def _browse_csv_file(self):
        path = filedialog.askopenfilename(
            title="Select CSV File",
            filetypes=[("CSV files", "*.csv")]
        )
        if path:
            self.csv_path_var.set(path)

    def run_model_suite_from_csv_ui(self):
        csv_path = self.csv_path_var.get().strip()
        label_col = self.logreg_label_var.get().strip()

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
                        f"Model suite completed.\nLabel: {label_col}"
                    )
                )
            except Exception as e:
                err_msg = str(e)
                self.parent.after(
                    0,
                    lambda: messagebox.showerror("Error", err_msg)
                )

        threading.Thread(target=worker, daemon=True).start()

    def _build_ui(self):
        frame = ttk.Frame(self.frame, padding=16)

        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame,
            text="Choose Injection Schedule",
            font=("Arial", 16, "bold")
        ).pack(anchor="w", pady=(0, 12))

        ttk.Radiobutton(
            frame,
            text="Isolated - 4 paths",
            variable=self.schedule_type,
            value="isolated",
            command=self._update_description
        ).pack(anchor="w", pady=4)

        ttk.Radiobutton(
            frame,
            text="Mixed",
            variable=self.schedule_type,
            value="mixed",
            command=self._update_description
        ).pack(anchor="w", pady=4)

        ttk.Radiobutton(
            frame,
            text="Sequence",
            variable=self.schedule_type,
            value="sequence",
            command=self._update_description
        ).pack(anchor="w", pady=4)
        ttk.Label(
            frame,
            text="Select Injection Types",
            font=("Arial", 11, "bold")
        ).pack(anchor="w", pady=(16, 6))

        ttk.Checkbutton(frame, text="Session", variable=self.session_var).pack(anchor="w", pady=2)
        ttk.Checkbutton(frame, text="Individual Permission", variable=self.i_perm_var).pack(anchor="w", pady=2)
        ttk.Checkbutton(frame, text="Group Permission", variable=self.g_perm_var).pack(anchor="w", pady=2)
        ttk.Checkbutton(frame, text="Group Nesting", variable=self.nesting_var).pack(anchor="w", pady=2)

        ttk.Label(frame, text="Description", font=("Arial", 11, "bold")).pack(anchor="w", pady=(16, 4))

        self.description = tk.Text(frame, height=8, wrap="word")
        self.description.pack(fill="x", pady=(0, 12))

        ttk.Label(frame, text="Optional Output Name").pack(anchor="w")
        self.output_name_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.output_name_var).pack(fill="x", pady=(4, 12))

        button_row = ttk.Frame(frame)
        button_row.pack(fill="x", pady=(10, 0))

        ttk.Button(button_row, text="Run Injection", command=self.run_selected_schedule).pack(side="left")
        ttk.Button(button_row, text="Close", command=self.frame.destroy).pack(side="left", padx=8)

        self._update_description()
        logreg_frame = ttk.LabelFrame(frame, text="Run Model Suite from CSV", padding=10)
        logreg_frame.pack(fill="x", pady=(8, 12))

        ttk.Checkbutton(
            logreg_frame,
            text="Run model suite after injection",
            variable=self.run_logreg_after_injection_var
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))

        ttk.Label(logreg_frame, text="CSV File").grid(row=1, column=0, sticky="w")
        ttk.Entry(logreg_frame, textvariable=self.csv_path_var, width=50).grid(row=1, column=1, sticky="ew", padx=6)
        ttk.Button(logreg_frame, text="Browse", command=self._browse_csv_file).grid(row=1, column=2, sticky="w")

        ttk.Label(logreg_frame, text="Label Column").grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Combobox(
            logreg_frame,
            textvariable=self.logreg_label_var,
            state="readonly",
            values=[
                "J_k5_z2p0",
                "J_k10_z2p0",
                "J_k5_d0p1",
                "J_k10_d0p1",
            ],
        ).grid(row=2, column=1, sticky="ew", padx=6, pady=(8, 0))
        # combo.set("J_k5_z2p0")
        ttk.Button(
            logreg_frame,
            text="Run M1–M5 from CSV",
            command=self.run_model_suite_from_csv_ui
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(10, 0))

        logreg_frame.columnconfigure(1, weight=1)

    def get_selected_injections(self):
        injections = []

        if self.session_var.get():
            injections.append("session")
        if self.i_perm_var.get():
            injections.append("i_perm")
        if self.g_perm_var.get():
            injections.append("g_perm")
        if self.nesting_var.get():
            injections.append("nesting")

        return injections

    def _update_description(self):
        mode = self.schedule_type.get()
        self.description.delete("1.0", "end")

        if mode == "isolated":
            self.description.insert(
                "end",
                "Run four independent injection paths from the same baseline graph:\n"
                "1. Session only\n"
                "2. Individual permission only\n"
                "3. Group permission only\n"
                "4. Group nesting only\n\n"

            )
        elif mode == "mixed":
            self.description.insert(
                "end",
                "Run a single experiment where multiple misconfiguration types are injected together "
                "into the same graph.\n\n"

            )
        elif mode == "sequence":
            self.description.insert(
                "end",
                "Run staged injections in a fixed order over time.\n\n"
                "Example:\n"
                "Stage 1 -> Session\n"
                "Stage 2 -> Individual permissions\n"
                "Stage 3 -> Group permissions\n"
                "Stage 4 -> Group nesting\n\n"

            )

    def run_selected_schedule(self):
        mode = self.schedule_type.get()
        output_name = self.output_name_var.get().strip()
        selected_injections = self.get_selected_injections()

        if not selected_injections:
            messagebox.showerror("No Injection Selected", "Please select at least one injection type.")
            return

        def worker():
            try:
                if mode == "isolated":
                    if len(selected_injections) == 1:
                        self.menu.run_injection_schedule(mode, selected_injections)
                    else:
                        self.parent.after(
                            0,
                            lambda: messagebox.showerror("Error",
                                                         "Isolated mode can run only injection schedules\n Please select only one schedule.")
                        )
                elif mode == "mixed":
                    if len(selected_injections) > 1:
                        self.menu.run_injection_schedule(mode, selected_injections)
                    else:
                        self.parent.after(
                            0,
                            lambda: messagebox.showerror("Error",
                                                         "Mixed mode can run multiple injection schedules\n Please select more than one schedule.")
                        )
                elif mode == "sequence":
                    self.menu.run_injection_schedule(mode, selected_injections)

                self.parent.after(
                    0,
                    lambda: messagebox.showinfo("Success", f"{mode.title()} injection schedule completed.")
                )

                if self.run_logreg_after_injection_var.get():
                    csv_path = self.csv_path_var.get().strip()
                    label_col = self.logreg_label_var.get().strip()

                    if csv_path:
                        self.menu.run_model_suite_from_csv(
                            csv_path=csv_path,
                            label_col=label_col,
                        )

            except Exception as e:

                err_msg = str(e)

                self.parent.after(
                    0,
                    lambda: messagebox.showerror("Error", err_msg)
                )

        threading.Thread(target=worker, daemon=True).start()
