# Dizaina projektu pārvaldnieks

Vienkārša Python darbvirsmas lietotne dizaina klientu un projektu pārvaldībai. Grafiskajā lietotnē ievades lauki atrodas virs tabulas.

## Palaide

Nepieciešams Python 3 ar Tkinter un SQLite (parasti iekļauti Python instalācijā).

```bash
python main.py
```

Linux sistēmā, ja Tkinter nav pieejams, instalē to ar `sudo apt install python3-tk`.

## Faili

- `main.py` — palaiž grafisko lietotni.
- `ui.py` — Tkinter logi, formas un tabulas.
- `database.py` — SQLite datubāze, ievades pārbaude un datu saglabāšana.
- `schema.sql` — datubāzes tabulu shēma.
- `terminal.py` — vienkāršā komandrindas versija.

Datubāzes fails `design_tracker.db` tiek izveidots automātiski projekta mapē.
