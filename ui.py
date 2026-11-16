import os
import sqlite3

DB_FILE = os.path.join(os.path.dirname(__file__), "design_tracker.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT,
    hourly_rate REAL NOT NULL DEFAULT 25
);

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    type TEXT,
    status TEXT NOT NULL DEFAULT 'Jauns',
    deadline TEXT,
    budget_hours REAL NOT NULL DEFAULT 20,
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS time_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    activity_id INTEGER NOT NULL,
    work_date TEXT NOT NULL,
    hours REAL NOT NULL,
    note TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (activity_id) REFERENCES activities(id)
);

CREATE TABLE IF NOT EXISTS palette_colors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    hex TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);
"""


class Database:
    def __init__(self, path=DB_FILE):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)
        self._seed_activities()

    def close(self):
        self.conn.close()

    def _seed_activities(self):
        default_activities = [
            "Skices",
            "Maketēšana",
            "Ilustrēšana",
            "Tipogrāfija",
            "Labojumi",
            "Sanāksme",
            "Eksports",
        ]
        for name in default_activities:
            self.conn.execute(
                "INSERT OR IGNORE INTO activities (name) VALUES (?)",
                (name,),
            )
        self.conn.commit()

    def add_client(self, name, email="", hourly_rate=25):
        name = (name or "").strip()
        if not name:
            raise ValueError("Vārds ir obligāts.")
        if email is None:
            email = ""
        rate = float(hourly_rate)
        self.conn.execute(
            "INSERT INTO clients (name, email, hourly_rate) VALUES (?, ?, ?)",
            (name, email.strip(), rate),
        )
        self.conn.commit()

    def list_clients(self, search=""):
        query = "SELECT * FROM clients WHERE name LIKE ? OR email LIKE ? ORDER BY name"
        like = f"%{search.strip()}%"
        rows = self.conn.execute(query, (like, like)).fetchall()
        return [dict(row) for row in rows]

    def update_client(self, client_id, name, email="", hourly_rate=25):
        name = (name or "").strip()
        if not name:
            raise ValueError("Vārds ir obligāts.")
        self.conn.execute(
            "UPDATE clients SET name=?, email=?, hourly_rate=? WHERE id=?",
            (name, (email or "").strip(), float(hourly_rate), client_id),
        )
        self.conn.commit()

    def delete_client(self, client_id):
        self.conn.execute("DELETE FROM clients WHERE id=?", (client_id,))
        self.conn.commit()

    def add_project(self, client_id, title, project_type, status, deadline, budget_hours):
        title = (title or "").strip()
        if not title:
            raise ValueError("Projekta nosaukums ir obligāts.")
        self.conn.execute(
            """
            INSERT INTO projects (client_id, title, type, status, deadline, budget_hours)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (client_id, title, project_type or "", status or "Jauns", deadline or "", float(budget_hours or 20)),
        )
        self.conn.commit()

    def list_projects(self, search=""):
        query = """
            SELECT p.*, c.name AS client_name,
                   COALESCE((SELECT SUM(t.hours) FROM time_logs t WHERE t.project_id = p.id), 0) AS spent
            FROM projects p
            JOIN clients c ON c.id = p.client_id
            WHERE p.title LIKE ? OR c.name LIKE ?
            ORDER BY p.title
        """
        like = f"%{search.strip()}%"
        rows = self.conn.execute(query, (like, like)).fetchall()
        return [dict(row) for row in rows]

    def update_project(self, project_id, client_id, title, project_type, status, deadline, budget_hours):
        title = (title or "").strip()
        if not title:
            raise ValueError("Projekta nosaukums ir obligāts.")
        self.conn.execute(
            """
            UPDATE projects
            SET client_id=?, title=?, type=?, status=?, deadline=?, budget_hours=?
            WHERE id=?
            """,
            (client_id, title, project_type or "", status or "Jauns", deadline or "", float(budget_hours or 20), project_id),
        )
        self.conn.commit()

    def delete_project(self, project_id):
        self.conn.execute("DELETE FROM projects WHERE id=?", (project_id,))
        self.conn.commit()

    def get_activities(self):
        rows = self.conn.execute("SELECT * FROM activities ORDER BY name").fetchall()
        return [dict(row) for row in rows]

    def add_time_entry(self, project_id, activity_id, work_date, hours, note=""):
        self.conn.execute(
            "INSERT INTO time_logs (project_id, activity_id, work_date, hours, note) VALUES (?, ?, ?, ?, ?)",
            (project_id, activity_id, work_date or "", float(hours), note or ""),
        )
        self.conn.commit()

    def list_time_entries(self, search=""):
        query = """
            SELECT t.*, p.title AS project_title, a.name AS activity_name
            FROM time_logs t
            JOIN projects p ON p.id = t.project_id
            JOIN activities a ON a.id = t.activity_id
            WHERE p.title LIKE ? OR a.name LIKE ? OR t.note LIKE ?
            ORDER BY t.work_date DESC
        """
        like = f"%{search.strip()}%"
        rows = self.conn.execute(query, (like, like, like)).fetchall()
        return [dict(row) for row in rows]

    def delete_time_entry(self, time_id):
        self.conn.execute("DELETE FROM time_logs WHERE id=?", (time_id,))
        self.conn.commit()

    def add_color(self, project_id, name, hex_code):
        name = (name or "").strip()
        if not name:
            raise ValueError("Krāsas nosaukums ir obligāts.")
        code = (hex_code or "").strip()
        if not code.startswith("#") or len(code) != 7:
            raise ValueError("HEX kodam jābūt formātā #RRGGBB")
        self.conn.execute(
            "INSERT INTO palette_colors (project_id, name, hex) VALUES (?, ?, ?)",
            (project_id, name, code.upper()),
        )
        self.conn.commit()

    def list_colors(self, search=""):
        query = """
            SELECT c.*, p.title AS project_title
            FROM palette_colors c
            JOIN projects p ON p.id = c.project_id
            WHERE p.title LIKE ? OR c.name LIKE ? OR c.hex LIKE ?
            ORDER BY p.title, c.name
        """
        like = f"%{search.strip()}%"
        rows = self.conn.execute(query, (like, like, like)).fetchall()
        return [dict(row) for row in rows]

    def delete_color(self, color_id):
        self.conn.execute("DELETE FROM palette_colors WHERE id=?", (color_id,))
        self.conn.commit()

    def project_summary(self, project_id):
        project = self.conn.execute(
            """
            SELECT p.*, c.name AS client_name,
                   COALESCE((SELECT SUM(t.hours) FROM time_logs t WHERE t.project_id = p.id), 0) AS spent
            FROM projects p
            JOIN clients c ON c.id = p.client_id
            WHERE p.id = ?
            """,
            (project_id,),
        ).fetchone()
        if project is None:
            return None

        spent = float(project["spent"])
        budget = float(project["budget_hours"])
        earned = spent * float(project["hourly_rate"]) if "hourly_rate" in project.keys() else 0.0
        return {
            "title": project["title"],
            "client": project["client_name"],
            "spent": spent,
            "budget": budget,
            "left": budget - spent,
            "earned": earned,
        }

    def totals_for_project(self, project_id):
        total = self.conn.execute(
            "SELECT COALESCE(SUM(hours), 0) AS total FROM time_logs WHERE project_id=?",
            (project_id,),
        ).fetchone()
        return float(total["total"]) if total else 0.0

    def get_statuses(self):
        return ["Jauns", "Procesā", "Pārskatīšanā", "Pabeigts"]


if __name__ == "__main__":
    db = Database()
    print("Database ready:", DB_FILE)
    db.close()
