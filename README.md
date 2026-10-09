# windows-toolbox

Sammlung kleiner, selbst geschriebener Windows-Tools mit einer gemeinsamen Oberfläche (Toolbox).

| Teil | Ordner | Was es macht |
|---|---|---|
| **Toolbox** (GUI) | `src/gui/` | Oberfläche für alle Tools: Tabs oben, Programmliste links, Einstellungen rechts, Zahnrad für die GUI selbst |
| **Hardware-Monitor** | `src/hardware_monitor/` | CPU- und GPU-Temperatur als Zahlen in der Taskleiste; Klick öffnet ein Fenster mit Hardware-Werten in Tabs und allen Hardwaredaten (Hersteller-/Produkt-IDs, Seriennummern) ([README](src/hardware_monitor/README.md)) |

Jedes Tool hat in seinem Ordner eine eigene `README.md` mit Einrichtung, Bedienung und Technik.

## Ordnerstruktur

```
windows-toolbox/
├─ Einrichten.cmd         richtet alles ein (einmal nach dem Klonen, erneut nach dem Verschieben)
├─ Entfernen.cmd          Gegenstück: Monitor beenden, Aufgabe löschen
├─ Toolbox.cmd            startet die GUI mit dem Python aus runtime\
├─ Toolbox.pyw            startet die GUI mit dem installierten Python
├─ __init__.py            damit Zed die Skripte als Modul starten kann (Play-Button)
├─ requirements.txt
├─ runtime/               eigenes Python mit allen Paketen (legt Einrichten.cmd an, nicht im Repo)
├─ setup/
│  ├─ einrichten.ps1      was Einrichten.cmd macht
│  ├─ admin.py            Teil davon mit Adminrechten: PawnIO, geplante Aufgabe
│  └─ entfernen.ps1       was Entfernen.cmd macht
└─ src/
   ├─ gui/
   │  ├─ toolbox.py       Hauptfenster; findet die Programmseiten automatisch
   │  ├─ base.py          Baukasten für Programmseiten (Section, Text, Choice, Slider, …)
   │  ├─ winutil.py       Windows-Helfer (UAC, Aufgabenplanung)
   │  ├─ platzhalter.py   leere Seite für Tabs ohne Programm
   │  └─ toolbox.ico      Symbol der Toolbox
   └─ hardware_monitor/
      ├─ hardware_monitor.py       Hardware-Monitor (läuft eigenständig): Sensoren, Tray-Icons, IPC
      ├─ detailfenster_inhalt.py   WAS im Detailfenster steht – hier passt du das Fenster an
      ├─ detailfenster.py          baut das Detailfenster daraus (wie base.py bei der Toolbox)
      ├─ hardwaredaten.py          liest Hersteller, Modelle, IDs und Seriennummern für den Tab „Hardwaredaten“
      ├─ hardware_monitor_gui.py   seine Seite in der Toolbox
      └─ lhm/                      LibreHardwareMonitor (nicht im Repo, siehe unten)
```

## Einrichtung

```
git clone https://github.com/ItsMaxxx/windows-toolbox.git
```
Danach **Doppelklick auf `Einrichten.cmd`** – sonst ist nichts nötig, nicht einmal ein installiertes Python. Das Skript
(`setup\einrichten.ps1`):

1. sucht ein installiertes Python ab 3.10 (fehlt es, installiert es Python 3.14 per winget),
2. kopiert es nach `runtime\` (ohne Doku und Tests, ~90 MB) und installiert dort die Pakete aus `requirements.txt` –
   dieses Python nutzt nur, was in `runtime\` liegt, nichts aus dem installierten Python oder `%APPDATA%\Python`,
3. legt `runtime\HardwareMonitor.exe` an (Kopie von `pythonw.exe`, damit der Monitor im Task-Manager unter seinem
   Namen erscheint),
4. lädt LibreHardwareMonitor 0.9.6 von GitHub (Prüfsumme wird kontrolliert) nach `src\hardware_monitor\lhm\`,
5. holt **einmal** Adminrechte (UAC-Abfrage) und installiert damit PawnIO (Treiber für CPU- und Mainboard-Sensoren)
   und die geplante Aufgabe `HardwareMonitor` (startet den Monitor beim Anmelden mit Adminrechten, ohne Nachfrage),
6. startet den Hardware-Monitor (bzw. neu, wenn er noch mit dem alten Programm lief).

Jeder Schritt prüft vorher, ob er schon erledigt ist – `Einrichten.cmd` lässt sich also jederzeit erneut ausführen,
z. B. nach einem `git pull` (neue Pakete) oder **nach dem Verschieben des Ordners**: dann wird nur die Aufgabe neu
eingerichtet. Mit `-OhneAdmin` (im Terminal: `Einrichten.cmd -OhneAdmin`) entfallen Schritt 5 und 6.

**Toolbox starten**: Doppelklick auf `Toolbox.cmd` (nutzt `runtime\`). `Toolbox.pyw` geht weiterhin, nutzt aber das
installierte Python.

**Portabel**: Nach dem Einrichten steckt alles im Ordner. Verschieben oder auf einen anderen PC kopieren, dort
`Einrichten.cmd` erneut ausführen – fertig. Außerhalb des Ordners liegen nur PawnIO (ein Treiber muss in Windows
registriert sein) und die geplante Aufgabe (speichert Windows selbst).

**Neues Python für `runtime\`**: Ordner `runtime\` löschen und `Einrichten.cmd` ausführen.

**Entfernen**: `Entfernen.cmd` beendet den Hardware-Monitor, löscht die Aufgabe und auf Wunsch `runtime\` und `lhm\`.
Danach kann der Ordner gelöscht werden. PawnIO bleibt installiert (`winget uninstall namazso.PawnIO`).

## Prüfen

```
python src\hardware_monitor\hardware_monitor.py --list
```
listet alle Sensoren auf. Läuft das im Admin-Terminal und zeigt bei der CPU echte Temperaturen, funktioniert alles.

## Detailfenster anpassen

Was im Fenster steht, steht in `src/hardware_monitor/detailfenster_inhalt.py` – Tab für Tab, eine Zeile pro Wert:
```python
Tab("GPU",
    Gruppe("gpu",
           Wert("GPU Core", typ="Temperatur"),
           Wert("GPU Hot Spot"),
           Wert("GPU Fan *", typ="Lüfter")))       # * = beliebiger Text, hier: alle GPU-Lüfter
```
Wert hinzufügen = Zeile schreiben, Wert weglassen = Zeile löschen. Die genauen Namen zeigt `--list`. Gespeicherte Änderungen erscheinen beim nächsten Öffnen des Fensters, ohne Neustart.

## Neues Tool hinzufügen

1. Programm unter `src/<name>/` ablegen.
2. Daneben die Seite für die GUI als `src/<name>/<name>_gui.py` anlegen. Sie wird mit den Bausteinen aus
   `src/gui/base.py` nur beschrieben, Laden und Speichern der Einstellungen übernimmt die Toolbox:
   ```python
   from pathlib import Path
   from base import Choice, Section, Text, ToolInfo, ToolPage

   class MeinPage(ToolPage):
       settings_file = Path(__file__).with_name("mein_settings.json")
       defaults = {"rate": 2}

       def layout(self):
           return [Section("Aktualisierung",
                           Text("Wie oft gemessen wird."),
                           Choice("Rate", "rate", {"1 s": 1, "2 s": 2, "5 s": 5}))]

   TOOL = ToolInfo("mein", "Mein Programm", "Werkzeuge", "Kurze Beschreibung", MeinPage)
   ```
   Alle Bausteine stehen oben in `base.py` erklärt, ein volles Beispiel ist `hardware_monitor_gui.py`.
3. Eine `src/<name>/README.md` anlegen (was das Tool macht, Einrichtung, Bedienung, Einstellungen, Technik – Vorbild
   ist `src/hardware_monitor/README.md`) und das Tool oben in der Tabelle eintragen.
4. Fertig – die Toolbox findet jede `*_gui.py` beim Start automatisch, sortiert wird alphabetisch.

## Technisches

- **Einstellungen** liegen jeweils als `*_settings.json` neben dem Skript, **Fehler** in `*.log` (beides ignoriert git).
- **GUI ↔ Hardware-Monitor**: Der Monitor läuft mit Adminrechten, die GUI ohne. Gesteuert wird über eine lokale
  Verbindung auf `127.0.0.1:47815` (Befehle `status`, `reload`, `quit`). Die GUI selbst lauscht auf Port `47816`,
  damit ein zweiter Start nur das vorhandene Fenster nach vorne holt.
- **Sparsam**: Bei geschlossenem oder minimiertem Detailfenster liest der Monitor nur CPU und GPU, bei offenem Fenster
  nur die Geräte des gewählten Tabs; Raten im Rechtsklick-Menü oder in der GUI.
  Die GPU-Temperatur fürs Icon kommt bei Nvidia direkt aus `nvml.dll` (Teil des Treibers). LHMs komplettes
  GPU-Update kostet ~90 ms pro Messung, NVML nur einen Bruchteil davon. Das gilt für „Automatisch“ und „GPU Core“, andere
  GPU-Sensoren laufen weiter über LHM. Für die Icons wird nur der eine Temperatursensor gelesen, und bei geschlossenem
  Fenster läuft der Monitor im Effizienzmodus von Windows 11.
- **Schneller Start**: Zuerst werden nur CPU und GPU geöffnet (Icons nach Sekundenbruchteilen), die übrige Hardware
  lädt danach im Hintergrund nach. Allein der RAM braucht dabei ~8 s; bis dahin zeigt das Detailfenster „Lade Sensordaten …“.
- **Kein `__pycache__`**: `toolbox.py` setzt gleich am Anfang `sys.dont_write_bytecode = True`, dadurch legt Python
  für die Programmseiten und Hilfsdateien keine `__pycache__`-Ordner an. Nur beim Start als Modul
  (`python -m src.gui.toolbox`, z. B. über den Play-Button in Zed) speichert Python `toolbox.py` selbst, bevor diese
  Zeile läuft. Dagegen hilft `python -B -m src.gui.toolbox` oder einmalig für alle Python-Programme:
  ```
  setx PYTHONDONTWRITEBYTECODE 1
  ```
  (wirkt in neu geöffneten Terminals bzw. nach Neustart von Zed).
