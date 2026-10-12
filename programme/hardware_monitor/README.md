# Hardware-Monitor

Zeigt CPU- und GPU-Temperatur als zwei Zahlen im Infobereich der Taskleiste (ohne GPU-Temperatur, z. B. bei
Intel-Onboard-Grafik, nur die CPU). Ein Klick auf eines der Icons öffnet ein
Detailfenster mit fast allen Hardware-Werten in Tabs (CPU, GPU, RAM, Mainboard, Laufwerke, Netzwerk, Akku) und dem Tab
**Hardwaredaten**: Hersteller, Modelle, Hersteller- und Produkt-IDs, Seriennummern und Treiber aller Komponenten.
Läuft auf AMD- und Intel-Systemen, Desktop wie Laptop; Tabs für Geräte, die der PC nicht hat (z. B. Mainboard-Sensoren
am Laptop, Akku am Desktop), werden ausgeblendet.
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
| `hardware_monitor_einstellungen.py` | Startwerte, erlaubte Werte, Laden und Speichern – gemeinsam für Programm und Seite |
| `programm.json` | Ausweis: Name, Tab, Beschreibung, Version, Skript, Starter, Port, Aufgabe, Download von LibreHardwareMonitor |
| `HardwareMonitor.exe` | Starter (legt `Setup.exe` an, nicht im Repo) – startet `hardware_monitor.py` ohne Argumente |
| `lhm/` | LibreHardwareMonitor (nicht im Repo, siehe unten) |
| `daten/hardware_monitor.json` (im Hauptordner) | Einstellungen (entsteht beim ersten Speichern, nicht im Repo) |
| `daten/logs/hardware_monitor.log` (im Hauptordner) | Fehler und Hinweise – `pythonw` hat keine Konsole (nicht im Repo) |

## Einrichtung

**`Setup.exe` im Repo-Ordner** erledigt alles (siehe Haupt-README): eigenes Python in `runtime\`, die Pakete
(`pythonnet`, `pystray`, `pillow`), den Starter `HardwareMonitor.exe`, LibreHardwareMonitor 0.9.6 nach `lhm\`, PawnIO
und die geplante Aufgabe `HardwareMonitor`. Von Hand ginge es so:

1. **Python-Pakete**: `pip install -r requirements.txt` im Repo-Ordner (feste Versionen, geprüft mit Python 3.14).
2. **PawnIO** (Treiber für CPU- und Mainboard-Sensoren), einmalig im Admin-Terminal:
   ```
   winget install namazso.PawnIO
   ```
3. **LibreHardwareMonitor**: `LibreHardwareMonitor.zip` (nicht die .NET-10-Variante) von den
   [GitHub-Releases](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases) nach `lhm\` in
   diesem Ordner entpacken.
4. **Autostart**: in der Toolbox auf *Aufgabe einrichten* klicken. Das legt die geplante Aufgabe `HardwareMonitor`
   (Name aus `"aufgabe"` in `programm.json`) an,
   die das Programm beim Anmelden mit Adminrechten startet – ohne UAC-Abfrage. Sie wird ausgeschaltet angelegt
   (Setup.exe macht das genauso); der Schalter *Beim Anmelden automatisch starten* schaltet sie ein. Ist sie aus oder
   fehlt sie, startet *Starten* in der Toolbox das Programm direkt, dann fragt Windows jedes Mal nach.
   Neu einrichten (Knopf, Setup.exe, Update) lässt den Schalter, wie er war.

**Womit es läuft:** Aufgabe und *Starten* rufen den Starter `HardwareMonitor.exe` in diesem Ordner auf (ohne
Argumente). Der startet `runtime\HardwareMonitor.exe` (`pythonw.exe` des Projekt-Pythons mit eigener
Dateibeschreibung und eigenem Symbol, angelegt von `setup\exe_anlegen.py`) mit `hardware_monitor.py` und beendet
sich – im Task-Manager steht dann „Hardware-Monitor“ mit dem Toolbox-Symbol statt „Python“. Fehlt der Starter, zeigt
die Toolbox einen Hinweis, `Setup.exe` auszuführen. Ist das Detailfenster zu, steht der Monitor im Task-Manager unter
„Hintergrundprozesse“ statt unter „Apps“ – so hält Windows es mit jedem Programm ohne sichtbares Fenster.

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
- **⚙ rechts daneben**: öffnet die Einstellungen – die Seite des Hardware-Monitors in der Toolbox. Läuft die Toolbox
  nicht, wird sie gestartet, und zwar als normales Programm (über `explorer.exe`), auch wenn der Monitor selbst
  Adminrechte hat.
- **Klick auf einen Wert oder Gerätenamen** kopiert ihn in die Zwischenablage, z. B. „2786“ bei der Produkt-ID oder
  „G.Skill F4-3200C16-8GTZRX“ bei einem RAM-Riegel – aber nur direkt auf dem Text (die Hand als Mauszeiger zeigt es).
  Ein Klick auf die Beschriftung davor („Produkt-ID“) oder ins Leere daneben markiert nur die Zeile. Die Fußzeile
  bestätigt das Kopieren kurz; beim Drüberfahren zeigt sie den vollen Wert.
- **Mehrere Zeilen kopieren**: markieren – mit gedrückter Maustaste darüberziehen, Strg+Klick (einzelne dazu),
  Umschalt+Klick (bis hierhin) oder Strg+A (alle) – und mit Strg+C kopieren, z. B. „Hersteller-ID: 10DE“ und
  „Produkt-ID: 2786“ untereinander. Überschriften kommen nur mit ihrem Namen mit, eingerückt wie in der Liste.
  Dasselbe steht im Rechtsklick-Menü der Liste; Esc oder ein Klick ins Leere hebt die Markierung auf.
- **Tab „Hardwaredaten“** hat zwei Unterreiter: „Übersicht“ zeigt nur die Modellnamen (gleiche Geräte zusammengefasst,
  z. B. „2× G.Skill …“), „Details“ alle Felder (Hersteller, IDs, Seriennummern, Treiber …). Kopiert wird immer das,
  was gerade zu sehen ist: „⧉ Kopieren“ rechts in jeder Bereichszeile (Prozessor, Grafikkarte, …) den Bereich,
  „Alles kopieren“ oben alle Bereiche – in der Übersicht je Bereich eine Zeile, darunter jedes Gerät mit einem Tab
  davor; in den Details als Text mit Computername und Datum, z. B. zum Einfügen in ein Forum.
- **Rechtsklick aufs Icon**: Aktualisierungsrate der Icons (1–10 s) und des Fensters (0,5–5 s), Beenden.
- **Zahlenfarbe**: grün, ab `…_warn_temp` gelb, ab `…_hot_temp` rot – getrennt für CPU (Standard 75 / 90 °C) und
  GPU (70 / 83 °C). Im Detailfenster richten sich Mainboard und Laufwerke nach den CPU-Grenzen.

## Einstellungen

Gespeichert in `daten\hardware_monitor.json`. Die Toolbox schreibt die Datei und schickt danach `reload`, das
laufende Programm übernimmt die Werte sofort. Fehlende oder ungültige Werte bekommen den Startwert.

| Schlüssel | Standard | Bedeutung |
|---|---|---|
| `icon_interval` | `2` | Sekunden zwischen Messungen für die Icons (1, 2, 5, 10) |
| `popup_interval` | `1` | Sekunden zwischen Messungen bei offenem Fenster (0.5, 1, 2, 5) |
| `icon_order` | `["cpu", "gpu"]` | Reihenfolge der Icons – wirkt erst nach Neustart des Programms |
| `cpu_sensor` / `gpu_sensor` | `"auto"` | Sensor im Icon; `auto` nimmt den ersten vorhandenen aus `CPU_SENSORS` bzw. `GPU_SENSORS` |
| `cpu_warn_temp` / `cpu_hot_temp` | `75` / `90` | CPU: ab hier gelb bzw. rot (auch Mainboard, Laufwerke) |
| `gpu_warn_temp` / `gpu_hot_temp` | `70` / `83` | GPU: ab hier gelb bzw. rot |
| `effizienzmodus` | `"auto"` | Effizienzmodus von Windows 11: `auto` = nur bei geschlossenem Fenster, `an` = immer, `aus` = nie |
| `window` | `""` | Größe und Position des Detailfensters (setzt das Fenster selbst) |

Startwerte, erlaubte Werte und die Prüfung beim Laden stehen in `hardware_monitor_einstellungen.py` – Monitor und
Toolbox-Seite nutzen beide diese Datei.

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
  `netzwerk`, `akku`, `weitere`. `name=` beschränkt eine Gruppe auf Geräte mit passendem Namen (z. B. `"Intel*"`).
- `typ=` ist nur nötig, wenn es denselben Namen mehrfach gibt; `text=` setzt eine eigene Beschriftung; `ohne=` schließt
  Namen aus, die trotz `*` nicht dazugehören (`Wert("CPU Core #*", ohne="*Distance*")`).
- `Abschnitt("Lüfter", Wert(...), ...)` in einer Gruppe ist ein einklappbarer Unterpunkt; mit `eine_zeile=True` stehen
  gleichnamige Werte in einer Zeile (Fan #1: Drehzahl, dahinter die Ansteuerung als Balken mit %; dreht sich ein
  angesteuerter Lüfter nicht, steht dort grau „steht“). Zugeklappte Bereiche bleiben zu, bis das
  Programm beendet wird.
- Die Namen hängen von der Hardware ab (AMD: `Core (Tctl/Tdie)`, Intel: `CPU Package`). Was es auf dem PC nicht gibt,
  wird nicht angezeigt – daher stehen die Namen für beide nebeneinander in der Datei.
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
| Grafikkarte | Art (Integriert/Dediziert/Extern), Hersteller-ID, Produkt-ID, Platinen-Hersteller, Subsystem-ID, Revision, Hardware-ID, Treiber |
| Mainboard | Hersteller, Modell, Version, Seriennummer, BIOS-Hersteller/-Version/-Datum |
| Arbeitsspeicher | je Riegel: Hersteller, Teilenummer, Größe, Typ, Bauform (DIMM/SO-DIMM), Takt, Steckplatz, Seriennummer. Verlöteter LPDDR-Speicher als ein Eintrag: Größe gesamt, Bauform „verlötet“, Kanäle |
| Laufwerke | Art (SSD/HDD), Anschluss (NVMe/SATA/USB), Größe, Seriennummer, Firmware |
| Netzwerk | Art (LAN/WLAN/Mobilfunk), Hersteller-/Produkt-ID, Platinen-Hersteller, Hardware-ID, MAC-Adresse |
| Audio | Hersteller-/Produkt-ID, Platinen-Hersteller, Hardware-ID |
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

Der Port steht als `"port"` in `programm.json`; Monitor, Toolbox-Seite und `setup.ps1` lesen ihn von dort.

## Sparsamkeit

- **Fenster zu oder minimiert**: Gemessen werden nur CPU und GPU. Die GPU-Temperatur kommt bei Nvidia direkt aus
  `nvml.dll` (Teil des Treibers) – ein Bruchteil der ~90 ms, die ein komplettes GPU-Update über LHM kostet. Das gilt
  für die Sensorwahl „Automatisch“ und „GPU Core“; andere GPU-Sensoren laufen über LHM.
- **Nur ein Wert pro Icon**: Für die Icons wird nur der eine Temperatursensor gelesen (`icon_werte()`), nicht alle
  ~50 CPU-Sensoren einzeln über pythonnet. Der Sensor wird einmal gesucht und danach direkt abgefragt.
- **Effizienzmodus von Windows 11**: Bei geschlossenem Fenster läuft das Programm im Effizienzmodus (Blatt-Symbol im
  Task-Manager: stromsparend eingeplant, niedrigste Priorität), bei offenem Fenster normal. Einstellbar in der Toolbox
  (*Aktualisierung → Effizienzmodus*: Automatisch / Immer an / Aus; das „i“ daneben erklärt die drei). Von Hand im
  Task-Manager umgeschaltet, setzt das Programm beim nächsten Öffnen oder Schließen des Fensters wieder seinen Modus.
- **Kein GPU-Icon ohne GPU-Temperatur**: Beim Start prüft `gpu_hat_temperatur()`, ob es eine GPU-Temperatur gibt
  (Nvidia per NVML oder irgendein Temperatursensor einer GPU in LHM). Wenn nicht, entfällt das GPU-Icon, und die GPU
  wird für die Icons gar nicht erst gelesen.
- **Kaum Aufwachen im Leerlauf**: Die Fernsteuerung wartet ohne Timeout auf Verbindungen; bei geschlossenem Fenster
  sieht die Oberfläche nur alle 250 ms nach Klicks aufs Icon (offen: 100 ms).
- **Fenster offen**: Gemessen werden nur die Geräte des gewählten Tabs; die Icons bekommen die Werte mit.
- **Schneller Start**: Zuerst werden nur CPU und GPU geöffnet (Icons nach Sekundenbruchteilen), die übrige Hardware
  lädt im Hintergrund nach. Allein der RAM braucht dabei ~8 s; so lange zeigt das Fenster „Lade Sensordaten …“.
- Icons werden nur neu gezeichnet, wenn sich die angezeigte Zahl ändert.

## Fehlersuche

- **CPU zeigt `--` oder fehlt**: Programm läuft ohne Adminrechte, oder PawnIO ist nicht installiert.
- **Kein GPU-Icon**: Die Grafik hat keinen Temperatursensor – bei Intel-Onboard-Grafik (z. B. Iris Xe) normal
  (steht auch so im Log).
- **Task-Manager zeigt noch „Python“ oder das Python-Logo**: `Setup.exe` erneut ausführen (legt die
  `.exe`-Dateien neu an und lässt Windows Name und Symbol neu lesen), danach den Task-Manager ganz schließen und neu
  öffnen – ein offener behält, was er einmal geladen hat.
- **Ein Tab zeigt „Keine passenden Sensoren“**: Die Hardware nennt ihre Sensoren anders; `--list` zeigt die Namen,
  die dann in `detailfenster_inhalt.py` ergänzt werden.
- **Startet gar nicht**: `daten\logs\hardware_monitor.log` ansehen (Toolbox: *Erweitert → Log öffnen*). Häufig
  fehlt `lhm\` oder es ist die .NET-10-Variante von LHM.
- **Toolbox zeigt „Gestoppt“, obwohl die Icons da sind**: Port 47815 war beim Start belegt; das Programm versucht es
  alle 2 s erneut (steht dann auch im Log).
- **Tab „Hardwaredaten“ bleibt leer**: Fehler der WMI-Abfragen stehen im Log; `python hardwaredaten.py` zeigt, was
  Windows liefert.
- **Aufgabe startet eine alte Kopie**: Die Toolbox warnt, wenn die Aufgabe nicht auf `HardwareMonitor.exe` in diesem
  Ordner zeigt (z. B. nach dem Verschieben des Ordners); *Aufgabe aktualisieren* oder `Setup.exe`
  stellt sie um.
