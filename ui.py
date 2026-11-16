"""Simple database browser: view and edit app tables from the menu."""
import tkinter as tk
from tkinter import messagebox, ttk

from database import Database

# Four advanced tables are hidden from the menu; their existing data is preserved.
TABLES = {
    "clients": "Klienti", "projects": "Projekti", "deliverables": "Nodevumi",
    "activities": "Darbības", "team_members": "Komandas locekļi",
    "time_logs": "Laika ieraksti", "palette_colors": "Krāsu paletes",
    "revision_logs": "Labojumu vēsture",
}

EXTRA_SCHEMA = """
CREATE TABLE IF NOT EXISTS deliverables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL, format TEXT, done INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS project_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    member_id INTEGER NOT NULL REFERENCES team_members(id) ON DELETE CASCADE,
    role TEXT, allocation_pct REAL,
    UNIQUE(project_id, member_id)
);
"""


class DesignApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Dizaina projektu pārvaldnieks")
        self.geometry("1200x760")
        self.minsize(900, 600)
        self.db = Database()
        self.db.connection.executescript(EXTRA_SCHEMA)
        self.db.connection.commit()
        self.table_name, self.columns = None, []

        ttk.Label(self, text="Dizaina projektu pārvaldnieks",
                  font=("TkDefaultFont", 18, "bold")).pack(anchor="w", padx=14, pady=10)
        body = ttk.Frame(self, padding=(12, 0, 12, 12))
        body.pack(fill="both", expand=True)
        menu = ttk.LabelFrame(body, text="Tabulas", padding=8)
        menu.pack(side="left", fill="y", padx=(0, 10))
        self.table_menu = tk.Listbox(menu, width=23, exportselection=False)
        self.table_menu.pack(fill="y", expand=True)
        for title in TABLES.values():
            self.table_menu.insert("end", title)
        self.table_menu.bind("<<ListboxSelect>>", self.open_table)

        self.page = ttk.Frame(body)
        self.page.pack(side="left", fill="both", expand=True)
        self.title_label = ttk.Label(self.page, text="Izvēlies tabulu kreisajā izvēlnē",
                                     font=("TkDefaultFont", 13, "bold"))
        self.title_label.pack(anchor="w", pady=(0, 8))
        self.form = ttk.LabelFrame(self.page, text="Ieraksta dati", padding=8)
        self.form.pack(fill="x", pady=(0, 8))
        self.entries = {}
        buttons = ttk.Frame(self.page)
        buttons.pack(fill="x", pady=(0, 8))
        for label, command in (("Pievienot", self.add_row), ("Saglabāt", self.update_row),
                               ("Dzēst", self.delete_row), ("Notīrīt", self.clear_form),
                               ("Atjaunot", self.refresh)):
            ttk.Button(buttons, text=label, command=command).pack(side="left", padx=(0, 5))
        grid = ttk.Frame(self.page)
        grid.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(grid, show="headings")
        ybar = ttk.Scrollbar(grid, orient="vertical", command=self.tree.yview)
        xbar = ttk.Scrollbar(self.page, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=ybar.set, xscrollcommand=xbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        ybar.pack(side="right", fill="y")
        xbar.pack(fill="x")
        self.tree.bind("<<TreeviewSelect>>", self.select_row)
        self.protocol("WM_DELETE_WINDOW", self.close)

    def open_table(self, _event=None):
        selected = self.table_menu.curselection()
        if not selected:
            return
        self.table_name = list(TABLES)[selected[0]]
        self.title_label.config(text=TABLES[self.table_name])
        info = self.db.connection.execute(f"PRAGMA table_info({self.table_name})").fetchall()
        self.columns = [row[1] for row in info]
        primary_keys = {row[1] for row in info if row[5]}
        for widget in self.form.winfo_children():
            widget.destroy()
        self.entries.clear()
        for index, column in enumerate(c for c in self.columns if c not in primary_keys):
            line = ttk.Frame(self.form)
            line.grid(row=index // 4, column=index % 4, sticky="ew", padx=4, pady=3)
            ttk.Label(line, text=column).pack(anchor="w")
            entry = ttk.Entry(line, width=22)
            entry.pack(fill="x")
            self.entries[column] = entry
        for column in range(4):
            self.form.columnconfigure(column, weight=1)
        self.tree["columns"] = self.columns
        for column in self.columns:
            self.tree.heading(column, text=column)
            self.tree.column(column, width=125, minwidth=70, stretch=True)
        self.clear_form()
        self.refresh()

    def refresh(self):
        if not self.table_name:
            return
        rows = self.db.connection.execute(
            f"SELECT * FROM {self.table_name} ORDER BY id DESC"
        ).fetchall()
        self.tree.delete(*self.tree.get_children())
        for row in rows:
            self.tree.insert("", "end", iid=str(row["id"]),
                             values=[row[column] for column in self.columns])

    def values(self, for_update=False):
        result = {}
        for column, entry in self.entries.items():
            text = entry.get().strip()
            if text or for_update:
                result[column] = text or None
        return result

    def run_sql(self, sql, values):
        try:
            self.db.connection.execute(sql, values)
            self.db.connection.commit()
            self.refresh()
            self.clear_form()
        except Exception as error:
            self.db.connection.rollback()
            messagebox.showerror("Neizdevās saglabāt", str(error), parent=self)

    def add_row(self):
        if not self.table_name:
            return
        values = self.values()
        if not values:
            messagebox.showinfo("Dati", "Ievadi vismaz vienu lauku.", parent=self)
            return
        names = list(values)
        marks = ",".join("?" for _ in names)
        self.run_sql(f"INSERT INTO {self.table_name} ({','.join(names)}) VALUES ({marks})",
                     tuple(values.values()))

    def update_row(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Izvēlies rindu", "Vispirms izvēlies ierakstu tabulā.", parent=self)
            return
        values = self.values(for_update=True)
        assignments = ",".join(f"{column}=?" for column in values)
        self.run_sql(f"UPDATE {self.table_name} SET {assignments} WHERE id=?",
                     (*values.values(), int(selected[0])))

    def delete_row(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Izvēlies rindu", "Vispirms izvēlies ierakstu tabulā.", parent=self)
            return
        if messagebox.askyesno("Dzēst?", "Vai dzēst izvēlēto ierakstu?", parent=self):
            self.run_sql(f"DELETE FROM {self.table_name} WHERE id=?", (int(selected[0]),))

    def select_row(self, _event=None):
        selected = self.tree.selection()
        if not selected:
            return
        row = self.db.connection.execute(
            f"SELECT * FROM {self.table_name} WHERE id=?", (int(selected[0]),)
        ).fetchone()
        for column, entry in self.entries.items():
            entry.delete(0, "end")
            if row[column] is not None:
                entry.insert(0, str(row[column]))

    def clear_form(self):
        for entry in self.entries.values():
            entry.delete(0, "end")
        self.tree.selection_remove(self.tree.selection())

    def close(self):
        self.db.close()
        self.destroy()
