"""Tkinter interface. Database queries and data validation live in database.py."""
import tkinter as tk
from tkinter import messagebox, ttk

from database import Database, STATUSES


class BaseTab(ttk.Frame):
    """Shared layout for a form above a searchable table."""

    def __init__(self, parent, app, title, columns, widths):
        super().__init__(parent, padding=16)
        self.app = app
        self.db = app.db
        self.records = {}
        self.column_names = columns

        ttk.Label(self, text=title, style="Section.TLabel").pack(anchor="w", pady=(0, 10))
        self.form = ttk.LabelFrame(self, text="Dati", padding=12)
        self.form.pack(fill="x", pady=(0, 12))
        self.inputs = {}
        self.buttons = ttk.Frame(self.form)
        self.buttons.pack(fill="x", pady=(10, 0))
        self.make_button("Pievienot", self.add)
        self.make_button("Saglabāt", self.save)
        self.make_button("Dzēst", self.delete)
        self.make_button("Notīrīt", self.clear)

        search_bar = ttk.Frame(self)
        search_bar.pack(fill="x", pady=(0, 6))
        ttk.Label(search_bar, text="Meklēt:").pack(side="left")
        self.search = tk.StringVar()
        ttk.Entry(search_bar, textvariable=self.search, width=28).pack(side="left", padx=8)

        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True)
        self.table = ttk.Treeview(table_frame, columns=columns, show="headings", height=12)
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=scrollbar.set)
        for column, width in zip(columns, widths):
            self.table.heading(column, text=column)
            self.table.column(column, width=width, minwidth=60, anchor="w")
        self.table.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.table.bind("<<TreeviewSelect>>", self.select_row)
        self.search.trace_add("write", lambda *_: self.refresh())

    def make_button(self, text, command):
        ttk.Button(self.buttons, text=text, command=command).pack(side="left", padx=(0, 6))

    def add_field(self, key, label, row, column, width=20, choices=None):
        field = ttk.Frame(self.form)
        field.pack(side="left", fill="x", expand=True, padx=5, anchor="n")
        ttk.Label(field, text=label).pack(anchor="w", pady=(0, 4))
        if choices is None:
            widget = ttk.Entry(field, width=width)
        else:
            widget = ttk.Combobox(field, width=width, state="readonly", values=choices)
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

    def selected_id(self):
        selection = self.table.selection()
        return int(selection[0]) if selection else None

    def selected_record(self):
        record_id = self.selected_id()
        return self.records.get(record_id)

    def select_row(self, _event=None):
        record = self.selected_record()
        if record:
            self.fill_form(record)

    def clear(self):
        for widget in self.inputs.values():
            if isinstance(widget, ttk.Combobox):
                widget.set("")
            else:
                widget.delete(0, "end")

    def run_action(self, action):
        try:
            action()
        except (ValueError, TypeError) as error:
            messagebox.showerror("Pārbaudi ievadi", str(error), parent=self)
            return
        self.refresh()
        self.app.refresh_dropdowns()

    def add(self):
        self.run_action(self.add_record)

    def save(self):
        record = self.selected_record()
        if record is None:
            messagebox.showinfo("Izvēlies ierakstu", "Vispirms izvēlies rindu tabulā.", parent=self)
            return
        self.run_action(lambda: self.update_record(record))

    def delete(self):
        record = self.selected_record()
        if record is None:
            messagebox.showinfo("Izvēlies ierakstu", "Vispirms izvēlies rindu tabulā.", parent=self)
            return
        if messagebox.askyesno("Dzēst ierakstu?", "Vai tiešām vēlies dzēst izvēlēto ierakstu?", parent=self):
            self.run_action(lambda: self.delete_record(record))
            self.clear()

    def refresh(self):
        self.records = {row["id"]: row for row in self.get_rows()}
        self.table.delete(*self.table.get_children())
        for record_id, record in self.records.items():
            self.table.insert("", "end", iid=str(record_id), values=self.row_values(record))


class ClientsTab(BaseTab):
    def __init__(self, parent, app):
        super().__init__(parent, app, "Klienti", ("Vārds", "E-pasts", "Likme €/h"), (240, 300, 120))
        self.add_field("name", "Vārds *", 0, 0)
        self.add_field("email", "E-pasts", 0, 1)
        rate = self.add_field("rate", "Likme €/h", 0, 2)
        rate.insert(0, "25")
        self.refresh()

    def get_rows(self):
        return self.db.list_clients(self.search.get())

    def row_values(self, row):
        return row["name"], row["email"] or "", f"{row['hourly_rate']:.2f}"

    def fill_form(self, row):
        self.set_value("name", row["name"])
        self.set_value("email", row["email"])
        self.set_value("rate", row["hourly_rate"])

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
        self.client_combo = self.add_field("client", "Klients *", 0, 0, choices=[])
        self.add_field("title", "Projekta nosaukums *", 0, 1, 24)
        self.add_field("type", "Veids", 0, 2)
        self.add_field("status", "Statuss", 0, 3, choices=STATUSES)
        self.add_field("deadline", "Termiņš (GGGG-MM-DD)", 0, 4)
        hours = self.add_field("hours", "Plānotās stundas", 0, 5)
        hours.insert(0, "20")
        self.refresh()

    def get_rows(self):
        self.clients = self.db.list_clients()
        self.client_combo["values"] = [self.client_label(row) for row in self.clients]
        return self.db.list_projects(self.search.get())

    def client_label(self, client):
        return f"{client['name']} [#{client['id']}]"

    def row_values(self, row):
        return (row["title"], row["client_name"], row["type"] or "", row["status"],
                row["deadline"] or "", row["budget_hours"], f"{row['spent']:.1f}")

    def fill_form(self, row):
        client = next((item for item in self.clients if item["id"] == row["client_id"]), None)
        if client:
            self.set_value("client", self.client_label(client))
        for key, value in (("title", row["title"]), ("type", row["type"]),
                           ("status", row["status"]), ("deadline", row["deadline"]),
                           ("hours", row["budget_hours"])):
            self.set_value(key, value)

    def form_values(self):
        client_label = self.value("client")
        client = next((item for item in self.clients if self.client_label(item) == client_label), None)
        if client is None:
            raise ValueError("Izvēlies klientu.")
        return (client["id"], self.value("title"), self.value("type"), self.value("status") or "Jauns",
                self.value("deadline"), self.value("hours") or 20)

    def add_record(self):
        self.db.add_project(*self.form_values())
        self.clear()

    def update_record(self, row):
        self.db.update_project(row["id"], *self.form_values())

    def delete_record(self, row):
        self.db.delete_project(row["id"])


class TimeTab(BaseTab):
    def __init__(self, parent, app):
        super().__init__(parent, app, "Laika uzskaite",
                         ("Datums", "Projekts", "Darbība", "Stundas", "Piezīme"),
                         (120, 210, 170, 90, 300))
        self.projects = []
        self.activities = []
        self.project_combo = self.add_field("project", "Projekts *", 0, 0, choices=[])
        self.activity_combo = self.add_field("activity", "Darbība *", 0, 1, choices=[])
        self.add_field("date", "Datums (GGGG-MM-DD; tukšs = šodien)", 0, 2)
        hours = self.add_field("hours", "Stundas *", 0, 3)
        hours.insert(0, "1")
        self.add_field("note", "Piezīme", 0, 4)
        self.refresh()

    def get_rows(self):
        self.projects = self.db.list_projects()
        self.activities = self.db.get_activities()
        self.project_combo["values"] = [self.project_label(row) for row in self.projects]
        self.activity_combo["values"] = [row["name"] for row in self.activities]
        return self.db.list_time_entries(self.search.get())

    def project_label(self, project):
        return f"{project['title']} [#{project['id']}]"

    def row_values(self, row):
        return row["work_date"], row["project_title"], row["activity_name"], row["hours"], row["note"] or ""

    def fill_form(self, row):
        project = next((item for item in self.projects if item["id"] == row["project_id"]), None)
        if project:
            self.set_value("project", self.project_label(project))
        self.set_value("activity", row["activity_name"])
        self.set_value("date", row["work_date"])
        self.set_value("hours", row["hours"])
        self.set_value("note", row["note"])

    def add_record(self):
        project = next((item for item in self.projects if self.project_label(item) == self.value("project")), None)
        activity = next((item for item in self.activities if item["name"] == self.value("activity")), None)
        if project is None or activity is None:
            raise ValueError("Izvēlies projektu un darbību.")
        self.db.add_time_entry(project["id"], activity["id"], self.value("date"),
                               self.value("hours"), self.value("note"))
        self.clear()

    def update_record(self, row):
        raise ValueError("Laika ierakstu labošana vēl nav pieejama. Dzēs ierakstu un pievieno to no jauna.")

    def delete_record(self, row):
        self.db.delete_time_entry(row["id"])


class ColorsTab(BaseTab):
    def __init__(self, parent, app):
        super().__init__(parent, app, "Krāsu paletes", ("Projekts", "Nosaukums", "HEX"), (260, 240, 140))
        self.projects = []
        self.project_combo = self.add_field("project", "Projekts *", 0, 0, choices=[])
        self.add_field("name", "Krāsas nosaukums *", 0, 1)
        self.add_field("hex", "HEX krāsa (#RRGGBB) *", 0, 2)
        self.refresh()

    def get_rows(self):
        self.projects = self.db.list_projects()
        self.project_combo["values"] = [self.project_label(row) for row in self.projects]
        return self.db.list_colors(self.search.get())

    def project_label(self, project):
        return f"{project['title']} [#{project['id']}]"

    def row_values(self, row):
        return row["project_title"], row["name"], row["hex"]

    def fill_form(self, row):
        project = next((item for item in self.projects if item["id"] == row["project_id"]), None)
        if project:
            self.set_value("project", self.project_label(project))
        self.set_value("name", row["name"])
        self.set_value("hex", row["hex"])

    def add_record(self):
        project = next((item for item in self.projects if self.project_label(item) == self.value("project")), None)
        if project is None:
            raise ValueError("Izvēlies projektu.")
        self.db.add_color(project["id"], self.value("name"), self.value("hex"))
        self.clear()

    def update_record(self, row):
        raise ValueError("Krāsas labošana vēl nav pieejama. Dzēs krāsu un pievieno to no jauna.")

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

        ttk.Label(self, text="Dizaina projektu pārvaldnieks",
                  font=("TkDefaultFont", 20, "bold"), background="#f4f6fa",
                  foreground="#172033").pack(anchor="w", padx=22, pady=(18, 8))
        self.db = Database()
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        self.tabs = [ClientsTab(self.notebook, self), ProjectsTab(self.notebook, self),
                     TimeTab(self.notebook, self), ColorsTab(self.notebook, self)]
        for tab, title in zip(self.tabs, ("Klienti", "Projekti", "Laiks", "Krāsas")):
            self.notebook.add(tab, text=title)
        self.protocol("WM_DELETE_WINDOW", self.close)

    def refresh_dropdowns(self):
        for tab in self.tabs:
            if isinstance(tab, (ProjectsTab, TimeTab, ColorsTab)):
                tab.refresh()

    def close(self):
        self.db.close()
        self.destroy()
