from database import Database

db = Database()


def pick(rows, label):
    for r in rows:
        print(f"  [{r['id']}] {r[label]}")
    return int(input("ID: "))


def menu():
    while True:
        print("\n=== DIZAINA PROJEKTU PĀRVALDNIEKS ===")
        print("1 Pievienot klientu    2 Pievienot projektu   3 Reģistrēt laiku")
        print("4 Pievienot krāsu      5 Reģistrēt labojumu   6 Projekta kopsavilkums")
        print("0 Iziet")
        c = input("> ").strip()
        if c == "1":
            db.add_client(input("Vārds: "), input("E-pasts: "), float(input("Likme €/h: ")))
        elif c == "2":
            cid = pick(db.get_clients(), "name")
            db.add_project(cid, input("Nosaukums: "), input("Veids (logo, plakāts...): "),
                           input("Termiņš (GGGG-MM-DD): "), float(input("Plānotās stundas: ")))
        elif c == "3":
            pid = pick(db.get_projects(), "title")
            aid = pick(db.get_activities(), "name")
            db.add_time(pid, aid, float(input("Stundas: ")), input("Piezīme: "))
        elif c == "4":
            pid = pick(db.get_projects(), "title")
            db.add_color(pid, input("Nosaukums: "), input("HEX (#RRGGBB): "))
        elif c == "5":
            pid = pick(db.get_projects(), "title")
            db.add_revision(pid, input("Piezīme: "))
        elif c == "6":
            s = db.project_summary(pick(db.get_projects(), "title"))
            print(f"\n{s['title']}: {s['spent']:.1f}/{s['budget']:.1f} h, "
                  f"atlicis {s['left']:.1f} h, nopelnīts {s['earned']:.2f} €")
        elif c == "0":
            break


if __name__ == "__main__":
    menu()
