import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading


class Neo4jJsonLoadPanel:
    def __init__(self, parent, menu):
        self.parent = parent
        self.menu = menu

        self.frame = ttk.LabelFrame(parent, text="Load Neo4j Graph from JSON", padding=12)
        self.frame.pack(fill="both", expand=True)

        self.json_path_var = tk.StringVar()

        self._build_ui()

    def _build_ui(self):
        frame = ttk.Frame(self.frame, padding=16)
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame,
            text="Load Graph JSON into Neo4j",
            font=("Arial", 16, "bold")
        ).pack(anchor="w", pady=(0, 12))

        ttk.Label(frame, text="Select JSON File").pack(anchor="w")

        file_row = ttk.Frame(frame)
        file_row.pack(fill="x", pady=(4, 12))

        ttk.Entry(
            file_row,
            textvariable=self.json_path_var
        ).pack(side="left", fill="x", expand=True)

        ttk.Button(
            file_row,
            text="Browse",
            command=self.select_json_file
        ).pack(side="left", padx=(8, 0))

        self.description = tk.Text(frame, height=5, wrap="word")
        self.description.pack(fill="x", pady=(0, 12))
        self.description.insert(
            "end",
            "This will clear the current Neo4j experiment database and load the selected JSON graph file."
        )
        self.description.config(state="disabled")

        button_row = ttk.Frame(frame)
        button_row.pack(fill="x", pady=(10, 0))

        ttk.Button(
            button_row,
            text="Load into Neo4j",
            command=self.load_selected_json
        ).pack(side="left")

        ttk.Button(
            button_row,
            text="Close",
            command=self.frame.destroy
        ).pack(side="left", padx=8)

    def select_json_file(self):
        filename = filedialog.askopenfilename(
            title="Select Graph JSON File",
            filetypes=[
                ("JSON files", "*.json"),
                ("All files", "*.*")
            ]
        )

        if filename:
            self.json_path_var.set(filename)

    def load_selected_json(self):
        filename = self.json_path_var.get().strip()

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