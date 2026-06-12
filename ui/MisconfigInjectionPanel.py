import tkinter as tk
from tkinter import ttk, messagebox
import threading
from tkinter import ttk, messagebox, filedialog

class MisconfigInjectionPanel:
    def __init__(self, parent, menu):
        self.mitigation_enabled = tk.BooleanVar(value=False)
        self.parent = parent
        self.menu = menu
        self.frame = ttk.LabelFrame(parent, text="Misconfiguration Injection", padding=12)
        self.frame.pack(fill="both", expand=True)

        self.schedule_type = tk.StringVar(value="isolated")

        self.session_var = tk.BooleanVar(value=True)
        self.i_perm_var = tk.BooleanVar(value=False)
        self.g_perm_var = tk.BooleanVar(value=False)
        self.nesting_var = tk.BooleanVar(value=False)
        self.neo4j_json_path_var = tk.StringVar()
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

        ttk.Checkbutton(
            frame,
            text="Enable Mitigation",
            variable=self.mitigation_enabled
        ).pack(anchor="w", pady=(8, 12))

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=(16, 12))

        ttk.Label(
            frame,
            text="Load Neo4j Graph from JSON",
            font=("Arial", 11, "bold")
        ).pack(anchor="w", pady=(0, 6))

        ttk.Label(frame, text="JSON File").pack(anchor="w")

        neo4j_file_row = ttk.Frame(frame)
        neo4j_file_row.pack(fill="x", pady=(4, 8))

        ttk.Entry(
            neo4j_file_row,
            textvariable=self.neo4j_json_path_var
        ).pack(side="left", fill="x", expand=True)

        ttk.Button(
            neo4j_file_row,
            text="Browse",
            command=self.select_neo4j_json_file
        ).pack(side="left", padx=(8, 0))

        ttk.Button(
            frame,
            text="Load JSON into Neo4j",
            command=self.load_neo4j_json
        ).pack(anchor="w", pady=(4, 12))

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

    def select_neo4j_json_file(self):
        filename = filedialog.askopenfilename(
            title="Select Graph JSON File",
            filetypes=[
                ("JSON files", "*.json"),
                ("All files", "*.*")
            ]
        )

        if filename:
            self.neo4j_json_path_var.set(filename)

    def load_neo4j_json(self):
        filename = self.neo4j_json_path_var.get().strip()

        if not filename:
            messagebox.showerror("No File Selected", "Please select a JSON file.")
            return

        def worker():
            try:
                self.menu.do_load_neo4jFromJson(filename)

                self.parent.after(
                    0,
                    lambda: messagebox.showinfo(
                        "Success",
                        "Graph loaded into Neo4j successfully."
                    )
                )

            except Exception as e:
                self.parent.after(
                    0,
                    lambda: messagebox.showerror("Error", str(e))
                )

        threading.Thread(target=worker, daemon=True).start()
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
        selected_injections = self.get_selected_injections()

        if not selected_injections:
            messagebox.showerror("No Injection Selected", "Please select at least one injection type.")
            return

        def worker():
            try:
                if mode == "isolated":
                    if len(selected_injections) == 1:
                        self.menu.run_injection_schedule(mode,self.mitigation_enabled.get(),selected_injections)
                    else:
                        self.parent.after(
                            0,
                            lambda: messagebox.showerror(
                                "Error",
                                "Isolated mode can run only one injection type."
                            )
                        )

                elif mode == "mixed":
                    if len(selected_injections) > 1:
                        self.menu.run_injection_schedule(mode,self.mitigation_enabled.get(), selected_injections)
                    else:
                        self.parent.after(
                            0,
                            lambda: messagebox.showerror(
                                "Error",
                                "Mixed mode requires multiple injection types."
                            )
                        )

                elif mode == "sequence":
                    self.menu.run_injection_schedule(mode, self.mitigation_enabled.get(),selected_injections)

                self.parent.after(
                    0,
                    lambda: messagebox.showinfo(
                        "Success",
                        f"{mode.title()} injection schedule completed."
                    )
                )

            except Exception as e:
                self.parent.after(
                    0,
                    lambda: messagebox.showerror("Error", str(e))
                )

        threading.Thread(target=worker, daemon=True).start()