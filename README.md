# Dizaina projektu pārvaldnieks

Python darbvirsmas lietotne dizaina klientu un projektu informācijas pārvaldībai. Lietotne izmanto **Tkinter** grafiskajai saskarnei un **SQLite** lokālai datu glabāšanai.

## Iespējas

- Pārvaldīt klientus un projektus.
- Pārskatīt un rediģēt ar projektiem saistītos datus: nodevumus, darbības, komandas locekļus, laika ierakstus, krāsu paletes un labojumu vēsturi.
- Pievienot, labot un dzēst ierakstus grafiskajā saskarnē.
- Meklēt sadaļas un filtrēt tabulas ierakstus.
- Glabāt datus lokālā SQLite datubāzē.

## Prasības

- Python 3
- Tkinter
- SQLite

Tkinter un SQLite parasti ir iekļauti Python instalācijā. Linux sistēmā, ja Tkinter nav pieejams, instalējiet to, piemēram, ar:

```bash
sudo apt install python3-tk
```

## Instalēšana

1. Klonējiet repozitoriju:

   ```bash
   git clone https://github.com/TOMATS69/Design.git
   ```

2. Atveriet projekta mapi:

   ```bash
   cd Design
   ```

3. Palaidiet lietotni:

   ```bash
   python main.py
   ```

Papildu Python pakotnes nav nepieciešamas.

## Lietošana

Lietotnes kreisajā izvēlnē izvēlieties datu sadaļu. Lai pievienotu ierakstu, aizpildiet laukus un nospiediet **Pievienot ierakstu**. Lai labotu vai dzēstu ierakstu, vispirms izvēlieties to tabulā. Izmantojiet meklēšanas lauku, lai filtrētu attēlotos ierakstus.

Datubāzes fails `design_tracker.db` tiek izveidots automātiski projekta mapē, palaižot lietotni.

## Projekta struktūra

| Fails | Apraksts |
| --- | --- |
| `main.py` | Palaiž grafisko lietotni. |
| `ui.py` | Tkinter saskarne un lietotāja darbības. |
| `database.py` | SQLite datubāzes piekļuve un datu loģika. |
| `schema.sql` | Datubāzes shēma. |
| `terminal.py` | Komandrindas versijas palaišanas fails. |

## Ieguldījumi

Ieteikumus un kļūdu ziņojumus var iesniegt [GitHub Issues](https://github.com/TOMATS69/Design/issues) sadaļā. Koda izmaiņām izveidojiet atsevišķu atzaru un iesniedziet pull request ar īsu izmaiņu aprakstu.

Pirms iesniegšanas pārliecinieties, ka:

- [ ] Lietotne palaižas ar `python main.py`.
- [ ] Izmaiņas ir pārbaudītas attiecīgajās lietotnes sadaļās.
- [ ] Pull request apraksta izmaiņas un to mērķi.

## Licence

Šobrīd repozitorijā nav norādīts licences fails. Pirms koda izmantošanas, pārveidošanas vai izplatīšanas sazinieties ar autoru, lai noskaidrotu lietošanas nosacījumus.

## Kontakti

Jautājumiem vai ieteikumiem sazinieties ar repozitorija uzturētāju, izmantojot GitHub profilu [@TOMATS69](https://github.com/TOMATS69).
