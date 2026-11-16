"""SQLite database access for the design project tracker."""
import os
import re
import sqlite3
from datetime import date, datetime

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "design_tracker.db")
STATUSES = ["Jauns", "Procesā", "Pārskatīšanā", "Pabeigts"]
ACTIVITIES = ["Skices", "Maketēšana", "Ilustrēšana", "Tipogrāfija",
              "Sanāksme ar klientu", "Labojumi", "Eksports un nodošana"]

SCHEMA = """
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
"""


class Database:
    """Small database helper used by both the GUI and terminal app."""

    def __init__(self, path=DB_FILE):
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript(SCHEMA)
        for activity in ACTIVITIES:
            self.connection.execute(
                "INSERT OR IGNORE INTO activities (name) VALUES (?)", (activity,)
            )
        self.connection.commit()

    def close(self):
        self.connection.close()

    def _run(self, sql, values=()):
        try:
            self.connection.execute(sql, values)
            self.connection.commit()
        except sqlite3.IntegrityError as error:
            self.connection.rollback()
            raise ValueError(f"Nevar saglabāt izmaiņas: {error}") from error

    def _all(self, sql, values=()):
        return [dict(row) for row in self.connection.execute(sql, values).fetchall()]

    def add_client(self, name, email="", hourly_rate=25):
        name = (name or "").strip()
        if not name:
            raise ValueError("Klienta vārds ir obligāts.")
        try:
            rate = float(str(hourly_rate or 25).replace(",", "."))
        except ValueError:
            raise ValueError("Stundas likmei jābūt skaitlim.") from None
        if rate < 0:
            raise ValueError("Stundas likme nevar būt negatīva.")
        self._run("INSERT INTO clients (name, email, hourly_rate) VALUES (?, ?, ?)",
                  (name, (email or "").strip(), rate))

    def update_client(self, client_id, name, email="", hourly_rate=25):
        name = (name or "").strip()
        if not name:
            raise ValueError("Klienta vārds ir obligāts.")
        try:
            rate = float(str(hourly_rate or 25).replace(",", "."))
        except ValueError:
            raise ValueError("Stundas likmei jābūt skaitlim.") from None
        if rate < 0:
            raise ValueError("Stundas likme nevar būt negatīva.")
        self._run("UPDATE clients SET name=?, email=?, hourly_rate=? WHERE id=?",
                  (name, (email or "").strip(), rate, client_id))

    def list_clients(self, search=""):
        term = f"%{(search or '').strip()}%"
        return self._all(
            """
            SELECT * FROM clients
            WHERE name LIKE ? OR COALESCE(email, '') LIKE ?
            ORDER BY name
            """,
            (term, term),
        )

    def delete_client(self, client_id):
        self._run("DELETE FROM clients WHERE id=?", (client_id,))

    def list_projects(self, search=""):
        term = f"%{search.strip()}%"
        return self._all("""
            SELECT p.*, c.name AS client_name, c.hourly_rate,
                   COALESCE((SELECT SUM(hours) FROM time_logs WHERE project_id=p.id), 0) AS spent
            FROM projects p JOIN clients c ON c.id=p.client_id
            WHERE p.title LIKE ? OR c.name LIKE ?
            ORDER BY p.title
        """, (term, term))

    def add_project(self, client_id, title, project_type="", status="Jauns", deadline="", budget_hours=20):
        self._save_project("INSERT INTO projects (client_id,title,type,status,deadline,budget_hours) "
                            "VALUES (?,?,?,?,?,?)",
                            (client_id, title, project_type, status, deadline, budget_hours))

    def update_project(self, project_id, client_id, title, project_type="", status="Jauns",
                       deadline="", budget_hours=20):
        self._save_project("UPDATE projects SET client_id=?,title=?,type=?,status=?,deadline=?,"
                            "budget_hours=? WHERE id=?",
                            (client_id, title, project_type, status, deadline, budget_hours, project_id))

    def _save_project(self, sql, values):
        client_id, title, project_type, status, deadline, hours = values[:6]
        if not str(title or "").strip():
            raise ValueError("Projekta nosaukums ir obligāts.")
        try:
            hours = float(str(hours or 20).replace(",", "."))
        except ValueError:
            raise ValueError("Plānotajām stundām jābūt skaitlim.") from None
        if hours <= 0:
            raise ValueError("Plānotajām stundām jābūt lielākām par nulli.")
        if status not in STATUSES:
            raise ValueError("Izvēlies derīgu projekta statusu.")
        if deadline:
            try:
                datetime.strptime(deadline, "%Y-%m-%d")
            except ValueError:
                raise ValueError("Termiņš jāievada formātā GGGG-MM-DD.") from None
        self._run(sql, (client_id, str(title).strip(), (project_type or "").strip(), status,
                        deadline or None, hours, *values[6:]))

    def delete_project(self, project_id):
        self._run("DELETE FROM projects WHERE id=?", (project_id,))

    def get_statuses(self):
        return STATUSES[:]

    def get_activities(self):
        return self._all("SELECT * FROM activities ORDER BY name")

    def add_time_entry(self, project_id, activity_id, work_date, hours, note=""):
        try:
            hours = float(str(hours).replace(",", "."))
        except ValueError:
            raise ValueError("Stundām jābūt skaitlim.") from None
        if not 0 < hours <= 24:
            raise ValueError("Stundām jābūt lielākām par 0 un ne vairāk kā 24.")
        if work_date:
            try:
                datetime.strptime(work_date, "%Y-%m-%d")
            except ValueError:
                raise ValueError("Datums jāievada formātā GGGG-MM-DD.") from None
        self._run("INSERT INTO time_logs (project_id,activity_id,work_date,hours,note) "
                  "VALUES (?,?,?,?,?)",
                  (project_id, activity_id, work_date or date.today().isoformat(), hours, note.strip()))

    def list_time_entries(self, search=""):
        term = f"%{search.strip()}%"
        return self._all("""
            SELECT t.*, p.title AS project_title, a.name AS activity_name
            FROM time_logs t JOIN projects p ON p.id=t.project_id
            JOIN activities a ON a.id=t.activity_id
            WHERE p.title LIKE ? OR a.name LIKE ? OR COALESCE(t.note,'') LIKE ?
            ORDER BY t.work_date DESC, t.id DESC
        """, (term, term, term))

    def delete_time_entry(self, time_id):
        self._run("DELETE FROM time_logs WHERE id=?", (time_id,))

    def list_colors(self, search=""):
        term = f"%{search.strip()}%"
        return self._all("""
            SELECT color.*, project.title AS project_title
            FROM palette_colors color JOIN projects project ON project.id=color.project_id
            WHERE project.title LIKE ? OR color.name LIKE ? OR color.hex LIKE ?
            ORDER BY project.title, color.name
        """, (term, term, term))

    def add_color(self, project_id, name, hex_code):
        name = (name or "").strip()
        hex_code = (hex_code or "").strip()
        if not name:
            raise ValueError("Krāsas nosaukums ir obligāts.")
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", hex_code):
            raise ValueError("HEX kodam jābūt formātā #RRGGBB.")
        self._run("INSERT INTO palette_colors (project_id,name,hex) VALUES (?,?,?)",
                  (project_id, name, hex_code.upper()))

    def delete_color(self, color_id):
        self._run("DELETE FROM palette_colors WHERE id=?", (color_id,))

    def add_revision(self, project_id, note=""):
        row = self.connection.execute(
            "SELECT COALESCE(MAX(round_no), 0) + 1 FROM revision_logs WHERE project_id=?",
            (project_id,),
        ).fetchone()
        self._run("INSERT INTO revision_logs (project_id,rev_date,round_no,note) VALUES (?,?,?,?)",
                  (project_id, date.today().isoformat(), row[0], note))

    def get_revisions(self, project_id):
        return self._all("SELECT * FROM revision_logs WHERE project_id=? ORDER BY round_no",
                         (project_id,))

    def project_summary(self, project_id):
        project = self.connection.execute("""
            SELECT p.title, p.budget_hours, c.name AS client_name, c.hourly_rate,
                   COALESCE(SUM(t.hours), 0) AS spent
            FROM projects p JOIN clients c ON c.id=p.client_id
            LEFT JOIN time_logs t ON t.project_id=p.id
            WHERE p.id=? GROUP BY p.id
        """, (project_id,)).fetchone()
        if project is None:
            return None
        spent = project["spent"]
        budget = project["budget_hours"]
        return {"title": project["title"], "client": project["client_name"],
                "spent": spent, "budget": budget, "left": budget - spent,
                "earned": spent * project["hourly_rate"]}


if __name__ == "__main__":
    database = Database()
    print("Datubāze gatava:", DB_FILE)
    database.close()
