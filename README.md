# windows-toolbox

Sammlung kleiner, selbst geschriebener Windows-Tools mit einer gemeinsamen Oberfläche (Toolbox).

| Teil | Ordner | Was es macht |
|---|---|---|
| **Toolbox** (GUI) | `src/gui/` | Oberfläche für alle Tools: Tabs oben, Programmliste links, Einstellungen rechts, Zahnrad für die GUI selbst |
| **Hardware-Monitor** | `src/hardware_monitor/` | CPU- und GPU-Temperatur als Zahlen in der Taskleiste; Klick öffnet fast alle Hardware-Werte in Tabs |

## Ordnerstruktur

```
windows-toolbox/
├─ Toolbox.pyw            Doppelklick startet die GUI
├─ requirements.txt
└─ src/
   ├─ gui/
   │  ├─ toolbox.py       Hauptfenster
   │  └─ tools/           eine Datei pro Programmseite + Hilfsfunktionen
   └─ hardware_monitor/
      ├─ hardware_monitor.py   Hardware-Monitor
      └─ lhm/              LibreHardwareMonitor (nicht im Repo, siehe unten)
```

## Einrichtung

1. **Python-Pakete** (im Repo-Ordner):
   ```
   pip install -r requirements.txt
   ```
2. **PawnIO** (Treiber für CPU- und Mainboard-Sensoren), einmalig im Admin-Terminal:
   ```
   winget install namazso.PawnIO
   ```
3. **LibreHardwareMonitor**: `LibreHardwareMonitor.zip` (nicht die .NET-10-Variante) von
   [GitHub-Releases](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases) nach
   `src/hardware_monitor/lhm/` entpacken. Liegt es noch unter `C:\Tools\lhm`, wird es dort ebenfalls gefunden.
4. **Toolbox starten**: Doppelklick auf `Toolbox.pyw`.
5. **Autostart des Hardware-Monitors**: in der Toolbox unter *Allgemein → Hardware-Monitor → Autostart* auf
   „Aufgabe einrichten“ klicken. Das legt die geplante Aufgabe `HardwareMonitor` an (läuft beim Anmelden mit Adminrechten,
   ohne Nachfrage).

## Prüfen

```
python src\hardware_monitor\hardware_monitor.py --list
```
listet alle Sensoren auf. Läuft das im Admin-Terminal und zeigt bei der CPU echte Temperaturen, funktioniert alles.

## Neues Tool hinzufügen

1. Programm unter `src/<name>/` ablegen.
2. Eine Seite für die GUI in `src/gui/tools/<name>.py` schreiben (Unterklasse von `ToolPage`, siehe `hardware_monitor.py`).
3. In `src/gui/tools/__init__.py` eine Zeile in `TOOLS` ergänzen – Tab und Name angeben, sortiert wird automatisch.

## Technisches

- **Einstellungen** liegen jeweils als `*_settings.json` neben dem Skript, **Fehler** in `*.log` (beides ignoriert git).
- **GUI ↔ Hardware-Monitor**: Der Monitor läuft mit Adminrechten, die GUI ohne. Gesteuert wird über eine lokale
  Verbindung auf `127.0.0.1:47815` (Befehle `status`, `reload`, `quit`). Die GUI selbst lauscht auf Port `47816`,
  damit ein zweiter Start nur das vorhandene Fenster nach vorne holt.
- **Sparsam**: Bei geschlossenem Detailfenster liest der Monitor nur CPU und GPU; Raten im Rechtsklick-Menü oder in der GUI.
