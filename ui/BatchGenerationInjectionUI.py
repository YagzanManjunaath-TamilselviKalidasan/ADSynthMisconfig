import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import io
import contextlib

from adsynth.ADSynth import MainMenu, safe_import_neo4j
from adsynth.utils.data import get_parameters_from_json
from adsynth.utils.ablation_study_utils import populate_node_tiers, build_tier_caches


class BatchGenerationInjectionUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ADSynth Batch Generation + Injection Runner")
        self.root.geometry("1100x850")

        self.menu = MainMenu()

        self.json_path_var = tk.StringVar(value="")
        self.level_var = tk.StringVar(value="High")
        self.domain_var = tk.StringVar(value=self.menu.domain)
        self.db_url_var = tk.StringVar(value=self.menu.url)
        self.db_user_var = tk.StringVar(value=self.menu.username)
        self.db_pass_var = tk.StringVar(value="admin1234")

        self.random_values_var = tk.StringVar(value="1,2,3,4,5")
        self.run_without_misconfig_var = tk.BooleanVar(value=True)
        self.run_with_misconfig_var = tk.BooleanVar(value=True)

        self.run_session_only_var = tk.BooleanVar(value=True)
        self.run_mixed_var = tk.BooleanVar(value=True)

        self._build_ui()

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=14)
        main.pack(fill="both", expand=True)

        ttk.Label(
            main,
            text="Batch Graph Generation + Injection Runner",
            font=("Arial", 16, "bold")
        ).pack(anchor="w", pady=(0, 12))

        form = ttk.Frame(main)
        form.pack(fill="x")

        self._add_row(form, "JSON Config", self.json_path_var, browse=True)
        self._add_row(form, "Security Level", self.level_var, combobox_values=["Customized", "Low", "High"])
        self._add_row(form, "Domain", self.domain_var)
        self._add_row(form, "Neo4j URL", self.db_url_var)
        self._add_row(form, "Neo4j Username", self.db_user_var)
        self._add_row(form, "Neo4j Password", self.db_pass_var, show="*")
        self._add_row(form, "Random values", self.random_values_var)

        ttk.Label(
            main,
            text="Generation Variants",
            font=("Arial", 11, "bold")
        ).pack(anchor="w", pady=(16, 6))

        ttk.Checkbutton(
            main,
            text="Generate without initial misconfiguration",
            variable=self.run_without_misconfig_var
        ).pack(anchor="w")

        ttk.Checkbutton(
            main,
            text="Generate with initial misconfiguration",
            variable=self.run_with_misconfig_var
        ).pack(anchor="w")

        ttk.Label(
            main,
            text="Injection Experiments After Each Generation",
            font=("Arial", 11, "bold")
        ).pack(anchor="w", pady=(16, 6))

        ttk.Checkbutton(
            main,
            text="Session only injection",
            variable=self.run_session_only_var
        ).pack(anchor="w")

        ttk.Checkbutton(
            main,
            text="Session + permission + nesting injection",
            variable=self.run_mixed_var
        ).pack(anchor="w")

        button_row = ttk.Frame(main)
        button_row.pack(fill="x", pady=(16, 8))

        ttk.Button(
            button_row,
            text="Test DB Connection",
            command=self.test_connection
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            button_row,
            text="Run Batch",
            command=self.run_batch
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            button_row,
            text="Clear Output",
            command=self.clear_output
        ).pack(side="left")

        ttk.Label(
            main,
            text="Output Log",
            font=("Arial", 11, "bold")
        ).pack(anchor="w", pady=(12, 4))

        self.output = tk.Text(main, wrap="word", height=25)
        self.output.pack(fill="both", expand=True)

    def _add_row(self, parent, label_text, variable, browse=False, combobox_values=None, show=None):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=4)

        ttk.Label(row, text=label_text, width=20).pack(side="left")

        if combobox_values:
            widget = ttk.Combobox(
                row,
                textvariable=variable,
                values=combobox_values,
                state="readonly"
            )
        else:
            widget = ttk.Entry(row, textvariable=variable, show=show)

        widget.pack(side="left", fill="x", expand=True)

        if browse:
            ttk.Button(row, text="Browse", command=self.browse_json).pack(side="left", padx=(8, 0))

    def browse_json(self):
        path = filedialog.askopenfilename(
            title="Select JSON Config",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if path:
            self.json_path_var.set(path)

    def log(self, msg):
        self.output.insert("end", msg + "\n")
        self.output.see("end")
        self.root.update_idletasks()

    def clear_output(self):
        self.output.delete("1.0", "end")

    def parse_random_values(self):
        raw = self.random_values_var.get().strip()

        if not raw:
            raise ValueError("Please provide at least one random value.")

        values = []
        for item in raw.split(","):
            item = item.strip()
            if item:
                values.append(int(item))

        if not values:
            raise ValueError("No valid random values found.")

        return values

    def _sync_to_menu(self, seed, initial_misconfig):
        self.menu.url = self.db_url_var.get().strip()
        self.menu.username = self.db_user_var.get().strip()
        self.menu.password = self.db_pass_var.get().strip()
        self.menu.domain = self.domain_var.get().strip().upper()
        self.menu.level = self.level_var.get().strip()

        self.menu.seed_number = seed
        self.menu.misconfig_enabled = initial_misconfig

    def test_connection(self):
        def worker():
            buffer = io.StringIO()
            try:
                with contextlib.redirect_stdout(buffer):
                    neo4j = safe_import_neo4j()
                    if neo4j is None:
                        raise RuntimeError("Neo4j driver not available.")

                    self.menu.url = self.db_url_var.get().strip()
                    self.menu.username = self.db_user_var.get().strip()
                    self.menu.password = self.db_pass_var.get().strip()
                    self.menu.test_db_conn()

                self.log(buffer.getvalue())

                if self.menu.connected:
                    self.log("DB connection successful.")
                else:
                    self.log("DB connection failed.")

            except Exception as e:
                self.log(buffer.getvalue())
                self.log(f"Connection error: {e}")

        threading.Thread(target=worker, daemon=True).start()

    def run_batch(self):
        json_path = self.json_path_var.get().strip()

        if not json_path:
            messagebox.showerror("Missing JSON", "Please select a JSON config file.")
            return

        try:
            seeds = self.parse_random_values()
        except Exception as e:
            messagebox.showerror("Invalid Random Values", str(e))
            return

        generation_variants = []

        if self.run_without_misconfig_var.get():
            generation_variants.append(False)

        if self.run_with_misconfig_var.get():
            generation_variants.append(True)

        if not generation_variants:
            messagebox.showerror("No Generation Variant", "Select at least one generation variant.")
            return

        if not self.run_session_only_var.get() and not self.run_mixed_var.get():
            messagebox.showerror("No Injection Selected", "Select at least one injection experiment.")
            return

        def worker():
            buffer = io.StringIO()

            try:
                with contextlib.redirect_stdout(buffer):
                    neo4j = safe_import_neo4j()
                    if neo4j is None:
                        raise RuntimeError("Neo4j driver not available.")

                    self.menu.url = self.db_url_var.get().strip()
                    self.menu.username = self.db_user_var.get().strip()
                    self.menu.password = self.db_pass_var.get().strip()
                    self.menu.test_db_conn()

                    if not self.menu.connected:
                        raise RuntimeError("Could not connect to Neo4j.")

                self.log(buffer.getvalue())

                for seed in seeds:
                    for initial_misconfig in generation_variants:
                        label = "WITH initial misconfig" if initial_misconfig else "WITHOUT initial misconfig"

                        self.log("=" * 80)
                        self.log(f"Starting generation | seed={seed} | {label}")

                        buffer = io.StringIO()

                        with contextlib.redirect_stdout(buffer):
                            self._sync_to_menu(seed, initial_misconfig)

                            self.menu.parameters = get_parameters_from_json(json_path)
                            self.menu.parameters_json_path = json_path

                            self.menu.do_generate(json_path)

                            populate_node_tiers()
                            build_tier_caches()

                        self.log(buffer.getvalue())
                        self.log(f"Generation completed | seed={seed} | {label}")

                        if self.run_session_only_var.get():
                            self.log("Running Session only injection...")

                            buffer = io.StringIO()
                            with contextlib.redirect_stdout(buffer):
                                self.menu.run_injection_schedule(
                                    "isolated",
                                    False,
                                    ["session"]
                                )

                            self.log(buffer.getvalue())
                            self.log("Session only injection completed.")

                        if self.run_mixed_var.get():
                            self.log("Running Session + Permission + Nesting injection...")

                            buffer = io.StringIO()
                            with contextlib.redirect_stdout(buffer):
                                self.menu.run_injection_schedule(
                                    "mixed",
                                    False,
                                    ["session", "i_perm", "g_perm", "nesting"]
                                )

                            self.log(buffer.getvalue())
                            self.log("Session + Permission + Nesting injection completed.")

                self.log("=" * 80)
                self.log("Batch run completed.")
                self.root.after(0, lambda: messagebox.showinfo("Success", "Batch run completed."))

            except Exception as e:
                self.log(buffer.getvalue())
                self.log(f"Error: {e}")
                self.root.after(0, lambda: messagebox.showerror("Batch Failed", str(e)))

        threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    root = tk.Tk()
    app = BatchGenerationInjectionUI(root)
    root.mainloop()