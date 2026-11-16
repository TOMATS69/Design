# Dizaina projektu pārvaldnieks

Vienkārša Python darbvirsmas lietotne dizaina klientu, projektu un saistīto datu pārvaldībai. Lietotne izmanto Tkinter grafiskajam interfeisam un SQLite datu glabāšanai. Saskarne pieejama latviešu valodā.

## Iespējas

- Pārskatīt un pārvaldīt klientus un projektus.
- Pārvaldīt nodevumus, darbības, komandas locekļus, laika ierakstus, krāsu paletes un labojumu vēsturi.
- Pievienot, labot un dzēst ierakstus grafiskajā saskarnē.
- Meklēt sadaļas un filtrēt tabulas ierakstus.
- Saglabāt datus lokālā SQLite datubāzē.

## Prasības

- Python 3
- Tkinter
- SQLite

Tkinter un SQLite parasti ir iekļauti Python instalācijā. Linux sistēmā, ja Tkinter nav pieejams, instalējiet to, piemēram, ar:

```bash
sudo apt install python3-tk
```

## Instalēšana un palaišana

1. Klonējiet repozitoriju:

   ```bash
   git clone https://github.com/TOMATS69/Design.git
   cd Design
   ```

2. Palaidiet grafisko lietotni:

   ```bash
   python main.py
   ```

Nav nepieciešams instalēt papildu Python pakotnes.

## Lietošana

Lietotnes kreisajā izvēlnē izvēlieties sadaļu. Izmantojiet ievades laukus, lai pievienotu vai labotu ierakstu, un darbību pogas, lai saglabātu izmaiņas, dzēstu vai notīrītu laukus. Tabulas meklēšanas lauks ļauj ātri atrast ierakstus.

Palaižot lietotni, projekta mapē automātiski tiek izveidots `design_tracker.db` SQLite datubāzes fails.

## Projekta faili

- `main.py` — palaiž grafisko lietotni.
- `ui.py` — Tkinter saskarne un lietotāja darbības.
- `database.py` — SQLite datubāzes piekļuve un datu loģika.
- `schema.sql` — datubāzes shēma.
- `terminal.py` — komandrindas versijas palaišanas fails.

## Ieguldījumi

Ieteikumus un kļūdu ziņojumus var iesniegt GitHub repozitorija [Issues](https://github.com/TOMATS69/Design/issues) sadaļā. Koda izmaiņām izveidojiet atsevišķu atzaru un iesniedziet pull request ar īsu izmaiņu aprakstu.

## Licence

Šobrīd repozitorijā nav norādīts licences fails. Pirms koda izmantošanas vai izplatīšanas pārbaudiet ar autoru, kādi lietošanas nosacījumi ir spēkā.

## Kontakti

Jautājumiem vai ieteikumiem sazinieties ar repozitorija uzturētāju, izmantojot GitHub profilu [@TOMATS69](https://github.com/TOMATS69).
