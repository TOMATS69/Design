import tkinter as tk
from tkinter import messagebox, ttk

from database import Database


class BaseTab(ttk.Frame):
    def __init__(self, parent, app, title):
        super().__init__(parent)
        self.app = app
        self.db = app.db
        self.title = title

        self.pack(fill="both", expand=True, padx=10, pady=10)
        self.search_var = tk.StringVar()

        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 8))

        ttk.Label(top, text="Meklēt:").pack(side="left")
        ttk.Entry(top, textvariable=self.search_var, width=28).pack(side="left", padx=(8, 0))
        self.search_var.trace_add("write", lambda *_: self.refresh())

        self.form = ttk.Frame(self)
        self.form.pack(fill="x", pady=(0, 8))
        self.columns = ()
        self.table = None

    def set_table(self, columns, widths):
        self.columns = columns
        self.table = ttk.Treeview(self, columns=columns, show="headings", height=12)
        for column, width in zip(columns, widths):
            self.table.heading(column, text=column)
            self.table.column(column, width=width, anchor="w")
        self.table.pack(fill="both", expand=True)

    def refresh(self):
        raise NotImplementedError


class ClientsTab(BaseTab):
    def __init__(self, parent, app):
        super().__init__(parent, app, "Klienti")
        self.name_var = tk.StringVar()
        self.email_var = tk.StringVar()
        self.rate_var = tk.StringVar(value="25")

        ttk.Label(self.form, text="Vārds").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(self.form, textvariable=self.name_var, width=24).grid(row=0, column=1, padx=(0, 12), pady=4)

        ttk.Label(self.form, text="E-pasts").grid(row=0, column=2, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(self.form, textvariable=self.email_var, width=28).grid(row=0, column=3, padx=(0, 12), pady=4)

        ttk.Label(self.form, text="Likme €/h").grid(row=0, column=4, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(self.form, textvariable=self.rate_var, width=10).grid(row=0, column=5, pady=4)

        buttons = ttk.Frame(self.form)
        buttons.grid(row=1, column=0, columnspan=6, sticky="w", pady=(8, 0))
        ttk.Button(buttons, text="Pievienot", command=self.add_client).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Saglabāt", command=self.save_client).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Dzēst", command=self.delete_client).pack(side="left")

        self.set_table(("Vārds", "E-pasts", "Likme €/h"), (200, 260, 100))
        self.refresh()

    def add_client(self):
        try:
            self.db.add_client(self.name_var.get(), self.email_var.get(), self.rate_var.get())
            self.clear_form()
            self.refresh()
        except ValueError as error:
            messagebox.showerror("Kļūda", str(error))

    def save_client(self):
        selected = self.get_selected()
        if not selected:
            messagebox.showinfo("Izvēle", "Vispirms izvēlies klientu.")
            return
        try:
            self.db.update_client(selected["id"], self.name_var.get(), self.email_var.get(), self.rate_var.get())
            self.refresh()
        except ValueError as error:
            messagebox.showerror("Kļūda", str(error))

    def delete_client(self):
        selected = self.get_selected()
        if not selected:
            messagebox.showinfo("Izvēle", "Vispirms izvēlies klientu.")
            return
        if messagebox.askyesno("Dzēst", "Dzēst izvēlēto klientu?"):
            self.db.delete_client(selected["id"])
            self.clear_form()
            self.refresh()

    def clear_form(self):
        self.name_var.set("")
        self.email_var.set("")
        self.rate_var.set("25")

    def get_selected(self):
        selection = self.table.selection()
        if not selection:
            return None
        item_id = int(selection[0])
        for client in self.db.list_clients():
            if client["id"] == item_id:
                return client
        return None

    def refresh(self):
        self.table.delete(*self.table.get_children())
        for client in self.db.list_clients(self.search_var.get()):
            self.table.insert(
                "",
                "end",
                iid=str(client["id"]),
                values=(client["name"], client["email"], f"{client['hourly_rate']:.2f}"),
            )
        self.table.bind("<<TreeviewSelect>>", self.on_select)

    def on_select(self, *_):
        selected = self.get_selected()
        if selected:
            self.name_var.set(selected["name"])
            self.email_var.set(selected["email"])
            self.rate_var.set(str(selected["hourly_rate"]))


class ProjectsTab(BaseTab):
    def __init__(self, parent, app):
        super().__init__(parent, app, "Projekti")
        self.clients = []
        self.client_var = tk.StringVar()
        self.title_var = tk.StringVar()
        self.type_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Jauns")
        self.deadline_var = tk.StringVar()
        self.hours_var = tk.StringVar(value="20")

        ttk.Label(self.form, text="Klients").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        self.client_combo = ttk.Combobox(self.form, textvariable=self.client_var, state="readonly", width=22)
        self.client_combo.grid(row=0, column=1, padx=(0, 12), pady=4)

        ttk.Label(self.form, text="Nosaukums").grid(row=0, column=2, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(self.form, textvariable=self.title_var, width=26).grid(row=0, column=3, padx=(0, 12), pady=4)

        ttk.Label(self.form, text="Veids").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(self.form, textvariable=self.type_var, width=22).grid(row=1, column=1, padx=(0, 12), pady=4)

        ttk.Label(self.form, text="Statuss").grid(row=1, column=2, sticky="w", padx=(0, 8), pady=4)
        status_box = ttk.Combobox(self.form, textvariable=self.status_var, state="readonly", values=self.db.get_statuses(), width=18)
        status_box.grid(row=1, column=3, padx=(0, 12), pady=4)

        ttk.Label(self.form, text="Termiņš").grid(row=1, column=4, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(self.form, textvariable=self.deadline_var, width=12).grid(row=1, column=5, pady=4)

        ttk.Label(self.form, text="Plānotās h").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(self.form, textvariable=self.hours_var, width=12).grid(row=2, column=1, pady=4)

        buttons = ttk.Frame(self.form)
        buttons.grid(row=3, column=0, columnspan=6, sticky="w", pady=(12, 0))
        ttk.Button(buttons, text="Pievienot", command=self.add_project).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Saglabāt", command=self.save_project).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Dzēst", command=self.delete_project).pack(side="left")

        self.set_table(("Projekts", "Klients", "Veids", "Statuss", "Termiņš", "Plānotās h", "Izmantotas h"), (200, 150, 120, 110, 100, 90, 90))
        self.refresh()

    def clear_form(self):
        self.title_var.set("")
        self.type_var.set("")
        self.status_var.set("Jauns")
        self.deadline_var.set("")
        self.hours_var.set("20")

    def get_selected(self):
        selection = self.table.selection()
        if not selection:
            return None
        item_id = int(selection[0])
        for project in self.db.list_projects():
            if project["id"] == item_id:
                return project
        return None

    def add_project(self):
        try:
            client_name = self.client_var.get()
            client = next((c for c in self.db.list_clients() if c["name"] == client_name), None)
            if not client:
                raise ValueError("Izvēlies klientu.")
            self.db.add_project(client["id"], self.title_var.get(), self.type_var.get(), self.status_var.get(), self.deadline_var.get(), self.hours_var.get())
            self.clear_form()
            self.refresh()
        except ValueError as error:
            messagebox.showerror("Kļūda", str(error))

    def save_project(self):
        selected = self.get_selected()
        if not selected:
            messagebox.showinfo("Izvēle", "Vispirms izvēlies projektu.")
            return
        try:
            client_name = self.client_var.get()
            client = next((c for c in self.db.list_clients() if c["name"] == client_name), None)
            if not client:
                raise ValueError("Izvēlies klientu.")
            self.db.update_project(selected["id"], client["id"], self.title_var.get(), self.type_var.get(), self.status_var.get(), self.deadline_var.get(), self.hours_var.get())
            self.refresh()
        except ValueError as error:
            messagebox.showerror("Kļūda", str(error))

    def delete_project(self):
        selected = self.get_selected()
        if not selected:
            messagebox.showinfo("Izvēle", "Vispirms izvēlies projektu.")
            return
        if messagebox.askyesno("Dzēst", "Dzēst izvēlēto projektu?"):
            self.db.delete_project(selected["id"])
            self.clear_form()
            self.refresh()

    def refresh(self):
        self.clients = self.db.list_clients()
        names = [client["name"] for client in self.clients]
        self.client_combo["values"] = names
        self.table.delete(*self.table.get_children())
        for project in self.db.list_projects(self.search_var.get()):
            self.table.insert(
                "",
                "end",
                iid=str(project["id"]),
                values=(project["title"], project["client_name"], project["type"], project["status"], project["deadline"], project["budget_hours"], project["spent"]),
            )
        self.table.bind("<<TreeviewSelect>>", self.on_select)

    def on_select(self, *_):
        selected = self.get_selected()
        if not selected:
            return
        self.client_var.set(selected["client_name"])
        self.title_var.set(selected["title"])
        self.type_var.set(selected["type"])
        self.status_var.set(selected["status"])
        self.deadline_var.set(selected["deadline"])
        self.hours_var.set(str(selected["budget_hours"]))


class TimeTab(BaseTab):
    def __init__(self, parent, app):
        super().__init__(parent, app, "Laika uzskaite")
        self.projects = []
        self.activities = []

        self.project_var = tk.StringVar()
        self.activity_var = tk.StringVar()
        self.date_var = tk.StringVar()
        self.hours_var = tk.StringVar(value="1")
        self.note_var = tk.StringVar()

        ttk.Label(self.form, text="Projekts").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        self.project_combo = ttk.Combobox(self.form, textvariable=self.project_var, state="readonly", width=24)
        self.project_combo.grid(row=0, column=1, padx=(0, 12), pady=4)

        ttk.Label(self.form, text="Darbība").grid(row=0, column=2, sticky="w", padx=(0, 8), pady=4)
        self.activity_combo = ttk.Combobox(self.form, textvariable=self.activity_var, state="readonly", width=18)
        self.activity_combo.grid(row=0, column=3, padx=(0, 12), pady=4)

        ttk.Label(self.form, text="Datums").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(self.form, textvariable=self.date_var, width=12).grid(row=1, column=1, padx=(0, 12), pady=4)

        ttk.Label(self.form, text="Stundas").grid(row=1, column=2, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(self.form, textvariable=self.hours_var, width=10).grid(row=1, column=3, padx=(0, 12), pady=4)

        ttk.Label(self.form, text="Piezīme").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(self.form, textvariable=self.note_var, width=44).grid(row=2, column=1, columnspan=3, sticky="w", pady=4)

        buttons = ttk.Frame(self.form)
        buttons.grid(row=3, column=0, columnspan=4, sticky="w", pady=(12, 0))
        ttk.Button(buttons, text="Pievienot", command=self.add_entry).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Dzēst", command=self.delete_entry).pack(side="left")

        self.set_table(("Datums", "Projekts", "Darbība", "Stundas", "Piezīme"), (100, 180, 150, 80, 260))
        self.refresh()

    def refresh(self):
        self.projects = self.db.list_projects()
        self.activities = self.db.get_activities()
        self.project_combo["values"] = [p["title"] for p in self.projects]
        self.activity_combo["values"] = [a["name"] for a in self.activities]

        self.table.delete(*self.table.get_children())
        for item in self.db.list_time_entries(self.search_var.get()):
            self.table.insert(
                "",
                "end",
                iid=str(item["id"]),
                values=(item["work_date"], item["project_title"], item["activity_name"], item["hours"], item["note"]),
            )
        self.table.bind("<<TreeviewSelect>>", self.on_select)

    def add_entry(self):
        try:
            project_name = self.project_var.get()
            activity_name = self.activity_var.get()
            project = next((p for p in self.projects if p["title"] == project_name), None)
            activity = next((a for a in self.activities if a["name"] == activity_name), None)
            if not project or not activity:
                raise ValueError("Priekš izvēles jāizvēlas projekts un darbība.")
            self.db.add_time_entry(project["id"], activity["id"], self.date_var.get(), self.hours_var.get(), self.note_var.get())
            self.clear_form()
            self.refresh()
        except ValueError as error:
            messagebox.showerror("Kļūda", str(error))

    def delete_entry(self):
        selection = self.table.selection()
        if not selection:
            messagebox.showinfo("Izvēle", "Vispirms izvēlies laika ierakstu.")
            return
        if messagebox.askyesno("Dzēst", "Dzēst izvēlēto laika ierakstu?"):
            self.db.delete_time_entry(int(selection[0]))
            self.refresh()

    def on_select(self, *_):
        selection = self.table.selection()
        if not selection:
            return
        item_id = int(selection[0])
        for item in self.db.list_time_entries():
            if item["id"] == item_id:
                self.project_var.set(item["project_title"])
                self.activity_var.set(item["activity_name"])
                self.date_var.set(item["work_date"])
                self.hours_var.set(str(item["hours"]))
                self.note_var.set(item["note"])
                return

    def clear_form(self):
        self.project_var.set("")
        self.activity_var.set("")
        self.date_var.set("")
        self.hours_var.set("1")
        self.note_var.set("")


class ColorsTab(BaseTab):
    def __init__(self, parent, app):
        super().__init__(parent, app, "Krāsas")
        self.projects = []
        self.project_var = tk.StringVar()
        self.name_var = tk.StringVar()
        self.hex_var = tk.StringVar()

        ttk.Label(self.form, text="Projekts").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        self.project_combo = ttk.Combobox(self.form, textvariable=self.project_var, state="readonly", width=24)
        self.project_combo.grid(row=0, column=1, padx=(0, 12), pady=4)

        ttk.Label(self.form, text="Krāsas nosaukums").grid(row=0, column=2, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(self.form, textvariable=self.name_var, width=20).grid(row=0, column=3, pady=4)

        ttk.Label(self.form, text="HEX").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(self.form, textvariable=self.hex_var, width=12).grid(row=1, column=1, padx=(0, 12), pady=4)

        buttons = ttk.Frame(self.form)
        buttons.grid(row=2, column=0, columnspan=4, sticky="w", pady=(12, 0))
        ttk.Button(buttons, text="Pievienot", command=self.add_color).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Dzēst", command=self.delete_color).pack(side="left")

        self.set_table(("Projekts", "Nosaukums", "HEX"), (220, 200, 120))
        self.refresh()

    def refresh(self):
        self.projects = self.db.list_projects()
        self.project_combo["values"] = [p["title"] for p in self.projects]

        self.table.delete(*self.table.get_children())
        for item in self.db.list_colors(self.search_var.get()):
            self.table.insert(
                "",
                "end",
                iid=str(item["id"]),
                values=(item["project_title"], item["name"], item["hex"]),
            )
        self.table.bind("<<TreeviewSelect>>", self.on_select)

    def add_color(self):
        try:
            project_name = self.project_var.get()
            project = next((p for p in self.projects if p["title"] == project_name), None)
            if not project:
                raise ValueError("Izvēlies projektu.")
            self.db.add_color(project["id"], self.name_var.get(), self.hex_var.get())
            self.clear_form()
            self.refresh()
        except ValueError as error:
            messagebox.showerror("Kļūda", str(error))

    def delete_color(self):
        selection = self.table.selection()
        if not selection:
            messagebox.showinfo("Izvēle", "Vispirms izvēlies krāsu.")
            return
        if messagebox.askyesno("Dzēst", "Dzēst izvēlēto krāsu?"):
            self.db.delete_color(int(selection[0]))
            self.refresh()

    def on_select(self, *_):
        selection = self.table.selection()
        if not selection:
            return
        item_id = int(selection[0])
        for item in self.db.list_colors():
            if item["id"] == item_id:
                self.project_var.set(item["project_title"])
                self.name_var.set(item["name"])
                self.hex_var.set(item["hex"])
                return

    def clear_form(self):
        self.project_var.set("")
        self.name_var.set("")
        self.hex_var.set("")


class DesignApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.title("Dizaina projektu pārvaldnieks")
        self.geometry("1100x700")
        self.minsize(900, 600)
        self.configure(bg="#eef3f9")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=12, pady=12)

        self.clients_tab = ClientsTab(notebook, self)
        self.projects_tab = ProjectsTab(notebook, self)
        self.time_tab = TimeTab(notebook, self)
        self.colors_tab = ColorsTab(notebook, self)

        notebook.add(self.clients_tab, text="Klienti")
        notebook.add(self.projects_tab, text="Projekti")
        notebook.add(self.time_tab, text="Laika uzskaite")
        notebook.add(self.colors_tab, text="Krāsas")

        self.protocol("WM_DELETE_WINDOW", self.close_app)

    def close_app(self):
        self.db.close()
        self.destroy()


if __name__ == "__main__":
    app = DesignApp()
    app.mainloop()
