import tkinter as tk
from tkinter import ttk, messagebox
import threading


class MisconfigInjectionPanel:
    def __init__(self, parent, menu):
        self.parent = parent
        self.menu = menu

        self.schedule_type = tk.StringVar(value="isolated")
        self.injection_schedules = []

        self.session_var = tk.BooleanVar(value=True)
        self.i_perm_var = tk.BooleanVar(value=False)
        self.g_perm_var = tk.BooleanVar(value=False)
        self.nesting_var = tk.BooleanVar(value=False)

        self.frame = ttk.LabelFrame(parent, text="Misconfiguration Injection", padding=12)

        self._build_ui()

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


            except Exception as e:

                err_msg = str(e)

                self.parent.after(
                    0,
                    lambda: messagebox.showerror("Error", err_msg)
                )

        threading.Thread(target=worker, daemon=True).start()
