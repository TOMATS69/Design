"""Datubāzes slānis: visas SQL operācijas un ievades datu pārbaude.

Gan main.py (grafiskais logs), gan terminal.py (konsole) izmanto tikai šo failu,
tāpēc SQL vaicājumi nav atkārtoti dažādās vietās.
"""
import os
import re
import sqlite3
from datetime import date, datetime

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "design_tracker.db")

STATUSES = ["Jauns", "Procesā", "Pārskatīšanā", "Pabeigts"]
INVOICE_STATUSES = ["draft", "sent", "paid", "cancelled"]
ACTIVITIES = ["Skices", "Maketēšana", "Ilustrēšana", "Tipogrāfija",
              "Sanāksme ar klientu", "Labojumi", "Eksports un nodošana"]


def _sql_list(items):
    return ", ".join(f"'{item}'" for item in items)


SCHEMA = f"""
CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT,
    hourly_rate REAL NOT NULL DEFAULT 25 CHECK (hourly_rate >= 0)
);
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    type TEXT,
    status TEXT NOT NULL DEFAULT 'Jauns' CHECK (status IN ({_sql_list(STATUSES)})),
    deadline TEXT,
    budget_hours REAL NOT NULL DEFAULT 20 CHECK (budget_hours > 0)
);
CREATE TABLE IF NOT EXISTS deliverables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    format TEXT,
    done INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0, 1))
);
CREATE TABLE IF NOT EXISTS activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS team_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE,
    role TEXT,
    cost_rate REAL CHECK (cost_rate IS NULL OR cost_rate >= 0)
);
CREATE TABLE IF NOT EXISTS time_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    activity_id INTEGER NOT NULL REFERENCES activities(id),
    work_date TEXT NOT NULL,
    hours REAL NOT NULL CHECK (hours > 0 AND hours <= 24),
    note TEXT,
    member_id INTEGER REFERENCES team_members(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS palette_colors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    hex TEXT NOT NULL CHECK (length(hex) = 7)
);
CREATE TABLE IF NOT EXISTS revision_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    rev_date TEXT NOT NULL,
    round_no INTEGER NOT NULL,
    note TEXT,
    UNIQUE (project_id, round_no)
);
CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES clients(id),
    project_id INTEGER REFERENCES projects(id),
    invoice_no TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ({_sql_list(INVOICE_STATUSES)})),
    amount REAL NOT NULL CHECK (amount >= 0),
    issued_on TEXT,
    due_on TEXT
);
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL REFERENCES invoices(id),
    amount REAL NOT NULL CHECK (amount > 0),
    paid_on TEXT NOT NULL,
    method TEXT,
    reference TEXT
);
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    description TEXT NOT NULL,
    category TEXT,
    amount REAL NOT NULL CHECK (amount >= 0),
    spent_on TEXT NOT NULL,
    billable INTEGER NOT NULL DEFAULT 0 CHECK (billable IN (0, 1))
);
CREATE TABLE IF NOT EXISTS project_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    member_id INTEGER NOT NULL REFERENCES team_members(id) ON DELETE CASCADE,
    role TEXT,
    allocation_pct REAL CHECK (allocation_pct IS NULL OR (allocation_pct >= 0 AND allocation_pct <= 100)),
    UNIQUE (project_id, member_id)
);
CREATE INDEX IF NOT EXISTS idx_projects_client ON projects(client_id);
CREATE INDEX IF NOT EXISTS idx_deliverables_project ON deliverables(project_id);
CREATE INDEX IF NOT EXISTS idx_time_project ON time_logs(project_id);
CREATE INDEX IF NOT EXISTS idx_colors_project ON palette_colors(project_id);
CREATE INDEX IF NOT EXISTS idx_invoices_client ON invoices(client_id);
CREATE INDEX IF NOT EXISTS idx_payments_invoice ON payments(invoice_id);
CREATE INDEX IF NOT EXISTS idx_expenses_project ON expenses(project_id);
"""

PROJECT_SELECT = """
SELECT p.*, c.name AS client_name, c.hourly_rate,
       COALESCE((SELECT SUM(t.hours) FROM time_logs t WHERE t.project_id = p.id), 0) AS spent
FROM projects p JOIN clients c ON c.id = p.client_id
"""

INVOICE_SELECT = """
SELECT i.*, c.name AS client_name, p.title AS project_title,
       COALESCE((SELECT SUM(pay.amount) FROM payments pay WHERE pay.invoice_id = i.id), 0) AS paid,
       i.amount - COALESCE((SELECT SUM(pay.amount) FROM payments pay
                            WHERE pay.invoice_id = i.id), 0) AS balance
FROM invoices i JOIN clients c ON c.id = i.client_id
LEFT JOIN projects p ON p.id = i.project_id
"""


def clean_text(value):
    return str(value or "").strip() or None


def require_text(value, name):
    text = clean_text(value)
    if text is None:
        raise ValueError(f"{name}: lauks nedrīkst būt tukšs")
    return text


def parse_number(value, name, low=None, strict_low=False, high=None, default=None):
    text = str(value if value is not None else "").strip().replace(",", ".")
    if text == "":
        if default is not None:
            return default
        raise ValueError(f"{name}: ievadi skaitli")
    try:
        number = float(text)
    except ValueError:
        raise ValueError(f"{name}: jābūt skaitlim")
    if low is not None and (number <= low if strict_low else number < low):
        raise ValueError(f"{name}: jābūt {'lielākam par' if strict_low else 'vismaz'} {low:g}")
    if high is not None and number > high:
        raise ValueError(f"{name}: nedrīkst būt lielāks par {high:g}")
    return number


def optional_number(value, name, low=None, high=None):
    if str(value if value is not None else "").strip() == "":
        return None
    return parse_number(value, name, low=low, high=high)


def parse_date(value, name, required=False):
    text = str(value or "").strip()
    if not text:
        if required:
            raise ValueError(f"{name}: ievadi datumu")
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date().isoformat()
    except ValueError:
        raise ValueError(f"{name}: datuma formāts ir GGGG-MM-DD")


def parse_hex(value):
    text = str(value or "").strip()
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", text):
        raise ValueError("HEX kodam jābūt formātā #RRGGBB")
    return text.upper()


def parse_email(value):
    text = str(value or "").strip()
    if text and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", text):
        raise ValueError("E-pasta adrese nav pareiza")
    return text or None


def parse_choice(value, options, name, default):
    text = str(value or "").strip() or default
    if text not in options:
        raise ValueError(f"{name}: izvēlies vienu no " + ", ".join(options))
    return text


def parse_yes_no(value):
    text = str(value if value is not None else "").strip().lower()
    if text in ("jā", "ja", "j", "1", "yes", "y"):
        return 1
    if text in ("", "nē", "ne", "n", "0", "no"):
        return 0
    raise ValueError("Rēķināms: ievadi Jā vai Nē")


def _like(term):
    return f"%{str(term or '').strip()}%"


def _friendly(error):
    text = str(error)
    if "FOREIGN KEY" in text:
        return ("Darbību nevar izpildīt: ieraksts ir saistīts ar citiem datiem (piemēram, "
                "rēķiniem, maksājumiem vai izdevumiem) vai izvēlētais ieraksts neeksistē. "
                "Vispirms izdzēs saistītos ierakstus.")
    if "UNIQUE" in text:
        return ("Šāda vērtība jau eksistē (rēķina numuram, e-pastam un projekta "
                "piešķīrumam jābūt unikāliem).")
    if "CHECK" in text:
        return "Vērtība neatbilst atļautajam diapazonam."
    return text


def invoice_overdue(invoice):
    return bool(invoice["status"] == "sent" and invoice["due_on"]
                and invoice["due_on"] < date.today().isoformat()
                and invoice["balance"] > 0.005)


def format_project_summary(s):
    return (f"Klients: {s['client']}\n"
            f"Stundas: {s['spent']:.1f} / {s['budget']:.1f} (atlicis {s['left']:.1f})\n"
            f"Ieņēmumi pēc stundām: {s['earned']:.2f} €\n"
            f"Komandas izmaksas: {s['team_cost']:.2f} €\n"
            f"Izdevumi: {s['expenses']:.2f} € (no tiem rēķināmi {s['billable_expenses']:.2f} €)\n"
            f"Peļņa: {s['profit']:.2f} €\n"
            f"Rēķini: izrakstīti {s['invoiced']:.2f} €, apmaksāti {s['paid']:.2f} €\n"
            f"Nododamie darbi: {s['deliverables_done']} / {s['deliverables_total']} gatavi\n"
            f"Labojumu kārtas: {s['revisions']}")


def format_client_balances(rows):
    if not rows:
        return "Nav neviena rēķina."
    return "\n".join(f"{r['name']}: rēķini {r['invoiced']:.2f} €, apmaksāts {r['paid']:.2f} €, "
                       f"atlikums {r['invoiced'] - r['paid']:.2f} €" for r in rows)


class Database:
    def __init__(self, path=DB_FILE):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)
        self._migrate()
        with self.conn:
            for name in ACTIVITIES:
                self.conn.execute("INSERT OR IGNORE INTO activities(name) VALUES (?)", (name,))

    def _migrate(self):
        columns = [row["name"] for row in self.conn.execute("PRAGMA table_info(time_logs)")]
        if "member_id" not in columns:
            with self.conn:
                self.conn.execute("ALTER TABLE time_logs ADD COLUMN member_id INTEGER "
                                  "REFERENCES team_members(id) ON DELETE SET NULL")

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def _transaction(self, work):
        try:
            with self.conn:
                return work(self.conn)
        except sqlite3.IntegrityError as error:
            raise ValueError(_friendly(error)) from None

    def _run(self, sql, params=()):
        return self._transaction(lambda conn: conn.execute(sql, params))

    def _all(self, sql, params=()):
        return self.conn.execute(sql, params).fetchall()

    def _one(self, sql, params=()):
        return self.conn.execute(sql, params).fetchone()

    def add_client(self, name, email, rate):
        self._run("INSERT INTO clients(name, email, hourly_rate) VALUES (?, ?, ?)",
                  (require_text(name, "Vārds"), parse_email(email),
                   parse_number(rate, "Likme", low=0, default=25.0)))

    def update_client(self, client_id, name, email, rate):
        self._run("UPDATE clients SET name=?, email=?, hourly_rate=? WHERE id=?",
                  (require_text(name, "Vārds"), parse_email(email),
                   parse_number(rate, "Likme", low=0, default=25.0), client_id))

    def delete_client(self, client_id):
        self._run("DELETE FROM clients WHERE id=?", (client_id,))

    def get_clients(self, search=""):
        like = _like(search)
        return self._all("SELECT * FROM clients WHERE name LIKE ? OR COALESCE(email,'') LIKE ? "
                         "ORDER BY name", (like, like))

    def _project_values(self, client_id, title, ptype, status, deadline, budget):
        return (client_id, require_text(title, "Nosaukums"), clean_text(ptype),
                parse_choice(status, STATUSES, "Statuss", STATUSES[0]),
                parse_date(deadline, "Termiņš"),
                parse_number(budget, "Plānotās stundas", low=0, strict_low=True, default=20.0))

    def add_project(self, client_id, title, ptype, status, deadline, budget):
        self._run("INSERT INTO projects(client_id, title, type, status, deadline, budget_hours) "
                  "VALUES (?, ?, ?, ?, ?, ?)",
                  self._project_values(client_id, title, ptype, status, deadline, budget))

    def update_project(self, project_id, client_id, title, ptype, status, deadline, budget):
        self._run("UPDATE projects SET client_id=?, title=?, type=?, status=?, deadline=?, "
                  "budget_hours=? WHERE id=?",
                  self._project_values(client_id, title, ptype, status, deadline, budget)
                  + (project_id,))

    def delete_project(self, project_id):
        self._run("DELETE FROM projects WHERE id=?", (project_id,))

    def get_projects(self, search="", status=""):
        like = _like(search)
        sql = (PROJECT_SELECT + " WHERE (p.title LIKE ? OR c.name LIKE ? "
               "OR COALESCE(p.type,'') LIKE ?)")
        params = [like, like, like]
        if status:
            sql += " AND p.status = ?"
            params.append(status)
        sql += " ORDER BY COALESCE(p.deadline, '9999-12-31'), p.title"
        return self._all(sql, params)

    def project_summary(self, project_id):
        p = self._one(PROJECT_SELECT + " WHERE p.id = ?", (project_id,))
        if p is None:
            return None
        deliverables = self._one("SELECT COUNT(*) AS total, COALESCE(SUM(done), 0) AS done "
                                 "FROM deliverables WHERE project_id = ?", (project_id,))
        revisions = self._one("SELECT COUNT(*) AS n FROM revision_logs WHERE project_id = ?",
                              (project_id,))["n"]
        expenses = self._one(
            "SELECT COALESCE(SUM(amount), 0) AS total, "
            "COALESCE(SUM(CASE WHEN billable = 1 THEN amount END), 0) AS billable "
            "FROM expenses WHERE project_id = ?", (project_id,))
        team_cost = self._one(
            "SELECT COALESCE(SUM(t.hours * COALESCE(m.cost_rate, 0)), 0) AS cost "
            "FROM time_logs t LEFT JOIN team_members m ON m.id = t.member_id "
            "WHERE t.project_id = ?", (project_id,))["cost"]
        invoices = self._one(
            "SELECT COALESCE(SUM(amount), 0) AS invoiced, COALESCE(SUM(paid), 0) AS paid FROM ("
            "SELECT i.amount, COALESCE((SELECT SUM(pay.amount) FROM payments pay "
            "WHERE pay.invoice_id = i.id), 0) AS paid FROM invoices i "
            "WHERE i.project_id = ? AND i.status != 'cancelled')", (project_id,))
        earned = p["spent"] * p["hourly_rate"]
        profit = earned - team_cost - (expenses["total"] - expenses["billable"])
        return {"title": p["title"], "client": p["client_name"], "budget": p["budget_hours"],
                "spent": p["spent"], "left": p["budget_hours"] - p["spent"], "earned": earned,
                "team_cost": team_cost, "expenses": expenses["total"],
                "billable_expenses": expenses["billable"], "profit": profit,
                "invoiced": invoices["invoiced"], "paid": invoices["paid"],
                "deliverables_total": deliverables["total"],
                "deliverables_done": deliverables["done"], "revisions": revisions}

    def add_deliverable(self, project_id, name, fmt):
        self._run("INSERT INTO deliverables(project_id, name, format) VALUES (?, ?, ?)",
                  (project_id, require_text(name, "Nosaukums"), clean_text(fmt)))

    def update_deliverable(self, deliverable_id, project_id, name, fmt):
        self._run("UPDATE deliverables SET project_id=?, name=?, format=? WHERE id=?",
                  (project_id, require_text(name, "Nosaukums"), clean_text(fmt), deliverable_id))

    def toggle_deliverable(self, deliverable_id):
        self._run("UPDATE deliverables SET done = 1 - done WHERE id=?", (deliverable_id,))

    def delete_deliverable(self, deliverable_id):
        self._run("DELETE FROM deliverables WHERE id=?", (deliverable_id,))

    def get_deliverables(self, search=""):
        like = _like(search)
        return self._all("""
            SELECT d.*, p.title AS project_title, c.name AS client_name
            FROM deliverables d JOIN projects p ON p.id = d.project_id
            JOIN clients c ON c.id = p.client_id
            WHERE d.name LIKE ? OR p.title LIKE ? OR COALESCE(d.format,'') LIKE ?
            ORDER BY p.title, d.id""", (like, like, like))

    def _member_values(self, name, email, role, cost_rate):
        return (require_text(name, "Vārds"), parse_email(email), clean_text(role),
                optional_number(cost_rate, "Pašizmaksa", low=0))

    def add_member(self, name, email, role, cost_rate):
        self._run("INSERT INTO team_members(name, email, role, cost_rate) VALUES (?, ?, ?, ?)",
                  self._member_values(name, email, role, cost_rate))

    def update_member(self, member_id, name, email, role, cost_rate):
        self._run("UPDATE team_members SET name=?, email=?, role=?, cost_rate=? WHERE id=?",
                  self._member_values(name, email, role, cost_rate) + (member_id,))

    def delete_member(self, member_id):
        self._run("DELETE FROM team_members WHERE id=?", (member_id,))

    def get_members(self, search=""):
        like = _like(search)
        return self._all("SELECT * FROM team_members WHERE name LIKE ? OR COALESCE(email,'') "
                         "LIKE ? OR COALESCE(role,'') LIKE ? ORDER BY name", (like, like, like))

    def _assignment_values(self, project_id, member_id, role, allocation):
        return (project_id, member_id, clean_text(role),
                optional_number(allocation, "Noslodze %", low=0, high=100))

    def add_assignment(self, project_id, member_id, role, allocation):
        self._run("INSERT INTO project_members(project_id, member_id, role, allocation_pct) "
                  "VALUES (?, ?, ?, ?)",
                  self._assignment_values(project_id, member_id, role, allocation))

    def update_assignment(self, assignment_id, project_id, member_id, role, allocation):
        self._run("UPDATE project_members SET project_id=?, member_id=?, role=?, "
                  "allocation_pct=? WHERE id=?",
                  self._assignment_values(project_id, member_id, role, allocation)
                  + (assignment_id,))

    def delete_assignment(self, assignment_id):
        self._run("DELETE FROM project_members WHERE id=?", (assignment_id,))

    def get_assignments(self, search=""):
        like = _like(search)
        return self._all("""
            SELECT a.*, p.title AS project_title, c.name AS client_name, m.name AS member_name
            FROM project_members a JOIN projects p ON p.id = a.project_id
            JOIN clients c ON c.id = p.client_id JOIN team_members m ON m.id = a.member_id
            WHERE p.title LIKE ? OR m.name LIKE ? OR COALESCE(a.role,'') LIKE ?
            ORDER BY p.title, m.name""", (like, like, like))

    def get_activities(self):
        return self._all("SELECT * FROM activities ORDER BY name")

    def _time_values(self, project_id, activity_id, work_date, hours, note, member_id):
        return (project_id, activity_id,
                parse_date(work_date, "Datums") or date.today().isoformat(),
                parse_number(hours, "Stundas", low=0, strict_low=True, high=24),
                clean_text(note), member_id)

    def add_time(self, project_id, activity_id, work_date, hours, note="", member_id=None):
        self._run("INSERT INTO time_logs(project_id, activity_id, work_date, hours, note, "
                  "member_id) VALUES (?, ?, ?, ?, ?, ?)",
                  self._time_values(project_id, activity_id, work_date, hours, note, member_id))

    def update_time(self, log_id, project_id, activity_id, work_date, hours, note="",
                    member_id=None):
        self._run("UPDATE time_logs SET project_id=?, activity_id=?, work_date=?, hours=?, "
                  "note=?, member_id=? WHERE id=?",
                  self._time_values(project_id, activity_id, work_date, hours, note, member_id)
                  + (log_id,))

    def delete_time(self, log_id):
        self._run("DELETE FROM time_logs WHERE id=?", (log_id,))

    def get_time_logs(self, search=""):
        like = _like(search)
        return self._all("""
            SELECT t.*, a.name AS activity, p.title AS project_title, c.name AS client_name,
                   m.name AS member_name
            FROM time_logs t JOIN activities a ON a.id = t.activity_id
            JOIN projects p ON p.id = t.project_id JOIN clients c ON c.id = p.client_id
            LEFT JOIN team_members m ON m.id = t.member_id
            WHERE p.title LIKE ? OR a.name LIKE ? OR COALESCE(t.note,'') LIKE ?
                  OR t.work_date LIKE ? OR COALESCE(m.name,'') LIKE ?
            ORDER BY t.work_date DESC, t.id DESC""", (like, like, like, like, like))

    def add_color(self, project_id, name, hex_code):
        self._run("INSERT INTO palette_colors(project_id, name, hex) VALUES (?, ?, ?)",
                  (project_id, require_text(name, "Nosaukums"), parse_hex(hex_code)))

    def update_color(self, color_id, project_id, name, hex_code):
        self._run("UPDATE palette_colors SET project_id=?, name=?, hex=? WHERE id=?",
                  (project_id, require_text(name, "Nosaukums"), parse_hex(hex_code), color_id))

    def delete_color(self, color_id):
        self._run("DELETE FROM palette_colors WHERE id=?", (color_id,))

    def get_colors(self, search=""):
        like = _like(search)
        return self._all("""
            SELECT k.*, p.title AS project_title, c.name AS client_name
            FROM palette_colors k JOIN projects p ON p.id = k.project_id
            JOIN clients c ON c.id = p.client_id
            WHERE p.title LIKE ? OR k.name LIKE ? OR k.hex LIKE ?
            ORDER BY p.title, k.id""", (like, like, like))

    def add_revision(self, project_id, note=""):
        self._run("INSERT INTO revision_logs(project_id, rev_date, round_no, note) "
                  "SELECT ?, ?, COALESCE(MAX(round_no), 0) + 1, ? "
                  "FROM revision_logs WHERE project_id = ?",
                  (project_id, date.today().isoformat(), clean_text(note), project_id))

    def get_revisions(self, project_id):
        return self._all("SELECT * FROM revision_logs WHERE project_id=? ORDER BY round_no",
                         (project_id,))

    def _expense_values(self, project_id, description, category, amount, spent_on, billable):
        return (project_id, require_text(description, "Apraksts"), clean_text(category),
                parse_number(amount, "Summa", low=0),
                parse_date(spent_on, "Datums") or date.today().isoformat(),
                parse_yes_no(billable))

    def add_expense(self, project_id, description, category, amount, spent_on, billable):
        self._run("INSERT INTO expenses(project_id, description, category, amount, spent_on, "
                  "billable) VALUES (?, ?, ?, ?, ?, ?)",
                  self._expense_values(project_id, description, category, amount,
                                       spent_on, billable))

    def update_expense(self, expense_id, project_id, description, category, amount,
                       spent_on, billable):
        self._run("UPDATE expenses SET project_id=?, description=?, category=?, amount=?, "
                  "spent_on=?, billable=? WHERE id=?",
                  self._expense_values(project_id, description, category, amount,
                                       spent_on, billable) + (expense_id,))

    def delete_expense(self, expense_id):
        self._run("DELETE FROM expenses WHERE id=?", (expense_id,))

    def get_expenses(self, search=""):
        like = _like(search)
        return self._all("""
            SELECT e.*, p.title AS project_title, c.name AS client_name
            FROM expenses e JOIN projects p ON p.id = e.project_id
            JOIN clients c ON c.id = p.client_id
            WHERE e.description LIKE ? OR p.title LIKE ? OR COALESCE(e.category,'') LIKE ?
            ORDER BY e.spent_on DESC, e.id DESC""", (like, like, like))

    def suggested_amount(self, project_id):
        row = self._one("""
            SELECT c.hourly_rate,
                   COALESCE((SELECT SUM(hours) FROM time_logs WHERE project_id = p.id), 0) AS spent,
                   COALESCE((SELECT SUM(amount) FROM expenses
                             WHERE project_id = p.id AND billable = 1), 0) AS billable
            FROM projects p JOIN clients c ON c.id = p.client_id WHERE p.id = ?""", (project_id,))
        if row is None:
            raise ValueError("Projekts nav atrasts")
        return round(row["spent"] * row["hourly_rate"] + row["billable"], 2)

    def _invoice_values(self, client_id, project_id, status, amount, issued_on, due_on):
        if project_id is not None:
            project = self._one("SELECT client_id FROM projects WHERE id = ?", (project_id,))
            if project is None or project["client_id"] != client_id:
                raise ValueError("Projekts nepieder izvēlētajam klientam")
        if str(amount if amount is not None else "").strip() == "":
            if project_id is None:
                raise ValueError("Summa: ievadi skaitli vai izvēlies projektu")
            amount = self.suggested_amount(project_id)
        issued = parse_date(issued_on, "Izrakstīšanas datums")
        due = parse_date(due_on, "Apmaksas termiņš")
        if issued and due and due < issued:
            raise ValueError("Apmaksas termiņš nedrīkst būt pirms izrakstīšanas datuma")
        return (client_id, project_id, parse_choice(status, INVOICE_STATUSES, "Statuss", "draft"),
                parse_number(amount, "Summa", low=0), issued, due)

    def _next_invoice_no(self):
        n = self._one("SELECT COALESCE(MAX(id), 0) + 1 AS n FROM invoices")["n"]
        return f"INV-{date.today().year}-{n:03d}"

    def add_invoice(self, client_id, project_id, invoice_no, status, amount, issued_on, due_on):
        c, p, st, am, iss, due = self._invoice_values(client_id, project_id, status, amount,
                                                       issued_on, due_on)
        number = clean_text(invoice_no) or self._next_invoice_no()
        self._run("INSERT INTO invoices(client_id, project_id, invoice_no, status, amount, "
                  "issued_on, due_on) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (c, p, number, st, am, iss, due))

    def update_invoice(self, invoice_id, client_id, project_id, invoice_no, status, amount,
                       issued_on, due_on):
        c, p, st, am, iss, due = self._invoice_values(client_id, project_id, status, amount,
                                                       issued_on, due_on)
        self._run("UPDATE invoices SET client_id=?, project_id=?, invoice_no=?, status=?, "
                  "amount=?, issued_on=?, due_on=? WHERE id=?",
                  (c, p, require_text(invoice_no, "Rēķina numurs"), st, am, iss, due, invoice_id))

    def delete_invoice(self, invoice_id):
        self._run("DELETE FROM invoices WHERE id=?", (invoice_id,))

    def get_invoices(self, search="", status=""):
        like = _like(search)
        sql = INVOICE_SELECT + (" WHERE (i.invoice_no LIKE ? OR c.name LIKE ? "
                                "OR COALESCE(p.title,'') LIKE ?)")
        params = [like, like, like]
        if status:
            sql += " AND i.status = ?"
            params.append(status)
        return self._all(sql + " ORDER BY i.id DESC", params)

    def get_client_balances(self):
        return self._all("""
            SELECT c.id, c.name, SUM(x.amount) AS invoiced, SUM(x.paid) AS paid
            FROM clients c JOIN (
                SELECT i.client_id, i.amount,
                       COALESCE((SELECT SUM(pay.amount) FROM payments pay
                                 WHERE pay.invoice_id = i.id), 0) AS paid
                FROM invoices i WHERE i.status != 'cancelled') x ON x.client_id = c.id
            GROUP BY c.id ORDER BY c.name""")

    def _sync_invoice(self, conn, invoice_id):
        row = conn.execute(
            "SELECT status, amount, COALESCE((SELECT SUM(amount) FROM payments "
            "WHERE invoice_id = ?), 0) AS paid FROM invoices WHERE id = ?",
            (invoice_id, invoice_id)).fetchone()
        if row is None or row["status"] == "cancelled":
            return
        if row["amount"] > 0 and row["paid"] >= row["amount"] - 0.005:
            new_status = "paid"
        elif row["status"] == "paid":
            new_status = "sent"
        else:
            return
        conn.execute("UPDATE invoices SET status = ? WHERE id = ?", (new_status, invoice_id))

    def _payment_values(self, invoice_id, amount, paid_on, method, reference, payment_id=0):
        amount = parse_number(amount, "Summa", low=0, strict_low=True)
        invoice = self._one(
            "SELECT i.status, i.amount - COALESCE((SELECT SUM(amount) FROM payments "
            "WHERE invoice_id = i.id AND id != ?), 0) AS balance FROM invoices i WHERE i.id = ?",
            (payment_id, invoice_id))
        if invoice is None:
            raise ValueError("Rēķins nav atrasts")
        if invoice["status"] == "cancelled":
            raise ValueError("Atceltam rēķinam maksājumu reģistrēt nevar")
        if amount > invoice["balance"] + 0.005:
            raise ValueError(f"Maksājums pārsniedz rēķina atlikumu ({invoice['balance']:.2f} €)")
        return (invoice_id, amount, parse_date(paid_on, "Datums") or date.today().isoformat(),
                clean_text(method), clean_text(reference))

    def add_payment(self, invoice_id, amount, paid_on, method, reference):
        values = self._payment_values(invoice_id, amount, paid_on, method, reference)

        def work(conn):
            conn.execute("INSERT INTO payments(invoice_id, amount, paid_on, method, reference) "
                         "VALUES (?, ?, ?, ?, ?)", values)
            self._sync_invoice(conn, invoice_id)
        self._transaction(work)

    def update_payment(self, payment_id, invoice_id, amount, paid_on, method, reference):
        old = self._one("SELECT invoice_id FROM payments WHERE id = ?", (payment_id,))
        if old is None:
            raise ValueError("Maksājums nav atrasts")
        values = self._payment_values(invoice_id, amount, paid_on, method, reference, payment_id)

        def work(conn):
            conn.execute("UPDATE payments SET invoice_id=?, amount=?, paid_on=?, method=?, "
                         "reference=? WHERE id=?", values + (payment_id,))
            for affected in {old["invoice_id"], invoice_id}:
                self._sync_invoice(conn, affected)
        self._transaction(work)

    def delete_payment(self, payment_id):
        old = self._one("SELECT invoice_id FROM payments WHERE id = ?", (payment_id,))
        if old is None:
            return

        def work(conn):
            conn.execute("DELETE FROM payments WHERE id = ?", (payment_id,))
            self._sync_invoice(conn, old["invoice_id"])
        self._transaction(work)

    def get_payments(self, search=""):
        like = _like(search)
        return self._all("""
            SELECT pay.*, i.invoice_no, c.name AS client_name
            FROM payments pay JOIN invoices i ON i.id = pay.invoice_id
            JOIN clients c ON c.id = i.client_id
            WHERE i.invoice_no LIKE ? OR c.name LIKE ? OR COALESCE(pay.method,'') LIKE ?
                  OR COALESCE(pay.reference,'') LIKE ?
            ORDER BY pay.paid_on DESC, pay.id DESC""", (like, like, like, like))


""""""""""""""""""""""""""""""""""""""""


"""Terminal version"""


"""Konsoles versija. Izmanto to pašu datubāzes slāni (database.py) kā grafiskais logs."""
import sqlite3

from database import (INVOICE_STATUSES, STATUSES, Database, format_client_balances,
                      format_project_summary, invoice_overdue)


def ask(label, default=""):
    shown = f" [{default}]" if default not in (None, "") else ""
    value = input(f"{label}{shown}: ").strip()
    return value if value else ("" if default is None else str(default))


def print_rows(rows, describe):
    for row in rows:
        print(f"  [{row['id']}] {describe(row)}")


def choose(rows, describe, current=None):
    if not rows:
        raise ValueError("Nav ierakstu, ko izvēlēties")
    print_rows(rows, describe)
    by_id = {row["id"]: row for row in rows}
    text = input(f"ID{f' [{current}]' if current else ''}: ").strip()
    if text == "" and current in by_id:
        return by_id[current]
    try:
        return by_id[int(text)]
    except (ValueError, KeyError):
        raise ValueError("Nepareizs ID")


def choose_optional(rows, describe, current=None):
    if not rows:
        return None
    print_rows(rows, describe)
    by_id = {row["id"]: row for row in rows}
    text = input("ID (Enter = " + ("paturēt" if current else "nav") + ", 0 = nav): ").strip()
    if text == "":
        return by_id.get(current)
    if text == "0":
        return None
    try:
        return by_id[int(text)]
    except (ValueError, KeyError):
        raise ValueError("Nepareizs ID")


def show(rows, describe):
    print_rows(rows, describe) if rows else print("Nekas nav atrasts.")


def crud_menu(title, list_fn, describe, add_fn, edit_fn, delete_fn, extra=None):
    extra = extra or {}
    while True:
        print(f"\n--- {title} ---")
        print("1 Skatīt / meklēt   2 Pievienot   3 Labot   4 Dzēst")
        for key, (name, _) in extra.items():
            print(f"{key} {name}")
        print("0 Atpakaļ")
        choice = input("> ").strip()
        if choice == "0":
            return
        try:
            if choice == "1":
                show(list_fn(input("Meklēt (Enter = rādīt visu): ").strip()), describe)
            elif choice == "2":
                add_fn()
                print("Pievienots.")
            elif choice == "3":
                edit_fn(choose(list_fn(""), describe))
                print("Saglabāts.")
            elif choice == "4":
                row = choose(list_fn(""), describe)
                if input(f"Tiešām dzēst «{describe(row)}»? (j/n): ").lower() == "j":
                    delete_fn(row)
                    print("Izdzēsts.")
            elif choice in extra:
                extra[choice][1]()
            else:
                print("Nezināma izvēle.")
        except (ValueError, sqlite3.Error) as error:
            print("Kļūda:", error)


def d_client(c):
    return f"{c['name']} | {c['email'] or '-'} | {c['hourly_rate']:g} €/h"


def d_project(p):
    return (f"{p['title']} ({p['client_name']}) | {p['status']} | "
            f"termiņš {p['deadline'] or '-'} | {p['spent']:g}/{p['budget_hours']:g} h")


def d_deliverable(d):
    return f"{'[x]' if d['done'] else '[ ]'} {d['name']} | {d['format'] or '-'} | {d['project_title']}"


def d_time(t):
    return (f"{t['work_date']} | {t['project_title']} | {t['activity']} | "
            f"{t['member_name'] or '-'} | {t['hours']:g} h | {t['note'] or ''}")


def d_color(k):
    return f"{k['name']} {k['hex']} | {k['project_title']}"


def d_member(m):
    cost = f"{m['cost_rate']:g} €/h" if m["cost_rate"] is not None else "-"
    return f"{m['name']} | {m['email'] or '-'} | {m['role'] or '-'} | {cost}"


def d_assignment(a):
    pct = f"{a['allocation_pct']:g} %" if a["allocation_pct"] is not None else "-"
    return f"{a['member_name']} → {a['project_title']} | {a['role'] or '-'} | {pct}"


def d_expense(e):
    return (f"{e['spent_on']} | {e['project_title']} | {e['description']} | "
            f"{e['amount']:.2f} € | {'rēķināms' if e['billable'] else 'nerēķināms'}")


def d_invoice(i):
    late = " KAVĒTS" if invoice_overdue(i) else ""
    return (f"{i['invoice_no']} | {i['client_name']} | {i['status']} | {i['amount']:.2f} € "
            f"(atlikums {i['balance']:.2f} €){late}")


def d_payment(p):
    return f"{p['paid_on']} | {p['invoice_no']} ({p['client_name']}) | {p['amount']:.2f} € | {p['method'] or '-'}"


def pick_project(db, current=None):
    return choose(db.get_projects(), d_project, current)["id"]


def pick_member(db, current=None):
    return choose(db.get_members(), d_member, current)["id"]


def clients_menu(db):
    crud_menu(
        "KLIENTI", db.get_clients, d_client,
        lambda: db.add_client(ask("Vārds"), ask("E-pasts"), ask("Likme €/h", 25)),
        lambda c: db.update_client(c["id"], ask("Vārds", c["name"]),
                                   ask("E-pasts", c["email"]), ask("Likme €/h", c["hourly_rate"])),
        lambda c: db.delete_client(c["id"]))


def projects_menu(db):
    def add():
        client = choose(db.get_clients(), d_client)
        db.add_project(client["id"], ask("Nosaukums"), ask("Veids (logo, plakāts...)"),
                       ask(f"Statuss ({', '.join(STATUSES)})", STATUSES[0]),
                       ask("Termiņš (GGGG-MM-DD)"), ask("Plānotās stundas", 20))

    def edit(p):
        client = choose(db.get_clients(), d_client, p["client_id"])
        db.update_project(p["id"], client["id"], ask("Nosaukums", p["title"]),
                          ask("Veids", p["type"]), ask("Statuss", p["status"]),
                          ask("Termiņš", p["deadline"]), ask("Plānotās stundas", p["budget_hours"]))

    def summary():
        project = choose(db.get_projects(), d_project)
        print(f"\n{project['title']}\n" + format_project_summary(db.project_summary(project["id"])))

    def revision():
        db.add_revision(pick_project(db), ask("Piezīme"))
        print("Labojumu kārta reģistrēta.")

    crud_menu("PROJEKTI", db.get_projects, d_project, add, edit,
              lambda p: db.delete_project(p["id"]),
              extra={"5": ("Projekta kopsavilkums", summary), "6": ("+ Labojumu kārta", revision)})


def deliverables_menu(db):
    def toggle():
        db.toggle_deliverable(choose(db.get_deliverables(""), d_deliverable)["id"])
        print("Statuss nomainīts.")

    crud_menu(
        "NODODAMIE DARBI", db.get_deliverables, d_deliverable,
        lambda: db.add_deliverable(pick_project(db), ask("Nosaukums"), ask("Formāts (PNG, PDF...)")),
        lambda d: db.update_deliverable(d["id"], pick_project(db, d["project_id"]),
                                        ask("Nosaukums", d["name"]), ask("Formāts", d["format"])),
        lambda d: db.delete_deliverable(d["id"]),
        extra={"5": ("Gatavs / nav gatavs", toggle)})


def time_menu(db):
    def activity(current=None):
        return choose(db.get_activities(), lambda a: a["name"], current)["id"]

    def member_id(current=None):
        member = choose_optional(db.get_members(), d_member, current)
        return member["id"] if member else None

    crud_menu(
        "LAIKA UZSKAITE", db.get_time_logs, d_time,
        lambda: db.add_time(pick_project(db), activity(), ask("Datums (Enter = šodien)"),
                            ask("Stundas"), ask("Piezīme"), member_id()),
        lambda t: db.update_time(t["id"], pick_project(db, t["project_id"]),
                                 activity(t["activity_id"]), ask("Datums", t["work_date"]),
                                 ask("Stundas", t["hours"]), ask("Piezīme", t["note"]),
                                 member_id(t["member_id"])),
        lambda t: db.delete_time(t["id"]))


def colors_menu(db):
    crud_menu(
        "KRĀSU PALETE", db.get_colors, d_color,
        lambda: db.add_color(pick_project(db), ask("Krāsas nosaukums"), ask("HEX (#RRGGBB)")),
        lambda k: db.update_color(k["id"], pick_project(db, k["project_id"]),
                                  ask("Nosaukums", k["name"]), ask("HEX", k["hex"])),
        lambda k: db.delete_color(k["id"]))


def members_menu(db):
    crud_menu(
        "KOMANDA", db.get_members, d_member,
        lambda: db.add_member(ask("Vārds"), ask("E-pasts"), ask("Loma"), ask("Pašizmaksa €/h")),
        lambda m: db.update_member(m["id"], ask("Vārds", m["name"]), ask("E-pasts", m["email"]),
                                   ask("Loma", m["role"]), ask("Pašizmaksa €/h", m["cost_rate"])),
        lambda m: db.delete_member(m["id"]))


def assignments_menu(db):
    crud_menu(
        "PROJEKTA KOMANDA (PIEŠĶĪRUMI)", db.get_assignments, d_assignment,
        lambda: db.add_assignment(pick_project(db), pick_member(db), ask("Loma projektā"),
                                  ask("Noslodze % (0-100)")),
        lambda a: db.update_assignment(a["id"], pick_project(db, a["project_id"]),
                                       pick_member(db, a["member_id"]),
                                       ask("Loma projektā", a["role"]),
                                       ask("Noslodze %", a["allocation_pct"])),
        lambda a: db.delete_assignment(a["id"]))


def expenses_menu(db):
    crud_menu(
        "IZDEVUMI", db.get_expenses, d_expense,
        lambda: db.add_expense(pick_project(db), ask("Apraksts"), ask("Kategorija"), ask("Summa €"),
                               ask("Datums (Enter = šodien)"), ask("Rēķināms klientam (j/n)")),
        lambda e: db.update_expense(e["id"], pick_project(db, e["project_id"]),
                                    ask("Apraksts", e["description"]), ask("Kategorija", e["category"]),
                                    ask("Summa €", e["amount"]), ask("Datums", e["spent_on"]),
                                    ask("Rēķināms (j/n)", "j" if e["billable"] else "n")),
        lambda e: db.delete_expense(e["id"]))


def invoices_menu(db):
    def client_projects(client):
        return [p for p in db.get_projects() if p["client_id"] == client["id"]]

    def add():
        client = choose(db.get_clients(), d_client)
        project = choose_optional(client_projects(client), d_project)
        db.add_invoice(client["id"], project["id"] if project else None,
                       ask("Rēķina nr. (Enter = automātiski)"),
                       ask(f"Statuss ({', '.join(INVOICE_STATUSES)})", "draft"),
                       ask("Summa € (Enter = aprēķināt no projekta)"),
                       ask("Izrakstīšanas datums (GGGG-MM-DD)"), ask("Apmaksāt līdz (GGGG-MM-DD)"))

    def edit(i):
        client = choose(db.get_clients(), d_client, i["client_id"])
        project = choose_optional(client_projects(client), d_project, i["project_id"])
        db.update_invoice(i["id"], client["id"], project["id"] if project else None,
                          ask("Rēķina nr.", i["invoice_no"]), ask("Statuss", i["status"]),
                          ask("Summa €", i["amount"]), ask("Izrakstīts", i["issued_on"]),
                          ask("Apmaksāt līdz", i["due_on"]))

    crud_menu("RĒĶINI", db.get_invoices, d_invoice, add, edit, lambda i: db.delete_invoice(i["id"]),
              extra={"5": ("Parādi pa klientiem",
                           lambda: print(format_client_balances(db.get_client_balances())) )})


def payments_menu(db):
    def invoice():
        return choose(db.get_invoices(), d_invoice)

    crud_menu(
        "MAKSĀJUMI", db.get_payments, d_payment,
        lambda: db.add_payment(invoice()["id"], ask("Summa €"), ask("Datums (Enter = šodien)"),
                               ask("Metode"), ask("Atsauce")),
        lambda p: db.update_payment(p["id"], choose(db.get_invoices(), d_invoice, p["invoice_id"])["id"],
                                    ask("Summa €", p["amount"]), ask("Datums", p["paid_on"]),
                                    ask("Metode", p["method"]), ask("Atsauce", p["reference"])),
        lambda p: db.delete_payment(p["id"]))


def main():
    menus = {"1": clients_menu, "2": projects_menu, "3": deliverables_menu, "4": time_menu,
             "5": colors_menu, "6": members_menu, "7": assignments_menu,
             "8": expenses_menu, "9": invoices_menu, "10": payments_menu}
    with Database() as db:
        while True:
            print("\n=== DIZAINA PROJEKTU PĀRVALDNIEKS ===")
            print("1 Klienti   2 Projekti   3 Nododamie   4 Laiks   5 Krāsas")
            print("6 Komanda   7 Piešķīrumi   8 Izdevumi   9 Rēķini   10 Maksājumi   0 Iziet")
            choice = input("> ").strip()
            if choice == "0":
                break
            if choice in menus:
                menus[choice](db)
            else:
                print("Nezināma izvēle.")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nPrograma aizvērta.")


""""""""""""""""""""""""""""""""""""""""


"""Grafiskais interfeiss (Tkinter). Visa datu loģika atrodas database.py."""
import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk

from database import (INVOICE_STATUSES, STATUSES, Database, format_client_balances,
                      format_project_summary, invoice_overdue)

NONE_LABEL = "(nav norādīts)"


def fmt(value):
    return "" if value is None else value


def money(value):
    return f"{value:.2f}"


def project_label(project):
    return f"{project['title']} ({project['client_name']})"


class Form(ttk.Frame):
    def __init__(self, parent, fields, per_row=6):
        super().__init__(parent)
        self.widgets = {}
        for n, (key, label, values) in enumerate(fields):
            row, column = (n // per_row) * 2, n % per_row
            ttk.Label(self, text=label).grid(row=row, column=column, sticky="w", padx=4)
            if values is None:
                widget = ttk.Entry(self, width=17)
            else:
                widget = ttk.Combobox(self, values=values, state="readonly", width=19)
            widget.grid(row=row + 1, column=column, padx=4, pady=(0, 4))
            self.widgets[key] = widget

    def get(self, key):
        return self.widgets[key].get().strip()

    def index(self, key):
        return self.widgets[key].current()

    def set(self, key, value):
        widget = self.widgets[key]
        if isinstance(widget, ttk.Combobox):
            widget.set(fmt(value))
        else:
            widget.delete(0, "end")
            widget.insert(0, fmt(value))

    def fill(self, **values):
        for key, value in values.items():
            self.set(key, value)

    def select(self, key, index):
        if index >= 0:
            self.widgets[key].current(index)

    def set_values(self, key, values):
        self.widgets[key]["values"] = values

    def clear(self):
        for key in self.widgets:
            self.set(key, "")


class BaseTab(ttk.Frame):
    columns = ()
    widths = ()
    fields = ()
    filter_values = None
    delete_warning = "Dzēst izvēlēto ierakstu?"

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.db = app.db
        self.records = {}

        self.bar = ttk.Frame(self)
        self.bar.pack(fill="x", padx=6, pady=6)
        ttk.Label(self.bar, text="Meklēt:").pack(side="left")
        self.search_var = tk.StringVar()
        ttk.Entry(self.bar, textvariable=self.search_var, width=28).pack(side="left", padx=4)
        self.search_var.trace_add("write", lambda *_: self.refresh())

        self.filter = None
        if self.filter_values:
            ttk.Label(self.bar, text="Statuss:").pack(side="left", padx=(14, 0))
            self.filter = ttk.Combobox(self.bar, values=["Visi"] + self.filter_values,
                                       state="readonly", width=14)
            self.filter.set("Visi")
            self.filter.pack(side="left", padx=4)
            self.filter.bind("<<ComboboxSelected>>", lambda _: self.refresh())

        self.form = Form(self, self.fields)
        self.form.pack(fill="x", padx=6, pady=(8, 0))

        self.tree = ttk.Treeview(self, columns=self.columns, show="headings", height=8)
        for column, width in zip(self.columns, self.widths):
            self.tree.heading(column, text=column)
            self.tree.column(column, width=width)
        self.tree.pack(fill="both", expand=True, padx=6)
        self.tree.bind("<<TreeviewSelect>>", lambda _: self.on_select())

        self.buttons = ttk.Frame(self)
        self.buttons.pack(fill="x", padx=6, pady=6)
        self.add_button("Pievienot", self.add)
        self.add_button("Saglabāt izmaiņas", self.save)
        self.add_button("Dzēst", self.remove)
        self.add_button("Notīrīt formu", self.form.clear)

    def add_button(self, text, command):
        ttk.Button(self.buttons, text=text, command=command).pack(side="left", padx=(0, 6))

    def filter_value(self):
        value = self.filter.get() if self.filter else ""
        return "" if value in ("", "Visi") else value

    def selected(self):
        selection = self.tree.selection()
        return self.records.get(int(selection[0])) if selection else None

    def need_selection(self):
        record = self.selected()
        if record is None:
            messagebox.showinfo("Izvēle", "Vispirms izvēlies ierakstu tabulā.")
        return record

    def picked(self, key, items, message):
        index = self.form.index(key)
        if index < 0:
            raise ValueError(message)
        return items[index]["id"]

    def optional(self, key, items):
        index = self.form.index(key)
        return items[index - 1]["id"] if index > 0 else None

    def index_of(self, items, record_id):
        return next((i for i, item in enumerate(items) if item["id"] == record_id), -1)

    def run(self, action):
        try:
            action()
        except (ValueError, sqlite3.Error) as error:
            messagebox.showerror("Kļūda", str(error))
            return
        self.form.clear()
        self.app.refresh_all()

    def add(self):
        self.run(self.do_add)

    def save(self):
        record = self.need_selection()
        if record:
            self.run(lambda: self.do_save(record))

    def remove(self):
        record = self.need_selection()
        if record and messagebox.askyesno("Dzēšana", self.delete_warning):
            self.run(lambda: self.do_delete(record))

    def on_select(self):
        record = self.selected()
        if record:
            self.fill(record)

    def refresh(self):
        self.records = {}
        self.tree.delete(*self.tree.get_children())
        for record in self.fetch(self.search_var.get().strip()):
            self.records[record["id"]] = record
            self.tree.insert("", "end", iid=str(record["id"]),
                             values=[fmt(v) for v in self.to_values(record)])
        self.on_refresh()

    def on_refresh(self):
        pass


class ClientsTab(BaseTab):
    columns = ("Vārds", "E-pasts", "Likme €/h")
    widths = (260, 320, 100)
    fields = [("name", "Vārds", None), ("email", "E-pasts", None), ("rate", "Likme €/h", None)]
    delete_warning = "Dzēst klientu un visus viņa projektus?"

    def fetch(self, term):
        return self.db.get_clients(term)

    def to_values(self, r):
        return r["name"], r["email"], r["hourly_rate"]

    def fill(self, r):
        self.form.fill(name=r["name"], email=r["email"], rate=r["hourly_rate"])

    def do_add(self):
        f = self.form
        self.db.add_client(f.get("name"), f.get("email"), f.get("rate"))

    def do_save(self, r):
        f = self.form
        self.db.update_client(r["id"], f.get("name"), f.get("email"), f.get("rate"))

    def do_delete(self, r):
        self.db.delete_client(r["id"])


class ProjectsTab(BaseTab):
    columns = ("Projekts", "Klients", "Veids", "Statuss", "Termiņš", "Plān. h", "Izmantots h")
    widths = (190, 140, 100, 110, 95, 70, 90)
    fields = [("client", "Klients", []), ("title", "Nosaukums", None), ("type", "Veids", None),
              ("status", "Statuss", STATUSES), ("deadline", "Termiņš (GGGG-MM-DD)", None),
              ("budget", "Plān. stundas", None)]
    filter_values = STATUSES
    delete_warning = "Dzēst projektu un tā laiku, krāsas un nododamos darbus?"

    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.clients = []
        self.add_button("Kopsavilkums", self.summary)
        self.add_button("+ Labojumu kārta", self.add_revision)

    def fetch(self, term):
        return self.db.get_projects(term, self.filter_value())

    def to_values(self, r):
        return (r["title"], r["client_name"], r["type"], r["status"], r["deadline"],
                r["budget_hours"], r["spent"])

    def on_refresh(self):
        self.clients = self.db.get_clients()
        self.form.set_values("client", [c["name"] for c in self.clients])

    def fill(self, r):
        self.form.select("client", self.index_of(self.clients, r["client_id"]))
        self.form.fill(title=r["title"], type=r["type"], status=r["status"],
                       deadline=r["deadline"], budget=r["budget_hours"])

    def values(self):
        f = self.form
        return (self.picked("client", self.clients, "Izvēlies klientu"), f.get("title"),
                f.get("type"), f.get("status"), f.get("deadline"), f.get("budget"))

    def do_add(self):
        self.db.add_project(*self.values())

    def do_save(self, r):
        self.db.update_project(r["id"], *self.values())

    def do_delete(self, r):
        self.db.delete_project(r["id"])

    def summary(self):
        record = self.need_selection()
        if record:
            summary = self.db.project_summary(record["id"])
            messagebox.showinfo(summary["title"], format_project_summary(summary))

    def add_revision(self):
        record = self.need_selection()
        if record:
            self.run(lambda: self.db.add_revision(record["id"]))


class ProjectPickerTab(BaseTab):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.projects = []

    def load_projects(self):
        self.projects = self.db.get_projects()
        self.form.set_values("project", [project_label(p) for p in self.projects])


class DeliverablesTab(ProjectPickerTab):
    columns = ("Projekts", "Nododamais darbs", "Formāts", "Gatavs")
    widths = (260, 280, 120, 80)
    fields = [("project", "Projekts", []), ("name", "Nododamais darbs", None),
              ("format", "Formāts (PNG, PDF...)", None)]

    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.add_button("Gatavs / nav gatavs", self.toggle)

    def fetch(self, term):
        return self.db.get_deliverables(term)

    def to_values(self, r):
        return r["project_title"], r["name"], r["format"], "✓" if r["done"] else ""

    def on_refresh(self):
        self.load_projects()

    def fill(self, r):
        self.form.select("project", self.index_of(self.projects, r["project_id"]))
        self.form.fill(name=r["name"], format=r["format"])

    def values(self):
        return (self.picked("project", self.projects, "Izvēlies projektu"),
                self.form.get("name"), self.form.get("format"))

    def do_add(self):
        self.db.add_deliverable(*self.values())

    def do_save(self, r):
        self.db.update_deliverable(r["id"], *self.values())

    def do_delete(self, r):
        self.db.delete_deliverable(r["id"])

    def toggle(self):
        record = self.need_selection()
        if record:
            self.run(lambda: self.db.toggle_deliverable(record["id"]))


class TimeTab(ProjectPickerTab):
    columns = ("Datums", "Projekts", "Darbība", "Dalībnieks", "Stundas", "Piezīme")
    widths = (95, 200, 150, 120, 70, 230)
    fields = [("project", "Projekts", []), ("activity", "Darbība", []),
              ("member", "Dalībnieks", []), ("date", "Datums (tukšs = šodien)", None),
              ("hours", "Stundas", None), ("note", "Piezīme", None)]

    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.activities, self.members = [], []
        self.total = ttk.Label(self.bar, text="")
        self.total.pack(side="right")

    def fetch(self, term):
        return self.db.get_time_logs(term)

    def to_values(self, r):
        return (r["work_date"], r["project_title"], r["activity"], r["member_name"],
                r["hours"], r["note"])

    def on_refresh(self):
        self.load_projects()
        self.activities = self.db.get_activities()
        self.members = self.db.get_members()
        self.form.set_values("activity", [a["name"] for a in self.activities])
        self.form.set_values("member", [NONE_LABEL] + [m["name"] for m in self.members])
        total = sum(r["hours"] for r in self.records.values())
        self.total.config(text=f"Kopā redzamajiem ierakstiem: {total:.1f} h")

    def fill(self, r):
        self.form.select("project", self.index_of(self.projects, r["project_id"]))
        self.form.select("activity", self.index_of(self.activities, r["activity_id"]))
        self.form.select("member", self.index_of(self.members, r["member_id"]) + 1)
        self.form.fill(date=r["work_date"], hours=r["hours"], note=r["note"])

    def values(self):
        f = self.form
        return (self.picked("project", self.projects, "Izvēlies projektu"),
                self.picked("activity", self.activities, "Izvēlies darbību"),
                f.get("date"), f.get("hours"), f.get("note"),
                self.optional("member", self.members))

    def do_add(self):
        self.db.add_time(*self.values())

    def do_save(self, r):
        self.db.update_time(r["id"], *self.values())

    def do_delete(self, r):
        self.db.delete_time(r["id"])


class ColorsTab(ProjectPickerTab):
    columns = ("Projekts", "Krāsas nosaukums", "HEX")
    widths = (280, 260, 120)
    fields = [("project", "Projekts", []), ("name", "Krāsas nosaukums", None),
              ("hex", "HEX (#RRGGBB)", None)]

    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.canvas = tk.Canvas(self, height=172, bg="white", highlightthickness=0)
        self.canvas.pack(fill="x", padx=6, pady=6)

    def fetch(self, term):
        return self.db.get_colors(term)

    def to_values(self, r):
        return r["project_title"], r["name"], r["hex"]

    def on_refresh(self):
        self.load_projects()
        self.draw_palette()

    def draw_palette(self):
        self.canvas.delete("all")
        for i, r in enumerate(list(self.records.values())[:16]):
            x, y = 10 + (i % 8) * 108, 8 + (i // 8) * 84
            self.canvas.create_rectangle(x, y, x + 98, y + 48, fill=r["hex"], outline="#bbbbbb")
            self.canvas.create_text(x + 49, y + 60, text=r["name"][:16], fill="#222222")
            self.canvas.create_text(x + 49, y + 74, text=r["hex"], fill="#777777")

    def fill(self, r):
        self.form.select("project", self.index_of(self.projects, r["project_id"]))
        self.form.fill(name=r["name"], hex=r["hex"])

    def values(self):
        return (self.picked("project", self.projects, "Izvēlies projektu"),
                self.form.get("name"), self.form.get("hex"))

    def do_add(self):
        self.db.add_color(*self.values())

    def do_save(self, r):
        self.db.update_color(r["id"], *self.values())

    def do_delete(self, r):
        self.db.delete_color(r["id"])


class MembersTab(BaseTab):
    columns = ("Vārds", "E-pasts", "Loma", "Pašizmaksa €/h")
    widths = (220, 260, 200, 120)
    fields = [("name", "Vārds", None), ("email", "E-pasts", None), ("role", "Loma", None),
              ("cost", "Pašizmaksa €/h", None)]
    delete_warning = "Dzēst komandas dalībnieku? Viņa piešķīrumi tiks izdzēsti, laika ieraksti paliks."

    def fetch(self, term):
        return self.db.get_members(term)

    def to_values(self, r):
        return r["name"], r["email"], r["role"], r["cost_rate"]

    def fill(self, r):
        self.form.fill(name=r["name"], email=r["email"], role=r["role"], cost=r["cost_rate"])

    def values(self):
        f = self.form
        return f.get("name"), f.get("email"), f.get("role"), f.get("cost")

    def do_add(self):
        self.db.add_member(*self.values())

    def do_save(self, r):
        self.db.update_member(r["id"], *self.values())

    def do_delete(self, r):
        self.db.delete_member(r["id"])


class AssignmentsTab(ProjectPickerTab):
    columns = ("Projekts", "Dalībnieks", "Loma projektā", "Noslodze %")
    widths = (280, 200, 220, 100)
    fields = [("project", "Projekts", []), ("member", "Dalībnieks", []),
              ("role", "Loma projektā", None), ("allocation", "Noslodze % (0-100)", None)]

    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.members = []

    def fetch(self, term):
        return self.db.get_assignments(term)

    def to_values(self, r):
        return r["project_title"], r["member_name"], r["role"], r["allocation_pct"]

    def on_refresh(self):
        self.load_projects()
        self.members = self.db.get_members()
        self.form.set_values("member", [m["name"] for m in self.members])

    def fill(self, r):
        self.form.select("project", self.index_of(self.projects, r["project_id"]))
        self.form.select("member", self.index_of(self.members, r["member_id"]))
        self.form.fill(role=r["role"], allocation=r["allocation_pct"])

    def values(self):
        f = self.form
        return (self.picked("project", self.projects, "Izvēlies projektu"),
                self.picked("member", self.members, "Izvēlies dalībnieku"),
                f.get("role"), f.get("allocation"))

    def do_add(self):
        self.db.add_assignment(*self.values())

    def do_save(self, r):
        self.db.update_assignment(r["id"], *self.values())

    def do_delete(self, r):
        self.db.delete_assignment(r["id"])


class ExpensesTab(ProjectPickerTab):
    columns = ("Datums", "Projekts", "Apraksts", "Kategorija", "Summa €", "Rēķināms")
    widths = (95, 200, 220, 120, 80, 80)
    fields = [("project", "Projekts", []), ("description", "Apraksts", None),
              ("category", "Kategorija", None), ("amount", "Summa €", None),
              ("date", "Datums (tukšs = šodien)", None), ("billable", "Rēķināms klientam", ["Nē", "Jā"])]

    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.total = ttk.Label(self.bar, text="")
        self.total.pack(side="right")

    def fetch(self, term):
        return self.db.get_expenses(term)

    def to_values(self, r):
        return (r["spent_on"], r["project_title"], r["description"], r["category"],
                money(r["amount"]), "Jā" if r["billable"] else "Nē")

    def on_refresh(self):
        self.load_projects()
        total = sum(r["amount"] for r in self.records.values())
        self.total.config(text=f"Kopā redzamajiem ierakstiem: {total:.2f} €")

    def fill(self, r):
        self.form.select("project", self.index_of(self.projects, r["project_id"]))
        self.form.fill(description=r["description"], category=r["category"], amount=r["amount"],
                       date=r["spent_on"], billable="Jā" if r["billable"] else "Nē")

    def values(self):
        f = self.form
        return (self.picked("project", self.projects, "Izvēlies projektu"), f.get("description"),
                f.get("category"), f.get("amount"), f.get("date"), f.get("billable"))

    def do_add(self):
        self.db.add_expense(*self.values())

    def do_save(self, r):
        self.db.update_expense(r["id"], *self.values())

    def do_delete(self, r):
        self.db.delete_expense(r["id"])


class InvoicesTab(BaseTab):
    columns = ("Nr.", "Klients", "Projekts", "Statuss", "Summa €", "Apmaksāts €",
               "Atlikums €", "Izrakstīts", "Termiņš", "Kavēts")
    widths = (100, 120, 130, 70, 75, 85, 80, 85, 85, 55)
    fields = [("client", "Klients", []), ("project", "Projekts", []),
              ("number", "Rēķina nr.", None), ("status", "Statuss", INVOICE_STATUSES),
              ("amount", "Summa €", None), ("issued", "Izrakstīts (GGGG-MM-DD)", None),
              ("due", "Apmaksāt līdz", None)]
    filter_values = INVOICE_STATUSES
    delete_warning = "Dzēst rēķinu? (Rēķinu ar maksājumiem dzēst nevar.)"

    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.clients, self.projects = [], []
        self.add_button("Parādi pa klientiem", self.show_balances)
        ttk.Label(self, text="Tukšs rēķina numurs vai tukša summa tiek aizpildīti automātiski "
                  "(summa = stundas × likme + rēķināmie izdevumi).") .pack(anchor="w", padx=6)

    def fetch(self, term):
        return self.db.get_invoices(term, self.filter_value())

    def to_values(self, r):
        return (r["invoice_no"], r["client_name"], r["project_title"], r["status"],
                money(r["amount"]), money(r["paid"]), money(r["balance"]), r["issued_on"],
                r["due_on"], "kavēts" if invoice_overdue(r) else "")

    def on_refresh(self):
        self.clients = self.db.get_clients()
        self.projects = self.db.get_projects()
        self.form.set_values("client", [c["name"] for c in self.clients])
        self.form.set_values("project", [NONE_LABEL] + [project_label(p) for p in self.projects])

    def fill(self, r):
        self.form.select("client", self.index_of(self.clients, r["client_id"]))
        self.form.select("project", self.index_of(self.projects, r["project_id"]) + 1)
        self.form.fill(number=r["invoice_no"], status=r["status"], amount=r["amount"],
                       issued=r["issued_on"], due=r["due_on"])

    def values(self):
        f = self.form
        return (self.picked("client", self.clients, "Izvēlies klientu"),
                self.optional("project", self.projects), f.get("number"), f.get("status"),
                f.get("amount"), f.get("issued"), f.get("due"))

    def do_add(self):
        self.db.add_invoice(*self.values())

    def do_save(self, r):
        self.db.update_invoice(r["id"], *self.values())

    def do_delete(self, r):
        self.db.delete_invoice(r["id"])

    def show_balances(self):
        messagebox.showinfo("Parādi pa klientiem",
                            format_client_balances(self.db.get_client_balances()))


class PaymentsTab(BaseTab):
    columns = ("Rēķins", "Klients", "Datums", "Summa €", "Metode", "Atsauce")
    widths = (110, 160, 95, 90, 150, 250)
    fields = [("invoice", "Rēķins", []), ("amount", "Summa €", None),
              ("date", "Datums (tukšs = šodien)", None), ("method", "Metode", None),
              ("reference", "Atsauce", None)]

    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.invoices = []

    def fetch(self, term):
        return self.db.get_payments(term)

    def to_values(self, r):
        return (r["invoice_no"], r["client_name"], r["paid_on"], money(r["amount"]),
                r["method"], r["reference"])

    def on_refresh(self):
        self.invoices = self.db.get_invoices()
        self.form.set_values("invoice", [
            f"{i['invoice_no']} ({i['client_name']}) – atlikums {i['balance']:.2f} €"
            for i in self.invoices])

    def fill(self, r):
        self.form.select("invoice", self.index_of(self.invoices, r["invoice_id"]))
        self.form.fill(amount=r["amount"], date=r["paid_on"], method=r["method"],
                       reference=r["reference"])

    def values(self):
        f = self.form
        return (self.picked("invoice", self.invoices, "Izvēlies rēķinu"), f.get("amount"),
                f.get("date"), f.get("method"), f.get("reference"))

    def do_add(self):
        self.db.add_payment(*self.values())

    def do_save(self, r):
        self.db.update_payment(r["id"], *self.values())

    def do_delete(self, r):
        self.db.delete_payment(r["id"])


class App(tk.Tk):
    TABS = [("Klienti", ClientsTab), ("Projekti", ProjectsTab),
            ("Nododamie", DeliverablesTab), ("Laiks", TimeTab), ("Krāsas", ColorsTab),
            ("Komanda", MembersTab), ("Piešķīrumi", AssignmentsTab),
            ("Izdevumi", ExpensesTab), ("Rēķini", InvoicesTab), ("Maksājumi", PaymentsTab)]

    def __init__(self):
        super().__init__()
        self.title("Dizaina projektu pārvaldnieks")
        self.geometry("1020x760")
        self.db = Database()

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)
        self.tabs = []
        for title, cls in self.TABS:
            tab = cls(notebook, self)
            notebook.add(tab, text=title)
            self.tabs.append(tab)

        self.protocol("WM_DELETE_WINDOW", self.close)
        self.refresh_all()

    def refresh_all(self):
        for tab in self.tabs:
            tab.refresh()

    def close(self):
        self.db.close()
        self.destroy()


if __name__ == "__main__":
    App().mainloop()


"""Schema for drawDB / diagram tools"""

"""""""""""""""""""""""""""""""""""""""""""""""

CREATE TABLE IF NOT EXISTS "clients" (
    "id" INTEGER,
    "name" TEXT NOT NULL,
    "email" TEXT,
    "hourly_rate" REAL NOT NULL DEFAULT 25,
    PRIMARY KEY("id")
);

CREATE TABLE IF NOT EXISTS "projects" (
    "id" INTEGER,
    "client_id" INTEGER NOT NULL,
    "title" TEXT NOT NULL,
    "type" TEXT,
    "status" TEXT NOT NULL DEFAULT 'Jauns',
    "deadline" TEXT,
    "budget_hours" REAL NOT NULL DEFAULT 20,
    PRIMARY KEY("id"),
    FOREIGN KEY ("client_id") REFERENCES "clients"("id")
    ON UPDATE NO ACTION ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS "deliverables" (
    "id" INTEGER,
    "project_id" INTEGER NOT NULL,
    "name" TEXT NOT NULL,
    "format" TEXT,
    "done" INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY("id"),
    FOREIGN KEY ("project_id") REFERENCES "projects"("id")
    ON UPDATE NO ACTION ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS "activities" (
    "id" INTEGER,
    "name" TEXT NOT NULL UNIQUE,
    PRIMARY KEY("id")
);

CREATE TABLE IF NOT EXISTS "team_members" (
    "id" INTEGER NOT NULL,
    "name" TEXT NOT NULL,
    "email" TEXT UNIQUE,
    "role" TEXT,
    "cost_rate" REAL,
    PRIMARY KEY("id")
);

CREATE TABLE IF NOT EXISTS "time_logs" (
    "id" INTEGER,
    "project_id" INTEGER NOT NULL,
    "activity_id" INTEGER NOT NULL,
    "work_date" TEXT NOT NULL,
    "hours" REAL NOT NULL,
    "note" TEXT,
    "member_id" INTEGER,
    PRIMARY KEY("id"),
    FOREIGN KEY ("project_id") REFERENCES "projects"("id")
    ON UPDATE NO ACTION ON DELETE CASCADE,
    FOREIGN KEY ("activity_id") REFERENCES "activities"("id")
    ON UPDATE NO ACTION ON DELETE NO ACTION,
    FOREIGN KEY ("member_id") REFERENCES "team_members"("id")
    ON UPDATE NO ACTION ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS "palette_colors" (
    "id" INTEGER,
    "project_id" INTEGER NOT NULL,
    "name" TEXT NOT NULL,
    "hex" TEXT NOT NULL,
    PRIMARY KEY("id"),
    FOREIGN KEY ("project_id") REFERENCES "projects"("id")
    ON UPDATE NO ACTION ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS "revision_logs" (
    "id" INTEGER,
    "project_id" INTEGER NOT NULL,
    "rev_date" TEXT NOT NULL,
    "round_no" INTEGER NOT NULL,
    "note" TEXT,
    PRIMARY KEY("id"),
    FOREIGN KEY ("project_id") REFERENCES "projects"("id")
    ON UPDATE NO ACTION ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS "invoices" (
    "id" INTEGER NOT NULL,
    "client_id" INTEGER NOT NULL,
    "project_id" INTEGER,
    "invoice_no" TEXT NOT NULL UNIQUE,
    "status" TEXT NOT NULL DEFAULT 'draft',
    "amount" REAL NOT NULL,
    "issued_on" TEXT,
    "due_on" TEXT,
    PRIMARY KEY("id"),
    FOREIGN KEY ("client_id") REFERENCES "clients"("id")
    ON UPDATE NO ACTION ON DELETE NO ACTION,
    FOREIGN KEY ("project_id") REFERENCES "projects"("id")
    ON UPDATE NO ACTION ON DELETE NO ACTION
);

CREATE TABLE IF NOT EXISTS "payments" (
    "id" INTEGER NOT NULL,
    "invoice_id" INTEGER NOT NULL,
    "amount" REAL NOT NULL,
    "paid_on" TEXT NOT NULL,
    "method" TEXT,
    "reference" TEXT,
    PRIMARY KEY("id"),
    FOREIGN KEY ("invoice_id") REFERENCES "invoices"("id")
    ON UPDATE NO ACTION ON DELETE NO ACTION
);

CREATE TABLE IF NOT EXISTS "expenses" (
    "id" INTEGER NOT NULL,
    "project_id" INTEGER NOT NULL,
    "description" TEXT NOT NULL,
    "category" TEXT,
    "amount" REAL NOT NULL,
    "spent_on" TEXT NOT NULL,
    "billable" INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY("id"),
    FOREIGN KEY ("project_id") REFERENCES "projects"("id")
    ON UPDATE NO ACTION ON DELETE NO ACTION
);

CREATE TABLE IF NOT EXISTS "project_members" (
    "id" INTEGER NOT NULL,
    "project_id" INTEGER NOT NULL,
    "member_id" INTEGER NOT NULL,
    "role" TEXT,
    "allocation_pct" REAL,
    PRIMARY KEY("id"),
    UNIQUE("project_id", "member_id"),
    FOREIGN KEY ("project_id") REFERENCES "projects"("id")
    ON UPDATE NO ACTION ON DELETE CASCADE,
    FOREIGN KEY ("member_id") REFERENCES "team_members"("id")
    ON UPDATE NO ACTION ON DELETE CASCADE
);

"""""""""""""""""""""""""""""""""""""""""""""""


""""""""""""""""""""""""""""""""""""""""

"""Konsoles versija. Izmanto to pašu datubāzes slāni (database.py) kā grafiskais logs."""
import sqlite3

from database import (INVOICE_STATUSES, STATUSES, Database, format_client_balances,
                      format_project_summary, invoice_overdue)


def ask(label, default=""):
    shown = f" [{default}]" if default not in (None, "") else ""
    value = input(f"{label}{shown}: ").strip()
    return value if value else ("" if default is None else str(default))


def print_rows(rows, describe):
    for row in rows:
        print(f"  [{row['id']}] {describe(row)}")


def choose(rows, describe, current=None):
    if not rows:
        raise ValueError("Nav ierakstu, ko izvēlēties")
    print_rows(rows, describe)
    by_id = {row["id"]: row for row in rows}
    text = input(f"ID{f' [{current}]' if current else ''}: ").strip()
    if text == "" and current in by_id:
        return by_id[current]
    try:
        return by_id[int(text)]
    except (ValueError, KeyError):
        raise ValueError("Nepareizs ID")


def choose_optional(rows, describe, current=None):
    if not rows:
        return None
    print_rows(rows, describe)
    by_id = {row["id"]: row for row in rows}
    text = input("ID (Enter = " + ("paturēt" if current else "nav") + ", 0 = nav): ").strip()
    if text == "":
        return by_id.get(current)
    if text == "0":
        return None
    try:
        return by_id[int(text)]
    except (ValueError, KeyError):
        raise ValueError("Nepareizs ID")


def show(rows, describe):
    print_rows(rows, describe) if rows else print("Nekas nav atrasts.")


def crud_menu(title, list_fn, describe, add_fn, edit_fn, delete_fn, extra=None):
    extra = extra or {}
    while True:
        print(f"\n--- {title} ---")
        print("1 Skatīt / meklēt   2 Pievienot   3 Labot   4 Dzēst")
        for key, (name, _) in extra.items():
            print(f"{key} {name}")
        print("0 Atpakaļ")
        choice = input("> ").strip()
        if choice == "0":
            return
        try:
            if choice == "1":
                show(list_fn(input("Meklēt (Enter = rādīt visu): ").strip()), describe)
            elif choice == "2":
                add_fn()
                print("Pievienots.")
            elif choice == "3":
                edit_fn(choose(list_fn(""), describe))
                print("Saglabāts.")
            elif choice == "4":
                row = choose(list_fn(""), describe)
                if input(f"Tiešām dzēst «{describe(row)}»? (j/n): ").lower() == "j":
                    delete_fn(row)
                    print("Izdzēsts.")
            elif choice in extra:
                extra[choice][1]()
            else:
                print("Nezināma izvēle.")
        except (ValueError, sqlite3.Error) as error:
            print("Kļūda:", error)


def d_client(c):
    return f"{c['name']} | {c['email'] or '-'} | {c['hourly_rate']:g} €/h"


def d_project(p):
    return (f"{p['title']} ({p['client_name']}) | {p['status']} | "
            f"termiņš {p['deadline'] or '-'} | {p['spent']:g}/{p['budget_hours']:g} h")


def d_deliverable(d):
    return f"{'[x]' if d['done'] else '[ ]'} {d['name']} | {d['format'] or '-'} | {d['project_title']}"


def d_time(t):
    return (f"{t['work_date']} | {t['project_title']} | {t['activity']} | "
            f"{t['member_name'] or '-'} | {t['hours']:g} h | {t['note'] or ''}")


def d_color(k):
    return f"{k['name']} {k['hex']} | {k['project_title']}"


def d_member(m):
    cost = f"{m['cost_rate']:g} €/h" if m["cost_rate"] is not None else "-"
    return f"{m['name']} | {m['email'] or '-'} | {m['role'] or '-'} | {cost}"


def d_assignment(a):
    pct = f"{a['allocation_pct']:g} %" if a["allocation_pct"] is not None else "-"
    return f"{a['member_name']} → {a['project_title']} | {a['role'] or '-'} | {pct}"


def d_expense(e):
    return (f"{e['spent_on']} | {e['project_title']} | {e['description']} | "
            f"{e['amount']:.2f} € | {'rēķināms' if e['billable'] else 'nerēķināms'}")


def d_invoice(i):
    late = " KAVĒTS" if invoice_overdue(i) else ""
    return (f"{i['invoice_no']} | {i['client_name']} | {i['status']} | {i['amount']:.2f} € "
            f"(atlikums {i['balance']:.2f} €){late}")


def d_payment(p):
    return f"{p['paid_on']} | {p['invoice_no']} ({p['client_name']}) | {p['amount']:.2f} € | {p['method'] or '-'}"


def pick_project(db, current=None):
    return choose(db.get_projects(), d_project, current)["id"]


def pick_member(db, current=None):
    return choose(db.get_members(), d_member, current)["id"]


def clients_menu(db):
    crud_menu(
        "KLIENTI", db.get_clients, d_client,
        lambda: db.add_client(ask("Vārds"), ask("E-pasts"), ask("Likme €/h", 25)),
        lambda c: db.update_client(c["id"], ask("Vārds", c["name"]),
                                   ask("E-pasts", c["email"]), ask("Likme €/h", c["hourly_rate"])),
        lambda c: db.delete_client(c["id"]))


def projects_menu(db):
    def add():
        client = choose(db.get_clients(), d_client)
        db.add_project(client["id"], ask("Nosaukums"), ask("Veids (logo, plakāts...)"),
                       ask(f"Statuss ({', '.join(STATUSES)})", STATUSES[0]),
                       ask("Termiņš (GGGG-MM-DD)"), ask("Plānotās stundas", 20))

    def edit(p):
        client = choose(db.get_clients(), d_client, p["client_id"])
        db.update_project(p["id"], client["id"], ask("Nosaukums", p["title"]),
                          ask("Veids", p["type"]), ask("Statuss", p["status"]),
                          ask("Termiņš", p["deadline"]), ask("Plānotās stundas", p["budget_hours"]))

    def summary():
        project = choose(db.get_projects(), d_project)
        print(f"\n{project['title']}\n" + format_project_summary(db.project_summary(project["id"])))

    def revision():
        db.add_revision(pick_project(db), ask("Piezīme"))
        print("Labojumu kārta reģistrēta.")

    crud_menu("PROJEKTI", db.get_projects, d_project, add, edit,
              lambda p: db.delete_project(p["id"]),
              extra={"5": ("Projekta kopsavilkums", summary), "6": ("+ Labojumu kārta", revision)})


def deliverables_menu(db):
    def toggle():
        db.toggle_deliverable(choose(db.get_deliverables(""), d_deliverable)["id"])
        print("Statuss nomainīts.")

    crud_menu(
        "NODODAMIE DARBI", db.get_deliverables, d_deliverable,
        lambda: db.add_deliverable(pick_project(db), ask("Nosaukums"), ask("Formāts (PNG, PDF...)")),
        lambda d: db.update_deliverable(d["id"], pick_project(db, d["project_id"]),
                                        ask("Nosaukums", d["name"]), ask("Formāts", d["format"])),
        lambda d: db.delete_deliverable(d["id"]),
        extra={"5": ("Gatavs / nav gatavs", toggle)})


def time_menu(db):
    def activity(current=None):
        return choose(db.get_activities(), lambda a: a["name"], current)["id"]

    def member_id(current=None):
        member = choose_optional(db.get_members(), d_member, current)
        return member["id"] if member else None

    crud_menu(
        "LAIKA UZSKAITE", db.get_time_logs, d_time,
        lambda: db.add_time(pick_project(db), activity(), ask("Datums (Enter = šodien)"),
                            ask("Stundas"), ask("Piezīme"), member_id()),
        lambda t: db.update_time(t["id"], pick_project(db, t["project_id"]),
                                 activity(t["activity_id"]), ask("Datums", t["work_date"]),
                                 ask("Stundas", t["hours"]), ask("Piezīme", t["note"]),
                                 member_id(t["member_id"])),
        lambda t: db.delete_time(t["id"]))


def colors_menu(db):
    crud_menu(
        "KRĀSU PALETE", db.get_colors, d_color,
        lambda: db.add_color(pick_project(db), ask("Krāsas nosaukums"), ask("HEX (#RRGGBB)")),
        lambda k: db.update_color(k["id"], pick_project(db, k["project_id"]),
                                  ask("Nosaukums", k["name"]), ask("HEX", k["hex"])),
        lambda k: db.delete_color(k["id"]))


def members_menu(db):
    crud_menu(
        "KOMANDA", db.get_members, d_member,
        lambda: db.add_member(ask("Vārds"), ask("E-pasts"), ask("Loma"), ask("Pašizmaksa €/h")),
        lambda m: db.update_member(m["id"], ask("Vārds", m["name"]), ask("E-pasts", m["email"]),
                                   ask("Loma", m["role"]), ask("Pašizmaksa €/h", m["cost_rate"])),
        lambda m: db.delete_member(m["id"]))


def assignments_menu(db):
    crud_menu(
        "PROJEKTA KOMANDA (PIEŠĶĪRUMI)", db.get_assignments, d_assignment,
        lambda: db.add_assignment(pick_project(db), pick_member(db), ask("Loma projektā"),
                                  ask("Noslodze % (0-100)")),
        lambda a: db.update_assignment(a["id"], pick_project(db, a["project_id"]),
                                       pick_member(db, a["member_id"]),
                                       ask("Loma projektā", a["role"]),
                                       ask("Noslodze %", a["allocation_pct"])),
        lambda a: db.delete_assignment(a["id"]))


def expenses_menu(db):
    crud_menu(
        "IZDEVUMI", db.get_expenses, d_expense,
        lambda: db.add_expense(pick_project(db), ask("Apraksts"), ask("Kategorija"), ask("Summa €"),
                               ask("Datums (Enter = šodien)"), ask("Rēķināms klientam (j/n)")),
        lambda e: db.update_expense(e["id"], pick_project(db, e["project_id"]),
                                    ask("Apraksts", e["description"]), ask("Kategorija", e["category"]),
                                    ask("Summa €", e["amount"]), ask("Datums", e["spent_on"]),
                                    ask("Rēķināms (j/n)", "j" if e["billable"] else "n")),
        lambda e: db.delete_expense(e["id"]))


def invoices_menu(db):
    def client_projects(client):
        return [p for p in db.get_projects() if p["client_id"] == client["id"]]

    def add():
        client = choose(db.get_clients(), d_client)
        project = choose_optional(client_projects(client), d_project)
        db.add_invoice(client["id"], project["id"] if project else None,
                       ask("Rēķina nr. (Enter = automātiski)"),
                       ask(f"Statuss ({', '.join(INVOICE_STATUSES)})", "draft"),
                       ask("Summa € (Enter = aprēķināt no projekta)"),
                       ask("Izrakstīšanas datums (GGGG-MM-DD)"), ask("Apmaksāt līdz (GGGG-MM-DD)"))

    def edit(i):
        client = choose(db.get_clients(), d_client, i["client_id"])
        project = choose_optional(client_projects(client), d_project, i["project_id"])
        db.update_invoice(i["id"], client["id"], project["id"] if project else None,
                          ask("Rēķina nr.", i["invoice_no"]), ask("Statuss", i["status"]),
                          ask("Summa €", i["amount"]), ask("Izrakstīts", i["issued_on"]),
                          ask("Apmaksāt līdz", i["due_on"]))

    crud_menu("RĒĶINI", db.get_invoices, d_invoice, add, edit, lambda i: db.delete_invoice(i["id"]),
              extra={"5": ("Parādi pa klientiem",
                           lambda: print(format_client_balances(db.get_client_balances())) )})


def payments_menu(db):
    def invoice():
        return choose(db.get_invoices(), d_invoice)

    crud_menu(
        "MAKSĀJUMI", db.get_payments, d_payment,
        lambda: db.add_payment(invoice()["id"], ask("Summa €"), ask("Datums (Enter = šodien)"),
                               ask("Metode"), ask("Atsauce")),
        lambda p: db.update_payment(p["id"], choose(db.get_invoices(), d_invoice, p["invoice_id"])["id"],
                                    ask("Summa €", p["amount"]), ask("Datums", p["paid_on"]),
                                    ask("Metode", p["method"]), ask("Atsauce", p["reference"])),
        lambda p: db.delete_payment(p["id"]))


def main():
    menus = {"1": clients_menu, "2": projects_menu, "3": deliverables_menu, "4": time_menu,
             "5": colors_menu, "6": members_menu, "7": assignments_menu,
             "8": expenses_menu, "9": invoices_menu, "10": payments_menu}
    with Database() as db:
        while True:
            print("\n=== DIZAINA PROJEKTU PĀRVALDNIEKS ===")
            print("1 Klienti   2 Projekti   3 Nododamie   4 Laiks   5 Krāsas")
            print("6 Komanda   7 Piešķīrumi   8 Izdevumi   9 Rēķini   10 Maksājumi   0 Iziet")
            choice = input("> ").strip()
            if choice == "0":
                break
            if choice in menus:
                menus[choice](db)
            else:
                print("Nezināma izvēle.")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nPrograma aizvērta.")


"""Schema for drawDB / diagram tools"""

"""""""""""""""""""""""""""""""""""""""""""""""

CREATE TABLE IF NOT EXISTS "clients" (
    "id" INTEGER,
    "name" TEXT NOT NULL,
    "email" TEXT,
    "hourly_rate" REAL NOT NULL DEFAULT 25,
    PRIMARY KEY("id")
);

CREATE TABLE IF NOT EXISTS "projects" (
    "id" INTEGER,
    "client_id" INTEGER NOT NULL,
    "title" TEXT NOT NULL,
    "type" TEXT,
    "status" TEXT NOT NULL DEFAULT 'Jauns',
    "deadline" TEXT,
    "budget_hours" REAL NOT NULL DEFAULT 20,
    PRIMARY KEY("id"),
    FOREIGN KEY ("client_id") REFERENCES "clients"("id")
    ON UPDATE NO ACTION ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS "deliverables" (
    "id" INTEGER,
    "project_id" INTEGER NOT NULL,
    "name" TEXT NOT NULL,
    "format" TEXT,
    "done" INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY("id"),
    FOREIGN KEY ("project_id") REFERENCES "projects"("id")
    ON UPDATE NO ACTION ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS "activities" (
    "id" INTEGER,
    "name" TEXT NOT NULL UNIQUE,
    PRIMARY KEY("id")
);

CREATE TABLE IF NOT EXISTS "team_members" (
    "id" INTEGER NOT NULL,
    "name" TEXT NOT NULL,
    "email" TEXT UNIQUE,
    "role" TEXT,
    "cost_rate" REAL,
    PRIMARY KEY("id")
);

CREATE TABLE IF NOT EXISTS "time_logs" (
    "id" INTEGER,
    "project_id" INTEGER NOT NULL,
    "activity_id" INTEGER NOT NULL,
    "work_date" TEXT NOT NULL,
    "hours" REAL NOT NULL,
    "note" TEXT,
    "member_id" INTEGER,
    PRIMARY KEY("id"),
    FOREIGN KEY ("project_id") REFERENCES "projects"("id")
    ON UPDATE NO ACTION ON DELETE CASCADE,
    FOREIGN KEY ("activity_id") REFERENCES "activities"("id")
    ON UPDATE NO ACTION ON DELETE NO ACTION,
    FOREIGN KEY ("member_id") REFERENCES "team_members"("id")
    ON UPDATE NO ACTION ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS "palette_colors" (
    "id" INTEGER,
    "project_id" INTEGER NOT NULL,
    "name" TEXT NOT NULL,
    "hex" TEXT NOT NULL,
    PRIMARY KEY("id"),
    FOREIGN KEY ("project_id") REFERENCES "projects"("id")
    ON UPDATE NO ACTION ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS "revision_logs" (
    "id" INTEGER,
    "project_id" INTEGER NOT NULL,
    "rev_date" TEXT NOT NULL,
    "round_no" INTEGER NOT NULL,
    "note" TEXT,
    PRIMARY KEY("id"),
    FOREIGN KEY ("project_id") REFERENCES "projects"("id")
    ON UPDATE NO ACTION ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS "invoices" (
    "id" INTEGER NOT NULL,
    "client_id" INTEGER NOT NULL,
    "project_id" INTEGER,
    "invoice_no" TEXT NOT NULL UNIQUE,
    "status" TEXT NOT NULL DEFAULT 'draft',
    "amount" REAL NOT NULL,
    "issued_on" TEXT,
    "due_on" TEXT,
    PRIMARY KEY("id"),
    FOREIGN KEY ("client_id") REFERENCES "clients"("id")
    ON UPDATE NO ACTION ON DELETE NO ACTION,
    FOREIGN KEY ("project_id") REFERENCES "projects"("id")
    ON UPDATE NO ACTION ON DELETE NO ACTION
);

CREATE TABLE IF NOT EXISTS "payments" (
    "id" INTEGER NOT NULL,
    "invoice_id" INTEGER NOT NULL,
    "amount" REAL NOT NULL,
    "paid_on" TEXT NOT NULL,
    "method" TEXT,
    "reference" TEXT,
    PRIMARY KEY("id"),
    FOREIGN KEY ("invoice_id") REFERENCES "invoices"("id")
    ON UPDATE NO ACTION ON DELETE NO ACTION
);

CREATE TABLE IF NOT EXISTS "expenses" (
    "id" INTEGER NOT NULL,
    "project_id" INTEGER NOT NULL,
    "description" TEXT NOT NULL,
    "category" TEXT,
    "amount" REAL NOT NULL,
    "spent_on" TEXT NOT NULL,
    "billable" INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY("id"),
    FOREIGN KEY ("project_id") REFERENCES "projects"("id")
    ON UPDATE NO ACTION ON DELETE NO ACTION
);

CREATE TABLE IF NOT EXISTS "project_members" (
    "id" INTEGER NOT NULL,
    "project_id" INTEGER NOT NULL,
    "member_id" INTEGER NOT NULL,
    "role" TEXT,
    "allocation_pct" REAL,
    PRIMARY KEY("id"),
    UNIQUE("project_id", "member_id"),
    FOREIGN KEY ("project_id") REFERENCES "projects"("id")
    ON UPDATE NO ACTION ON DELETE CASCADE,
    FOREIGN KEY ("member_id") REFERENCES "team_members"("id")
    ON UPDATE NO ACTION ON DELETE CASCADE
);

"""""""""""""""""""""""""""""""""""""""""""""""

