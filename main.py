import tkinter as tk
from tkinter import ttk, messagebox
import re
from database import Database

db = Database()
STATUSES = ["Jauns", "Procesā", "Pārskatīšanā", "Pabeigts"]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Design Project Tracker")
        self.geometry("980x650")
        self.minsize(900, 580)
        self.configure(bg="#f3f6ff")

        self.style = ttk.Style(self)
        self.style.theme_use("clam")

        self.style.configure("TFrame", background="#f3f6ff")
        self.style.configure("TLabel", background="#f3f6ff", foreground="#243b53", font=("Arial", 10))
        self.style.configure("TEntry", fieldbackground="#ffffff")
        self.style.configure("TCombobox", fieldbackground="#ffffff")
        self.style.configure("Treeview", rowheight=28, background="#ffffff", fieldbackground="#ffffff", foreground="#1f2937")
        self.style.map("Treeview", background=[("selected", "#dfe7ff")], foreground=[("selected", "#111827")])
        self.style.configure("Treeview.Heading", background="#e8ecff", foreground="#1f2937", font=("Arial", 10, "bold"))
        self.style.configure("Accent.TButton", background="#5b6cff", foreground="white", padding=8, font=("Arial", 10, "bold"))
        self.style.map("Accent.TButton", background=[("active", "#4f5ef5")], foreground=[("active", "white")])
        self.style.configure("Secondary.TButton", background="#eef2ff", foreground="#243b53", padding=8, font=("Arial", 10, "bold"))
        self.style.map("Secondary.TButton", background=[("active", "#e2e8ff")], foreground=[("active", "#1f2937")])

        self.header = ttk.Frame(self, padding=(20, 18, 20, 10))
        self.header.pack(fill="x")

        title = ttk.Label(self.header, text="Dizaina projektu pārvaldnieks", font=("Arial", 20, "bold"), foreground="#1e2a78")
        title.pack(anchor="w")

        subtitle = ttk.Label(self.header, text="Pārvaldi klientus, projektus, laiku un krāsas vienuviet", foreground="#51607a", font=("Arial", 10))
        subtitle.pack(anchor="w", pady=(4, 0))

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        self.tab_clients = ttk.Frame(nb, padding=10)
        self.tab_projects = ttk.Frame(nb, padding=10)
        self.tab_time = ttk.Frame(nb, padding=10)
        self.tab_colors = ttk.Frame(nb, padding=10)

        for t, n in [
            (self.tab_clients, "Klienti"),
            (self.tab_projects, "Projekti"),
            (self.tab_time, "Laiks"),
            (self.tab_colors, "Krāsu palete"),
        ]:
            nb.add(t, text=n)

        self.build_clients()
        self.build_projects()
        self.build_time()
        self.build_colors()
        self.refresh()

    def tree(self, parent, cols, widths):
        t = ttk.Treeview(parent, columns=cols, show="headings", height=10)
        for c, w in zip(cols, widths):
            t.heading(c, text=c)
            t.column(c, width=w)
        t.pack(fill="both", expand=True, padx=6, pady=(0, 10))
        return t

    def form(self, parent, labels):
        f = ttk.Frame(parent, padding=(0, 8, 0, 6))
        f.pack(fill="x", padx=4)
        entries = []
        for l in labels:
            col = ttk.Frame(f)
            col.pack(side="left", padx=(0, 8), fill="y")

            ttk.Label(col, text=l).pack(anchor="w")
            e = ttk.Entry(col, width=16)
            e.pack(pady=(4, 0))
            entries.append(e)
        return f, entries

    def combo_value(self, combo, rows):
        i = combo.current()
        return rows[i]["id"] if i >= 0 and rows and i < len(rows) else None

    def build_clients(self):
        self.t_clients = self.tree(self.tab_clients, ("Vārds", "E-pasts", "Likme €/h"), (260, 320, 120))

        f, self.c_in = self.form(self.tab_clients, ["Vārds", "E-pasts", "Likme"])
        ttk.Button(f, text="Pievienot", style="Accent.TButton", command=self.add_client).pack(side="left", padx=(0, 8))
        ttk.Button(f, text="Dzēst", style="Secondary.TButton", command=self.del_client).pack(side="left")

    def add_client(self):
        n, e, r = [x.get().strip() for x in self.c_in]
        try:
            db.add_client(n, e, float(r or 25))
        except ValueError:
            return messagebox.showerror("Kļūda", "Likmei jābūt skaitlim")
        if n:
            self.refresh()

    def del_client(self):
        s = self.t_clients.selection()
        if s and messagebox.askyesno("Dzēst", "Dzēst klientu un visus viņa projektus?"):
            db.delete_client(int(s[0]))
            self.refresh()

    def build_projects(self):
        self.t_projects = self.tree(self.tab_projects,
                                   ("Projekts", "Klients", "Veids", "Statuss", "Termiņš", "Stundas"),
                                   (220, 150, 100, 120, 110, 90))

        top = ttk.Frame(self.tab_projects)
        top.pack(fill="x", padx=6, pady=(0, 8))

        self.p_client = ttk.Combobox(top, state="readonly", width=18, font=("Arial", 10))
        self.p_client.pack(side="left", padx=(0, 8))

        self.p_in = []

        for l in ["Nosaukums", "Veids", "Termiņš GGGG-MM-DD", "Plān. h"]:
            box = ttk.Frame(top)
            box.pack(side="left", padx=(0, 8))
            ttk.Label(box, text=l).pack(anchor="w")
            e = ttk.Entry(box, width=12)
            e.pack(pady=(4, 0))
            self.p_in.append(e)

        ttk.Button(top, text="Pievienot", style="Accent.TButton", command=self.add_project).pack(side="left", padx=(0, 8))

        actions = ttk.Frame(self.tab_projects)
        actions.pack(fill="x", padx=6, pady=(4, 8))

        self.p_status = ttk.Combobox(actions, values=STATUSES, state="readonly", width=16)
        self.p_status.pack(side="left", padx=(0, 8))

        ttk.Button(actions, text="Mainīt statusu", style="Secondary.TButton", command=self.change_status).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Dzēst projektu", style="Secondary.TButton", command=self.del_project).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Kopsavilkums", style="Secondary.TButton", command=self.show_summary).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="+ Labojumu kārta", style="Secondary.TButton", command=self.add_revision).pack(side="left", padx=(0, 8))

    def add_project(self):
        cid = self.combo_value(self.p_client, self.clients)
        t, ty, dl, h = [x.get().strip() for x in self.p_in]
        if not (cid and t):
            return
        try:
            db.add_project(cid, t, ty, dl, float(h or 20))
        except ValueError:
            return messagebox.showerror("Kļūda", "Stundām jābūt skaitlim")
        self.refresh()

    def sel_project(self):
        s = self.t_projects.selection()
        return int(s[0]) if s else None

    def change_status(self):
        pid = self.sel_project()
        if pid and self.p_status.get():
            db.set_status(pid, self.p_status.get())
            self.refresh()

    def del_project(self):
        pid = self.sel_project()
        if pid and messagebox.askyesno("Dzēst", "Dzēst projektu?"):
            db.delete_project(pid)
            self.refresh()

    def add_revision(self):
        pid = self.sel_project()
        if pid:
            db.add_revision(pid)
            n = len(db.get_revisions(pid))
            messagebox.showinfo("Labojumi", f"Reģistrēta {n}. labojumu kārta")

    def show_summary(self):
        pid = self.sel_project()
        if pid:
            s = db.project_summary(pid)
            messagebox.showinfo(s["title"],
                                f"Izmantots: {s['spent']:.1f} / {s['budget']:.1f} h\n"
                                f"Atlicis: {s['left']:.1f} h\nNopelnīts: {s['earned']:.2f} €")

    def build_time(self):
        self.t_time = self.tree(self.tab_time, ("Datums", "Projekts", "Darbība", "Stundas", "Piezīme"),
                                (100, 220, 180, 80, 260))

        form = ttk.Frame(self.tab_time)
        form.pack(fill="x", padx=6, pady=(0, 8))

        self.tm_project = ttk.Combobox(form, state="readonly", width=18)
        self.tm_project.pack(side="left", padx=(0, 8))

        self.tm_activity = ttk.Combobox(form, state="readonly", width=18)
        self.tm_activity.pack(side="left", padx=(0, 8))

        box_hours = ttk.Frame(form)
        box_hours.pack(side="left", padx=(0, 8))
        ttk.Label(box_hours, text="Stundas").pack(anchor="w")
        self.tm_hours = ttk.Entry(box_hours, width=8)
        self.tm_hours.pack(pady=(4, 0))

        box_note = ttk.Frame(form)
        box_note.pack(side="left", padx=(0, 8))
        ttk.Label(box_note, text="Piezīme").pack(anchor="w")
        self.tm_note = ttk.Entry(box_note, width=22)
        self.tm_note.pack(pady=(4, 0))

        ttk.Button(form, text="Pievienot", style="Accent.TButton", command=self.add_time).pack(side="left", padx=(0, 8))

    def add_time(self):
        pid = self.combo_value(self.tm_project, self.projects)
        aid = self.combo_value(self.tm_activity, self.activities)
        try:
            h = float(self.tm_hours.get())
        except ValueError:
            return messagebox.showerror("Kļūda", "Ievadi stundas kā skaitli")
        if pid and aid:
            db.add_time(pid, aid, h, self.tm_note.get())
            self.refresh()

    def build_colors(self):
        top = ttk.Frame(self.tab_colors)
        top.pack(fill="x", padx=6, pady=(0, 8))

        self.col_project = ttk.Combobox(top, state="readonly", width=24)
        self.col_project.pack(side="left", padx=(0, 8))
        self.col_project.bind("<<ComboboxSelected>>", lambda e: self.draw_palette())

        box_name = ttk.Frame(top)
        box_name.pack(side="left", padx=(0, 8))
        ttk.Label(box_name, text="Nosaukums").pack(anchor="w")
        self.col_name = ttk.Entry(box_name, width=14)
        self.col_name.pack(pady=(4, 0))

        box_hex = ttk.Frame(top)
        box_hex.pack(side="left", padx=(0, 8))
        ttk.Label(box_hex, text="HEX").pack(anchor="w")
        self.col_hex = ttk.Entry(box_hex, width=10)
        self.col_hex.pack(pady=(4, 0))

        ttk.Button(top, text="Pievienot krāsu", style="Accent.TButton", command=self.add_color).pack(side="left", padx=(0, 8))

        self.canvas = tk.Canvas(self.tab_colors, height=260, bg="#f9fbff", highlightthickness=0, borderwidth=0)
        self.canvas.pack(fill="both", expand=True, padx=6, pady=(4, 6))

    def add_color(self):
        pid = self.combo_value(self.col_project, self.projects)
        hx = self.col_hex.get().strip()
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", hx):
            return messagebox.showerror("Kļūda", "HEX formāts: #RRGGBB")
        if pid:
            db.add_color(pid, self.col_name.get().strip() or hx, hx)
            self.draw_palette()

    def draw_palette(self):
        self.canvas.delete("all")
        pid = self.combo_value(self.col_project, self.projects)
        if not pid:
            return

        colors = db.get_colors(pid)
        for i, c in enumerate(colors):
            x = 10 + i * 120
            self.canvas.create_rectangle(x, 10, x + 100, 170, fill=c["hex"], outline="#dfe7ff", width=2)
            self.canvas.create_text(x + 50, 190, text=c["name"], fill="#1f2937", font=("Arial", 10, "bold"))
            self.canvas.create_text(x + 50, 210, text=c["hex"].upper(), fill="#667085", font=("Arial", 9))

    def refresh(self):
        self.clients = db.get_clients()
        self.projects = db.get_projects()
        self.activities = db.get_activities()

        for t in (self.t_clients, self.t_projects, self.t_time):
            t.delete(*t.get_children())

        for c in self.clients:
            self.t_clients.insert("", "end", iid=c["id"], values=(c["name"], c["email"], c["hourly_rate"]))

        for p in self.projects:
            self.t_projects.insert("", "end", iid=p["id"],
                                   values=(p["title"], p["client_name"], p["type"], p["status"],
                                           p["deadline"], p["budget_hours"]))

        for t in db.get_time_logs():
            self.t_time.insert("", "end", values=(t["work_date"], t["title"], t["activity"],
                                                   t["hours"], t["note"]))

        self.p_client["values"] = [c["name"] for c in self.clients]
        names = [p["title"] for p in self.projects]

        for cb in (self.tm_project, self.col_project):
            cb["values"] = names

        self.tm_activity["values"] = [a["name"] for a in self.activities]


if __name__ == "__main__":
    App().mainloop()
