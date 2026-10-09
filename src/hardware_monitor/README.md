# Hardware-Monitor

Zeigt CPU- und GPU-Temperatur als zwei Zahlen im Infobereich der Taskleiste. Ein Klick auf eines der Icons öffnet ein
Detailfenster mit fast allen Hardware-Werten in Tabs (CPU, GPU, RAM, Mainboard, Laufwerke, Netzwerk, …) und dem Tab
**Hardwaredaten**: Hersteller, Modelle, Hersteller- und Produkt-IDs, Seriennummern und Treiber aller Komponenten.
Die Sensoren liest [LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor) (LHM) über
pythonnet.

Läuft als eigenes Programm **mit Adminrechten** (sonst fehlen CPU- und Mainboard-Werte). Bedient und eingestellt wird
es über seine Seite in der Toolbox (*Allgemein → Hardware-Monitor*) oder per Rechtsklick auf ein Icon.

## Dateien

| Datei | Inhalt |
|---|---|
| `hardware_monitor.py` | das Programm: Sensoren lesen, Tray-Icons, Fernsteuerung durch die Toolbox |
| `detailfenster_inhalt.py` | **was** im Detailfenster steht (Tabs, Werte) – hier passt du das Fenster an |
| `detailfenster.py` | baut das Fenster aus `detailfenster_inhalt.py` (Farben, Layout, Ampelfarben) |
| `hardwaredaten.py` | liest die festen Daten für den Tab „Hardwaredaten“ über WMI; `python hardwaredaten.py` gibt sie aus |
| `hardware_monitor_gui.py` | Seite in der Toolbox: Status, Starten/Beenden, Autostart, Einstellungen |
| `lhm/` | LibreHardwareMonitor (nicht im Repo, siehe unten) |
| `hardware_monitor_settings.json` | Einstellungen (entsteht beim ersten Speichern, nicht im Repo) |
| `hardware_monitor.log` | Fehler und Hinweise – `pythonw` hat keine Konsole (nicht im Repo) |

## Einrichtung

**`Einrichten.cmd` im Repo-Ordner** erledigt alles (siehe Haupt-README): eigenes Python in `runtime\`, die Pakete
(`pythonnet`, `pystray`, `pillow`), `runtime\HardwareMonitor.exe`, LibreHardwareMonitor 0.9.6 nach `lhm/`, PawnIO
und die geplante Aufgabe `HardwareMonitor`. Von Hand ginge es so:

1. **Python-Pakete**: `pip install -r requirements.txt` im Repo-Ordner.
2. **PawnIO** (Treiber für CPU- und Mainboard-Sensoren), einmalig im Admin-Terminal:
   ```
   winget install namazso.PawnIO
   ```
3. **LibreHardwareMonitor**: `LibreHardwareMonitor.zip` (nicht die .NET-10-Variante) von den
   [GitHub-Releases](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases) nach `lhm/` in diesem
   Ordner entpacken. Gesucht wird `LibreHardwareMonitorLib.dll` zuerst hier, dann in `lhm/` im Repo-Ordner, dann in
   `C:\Tools\lhm`.
4. **Autostart**: in der Toolbox auf *Aufgabe einrichten* klicken. Das legt die geplante Aufgabe `HardwareMonitor` an,
   die das Programm beim Anmelden mit Adminrechten startet – ohne UAC-Abfrage. Ohne Aufgabe startet *Starten* in der
   Toolbox das Programm direkt, dann fragt Windows jedes Mal nach.

**Womit es läuft:** Gibt es `runtime\HardwareMonitor.exe` (eine Kopie von `pythonw.exe` im Projekt-Python), nutzen
Aufgabe und *Starten* diese – dann heißt der Prozess im Task-Manager „HardwareMonitor.exe“ statt „pythonw.exe“.
Sonst das `pythonw.exe` des Pythons, mit dem die Toolbox läuft.

## Starten und prüfen

```
pythonw hardware_monitor.py          # Tray-Icons, ohne Konsolenfenster
python  hardware_monitor.py --list   # alle Sensoren mit Gerät, Typ, Name und Wert auflisten
```

Zeigt `--list` im Admin-Terminal bei der CPU echte Temperaturen, funktioniert alles. Es läuft immer nur eine Instanz;
ein zweiter Start beendet sich sofort.

## Bedienung

- **Linksklick** auf ein Icon: Detailfenster öffnen/schließen. Größe und Position merkt sich das Fenster.
- **Status oben rechts**: Beim Öffnen beginnt sofort die Messung der Werte des gewählten Tabs; bis sie da ist, steht
  dort „Daten werden geladen …“, danach „● Live“ bis zum Schließen. Beim Tabwechsel werden die Geräte des neuen Tabs
  sofort gemessen, die Liste zeigt dafür kurz „Lade Sensordaten …“. Bei geschlossenem oder minimiertem Fenster werden
  nur CPU und GPU für die Icons gemessen – deshalb lädt das Fenster beim Öffnen kurz. Direkt nach dem Programmstart
  dauert es länger (~10 s), weil dann noch die übrige Hardware nachgeladen wird (vor allem der RAM).
- **Klick auf einen Gerätenamen** (fette Überschrift, in jedem Tab) kopiert ihn in die Zwischenablage, z. B.
  „G.Skill F4-3200C16-8GTZRX“ bei einem RAM-Riegel. Im Tab „Hardwaredaten“ kopiert ein Klick auf eine Zeile ihren Wert
  (z. B. die Hardware-ID). Die Fußzeile bestätigt das kurz; beim Drüberfahren zeigt sie den vollen Wert.
- **Buttons im Tab „Hardwaredaten“**: „⧉ Kopieren“ rechts in jeder Bereichszeile (Prozessor, Grafikkarte, …) kopiert
  den ganzen Bereich als Text – alle Geräte darin mit ihren Feldern, z. B. zum Einfügen in ein Forum. Oben kopiert
  „Alles kopieren“ alle Hardwaredaten (mit Computername und Datum), „Modellnamen kopieren“ nur die Modellnamen: je
  Bereich eine Zeile, darunter jedes Gerät mit einem Tab davor (gleiche Geräte zusammengefasst, z. B. „2× G.Skill …“).
- **Rechtsklick**: Aktualisierungsrate der Icons (1–10 s) und des Fensters (0,5–5 s), Beenden.
- **Zahlenfarbe**: grün, ab `warn_temp` gelb, ab `hot_temp` rot (Standard 60 / 80 °C).

## Einstellungen

Gespeichert in `hardware_monitor_settings.json`. Die Toolbox schreibt die Datei und schickt danach `reload`, das
laufende Programm übernimmt die Werte sofort. Fehlende oder ungültige Werte bekommen den Startwert.

| Schlüssel | Standard | Bedeutung |
|---|---|---|
| `icon_interval` | `2` | Sekunden zwischen Messungen für die Icons (1, 2, 5, 10) |
| `popup_interval` | `1` | Sekunden zwischen Messungen bei offenem Fenster (0.5, 1, 2, 5) |
| `icon_order` | `["cpu", "gpu"]` | Reihenfolge der Icons – wirkt erst nach Neustart des Programms |
| `cpu_sensor` / `gpu_sensor` | `"auto"` | Sensor im Icon; `auto` nimmt den ersten vorhandenen aus `CPU_SENSORS` bzw. `GPU_SENSORS` |
| `warn_temp` / `hot_temp` | `60` / `80` | ab hier gelb bzw. rot |
| `window` | `""` | Größe und Position des Detailfensters (setzt das Fenster selbst) |

Die Standardwerte stehen doppelt: `DEFAULT_SETTINGS` in `hardware_monitor.py` und `defaults` in
`hardware_monitor_gui.py` – bei Änderungen beide anpassen.

## Detailfenster anpassen

Was im Fenster steht, steht in `detailfenster_inhalt.py` – Tab für Tab, eine Zeile pro Wert:

```python
Tab("GPU",
    Gruppe("gpu",
           Wert("GPU Core", typ="Temperatur"),
           Wert("GPU Hot Spot"),
           Wert("GPU Fan *", typ="Lüfter")))       # * = beliebiger Text, hier: alle GPU-Lüfter
```

- Geräte für `Gruppe(...)`: `cpu`, `gpu`, `ram`, `mainboard`, `laufwerk` (gilt für jedes Laufwerk einzeln),
  `netzwerk`, `weitere`.
- `typ=` ist nur nötig, wenn es denselben Namen mehrfach gibt; `text=` setzt eine eigene Beschriftung.
- Die genauen Namen zeigt `--list`. Den früheren Tab „Alles“ (alle Sensoren) kann man in `detailfenster_inhalt.py`
  wieder einkommentieren.
- Gespeicherte Änderungen erscheinen beim nächsten Öffnen des Fensters, ohne Neustart.

## Hardwaredaten

Der Tab liest beim Anzeigen einmal über WMI (per pythonnet, `System.Management`), was Windows über die Hardware weiß –
keine Sensoren, keine Adminrechte nötig, unter 1 s. Nach jedem erneuten Öffnen des Fensters wird neu gelesen (z. B.
für frisch eingesteckte USB-Geräte); bis dahin bleiben die alten Daten stehen.

| Bereich | Felder |
|---|---|
| Prozessor | Hersteller, Kerne/Threads, Grundtakt, L3-Cache, Sockel, Prozessor-ID (CPUID) |
| Grafikkarte | Hersteller-ID, Produkt-ID, Platinen-Hersteller, Subsystem-ID, Revision, Hardware-ID, Treiber |
| Mainboard | Hersteller, Modell, Version, Seriennummer, BIOS-Hersteller/-Version/-Datum |
| Arbeitsspeicher | je Riegel: Hersteller, Teilenummer, Größe, Typ, Takt, Steckplatz, Seriennummer |
| Laufwerke | Art (SSD/HDD), Anschluss (NVMe/SATA/USB), Größe, Seriennummer, Firmware |
| Netzwerk, Audio | Hersteller-/Produkt-ID, Platinen-Hersteller, Hardware-ID, MAC-Adresse |
| USB-Geräte | Hersteller-ID (VID), Produkt-ID (PID), Seriennummer – ein Eintrag pro Gerät |

- Herstellernamen hinter den IDs („10DE (Nvidia)“) kommen aus kleinen Tabellen in `hardwaredaten.py`
  (`PCI_HERSTELLER`, `USB_HERSTELLER`). Unbekannte IDs stehen ohne Namen da – bei Bedarf dort ergänzen.
- Den RAM-Hersteller meldet Windows oft nur als „Unknown“; dann wird er aus dem Anfang der Teilenummer abgeleitet
  (`RAM_TEILENUMMER`) und als „(laut Teilenummer)“ gekennzeichnet.
- Virtuelle Geräte (VPN-Adapter, virtuelle Anzeigen und Audiogeräte) werden weggelassen.
- Der Mess-Thread liest bei diesem Tab nur CPU und GPU für die Icons.

## Fernsteuerung (IPC)

Die Toolbox läuft ohne Adminrechte und darf das Programm daher nicht einfach beenden. Stattdessen lauscht es auf
`127.0.0.1:47815` (nur von diesem PC erreichbar) auf einen Befehl pro Verbindung, Antwort ist eine JSON-Zeile:

| Befehl | Antwort / Wirkung |
|---|---|
| `status` | `{"ok": true, "pid": …, "cpu": 52.0, "gpu": 41.0, "order": ["cpu", "gpu"]}` |
| `reload` | Einstellungen neu einlesen |
| `quit` | Programm beenden |

Der Port steht als `IPC_PORT` in `hardware_monitor.py` **und** `hardware_monitor_gui.py` und muss übereinstimmen.

## Sparsamkeit

- **Fenster zu oder minimiert**: Gemessen werden nur CPU und GPU. Die GPU-Temperatur kommt bei Nvidia direkt aus
  `nvml.dll` (Teil des Treibers) – ein Bruchteil der ~90 ms, die ein komplettes GPU-Update über LHM kostet. Das gilt
  für die Sensorwahl „Automatisch“ und „GPU Core“; andere GPU-Sensoren laufen über LHM.
- **Nur ein Wert pro Icon**: Für die Icons wird nur der eine Temperatursensor gelesen (`icon_werte()`), nicht alle
  ~50 CPU-Sensoren einzeln über pythonnet. Der Sensor wird einmal gesucht und danach direkt abgefragt.
- **Effizienzmodus von Windows 11**: Bei geschlossenem Fenster läuft das Programm im Effizienzmodus (Blatt-Symbol im
  Task-Manager: stromsparend eingeplant, niedrigste Priorität), bei offenem Fenster normal.
- **Kaum Aufwachen im Leerlauf**: Die Fernsteuerung wartet ohne Timeout auf Verbindungen; bei geschlossenem Fenster
  sieht die Oberfläche nur alle 250 ms nach Klicks aufs Icon (offen: 100 ms).
- **Fenster offen**: Gemessen werden nur die Geräte des gewählten Tabs; die Icons bekommen die Werte mit.
- **Schneller Start**: Zuerst werden nur CPU und GPU geöffnet (Icons nach Sekundenbruchteilen), die übrige Hardware
  lädt im Hintergrund nach. Allein der RAM braucht dabei ~8 s; so lange zeigt das Fenster „Lade Sensordaten …“.
- Icons werden nur neu gezeichnet, wenn sich die angezeigte Zahl ändert.

## Fehlersuche

- **CPU zeigt `--` oder fehlt**: Programm läuft ohne Adminrechte, oder PawnIO ist nicht installiert.
- **Startet gar nicht**: `hardware_monitor.log` ansehen (Toolbox: *Erweitert → Log öffnen*). Häufig fehlt `lhm/` oder
  es ist die .NET-10-Variante von LHM.
- **Toolbox zeigt „Gestoppt“, obwohl die Icons da sind**: Port 47815 war beim Start belegt; das Programm versucht es
  alle 2 s erneut (steht dann auch im Log).
- **Tab „Hardwaredaten“ bleibt leer**: Fehler der WMI-Abfragen stehen im Log; `python hardwaredaten.py` zeigt, was
  Windows liefert.
- **Aufgabe startet eine alte Kopie**: Die Toolbox warnt, wenn die Aufgabe auf ein anderes `hardware_monitor.py` oder
  ein anderes Programm zeigt (z. B. nach dem Verschieben des Ordners); *Aufgabe aktualisieren* oder `Einrichten.cmd`
  stellt sie um.
