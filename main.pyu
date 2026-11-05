import tkinter as tk
from tkinter import ttk, messagebox
import re
from database import Database

db = Database()
STATUSES = ["Jauns", "Procesā", "Pārskatīšanā", "Pabeigts"]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Dizaina projektu pārvaldnieks")
        self.geometry("860x560")
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=8, pady=8)
        self.tab_clients = ttk.Frame(nb)
        self.tab_projects = ttk.Frame(nb)
        self.tab_time = ttk.Frame(nb)
        self.tab_colors = ttk.Frame(nb)
        for t, n in [(self.tab_clients, "Klienti"), (self.tab_projects, "Projekti"),
                     (self.tab_time, "Laiks"), (self.tab_colors, "Krāsu palete")]:
            nb.add(t, text=n)
        self.build_clients()
        self.build_projects()
        self.build_time()
        self.build_colors()
        self.refresh()

    # ---------- palīgfunkcijas ----------
    def tree(self, parent, cols, widths):
        t = ttk.Treeview(parent, columns=cols, show="headings", height=10)
        for c, w in zip(cols, widths):
            t.heading(c, text=c)
            t.column(c, width=w)
        t.pack(fill="both", expand=True, padx=6, pady=6)
        return t

    def form(self, parent, labels):
        f = ttk.Frame(parent)
        f.pack(fill="x", padx=6)
        entries = []
        for l in labels:
            ttk.Label(f, text=l).pack(side="left")
            e = ttk.Entry(f, width=14)
            e.pack(side="left", padx=4)
            entries.append(e)
        return f, entries

    def combo_value(self, combo, rows):
        i = combo.current()
        return rows[i]["id"] if i >= 0 else None

    # ---------- klienti ----------
    def build_clients(self):
        self.t_clients = self.tree(self.tab_clients, ("Vārds", "E-pasts", "Likme €/h"), (250, 300, 100))
        f, self.c_in = self.form(self.tab_clients, ["Vārds", "E-pasts", "Likme"])
        ttk.Button(f, text="Pievienot", command=self.add_client).pack(side="left", padx=4)
        ttk.Button(f, text="Dzēst", command=self.del_client).pack(side="left")

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

    # ---------- projekti ----------
    def build_projects(self):
        self.t_projects = self.tree(self.tab_projects,
                                    ("Projekts", "Klients", "Veids", "Statuss", "Termiņš", "Stundas"),
                                    (200, 150, 100, 110, 100, 80))
        f = ttk.Frame(self.tab_projects)
        f.pack(fill="x", padx=6)
        self.p_client = ttk.Combobox(f, state="readonly", width=16)
        self.p_client.pack(side="left", padx=4)
        self.p_in = []
        for l in ["Nosaukums", "Veids", "Termiņš GGGG-MM-DD", "Plān. h"]:
            ttk.Label(f, text=l).pack(side="left")
            e = ttk.Entry(f, width=10)
            e.pack(side="left", padx=3)
            self.p_in.append(e)
        ttk.Button(f, text="Pievienot", command=self.add_project).pack(side="left", padx=4)
        f2 = ttk.Frame(self.tab_projects)
        f2.pack(fill="x", padx=6, pady=6)
        self.p_status = ttk.Combobox(f2, values=STATUSES, state="readonly", width=14)
        self.p_status.pack(side="left", padx=4)
        ttk.Button(f2, text="Mainīt statusu", command=self.change_status).pack(side="left")
        ttk.Button(f2, text="Dzēst projektu", command=self.del_project).pack(side="left", padx=4)
        ttk.Button(f2, text="Kopsavilkums", command=self.show_summary).pack(side="left")
        ttk.Button(f2, text="+ Labojumu kārta", command=self.add_revision).pack(side="left", padx=4)

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

    # ---------- laiks ----------
    def build_time(self):
        self.t_time = self.tree(self.tab_time, ("Datums", "Projekts", "Darbība", "Stundas", "Piezīme"),
                                (100, 200, 160, 70, 250))
        f = ttk.Frame(self.tab_time)
        f.pack(fill="x", padx=6)
        self.tm_project = ttk.Combobox(f, state="readonly", width=20)
        self.tm_activity = ttk.Combobox(f, state="readonly", width=20)
        self.tm_project.pack(side="left", padx=4)
        self.tm_activity.pack(side="left", padx=4)
        self.tm_hours = ttk.Entry(f, width=6)
        self.tm_note = ttk.Entry(f, width=20)
        ttk.Label(f, text="h").pack(side="left")
        self.tm_hours.pack(side="left", padx=3)
        self.tm_note.pack(side="left", padx=3)
        ttk.Button(f, text="Pievienot", command=self.add_time).pack(side="left", padx=4)

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

    # ---------- krāsas ----------
    def build_colors(self):
        top = ttk.Frame(self.tab_colors)
        top.pack(fill="x", padx=6, pady=6)
        self.col_project = ttk.Combobox(top, state="readonly", width=24)
        self.col_project.pack(side="left")
        self.col_project.bind("<<ComboboxSelected>>", lambda e: self.draw_palette())
        self.col_name = ttk.Entry(top, width=14)
        self.col_hex = ttk.Entry(top, width=10)
        ttk.Label(top, text="Nosaukums").pack(side="left", padx=4)
        self.col_name.pack(side="left")
        ttk.Label(top, text="HEX").pack(side="left", padx=4)
        self.col_hex.pack(side="left")
        ttk.Button(top, text="Pievienot krāsu", command=self.add_color).pack(side="left", padx=6)
        self.canvas = tk.Canvas(self.tab_colors, height=260, bg="white", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=6, pady=6)

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
        for i, c in enumerate(db.get_colors(pid)):
            x = 10 + i * 110
            self.canvas.create_rectangle(x, 10, x + 100, 160, fill=c["hex"], outline="#ccc")
            self.canvas.create_text(x + 50, 180, text=c["name"])
            self.canvas.create_text(x + 50, 200, text=c["hex"].upper(), fill="#666")

    # ---------- atjaunošana ----------
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
