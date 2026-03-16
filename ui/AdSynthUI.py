import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import io
import contextlib

from adsynth.ADSynth import MainMenu, safe_import_neo4j
from adsynth.utils.ablation_study_utils import populate_node_tiers
from adsynth.utils.data import get_parameters_from_json
from ui.MisconfigInjectionPanel import MisconfigInjectionPanel


# Reuse your existing MainMenu class
# from your_module import MainMenu


class ADSynthUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ADSynth UI")
        self.root.geometry("1100x900")

        self.menu = MainMenu()

        self.json_path_var = tk.StringVar(value="/Users/yagzanmanjunaath/UniWorkspace/ResearchMethods/Part2/ADSynth/adsynth/experiment_params/vul_1k.json")
        self.level_var = tk.StringVar(value="High")
        self.db_url_var = tk.StringVar(value=self.menu.url)
        self.db_user_var = tk.StringVar(value=self.menu.username)
        self.db_pass_var = tk.StringVar(value="admin1234")
        self.domain_var = tk.StringVar(value=self.menu.domain)
        self.misconfig_var = tk.BooleanVar(value=True)

        self._build_ui()

    def _build_ui(self):


        main = ttk.Frame(self.root, padding=12)
        main.pack(fill="both", expand=True)


        right_panel = ttk.Frame(main)
        right_panel.pack(side="right", fill="y", padx=(0, 12))


        left_panel = ttk.Frame(main)
        left_panel.pack(side="left", fill="both", expand=True)

        # build embedded misconfig panel
        self.misconfig_panel = MisconfigInjectionPanel(right_panel, self.menu)
        self.misconfig_panel.frame.pack_forget()
        title = ttk.Label(left_panel, text="ADSynth Graph Initializer", font=("Arial", 16, "bold"))
        title.pack(anchor="w", pady=(0, 12))

        form = ttk.Frame(left_panel)
        form.pack(fill="x", pady=4)

        self._add_row(form, "JSON Config", self.json_path_var, browse=True)
        self._add_row(form, "Security Level", self.level_var, combobox_values=["Customized", "Low", "High"])
        self._add_row(form, "Domain", self.domain_var)
        self._add_row(form, "Neo4j URL", self.db_url_var)
        self._add_row(form, "Neo4j Username", self.db_user_var)
        self._add_row(form, "Neo4j Password", self.db_pass_var, show="*")

        ttk.Checkbutton(
            left_panel,
            text="Enable initial misconfiguration",
            variable=self.misconfig_var
        ).pack(anchor="w", pady=(8, 12))

        button_frame = ttk.Frame(left_panel)
        button_frame.pack(fill="x", pady=6)

        ttk.Button(button_frame, text="Test DB Connection", command=self.test_connection).pack(side="left", padx=(0, 8))
        ttk.Button(button_frame, text="Generate Graph", command=self.run_generation).pack(side="left", padx=(0, 8))
        ttk.Button(button_frame, text="Clear Output", command=self.clear_output).pack(side="left")

        ttk.Label(left_panel, text="Output Log", font=("Arial", 11, "bold")).pack(anchor="w", pady=(14, 6))

        self.output = tk.Text(left_panel, wrap="word", height=22)
        self.output.pack(fill="both", expand=True)

    def _add_row(self, parent, label_text, variable, browse=False, combobox_values=None, show=None):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=4)

        ttk.Label(row, text=label_text, width=18).pack(side="left")

        if combobox_values:
            widget = ttk.Combobox(row, textvariable=variable, values=combobox_values, state="readonly")
            widget.pack(side="left", fill="x", expand=True)
        else:
            widget = ttk.Entry(row, textvariable=variable, show=show)
            widget.pack(side="left", fill="x", expand=True)

        if browse:
            ttk.Button(row, text="Browse", command=self.browse_json).pack(side="left", padx=(8, 0))

    def browse_json(self):
        file_path = filedialog.askopenfilename(
            title="Select JSON Config",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if file_path:
            self.json_path_var.set(file_path)

    def log(self, text):
        self.output.insert("end", text + "\n")
        self.output.see("end")
        self.root.update_idletasks()

    def clear_output(self):
        self.output.delete("1.0", "end")

    def _sync_to_menu(self):
        self.menu.url = self.db_url_var.get().strip()
        self.menu.username = self.db_user_var.get().strip()
        self.menu.password = self.db_pass_var.get().strip()
        self.menu.domain = self.domain_var.get().strip().upper()
        self.menu.level = self.level_var.get().strip()
        self.menu.misconfig_enabled = self.misconfig_var.get()

    def test_connection(self):
        self._sync_to_menu()

        def worker():
            buffer = io.StringIO()
            try:
                with contextlib.redirect_stdout(buffer):
                    global neo4j
                    neo4j = safe_import_neo4j()
                    if neo4j is None:
                        raise RuntimeError("Neo4j driver not available.")
                    self.menu.test_db_conn()

                self.log(buffer.getvalue())
                if self.menu.connected:
                    self.log("DB connection successful.\n")
                else:
                    self.log("DB connection failed.\n")
            except Exception as e:
                self.log(f"Error while testing DB connection: {e}\n")

        threading.Thread(target=worker, daemon=True).start()
    def show_misconfig_panel(self):
        if not self.misconfig_panel.frame.winfo_ismapped():
            self.misconfig_panel.frame.pack(fill="y", expand=False)
    def run_generation(self):
        json_path = self.json_path_var.get().strip()
        if not json_path:
            messagebox.showerror("Missing JSON", "Please select a JSON configuration file.")
            return

        self._sync_to_menu()

        def worker():
            buffer = io.StringIO()
            try:
                with contextlib.redirect_stdout(buffer):
                    global neo4j
                    neo4j = safe_import_neo4j()
                    if neo4j is None:
                        raise RuntimeError("Neo4j driver not available.")

                    self.menu.password = self.db_pass_var.get().strip()
                    self.menu.test_db_conn()

                    if not self.menu.connected:
                        raise RuntimeError("Could not connect to Neo4j.")

                    self.menu.parameters = get_parameters_from_json(json_path)
                    self.menu.parameters_json_path = json_path
                    self.menu.do_generate(json_path)
                    populate_node_tiers()

                self.log(buffer.getvalue())
                self.log("Graph generation completed.\n")
                messagebox.showinfo("Success", "Graph generation completed.")
                self.root.after(0, self.show_misconfig_panel)


            except Exception as e:
                self.log(buffer.getvalue())
                self.log(f"Error: {e}\n")
                messagebox.showerror("Generation Failed", str(e))

        threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    root = tk.Tk()
    app = ADSynthUI(root)
    root.mainloop()