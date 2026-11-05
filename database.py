import sqlite3
from datetime import date

DB_FILE = "design_tracker.db"

ACTIVITIES = ["Skices", "Maketēšana", "Ilustrēšana", "Tipogrāfija",
              "Sanāksme ar klientu", "Labojumi", "Eksports un nodošana"]


class Database:
    def __init__(self, path=DB_FILE):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._create_tables()
        self._seed()

    def _create_tables(self):
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            hourly_rate REAL NOT NULL DEFAULT 25
        );
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            type TEXT,
            status TEXT NOT NULL DEFAULT 'Jauns',
            deadline TEXT,
            budget_hours REAL NOT NULL DEFAULT 20
        );
        CREATE TABLE IF NOT EXISTS deliverables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            format TEXT,
            done INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS time_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            activity_id INTEGER NOT NULL REFERENCES activities(id),
            work_date TEXT NOT NULL,
            hours REAL NOT NULL,
            note TEXT
        );
        CREATE TABLE IF NOT EXISTS palette_colors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            hex TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS revision_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            rev_date TEXT NOT NULL,
            round_no INTEGER NOT NULL,
            note TEXT
        );
        """)
        self.conn.commit()

    def _seed(self):
        for a in ACTIVITIES:
            self.conn.execute("INSERT OR IGNORE INTO activities(name) VALUES (?)", (a,))
        self.conn.commit()

    # ---------- klienti ----------
    def add_client(self, name, email, rate):
        self.conn.execute("INSERT INTO clients(name,email,hourly_rate) VALUES (?,?,?)",
                          (name, email, rate))
        self.conn.commit()

    def get_clients(self):
        return self.conn.execute("SELECT * FROM clients ORDER BY name").fetchall()

    def delete_client(self, cid):
        self.conn.execute("DELETE FROM clients WHERE id=?", (cid,))
        self.conn.commit()

    # ---------- projekti ----------
    def add_project(self, client_id, title, ptype, deadline, budget_hours):
        self.conn.execute(
            "INSERT INTO projects(client_id,title,type,deadline,budget_hours) VALUES (?,?,?,?,?)",
            (client_id, title, ptype, deadline, budget_hours))
        self.conn.commit()

    def get_projects(self):
        return self.conn.execute("""
            SELECT p.*, c.name AS client_name FROM projects p
            JOIN clients c ON c.id = p.client_id ORDER BY p.deadline, p.title""").fetchall()

    def set_status(self, project_id, status):
        self.conn.execute("UPDATE projects SET status=? WHERE id=?", (status, project_id))
        self.conn.commit()

    def delete_project(self, pid):
        self.conn.execute("DELETE FROM projects WHERE id=?", (pid,))
        self.conn.commit()

    # ---------- nododamie ----------
    def add_deliverable(self, project_id, name, fmt):
        self.conn.execute("INSERT INTO deliverables(project_id,name,format) VALUES (?,?,?)",
                          (project_id, name, fmt))
        self.conn.commit()

    def get_deliverables(self, project_id):
        return self.conn.execute("SELECT * FROM deliverables WHERE project_id=?",
                                 (project_id,)).fetchall()

    def toggle_deliverable(self, did):
        self.conn.execute("UPDATE deliverables SET done = 1 - done WHERE id=?", (did,))
        self.conn.commit()

    # ---------- laika uzskaite ----------
    def get_activities(self):
        return self.conn.execute("SELECT * FROM activities ORDER BY name").fetchall()

    def add_time(self, project_id, activity_id, hours, note="", work_date=None):
        self.conn.execute(
            "INSERT INTO time_logs(project_id,activity_id,work_date,hours,note) VALUES (?,?,?,?,?)",
            (project_id, activity_id, work_date or date.today().isoformat(), hours, note))
        self.conn.commit()

    def get_time_logs(self, project_id=None):
        q = """SELECT t.*, a.name AS activity, p.title FROM time_logs t
               JOIN activities a ON a.id=t.activity_id
               JOIN projects p ON p.id=t.project_id"""
        args = ()
        if project_id:
            q += " WHERE t.project_id=?"
            args = (project_id,)
        return self.conn.execute(q + " ORDER BY t.work_date DESC", args).fetchall()

    # ---------- krāsu palete ----------
    def add_color(self, project_id, name, hex_code):
        self.conn.execute("INSERT INTO palette_colors(project_id,name,hex) VALUES (?,?,?)",
                          (project_id, name, hex_code))
        self.conn.commit()

    def get_colors(self, project_id):
        return self.conn.execute("SELECT * FROM palette_colors WHERE project_id=?",
                                 (project_id,)).fetchall()

    # ---------- labojumu kārtas ----------
    def add_revision(self, project_id, note=""):
        n = self.conn.execute("SELECT COUNT(*) FROM revision_logs WHERE project_id=?",
                              (project_id,)).fetchone()[0] + 1
        self.conn.execute(
            "INSERT INTO revision_logs(project_id,rev_date,round_no,note) VALUES (?,?,?,?)",
            (project_id, date.today().isoformat(), n, note))
        self.conn.commit()

    def get_revisions(self, project_id):
        return self.conn.execute(
            "SELECT * FROM revision_logs WHERE project_id=? ORDER BY round_no",
            (project_id,)).fetchall()

    # ---------- kopsavilkums ----------
    def project_summary(self, project_id):
        r = self.conn.execute("""
            SELECT p.title, p.budget_hours, c.hourly_rate,
                   COALESCE((SELECT SUM(hours) FROM time_logs WHERE project_id=p.id),0) AS spent
            FROM projects p JOIN clients c ON c.id=p.client_id WHERE p.id=?""",
            (project_id,)).fetchone()
        if not r:
            return None
        return {"title": r["title"], "budget": r["budget_hours"], "spent": r["spent"],
                "left": r["budget_hours"] - r["spent"], "earned": r["spent"] * r["hourly_rate"]}
