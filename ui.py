"""Polished desktop interface for the design project tracker."""
import tkinter as tk
from tkinter import messagebox, ttk

from database import Database

TABLES = {
    "clients": "Klienti",
    "projects": "Projekti",
    "deliverables": "Nodevumi",
    "activities": "Darbības",
    "team_members": "Komandas locekļi",
    "time_logs": "Laika ieraksti",
    "palette_colors": "Krāsu paletes",
    "revision_logs": "Labojumu vēsture",
}

EXTRA_SCHEMA = """
CREATE TABLE IF NOT EXISTS deliverables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL, format TEXT, done INTEGER NOT NULL DEFAULT 0
);
"""

COLORS = {
    "sidebar": "#182230",
    "sidebar_muted": "#9AA8B8",
    "sidebar_active": "#26374A",
    "accent": "#6C63FF",
    "accent_hover": "#584FE0",
    "canvas": "#F4F6FA",
    "surface": "#FFFFFF",
    "text": "#202B3C",
    "muted": "#78869A",
    "border": "#E5EAF1",
    "danger": "#D84B55",
    "success": "#16856B",
}


class DesignApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Dizaina projektu pārvaldnieks")
        self.geometry("1360x860")
        self.minsize(1000, 680)
        self.configure(bg=COLORS["canvas"])

        self.db = Database()
        self.db.connection.executescript(EXTRA_SCHEMA)
        self.db.connection.commit()
        self.table_name, self.columns = None, []
        self.entries = {}
        self.visible_tables = list(TABLES)
        self.row_search = tk.StringVar()
        self.table_search = tk.StringVar()
        self.status_text = tk.StringVar(value="Izvēlies tabulu, lai sāktu darbu")

        self._configure_styles()
        self._build_layout()
        self.protocol("WM_DELETE_WINDOW", self.close)

    def _configure_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("App.TFrame", background=COLORS["canvas"])
        style.configure("Card.TFrame", background=COLORS["surface"])
        style.configure("App.TLabel", background=COLORS["canvas"], foreground=COLORS["text"],
                        font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=COLORS["canvas"], foreground=COLORS["muted"],
                        font=("Segoe UI", 9))
        style.configure("CardTitle.TLabel", background=COLORS["surface"], foreground=COLORS["text"],
                        font=("Segoe UI", 11, "bold"))
        style.configure("Field.TLabel", background=COLORS["surface"], foreground=COLORS["muted"],
                        font=("Segoe UI", 9))
        style.configure("TEntry", padding=(9, 8), fieldbackground="#FFFFFF",
                        foreground=COLORS["text"], bordercolor=COLORS["border"],
                        lightcolor=COLORS["border"], darkcolor=COLORS["border"])
        style.map("TEntry", bordercolor=[("focus", COLORS["accent"])])
        style.configure("Primary.TButton", background=COLORS["accent"], foreground="#FFFFFF",
                        padding=(15, 9), borderwidth=0, font=("Segoe UI", 9, "bold"))
        style.map("Primary.TButton", background=[("active", COLORS["accent_hover"])])
        style.configure("Secondary.TButton", background="#FFFFFF", foreground=COLORS["text"],
                        padding=(13, 9), borderwidth=1, relief="solid",
                        font=("Segoe UI", 9, "bold"))
        style.map("Secondary.TButton", background=[("active", "#F1F3F8")])
        style.configure("Danger.TButton", background="#FFF5F5", foreground=COLORS["danger"],
                        padding=(13, 9), borderwidth=1, relief="solid",
                        font=("Segoe UI", 9, "bold"))
        style.map("Danger.TButton", background=[("active", "#FDE8E9")])
        style.configure("Treeview", background="#FFFFFF", foreground=COLORS["text"],
                        fieldbackground="#FFFFFF", rowheight=36, borderwidth=0,
                        font=("Segoe UI", 9))
        style.configure("Treeview.Heading", background="#F8FAFC", foreground=COLORS["muted"],
                        relief="flat", padding=(10, 11), font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", "#EAE9FF")],
                  foreground=[("selected", COLORS["text"])])
        style.configure("Vertical.TScrollbar", background="#E8ECF2", troughcolor="#FFFFFF",
                        borderwidth=0, arrowsize=12)
        style.configure("Horizontal.TScrollbar", background="#E8ECF2", troughcolor="#FFFFFF",
                        borderwidth=0, arrowsize=12)

    def _build_layout(self):
        shell = tk.Frame(self, bg=COLORS["canvas"])
        shell.pack(fill="both", expand=True)

        # Dark navigation rail
        sidebar = tk.Frame(shell, bg=COLORS["sidebar"], width=250)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        brand = tk.Frame(sidebar, bg=COLORS["sidebar"])
        brand.pack(fill="x", padx=22, pady=(25, 28))
        mark = tk.Label(brand, text="D", bg=COLORS["accent"], fg="white",
                        font=("Segoe UI", 14, "bold"), width=2, height=1)
        mark.pack(side="left", padx=(0, 11))
        brand_text = tk.Frame(brand, bg=COLORS["sidebar"])
        brand_text.pack(side="left")
        tk.Label(brand_text, text="STUDIO", bg=COLORS["sidebar"], fg="#FFFFFF",
                 font=("Segoe UI", 10, "bold")).pack(anchor="w")
        tk.Label(brand_text, text="PROJECT SPACE", bg=COLORS["sidebar"],
                 fg=COLORS["sidebar_muted"], font=("Segoe UI", 7, "bold")).pack(anchor="w", pady=(2, 0))

        tk.Label(sidebar, text="DARBA TELPA", bg=COLORS["sidebar"], fg=COLORS["sidebar_muted"],
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=22, pady=(0, 10))
        search_wrap = tk.Frame(sidebar, bg="#223043")
        search_wrap.pack(fill="x", padx=16, pady=(0, 15))
        tk.Label(search_wrap, text="⌕", bg="#223043", fg=COLORS["sidebar_muted"],
                 font=("Segoe UI", 13)).pack(side="left", padx=(10, 4))
        self.table_search_entry = tk.Entry(
            search_wrap, textvariable=self.table_search, bg="#223043", fg="#FFFFFF",
            insertbackground="#FFFFFF", relief="flat", font=("Segoe UI", 9),
        )
        self.table_search_entry.pack(side="left", fill="x", expand=True, ipady=9, padx=(0, 8))
        self.table_search_entry.insert(0, "Meklēt sadaļu")
        self.table_search_entry.bind("<FocusIn>", self._clear_table_placeholder)
        self.table_search_entry.bind("<KeyRelease>", self.filter_table_menu)

        self.table_menu = tk.Listbox(
            sidebar, bg=COLORS["sidebar"], fg="#D8E0E9", selectbackground=COLORS["sidebar_active"],
            selectforeground="#FFFFFF", activestyle="none", relief="flat", borderwidth=0,
            highlightthickness=0, font=("Segoe UI", 10), height=12,
            exportselection=False, selectmode=tk.SINGLE,
        )
        self.table_menu.pack(fill="x", padx=10)
        self._populate_table_menu()
        self.table_menu.bind("<<ListboxSelect>>", self.open_table)
        tk.Frame(sidebar, bg="#2A3747", height=1).pack(fill="x", padx=18, pady=(20, 14))
        tk.Label(sidebar, text="DESIGN PROJECT MANAGER", bg=COLORS["sidebar"],
                 fg="#738196", font=("Segoe UI", 8)).pack(side="bottom", anchor="w", padx=20, pady=18)

        # Main work area
        main = tk.Frame(shell, bg=COLORS["canvas"])
        main.pack(side="left", fill="both", expand=True)
        header = tk.Frame(main, bg=COLORS["canvas"])
        header.pack(fill="x", padx=34, pady=(27, 21))
        header_copy = tk.Frame(header, bg=COLORS["canvas"])
        header_copy.pack(side="left", fill="x", expand=True)
        tk.Label(header_copy, text="Dizaina projektu pārvaldnieks", bg=COLORS["canvas"],
                 fg=COLORS["text"], font=("Segoe UI", 21, "bold")).pack(anchor="w")
        self.breadcrumb = tk.Label(header_copy, text="Darba telpa  /  Pārskats", bg=COLORS["canvas"],
                                   fg=COLORS["muted"], font=("Segoe UI", 9))
        self.breadcrumb.pack(anchor="w", pady=(5, 0))
        db_badge = tk.Frame(header, bg="#E7F5F0", padx=11, pady=8)
        db_badge.pack(side="right", anchor="n", pady=4)
        tk.Label(db_badge, text="●  DATUBĀZE AKTĪVA", bg="#E7F5F0", fg=COLORS["success"],
                 font=("Segoe UI", 8, "bold")).pack()

        content = tk.Frame(main, bg=COLORS["canvas"])
        content.pack(fill="both", expand=True, padx=34, pady=(0, 20))

        # Editor card
        self.form_card = tk.Frame(content, bg=COLORS["surface"], highlightbackground=COLORS["border"],
                                  highlightthickness=1)
        self.form_card.pack(fill="x", pady=(0, 16))
        form_header = tk.Frame(self.form_card, bg=COLORS["surface"])
        form_header.pack(fill="x", padx=20, pady=(16, 11))
        self.title_label = tk.Label(form_header, text="Izvēlies sadaļu", bg=COLORS["surface"],
                                    fg=COLORS["text"], font=("Segoe UI", 12, "bold"))
        self.title_label.pack(side="left")
        self.form_hint = tk.Label(form_header, text="Ieraksta informācija", bg=COLORS["surface"],
                                  fg=COLORS["muted"], font=("Segoe UI", 9))
        self.form_hint.pack(side="right")
        tk.Frame(self.form_card, bg=COLORS["border"], height=1).pack(fill="x")
        self.form = tk.Frame(self.form_card, bg=COLORS["surface"])
        self.form.pack(fill="x", padx=16, pady=(12, 16))

        # Records card
        records_card = tk.Frame(content, bg=COLORS["surface"], highlightbackground=COLORS["border"],
                                highlightthickness=1)
        records_card.pack(fill="both", expand=True)
        records_top = tk.Frame(records_card, bg=COLORS["surface"])
        records_top.pack(fill="x", padx=20, pady=(16, 13))
        records_copy = tk.Frame(records_top, bg=COLORS["surface"])
        records_copy.pack(side="left", fill="x", expand=True)
        tk.Label(records_copy, text="Ieraksti", bg=COLORS["surface"], fg=COLORS["text"],
                 font=("Segoe UI", 12, "bold")).pack(anchor="w")
        self.record_count = tk.Label(records_copy, text="Izvēlies sadaļu, lai skatītu ierakstus",
                                     bg=COLORS["surface"], fg=COLORS["muted"],
                                     font=("Segoe UI", 9))
        self.record_count.pack(anchor="w", pady=(3, 0))
        search_box = tk.Frame(records_top, bg="#F7F8FB", highlightbackground=COLORS["border"],
                              highlightthickness=1)
        search_box.pack(side="right")
        tk.Label(search_box, text="⌕", bg="#F7F8FB", fg=COLORS["muted"],
                 font=("Segoe UI", 13)).pack(side="left", padx=(10, 3))
        self.row_search_entry = tk.Entry(search_box, textvariable=self.row_search, bg="#F7F8FB",
                                         fg=COLORS["text"], insertbackground=COLORS["text"],
                                         relief="flat", font=("Segoe UI", 9), width=23)
        self.row_search_entry.pack(side="left", ipady=9, padx=(0, 10))
        self.row_search_entry.bind("<KeyRelease>", lambda _event: self.refresh())
        tk.Frame(records_card, bg=COLORS["border"], height=1).pack(fill="x")

        table_area = tk.Frame(records_card, bg=COLORS["surface"])
        table_area.pack(fill="both", expand=True, padx=14, pady=14)
        self.tree = ttk.Treeview(table_area, show="headings", selectmode="browse")
        ybar = ttk.Scrollbar(table_area, orient="vertical", command=self.tree.yview)
        xbar = ttk.Scrollbar(records_card, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=ybar.set, xscrollcommand=xbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        ybar.pack(side="right", fill="y")
        xbar.pack(fill="x", padx=14, pady=(0, 13))
        self.tree.tag_configure("odd", background="#F8FAFC")
        self.tree.tag_configure("even", background="#FFFFFF")
        self.tree.bind("<<TreeviewSelect>>", self.select_row)

        # Compact footer/status line
        footer = tk.Frame(main, bg=COLORS["canvas"])
        footer.pack(fill="x", padx=34, pady=(0, 14))
        tk.Label(footer, textvariable=self.status_text, bg=COLORS["canvas"], fg=COLORS["muted"],
                 font=("Segoe UI", 8)).pack(side="left")
        actions = tk.Frame(footer, bg=COLORS["canvas"])
        actions.pack(side="right")
        ttk.Button(actions, text="Notīrīt", style="Secondary.TButton",
                   command=self.clear_form).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Dzēst", style="Danger.TButton",
                   command=self.delete_row).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Saglabāt izmaiņas", style="Secondary.TButton",
                   command=self.update_row).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="＋  Pievienot ierakstu", style="Primary.TButton",
                   command=self.add_row).pack(side="left")

    def _clear_table_placeholder(self, _event=None):
        if self.table_search.get() == "Meklēt sadaļu":
            self.table_search_entry.delete(0, "end")
            self.table_search.set("")

    def _populate_table_menu(self):
        query = self.table_search.get().strip().casefold()
        if query == "Meklēt sadaļu":
            query = ""
        self.visible_tables = [
            name for name, title in TABLES.items()
            if query in title.casefold() or query in name.casefold()
        ]
        self.table_menu.delete(0, "end")
        for name in self.visible_tables:
            self.table_menu.insert("end", f"  {TABLES[name]}")

    def filter_table_menu(self, _event=None):
        self._populate_table_menu()

    def open_table(self, _event=None):
        selected = self.table_menu.curselection()
        if not selected:
            return
        self.table_name = self.visible_tables[selected[0]]
        title = TABLES[self.table_name]
        self.title_label.config(text=title)
        self.breadcrumb.config(text=f"Darba telpa  /  {title}")
        self.form_hint.config(text=f"Rediģē {title.lower()} ierakstu")
        self.status_text.set(f"Atvērta sadaļa: {title}")
        info = self.db.connection.execute(f"PRAGMA table_info({self.table_name})").fetchall()
        self.columns = [row[1] for row in info]
        primary_keys = {row[1] for row in info if row[5]}
        for widget in self.form.winfo_children():
            widget.destroy()
        self.entries.clear()
        editable_columns = [column for column in self.columns if column not in primary_keys]
        for index, column in enumerate(editable_columns):
            field = tk.Frame(self.form, bg=COLORS["surface"])
            field.grid(row=index // 4, column=index % 4, sticky="ew", padx=5, pady=5)
            ttk.Label(field, text=column.replace("_", " ").title(), style="Field.TLabel").pack(anchor="w", pady=(0, 5))
            entry = ttk.Entry(field)
            entry.pack(fill="x")
            self.entries[column] = entry
        for column in range(4):
            self.form.columnconfigure(column, weight=1)
        self.tree["columns"] = self.columns
        for column in self.columns:
            self.tree.heading(column, text=column.replace("_", " ").title())
            self.tree.column(column, width=145, minwidth=85, stretch=True, anchor="w")
        self.row_search.set("")
        self.clear_form()
        self.refresh()

    def refresh(self):
        if not self.table_name:
            return
        rows = self.db.connection.execute(
            f"SELECT * FROM {self.table_name} ORDER BY id DESC"
        ).fetchall()
        query = self.row_search.get().strip().casefold()
        filtered = [row for row in rows if not query or any(
            query in str(row[column] or "").casefold() for column in self.columns
        )]
        self.tree.delete(*self.tree.get_children())
        for index, row in enumerate(filtered):
            self.tree.insert("", "end", iid=str(row["id"]),
                             values=[row[column] for column in self.columns],
                             tags=("even" if index % 2 == 0 else "odd",))
        total = len(rows)
        shown = len(filtered)
        self.record_count.config(text=f"{shown} ieraksti" if shown == total else f"{shown} no {total} ierakstiem")

    def values(self, for_update=False):
        result = {}
        for column, entry in self.entries.items():
            text = entry.get().strip()
            if text or for_update:
                result[column] = text or None
        return result

    def run_sql(self, sql, values, success_message):
        try:
            self.db.connection.execute(sql, values)
            self.db.connection.commit()
            self.refresh()
            self.clear_form()
            self.status_text.set(success_message)
        except Exception as error:
            self.db.connection.rollback()
            messagebox.showerror("Neizdevās saglabāt", str(error), parent=self)
            self.status_text.set("Darbību neizdevās izpildīt")

    def add_row(self):
        if not self.table_name:
            messagebox.showinfo("Izvēlies sadaļu", "Vispirms izvēlies tabulu kreisajā izvēlnē.", parent=self)
            return
        values = self.values()
        if not values:
            messagebox.showinfo("Dati", "Ievadi vismaz vienu lauku.", parent=self)
            return
        names = list(values)
        marks = ",".join("?" for _ in names)
        self.run_sql(f"INSERT INTO {self.table_name} ({','.join(names)}) VALUES ({marks})",
                     tuple(values.values()), "Jauns ieraksts pievienots")

    def update_row(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Izvēlies ierakstu", "Lai saglabātu izmaiņas, vispirms izvēlies ierakstu.", parent=self)
            return
        values = self.values(for_update=True)
        assignments = ",".join(f"{column}=?" for column in values)
        self.run_sql(f"UPDATE {self.table_name} SET {assignments} WHERE id=?",
                     (*values.values(), int(selected[0])), "Izmaiņas saglabātas")

    def delete_row(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Izvēlies ierakstu", "Vispirms izvēlies ierakstu, ko dzēst.", parent=self)
            return
        if messagebox.askyesno("Dzēst ierakstu?", "Šo darbību nevarēs atsaukt. Vai turpināt?", parent=self):
            self.run_sql(f"DELETE FROM {self.table_name} WHERE id=?", (int(selected[0]),), "Ieraksts izdzēsts")

    def select_row(self, _event=None):
        selected = self.tree.selection()
        if not selected or not self.table_name:
            return
        row = self.db.connection.execute(
            f"SELECT * FROM {self.table_name} WHERE id=?", (int(selected[0]),)
        ).fetchone()
        for column, entry in self.entries.items():
            entry.delete(0, "end")
            if row[column] is not None:
                entry.insert(0, str(row[column]))
        self.status_text.set("Ieraksts izvēlēts — veiciet izmaiņas un saglabājiet")

    def clear_form(self):
        for entry in self.entries.values():
            entry.delete(0, "end")
        if hasattr(self, "tree"):
            self.tree.selection_remove(self.tree.selection())

    def close(self):
        self.db.close()
        self.destroy()


if __name__ == "__main__":
    DesignApp().mainloop()
