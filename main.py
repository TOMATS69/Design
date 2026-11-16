import re
import tkinter as tk
from tkinter import messagebox, ttk

from database import Database


# These are the project statuses shown in the project tab.
PROJECT_STATUSES = ["Jauns", "Procesā", "Pārskatīšanā", "Pabeigts"]


class DesignTrackerApp(tk.Tk):
    """The main window for the design project tracker."""

    def __init__(self):
        super().__init__()

        self.db = Database()
        self.title("Dizaina projektu pārvaldnieks")
        self.geometry("1100x720")
        self.minsize(900, 600)
        self.configure(background="#f4f6fa")

        self.set_styles()
        self.build_window()
        self.refresh_data()

    def set_styles(self):
        """Set a consistent, clean look using Tkinter's built-in theme system."""
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")

        style.configure("App.TFrame", background="#f4f6fa")
        style.configure("Card.TFrame", background="#ffffff")
        style.configure(
            "Title.TLabel", background="#f4f6fa", foreground="#172033",
            font=("TkDefaultFont", 20, "bold")
        )
        style.configure(
            "Subtitle.TLabel", background="#f4f6fa", foreground="#64748b",
            font=("TkDefaultFont", 10)
        )
        style.configure(
            "Section.TLabel", background="#ffffff", foreground="#172033",
            font=("TkDefaultFont", 11, "bold")
        )
        style.configure("TNotebook", background="#f4f6fa", borderwidth=0)
        style.configure("TNotebook.Tab", padding=(16, 10), font=("TkDefaultFont", 10))
        style.map("TNotebook.Tab", background=[("selected", "#ffffff")])
        style.configure("Treeview", rowheight=30, font=("TkDefaultFont", 10))
        style.configure(
            "Treeview.Heading", font=("TkDefaultFont", 10, "bold"),
            background="#e8edf5", foreground="#25324a", padding=(8, 8)
        )
        style.map("Treeview", background=[("selected", "#dbeafe")],
                  foreground=[("selected", "#172033")])
        style.configure("Accent.TButton", padding=(12, 8), font=("TkDefaultFont", 10, "bold"))
        style.configure("TButton", padding=(10, 7), font=("TkDefaultFont", 10))
        style.configure("TEntry", padding=7)
        style.configure("TCombobox", padding=6)

    def build_window(self):
        """Create the heading and the four main sections of the app."""
        page = ttk.Frame(self, style="App.TFrame", padding=(24, 20))
        page.pack(fill="both", expand=True)

        ttk.Label(page, text="Dizaina projektu pārvaldnieks", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            page,
            text="Pārvaldi klientus, projektus, darba laiku un projektu krāsu paletes.",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(4, 18))

        self.tabs = ttk.Notebook(page)
        self.tabs.pack(fill="both", expand=True)

        self.clients_tab = ttk.Frame(self.tabs, padding=16)
        self.projects_tab = ttk.Frame(self.tabs, padding=16)
        self.time_tab = ttk.Frame(self.tabs, padding=16)
        self.colors_tab = ttk.Frame(self.tabs, padding=16)

        self.tabs.add(self.clients_tab, text="Klienti")
        self.tabs.add(self.projects_tab, text="Projekti")
        self.tabs.add(self.time_tab, text="Laika uzskaite")
        self.tabs.add(self.colors_tab, text="Krāsu paletes")

        self.build_clients_tab()
        self.build_projects_tab()
        self.build_time_tab()
        self.build_colors_tab()

    def create_table(self, parent, columns):
        """Create a table with headings and a vertical scrollbar.

        Each column is (internal_name, visible_heading, width).
        """
        table_frame = ttk.Frame(parent)
        table_frame.pack(fill="both", expand=True, pady=(0, 14))

        column_names = [column[0] for column in columns]
        table = ttk.Treeview(
            table_frame, columns=column_names, show="headings", selectmode="browse"
        )
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=table.yview)
        table.configure(yscrollcommand=scrollbar.set)

        for name, heading, width in columns:
            table.heading(name, text=heading)
            table.column(name, width=width, minwidth=60, anchor="w")

        table.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        table.tag_configure("even", background="#ffffff")
        table.tag_configure("odd", background="#f8fafc")
        return table

    def create_field(self, parent, label, row, column, width=20):
        """Add a labeled text box to a form and return the text box."""
        field = ttk.Frame(parent)
        field.grid(row=row, column=column, sticky="ew", padx=6, pady=5)
        ttk.Label(field, text=label).pack(anchor="w", pady=(0, 4))
        entry = ttk.Entry(field, width=width)
        entry.pack(fill="x")
        return entry

    def create_combo_field(self, parent, label, row, column, width=22):
        """Add a labeled dropdown to a form and return the dropdown."""
        field = ttk.Frame(parent)
        field.grid(row=row, column=column, sticky="ew", padx=6, pady=5)
        ttk.Label(field, text=label).pack(anchor="w", pady=(0, 4))
        combo = ttk.Combobox(field, state="readonly", width=width)
        combo.pack(fill="x")
        return combo

    def selected_id(self, combo, rows):
        """Return the database ID for the currently selected dropdown item."""
        selected_index = combo.current()
        if selected_index == -1 or selected_index >= len(rows):
            return None
        return rows[selected_index]["id"]

    def build_clients_tab(self):
        self.client_table = self.create_table(
            self.clients_tab,
            [("name", "Vārds", 250), ("email", "E-pasts", 300),
             ("rate", "Likme €/h", 120)],
        )

        form = ttk.LabelFrame(self.clients_tab, text="Pievienot klientu", padding=12)
        form.pack(fill="x")
        form.columnconfigure((0, 1, 2), weight=1)
        self.client_name = self.create_field(form, "Vārds *", 0, 0)
        self.client_email = self.create_field(form, "E-pasts", 0, 1)
        self.client_rate = self.create_field(form, "Stundas likme (€)", 0, 2)
        self.client_rate.insert(0, "25")

        buttons = ttk.Frame(form)
        buttons.grid(row=1, column=0, columnspan=3, sticky="e", padx=6, pady=(8, 0))
        ttk.Button(buttons, text="Pievienot klientu", style="Accent.TButton",
                   command=self.add_client).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Dzēst izvēlēto", command=self.delete_client).pack(side="left")

    def add_client(self):
        name = self.client_name.get().strip()
        email = self.client_email.get().strip()
        rate_text = self.client_rate.get().strip()

        if not name:
            messagebox.showwarning("Trūkst vārda", "Lūdzu, ievadi klienta vārdu.")
            self.client_name.focus_set()
            return

        try:
            hourly_rate = float(rate_text)
            if hourly_rate <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Nederīga likme", "Stundas likmei jābūt pozitīvam skaitlim.")
            self.client_rate.focus_set()
            return

        self.db.add_client(name, email, hourly_rate)
        self.client_name.delete(0, "end")
        self.client_email.delete(0, "end")
        self.client_rate.delete(0, "end")
        self.client_rate.insert(0, "25")
        self.refresh_data()

    def delete_client(self):
        selection = self.client_table.selection()
        if not selection:
            messagebox.showinfo("Izvēlies klientu", "Vispirms izvēlies klientu tabulā.")
            return

        confirmed = messagebox.askyesno(
            "Dzēst klientu?",
            "Klienta dzēšana izdzēsīs arī visus ar viņu saistītos projektus. Turpināt?",
        )
        if confirmed:
            self.db.delete_client(int(selection[0]))
            self.refresh_data()

    def build_projects_tab(self):
        self.project_table = self.create_table(
            self.projects_tab,
            [("title", "Projekts", 210), ("client", "Klients", 160),
             ("type", "Veids", 120), ("status", "Statuss", 140),
             ("deadline", "Termiņš", 130), ("hours", "Plānotās h", 110)],
        )

        form = ttk.LabelFrame(self.projects_tab, text="Pievienot projektu", padding=12)
        form.pack(fill="x")
        form.columnconfigure((0, 1, 2, 3, 4), weight=1)
        self.project_client = self.create_combo_field(form, "Klients *", 0, 0)
        self.project_title = self.create_field(form, "Projekta nosaukums *", 0, 1)
        self.project_type = self.create_field(form, "Veids", 0, 2)
        self.project_deadline = self.create_field(form, "Termiņš (GGGG-MM-DD)", 0, 3)
        self.project_hours = self.create_field(form, "Plānotās stundas", 0, 4)
        self.project_hours.insert(0, "20")

        buttons = ttk.Frame(form)
        buttons.grid(row=1, column=0, columnspan=5, sticky="ew", padx=6, pady=(8, 0))
        ttk.Button(buttons, text="Pievienot projektu", style="Accent.TButton",
                   command=self.add_project).pack(side="left")

        actions = ttk.LabelFrame(self.projects_tab, text="Izvēlētā projekta darbības", padding=10)
        actions.pack(fill="x", pady=(12, 0))
        self.project_status = ttk.Combobox(
            actions, values=PROJECT_STATUSES, state="readonly", width=20
        )
        self.project_status.pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Mainīt statusu", command=self.change_project_status).pack(side="left")
        ttk.Button(actions, text="Kopsavilkums", command=self.show_project_summary).pack(side="left", padx=8)
        ttk.Button(actions, text="Pievienot labojumu", command=self.add_revision).pack(side="left")
        ttk.Button(actions, text="Dzēst projektu", command=self.delete_project).pack(side="right")

    def add_project(self):
        client_id = self.selected_id(self.project_client, self.clients)
        title = self.project_title.get().strip()
        project_type = self.project_type.get().strip()
        deadline = self.project_deadline.get().strip()
        hours_text = self.project_hours.get().strip()

        if client_id is None:
            messagebox.showwarning("Izvēlies klientu", "Lai pievienotu projektu, vispirms pievieno un izvēlies klientu.")
            return
        if not title:
            messagebox.showwarning("Trūkst nosaukuma", "Lūdzu, ievadi projekta nosaukumu.")
            self.project_title.focus_set()
            return

        try:
            planned_hours = float(hours_text)
            if planned_hours <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Nederīgs stundu skaits", "Plānotajām stundām jābūt pozitīvam skaitlim.")
            self.project_hours.focus_set()
            return

        self.db.add_project(client_id, title, project_type, deadline, planned_hours)
        for entry in (self.project_title, self.project_type, self.project_deadline):
            entry.delete(0, "end")
        self.project_hours.delete(0, "end")
        self.project_hours.insert(0, "20")
        self.refresh_data()

    def selected_project_id(self):
        selection = self.project_table.selection()
        return int(selection[0]) if selection else None

    def change_project_status(self):
        project_id = self.selected_project_id()
        status = self.project_status.get()
        if project_id is None or not status:
            messagebox.showinfo("Izvēlies projektu", "Izvēlies projektu un jauno statusu.")
            return
        self.db.set_status(project_id, status)
        self.refresh_data()

    def delete_project(self):
        project_id = self.selected_project_id()
        if project_id is None:
            messagebox.showinfo("Izvēlies projektu", "Vispirms izvēlies projektu tabulā.")
            return
        if messagebox.askyesno("Dzēst projektu?", "Vai tiešām dzēst izvēlēto projektu?"):
            self.db.delete_project(project_id)
            self.refresh_data()

    def add_revision(self):
        project_id = self.selected_project_id()
        if project_id is None:
            messagebox.showinfo("Izvēlies projektu", "Vispirms izvēlies projektu tabulā.")
            return
        self.db.add_revision(project_id)
        revision_count = len(self.db.get_revisions(project_id))
        messagebox.showinfo("Labojums reģistrēts", f"Pievienota {revision_count}. labojumu kārta.")

    def show_project_summary(self):
        project_id = self.selected_project_id()
        if project_id is None:
            messagebox.showinfo("Izvēlies projektu", "Vispirms izvēlies projektu tabulā.")
            return

        summary = self.db.project_summary(project_id)
        if summary is None:
            messagebox.showerror("Kļūda", "Neizdevās atrast izvēlēto projektu.")
            return

        messagebox.showinfo(
            summary["title"],
            f"Izmantots: {summary['spent']:.1f} / {summary['budget']:.1f} h\n"
            f"Atlicis: {summary['left']:.1f} h\n"
            f"Nopelnīts: {summary['earned']:.2f} €",
        )

    def build_time_tab(self):
        self.time_table = self.create_table(
            self.time_tab,
            [("date", "Datums", 120), ("project", "Projekts", 210),
             ("activity", "Darbība", 190), ("hours", "Stundas", 90),
             ("note", "Piezīme", 300)],
        )

        form = ttk.LabelFrame(self.time_tab, text="Reģistrēt nostrādāto laiku", padding=12)
        form.pack(fill="x")
        form.columnconfigure((0, 1, 2, 3), weight=1)
        self.time_project = self.create_combo_field(form, "Projekts *", 0, 0)
        self.time_activity = self.create_combo_field(form, "Darbība *", 0, 1)
        self.time_hours = self.create_field(form, "Stundas *", 0, 2)
        self.time_note = self.create_field(form, "Piezīme", 0, 3)

        ttk.Button(form, text="Pievienot ierakstu", style="Accent.TButton",
                   command=self.add_time_entry).grid(
                       row=1, column=0, columnspan=4, sticky="e", padx=6, pady=(8, 0)
                   )

    def add_time_entry(self):
        project_id = self.selected_id(self.time_project, self.projects)
        activity_id = self.selected_id(self.time_activity, self.activities)
        if project_id is None or activity_id is None:
            messagebox.showwarning("Trūkst izvēles", "Izvēlies projektu un darba darbību.")
            return

        try:
            hours = float(self.time_hours.get().strip())
            if hours <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Nederīgs stundu skaits", "Stundām jābūt pozitīvam skaitlim.")
            self.time_hours.focus_set()
            return

        self.db.add_time(project_id, activity_id, hours, self.time_note.get().strip())
        self.time_hours.delete(0, "end")
        self.time_note.delete(0, "end")
        self.refresh_data()

    def build_colors_tab(self):
        form = ttk.LabelFrame(self.colors_tab, text="Projekta krāsu palete", padding=12)
        form.pack(fill="x", pady=(0, 14))
        form.columnconfigure((0, 1, 2), weight=1)
        self.color_project = self.create_combo_field(form, "Projekts *", 0, 0)
        self.color_project.bind("<<ComboboxSelected>>", lambda event: self.draw_palette())
        self.color_name = self.create_field(form, "Krāsas nosaukums", 0, 1)
        self.color_hex = self.create_field(form, "HEX krāsa (piem., #4F46E5) *", 0, 2)
        ttk.Button(form, text="Pievienot krāsu", style="Accent.TButton",
                   command=self.add_color).grid(
                       row=1, column=0, columnspan=3, sticky="e", padx=6, pady=(8, 0)
                   )

        palette_frame = ttk.LabelFrame(self.colors_tab, text="Priekšskatījums", padding=10)
        palette_frame.pack(fill="both", expand=True)
        self.palette_canvas = tk.Canvas(
            palette_frame, background="#ffffff", highlightthickness=0, height=300
        )
        horizontal_scrollbar = ttk.Scrollbar(
            palette_frame, orient="horizontal", command=self.palette_canvas.xview
        )
        self.palette_canvas.configure(xscrollcommand=horizontal_scrollbar.set)
        self.palette_canvas.pack(fill="both", expand=True)
        horizontal_scrollbar.pack(fill="x")
        self.palette_canvas.bind("<Configure>", lambda event: self.draw_palette())

    def add_color(self):
        project_id = self.selected_id(self.color_project, self.projects)
        color_hex = self.color_hex.get().strip()
        if project_id is None:
            messagebox.showwarning("Izvēlies projektu", "Izvēlies projektu, kam pievienot krāsu.")
            return
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", color_hex):
            messagebox.showerror("Nederīga HEX krāsa", "Izmanto formātu #RRGGBB, piemēram, #4F46E5.")
            self.color_hex.focus_set()
            return

        color_name = self.color_name.get().strip() or color_hex.upper()
        self.db.add_color(project_id, color_name, color_hex.upper())
        self.color_name.delete(0, "end")
        self.color_hex.delete(0, "end")
        self.draw_palette()

    def draw_palette(self):
        """Draw one labeled color card for every saved project color."""
        self.palette_canvas.delete("all")
        project_id = self.selected_id(self.color_project, self.projects)
        if project_id is None:
            self.palette_canvas.configure(scrollregion=(0, 0, 0, 0))
            return

        colors = self.db.get_colors(project_id)
        card_width = 140
        card_gap = 14
        card_height = 190

        for index, color in enumerate(colors):
            left = 12 + index * (card_width + card_gap)
            self.palette_canvas.create_rectangle(
                left, 12, left + card_width, 122,
                fill=color["hex"], outline="#d9e0ea", width=1,
            )
            self.palette_canvas.create_text(
                left + card_width / 2, 145, text=color["name"],
                fill="#172033", font=("TkDefaultFont", 10, "bold"),
                width=card_width - 8,
            )
            self.palette_canvas.create_text(
                left + card_width / 2, 168, text=color["hex"].upper(),
                fill="#64748b", font=("TkDefaultFont", 9),
            )

        content_width = max(self.palette_canvas.winfo_width(), 24 + len(colors) * (card_width + card_gap))
        self.palette_canvas.configure(scrollregion=(0, 0, content_width, card_height))

    def refresh_data(self):
        """Reload data from SQLite and update every table and dropdown."""
        self.clients = self.db.get_clients()
        self.projects = self.db.get_projects()
        self.activities = self.db.get_activities()

        for table in (self.client_table, self.project_table, self.time_table):
            table.delete(*table.get_children())

        for index, client in enumerate(self.clients):
            self.client_table.insert(
                "", "end", iid=client["id"],
                values=(client["name"], client["email"], f"{client['hourly_rate']:.2f}"),
                tags=("even" if index % 2 == 0 else "odd",),
            )

        for index, project in enumerate(self.projects):
            self.project_table.insert(
                "", "end", iid=project["id"],
                values=(project["title"], project["client_name"], project["type"],
                        project["status"], project["deadline"], project["budget_hours"]),
                tags=("even" if index % 2 == 0 else "odd",),
            )

        for index, entry in enumerate(self.db.get_time_logs()):
            self.time_table.insert(
                "", "end",
                values=(entry["work_date"], entry["title"], entry["activity"],
                        entry["hours"], entry["note"]),
                tags=("even" if index % 2 == 0 else "odd",),
            )

        self.project_client["values"] = [client["name"] for client in self.clients]
        project_names = [project["title"] for project in self.projects]
        self.time_project["values"] = project_names
        self.color_project["values"] = project_names
        self.time_activity["values"] = [activity["name"] for activity in self.activities]

        # Select the first available option so new entries are quick to add.
        for combo, rows in (
            (self.project_client, self.clients),
            (self.time_project, self.projects),
            (self.color_project, self.projects),
            (self.time_activity, self.activities),
        ):
            if rows and combo.current() == -1:
                combo.current(0)

        self.draw_palette()


if __name__ == "__main__":
    app = DesignTrackerApp()
    app.mainloop()
