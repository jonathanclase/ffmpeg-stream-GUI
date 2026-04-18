import tkinter as tk
from tkinter import filedialog
import os
from datetime import datetime


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("File Browser")
        self.geometry("800x500")

        self.open_files: dict[str, os.stat_result] = {}

        self._build_toolbar()
        self._build_main_pane()

    def _build_toolbar(self):
        toolbar = tk.Frame(self, bd=1, relief=tk.RAISED)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        tk.Button(toolbar, text="Open File", command=self.open_file).pack(side=tk.LEFT, padx=2, pady=2)

    def _build_main_pane(self):
        pane = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, sashwidth=5)
        pane.pack(fill=tk.BOTH, expand=True)
        self._build_left_pane(pane)
        self._build_right_pane(pane)

    def _build_left_pane(self, parent):
        frame = tk.Frame(parent, bd=1, relief=tk.SUNKEN)
        parent.add(frame, minsize=150)

        tk.Label(frame, text="Open Files", font=("", 10, "bold")).pack(side=tk.TOP, fill=tk.X, padx=4, pady=(4, 0))

        scrollbar = tk.Scrollbar(frame, orient=tk.VERTICAL)
        self.file_listbox = tk.Listbox(frame, yscrollcommand=scrollbar.set, selectmode=tk.SINGLE)
        scrollbar.config(command=self.file_listbox.yview)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.file_listbox.bind("<<ListboxSelect>>", self.on_select)

    def _build_right_pane(self, parent):
        frame = tk.Frame(parent, bd=1, relief=tk.SUNKEN)
        parent.add(frame, minsize=200)

        tk.Label(frame, text="File Info", font=("", 10, "bold")).pack(anchor=tk.W, padx=8, pady=(8, 4))

        self.var_path = tk.StringVar()
        self.var_size = tk.StringVar()
        self.var_modified = tk.StringVar()

        for label_text, var in [("Path:", self.var_path), ("Size:", self.var_size), ("Modified:", self.var_modified)]:
            row = tk.Frame(frame)
            row.pack(fill=tk.X, padx=8, pady=2)
            tk.Label(row, text=label_text, width=10, anchor=tk.W).pack(side=tk.LEFT)
            tk.Label(row, textvariable=var, anchor=tk.W, wraplength=400, justify=tk.LEFT).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def open_file(self):
        paths = filedialog.askopenfilenames()
        if not paths:
            return
        for path in paths:
            if path in self.open_files:
                continue
            self.open_files[path] = os.stat(path)
            self.file_listbox.insert(tk.END, os.path.basename(path))

    def on_select(self, event):
        sel = self.file_listbox.curselection()
        if not sel:
            self.clear_info()
            return
        path = list(self.open_files.keys())[sel[0]]
        self.update_info(path)

    def update_info(self, path: str):
        stat = self.open_files[path]
        self.var_path.set(path)
        self.var_size.set(f"{stat.st_size:,} bytes")
        self.var_modified.set(datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"))

    def clear_info(self):
        self.var_path.set("")
        self.var_size.set("")
        self.var_modified.set("")


if __name__ == "__main__":
    app = App()
    app.mainloop()
