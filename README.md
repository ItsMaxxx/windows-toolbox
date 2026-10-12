# windows-toolbox

Sammlung kleiner, selbst geschriebener Windows-Tools mit einer gemeinsamen Oberfläche (Toolbox).

| Teil | Ordner | Was es macht |
|---|---|---|
| **Toolbox** (GUI) | `toolbox/` | Oberfläche für alle Tools: Tabs oben, Programmliste links, Einstellungen rechts, Zahnrad für die GUI selbst |
| **Hardware-Monitor** | `programme/hardware_monitor/` | CPU- und GPU-Temperatur als Zahlen in der Taskleiste; Klick öffnet ein Fenster mit Hardware-Werten in Tabs und allen Hardwaredaten (Hersteller-/Produkt-IDs, Seriennummern) ([README](programme/hardware_monitor/README.md)) |
| **Cube Game** | `programme/cube_game/` | Kleines Spiel: weißer Würfel (WASD) weicht roten Würfeln aus, die vom Rand kommen; Rekord wird gespeichert ([README](programme/cube_game/README.md)) |

Jedes Tool hat in seinem Ordner eine eigene `README.md` mit Einrichtung, Bedienung und Technik.

## Ordnerstruktur

```
windows-toolbox/
├─ Setup.exe              richtet alles ein (einmal nach dem Klonen, erneut nach dem Verschieben oder Update)
├─ Uninstall.exe          Gegenstück zu Setup: Toolbox und Monitor beenden, Aufgabe löschen, Erzeugtes löschen
├─ Toolbox.exe            startet die Toolbox (Starter, legt Setup.exe an)
├─ __init__.py            damit Zed die Skripte als Modul starten kann (Play-Button)
├─ requirements.txt       Python-Pakete mit festen Versionen
├─ runtime/               wegwerfbar: eigenes Python mit Paketen (legt Setup.exe an)
├─ daten/                 gehört dir: toolbox.json, eine <programm>.json je Programm, installiert.json, logs/
├─ setup/
│  ├─ setup.ps1           was Setup.exe und Uninstall.exe machen
│  ├─ setup_exe.cs        Quelltext von Setup.exe und Uninstall.exe (neu bauen: setup_exe_bauen.ps1)
│  ├─ starter.cs          Vorlage für die Starter-.exe (Toolbox.exe, HardwareMonitor.exe, …)
│  ├─ argumente.cs        gemeinsamer Teil von setup_exe.cs und starter.cs (Argumente weiterreichen)
│  └─ exe_anlegen.py      runtime\Toolbox.exe / runtime\HardwareMonitor.exe: pythonw.exe mit eigenem Namen und Symbol
├─ toolbox/
│  ├─ programm.json       Ausweis der Toolbox (Version, Skript, Starter, Port)
│  ├─ toolbox.py          Hauptfenster; findet die Programme automatisch
│  ├─ base.py             Baukasten für Programmseiten (Section, Text, Choice, Slider, …)
│  ├─ winutil.py          Windows-Helfer (UAC, Aufgabenplanung)
│  ├─ daten.py            wo Einstellungen und Logs liegen (daten/), Lesen und Schreiben
│  ├─ toolbox.ico         Symbol der Toolbox (blauer Werkzeugkoffer) – auch für Setup.exe und Uninstall.exe
│  └─ programm.ico        Standardsymbol der Programme (⚒ auf Grün), z. B. für den Hardware-Monitor
└─ programme/
   ├─ cube_game/                   Spiel (pygame-ce) – Aufbau siehe programme/cube_game/README.md
   └─ hardware_monitor/            ein Programm = ein Ordner, alles darin
      ├─ programm.json             Ausweis: Name, Tab, Beschreibung, Version, Skript, Starter, Port, Aufgabe, Downloads
      ├─ HardwareMonitor.exe       Starter (legt Setup.exe an)
      ├─ hardware_monitor.py       Hardware-Monitor (läuft eigenständig): Sensoren, Tray-Icons, IPC
      ├─ detailfenster_inhalt.py   WAS im Detailfenster steht – hier passt du das Fenster an
      ├─ detailfenster.py          baut das Detailfenster daraus (wie base.py bei der Toolbox)
      ├─ hardwaredaten.py          liest Hersteller, Modelle, IDs und Seriennummern für den Tab „Hardwaredaten“
      ├─ hardware_monitor_gui.py   seine Seite in der Toolbox
      ├─ hardware_monitor_einstellungen.py   Startwerte, Laden/Speichern – gemeinsam für Monitor und Seite
      └─ lhm/                      LibreHardwareMonitor (Download aus programm.json, nicht im Repo)
```

Die Aufteilung folgt einer einfachen Regel: **Code** (`toolbox/`, `programme/`, `setup/`) kommt aus dem Repo,
**`runtime/`** lässt sich jederzeit löschen und neu einrichten, **`daten/`** gehört dir:

```
daten/
├─ toolbox.json              Einstellungen der Toolbox
├─ hardware_monitor.json     Einstellungen des Hardware-Monitors
├─ installiert.json          welche Programme eingerichtet sind (schreibt Setup.exe)
└─ logs/
   ├─ toolbox.log
   └─ hardware_monitor.log
```

Zum Sichern oder Umziehen der Einstellungen reicht `daten/`.

## Einrichtung

```
git clone https://github.com/ItsMaxxx/windows-toolbox.git
```
Danach **Doppelklick auf `Setup.exe`** – sonst ist nichts nötig, nicht einmal ein installiertes Python. `Setup.exe`
öffnet ein Konsolenfenster und führt darin `setup\setup.ps1` aus (eine `.ps1` direkt doppelzuklicken würde sie nur im
Editor öffnen). Es läuft ohne Adminrechte und fragt nur für Schritt 5 einmal nach.

Zuerst fragt ein kleines Fenster, **welche Programme** eingerichtet werden sollen: Die Toolbox ist immer dabei, die
übrigen per Kästchen (oder *Alle auswählen*). Die Auswahl landet in `daten\installiert.json`; die Toolbox zeigt links
nur diese Programme. Fehlt die Datei (Einrichtung von vor dieser Auswahl), gelten alle als eingerichtet. Danach:

1. sucht ein installiertes **Python 3.14** – genau diese Version, keine ältere oder neuere (fehlt es, installiert es
   Python 3.14 per winget),
2. kopiert es nach `runtime\` (ohne Doku und Tests, ~90 MB) und installiert dort die Pakete aus `requirements.txt` in
   **festen Versionen** – dieses Python nutzt nur, was in `runtime\` liegt, nichts aus dem installierten Python oder
   `%APPDATA%\Python`,
3. legt für jedes gewählte Programm (laut seiner `programm.json`) zwei `.exe` an:
   - den **Starter** zum Doppelklicken – `Toolbox.exe` im Hauptordner, `HardwareMonitor.exe` im Programmordner. Er
     findet `runtime\` und sein Skript relativ zum eigenen Ort, braucht also keine Argumente und funktioniert (samt
     Verknüpfungen) auch nach dem Verschieben. Übersetzt wird er aus `setup\starter.cs` mit `csc.exe`, dem
     C#-Compiler, den Windows im .NET Framework mitbringt.
   - eine Kopie von `pythonw.exe` mit eigener Dateibeschreibung und eigenem Symbol in `runtime\`
     (`setup\exe_anlegen.py`), die der Starter aufruft – damit die Programme im Task-Manager als „Toolbox“ und
     „Hardware-Monitor“ erscheinen statt als „Python“,
4. lädt die Downloads aus den `programm.json` (feste Version, Prüfsumme wird kontrolliert), z. B. LibreHardwareMonitor
   0.9.6 nach `programme\hardware_monitor\lhm\`,
5. nur mit Hardware-Monitor: holt **einmal** Adminrechte (UAC-Abfrage) und installiert damit PawnIO (Treiber für
   CPU- und Mainboard-Sensoren) und die geplante Aufgabe `HardwareMonitor` (startet `HardwareMonitor.exe` beim
   Anmelden mit Adminrechten, ohne Nachfrage),
6. nur mit Hardware-Monitor: startet ihn (bzw. neu, wenn er noch mit dem alten Programm lief).

Jeder Schritt prüft vorher, ob er schon erledigt ist – `Setup.exe` lässt sich also jederzeit erneut ausführen,
z. B. nach einem `git pull` (neue Pakete) oder **nach dem Verschieben des Ordners**: dann wird nur die Aufgabe neu
eingerichtet. Mit `-OhneAdmin` (im Terminal: `Setup.exe -OhneAdmin`) entfallen Schritt 5 und 6.

**Programme einzeln installieren und entfernen**: In der Toolbox unter Zahnrad → *Programme* – je Programm ein Knopf
*Installieren* bzw. *Entfernen*. Das ruft `Setup.exe -Programme <id>` bzw. `Uninstall.exe -Programme <id>` auf
(geht auch von Hand im Terminal, mehrere mit Komma). Entfernen beendet das Programm, löscht seine Aufgabe, den Starter
und die Downloads; der Code bleibt im Repo, die Einstellungen in `daten\` auch. Wer im Auswahlfenster von `Setup.exe`
ein Häkchen wegnimmt, entfernt das Programm genauso.

**`Setup.exe` und `Uninstall.exe`** liegen als einzige `.exe` fertig gebaut im Repo – nach dem Klonen gibt es ja noch
nichts, was sie bauen könnte. Es sind kleine C#-Programme aus `setup\setup_exe.cs` (nach einer Änderung dort mit
`setup\setup_exe_bauen.ps1` neu bauen und mit committen). Mit `git clone` geholt, starten sie ohne Rückfrage. Lädt man
das Repo dagegen als ZIP herunter, kann Windows SmartScreen beim ersten Start warnen („Der Computer wurde durch
Windows geschützt“, weil die `.exe` nicht signiert ist) – dann *Weitere Informationen → Trotzdem ausführen*.

**Toolbox starten**: Doppelklick auf `Toolbox.exe` – oder eine Verknüpfung darauf (Desktop, Startmenü, Taskleiste).
Den Hardware-Monitor startest du über die Toolbox (Windows fragt dabei nach Adminrechten) oder
`programme\hardware_monitor\HardwareMonitor.exe` (dann ohne Adminrechte, also ohne CPU-Werte). Autostart beim
Anmelden ist nach dem Einrichten aus – einschalten in der Toolbox auf der Seite Hardware-Monitor; dann startet ihn
auch „Starten“ ohne Nachfrage.

**Portabel**: Nach dem Einrichten steckt alles im Ordner. Verschieben oder auf einen anderen PC kopieren, dort
`Setup.exe` erneut ausführen – fertig. Außerhalb des Ordners liegen nur PawnIO (ein Treiber muss in Windows
registriert sein) und die geplante Aufgabe (speichert Windows selbst).

**Feste Versionen**: Jeder PC bekommt dieselbe Python-Version (`$PythonVersion` in `setup\setup.ps1`), dieselben
Pakete (`requirements.txt`, mit `==`) und dieselben Downloads (Version und Prüfsumme in `programm.json`). Ein neues
Release irgendwo kann so nichts kaputtmachen. Neue Versionen übernimmt man bewusst: in `runtime\` installieren,
testen, dann mit `runtime\python.exe -m pip freeze` in `requirements.txt` eintragen.

**Neues Python für `runtime\`**: `$PythonVersion` in `setup\setup.ps1` ändern, Ordner `runtime\` löschen und
`Setup.exe` ausführen.

**Aktualisieren**: In den Einstellungen der Toolbox (Zahnrad → *Aktualisieren*). Das holt den neuesten Stand von
GitHub (`git pull`, nur als Fast-Forward – eigene Änderungen werden nie überschrieben; passen sie nicht dazu, bricht
es mit einer Meldung ab) und führt danach `Setup.exe -Neustart` aus (ohne Auswahlfenster): Pakete auf den neuen
Stand bringen, die Toolbox und die eingerichteten Programme mit dem neuen Code neu starten. Neue Programme aus dem
Update erscheinen unter *Programme* zum Installieren. Von Hand geht dasselbe mit `git pull` und `Setup.exe -Neustart`.
Aktualisiert wird immer alles auf einmal – der Code aller Programme kommt mit demselben `git pull`.

Läuft die Toolbox beim Einrichten, wird sie vorher beendet (sie hält sonst Dateien in `runtime\` fest) und am Ende
wieder gestartet.

**Beenden und Neustart**: In den Einstellungen der Toolbox (Zahnrad) gibt es *Nur Toolbox* und *Toolbox und alle
Programme*, jeweils mit Neu starten und Beenden. „Alle Programme“ sind die Tools, die eigenständig weiterlaufen (z. B.
der Hardware-Monitor) – gestoppte bleiben beim Neustart gestoppt.

**Entfernen**: `Uninstall.exe` beendet Toolbox und Hardware-Monitor, löscht die Aufgabe und auf Wunsch alles Erzeugte
(`runtime\`, die Starter, `lhm\`). Danach kann der Ordner gelöscht werden. PawnIO bleibt installiert
(`winget uninstall namazso.PawnIO`). Nur einzelne Programme entfernen: siehe *Programme einzeln installieren und
entfernen* oben.

## Prüfen

```
runtime\python.exe programme\hardware_monitor\hardware_monitor.py --list
```
listet alle Sensoren auf. Läuft das im Admin-Terminal und zeigt bei der CPU echte Temperaturen, funktioniert alles.

## Detailfenster anpassen

Was im Fenster steht, steht in `programme/hardware_monitor/detailfenster_inhalt.py` – Tab für Tab, eine Zeile pro Wert:
```python
Tab("GPU",
    Gruppe("gpu",
           Wert("GPU Core", typ="Temperatur"),
           Wert("GPU Hot Spot"),
           Wert("GPU Fan *", typ="Lüfter")))       # * = beliebiger Text, hier: alle GPU-Lüfter
```
Wert hinzufügen = Zeile schreiben, Wert weglassen = Zeile löschen. Die genauen Namen zeigt `--list`. Gespeicherte Änderungen erscheinen beim nächsten Öffnen des Fensters, ohne Neustart.

## Neues Tool hinzufügen

1. Ordner `programme/<name>/` anlegen, darin das Programm.
2. Daneben den Ausweis `programm.json`:
   ```json
   {
     "id": "mein",
     "name": "Mein Programm",
     "version": "1.0",
     "kategorie": "Allgemein",
     "beschreibung": "Kurze Beschreibung",
     "seite": "mein_gui.py",
     "skript": "mein.py",
     "starter": "MeinProgramm.exe"
   }
   ```
   `kategorie` ist der Tab oben (Allgemein oder Games – `CATEGORIES` in
   `toolbox.py`). `skript` und `starter` braucht es nur, wenn das Tool ein eigenes Programm hat – `Setup.exe` legt dann `MeinProgramm.exe` an – mit dem grünen ⚒ (`toolbox/programm.ico`), oder mit eigenem
   Symbol über `"symbol": "mein.ico"`. Braucht es etwas zum Herunterladen, kommt das als `downloads` dazu (Vorbild:
   `programme/hardware_monitor/programm.json`).
3. Die Seite für die GUI (`seite`) wird mit den Bausteinen aus `toolbox/base.py` nur beschrieben, Laden und Speichern
   der Einstellungen übernimmt die Toolbox – automatisch in `daten/<id>.json`:
   ```python
   from base import Choice, Section, Text, ToolPage

   class MeinPage(ToolPage):
       defaults = {"rate": 2}

       def layout(self):
           return [Section("Aktualisierung",
                           Text("Wie oft gemessen wird."),
                           Choice("Rate", "rate", {"1 s": 1, "2 s": 2, "5 s": 5}))]

   SEITE = MeinPage
   ```
   Alle Bausteine stehen oben in `base.py` erklärt, ein volles Beispiel ist `hardware_monitor_gui.py`.
   Das eigenständige Programm selbst findet seine Datei mit `daten.einstellungen("mein")` bzw. `daten.log("mein")`.
   Hat das Tool eigene Fenster, bekommen sie als Titel den Pfad des Programms (wie der Explorer seinen Ordner) – so
   steht er im Task-Manager beim Aufklappen und zeigt, welche Kopie läuft.
   Läuft das Tool als eigenes Programm weiter (wie der Hardware-Monitor), zusätzlich
   `PROGRAMM = Programm(laeuft, beenden, starten)` angeben – dann beenden bzw. starten es
   „Toolbox und alle Programme“ in den Toolbox-Einstellungen automatisch mit.
4. Eine `programme/<name>/README.md` anlegen (was das Tool macht, Einrichtung, Bedienung, Einstellungen, Technik –
   Vorbild ist `programme/hardware_monitor/README.md`) und das Tool oben in der Tabelle eintragen.
5. Fertig – die Toolbox findet jede `programme/*/programm.json` beim Start automatisch, sortiert wird alphabetisch.

## Technisches

- **Einstellungen**: eine `.json` je Programm in `daten/` (`toolbox.json`, `hardware_monitor.json`, …), **Fehler** in
  `daten/logs/` (ignoriert git).
- **Starter**: Der Starter (`Toolbox.exe` usw.) startet `runtime\<Name>.exe` mit dem Skript und beendet sich sofort –
  im Task-Manager steht danach nur das Programm. Zusätzliche Argumente reicht er weiter, und wird er mit Adminrechten
  gestartet (Aufgabe, UAC), läuft auch das Programm mit Adminrechten.
- **GUI ↔ Hardware-Monitor**: Der Monitor läuft mit Adminrechten, die GUI ohne. Gesteuert wird über eine lokale
  Verbindung auf `127.0.0.1:47815` (Befehle `status`, `reload`, `quit`). Die GUI selbst lauscht auf Port `47816`
  (`show`, `status`, `quit`): ein zweiter Start holt damit nur das vorhandene Fenster nach vorne, `setup.ps1` beendet
  sie damit vor dem Einrichten bzw. Entfernen. Beide Ports stehen als `"port"` in der jeweiligen `programm.json` –
  daraus lesen sie Python und `setup.ps1`, ebenso den Namen der Autostart-Aufgabe (`"aufgabe"`).
- **Sparsam**: Bei geschlossenem oder minimiertem Detailfenster liest der Monitor nur CPU und GPU, bei offenem Fenster
  nur die Geräte des gewählten Tabs; Raten im Rechtsklick-Menü oder in der GUI.
  Die GPU-Temperatur fürs Icon kommt bei Nvidia direkt aus `nvml.dll` (Teil des Treibers). LHMs komplettes
  GPU-Update kostet ~90 ms pro Messung, NVML nur einen Bruchteil davon. Das gilt für „Automatisch“ und „GPU Core“, andere
  GPU-Sensoren laufen weiter über LHM. Für die Icons wird nur der eine Temperatursensor gelesen, und bei geschlossenem
  Fenster läuft der Monitor im Effizienzmodus von Windows 11 (einstellbar: Automatisch / Immer an / Aus). Hat die
  Grafik keine Temperatur (z. B. Intel-Onboard-Grafik), gibt es nur das CPU-Icon und die GPU wird nicht gelesen.
- **Schneller Start**: Zuerst werden nur CPU und GPU geöffnet (Icons nach Sekundenbruchteilen), die übrige Hardware
  lädt danach im Hintergrund nach. Allein der RAM braucht dabei ~8 s; bis dahin zeigt das Detailfenster „Lade Sensordaten …“.
- **Kein `__pycache__`**: `toolbox.py` setzt gleich am Anfang `sys.dont_write_bytecode = True`, dadurch legt Python
  für die Programmseiten und Hilfsdateien keine `__pycache__`-Ordner an. Nur beim Start als Modul
  (`python -m toolbox.toolbox`, z. B. über den Play-Button in Zed) speichert Python `toolbox.py` selbst, bevor diese
  Zeile läuft. Dagegen hilft `python -B -m toolbox.toolbox` oder einmalig für alle Python-Programme:
  ```
  setx PYTHONDONTWRITEBYTECODE 1
  ```
  (wirkt in neu geöffneten Terminals bzw. nach Neustart von Zed).
