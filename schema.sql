from database import Database


def print_menu():
    print("\n=== Dizaina projektu pārvaldnieks ===")
    print("1. Klienti")
    print("2. Projekti")
    print("3. Laika uzskaite")
    print("4. Krāsas")
    print("0. Iziet")


def main():
    db = Database()
    while True:
        print_menu()
        choice = input("Izvēle: ").strip()

        if choice == "0":
            break
        elif choice == "1":
            show_clients(db)
        elif choice == "2":
            show_projects(db)
        elif choice == "3":
            show_time(db)
        elif choice == "4":
            show_colors(db)
        else:
            print("Nepareiza izvēle.")

    db.close()


def show_clients(db):
    while True:
        print("\nKlienti")
        print("1. Pievienot")
        print("2. Skatīt")
        print("0. Atpakaļ")
        choice = input("Izvēle: ").strip()

        if choice == "0":
            break
        elif choice == "1":
            name = input("Vārds: ").strip()
            email = input("E-pasts: ").strip()
            rate = input("Likme €/h (25): ").strip() or "25"
            db.add_client(name, email, rate)
        elif choice == "2":
            for client in db.list_clients():
                print(f"[{client['id']}] {client['name']} | {client['email']} | {client['hourly_rate']:.2f} €/h")


def show_projects(db):
    while True:
        print("\nProjekti")
        print("1. Pievienot")
        print("2. Skatīt")
        print("0. Atpakaļ")
        choice = input("Izvēle: ").strip()

        if choice == "0":
            break
        elif choice == "1":
            clients = db.list_clients()
            if not clients:
                print("Vispirms pievieno klientu.")
                continue
            for client in clients:
                print(f"[{client['id']}] {client['name']}")
            client_id = int(input("Klienta ID: "))
            title = input("Nosaukums: ").strip()
            ptype = input("Veids: ").strip()
            status = input("Statuss (Jauns): ").strip() or "Jauns"
            deadline = input("Termiņš (GGGG-MM-DD): ").strip()
            budget = input("Plānotās stundas (20): ").strip() or "20"
            db.add_project(client_id, title, ptype, status, deadline, budget)
        elif choice == "2":
            for project in db.list_projects():
                print(f"[{project['id']}] {project['title']} | {project['client_name']} | {project['status']}")


def show_time(db):
    while True:
        print("\nLaika uzskaite")
        print("1. Pievienot")
        print("2. Skatīt")
        print("0. Atpakaļ")
        choice = input("Izvēle: ").strip()

        if choice == "0":
            break
        elif choice == "1":
            projects = db.list_projects()
            if not projects:
                print("Vispirms pievieno projektu.")
                continue
            for project in projects:
                print(f"[{project['id']}] {project['title']}")
            project_id = int(input("Projekta ID: "))
            for activity in db.get_activities():
                print(f"[{activity['id']}] {activity['name']}")
            activity_id = int(input("Darbības ID: "))
            work_date = input("Datums (YYYY-MM-DD): ").strip()
            hours = input("Stundas: ").strip()
            note = input("Piezīme: ").strip()
            db.add_time_entry(project_id, activity_id, work_date, hours, note)
        elif choice == "2":
            for entry in db.list_time_entries():
                print(f"[{entry['id']}] {entry['project_title']} | {entry['activity_name']} | {entry['hours']} h | {entry['note']}")


def show_colors(db):
    while True:
        print("\nKrāsas")
        print("1. Pievienot")
        print("2. Skatīt")
        print("0. Atpakaļ")
        choice = input("Izvēle: ").strip()

        if choice == "0":
            break
        elif choice == "1":
            projects = db.list_projects()
            if not projects:
                print("Vispirms pievieno projektu.")
                continue
            for project in projects:
                print(f"[{project['id']}] {project['title']}")
            project_id = int(input("Projekta ID: "))
            name = input("Krāsas nosaukums: ").strip()
            hex_code = input("HEX (#RRGGBB): ").strip()
            db.add_color(project_id, name, hex_code)
        elif choice == "2":
            for color in db.list_colors():
                print(f"[{color['id']}] {color['project_title']} | {color['name']} | {color['hex']}")


if __name__ == "__main__":
    main()
