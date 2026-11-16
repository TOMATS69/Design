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

