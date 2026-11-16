"""Tkinter interface. Database queries and data validation live in database.py."""
import tkinter as tk
from tkinter import messagebox, ttk

from database import Database, STATUSES
from extra_tabs import ExtraTableTab


class BaseTab(ttk.Frame):
    """Shared layout for a form above a searchable table."""

    def __init__(self, parent, app, title, columns, widths):
        super().__init__(parent, padding=16)
        self.app, self.db, self.records = app, app.db, {}
        ttk.Label(self, text=title, style="Section.TLabel").pack(anchor="w", pady=(0, 10))
        self.form = ttk.LabelFrame(self, text="Dati", padding=12)
        self.form.pack(fill="x", pady=(0, 12))
        self.inputs = {}
        buttons = ttk.Frame(self.form)
        buttons.pack(fill="x", pady=(10, 0))
        for label, command in (("Pievienot", self.add), ("Saglabāt", self.save),
                               ("Dzēst", self.delete), ("Notīrīt", self.clear)):
            ttk.Button(buttons, text=label, command=command).pack(side="left", padx=(0, 6))
        search_bar = ttk.Frame(self)
        search_bar.pack(fill="x", pady=(0, 6))
        ttk.Label(search_bar, text="Meklēt:").pack(side="left")
        self.search = tk.StringVar()
        ttk.Entry(search_bar, textvariable=self.search, width=28).pack(side="left", padx=8)
        frame = ttk.Frame(self)
        frame.pack(fill="both", expand=True)
        self.table = ttk.Treeview(frame, columns=columns, show="headings", height=12)
        scroll = ttk.Scrollbar(frame, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=scroll.set)
        for column, width in zip(columns, widths):
            self.table.heading(column, text=column)
            self.table.column(column, width=width, minwidth=60, anchor="w")
        self.table.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.table.bind("<<TreeviewSelect>>", self.select_row)
        self.search.trace_add("write", lambda *_: self.refresh())

    def add_field(self, key, label, row, column, width=20, choices=None):
        field = ttk.Frame(self.form)
        field.pack(side="left", fill="x", expand=True, padx=5, anchor="n")
        ttk.Label(field, text=label).pack(anchor="w", pady=(0, 4))
        widget = ttk.Entry(field, width=width) if choices is None else ttk.Combobox(
            field, width=width, state="readonly", values=choices)
        widget.pack(fill="x")
        self.inputs[key] = widget
        return widget

    def value(self, key):
        return self.inputs[key].get().strip()

    def set_value(self, key, value):
        widget = self.inputs[key]
        if isinstance(widget, ttk.Combobox):
            widget.set("" if value is None else str(value))
        else:
            widget.delete(0, "end")
            widget.insert(0, "" if value is None else str(value))

    def selected_record(self):
        selected = self.table.selection()
        return self.records.get(int(selected[0])) if selected else None

    def select_row(self, _event=None):
        record = self.selected_record()
        if record:
            self.fill_form(record)

    def clear(self):
        for widget in self.inputs.values():
            widget.set("") if isinstance(widget, ttk.Combobox) else widget.delete(0, "end")

    def run_action(self, action):
        try:
            action()
            self.refresh()
            self.app.refresh_dropdowns()
        except (ValueError, TypeError) as error:
            messagebox.showerror("Pārbaudi ievadi", str(error), parent=self)

    def add(self):
        self.run_action(self.add_record)

    def save(self):
        row = self.selected_record()
        if row is None:
            messagebox.showinfo("Izvēlies ierakstu", "Vispirms izvēlies rindu tabulā.", parent=self)
        else:
            self.run_action(lambda: self.update_record(row))

    def delete(self):
        row = self.selected_record()
        if row and messagebox.askyesno("Dzēst ierakstu?", "Vai tiešām dzēst izvēlēto rindu?", parent=self):
            self.run_action(lambda: self.delete_record(row))
            self.clear()

    def refresh(self):
        self.records = {row["id"]: row for row in self.get_rows()}
        self.table.delete(*self.table.get_children())
        for record_id, row in self.records.items():
            self.table.insert("", "end", iid=str(record_id), values=self.row_values(row))


class ClientsTab(BaseTab):
    def __init__(self, parent, app):
        super().__init__(parent, app, "Klienti", ("Vārds", "E-pasts", "Likme €/h"), (240, 300, 120))
        for key, label in (("name", "Vārds *"), ("email", "E-pasts"), ("rate", "Likme €/h")):
            self.add_field(key, label, 0, 0)
        self.set_value("rate", "25")
        self.refresh()

    def get_rows(self):
        return self.db.list_clients(self.search.get())

    def row_values(self, row):
        return row["name"], row["email"] or "", f"{row['hourly_rate']:.2f}"

    def fill_form(self, row):
        for key, value in (("name", row["name"]), ("email", row["email"]), ("rate", row["hourly_rate"])):
            self.set_value(key, value)

    def add_record(self):
        self.db.add_client(self.value("name"), self.value("email"), self.value("rate"))
        self.clear()

    def update_record(self, row):
        self.db.update_client(row["id"], self.value("name"), self.value("email"), self.value("rate"))

    def delete_record(self, row):
        self.db.delete_client(row["id"])


class ProjectsTab(BaseTab):
    def __init__(self, parent, app):
        super().__init__(parent, app, "Projekti",
                         ("Projekts", "Klients", "Veids", "Statuss", "Termiņš", "Plān. h", "Izmantots h"),
                         (190, 150, 100, 120, 110, 80, 90))
        self.clients = []
        self.add_field("client", "Klients *", 0, 0, choices=[])
        for key, label, choices in (("title", "Projekta nosaukums *", None), ("type", "Veids", None),
                                    ("status", "Statuss", STATUSES), ("deadline", "Termiņš (GGGG-MM-DD)", None),
                                    ("hours", "Plānotās stundas", None)):
            self.add_field(key, label, 0, 0, choices=choices)
        self.set_value("hours", "20")
        self.refresh()

    def get_rows(self):
        self.clients = self.db.list_clients()
        self.inputs["client"]["values"] = [self.client_label(c) for c in self.clients]
        return self.db.list_projects(self.search.get())

    @staticmethod
    def client_label(client):
        return f"{client['name']} [#{client['id']}]"

    def row_values(self, row):
        return (row["title"], row["client_name"], row["type"] or "", row["status"],
                row["deadline"] or "", row["budget_hours"], f"{row['spent']:.1f}")

    def fill_form(self, row):
        client = next((c for c in self.clients if c["id"] == row["client_id"]), None)
        if client:
            self.set_value("client", self.client_label(client))
        for key, value in (("title", row["title"]), ("type", row["type"]), ("status", row["status"]),
                           ("deadline", row["deadline"]), ("hours", row["budget_hours"])):
            self.set_value(key, value)

    def form_values(self):
        label = self.value("client")
        client = next((c for c in self.clients if self.client_label(c) == label), None)
        if not client:
            raise ValueError("Izvēlies klientu.")
        return client["id"], self.value("title"), self.value("type"), self.value("status") or "Jauns", \
               self.value("deadline"), self.value("hours") or 20

    def add_record(self):
        self.db.add_project(*self.form_values())
        self.clear()

    def update_record(self, row):
        self.db.update_project(row["id"], *self.form_values())

    def delete_record(self, row):
        self.db.delete_project(row["id"])


class TimeTab(BaseTab):
    def __init__(self, parent, app):
        super().__init__(parent, app, "Laika uzskaite", ("Datums", "Projekts", "Darbība", "Stundas", "Piezīme"),
                         (120, 210, 170, 90, 300))
        self.projects, self.activities = [], []
        for key, label, choices in (("project", "Projekts *", []), ("activity", "Darbība *", []),
                                    ("date", "Datums (GGGG-MM-DD; tukšs = šodien)", None),
                                    ("hours", "Stundas *", None), ("note", "Piezīme", None)):
            self.add_field(key, label, 0, 0, choices=choices)
        self.set_value("hours", "1")
        self.refresh()

    def get_rows(self):
        self.projects, self.activities = self.db.list_projects(), self.db.get_activities()
        self.inputs["project"]["values"] = [self.project_label(p) for p in self.projects]
        self.inputs["activity"]["values"] = [a["name"] for a in self.activities]
        return self.db.list_time_entries(self.search.get())

    @staticmethod
    def project_label(project):
        return f"{project['title']} [#{project['id']}]"

    def row_values(self, row):
        return row["work_date"], row["project_title"], row["activity_name"], row["hours"], row["note"] or ""

    def fill_form(self, row):
        project = next((p for p in self.projects if p["id"] == row["project_id"]), None)
        if project:
            self.set_value("project", self.project_label(project))
        for key, value in (("activity", row["activity_name"]), ("date", row["work_date"]),
                           ("hours", row["hours"]), ("note", row["note"])):
            self.set_value(key, value)

    def add_record(self):
        project = next((p for p in self.projects if self.project_label(p) == self.value("project")), None)
        activity = next((a for a in self.activities if a["name"] == self.value("activity")), None)
        if not project or not activity:
            raise ValueError("Izvēlies projektu un darbību.")
        self.db.add_time_entry(project["id"], activity["id"], self.value("date"),
                               self.value("hours"), self.value("note"))
        self.clear()

    def update_record(self, row):
        raise ValueError("Laika ierakstu labošana nav pieejama. Dzēs ierakstu un pievieno to no jauna.")

    def delete_record(self, row):
        self.db.delete_time_entry(row["id"])


class ColorsTab(BaseTab):
    def __init__(self, parent, app):
        super().__init__(parent, app, "Krāsu paletes", ("Projekts", "Nosaukums", "HEX"), (260, 240, 140))
        self.projects = []
        for key, label in (("project", "Projekts *"), ("name", "Krāsas nosaukums *"),
                           ("hex", "HEX krāsa (#RRGGBB) *")):
            self.add_field(key, label, 0, 0, choices=[] if key == "project" else None)
        self.refresh()

    def get_rows(self):
        self.projects = self.db.list_projects()
        self.inputs["project"]["values"] = [self.project_label(p) for p in self.projects]
        return self.db.list_colors(self.search.get())

    @staticmethod
    def project_label(project):
        return f"{project['title']} [#{project['id']}]"

    def row_values(self, row):
        return row["project_title"], row["name"], row["hex"]

    def fill_form(self, row):
        project = next((p for p in self.projects if p["id"] == row["project_id"]), None)
        if project:
            self.set_value("project", self.project_label(project))
        self.set_value("name", row["name"])
        self.set_value("hex", row["hex"])

    def add_record(self):
        project = next((p for p in self.projects if self.project_label(p) == self.value("project")), None)
        if not project:
            raise ValueError("Izvēlies projektu.")
        self.db.add_color(project["id"], self.value("name"), self.value("hex"))
        self.clear()

    def update_record(self, row):
        raise ValueError("Krāsas labošana nav pieejama. Dzēs krāsu un pievieno to no jauna.")

    def delete_record(self, row):
        self.db.delete_color(row["id"])


class DesignApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Dizaina projektu pārvaldnieks")
        self.geometry("1100x720")
        self.minsize(900, 600)
        self.configure(background="#f4f6fa")
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("TNotebook", background="#f4f6fa", borderwidth=0)
        style.configure("TNotebook.Tab", padding=(15, 9))
        style.configure("Treeview", rowheight=29)
        style.configure("Section.TLabel", font=("TkDefaultFont", 14, "bold"))
        ttk.Label(self, text="Dizaina projektu pārvaldnieks", font=("TkDefaultFont", 20, "bold"),
                  background="#f4f6fa", foreground="#172033").pack(anchor="w", padx=22, pady=(18, 8))
        self.db = Database()
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        self.tabs = [ClientsTab(notebook, self), ProjectsTab(notebook, self), TimeTab(notebook, self),
                     ColorsTab(notebook, self)]
        for tab, title in zip(self.tabs, ("Klienti", "Projekti", "Laiks", "Krāsas")):
            notebook.add(tab, text=title)
        for table in ("team_members", "invoices", "payments", "expenses"):
            tab = ExtraTableTab(notebook, self, table)
            self.tabs.append(tab)
            notebook.add(tab, text=tab.config["name"])
        self.protocol("WM_DELETE_WINDOW", self.close)

    def refresh_dropdowns(self):
        for tab in self.tabs:
            if isinstance(tab, (ProjectsTab, TimeTab, ColorsTab)):
                tab.refresh()

    def close(self):
        self.db.close()
        self.destroy()
