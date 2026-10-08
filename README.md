# windows-toolbox

Sammlung kleiner, selbst geschriebener Windows-Tools mit einer gemeinsamen Oberfläche (Toolbox).

| Teil | Ordner | Was es macht |
|---|---|---|
| **Toolbox** (GUI) | `src/gui/` | Oberfläche für alle Tools: Tabs oben, Programmliste links, Einstellungen rechts, Zahnrad für die GUI selbst |
| **Hardware-Monitor** | `src/hardware_monitor/` | CPU- und GPU-Temperatur als Zahlen in der Taskleiste; Klick öffnet ein Fenster mit Hardware-Werten in Tabs |

## Ordnerstruktur

```
windows-toolbox/
├─ Toolbox.pyw            Doppelklick startet die GUI
├─ __init__.py            damit Zed die Skripte als Modul starten kann (Play-Button)
├─ requirements.txt
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
      ├─ hardware_monitor_gui.py   seine Seite in der Toolbox
      └─ lhm/                      LibreHardwareMonitor (nicht im Repo, siehe unten)
```

## Einrichtung

1. **Python-Pakete** (im Repo-Ordner):
   ```
   pip install -r requirements.txt
   ```
   ```
   oder hier: PS C:\WINDOWS\system32> python -m pip install -r E:\Software\windows-toolbox\requirements.txt
   ```
2. **PawnIO** (Treiber für CPU- und Mainboard-Sensoren), einmalig im Admin-Terminal:
   ```
   winget install namazso.PawnIO
   ```
3. **LibreHardwareMonitor**: `LibreHardwareMonitor.zip` (nicht die .NET-10-Variante) von
   [GitHub-Releases](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases) nach
   `src/hardware_monitor/lhm/` entpacken.
4. **Toolbox starten**: Doppelklick auf `Toolbox.pyw`.
5. **Autostart des Hardware-Monitors**: in der Toolbox unter *Allgemein → Hardware-Monitor → Autostart* auf
   „Aufgabe einrichten“ klicken. Das legt die geplante Aufgabe `HardwareMonitor` an (läuft beim Anmelden mit Adminrechten,
   ohne Nachfrage).

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
Wert hinzufügen = Zeile schreiben, Wert weglassen = Zeile löschen. Die genauen Namen zeigt der Tab „Alles“ im Fenster
(oder `--list`). Gespeicherte Änderungen erscheinen beim nächsten Öffnen des Fensters, ohne Neustart.

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
3. Fertig – die Toolbox findet jede `*_gui.py` beim Start automatisch, sortiert wird alphabetisch.

## Technisches

- **Einstellungen** liegen jeweils als `*_settings.json` neben dem Skript, **Fehler** in `*.log` (beides ignoriert git).
- **GUI ↔ Hardware-Monitor**: Der Monitor läuft mit Adminrechten, die GUI ohne. Gesteuert wird über eine lokale
  Verbindung auf `127.0.0.1:47815` (Befehle `status`, `reload`, `quit`). Die GUI selbst lauscht auf Port `47816`,
  damit ein zweiter Start nur das vorhandene Fenster nach vorne holt.
- **Sparsam**: Bei geschlossenem oder minimiertem Detailfenster liest der Monitor nur CPU und GPU, bei offenem Fenster
  nur die Geräte des gewählten Tabs; Raten im Rechtsklick-Menü oder in der GUI.
  Die GPU-Temperatur fürs Icon kommt bei Nvidia direkt aus `nvml.dll` (Teil des Treibers). LHMs komplettes
  GPU-Update kostet ~90 ms pro Messung, NVML nur einen Bruchteil davon. Das gilt für „Automatisch“ und „GPU Core“, andere
  GPU-Sensoren laufen weiter über LHM.
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
