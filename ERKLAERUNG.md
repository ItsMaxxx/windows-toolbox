# Windows-Toolbox – ausführliche Erklärung

Was hier passiert, welche Technik benutzt wird und wie du selbst weiterbauen kannst.
*Stand: Oktober 2026 – nach dem Umbau auf Programmordner, `programm.json` und Starter-`.exe`.*

Diese Datei ist zum Lernen und Nachschlagen gedacht. Sie fängt beim großen Bild an, erklärt dann die Grundlagen
(Python, GUI, Threads, Netzwerk, Windows, .NET, Sensoren, Skripte, Git) und geht danach Datei für Datei durch den
Code. Am Ende stehen Rezepte zum Weiterbauen, typische Stolperfallen, ein Glossar und alle Links gesammelt.

> **Tipp:** Lies Teil 1 und 2 ganz, die Grundlagen (Teil 3) nur dort, wo dir etwas unbekannt ist, und Teil 4 parallel
> zum jeweiligen Code im Editor. Funktionsnamen stehen in `Backticks`, damit du sie im Editor suchen kannst
> (Strg+F oder in Zed: Strg+Shift+F für das ganze Projekt).

## Inhalt

1. [Das große Bild](#1-das-große-bild)
2. [Ordner und Dateien](#2-ordner-und-dateien)
3. [Grundlagen](#3-grundlagen)
   - 3.1 Python-Sprachmittel, die im Code vorkommen
   - 3.2 Python unter Windows: `python.exe`, `pythonw.exe`, Starter, `runtime\`, `._pth`, pip
   - 3.3 GUI-Grundlagen: tkinter, ttk, CustomTkinter, Ereignisschleife
   - 3.4 Threads, Queue und die GIL
   - 3.5 Netzwerk-Grundlagen für die Fernsteuerung (TCP, localhost, Ports, JSON)
   - 3.6 Windows-Grundlagen: Adminrechte, UAC, Aufgabenplanung, Treiber, Infobereich, WinAPI
   - 3.7 .NET und pythonnet
   - 3.8 Wo die Hardware-Werte herkommen: LibreHardwareMonitor, PawnIO, NVML, WMI
   - 3.9 Batch (`.cmd`) und PowerShell (`.ps1`)
   - 3.10 Git: `.gitignore` und `.gitattributes`
4. [Der Code im Detail](#4-der-code-im-detail)
   - 4.1 `Einrichten.cmd` → `setup\setup.ps1`
   - 4.2 `Toolbox.exe` (Starter) und der Start der Toolbox
   - 4.3 `toolbox\toolbox.py` – das Hauptfenster
   - 4.4 `toolbox\base.py` – der Baukasten für Programmseiten
   - 4.5 `toolbox\winutil.py` – Windows-Helfer
   - 4.6 `toolbox\daten.py` und `toolbox\platzhalter.py`
   - 4.7 `programme\hardware_monitor\hardware_monitor_gui.py` – die Seite in der Toolbox
   - 4.8 `programme\hardware_monitor\hardware_monitor.py` – das eigentliche Programm
   - 4.9 `programme\hardware_monitor\detailfenster.py` – das Fenster mit den Werten
   - 4.10 `programme\hardware_monitor\detailfenster_inhalt.py` – was im Fenster steht
   - 4.11 `programme\hardware_monitor\hardwaredaten.py` – Hersteller, IDs, Seriennummern
   - 4.12 `Entfernen.cmd`
5. [Zusammenspiel an Beispielen](#5-zusammenspiel-an-beispielen)
6. [Rezepte zum Weiterbauen](#6-rezepte-zum-weiterbauen)
7. [Stolperfallen und Werte, die übereinstimmen müssen](#7-stolperfallen-und-werte-die-übereinstimmen-müssen)
8. [Fehlersuche und Testen](#8-fehlersuche-und-testen)
9. [Glossar](#9-glossar)
10. [Alle Links gesammelt](#10-alle-links-gesammelt)

---

## 1. Das große Bild

Das Projekt ist eine Sammlung kleiner Windows-Tools mit einer gemeinsamen Oberfläche, der „Toolbox“. Im Moment gibt
es ein echtes Tool: den Hardware-Monitor. Er zeigt CPU- und GPU-Temperatur als zwei Zahlen-Icons unten rechts in der
Taskleiste; ein Klick darauf öffnet ein Fenster mit fast allen Hardware-Werten und den festen Hardwaredaten
(Hersteller, IDs, Seriennummern).

Der wichtigste Gedanke: Es laufen **zwei getrennte Programme** (Prozesse) mit unterschiedlichen Rechten.

```
┌─────────────────────────────────┐                ┌──────────────────────────────────────────┐
│ TOOLBOX  (ohne Adminrechte)     │                │ HARDWARE-MONITOR  (mit Adminrechten)     │
│                                 │                │                                          │
│ toolbox\toolbox.py  Hauptfenster│  TCP-Verbindung│ hardware_monitor\hardware_monitor.py     │
│ toolbox\base.py     Baukasten   │  127.0.0.1:    │   - liest Sensoren (Mess-Thread)         │
│ toolbox\winutil.py  Win-Helfer  │  47815         │   - zeichnet die Tray-Icons              │
│ *_gui.py            Seiten  ────┼──────────────► │   - wartet auf Befehle (IPC-Thread)      │
│   (z. B. hardware_monitor_gui)  │ status/reload/ │   - Detailfenster (detailfenster.py)     │
│                                 │ quit           │   - Hardwaredaten (hardwaredaten.py)     │
└───────────────┬─────────────────┘                └───────────────┬──────────────────────────┘
                │ schreibt                                         │ liest
                ▼                                                  ▼
        daten\hardware_monitor.json     ◄──────────────────  (gleiche Datei)
```

- **Starten des Monitors:** Toolbox → Windows-Aufgabenplanung (Aufgabe „HardwareMonitor“ → `HardwareMonitor.exe`,
  ohne UAC-Abfrage) oder notfalls direkt mit UAC-Abfrage („Als Administrator ausführen“).
- **Jedes Programm hat einen eigenen Ordner** (`toolbox\`, `programme\hardware_monitor\`) mit einem Ausweis
  `programm.json` und eine eigene Starter-`.exe` (`Toolbox.exe`, `HardwareMonitor.exe`) – siehe Teil 2 und 4.2.

Woher die Werte kommen:

```
hardware_monitor.py ──pythonnet──► LibreHardwareMonitorLib.dll (.NET) ──► PawnIO-Treiber ──► CPU/Mainboard-Chips
                    ──ctypes────► nvml.dll (Nvidia-Treiber)            ──► GPU-Temperatur
                    ──pythonnet──► System.Management (WMI)             ──► Hersteller, IDs, Seriennummern
```

**Warum zwei Prozesse?** CPU- und Mainboard-Sensoren lassen sich nur mit Adminrechten lesen. Eine ganze GUI dauerhaft
als Admin laufen zu lassen, ist aber unschön (bei jedem Start UAC-Abfrage, mehr Risiko). Also läuft nur der kleine
Monitor als Admin, die Toolbox als normaler Benutzer. Weil Windows einem normalen Prozess verbietet, einen
Admin-Prozess zu beenden oder zu steuern, reden die beiden über eine lokale Netzwerkverbindung miteinander
(Abschnitt 3.5).

Das Einrichten erledigt `Einrichten.cmd`: Es legt ein eigenes Python im Projektordner an (`runtime\`), baut die
Starter-`.exe`, lädt LibreHardwareMonitor herunter, installiert den Treiber PawnIO und die geplante Aufgabe. Danach
ist der Ordner „portabel“: verschieben, `Einrichten.cmd` erneut ausführen, fertig.

---

## 2. Ordner und Dateien

```
windows-toolbox\
├─ Toolbox.exe             (nicht im Repo) Starter der Toolbox – Doppelklick genügt, siehe 4.2.
├─ Einrichten.cmd          Doppelklick-Starter für setup\setup.ps1 (einrichten). Beliebig oft ausführbar.
├─ Entfernen.cmd           Doppelklick-Starter für setup\setup.ps1 -Entfernen (Gegenstück).
├─ __init__.py             Macht den Ordner zum Python-Paket, damit „python -m toolbox.toolbox“ geht (Zed).
├─ requirements.txt        Python-Pakete mit FESTEN Versionen (customtkinter==6.0.0 …, samt Abhängigkeiten).
├─ README.md               Übersicht für GitHub.
├─ ERKLAERUNG.md           diese Datei.
├─ .gitignore              Was Git ignoriert (daten\, runtime\, Starter-.exe, Logs, Einstellungen, CLAUDE.md …).
├─ .gitattributes          Sorgt dafür, dass .cmd/.ps1 immer Windows-Zeilenenden (CRLF) haben.
├─ runtime\                (nicht im Repo) Wegwerfbar: Eigenes Python + Pakete. Legt Einrichten.cmd an.
│  ├─ python.exe / pythonw.exe / python314.dll / python314._pth / Lib\ / DLLs\ …
│  ├─ Toolbox.exe          pythonw.exe mit Namen „Toolbox“ und eigenem Symbol (für den Task-Manager).
│  ├─ HardwareMonitor.exe  dasselbe mit Namen „Hardware-Monitor“.
│  └─ starter\             zuletzt übersetzter Quelltext je Starter (damit er nur bei Änderungen neu gebaut wird).
├─ daten\                  (nicht im Repo) Gehört dir: Einstellungen und Logs. Das Einzige, was man sichern muss.
│  ├─ toolbox.json                    (entsteht) Einstellungen der Toolbox.
│  ├─ hardware_monitor.json           (entsteht) Einstellungen des Hardware-Monitors – eine .json je Programm.
│  └─ logs\
│     ├─ toolbox.log                  (entsteht) Fehlerprotokoll der Toolbox.
│     └─ hardware_monitor.log         (entsteht) Fehlerprotokoll des Hardware-Monitors.
├─ setup\
│  ├─ setup.ps1            Das eigentliche Einrichtungs-/Entfernen-Skript (PowerShell).
│  ├─ starter.cs           Vorlage für die Starter-.exe (C#), siehe 3.2 und 4.1.
│  └─ exe_anlegen.py       Legt runtime\Toolbox.exe / runtime\HardwareMonitor.exe an (Namen und Symbol in die Kopie).
├─ toolbox\                Die Toolbox (gemeinsame Oberfläche)
│  ├─ programm.json        Ausweis: Version, Skript, Starter (wie bei jedem Programm).
│  ├─ toolbox.py           Hauptfenster, findet Programme automatisch, Tray, Einzelinstanz.
│  ├─ base.py              Farben, Theme und Baukasten (Section, Text, Choice, Slider …, ToolPage).
│  ├─ winutil.py           UAC, unsichtbare Befehle, PowerShell, Aufgabenplanung.
│  ├─ daten.py             Wo Einstellungen und Logs liegen (daten\), zieht alte Dateien einmalig dorthin um.
│  ├─ platzhalter.py       Leere Seite für Tabs ohne Programm.
│  └─ toolbox.ico          Fenster-, Tray- und .exe-Symbol: ⚒ auf Grün (#3ddc97), wie das Logo oben links.
└─ programme\              Je Programm ein Ordner – alles, was zu ihm gehört, liegt darin.
   └─ hardware_monitor\    Das Tool „Hardware-Monitor“
      ├─ programm.json              Ausweis: id, Name, Tab, Beschreibung, Version, Seite, Skript, Starter, Downloads.
      ├─ HardwareMonitor.exe        (nicht im Repo) Starter, legt Einrichten.cmd an.
      ├─ hardware_monitor.py        Hauptprogramm (läuft eigenständig, als Admin).
      ├─ hardware_monitor_gui.py    Seine Seite in der Toolbox.
      ├─ detailfenster.py           Baut das Detailfenster (tkinter/ttk).
      ├─ detailfenster_inhalt.py    Beschreibt, WAS im Detailfenster steht – hier passt du an.
      ├─ hardwaredaten.py           Liest Hersteller/IDs/Seriennummern per WMI.
      ├─ lhm\                       (nicht im Repo) LibreHardwareMonitor – Download laut programm.json.
      └─ README.md                  Doku des Tools.
```

**Faustregel:** Alles, was beim Ausführen entsteht oder heruntergeladen wird, ist nicht im Git-Repo (siehe
`.gitignore`). Und es gibt genau drei Sorten Ordner:

| Sorte | Ordner | Bedeutung |
|---|---|---|
| Code | `toolbox\`, `programme\`, `setup\` | kommt aus dem Repo; `git pull` ersetzt ihn. Was ein Programm herunterlädt oder erzeugt (`lhm\`, Starter), liegt mit in seinem Ordner, ist aber per `.gitignore` ausgenommen. So ist ein Programm genau ein Ordner. |
| wegwerfbar | `runtime\` | löschen und `Einrichten.cmd` ausführen baut alles identisch wieder auf (feste Versionen, siehe 4.1) |
| gehört dir | `daten\` | eine `.json` je Programm und die Logs. Zum Sichern oder Umziehen reicht dieser Ordner. |

So kann man jede Sorte ersetzen, ohne die anderen anzufassen (dasselbe Prinzip wie z. B. beim Tor Browser, der
Programm und Profil strikt trennt).

### Der Ausweis `programm.json`

Beispiel Hardware-Monitor:

| Feld | Bedeutung |
|---|---|
| `id` | `"hardware_monitor"` – eindeutiger Kurzname; daraus wird auch `daten\hardware_monitor.json` |
| `name` | „Hardware-Monitor“ – Anzeige in der Seitenleiste, Dateibeschreibung der `.exe` |
| `version` | „1.0“ – Version des Programms (auch in den Eigenschaften der Starter-`.exe`) |
| `kategorie` | Tab in der Toolbox („Allgemein“ oder „Games“) |
| `beschreibung` | Untertitel auf der Programmseite |
| `seite` | Datei mit der Programmseite (`SEITE`, optional `PROGRAMM`) – siehe 4.3 |
| `skript` | das eigenständige Programm, das der Starter startet |
| `starter` | Name der Starter-`.exe`, relativ zum Ordner (bei der Toolbox `"../Toolbox.exe"` = im Hauptordner) |
| `downloads` | was `Einrichten.cmd` herunterlädt: `name`, `version`, `url`, `sha256`, `ordner`, `pruefdatei` |

Die Toolbox liest die Ausweise beim Start, `setup.ps1` beim Einrichten – die Angaben stehen nur an dieser einen Stelle.

---

## 3. Grundlagen

### 3.1 Python-Sprachmittel, die im Code vorkommen

Allgemeiner Einstieg:

- Offizielles Tutorial (englisch): https://docs.python.org/3/tutorial/
- Offizielles Tutorial (deutsch, älter): https://py-tutorial-de.readthedocs.io/
- Gute Artikel zu fast allem: https://realpython.com/

#### Module und `import`

Jede `.py`-Datei ist ein „Modul“. Mit `import base` lädt Python die Datei `base.py` – aber nur, wenn ihr Ordner in der
Suchliste `sys.path` steht. Deshalb steht am Anfang von `toolbox.py`:

```python
sys.path.insert(0, str(APP_DIR))
```

Damit findet Python `base.py`, `winutil.py` usw. – auch aus den Programmseiten in anderen Ordnern heraus.
Ein einmal geladenes Modul liegt in `sys.modules` und wird beim zweiten `import` nicht neu geladen.
`importlib` kann Module auch „von Hand“ laden (Datei → Modul) oder mit `importlib.reload()` neu laden.
→ https://docs.python.org/3/tutorial/modules.html · https://docs.python.org/3/library/importlib.html

#### `if __name__ == "__main__":`

Der Code darunter läuft nur, wenn die Datei direkt gestartet wird, nicht beim Importieren.
→ https://docs.python.org/3/library/__main__.html

#### Klassen und Vererbung

`class HardwareMonitorPage(ToolPage)` heißt: HardwareMonitorPage erbt alles von ToolPage und überschreibt einzelne
Methoden (`layout`, `on_change`, `on_show` …). `super().__init__(...)` ruft die Version der Elternklasse auf.
Klassenattribute wie `settings_file = ...` oder `defaults = {...}` stehen direkt in der Klasse und gelten für alle
Objekte, solange ein Objekt sie nicht selbst überschreibt.
→ https://docs.python.org/3/tutorial/classes.html · https://realpython.com/python3-object-oriented-programming/

#### `@dataclass`

`ToolInfo` ist eine Datenklasse: Python schreibt `__init__` usw. selbst, man listet nur die Felder auf.
→ https://docs.python.org/3/library/dataclasses.html

#### `@property`

`task_name` in `hardware_monitor_gui.py` sieht aus wie ein Attribut, ist aber eine Funktion, die bei jedem Zugriff
ausgeführt wird. → https://realpython.com/python-property/

#### `lambda` und der „Standardwert-Trick“

`lambda: self.open(FOLDER)` ist eine Mini-Funktion ohne Namen. In Schleifen sieht man oft

```python
command=lambda c=category: self.show_category(c)
```

Das `c=category` friert den aktuellen Wert ein. Ohne den Trick würden alle Lambdas am Ende den LETZTEN Wert der
Schleife sehen („late binding“).
→ https://docs.python.org/3/faq/programming.html#why-do-lambdas-defined-in-a-loop-with-different-values-all-return-the-same-result
→ https://realpython.com/python-lambda/

#### Closures (verschachtelte Funktionen)

In `alle()` (`toolbox.py`, Einstellungsseite) stehen `def work()` und `def done(fehler)` innerhalb der Methode. Sie
können die Variablen der äußeren Funktion (z. B. `tools`, `neu`) benutzen. Dieses Muster („Arbeit im Hintergrund,
danach Ergebnis anzeigen“) kommt oft vor.

#### Generatoren (`yield`)

`walk()` in `hardware_monitor.py` liefert mit `yield` Stück für Stück Geräte und Unter-Geräte, statt eine fertige
Liste zu bauen. `yield from` reicht die Ergebnisse eines verschachtelten Generators durch (Rekursion).
→ https://realpython.com/introduction-to-python-generators/

#### Comprehensions und `next(...)`

`[s for s in hw.Sensors if s.Value is not None]` baut eine Liste in einer Zeile.
`next((t for t in tools if t.id == remembered), tools[0])` = „das erste passende Element, sonst `tools[0]`“.
→ https://docs.python.org/3/tutorial/datastructures.html#list-comprehensions

#### `*args`, `**kwargs`

`Section(title, *elements)` nimmt beliebig viele Bausteine. `**Button.STYLES[b.style]` packt ein Dictionary als
benannte Parameter aus. → https://realpython.com/python-kwargs-and-args/

#### f-Strings

`f"{value:.0f} °C"` setzt den Wert ohne Nachkommastellen ein. `:g`, `:02d`, `:20` sind Formatangaben.
→ https://docs.python.org/3/library/string.html#format-specification-mini-language

#### Mengen (`set`)

`gebraucht <= gemessen` prüft „ist Teilmenge von“. `set(a) | {"cpu"}` = Vereinigung.
→ https://docs.python.org/3/tutorial/datastructures.html#sets

#### Ausnahmen (`try`/`except`) und `with`

Fast jede Stelle, die mit Windows, Dateien oder Netzwerk redet, steht in `try`/`except`, damit ein Fehler nicht das
ganze Programm abstürzen lässt. `with ... as conn:` schließt Verbindungen/Dateien automatisch.
→ https://docs.python.org/3/tutorial/errors.html

#### `json`

Einstellungen werden als JSON-Text gespeichert: `json.dumps(daten)` → Text, `json.loads(text)` → Daten.
Der Trick `json.loads(json.dumps(DEFAULT_SETTINGS))` erzeugt eine tiefe Kopie (sonst würden Änderungen an der
Kopie auch die Standardwerte verändern, weil Listen/Dicts nur „verwiesen“ werden). Auch die Ausweise
(`programm.json`) sind JSON.
→ https://docs.python.org/3/library/json.html · https://docs.python.org/3/library/copy.html

#### `pathlib`

`Path(__file__).resolve().parent` = Ordner der aktuellen Datei. `/` verbindet Pfade: `FOLDER / "lhm"`.
`.with_name("x.json")` ersetzt den Dateinamen. `.parents[1]` = zwei Ebenen höher. `.replace(ziel)` verschiebt
bzw. benennt eine Datei um (so zieht `daten.py` alte Einstellungen nach `daten\`).
→ https://docs.python.org/3/library/pathlib.html

#### `logging`

`logging.basicConfig(filename=...)` schreibt Meldungen in eine `.log`-Datei. `logging.exception(...)` schreibt
zusätzlich den kompletten Fehler-Stacktrace. Wichtig, weil `pythonw.exe` keine Konsole hat (siehe 3.2).
→ https://docs.python.org/3/howto/logging.html

#### `re` (reguläre Ausdrücke) und `fnmatch`

`re` sucht Muster in Text, z. B. `VEN_([0-9A-F]{4})` holt die Hersteller-ID aus `PCI\VEN_10DE&DEV_2805…`.
`fnmatch` ist die einfache Variante mit `*` als Platzhalter („GPU Fan *“).
→ https://docs.python.org/3/howto/regex.html · https://regex101.com/ (zum Ausprobieren, Python auswählen)
→ https://docs.python.org/3/library/fnmatch.html

#### `ctypes`

Ruft Funktionen aus Windows-DLLs (C-Funktionen) direkt aus Python auf, z. B. `ctypes.windll.kernel32.CreateMutexW`.
Strukturen aus C werden als `ctypes.Structure` mit `_fields_` nachgebaut. Siehe 3.6.
→ https://docs.python.org/3/library/ctypes.html

#### `subprocess`

Startet andere Programme (`powershell.exe`, `schtasks.exe`, `git`) und liest deren Ausgabe.
→ https://docs.python.org/3/library/subprocess.html

#### Kommentare wie `# noqa: E402`

Sagen Lint-Werkzeugen (flake8/ruff), dass ein bestimmter Hinweis hier absichtlich ignoriert wird. E402 = „import
nicht ganz oben“ – hier gewollt, weil vorher `sys.path` angepasst wird. → https://docs.astral.sh/ruff/rules/

#### Stil

→ PEP 8, der Python-Stilleitfaden: https://peps.python.org/pep-0008/

### 3.2 Python unter Windows: `python.exe`, `pythonw.exe`, Starter, `runtime\`, `._pth`, pip

#### `python.exe` vs. `pythonw.exe`

`python.exe` ist ein Konsolenprogramm (öffnet ein schwarzes Fenster bzw. nutzt das Terminal). `pythonw.exe` („w“ für
windowed) ist dasselbe Python ohne Konsole – für GUI-Programme. Nachteil: `print()` und Fehlermeldungen sieht man
nicht. Deshalb schreiben Toolbox und Monitor alles in `.log`-Dateien.
→ https://docs.python.org/3/using/windows.html

#### `runtime\Toolbox.exe` und `runtime\HardwareMonitor.exe`

`pythonw.exe` ist nur ein winziger Starter, der `python314.dll` aus demselben Ordner lädt. Eine umbenannte Kopie
funktioniert deshalb genauso – sie muss aber in `runtime\` liegen, sonst findet sie die DLL nicht („python314.dll
was not found“).

Den Namen in der App-Liste des Task-Managers nimmt Windows **nicht** aus dem Dateinamen, sondern aus der eingebauten
Versionsinfo (Feld „FileDescription“), das Symbol aus den eingebauten Symbol-Ressourcen. Bei einer reinen Kopie
stünde also weiter „Python“ mit Python-Logo da. `setup\exe_anlegen.py` ersetzt deshalb in der Kopie

- die Versionsinfo (VS_VERSIONINFO: ein Baum aus Blöcken mit Länge, Typ, Name und Wert, alles auf 4 Byte
  ausgerichtet) – FileDescription „Toolbox“ bzw. „Hardware-Monitor“, ProductName „Toolbox“,
- das Symbol: jedes Bild aus `toolbox.ico` wird eine RT_ICON-Ressource, dazu ein Verzeichnis (RT_GROUP_ICON), das
  auf sie verweist,

über die Windows-Funktionen BeginUpdateResource / UpdateResource / EndUpdateResource (kernel32, per ctypes).
Vorher wird die digitale Signatur der Python Software Foundation entfernt (Eintrag „Security“ im PE-Kopf leeren,
Signaturdaten am Dateiende abschneiden): Nach der Änderung wäre sie ungültig, und „ungültig signiert“ wirkt auf
Virenscanner verdächtiger als „unsigniert“.

Windows merkt sich Programmnamen außerdem im „MuiCache“ (Registry, `HKCU\Software\Classes\Local Settings\…\MuiCache`).
Stand dort von einer früheren reinen Kopie noch „Python“, zeigte der Task-Manager den alten Namen –
`exe_anlegen.py` löscht daher die Einträge der beiden `.exe`. Ebenso hält Windows das Symbol zwischengespeichert –
deshalb meldet `exe_anlegen.py` der Shell per `SHChangeNotify(SHCNE_UPDATEITEM)`, dass sich die Datei geändert hat.
Ein schon offener Task-Manager behält trotzdem, was er einmal geladen hat: ganz schließen und neu öffnen.
→ https://learn.microsoft.com/de-de/windows/win32/menurc/vs-versioninfo
→ https://learn.microsoft.com/de-de/windows/win32/api/winbase/nf-winbase-updateresourcew

#### Die Starter (`Toolbox.exe` im Hauptordner, `HardwareMonitor.exe` im Programmordner)

Die Kopie in `runtime\` braucht das Skript als Argument (`runtime\Toolbox.exe toolbox\toolbox.py`) – zum
Doppelklicken taugt sie also nicht, und eine Verknüpfung mit Argument enthält absolute Pfade, die nach dem
Verschieben ins Leere zeigen. Der Starter ist ein kleines eigenes C#-Programm (`setup\starter.cs`, ~40 KB): Er
rechnet von seinem eigenen Ort aus, wo `runtime\` und das Skript liegen (die Pfade sind relativ eingebaut, z. B.
`..\..\runtime` und `hardware_monitor.py`), startet die Kopie mit dem Skript und beendet sich. Dadurch:

- Doppelklick genügt, Verknüpfungen auf ihn brauchen kein Argument und überleben das Verschieben,
- im Task-Manager steht danach nur das Programm („Toolbox“), der Starter ist schon weg,
- Adminrechte vererbt er: Startet die Aufgabe (oder eine UAC-Abfrage) den Starter mit Adminrechten, läuft
  auch das Programm damit (CreateProcess ohne Shell = gleiche Rechte),
- zusätzliche Argumente reicht er weiter (z. B. `--nach <pid>` beim Neustart der Toolbox).

Übersetzt wird er von `setup.ps1` mit `csc.exe`, dem C#-Compiler des .NET Framework 4 – der gehört zu jedem
Windows 10/11, es braucht also kein Visual Studio. Name, Version und Symbol kommen über Assembly-Attribute bzw.
`/win32icon` in die `.exe`.
→ https://learn.microsoft.com/de-de/dotnet/csharp/language-reference/compiler-options/

#### Fenstertitel = Pfad

Klappt man im Task-Manager eine App auf, stehen darunter ihre Fenster mit Titel. Der Explorer zeigt dort den
Ordner, die Toolbox und das Detailfenster des Monitors genauso den Pfad ihres Programms (`toolbox.py` bzw.
`hardware_monitor.py`). Neue Tools mit eigenem Fenster sollten das genauso machen.

#### Apps vs. Hintergrundprozesse im Task-Manager

Unter „Apps“ steht nur, was ein sichtbares Fenster hat. Der Hardware-Monitor mit geschlossenem Detailfenster (nur
Tray-Icons) steht deshalb unter „Hintergrundprozesse“ – wie jedes Programm, das nur im Infobereich sitzt.

#### Bytecode und `__pycache__`

Python übersetzt `.py`-Dateien beim Import in Bytecode (`.pyc`) und speichert ihn in `__pycache__`-Ordnern. Das
Projekt will diese Ordner nicht: `sys.dont_write_bytecode = True` (bzw. Startoption `-B`) schaltet das ab.
→ https://docs.python.org/3/tutorial/modules.html#compiled-python-files

#### Das eigene Python in `runtime\`

`Einrichten.cmd` kopiert ein installiertes Python in den Projektordner. Damit der Ordner wirklich unabhängig ist,
wird es „isoliert“:

- `python314._pth`: Steht so eine Datei neben `python.exe`, nimmt Python NUR die dort aufgelisteten Suchpfade
  (`python314.zip`, `DLLs`, `Lib`) – Umgebungsvariablen wie `PYTHONPATH` zählen nicht. `import site` in der letzten
  Zeile schaltet die Paketverwaltung (site-packages) trotzdem ein.
  → https://docs.python.org/3/using/windows.html#finding-modules
- `Lib\sitecustomize.py`: Wird beim Start automatisch ausgeführt und entfernt die Pakete aus dem Benutzerordner
  (`%APPDATA%\Python`), damit wirklich nur Pakete aus `runtime\` benutzt werden.
  → https://docs.python.org/3/library/site.html

> **Wichtige Folge:** Mit `._pth` steht der Ordner des gestarteten Skripts NICHT automatisch in `sys.path`. Deshalb
> fügen `toolbox.py` und `hardware_monitor.py` ihren eigenen Ordner selbst hinzu (`sys.path.insert(0, ...)`). Wenn du
> ein neues Skript schreibst, das Nachbardateien importiert, brauchst du das auch.

#### pip und `requirements.txt`

pip installiert Pakete von PyPI (dem Python-Paketverzeichnis). `requirements.txt` listet sie, eins pro Zeile –
hier mit fester Version (`pillow==12.3.0`), auch für die Abhängigkeiten der Pakete. Ohne `==` holt pip immer die
neueste Version, und zwei PCs hätten je nach Tag der Einrichtung verschiedene Stände. Neue Versionen übernimmt man
bewusst: in `runtime\` installieren, testen, dann `runtime\python.exe -m pip freeze` nach `requirements.txt` kopieren.
`runtime\python.exe -m pip install -r requirements.txt` installiert sie in `runtime\Lib\site-packages`.
`ensurepip` bringt pip erst einmal in ein frisches Python.
→ https://pip.pypa.io/en/stable/user_guide/ · https://pip.pypa.io/en/stable/reference/requirements-file-format/ ·
https://pypi.org/

#### Wie `setup.ps1` ein installiertes Python findet (PEP 514)

Python-Installer tragen sich in der Registry ein (`HKCU/HKLM\Software\Python\PythonCore\3.x\InstallPath`).
→ https://peps.python.org/pep-0514/

#### Die vier Pakete

| Paket | Wofür | Doku |
|---|---|---|
| customtkinter | modernes Aussehen für tkinter | https://customtkinter.tomschimansky.com/ |
| pystray | Symbole im Infobereich (Tray) | https://pystray.readthedocs.io/ |
| pillow (PIL) | Bilder erzeugen/zeichnen (Icons) | https://pillow.readthedocs.io/ |
| pythonnet | .NET-Bibliotheken aus Python benutzen | https://pythonnet.github.io/ |

(tkinter selbst gehört zu Python dazu.)

### 3.3 GUI-Grundlagen: tkinter, ttk, CustomTkinter, Ereignisschleife

- Bestes Tutorial dazu (englisch, sehr gründlich): https://tkdocs.com/tutorial/
- Einsteiger-Artikel: https://realpython.com/python-gui-tkinter/
- Offizielle Doku: https://docs.python.org/3/library/tkinter.html

#### tkinter

Die GUI-Bibliothek, die mit Python kommt (Hülle um Tcl/Tk). Ein Fenster besteht aus „Widgets“ (Label, Button,
Frame, Entry …), die ineinander stecken. `tk.Tk()` ist das Hauptfenster, `tk.Toplevel()` ein weiteres Fenster.

#### ttk („themed tk“)

Modernere Widgets mit „Styles“: Aussehen wird zentral über `ttk.Style` festgelegt statt an jedem Widget. Das
Detailfenster des Monitors benutzt ttk (Notebook = Tabs, Treeview = aufklappbare Liste, Scrollbar, Button).
Das Design „clam“ ist das einzige eingebaute, das sich vollständig dunkel einfärben lässt.
→ https://docs.python.org/3/library/tkinter.ttk.html · https://tkdocs.com/tutorial/styles.html ·
https://tkdocs.com/tutorial/tree.html (Treeview)

#### CustomTkinter

Ein Paket, das tkinter mit runden Ecken, Hell-/Dunkel-Modus und modernen Widgets (CTkButton, CTkSwitch,
CTkSegmentedButton, CTkScrollableFrame …) erweitert. Farben können als Paar (hell, dunkel) angegeben werden;
CustomTkinter nimmt automatisch die passende. Die Standardfarben stehen in `ctk.ThemeManager.theme` – genau die
überschreibt `apply_theme()` in `base.py`. Die Toolbox benutzt CustomTkinter, der Monitor nicht (der ist bewusst
schlank und nimmt nur tkinter/ttk).
→ https://customtkinter.tomschimansky.com/documentation/ · https://github.com/TomSchimansky/CustomTkinter

#### Layout: `grid`, `pack`, `place`

Jedes Widget muss „platziert“ werden, sonst ist es unsichtbar:

| Methode | Wie |
|---|---|
| `grid` | Tabelle aus Zeilen/Spalten (`row=`, `column=`, `sticky="ew"` = in die Breite ziehen). Meistbenutzt hier. |
| `pack` | der Reihe nach stapeln (`side="left"`) |
| `place` | frei an Koordinaten – benutzt für die „Kopieren“-Buttons, die ÜBER der Treeview liegen |

`grid_remove()` versteckt ein Widget und merkt sich seinen Platz, `grid()` zeigt es wieder.
→ https://tkdocs.com/tutorial/grid.html · https://tkdocs.com/tutorial/concepts.html#geometry

#### Die Ereignisschleife (`mainloop`) – DAS wichtigste GUI-Konzept

`mainloop()` ist eine Endlosschleife: auf Ereignisse warten (Klick, Taste, Neuzeichnen) und die zugehörigen
Funktionen aufrufen. Solange eine deiner Funktionen läuft, steht die Schleife – das Fenster „friert ein“.
Deshalb gilt: **Alles Langsame (Netzwerk, PowerShell, Messen) gehört in einen anderen Thread** (3.4).

`widget.after(ms, funktion)` lässt die Schleife eine Funktion später aufrufen – so entstehen Timer und
regelmäßige Abfragen ohne Threads (z. B. Status alle 2 s, Queue alle 100 ms).
`bind("<Return>", funktion)` verknüpft ein Ereignis mit einer Funktion.
→ https://tkdocs.com/tutorial/eventloop.html

#### Fenster anzeigen/verstecken

`withdraw()` versteckt komplett (auch aus der Taskleiste), `deiconify()` zeigt wieder, `iconify()` minimiert.
`win.state()` liefert `"normal"`, `"zoomed"` (maximiert), `"iconic"` (minimiert) oder `"withdrawn"`.
`protocol("WM_DELETE_WINDOW", funktion)` fängt das ✕ ab – hier wird damit versteckt statt beendet.

### 3.4 Threads, Queue und die GIL

#### Thread

Ein zweiter (dritter …) Ablauf im selben Programm, der parallel läuft. `threading.Thread(target=f, daemon=True)`.
`daemon=True` heißt: Wenn das Hauptprogramm endet, wird dieser Thread einfach mit beendet.
→ https://docs.python.org/3/library/threading.html · https://realpython.com/intro-to-python-threading/

#### Goldene Regel: Nur der GUI-Thread darf Widgets anfassen

tkinter ist nicht „thread-sicher“. Ein Hintergrund-Thread darf also nicht direkt `label.configure(...)` aufrufen.
Lösung im ganzen Projekt: das Queue-Muster.

```
Hintergrund-Thread:  self.ui_queue.put(auftrag)
GUI-Thread:          poll_queue() läuft per after() alle 100 ms, holt alle Aufträge ab und führt sie aus.
```

`queue.Queue` ist eine thread-sichere Warteschlange. → https://docs.python.org/3/library/queue.html
Beispiele: `ToolboxApp.run_async` + `poll_queue` (Toolbox), `HardwareMonitorApp.poll_queue` (Monitor; dort sind
die Aufträge Texte wie `"toggle"`, `"data"`, `"reload"`, `"quit"`).

#### Event

`threading.Event` ist ein Signal zwischen Threads. Im Monitor weckt `self.wake.set()` den schlafenden Mess-Thread
sofort (statt dass er bis zur nächsten geplanten Messung wartet). `self.stop` signalisiert „Programm endet“.

#### Lock

`threading.Lock` verhindert, dass zwei Threads gleichzeitig dieselben Daten ändern/lesen (`with self.lock:`).
Benutzt für `self.latest` (letzte Messung fürs Fenster).

#### Die GIL (Global Interpreter Lock)

In (Standard-)Python kann immer nur EIN Thread gleichzeitig Python-Code ausführen. Threads helfen trotzdem, weil
die Sperre beim Warten (Netzwerk, Datei, `sleep`, viele C-Funktionen) freigegeben wird. Besonderheit hier: pythonnet
gibt die GIL nur bei .NET-METHODENaufrufen frei, nicht bei Zuweisungen an .NET-Eigenschaften. Deshalb schaltet
`enable_hardware()` die Hardware über `PropertyInfo.SetValue(...)` (eine Methode) ein statt mit
`pc.IsMemoryEnabled = True` – sonst würde während der ~8 s fürs RAM-Einlesen das ganze Programm stehen.
→ https://docs.python.org/3/glossary.html#term-global-interpreter-lock

### 3.5 Netzwerk-Grundlagen für die Fernsteuerung (TCP, localhost, Ports, JSON)

IPC = Inter-Process Communication, also „Prozesse reden miteinander“. Hier über TCP-Sockets.
→ https://de.wikipedia.org/wiki/Interprozesskommunikation

#### TCP und Sockets

Ein „Server“ öffnet einen Socket, bindet ihn an eine Adresse + Port (`bind`), wartet (`listen`, `accept`).
Ein „Client“ verbindet sich (`socket.create_connection`), schickt Bytes (`sendall`), liest die Antwort (`recv`).
→ https://docs.python.org/3/howto/sockets.html · https://realpython.com/python-sockets/ ·
https://de.wikipedia.org/wiki/Transmission_Control_Protocol

#### 127.0.0.1 (localhost)

Die Adresse „dieser Computer selbst“. Ein Server, der nur an 127.0.0.1 gebunden ist, ist von anderen PCs aus
NICHT erreichbar – deshalb ist das sicher genug für die Fernsteuerung.
→ https://de.wikipedia.org/wiki/Localhost

#### Ports

Nummern 0–65535, damit mehrere Programme auf demselben PC Verbindungen annehmen können. Hier:

| Port | Programm | Befehle |
|---|---|---|
| 47815 | Hardware-Monitor | `status` / `reload` / `quit` |
| 47816 | Toolbox | `show` / `show <programm-id>` / `status` / `quit` – „show“ holt bei einem zweiten Start das vorhandene Fenster nach vorne, „show hardware_monitor“ schickt das ⚙ im Detailfenster des Monitors, „status“ und „quit“ benutzt `setup.ps1`, um eine laufende Toolbox vor dem Einrichten/Entfernen zu beenden |

Ein Port kann nur von EINEM Programm gleichzeitig belegt werden. Genau das nutzt die Toolbox zur
Einzelinstanz-Erkennung: Antwortet jemand auf 47816, läuft schon eine Toolbox.

#### Das eigene Protokoll

Pro Verbindung genau ein Befehl als Textzeile (`status\n`), Antwort ist eine JSON-Zeile, dann wird geschlossen.

```
status  → {"ok": true, "pid": 1234, "cpu": 52.0, "gpu": 41.0, "order": ["cpu", "gpu"], "icons": ["cpu", "gpu"]}
          (icons = die angezeigten Icons; ohne GPU-Temperatur nur ["cpu"])
reload  → {"ok": true}   (Monitor liest danach daten\hardware_monitor.json neu)
quit    → {"ok": true}   (Monitor beendet sich)
```

JSON = einfaches Textformat für Daten (Zahlen, Texte, Listen, Objekte). → https://www.json.org/json-de.html

#### Warum nicht einfach den Prozess beenden?

Siehe 3.6 „Integritätsstufen“: Ein normaler Prozess darf einen Admin-Prozess nicht beenden. Eine höfliche Bitte
über einen Socket geht aber.

### 3.6 Windows-Grundlagen: Adminrechte, UAC, Aufgabenplanung, Treiber, Infobereich, WinAPI

#### Adminrechte und UAC

Auch ein Admin-Konto arbeitet normalerweise mit eingeschränkten Rechten. Erst „Als Administrator ausführen“ startet
ein Programm mit vollen Rechten – vorher fragt die Benutzerkontensteuerung (UAC) nach.
→ https://learn.microsoft.com/de-de/windows/security/application-security/application-control/user-account-control/

#### Integritätsstufen

Windows teilt Prozesse in Stufen ein: normale Programme „Mittel“, Admin-Programme „Hoch“. Ein Prozess mit
niedrigerer Stufe darf einen höheren nicht beenden, steuern oder ihm Fensternachrichten schicken. Darum braucht die
Toolbox (Mittel) den Socket, um den Monitor (Hoch) zu steuern.
→ https://learn.microsoft.com/de-de/windows/win32/secauthz/mandatory-integrity-control

#### Programm mit UAC-Abfrage starten

`winutil.run_elevated()` ruft die Windows-Funktion ShellExecuteExW mit dem „Verb“ `runas` auf – das ist genau
„Als Administrator ausführen“. In PowerShell heißt das `Start-Process -Verb RunAs`.
→ https://learn.microsoft.com/de-de/windows/win32/api/shellapi/nf-shellapi-shellexecuteexw

#### Aufgabenplanung (Task Scheduler)

Windows kann Programme zu bestimmten Anlässen starten („Bei Anmeldung“). Eine Aufgabe kann „mit höchsten
Privilegien“ laufen – dann startet sie als Admin OHNE UAC-Abfrage, weil man beim Anlegen der Aufgabe schon einmal
Adminrechte bestätigt hat. Das ist der Trick, mit dem der Monitor bei jeder Anmeldung ohne Nachfrage startet. Die
Aufgabe startet den Starter `HardwareMonitor.exe` (ohne Argumente), der die Rechte an den Monitor weitergibt.
Anlegen braucht Adminrechte; Starten einer vorhandenen Aufgabe (`schtasks /run`) nicht.
Ansehen: Startmenü → „Aufgabenplanung“ → Aufgabenplanungsbibliothek → HardwareMonitor.
→ https://learn.microsoft.com/de-de/windows/win32/taskschd/task-scheduler-start-page
→ https://learn.microsoft.com/en-us/powershell/module/scheduledtasks/register-scheduledtask

#### Treiber (PawnIO)

Temperaturen und Spannungen von CPU und Mainboard stecken in Hardware-Registern, die nur der Windows-Kern
(Kernelmodus) lesen darf. Ein Treiber ist Code, der dort läuft. PawnIO ist ein kleiner, signierter Treiber, über den
LibreHardwareMonitor diese Register liest (früher wurde dafür WinRing0 benutzt, das als unsicher gilt).
Er ist als Windows-Dienst namens „PawnIO“ registriert – daran erkennt `setup.ps1`, ob er installiert ist.
→ https://pawnio.eu/ · https://github.com/namazso/PawnIO

#### Infobereich (Tray)

Die kleinen Symbole unten rechts neben der Uhr. pystray legt dort Symbole an; jedes Symbol ist ein Bild (hier
64×64 Pixel, von Windows verkleinert), hat einen Tooltip (`title`) und ein Rechtsklick-Menü.
→ https://pystray.readthedocs.io/en/latest/usage.html

#### Windows-Funktionen über ctypes (WinAPI) – was im Code benutzt wird

| Funktion | Wofür |
|---|---|
| [CreateMutexW](https://learn.microsoft.com/de-de/windows/win32/api/synchapi/nf-synchapi-createmutexw) | benannter „Mutex“ als Einzelinstanz-Sperre des Monitors. Existiert er schon (Fehler 183 = ERROR_ALREADY_EXISTS), läuft der Monitor bereits. |
| [SetProcessInformation](https://learn.microsoft.com/de-de/windows/win32/api/processthreadsapi/nf-processthreadsapi-setprocessinformation) | + PowerThrottling = Effizienzmodus von Windows 11 (Blatt-Symbol im Task-Manager), siehe auch [EcoQoS](https://devblogs.microsoft.com/performance-diagnostics/introducing-ecoqos/) |
| [SetPriorityClass](https://learn.microsoft.com/de-de/windows/win32/api/processthreadsapi/nf-processthreadsapi-setpriorityclass) | Prozess-Priorität (IDLE = niedrigste, NORMAL) |
| [SetProcessDpiAwareness](https://learn.microsoft.com/de-de/windows/win32/hidpi/high-dpi-desktop-application-development-on-windows) | sagt Windows, dass das Programm mit 125/150 % Skalierung umgehen kann (sonst unscharf) |
| [DwmSetWindowAttribute](https://learn.microsoft.com/de-de/windows/win32/api/dwmapi/nf-dwmapi-dwmsetwindowattribute) | (Attribut 20) dunkle Titelleiste |
| [MonitorFromPoint](https://learn.microsoft.com/de-de/windows/win32/api/winuser/nf-winuser-monitorfrompoint) / GetMonitorInfoW | welcher Bildschirm an einer Position ist und wo dort die Taskleiste NICHT ist |
| [SetCurrentProcessExplicitAppUserModelID](https://learn.microsoft.com/de-de/windows/win32/shell/appids) | eigene App-ID, damit die Taskleiste das Toolbox-Symbol statt des Python-Symbols zeigt |
| WaitForSingleObject / GetExitCodeProcess | warten, bis ein gestarteter Prozess fertig ist, und seinen Rückgabewert holen |

Wie man so etwas liest: In der Microsoft-Doku steht die C-Signatur (z. B. `BOOL ShellExecuteExW(SHELLEXECUTEINFOW
*pExecInfo)`). In Python baut man die Struktur mit `ctypes.Structure` nach und ruft
`ctypes.windll.<dll>.<Funktion>(...)` auf. Zahlen wie `0x40` oder `183` sind Konstanten aus der Doku.

#### Codepages

Konsolenprogramme wie PowerShell/schtasks geben Text auf deutschem Windows in der „OEM-Codepage“ 850 aus, nicht in
UTF-8. Deshalb liest `winutil.run_hidden()` mit `encoding="oem"` – sonst gingen Umlaute kaputt.
→ https://de.wikipedia.org/wiki/Codepage_850

### 3.7 .NET und pythonnet

.NET ist Microsofts Plattform für Programme in C# & Co. LibreHardwareMonitor ist eine .NET-Bibliothek (DLL), und
Windows bringt mit System.Management eine .NET-Bibliothek für WMI mit. (Auch die Starter-`.exe` sind kleine
.NET-Programme, siehe 3.2.)
→ https://learn.microsoft.com/de-de/dotnet/core/introduction

pythonnet macht .NET-Klassen in Python benutzbar:

```python
import clr                                     # „clr“ = Common Language Runtime, kommt von pythonnet
clr.AddReference("LibreHardwareMonitorLib")    # DLL laden (muss in sys.path liegen → sys.path.append(LHM_DIR))
from LibreHardwareMonitor.Hardware import Computer
pc = Computer()                                # .NET-Objekt, benutzbar wie ein Python-Objekt
```

.NET-Enums (z. B. `SensorType.Temperature`) sind keine Texte; `enum_table()`/`enum_name()` übersetzen sie in Namen.
Reflection: `pc.GetType().GetProperty("IsCpuEnabled").SetValue(pc, True)` setzt eine Eigenschaft über ihren Namen
(siehe GIL in 3.4).
→ https://pythonnet.github.io/pythonnet/python.html
→ https://learn.microsoft.com/de-de/dotnet/api/system.reflection.propertyinfo.setvalue

> **Wichtig:** LHM gibt es in zwei Varianten. Benutzt wird `LibreHardwareMonitor.zip` (für das .NET Framework, das in
> Windows eingebaut ist und das pythonnet standardmäßig lädt), NICHT die .NET-10-Variante – dafür müsste .NET 10 extra
> installiert und pythonnet anders konfiguriert werden.

### 3.8 Wo die Hardware-Werte herkommen: LibreHardwareMonitor, PawnIO, NVML, WMI

#### LibreHardwareMonitor (LHM)

Freies Programm/Bibliothek, das fast alle Sensoren eines PCs liest.
→ https://github.com/LibreHardwareMonitor/LibreHardwareMonitor

Aufbau der Daten:

| Teil | Bedeutung |
|---|---|
| `Computer` | Einstiegspunkt. Schalter wie `IsCpuEnabled`, `IsGpuEnabled`, `IsMemoryEnabled` … sagen, welche Hardware-Gruppen gelesen werden. `pc.Open()` startet, `pc.Close()` räumt auf. |
| `pc.Hardware` | Liste der Geräte (IHardware): Name, HardwareType (Cpu, GpuNvidia, Memory, Motherboard, Storage, Network …), Identifier (eindeutige ID wie „/amdcpu/0“) |
| `hw.SubHardware` | Unter-Geräte, z. B. der Sensor-Chip (SuperIO) auf dem Mainboard |
| `hw.Sensors` | Liste der Sensoren (ISensor): Name („Core (Tctl/Tdie)“), SensorType (Temperature, Load, Clock, Power, Voltage, Fan …), Value (Zahl oder None) |
| `hw.Update()` | **Wichtig:** Liest die Werte neu von der Hardware. Ohne `Update()` bleiben die alten Werte stehen. `Update()` kostet Zeit – darum wird nur aktualisiert, was gerade gebraucht wird. |

Die Sensornamen hängen von deiner Hardware und der LHM-Version ab. Deshalb ist die Version in
`programme\hardware_monitor\programm.json` fest (0.9.6, mit Prüfsumme), und `hardware_monitor.py --list` zeigt alle
Namen deines PCs.

#### Begriffe bei AMD-CPUs (dein Ryzen 5 5600X)

| Begriff | Bedeutung |
|---|---|
| Tctl/Tdie | Steuertemperatur / echte Chiptemperatur (bei manchen Ryzen hat Tctl einen festen Aufschlag) |
| CCD | „Core Complex Die“ – der Chip mit den Kernen |
| SVI2 TFN | Spannungs-/Stromwerte, die der Spannungsregler an die CPU meldet |

Die Erklärtexte dazu stehen in `detailfenster_inhalt.py` (`ERKLAERUNGEN`).

#### NVML (Nvidia Management Library)

`nvml.dll` gehört zum Nvidia-Treiber. Die Funktion `nvmlDeviceGetTemperature` liefert die GPU-Temperatur fast ohne
Aufwand. LHMs komplettes GPU-Update dauert dagegen ~90 ms. Darum holt der Monitor die GPU-Temperatur fürs Icon bei
Nvidia-Karten direkt aus `nvml.dll` (über ctypes) – solange als Sensor „Automatisch“ oder „GPU Core“ gewählt ist.
→ https://docs.nvidia.com/deploy/nvml-api/

#### SMBus

Über diesen langsamen Bus liest LHM Daten der RAM-Riegel – daher die ~8 s beim Öffnen der RAM-Gruppe.
→ https://de.wikipedia.org/wiki/System_Management_Bus

#### WMI (Windows Management Instrumentation)

Eine Art Datenbank, in der Windows Infos über Hardware und System bereitstellt. Abgefragt wird mit WQL, einer
SQL-ähnlichen Sprache: `SELECT Name, ProcessorId FROM Win32_Processor`. Braucht keine Adminrechte.
Benutzte Klassen: Win32_Processor, Win32_VideoController, Win32_BaseBoard, Win32_BIOS, Win32_PhysicalMemory,
MSFT_PhysicalDisk (anderer „Namespace“: `root\Microsoft\Windows\Storage`), Win32_NetworkAdapter,
MSFT_NetAdapter (`root\StandardCimv2`, nur für die Art: LAN/WLAN – Win32_NetworkAdapter meldet WLAN als „Ethernet“),
Win32_SoundDevice, Win32_PnPEntity.

#### DXCore

Windows-Schnittstelle zu den Grafikchips (Teil von DirectX). Der Hardware-Monitor fragt darüber nur ab, ob eine GPU
integriert (im Prozessor) oder extern (eGPU) ist – das steht in WMI nicht, und am Namen sieht man es nicht sicher
(„Intel Arc Graphics“ ist integriert, „Intel Arc A770“ eine Steckkarte). DXCore ist eine COM-Schnittstelle; ohne
fertige Python-Anbindung ruft `gpu_arten()` die Methoden per `ctypes` direkt über ihre Nummer in der Methodentabelle
(vtable) auf. Gibt es DXCore nicht (Windows 10 vor Version 2004), fehlt das Feld „Art“ einfach.
→ https://learn.microsoft.com/de-de/windows/win32/dxcore/dxcore
→ https://learn.microsoft.com/de-de/windows/win32/api/dxcore_interface/ne-dxcore_interface-dxcoreadapterproperty
→ https://learn.microsoft.com/de-de/windows/win32/wmisdk/about-wmi
→ https://learn.microsoft.com/de-de/windows/win32/wmisdk/wql-sql-for-wmi
→ https://learn.microsoft.com/de-de/windows/win32/cimwin32prov/win32-processor (Beispiel für eine Klasse)
→ https://learn.microsoft.com/de-de/windows-hardware/drivers/storage/msft-physicaldisk
→ https://learn.microsoft.com/de-de/dotnet/api/system.management.managementobjectsearcher

Selbst ausprobieren in PowerShell: `Get-CimInstance Win32_Processor | Format-List *`

#### Hardware-IDs (PCI/USB)

Jedes Gerät meldet sich mit einer Kennung wie `PCI\VEN_10DE&DEV_2805&SUBSYS_…&REV_A1`:
VEN = Hersteller (10DE = Nvidia), DEV = Chip, SUBSYS = Kartenmodell + Platinenhersteller, REV = Revision.
Bei USB: VID (Hersteller) und PID (Produkt). Vollständige Listen:
→ https://pci-ids.ucw.cz/ · http://www.linux-usb.org/usb.ids

### 3.9 Batch (`.cmd`) und PowerShell (`.ps1`)

#### `.cmd` (Batch-Dateien)

Uralte, aber überall laufende Skriptsprache von `cmd.exe`. Doppelklick führt sie aus. Hier nur als „Starter“ für
`setup.ps1`:

| Befehl | Bedeutung |
|---|---|
| `@echo off` | Befehle nicht mit anzeigen |
| `rem …` | Kommentar |
| `chcp 65001` | Konsole auf UTF-8 umstellen (damit Umlaute richtig erscheinen) |
| `%~dp0` | Ordner, in dem die `.cmd`-Datei liegt (mit `\` am Ende) – macht alles verschiebbar |
| `%*` | alle Argumente weiterreichen (z. B. `-OhneAdmin`) |
| `set "PSModulePath="` | Umgebungsvariable leeren (siehe unten) |
| `pause` | „Drücken Sie eine beliebige Taste …“ |

→ https://ss64.com/nt/ · https://ss64.com/nt/syntax-args.html (`%~dp0`)
→ https://learn.microsoft.com/de-de/windows-server/administration/windows-commands/chcp

#### PowerShell

Modernere Skriptsprache von Microsoft. Es gibt zwei Varianten:

- **Windows PowerShell 5.1** (`powershell.exe`) – in jedem Windows eingebaut. Wird hier benutzt.
- **PowerShell 7** (`pwsh.exe`) – neuer, muss installiert werden.

Fallstricke, die im Projekt berücksichtigt sind:

- ExecutionPolicy: Windows blockiert standardmäßig `.ps1`-Skripte. `-ExecutionPolicy Bypass` erlaubt es nur für
  diesen einen Aufruf. → https://learn.microsoft.com/de-de/powershell/module/microsoft.powershell.core/about/about_execution_policies
- Doppelklick auf `.ps1` öffnet sie im Editor statt sie auszuführen → deshalb die `.cmd`-Starter.
- PowerShell 5.1 liest `.ps1`-Dateien ohne BOM als ANSI → Umlaute kaputt. Deshalb ist `setup.ps1` als UTF-8 MIT BOM
  gespeichert (BOM = unsichtbare Markierung „das ist UTF-8“ am Dateianfang). → https://de.wikipedia.org/wiki/Byte_Order_Mark
- Startet man `Einrichten.cmd` aus einem PowerShell-7-Terminal, erbt `powershell.exe` dessen `PSModulePath` und lädt
  falsche Module (dann fehlt z. B. `Get-FileHash`). `set "PSModulePath="` verhindert das.
- PowerShell 5.1 wertet Text auf stderr als Fehler – daher kurz `$ErrorActionPreference = 'Continue'` bei pip.
- Eigenschaften unterscheiden nicht zwischen Groß- und Kleinschreibung: `$p.Skript` und `$p.skript` sind dasselbe.
  Deshalb heißen die berechneten Pfade in `setup.ps1` `SkriptPfad`, `StarterPfad`, `HostPfad`.

Benutzte Befehle (Cmdlets): Get-ScheduledTask, Register-/Unregister-/Disable-/Start-ScheduledTask, Start-Process,
Get-Service, Get-Content/ConvertFrom-Json (Ausweise lesen), Invoke-WebRequest (Download), Get-FileHash (Prüfsumme),
Expand-Archive (ZIP entpacken), Unblock-File, Move-Item, Remove-Item, Get-ItemProperty (Registry).
→ https://learn.microsoft.com/de-de/powershell/scripting/overview
→ https://learn.microsoft.com/de-de/powershell/scripting/whats-new/differences-from-windows-powershell
→ https://learn.microsoft.com/de-de/powershell/module/microsoft.powershell.utility/unblock-file

#### Weitere Windows-Werkzeuge im Setup

| Werkzeug | Wofür |
|---|---|
| [winget](https://learn.microsoft.com/de-de/windows/package-manager/winget/) | Paketmanager von Windows (installiert Python, PawnIO) |
| [robocopy](https://learn.microsoft.com/de-de/windows-server/administration/windows-commands/robocopy) | robustes Kopieren mit Ausschlüssen (`/XD` Ordner, `/XF` Dateien); Rückgabewert < 8 = Erfolg |
| csc.exe | C#-Compiler des .NET Framework (`%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe`), baut die Starter |
| [SHA-256](https://de.wikipedia.org/wiki/SHA-2) | Prüfsumme: Ist der Download Byte für Byte die erwartete Datei? (Schutz vor Manipulation) |
| „Mark of the Web“ | Aus dem Internet geladene Dateien bekommen eine Markierung; .NET lädt solche DLLs nicht. `Unblock-File` entfernt sie. |

#### `-EncodedCommand` (in `winutil.register_task`)

PowerShell-Befehle als Base64 (aus UTF-16LE-Text) übergeben – dann können Anführungszeichen und Leerzeichen in
Pfaden beim Weiterreichen nichts kaputt machen.
→ https://learn.microsoft.com/de-de/powershell/module/microsoft.powershell.core/about/about_powershell_exe

### 3.10 Git: `.gitignore` und `.gitattributes`

- Git-Buch (deutsch): https://git-scm.com/book/de/v2
- **`.gitignore`**: Muster für Dateien, die Git nie aufnehmen soll (`daten/`, `runtime/`, `/Toolbox.exe`,
  `programme/*/*.exe`, `lhm/`, `__pycache__/`, `CLAUDE.md`, `.claude/`). → https://git-scm.com/docs/gitignore
- **`.gitattributes`**: `*.cmd text eol=crlf` – diese Dateien bekommen beim Auschecken immer Windows-Zeilenenden
  (CRLF = `\r\n`). `cmd.exe` kommt mit reinen LF-Zeilenenden (Linux-Stil) nicht zuverlässig klar.
  → https://git-scm.com/docs/gitattributes
- Alltag: `git status` · `git add <datei>` · `git commit -m "Text"` · `git push` · `git log --oneline`.
  Vorher kurz `git diff` ansehen, was sich geändert hat.

---

## 4. Der Code im Detail

### 4.1 `Einrichten.cmd` → `setup\setup.ps1`

`Einrichten.cmd` startet nur:

```
powershell.exe -NoProfile -ExecutionPolicy Bypass -File setup\setup.ps1 %*
```

(`-NoProfile`: das persönliche PowerShell-Profil nicht laden → gleiches Verhalten auf jedem PC.)

`setup.ps1` hat diese Betriebsarten (Parameter ganz oben in `param(...)`):

| Aufruf | Bedeutung |
|---|---|
| (ohne) | Einrichten |
| `-Entfernen` | Gegenstück |
| `-OhneAdmin` | Einrichten ohne Schritt 6 und 7 |
| `-Neustart` | lief der Hardware-Monitor, ihn in Schritt 7 auf jeden Fall neu starten – übergeben „Aktualisieren“ und „Neu einrichten“ in den Toolbox-Einstellungen |
| `-Admin a,b` | INTERN: der Teil, der Adminrechte braucht. Das Skript startet sich dafür selbst noch einmal mit UAC-Abfrage (Funktion `Als-Admin`) und wartet auf dessen Ende/Exitcode. |

Oben stehen Variablen für Pfade und Konstanten (`$Aufgabe = 'HardwareMonitor'`, `$IpcPort = 47815`,
`$PythonVersion = '3.14'`, Pfad zu `csc.exe`). Was je Programm gilt – Skript, Starter, Downloads mit URL und
SHA-256-Prüfsumme – steht nicht hier, sondern in den `programm.json`. `$ErrorActionPreference = 'Stop'` sorgt
dafür, dass jeder Fehler das Skript abbricht statt still weiterzulaufen.

**Grundprinzip: idempotent.** Jeder Schritt prüft erst, ob er schon erledigt ist. Man kann das Skript also beliebig
oft laufen lassen; es macht nur, was fehlt.

#### Vorab – die Ausweise lesen

`Lade-Programm` liest `toolbox\programm.json` und jede `programme\*\programm.json` (`ConvertFrom-Json`) und rechnet
die fertigen Pfade dazu: `SkriptPfad`, `StarterPfad`, `HostPfad` (die Kopie in `runtime\`, gleicher Dateiname wie
der Starter). Die Schritte 3 und 4 laufen für jedes Programm darin – ein neues Programm braucht keine Zeile in
`setup.ps1`. Programme ohne `starter` (nur eine Seite in der Toolbox) bekommen keine Pfade und keine `.exe`.

#### Vor Schritt 1 – Toolbox beenden

Fragt die Toolbox auf Port 47816 nach „status“. Läuft sie, bekommt sie „quit“ (`Toolbox-Beenden`): Sie hält sonst
Dateien in `runtime\` fest (Pakete, `Toolbox.exe`). Ganz am Ende wird sie dann wieder gestartet (`Toolbox-Starten`,
über den Starter).

#### Schritt 1 – Python finden

Welche Version, steht oben in `$PythonVersion` (3.14) – GENAU diese, keine ältere oder neuere: Die festen
Paketversionen in `requirements.txt` sind nur mit ihr geprüft.
Ist `runtime\python.exe` schon da → nur prüfen, ob es diese Version ist (`Runtime-Version`; sonst Warnung:
`runtime\` löschen und neu einrichten). Sonst sucht `Finde-Python` in der Registry (PEP 514) genau den Schlüssel
`PythonCore\3.14`. Gibt es ihn nicht, installiert winget Python 3.14 für den Benutzer.

#### Schritt 2 – `runtime\` anlegen (nur wenn noch nicht da)

- robocopy kopiert das installierte Python, OHNE Doku, Tests, Header, Scripts, vorhandene Pakete und `__pycache__`.
- `python314._pth` wird geschrieben (Suchpfade festlegen, siehe 3.2).
- `Lib\sitecustomize.py` wird geschrieben (Benutzer-Pakete ausblenden).
- ensurepip installiert pip.

Danach (IMMER): Prüfung `import ssl` – ohne ssl (z. B. wenn beim Kopieren `libcrypto-3.dll` fehlte) kann pip nichts
von PyPI laden, dann lieber gleich ein klarer Abbruch. Dann `pip install -r requirements.txt` (bringt die Pakete
genau auf die Versionen dort, z. B. nach `git pull` – auch abwärts) und eine Prüfung
`import tkinter, customtkinter, pystray, PIL, clr`. Schlägt die fehl → Abbruch mit Hinweis.

#### Schritt 3 – je Programm: `runtime\<Name>.exe` und der Starter

1. `setup\exe_anlegen.py` (siehe 3.2): Kopie von `runtime\pythonw.exe` mit eigenem Namen und Symbol.
   Das Skript baut die neue Datei als `….exe.neu` und vergleicht sie Byte für Byte mit der vorhandenen – gleich →
   „schon aktuell“. Läuft das Programm gerade, ist die Datei gesperrt → Exitcode 2. Beim Hardware-Monitor beendet
   `setup.ps1` ihn dann per „quit“, versucht es bis zu 10 s lang erneut (der Prozess räumt nach dem Beenden noch
   kurz auf) und startet ihn in Schritt 7 neu. Bei der Toolbox gibt es nur eine Warnung – sie muss man selbst
   schließen.
2. `Starter-Bauen`: `setup\starter.cs` nehmen, die `%PLATZHALTER%` ersetzen (Name, Version, relativer Weg zu
   `runtime\` und zum Skript – `Relativ` rechnet ihn über `[Uri]::MakeRelativeUri` aus, weil Windows PowerShell 5.1
   kein `GetRelativePath` kennt), mit `csc.exe` übersetzen. Den übersetzten Quelltext merkt es sich in
   `runtime\starter\` – ist er beim nächsten Mal gleich, bleibt die `.exe`, wie sie ist (csc baut jedes Mal eine
   leicht andere Datei, ein Byte-Vergleich wie in 1. ginge deshalb nicht). Klappt das Übersetzen nicht, gibt es nur
   eine Warnung – die Programme starten dann weiter direkt über `runtime\`.

#### Schritt 4 – je Programm: Downloads aus `programm.json`

Für jeden Eintrag in `"downloads"` (beim Hardware-Monitor: LibreHardwareMonitor nach
`programme\hardware_monitor\lhm\`):

- Liegt der Ordner noch an einem früheren Ort (`runtime\lhm\` bzw. `src\hardware_monitor\lhm\` aus älteren
  Versionen), wird er verschoben – ein laufender Monitor hält die DLLs fest und wird dafür kurz beendet (Schritt 7
  startet ihn neu).
- Ist die `pruefdatei` da: Version prüfen (nur Warnung bei Abweichung).
- Sonst: ZIP laden, SHA-256 vergleichen (bei Abweichung: löschen und Abbruch), entpacken, `Unblock-File`.

#### Schritt 5 – Verknüpfungen „Windows Toolbox“

Im Auswahlfenster gibt es unter den Programmen zwei Kästchen: *Verknüpfung auf dem Desktop* und *Verknüpfung im
Startmenü*. Eine Verknüpfung (`.lnk`) ist eine kleine Datei, die auf ein Programm zeigt – hier auf `Toolbox.exe`, mit
deren Symbol. `Verknuepfungen-Einrichten` legt sie über das COM-Objekt `WScript.Shell` an (`CreateShortcut`, `Save`),
das gehört zu Windows. Die Ordner liefert `[Environment]::GetFolderPath('Desktop')` bzw. `('Programs')` – so landet
sie auch dann richtig, wenn OneDrive den Desktop verschoben hat; das Startmenü des Benutzers braucht keine
Adminrechte. Der Name steht oben in `$VerknuepfungName`.

Anders als `Toolbox.exe` selbst enthält eine Verknüpfung einen **festen Pfad**. Deshalb:

- Ein Kästchen ist vorausgewählt, wenn es „unsere“ Verknüpfung schon gibt (`Verknuepfung-Unsere`: zeigt auf diesen
  Ordner oder ins Leere, weil der Ordner verschoben wurde). Häkchen weg → gelöscht.
- Ohne Fenster (`-Neustart` – also „Neu einrichten“ und „Aktualisieren“ –, `-Programme`) bleibt jede, wie sie ist:
  Steht sie noch und zeigt hierher → „schon da“; zeigt sie ins Leere → wieder auf diesen Ordner. Hast du sie selbst
  gelöscht oder woandershin verschoben, kommt sie nicht wieder – Setup sieht nur den festen Platz und deutet „fehlt“
  als „so gewollt“. Zurückholen: Kästchen in `Setup.exe`.
- Zeigt sie auf eine andere Toolbox, die es noch gibt (zweiter Klon), wird sie nie gelöscht – ersetzt nur, wenn man
  das Kästchen ausdrücklich anhakt.

#### Schritt 6 – Adminrechte: PawnIO und Aufgabe

Prüft: Gibt es den Dienst „PawnIO“? Gibt es die Aufgabe, und zeigt sie auf DIESEN Ordner (Execute =
`programme\hardware_monitor\HardwareMonitor.exe`, ohne Argumente)? Was fehlt, kommt in eine Liste, und nur dann gibt
es EINE UAC-Abfrage (`Als-Admin`). Im Admin-Durchlauf (`Admin-Schritte`):

- **pawnio**: `winget install namazso.PawnIO`
- **aufgabe**: ruft `runtime\python.exe` mit einem Python-Einzeiler (`$PyAufgabe`) auf, der
  `winutil.task_command()` benutzt – GENAU denselben Befehl wie der Knopf „Aufgabe einrichten“ in der Toolbox. So
  gibt es die Aufgaben-Definition nur an einer Stelle. Windows legt eine Aufgabe immer aktiv an – deshalb schaltet
  `task_command()` sie gleich wieder aus, wenn es sie vorher nicht gab (Autostart ist nach dem ersten Einrichten
  aus) oder sie deaktiviert war (Autostart bewusst aus). Nur eine Aufgabe, die schon an war, bleibt an.
- **autostart-an / autostart-aus / monitor-starten**: gehören zu Schritt 7 (zurückstellen, wie es vorher war).

Nach dem Verschieben des Ordners zeigt die Aufgabe auf den alten Ort → nur dieser Schritt wird wiederholt.

#### Schritt 7 – Alles wie vorher

Ganz am Anfang von `Einrichten`, bevor irgendetwas passiert, hält `Zustand-Merken` fest, was der Nutzer eingestellt
hat und das Einrichten anfassen könnte:

- **Autostart** an oder aus (`Autostart` liest die Aufgabe) – die liegt in Windows, nicht in `daten\`.
- **ob der Hardware-Monitor lief** (per Socket „status“, Funktion `Monitor-Befehl` – das PowerShell-Gegenstück zu
  `ipc()` in Python). Ob die Toolbox lief, merkt sich `Einrichten` selbst (`$toolboxLief`).
- **die Einstellungsdateien in `daten\`** (Text jeder `.json`, außer `installiert.json` – die schreibt Einrichten ja
  selbst).

Die Schritte 1–6 laufen in `Einrichten-Schritte`, und zwar in `try { … } finally { … }`: `Zustand-Abgleichen` und
der Neustart der Toolbox kommen also auch dann, wenn unterwegs etwas abbricht. `Zustand-Abgleichen`:

- **Autostart** wie vorher (gab es die Aufgabe nicht: aus). Weicht er ab, kommt `autostart-an`/`autostart-aus` in
  den Admin-Durchlauf – die Aufgabe läuft mit Adminrechten, ohne die lässt sie sich nicht ändern.
- **Hardware-Monitor**: Lief er vorher, läuft er danach wieder. Musste er neu starten (`-Neustart` nach einem Update,
  in Schritt 3 für die neue `.exe` beendet, Aufgabe auf einen neuen Ordner umgestellt), wird er per „quit“ beendet
  (`Monitor-Beenden` wartet bis zu 5 s) und neu gestartet – sonst liefe nach einem `git pull` noch der alte Code
  weiter. Gestartet wird über die Aufgabe (ohne Nachfrage), wenn Autostart an ist, sonst per `monitor-starten` im
  Admin-Durchlauf (eine UAC-Abfrage – ohne Adminrechte fehlten die CPU-Werte). Lief er vorher nicht, bleibt er aus.
- **`daten\`**: Fehlt eine Datei oder ist sie kein gültiges JSON mehr, wird die gemerkte zurückgeschrieben. Hat ein
  Programm sie selbst geändert (der Monitor speichert beim Beenden z. B. die Fensterposition), bleibt das so.

Was nur mit Adminrechten geht, sammelt `Zustand-Abgleichen` und erledigt es in EINER UAC-Abfrage.

Ganz unten entscheidet die letzte Zeile, welche Funktion läuft: `-Admin` → `Admin-Schritte`, `-Entfernen` →
`Entfernen`, sonst `Einrichten`.

### 4.2 `Toolbox.exe` (Starter) und der Start der Toolbox

Doppelklick auf `Toolbox.exe` im Hauptordner (oder eine Verknüpfung darauf). Der Starter (siehe 3.2) startet

```
runtime\Toolbox.exe "<Ordner>\toolbox\toolbox.py"
```

und beendet sich; die Toolbox läuft ohne Konsole – im Task-Manager als „Toolbox“. Fehlt `runtime\` (noch nicht
eingerichtet), sagt er das in einem Hinweisfenster.

Die Vorlage `setup\starter.cs` im Überblick:

- oben die Platzhalter `%NAME%`, `%VERSION%`, `%RUNTIME%`, `%HOST%`, `%SKRIPT%` (setzt `setup.ps1` ein),
- `Main`: eigenen Ordner bestimmen (`AppDomain.CurrentDomain.BaseDirectory`), daraus `runtime\` und das Skript
  berechnen, fehlt etwas → `MessageBox`, sonst `Process.Start` mit `UseShellExecute = false` (erbt so die Rechte)
  und Arbeitsordner = Ordner des Skripts,
- `Quote`: setzt jedes Argument so in Anführungszeichen, wie Windows-Programme (auch Python) es wieder
  auseinandernehmen.

Alternativen:

```
runtime\python.exe toolbox\toolbox.py      mit Konsole (Fehler erscheinen dort zusätzlich zum Log)
python -B -m toolbox.toolbox               als Modul (für den Play-Button in Zed); dafür gibt es __init__.py
                                           im Hauptordner. toolbox\ selbst hat keine __init__.py – Python
                                           behandelt es als „Namespace-Paket“ (PEP 420), das reicht.
```

### 4.3 `toolbox\toolbox.py` – das Hauptfenster

Ablauf beim Start (von oben nach unten, wie Python die Datei ausführt):

1. Importe, `sys.dont_write_bytecode = True`, `APP_DIR`/`ROOT`/`PROGRAMME_DIR` bestimmen, `APP_DIR` in `sys.path`.
2. `import daten`, `import winutil`, `from base import ...`, `from platzhalter import ...`.
3. Konstanten: `CATEGORIES` (Tabs oben: Allgemein, Games), `PLACEHOLDERS` (die
   „XXX“-Einträge), `AUSWEIS` (`toolbox\programm.json`) und daraus `VERSION`, `SETTINGS_FILE` (`daten\toolbox.json`),
   `ICON_FILE`, `TOOLBOX_EXE` (`runtime\Toolbox.exe`), `EINRICHTEN` (`Einrichten.cmd`), `GUI_PORT = 47816`,
   `APPEARANCE`, `DEFAULT_SETTINGS`.
4. logging in `daten\logs\toolbox.log` einrichten. Beide Pfade kommen aus `daten.py` (`daten.einstellungen("toolbox")`,
   `daten.log("toolbox")`, siehe 4.6).
5. `TOOLS = find_tools() + PLACEHOLDERS` – Programme automatisch finden:
   ```
   for ausweis in PROGRAMME_DIR.glob("*/programm.json"):     # jede programme\<irgendwas>\programm.json
       JSON lesen, die Datei aus "seite" laden (importlib.util.spec_from_file_location / exec_module)
       ToolInfo bauen: id, name, kategorie, beschreibung aus dem Ausweis, Seite = module.SEITE,
       programm = module.PROGRAMM (falls vorhanden)
   ```
   Wirft ein Programm einen Fehler, wird er nur geloggt – die anderen erscheinen trotzdem.
   → Ein neues Tool braucht also KEINE Änderung an `toolbox.py`.
6. `main()`:
   - Mit `--nach <pid>` gestartet (Neustart, siehe `neu_starten`): erst warten, bis die alte Toolbox wirklich
     beendet ist (`winutil.wait_for_exit`, höchstens 10 s).
   - `bring_existing_to_front()`: verbindet sich mit 127.0.0.1:47816 und schickt „show“. Antwortet jemand mit „ok“,
     läuft schon eine Toolbox → die zeigt ihr Fenster, dieser Start endet.
   - App-ID setzen (Taskleistensymbol).
   - `ToolboxApp().mainloop()`.

#### Einstellungen (`daten\toolbox.json`)

`load_settings()` nimmt die Standardwerte und übernimmt aus der Datei nur gültige Werte (`appearance` muss in
`APPEARANCE` stehen, `close_to_tray` muss bool sein …). So kann eine kaputte Datei nichts zerstören.
Hier steht NUR, was die Toolbox selbst betrifft. Jedes Programm hat seine eigene Datei (`daten\<id>.json`) – auch
der Aufgabenname des Hardware-Monitors steht in `daten\hardware_monitor.json`.

#### Klasse `ToolboxApp(ctk.CTk)` – das Fenster

`__init__`:

- Einstellungen laden, Hell/Dunkel setzen, `apply_theme()` (VOR dem Fenster), `super().__init__()` (erst jetzt
  gibt es das Fenster), `apply_font(self)` (braucht ein Fenster, um installierte Schriften abzufragen).
- Titel = vollständiger Pfad von `toolbox.py` (wie der Explorer seinen Ordner zeigt – im Task-Manager steht er
  aufgeklappt unter „Toolbox“ und verrät, welche Kopie läuft), Größe 1060×720, Mindestgröße, Symbol.
- Zustände: `ui_queue`, `pages` (Cache gebauter Seiten), `current_page`, `selected` (letztes Programm je Tab) …
- Raster: Zeile 0 = Kopfleiste, Zeile 1 = 1-px-Linie, Zeile 2 = Inhalt; Spalte 0 = Seitenleiste,
  Spalte 1 = 1-px-Linie, Spalte 2 = Hauptbereich (wächst mit: `columnconfigure(2, weight=1)`).
- `build_topbar()`, `build_sidebar()`, Hauptbereich `self.main`, `build_linkzeile()`: Kästchen unten links wie im
  Browser, das beim Drüberfahren über einen Knopf mit `ziel` zeigt, was er öffnet (`link_zeigen`/`link_verstecken`,
  liegt per `place` über allem; `show_page` und `hide_to_tray` blenden es aus).
- ersten Tab zeigen, ✕ abfangen (`on_close`), Instanz-Server-Thread starten, Queue-Abfrage starten.

Navigation:

| Methode | Was sie tut |
|---|---|
| `show_category(kategorie)` | Tab hervorheben, Seitenleiste leeren und mit den Programmen dieses Tabs füllen (alphabetisch), zuletzt gewähltes Programm wieder zeigen |
| `show_tool(tool)` | Seite beim ERSTEN Mal bauen (`tool.page(self.main, self, tool)`), danach aus `self.pages` wiederverwenden; dann `show_page` |
| `show_settings()` | Zahnrad → `GuiSettingsPage` |
| `show_page(page)` | alte Seite: `on_hide()` + `grid_forget()`; neue Seite: `grid()` + `on_show()`. Dadurch wissen Seiten, wann sie sichtbar sind (z. B. Status-Abfrage nur dann). |

Hilfen für Seiten:

| Methode | Was sie tut |
|---|---|
| `toast(text, error)` | kurze Meldung oben rechts („Gespeichert ✓“), verschwindet nach 2,5 s |
| `run_async(func, on_done)` | `func` im Hintergrund-Thread, Ergebnis per `ui_queue` → `on_done` im GUI-Thread |
| `poll_queue()` | alle 100 ms: Aufträge aus der Queue abarbeiten (`"show"`, `"quit"` oder eine Funktion) |

Schließen und Tray:

- `on_close`: Ist „Beim Schließen in den Infobereich minimieren“ an → `hide_to_tray()`: Fenster verstecken, beim
  ersten Mal ein pystray-Symbol anlegen (Menü: „Toolbox öffnen“ als Standardaktion, „Beenden“). Die Menü-Aktionen
  laufen im pystray-Thread und legen deshalb nur `"show"`/`"quit"` in die Queue.
- `quit_app`: `on_hide`, Tray stoppen, `destroy()` → `mainloop` endet → Programm endet.
- `neu_starten`: startet eine neue Toolbox (`runtime\Toolbox.exe`, sonst `pythonw.exe`) mit `--nach <eigene pid>` und
  beendet sich dann selbst. Ohne das Warten fände die neue die alte noch laufend und holte nur deren Fenster nach
  vorne (Einzelinstanz über Port 47816).

`instance_server` (eigener Thread): Lauscht auf 127.0.0.1:47816. „show“ und „quit“ legt er in die Queue, auf „show“,
„status“ und „quit“ antwortet er „ok“. „show hardware_monitor“ (allgemein „show <programm-id>“) schickt das ⚙ im
Detailfenster des Monitors: Die Queue bekommt dann `("show", id)`, und `poll_queue` ruft `show_programm(id)` auf
(Tab und Seite wählen) und holt das Fenster nach vorne. Läuft die Toolbox noch nicht, startet der Monitor sie über
`explorer.exe` – so läuft sie ohne die Adminrechte des Monitors – und schickt den Befehl, sobald sie antwortet
(`toolbox_oeffnen` in `detailfenster.py`). Eine Toolbox von vor dieser Version kennt nur „show“ – `setup.ps1` kann sie
deshalb nicht beenden. (Auf Linux/macOS wird `SO_REUSEADDR` gesetzt; unter Windows bewusst nicht, weil dort damit
zwei Programme denselben Port belegen könnten.)

#### Klasse `GuiSettingsPage(ToolPage)` – die Zahnrad-Seite

Überschreibt `load()`/`save()`, damit sie nicht in eine eigene Datei, sondern in `app.settings` speichert.
`on_change`: Design sofort umschalten bzw. Tray-Symbol entfernen, wenn „in den Infobereich“ ausgeschaltet wird.

Bereich „Beenden und Neustart“:

- Statuszeile: `programme_pruefen()` fragt im Hintergrund jedes Tool mit `programm` (siehe `base.Programm`), ob es
  läuft („● Hardware-Monitor: läuft“). Bei jedem Anzeigen der Seite neu.
- „Nur Toolbox“: Neu starten = `app.neu_starten`, Beenden = `app.quit_app`. Programme laufen weiter.
- „Toolbox und alle Programme“: `alle(neu)` – im Hintergrund für jedes LAUFENDE Programm `beenden()` und bei
  Neustart `starten()` (gestoppte bleiben gestoppt), danach die Toolbox selbst neu starten bzw. beenden. Klappt
  bei einem Programm etwas nicht, bleibt die Toolbox offen und zeigt „Nicht geklappt: …“.
- Die „i“-Tooltips erklären beide Zeilen (`NUR_TOOLBOX_INFO`, `ALLE_INFO`).

Bereich „Aktualisieren“:

- Statuszeile: `stand_pruefen()` zeigt den Stand des Ordners („Stand: 6c3fccf vom 10.10.2026“, aus `git log -1`).
  Ohne git oder ohne `.git`-Ordner ist der Knopf ausgegraut.
- Knopf „Aktualisieren“: `aktualisieren()` ruft im Hintergrund `git_holen()` auf:

  | Befehl | Zweck |
  |---|---|
  | `git fetch` | neue Commits von GitHub holen (noch nichts ändern) |
  | `git rev-list --count HEAD..@{upstream}` | wie viele davon sind neu? 0 → „Schon auf dem neuesten Stand“ |
  | `git pull --ff-only` | nur „vorspulen“ – eigene Commits oder Änderungen werden nie zusammengeführt oder überschrieben; passt es nicht, bricht git ab und die Meldung erscheint |

  Gab es Neues, startet `os.startfile()` `Setup.exe -Neustart` in einem eigenen Konsolenfenster (wie ein
  Doppelklick) – dasselbe macht der Knopf „Neu einrichten“, nur ohne git. Das Setup beendet die Toolbox per „quit“,
  bringt `runtime\` auf den Stand von `requirements.txt`, stellt alles wie vorher (Schritt 7: Autostart, laufender
  Hardware-Monitor neu gestartet) und startet zum Schluss die Toolbox. Hat alles geklappt, schließt sich das Fenster
  nach 5 s von selbst; bei gelben Warnungen oder einem Fehler bleibt es offen, bis man eine Taste drückt.
- `deinstallieren()` (Abschnitt „Deinstallieren“, roter Knopf): fragt erst Ja/Nein (`messagebox.askyesno`), startet
  dann `Uninstall.exe` per `os.startfile()` – genau wie ein Doppelklick darauf. Die Toolbox beendet `setup.ps1
  -Entfernen` selbst per „quit“ (siehe 4.12).
- `git()` führt git unsichtbar im Hauptordner aus (`git -C <Ordner> …` über `winutil.run_hidden`).

→ Ein neues Tool mit eigenem Programm muss für „Toolbox und alle Programme“ nichts an `toolbox.py` ändern – es gibt
in seiner Seiten-Datei `PROGRAMM = Programm(laeuft, beenden, starten)` an.

### 4.4 `toolbox\base.py` – der Baukasten für Programmseiten

Idee: Eine Programmseite wird nur BESCHRIEBEN (ähnlich wie HTML), `base.py` baut daraus die Widgets, lädt die Werte
und speichert Änderungen. Du schreibst also kaum GUI-Code selbst.

**Farben** (oben in der Datei): Jede Farbe ist ein Paar (hell, dunkel): `BG`, `BAR`, `CARD`, `BORDER`, `FIELD`,
`TEXT`, `MUTED`, `ACCENT` (#3ddc97, das Grün der PROOFM-Website), `SELECTED`, `HOVER`, `BUTTON`, `TRACK`, `GOOD`,
`BAD`, `WARN` … Neue Widgets sollten diese Konstanten benutzen.

**`apply_theme()`**: Startet vom eingebauten Theme „blue“ und überschreibt in `ctk.ThemeManager.theme` die
Farben/Rundungen aller CustomTkinter-Widgettypen. Muss vor dem Erzeugen des ersten Fensters laufen.

**`apply_font(root)`**: Nimmt „Inter“, wenn installiert, sonst „Segoe UI“.

**`ToolInfo`** (dataclass): `id`, `name` (Seitenleiste), `category` (Tab), `description` (Untertitel), `page` (die
Seitenklasse), `programm` (optional). Die Toolbox baut es aus `programm.json` + `SEITE`/`PROGRAMM` der Seiten-Datei.

#### Bausteine

| Baustein | Bedeutung |
|---|---|
| `Section(titel, *bausteine)` | eine Karte mit Überschrift; darin die Bausteine untereinander |
| `Element` | Basisklasse: Beschriftung links (`label`), Bedienelement rechts. Mit `info="…"` steht hinter der Beschriftung ein rundes „i“ (`info_symbol`), das den Text beim Drüberfahren als Tooltip zeigt. Wichtige Methoden: `place(page, card, row)` baut ein und gibt die Zahl belegter Zeilen zurück, `create(page, card)` erzeugt das eigentliche Widget, `refresh(page)` zeigt den aktuellen Wert aus `page.data` an. |
| `Text(text, name, color, size, hidden)` | Text über die ganze Breite (`hidden` → später `page.show(name)`) |
| `Buttons(Button(...), …, label, info)` | Knopfreihe, optional mit Beschriftung links (und „i“). `Button(text, command, name, width, style, ziel)` mit style `"normal"` (grün), `"grau"`, `"rahmen"`, `"gefahr"` (roter Text). `ziel` = was der Knopf außerhalb der Toolbox öffnet (Adresse, Pfad, Programm mit Argumenten oder eine Funktion, die das liefert) – steht beim Drüberfahren unten links im Fenster wie im Browser (`ziel_anzeigen()` → `app.link_zeigen()`); bei jedem solchen Knopf angeben. `page.enable(name, an)` graut einen Knopf aus und gibt ihm beim Einschalten wieder die Farbe seines Stils. |
| `Programm(laeuft, beenden, starten)` | kein Baustein, sondern `PROGRAMM = Programm(…)` in der Seiten-Datei: wie die Toolbox das eigenständige Programm eines Tools abfragt, beendet und startet (für „Toolbox und alle Programme“). Alle drei bekommen `app`, laufen im Hintergrund. |
| `Choice(label, key, optionen, info)` | Auswahlknöpfe (CTkSegmentedButton). `optionen` = `{"Anzeige": Wert}` oder Liste |
| `Tooltip(widget, text)` | kleines Hinweisfenster bei `<Enter>`, weg bei `<Leave>`. Bewusst schlichtes tk (`tk.Toplevel` ohne Titelleiste + `tk.Label`): CTkToplevel setzt verzögert Symbol und Titelleiste, und CTk-Widgets in einem `tk.Toplevel` verträgt die DPI-Überwachung von CustomTkinter nicht. Schrift und Abstände werden deshalb selbst mit `ScalingTracker.get_widget_scaling()` an die Windows-Skalierung angepasst; die Farben (hell/dunkel) nach `ctk.get_appearance_mode()`. |
| `Combo(label, key, werte, names)` | Aufklappliste mit freier Eingabe. `names` übersetzt gespeicherte Werte in Anzeige (`{"auto": "Automatisch"}`). Leer = Standardwert. |
| `Entry(label, key \| command)` | Eingabefeld; übernimmt bei Enter oder beim Verlassen |
| `Switch(text, key \| command)` | Schalter |
| `Slider(text, key, start, ende)` | Schieberegler für ganze Zahlen; `{}` im Text wird durch den Wert ersetzt. Speichert erst 500 ms nach der letzten Bewegung (`later=True`). |
| `Check(text, key, items, hint)` | Häkchen, das `items` in die Liste `data[key]` aufnimmt/entfernt |
| `TextList(text, key, exclude)` | mehrzeiliges Feld für eine Liste + „Übernehmen“-Knopf |

(`Check` und `TextList` sind vorhanden, werden aber derzeit von keiner Seite benutzt.)

- `key` → der Baustein zeigt `self.data[key]` und speichert Änderungen sofort.
- `name` → der Baustein ist danach als `self.w[name]` erreichbar (z. B. um eine Statuszeile zu ändern).
- `command` → statt zu speichern wird diese Funktion aufgerufen (für Aktionen, die nicht in die Datei gehören).

#### `ToolPage(ctk.CTkScrollableFrame)` – die Seite

Klassenattribute zum Überschreiben: `settings_file` (Path; ohne Angabe automatisch `daten\<id>.json` über
`daten.einstellungen(info.id)`), `defaults` (Startwerte).
`__init__`: setzt `settings_file`, lädt `self.data`, baut Titel/Untertitel, ruft `layout()` auf und baut jede
Section als Karte, `refresh()`.

Werte-Ablauf bei einer Änderung (Methode `set`):

```
self.data[key] = value  →  on_change(key, value)  →  refresh(key)  →  save()  (bzw. 500 ms später)
save(): JSON schreiben → toast „Gespeichert ✓“ → on_saved()
```

`load()`: `defaults` (tiefe Kopie) + Inhalt der Datei darüber. Unbekannte Schlüssel aus der Datei BLEIBEN erhalten –
wichtig, weil der Monitor in dieselbe Datei auch `"window"` schreibt, das die Toolbox gar nicht kennt.

Hilfen: `show(name, sichtbar)`, `enable(name, an)` (Knopf an/aus inkl. grauer Farbe), `open(pfad)` (mit
Standardprogramm öffnen: `os.startfile`), `reset()` (Standardwerte).

Hooks (zum Überschreiben):

| Hook | Wann |
|---|---|
| `layout()` | Liste der Sections |
| `on_change()` | vor dem Speichern |
| `on_saved()` | nach dem Speichern |
| `on_show()` | Seite sichtbar (lädt Datei neu) |
| `on_hide()` | Seite verlassen / Fenster versteckt |

### 4.5 `toolbox\winutil.py` – Windows-Helfer

| Funktion | Was sie tut |
|---|---|
| `run_hidden(args)` | Programm unsichtbar ausführen (`CREATE_NO_WINDOW` → keine aufblitzende Konsole), Ausgabe in OEM-Codepage lesen, Timeout 20 s. `None`, wenn es nicht klappt. |
| `powershell(befehl)` | `run_hidden` mit `powershell.exe -NoProfile -NonInteractive -Command …` |
| `ps_quote(text)` | Text sicher in `'...'` für PowerShell setzen (`'` wird zu `''`) |
| `pythonw_exe()` | `pythonw.exe` neben dem laufenden Python |
| `wait_for_exit(pid, timeout)` | wartet aufs Prozessende (OpenProcess mit nur SYNCHRONIZE + WaitForSingleObject – geht auch bei Programmen mit Adminrechten). Wichtig vor Neustarts: Ein Programm antwortet oft schon nicht mehr, hält aber noch kurz `.exe` und Einzelinstanz-Sperre. |
| `run_elevated(datei, params, cwd, wait)` | ShellExecuteExW mit `runas` → UAC-Abfrage. Mit `wait=True` wird auf das Ende gewartet und `True` bei Exitcode 0 zurückgegeben. `False`, wenn abgelehnt. |
| `task_info(name)` | Zustand/Programm/Argumente einer Aufgabe per PowerShell als JSON. PowerShell statt schtasks, weil schtasks die Zustände in der Windows-Sprache ausgibt. |
| `task_state(name)` | nur der Zustand |
| `task_command(name, exe, arguments, cwd)` | baut den PowerShell-Text, der die Aufgabe anlegt: startet `exe` (beim Monitor der Starter, ohne Argumente), Trigger „bei Anmeldung“, RunLevel Highest (= Admin ohne Nachfrage), auch im Akkubetrieb, ohne Zeitlimit, keine Doppelstarts. Wird von der Toolbox UND von `setup.ps1` benutzt. |
| `register_task(...)` | `task_command` als `-EncodedCommand` mit UAC ausführen |
| `set_task_enabled(name, an)` | Aufgabe (de)aktivieren – erst ohne, notfalls mit Adminrechten |
| `run_task(name)` | `schtasks /run` – startet die Aufgabe (sie läuft dann mit Adminrechten) |

Außerhalb von Windows geben die Funktionen `None`/`False` zurück, statt abzustürzen.

### 4.6 `toolbox\daten.py` und `toolbox\platzhalter.py`

#### `daten.py` – wo gespeicherte Daten liegen

| Funktion | Ergebnis |
|---|---|
| `einstellungen(programm)` | `daten\<programm>.json`, z. B. `daten\toolbox.json`, `daten\hardware_monitor.json` |
| `log(programm)` | `daten\logs\<programm>.log` |
| `DATEN_DIR`, `LOG_DIR` | die beiden Ordner |

Beide legen den Ordner bei Bedarf an und ziehen eine Datei einmalig von ihrem alten Ort um, falls sie dort noch
liegt: `daten\<programm>_settings.json` bzw. `daten\<programm>.log` (Zwischenstand Oktober 2026) oder davor neben
dem Skript in `src\…`. Klappt das Verschieben nicht (z. B. hält ein noch laufendes altes Programm sein Log offen),
wird es beim nächsten Start erneut versucht. `daten.py` liegt in `toolbox\`, wird aber auch von
`hardware_monitor.py` benutzt – der hängt dafür `toolbox\` hinten an `sys.path`.

#### `platzhalter.py`

Eine minimale ToolPage („Noch nichts hier“) für die XXX-Einträge in den Tabs ohne Programm. Gutes, kleinstes
Beispiel für eine Seite. Sobald ein Tab echte Programme hat, kannst du den Platzhalter aus `PLACEHOLDERS` in
`toolbox.py` streichen.

### 4.7 `programme\hardware_monitor\hardware_monitor_gui.py` – die Seite in der Toolbox

Läuft IM Toolbox-Prozess (ohne Adminrechte). Wird von `find_tools()` geladen, weil `programm.json` sie unter
`"seite"` nennt.

**Konstanten:** `FOLDER`, `SCRIPT` (`hardware_monitor.py`), `AUSWEIS` (die `programm.json`), daraus `STARTER`
(`programme\hardware_monitor\HardwareMonitor.exe`) und `MONITOR_EXE` (die Kopie in `runtime\`), `SETTINGS_FILE`
(`daten\hardware_monitor.json`), `LOG_FILE` (`daten\logs\hardware_monitor.log`), `IPC_PORT = 47815`,
`DEFAULT_TASK = "HardwareMonitor"`, die Auswahllisten (`ICON_RATES`, `POPUP_RATES`, `ORDERS`, `CPU_CHOICES`,
`GPU_CHOICES`).

| Funktion | Was sie tut |
|---|---|
| `ipc(befehl)` | Verbindet sich mit dem Monitor, schickt den Befehl, liest bis zum Zeilenende, gibt das JSON als dict zurück – oder `None`, wenn der Monitor nicht läuft. IMMER über `run_async` aufrufen (Netzwerk = potenziell langsam). |
| `startbefehl()` | (Programm, Argumente) für Aufgabe und UAC-Start: der Starter ohne Argumente; fehlt er (`Einrichten.cmd` noch nicht gelaufen), `runtime\HardwareMonitor.exe` bzw. `pythonw.exe` mit `"hardware_monitor.py"` |
| `task_name()` | Name der Aufgabe aus `daten\hardware_monitor.json` (`"task_name"`, Standard „HardwareMonitor“) |
| `task_points_here(info)` | Startet die Aufgabe wirklich diesen Starter (und nicht z. B. den Ort vor dem Verschieben)? |

#### `HardwareMonitorPage(ToolPage)`

`settings_file = SETTINGS_FILE` = `daten\hardware_monitor.json` (DIESELBE Datei, die der Monitor liest; die Toolbox
zieht sie auch selbst um, falls der Monitor nach einem Update noch alten Code fährt), `defaults` wie
`DEFAULT_SETTINGS` im Monitor (ohne `"window"`, dafür mit `"task_name"` – den lässt der Monitor beim Speichern
stehen).

- `layout()`: Bereiche Status (Statuszeile + Starten/Beenden/Neu starten), Autostart (Schalter + Aufgabe einrichten),
  Aktualisierung (zwei Raten + Effizienzmodus mit „i“-Tooltip, Text in `EFFIZIENZ_INFO`), Anzeige (Reihenfolge,
  Sensor-Combos, je zwei Slider für CPU und GPU), Detailfenster (Hinweis + Ordner öffnen), Erweitert (Aufgabenname,
  Ordner/Log/Einstellungsdatei öffnen, Alles zurücksetzen).
- `on_change`: hält „gelb ab“ immer unter „rot ab“ – je für CPU und GPU (zieht den anderen Regler mit); zeigt bei geänderter
  Icon-Reihenfolge den Hinweis „Wird nach Neu starten übernommen“.
- `on_saved`: schickt `"reload"` an den Monitor → der übernimmt die Werte sofort.
- `task_name` (property) / `on_task_name`: Aufgabenname aus bzw. in `self.data` – also in `daten\hardware_monitor.json`.

**Status-Abfrage:** `on_show` → `visible = True`, Datei neu einlesen (der Monitor kann z. B. die Raten per
Rechtsklick geändert haben), `poll_status()` alle 2 s (`after(2000, ...)`), `refresh_task()`. `on_hide` → Abfrage
stoppen. `show_status(antwort)`: „● Läuft · CPU 52 °C · GPU 41 °C“ oder „● Gestoppt“, Knöpfe passend an/aus.

**Programm steuern** – Funktionen außerhalb der Seite, damit auch die Toolbox-Einstellungen sie nutzen können
(„Toolbox und alle Programme“, über `PROGRAMM`):

| Funktion | Was sie tut |
|---|---|
| `laeuft(app)` | antwortet der Monitor auf „status“? |
| `beenden(app)` | „quit“ schicken, dann aufs Prozessende warten (pid aus „status“, `winutil.wait_for_exit`) – erst dann sind `.exe` und Einzelinstanz-Sperre frei. Rückfall: warten, bis „status“ nicht mehr antwortet. |
| `starten(app)` | Gibt es die Aufgabe, ist sie aktiv UND zeigt auf diesen Starter (`task_points_here`)? → `run_task` (keine UAC). Sonst → `run_elevated(startbefehl())` (UAC-Abfrage). |

Knöpfe der Seite: Starten = `starten()` im Hintergrund, danach `poll_status_soon()` (nach 0,4 / 1,2 / 2,5 s
nachsehen). Beenden = `ipc("quit")`. Neu starten = `beenden()`, dann Starten.

**Autostart:** `refresh_task` → `task_info` im Hintergrund → `show_task`: Schalter und Text je nachdem, ob die
Aufgabe fehlt, aktiv/deaktiviert ist oder auf einen anderen Ort zeigt (z. B. nach dem Verschieben des Ordners).
`setup_task` → `winutil.register_task(name, *startbefehl())` (UAC). `toggle_autostart` → `winutil.set_task_enabled`.

Ganz unten:

```python
SEITE = HardwareMonitorPage
PROGRAMM = Programm(laeuft, beenden, starten)
```

← diese Zeilen holt sich die Toolbox; Name, Tab und Beschreibung kommen aus `programm.json`.

### 4.8 `programme\hardware_monitor\hardware_monitor.py` – das eigentliche Programm

Läuft als EIGENER Prozess mit Adminrechten (gestartet von der Aufgabe oder per UAC, jeweils über den Starter).
Keine CustomTkinter-Abhängigkeit.

Was beim Start passiert (Reihenfolge im Code):

1. `sys.dont_write_bytecode`, eigenen Ordner in `sys.path` (wegen `._pth`, siehe 3.2), `toolbox\` hinten an
   `sys.path` (für `daten.py`), `from detailfenster import ...`.
2. Einstellungen/Konstanten:

   | Name | Bedeutung |
   |---|---|
   | `LHM_DIR` | wo `LibreHardwareMonitorLib.dll` liegt (`lhm\` neben dem Skript, sonst `runtime\lhm`, wo es kurzzeitig lag, sonst `C:\Tools\lhm`) |
   | `ICON_RATES` / `POPUP_RATES` | 1, 2, 5, 10 s / 0,5, 1, 2, 5 s |
   | `DEFAULT_SETTINGS` | `icon_interval`, `popup_interval`, `icon_order`, `cpu_sensor`, `gpu_sensor`, `cpu_warn_temp`/`cpu_hot_temp`, `gpu_warn_temp`/`gpu_hot_temp`, `window`, `effizienzmodus` (`"auto"`/`"an"`/`"aus"`) |
   | `SETTINGS_FILE` | `daten\hardware_monitor.json` (über `daten.einstellungen`) |
   | `CPU_SENSORS` | `("Core (Tctl/Tdie)", "CPU Package", "Core Average")` – Reihenfolge für „Automatisch“ |
   | `GPU_SENSORS` | `("GPU Core", "GPU Hot Spot")` |
   | `IPC_PORT` | 47815 |
   | `FAST_HARDWARE` | CPU, GPU – sofort beim Start |
   | `LATER_HARDWARE` | RAM, Mainboard, Controller, Laufwerke, Netzwerk, Netzteil, Akku, PowerMonitor – im Hintergrund |

3. logging → `daten\logs\hardware_monitor.log` (über `daten.log`).
4. LHM laden: `sys.path.append(LHM_DIR)`, `import clr`, `AddReference`, `Computer()` anlegen, CPU+GPU einschalten,
   `Open()`.
5. `nvidia = NvidiaTemp()` – versucht `nvml.dll` zu laden und die erste Nvidia-Karte zu öffnen. Ohne Nvidia:
   `available = False`, alles läuft über LHM.
6. Übersetzungstabellen: `HW_TYPES`/`SENSOR_TYPES` (.NET-Enum → Text), `HW_GERAET` (LHM-Typ → „cpu“, „gpu“, „ram“,
   „mainboard“, „laufwerk“, „netzwerk“, „akku“; alles andere → „weitere“). Diese Gerätenamen benutzt
   `detailfenster_inhalt.py` in `Gruppe("...")`.
7. `SETTINGS = load_settings()` – jeder Wert wird geprüft (Raten müssen in den erlaubten Listen sein,
   20 ≤ gelb < rot ≤ 120, `window` muss wie „480x640+1420+380“ aussehen …). Ungültiges → Standardwert. Schlüssel,
   die nur die Toolbox kennt (`task_name`), bleiben unverändert erhalten – sonst löschte `save_settings()` sie beim
   nächsten Speichern.
8. Falls `--list`: alles einschalten, einmal messen (erste Messung verwerfen, manche Sensoren liefern sonst 0),
   1 s warten, alle Sensoren ausgeben, Ende.
9. Sonst: tkinter, PIL, pystray importieren, Schriften für die Icons laden.
10. `main()`: `already_running()`? (Mutex) → dann Ende. DPI-Awareness. `HardwareMonitorApp().run()`.

#### Messen – die zwei Wege

**`collect(geraete)` → „Snapshot“ für das Detailfenster**

- `geraete` = Menge wie `{"gpu", "laufwerk"}` (nur diese lesen) oder `None` (alles). CPU wird immer gelesen.
- Für jedes Top-Gerät in `pc.Hardware`: nicht gebraucht → überspringen (wird gar nicht erst aktualisiert!).
  Sonst `walk()` (`Update()` + Unter-Geräte) und alle Sensoren mit Wert in ein dict packen.
- Ungenutzte Netzwerkadapter (alle Werte 0) fallen weg.
- Ergebnis:
  ```
  {"hardware": [ {id, geraet, kind, name, sensors: [{id, type, name, value}, …]}, … ],
   "cpu": {...}, "gpu": {...}, "geraete": {...}}
  ```
- Die GPU-Temperatur kommt aus NVML, wenn die GPU sonst gar nicht gebraucht wird.

**`icon_werte()` → nur die zwei Zahlen für die Icons** (der sparsame Weg, wenn das Fenster zu ist)

- Je Gerät ein `Update()` und genau EIN Sensorwert. Die .NET-Sensorobjekte werden beim ersten Mal gesucht
  (`icon_sensor_suchen`) und in `ICON_SENSOREN` gemerkt; danach wird direkt gelesen. Liefert der Sensor keinen Wert
  mehr, wird beim nächsten Mal neu gesucht. Bei `"reload"` wird `ICON_SENSOREN` geleert (anderer Sensor gewählt?).
- `collect()` würde dafür jeden der ~50 CPU-Sensoren einzeln über pythonnet abfragen – das ist der große
  Unterschied.

`sensor_priority(key, defaults)`: gewählter Sensor zuerst, dann die automatische Reihenfolge als Rückfall.

#### Tray-Icons

`make_icon(kind, wert)`: 64×64-Bild mit transparentem Hintergrund, Zahl in Ampelfarbe (`temp_color`), darunter ein
Farbstreifen (blau = CPU, grün = GPU). Zweistellig große Schrift, dreistellig kleinere.
→ https://pillow.readthedocs.io/en/stable/reference/ImageDraw.html
→ https://pillow.readthedocs.io/en/stable/handbook/text-anchors.html (`anchor="mm"` = Mitte/Mitte)

`make_logo(kind)`: das Programm-Logo (`toolbox\programm.ico`) mit demselben Farbstreifen. Wird nur beim Anmelden
gezeigt (siehe `TrayIcon`), weil sich Windows für Einstellungen > Personalisierung > Taskleiste > „Andere Symbole“ genau
dieses Bild merkt (Registry: `HKCU\Control Panel\NotifyIconSettings`, Wert `IconSnapshot`). Der Name daneben
kommt aus der Dateibeschreibung von `runtime\HardwareMonitor.exe`.

`TrayIcon`: `pystray.Icon` mit zwei ersetzten Methoden (pystray-Version fest in requirements.txt):
- `_show` meldet das Icon immer mit `make_logo` an und setzt gleich danach das eigentliche Bild. pystray ruft
  `_show` auch nach einem Neustart des Explorers auf (Nachricht `TaskbarCreated`) – ohne den Ersatz würde sich
  Windows dann die gerade angezeigte Temperatur merken.
- `_message` schickt eine feste Nummer mit (`uID`: CPU = 1, GPU = 2). Windows erkennt ein Tray-Icon an .exe + Nummer;
  pystray schickt die Nummer unter falschem Namen (`hID`), sie wäre also immer 0, und CPU und GPU wären für Windows
  ein einziger Eintrag.
→ https://learn.microsoft.com/de-de/windows/win32/api/shellapi/ns-shellapi-notifyicondataw

#### Klasse `HardwareMonitorApp`

`__init__`:

- `tk.Tk()` als unsichtbares Hauptfenster (`withdraw`). Das Detailfenster ist ein Toplevel davon und wird erst beim
  ersten Klick gebaut.
- `fenster_bedarf`: `False` = Fenster zu/minimiert, sonst die Menge der gebrauchten Geräte (`None` = alle).
- Events `stop`/`wake`, `lock`, `latest` (letzter Snapshot), `shown` (was gerade in den Icons steht), `ui_queue`,
  `current` (aktuelle Icon-Werte für die Statusabfrage).
- `kinds` = die Icons, die es wirklich gibt: `icon_order` ohne `"gpu"`, wenn `gpu_hat_temperatur()` nichts findet
  (kein NVML und kein Temperatursensor an einer GPU – z. B. Intel-Onboard-Grafik). `kinds` bekommen auch
  `measure_icons`, `measure` (`collect(…, icons)`), das Detailfenster (Kopfzeile) und die Statusabfrage (`"icons"`).
- Ein `TrayIcon` pro Eintrag in `kinds`, alle mit demselben Menü.
- Threads vorbereiten: `sensor_thread` (`sensor_loop`), `ipc_thread` (`ipc_server`).

**Rechtsklick-Menü** (`make_menu`, `rate_menu`): „Details anzeigen“ (`default=True` → auch Linksklick),
Untermenüs für die Raten (Radio-Häkchen), „Beenden“. Texte und Häkchen sind Funktionen (`lambda item: …`), damit
pystray sie bei jedem Öffnen neu auswertet. pystray prüft die Parameterzahl der Aktion – deshalb die kleinen
Fabrikfunktionen `action(s)`/`checked(s)`. `set_rate`: speichern, Menüs auffrischen, Mess-Thread wecken.

**`run()`**: Icons NACHEINANDER anmelden (`run_detached` + setup-Callback, auf ready warten) → feste Reihenfolge in
der Taskleiste. `effizienz_anwenden()`. Threads starten. `poll_queue` per `after()`. `root.mainloop()`.
Nach `quit()`: auf den Mess-Thread warten (max. 5 s), Fenster zerstören.

**`effizienz_anwenden()`**: Setzt den Effizienzmodus laut Einstellung `"effizienzmodus"`: `"auto"` = an, solange
das Fenster zu ist; `"an"` = immer; `"aus"` = nie. Aufgerufen beim Start, beim Wechsel Fenster offen↔zu und nach
`"reload"` (Toolbox geändert).

**`sensor_loop()` – der Mess-Thread (Herzstück)**

1. Icons sofort füllen (`measure_icons`).
2. Übrige Hardware einschalten (`LATER_HARDWARE`, RAM dauert ~8 s) und einmal komplett messen („anwärmen“).
   Aus dieser Messung: `vorhanden` = welche Geräte dieser PC hat (z. B. kein „mainboard“ am Laptop) – damit
   blendet das Fenster Tabs ohne passende Geräte aus. `hardware_ready = True`.
3. Schleife bis `stop`:
   ```
   needed = fenster_bedarf
   Fenster offen und Zeit fürs Fenster?  → measure(needed) → latest setzen → Icons aus dem Snapshot
                                          → "data" in die Queue (Fenster neu zeichnen)
   sonst Zeit für die Icons?           → measure_icons() → update_icons
   schlafen bis zur nächsten fälligen Messung – ODER bis wake gesetzt wird (dann sofort neu planen).
   ```
   `finally`: `pc.Close()`, `nvidia.close()`.

`update_icons` zeichnet ein Icon nur neu, wenn sich die angezeigte ganze Zahl geändert hat.

**`fenster_braucht(geraete)`** – vom Detailfenster aufgerufen: Merkt sich, was gebraucht wird; ruft beim Wechsel
offen↔zu `effizienz_anwenden()` auf; verwirft beim Schließen den alten Snapshot; weckt den Mess-Thread.

**`ipc_server()` – der IPC-Thread:** Bindet 127.0.0.1:47815 (ist der Port belegt, z. B. direkt nach einem Neustart:
alle 2 s neu versuchen, einmal loggen). Dann: `accept` → bis zu 64 Bytes lesen → `handle_command` → JSON-Zeile
zurück → Verbindung zu. `handle_command`: `"status"` beantwortet er direkt aus `self.current`; `"reload"`/`"quit"`
legt er in die Queue (die eigentliche Arbeit macht der GUI-Thread).

**`reload_settings()`**: `SETTINGS` neu laden, aber `"window"` behalten (gehört dem Fenster, die Toolbox hat evtl.
einen alten Stand), Icons neu zeichnen, Icon-Sensoren neu suchen, Menüs/Fenster auffrischen, Mess-Thread wecken.

**`poll_queue()`**: `"toggle"` (Fenster auf/zu), `"data"` (Fenster aktualisieren), `"reload"`, `"quit"`. Prüft bei
offenem Fenster alle 100 ms, sonst alle 250 ms (spart Aufwachen im Leerlauf).

**`quit()`**: `stop` + `wake` setzen, Fenstergeometrie speichern, Icons stoppen, `mainloop` beenden.

#### Threads im Monitor auf einen Blick

| Thread | Aufgabe |
|---|---|
| Haupt-Thread | tkinter (Detailfenster, `poll_queue`) |
| pystray | je Icon ein eigener Thread mit Windows-Nachrichtenschleife (Klicks, Menü) |
| `sensor_thread` | misst |
| `ipc_thread` | wartet auf Befehle |
| (kurzzeitig) | Thread zum Lesen der Hardwaredaten (`detailfenster.py`) |

### 4.9 `programme\hardware_monitor\detailfenster.py` – das Fenster mit den Werten

#### Bausteine für `detailfenster_inhalt.py` (ähnlich wie `base.py`, nur fürs Detailfenster)

| Baustein | Bedeutung |
|---|---|
| `Tab(titel, *gruppen)` | ein Reiter |
| `Gruppe(geraet, *werte, name="*", titel=None)` | Werte EINES Gerätetyps. Gibt es mehrere passende Geräte (drei Laufwerke), erscheint die Gruppe für jedes einmal. `name` filtert Geräte nach Namen. |
| `Wert(sensor, typ=None, text=None, ohne=None)` | eine Zeile. `*` als Platzhalter. `typ` nur nötig, wenn derselbe Name mehrfach vorkommt („GPU Core“ ist Temperatur, Auslastung UND Takt). `typ` darf deutsch („Temperatur“) oder englisch („Temperature“) sein. `ohne` schließt Namen aus, die trotz Platzhalter nicht dazugehören (`"CPU Core #*"`, `ohne="*Distance*"`). |
| `Abschnitt(titel, *werte, eine_zeile=False)` | einklappbarer Unterpunkt in einer Gruppe (z. B. „Lüfter“). `eine_zeile=True` zeigt gleichnamige Werte in einer Zeile: den ersten als Wert, den zweiten als Balken mit % (Fan #1: Drehzahl und Ansteuerung); „Control“ im Namen zählt dabei nicht mit. 0 RPM bei einem angesteuerten Lüfter erscheint grau als „steht“. |
| `AlleSensoren()` | alles, was LHM findet (zum Nachschlagen) |
| `Hardwaredaten()` | der Tab mit den festen Daten (`hardwaredaten.py`) |

#### Anzeige-Helfer

`TYPE_LABELS` (englisch → deutsch), `UNITS` (Nachkommastellen, Einheit), `BAR_TYPES` (bekommen einen Text-Balken),
`fmt_value` (Zahl schön formatieren, deutsches Komma, B/s→KB/s→MB/s, GB→TB …), `AMPEL` + `temp_stufe`/`temp_color`
(grün/gelb/rot nach `cpu_…`/`gpu_warn_temp` und `…_hot_temp` – GPU-Sensoren nach den GPU-Grenzen, alles andere nach den CPU-Grenzen; dieselben Farben auch in den Tray-Icons), `balken` (██████░░░░),
`erklaere` (passenden Erklärtext aus `ERKLAERUNGEN` suchen). `ICON_DATEI` = `toolbox\toolbox.ico` (Fenstersymbol).

#### Vom Inhalt zur Liste

| Funktion | Was sie tut |
|---|---|
| `benoetigte_geraete(tab)` | welche Geräte der Mess-Thread für diesen Tab lesen muss: Hardwaredaten → `set()` (nichts), AlleSensoren → `None` (alles), sonst `{g.geraet …}` |
| `zeilen(tab, snap)` | macht aus Tab + Snapshot eine flache Liste (Schlüssel, Eltern-Schlüssel, Text, Sensor). Überschriften haben keinen Sensor. Die Schlüssel bleiben stabil, solange sich der Aufbau nicht ändert. |
| `hwdaten_zeilen(daten)` | dasselbe für die Hardwaredaten (Bereich → Gerät → Feld) |

#### Klasse `Detailfenster`

- `__init__`: Toplevel (Titel = Pfad von `hardware_monitor.py`, `PROGRAMM_DATEI` – wie bei der Toolbox),
  Skalierungsfaktor (1,0 bei 100 %, 1,5 bei 150 %; `px()` rechnet damit um), ttk-Styles (`stil()`: Farben `BG`,
  `BG_LIST`, `FG`, `SUB`, `HOVER`, `AKZENT` – eine eigene Kopie der dunklen Toolbox-Palette), Kopfzeile mit den zwei
  großen Werten und „● Live“ / „Daten werden geladen …“, Notebook (Tabs), Fußzeile (Erklärungen).
  ✕ versteckt nur. `<Map>`/`<Unmap>` (gezeigt/minimiert) → `sichtbarkeit()` → `melden()` → `app.fenster_braucht(...)`.
- `inhalt_laden()`: Liest `detailfenster_inhalt.py` – aber nur, wenn sich ihre Änderungszeit (mtime) geändert hat
  (`importlib.reload`). Hat die Datei einen Fehler, läuft das Fenster trotzdem (Rückfall: Tab „Alles“) und die
  Fußzeile zeigt den Fehler rot. → Du kannst die Datei bei laufendem Monitor bearbeiten; Fenster zu/auf genügt.
- `tabs_bauen(tabs)`: Pro Tab ein Frame mit Treeview + Scrollbar; im Hardwaredaten-Tab zusätzlich die Leiste mit
  den Unterreitern „Übersicht“ / „Details“ (Radiobuttons auf `self.hw_ansicht`, `uebersicht()` fragt sie ab) und
  „Alles kopieren“, das wie die Bereichs-Knöpfe kopiert, was die gewählte Ansicht zeigt. `hw_spalten()` gibt in der
  Übersicht der Namensspalte die ganze Breite. Tags färben Zeilen (bereich, gruppe, typ, hinweis, Ampelfarben).
- `zeigen()`/`verstecken()`/`umschalten()`; `platzieren()`: gespeicherte Position, wenn sie noch auf einem
  angeschlossenen Bildschirm liegt – sonst unten rechts auf dem Bildschirm, auf dem geklickt wurde, über der
  Taskleiste. `speichern()`: Geometrie → `app.fenster_geometrie` → `daten\hardware_monitor.json` (`"window"`).
- `tabs_ausblenden()`: Sobald `app.vorhanden` bekannt ist (nach dem Nachladen der Hardware), werden Tabs versteckt
  (`notebook.hide`), deren Geräte der PC nicht hat – z. B. „Mainboard“ am Laptop, „Akku“ am Desktop. Läuft einmal
  pro Stand (`ausgeblendet_fuer`); ist gerade ein versteckter Tab gewählt, springt ttk von selbst zum nächsten.
  `notebook.index("current")` zählt versteckte Tabs mit – die Zuordnung zu `self.tabs` bleibt also gleich.

**`aktualisieren()`** – wird bei jeder neuen Messung (`"data"`) und bei Tabwechsel aufgerufen:

- Tabs ausblenden (siehe oben), Kopfwerte setzen.
- Passt der Snapshot zum aktiven Tab? (Sind alle gebrauchten Geräte gemessen? `gebraucht <= gemessen`) Wenn nicht:
  „Lade Sensordaten …“ – die passende Messung kommt gleich, weil `melden()` den Mess-Thread geweckt hat.
- „Signatur“-Trick: Die Liste wird nur dann komplett neu aufgebaut, wenn sich ihr Aufbau (Schlüssel/Texte)
  geändert hat. Sonst werden nur die Werte in den vorhandenen Zeilen ersetzt. Das verhindert Flackern und hält
  auf-/zugeklappte Zustände und die Scrollposition.
- Merkt sich, welche Zeile welcher Sensor ist (für Erklärungen) und was ein Klick kopiert (`self.kopierbar`).

**Erklären/Kopieren**

- `<Motion>` über einer Zeile → `erklaeren()` zeigt den Text in der Fußzeile (bei Hardwaredaten den vollen Wert).
- `<Button-1>` → `kopieren()`: Gerätename bzw. Hardwaredaten-Wert in die Zwischenablage (nicht beim Klick aufs
  Auf-/Zuklapp-Dreieck). Bestätigung „✓ … kopiert“ für 2 s.
- „⧉ Kopieren“-Buttons pro Bereich: echte `ttk.Button`s, mit `place()` ÜBER die Treeview gelegt, auf Höhe ihrer
  Zeile (`tree.bbox(key)`). Weil die Treeview selbst keine Widgets in Zeilen kann, werden sie bei Scrollen,
  Auf-/Zuklappen und Größenänderung neu platziert (`knoepfe_platzieren`) bzw. ausgeblendet.

**Hardwaredaten laden:** `hwdaten_laden()` startet einen Thread mit `hardwaredaten.lesen()`; `hwdaten_warten()`
schaut per `after(100)` nach, ob er fertig ist, und zeigt dann an. Gelesen wird beim ersten Anzeigen und nach jedem
erneuten Öffnen des Fensters (z. B. für neu eingesteckte USB-Geräte).

### 4.10 `programme\hardware_monitor\detailfenster_inhalt.py` – was im Fenster steht

Reine „Beschreibungs-Datei“ – hier passt du das Fenster an, ohne GUI-Code zu verstehen.

```python
FENSTER = [ Tab("Temperaturen", Gruppe("cpu", Wert(...), ...), Gruppe("gpu", ...)),
            Tab("CPU", ...), Tab("GPU", ...), Tab("RAM", ...), Tab("Mainboard", ...),
            Tab("Laufwerke", ...), Tab("Netzwerk", ...), Tab("Akku", ...), Tab("Hardwaredaten", Hardwaredaten()),
            # Tab("Alles", AlleSensoren()),   ← zum Nachschlagen wieder einkommentieren
          ]
```

Die Sensornamen hängen von der Hardware ab: AMD meldet „Core (Tctl/Tdie)“ und „Package“, Intel „CPU Package“,
„Core Max“ und „CPU Core #1“ … Darum stehen die Namen für beide in denselben Gruppen – was es nicht gibt, erscheint
einfach nicht. Intel-Onboard-Grafik hat keine Temperatur, nur Leistung und Windows-Werte („D3D …“); dafür gibt es im
GPU-Tab eine eigene Gruppe mit `name="Intel*"` (bei Nvidia-Karten gibt es die D3D-Werte auch, die sollen dort aber
nicht erscheinen).

- `ERKLAERUNGEN = [ (Sensortyp, regulärer Ausdruck, Text), ... ]` – der erste passende Eintrag gewinnt. Das Muster
  muss auf den GANZEN Namen passen (`re.fullmatch`). `{0}` im Text = erste Klammergruppe des Musters (z. B. die
  Kernnummer).
- `TYP_ERKLAERUNGEN = { Sensortyp: Text }` – Rückfall, wenn oben nichts passt.

### 4.11 `programme\hardware_monitor\hardwaredaten.py` – Hersteller, IDs, Seriennummern

Liest per WMI (über pythonnet + System.Management), braucht weder Adminrechte noch LHM. Lässt sich allein testen:

```
runtime\python.exe programme\hardware_monitor\hardwaredaten.py
```

| Teil | Bedeutung |
|---|---|
| `abfrage(wql, scope)` | führt eine WQL-Abfrage aus → Liste von dicts (alle Werte als Text). Fehler → leer + Log. |
| Helfer | `wert()` (Platzhalter wie „To Be Filled By O.E.M.“ → `None`), `mit_namen()` („10DE“ → „10DE (Nvidia)“), `datum()` (WMI-Datum → TT.MM.JJJJ), `pci_felder()`/`usb_ids()`/`ids_felder()` (IDs aus Kennungen per Regex), `hardware_id()` (Kennung ohne den Steckplatz-Teil) |
| Tabellen | `PCI_HERSTELLER`, `USB_HERSTELLER` (Auszüge – bei Bedarf ergänzen), `RAM_TEILENUMMER` (Hersteller aus dem Anfang der Teilenummer raten, weil Windows oft „Unknown“ meldet), `RAM_TYPEN`, `RAM_BAUFORMEN`, `NETZ_ARTEN`, `BUS_TYPEN`, `MEDIEN_TYPEN` |
| `gpu_arten()` | fragt per DXCore ab, welche GPU integriert / extern / dediziert ist (siehe Begriff DXCore); `com_methode()` ruft eine COM-Methode über ihre Nummer auf |
| Bereiche | `prozessoren`, `grafikkarten`, `mainboard` (+ BIOS), `arbeitsspeicher`, `laufwerke`, `netzwerk`, `audio`, `usb_geraete`. Jede Funktion liefert `[(Gerätename, [(Feld, Wert), …]), …]`. Virtuelle Geräte werden aussortiert. `grafikkarten` ordnet die Art aus `gpu_arten()` über Hersteller-/Produkt-ID zu, `netzwerk` die Art aus MSFT_NetAdapter über die Gerätekennung. `arbeitsspeicher` fasst verlöteten LPDDR-Speicher zu einem Eintrag zusammen – Windows meldet ihn je Speicherkanal, nicht je Riegel. `audio` nimmt PCI-, HDAUDIO- und `INTELAUDIO\FUNC_`-Geräte (Codec hinter Intel Smart Sound bei Laptops). `usb_geraete` fasst Einträge mit gleicher VID/PID zusammen (ein Gerät meldet sich oft mehrfach an). |
| `BEREICHE` | Liste (Anzeigename, Funktion) – Reihenfolge im Tab |
| `lesen()` | ruft alle Bereiche auf; ein kaputter Bereich verhindert die anderen nicht |
| `als_text` / `alles_als_text` / `modellnamen_als_text` | Textform für die Kopieren-Buttons |
| `ERKLAERUNGEN` | Feldname → Erklärung für die Fußzeile |

### 4.12 `Entfernen.cmd`

`setup.ps1 -Entfernen`: Toolbox und Monitor per „quit“ beenden, Aufgabe löschen (notfalls mit UAC), auf Nachfrage
alles Erzeugte und Heruntergeladene löschen: `runtime\`, die Starter (`Toolbox.exe`, `HardwareMonitor.exe`) und die
Downloads (`lhm\`). Die Verknüpfungen löscht es vorher immer, ohne Nachfrage (`Verknuepfungen-Loeschen` – danach
zeigten sie ja ins Leere): jede `.lnk` auf diese `Toolbox.exe` auf dem Desktop und im Startmenü samt Unterordnern,
also auch umbenannte oder verschobene. Verknüpfungen auf eine andere Toolbox bleiben. `daten\` bleibt – das gehört dir und verschwindet erst mit dem Ordner. PawnIO bleibt installiert
(andere Programme nutzen es evtl. auch): `winget uninstall namazso.PawnIO`.

---

## 5. Zusammenspiel an Beispielen

Was passiert wann?

**A) Du meldest dich bei Windows an**
Aufgabenplanung → startet `programme\hardware_monitor\HardwareMonitor.exe` mit Adminrechten (ohne Abfrage) → der
Starter startet `runtime\HardwareMonitor.exe "…\hardware_monitor.py"` (erbt die Adminrechte) und beendet sich → LHM
öffnet CPU+GPU → Mutex prüfen → Icons anmelden → Effizienzmodus an → Mess-Thread: Icons füllen, dann RAM & Co.
nachladen (~8 s) → danach alle 2 s (`icon_interval`) nur die zwei Icon-Werte.

**B) Du klickst aufs CPU-Icon**
pystray-Thread → `ui_queue.put("toggle")` → GUI-Thread (`poll_queue`, spätestens nach 250 ms) → Detailfenster bauen
(erstes Mal) → `inhalt_laden` → `zeigen` → `<Map>` → `melden()` → `fenster_braucht({"cpu","gpu"})` für Tab
„Temperaturen“ → Effizienzmodus aus, `wake.set()` → Mess-Thread misst sofort `collect({"cpu","gpu"})` → `"data"` →
`aktualisieren()` → „● Live“. Danach jede Sekunde (`popup_interval`).

**C) Du wechselst auf den Tab „Laufwerke“**
`<<NotebookTabChanged>>` → `melden()` → `fenster_braucht({"laufwerk"})` → `wake` → `collect({"laufwerk"})` (+ CPU,
+ GPU über NVML) → bis dahin „Lade Sensordaten …“.

**D) Du schiebst in der Toolbox „CPU rot ab“ auf 85**
Slider → `page.set("cpu_hot_temp", 85, later=True)` → `on_change` (gelb < rot sicherstellen) → `refresh` → 500 ms nach
dem Loslassen `save()` → `daten\hardware_monitor.json` schreiben → „Gespeichert ✓“ → `on_saved()` →
`run_async(ipc("reload"))` → Monitor-IPC-Thread → Queue → `reload_settings()` → Icons in neuer Farbe.

**E) Du klickst in der Toolbox „Beenden“**
`run_async(ipc("quit"))` → Monitor: Queue → `quit()` → Fenstergeometrie speichern, Icons weg, Mess-Thread endet,
`pc.Close()`. Toolbox: `poll_status_soon()` sieht kurz danach „Gestoppt“.

**F) Du startest die Toolbox ein zweites Mal**
`Toolbox.exe` → `runtime\Toolbox.exe toolbox.py` → `bring_existing_to_front()` → Verbindung zu 47816 → erste Toolbox
legt `"show"` in ihre Queue, antwortet „ok“ → der zweite Start beendet sich, das vorhandene Fenster kommt nach vorne.

**G) Du verschiebst den Projektordner**
`Toolbox.exe` im Ordner funktioniert sofort weiter (relative Pfade). Die Verknüpfungen „Windows Toolbox“ und die
Aufgabe zeigen aber noch auf den alten Ort → Toolbox warnt „Aufgabe startet einen anderen Ort“ → `Setup.exe`
(Schritt 5 biegt die Verknüpfungen um, Schritt 6 die Aufgabe, eine UAC-Abfrage) oder „Aufgabe aktualisieren“ in der
Toolbox.

**H) Du klickst in den Toolbox-Einstellungen „Aktualisieren“**
`git fetch` → neue Commits? → `git pull --ff-only` → `Einrichten.cmd -Neustart` in eigenem Fenster → beendet die
Toolbox → Pakete, `.exe`, Starter und Downloads auf den neuen Stand → Monitor neu starten → Toolbox neu starten.

---

## 6. Rezepte zum Weiterbauen

Allgemein: Erst lesen, was in der Nähe schon existiert, und im gleichen Stil weiterschreiben (deutsche Namen und
Kommentare, kurze Erklär-Kommentare über dem „Warum“). Nach Änderungen die README des Tools nachziehen.

### 6.1 Ein neues Tool hinzufügen

1. Ordner `programme\mein_tool\` anlegen.
2. `programme\mein_tool\programm.json` – der Ausweis:
   ```json
   {
     "id": "mein_tool",
     "name": "Mein Tool",
     "version": "1.0",
     "kategorie": "Allgemein",
     "beschreibung": "Kurze Beschreibung",
     "seite": "mein_tool_gui.py"
   }
   ```
3. `programme\mein_tool\mein_tool_gui.py`:
   ```python
   from pathlib import Path
   from base import Buttons, Button, Choice, Section, Switch, Text, ToolPage

   class MeinToolPage(ToolPage):
       defaults = {"rate": 2, "aktiv": True}            # gespeichert wird in daten\mein_tool.json

       def layout(self):
           return [
               Section("Allgemein",
                       Text("Was dieses Tool macht."),
                       Switch("Eingeschaltet", key="aktiv"),
                       Choice("Rate", "rate", {"1 s": 1, "2 s": 2, "5 s": 5})),
               Section("Aktionen",
                       Buttons(Button("Los", self.los), Button("Ordner öffnen",
                               lambda: self.open(Path(__file__).parent), style="grau",
                               ziel=Path(__file__).parent))),          # steht beim Drüberfahren unten links
           ]

       def los(self):
           self.app.run_async(self.lange_arbeit, self.fertig)   # nie im GUI-Thread blockieren

       def lange_arbeit(self):
           ...                                                    # läuft im Hintergrund
           return "Ergebnis"

       def fertig(self, ergebnis):
           self.app.toast(f"Fertig: {ergebnis}")                  # läuft wieder im GUI-Thread

   SEITE = MeinToolPage
   ```
4. `programme\mein_tool\README.md` schreiben und in der Tabelle der Haupt-README verlinken.
5. Toolbox neu starten – das Tool erscheint im Tab „Allgemein“. Den XXX-Platzhalter dieses Tabs kannst du dann in
   `toolbox.py` (`PLACEHOLDERS`) entfernen.

**Braucht das Tool ein eigenes Hintergrundprogramm** (wie der Monitor), nimm `hardware_monitor.py` als Vorbild:
eigener Prozess, eigener IPC-Port (z. B. 47817), Einzelinstanz-Sperre, logging nach `daten.log("mein_tool")`,
Einstellungen aus `daten.einstellungen("mein_tool")`. Dazu in `mein_tool_gui.py` drei Funktionen `laeuft(app)`,
`beenden(app)`, `starten(app)` (Vorbild: `hardware_monitor_gui.py`) und `PROGRAMM = Programm(laeuft, beenden,
starten)` – dann beenden/starten es „Toolbox und alle Programme“ in den Toolbox-Einstellungen automatisch mit.
Im Ausweis kommen dann `"skript": "mein_tool.py"` und `"starter": "MeinTool.exe"` dazu – `Einrichten.cmd` legt daraus
`runtime\MeinTool.exe` (eigener Name im Task-Manager) und den Starter `programme\mein_tool\MeinTool.exe` an.
Muss etwas heruntergeladen werden, kommt es als `"downloads"` in den Ausweis (Vorbild: `hardware_monitor`).

### 6.2 Ein neues Paket benutzen

In `requirements.txt` MIT Version eintragen (am einfachsten: in `runtime\` installieren, testen, dann
`runtime\python.exe -m pip freeze` – das listet auch die neuen Abhängigkeiten) UND in `setup.ps1` die Prüfzeile
`& $RuntimePy -c 'import tkinter, customtkinter, …'` ergänzen. Dann `Einrichten.cmd` ausführen (installiert es in
`runtime\`).

### 6.3 Einen Wert/Tab im Detailfenster ändern

`runtime\python.exe programme\hardware_monitor\hardware_monitor.py --list` in einem ADMIN-Terminal → Namen ablesen
→ in `detailfenster_inhalt.py` eine `Wert(...)`-Zeile ergänzen → speichern → Fenster zu und wieder auf.
Optional eine Erklärung in `ERKLAERUNGEN` ergänzen. Neuer Tab = neuer `Tab(...)`-Eintrag in `FENSTER`.

### 6.4 Eine neue Einstellung für den Monitor

Muss an mehreren Stellen passieren:

1. `hardware_monitor.py`: `DEFAULT_SETTINGS` + Prüfung in `load_settings()` (sonst wird der Wert auf den Standard
   zurückgesetzt!)
2. `hardware_monitor_gui.py`: `defaults` + passender Baustein in `layout()`
3. dort benutzen, wo sie wirken soll (`SETTINGS["neu"]` im Monitor; nach `"reload"` ist sie aktuell)
4. README des Monitors (Tabelle „Einstellungen“)

Braucht nur die Toolbox den Wert (wie `task_name`), genügt 2. – der Monitor lässt unbekannte Schlüssel stehen.

### 6.5 Einen neuen IPC-Befehl

`hardware_monitor.py` → `handle_command()` erweitern (alles, was tkinter/Icons anfasst, über `ui_queue` +
`poll_queue`!). Toolbox-Seite → `ipc("neuer_befehl")` über `run_async` aufrufen. README-Tabelle „Fernsteuerung“
ergänzen.

### 6.6 Einen neuen Baustein für `base.py`

Von `Element` erben, `create()` (Widget zurückgeben) und ggf. `refresh()` (Wert anzeigen) schreiben; bei Änderungen
`page.set(self.key, wert)` aufrufen. Braucht er mehrere Zeilen, `place()` überschreiben und die Zeilenzahl
zurückgeben (Vorbild: `TextList`). Farben aus den Konstanten oben nehmen.

### 6.7 Einen neuen Bereich bei den Hardwaredaten

In `hardwaredaten.py` eine Funktion schreiben, die `[(Name, [(Feld, Wert), …]), …]` liefert (WMI-Abfrage mit
`abfrage()`), und in `BEREICHE` eintragen. Welche WMI-Klassen/Felder es gibt: in PowerShell
`Get-CimInstance <Klasse> | fl *`.

### 6.8 Farben/Aussehen ändern

Toolbox: Konstanten oben in `base.py` (und ggf. `apply_theme`). Detailfenster: `BG`, `BG_LIST`, … in
`detailfenster.py`; `AMPEL` dort färbt auch die Zahlen in den Tray-Icons.

### 6.9 Etwas am Einrichten ändern

`setup\setup.ps1`. Regeln: jeder Schritt prüft erst, ob er schon erledigt ist (idempotent); Datei als UTF-8 MIT BOM
und mit CRLF speichern; Adminkram in `Admin-Schritte` (über die `-Admin`-Liste); nichts außerhalb des Ordners
voraussetzen; was je Programm gilt, gehört in die `programm.json`, nicht ins Skript. Danach README-Abschnitt
„Einrichtung“ anpassen. Änderungen an `setup\starter.cs` übernimmt `Einrichten.cmd` von selbst (der Quelltext
unterscheidet sich → Starter wird neu gebaut).

---

## 7. Stolperfallen und Werte, die übereinstimmen müssen

Muss an mehreren Stellen gleich sein:

| Wert | Wo |
|---|---|
| IPC-Port 47815 | `IPC_PORT` in `hardware_monitor.py`, `IPC_PORT` in `hardware_monitor_gui.py`, `$IpcPort` in `setup.ps1` |
| Toolbox-Port 47816 | `GUI_PORT` in `toolbox.py`, `$GuiPort` in `setup.ps1` |
| Aufgabenname | `DEFAULT_TASK` in `hardware_monitor_gui.py`, `$Aufgabe` in `setup.ps1` |
| Standard-Einstellungen | `DEFAULT_SETTINGS` in `hardware_monitor.py` ↔ `defaults` in `hardware_monitor_gui.py` |
| Gerätenamen | `HW_GERAET` in `hardware_monitor.py` ↔ `Gruppe("...")` in `detailfenster_inhalt.py` |
| LHM-Version | `"downloads"` in `programme\hardware_monitor\programm.json`: `version`, `url` und `sha256` gehören zusammen (neue Version → neue Prüfsumme, Sensornamen prüfen) |
| Python-Version | `$PythonVersion` in `setup.ps1` ↔ die festen Versionen in `requirements.txt` |

Typische Fehler:

- Widgets aus einem Hintergrund-Thread ändern → zufällige Abstürze/Einfrieren. Immer über Queue/`run_async`.
- Langsames im GUI-Thread (Netzwerk, PowerShell, `time.sleep`) → Fenster friert ein.
- Neue Einstellung nur in `DEFAULT_SETTINGS`, aber nicht in `load_settings()` → bleibt immer beim Standardwert.
- Import von Nachbardateien in einem neuen Skript ohne `sys.path.insert` → „ModuleNotFoundError“ mit `runtime\`.
- Fehler in pythonw-Programmen sieht man nicht → in `daten\logs\` nachsehen, oder mit `python.exe` starten.
- Hardware-Monitor ohne Adminrechte → CPU zeigt „--“ (z. B. bei Doppelklick auf `HardwareMonitor.exe`).
- `.ps1` ohne BOM gespeichert → Umlaute in der Ausgabe kaputt. `.cmd`/`.ps1` mit LF statt CRLF → seltsame Fehler.
- Lambda in einer Schleife ohne Standardwert-Trick → alle Knöpfe machen dasselbe.
- Variablen-Name der Seite überschreibt etwas von CTkScrollableFrame (z. B. eine Methode namens „configure“,
  „grid“, „after“, „destroy“) → merkwürdiges Verhalten. Lieber deutsche/eindeutige Namen.
- In PowerShell eine eigene Eigenschaft so nennen wie ein JSON-Feld, nur anders geschrieben (`Skript`/`skript`) →
  „member already exists“ (siehe 3.9).

---

## 8. Fehlersuche und Testen

| Was | Wie |
|---|---|
| Logs | `daten\logs\toolbox.log`, `daten\logs\hardware_monitor.log` |
| Toolbox mit Konsole | `runtime\python.exe toolbox\toolbox.py` |
| Alle Sensoren | `runtime\python.exe programme\hardware_monitor\hardware_monitor.py --list` (Admin-Terminal!) |
| Hardwaredaten | `runtime\python.exe programme\hardware_monitor\hardwaredaten.py` |
| Wer belegt einen Port? | `netstat -ano \| findstr 47815` (letzte Spalte = Prozess-ID, im Task-Manager suchen) |
| Aufgabe ansehen | Aufgabenplanung öffnen oder `Get-ScheduledTask HardwareMonitor \| fl *` |
| Starter neu bauen | `runtime\starter\<id>.cs` löschen und `Einrichten.cmd` ausführen |

Syntax prüfen, ohne zu starten (erzeugt kein `__pycache__`):

```
runtime\python.exe -c "import ast,sys; ast.parse(open(sys.argv[1], encoding='utf-8').read())" datei.py
```

Läuft der Monitor? Status direkt abfragen:

```
runtime\python.exe -c "import socket; s=socket.create_connection(('127.0.0.1',47815)); s.sendall(b'status\n'); print(s.recv(999))"
```

Monitor im Vordergrund testen (mit Konsole, als Admin): Toolbox → Beenden, dann im Admin-Terminal
`runtime\python.exe programme\hardware_monitor\hardware_monitor.py`.

Debugger: In Zed/VS Code Haltepunkte setzen geht für die Toolbox gut; für den Monitor braucht der Editor
Adminrechte. Alternativ gezielt `logging.info(...)` einstreuen. → https://docs.python.org/3/library/pdb.html

---

## 9. Glossar

| Begriff | Bedeutung |
|---|---|
| Admin / erhöht | Prozess mit vollen Administratorrechten (Integritätsstufe „Hoch“) |
| Ausweis | `programm.json` eines Programms: Name, Tab, Version, Skript, Starter, Downloads |
| Callback | Funktion, die man übergibt, damit sie später aufgerufen wird (`command=…`, `on_done=…`) |
| Daemon-Thread | Hintergrund-Thread, der beim Programmende einfach mit endet |
| DLL | Bibliotheksdatei unter Windows (Code, den Programme laden) |
| Event-Loop | Endlosschleife der GUI, die auf Ereignisse wartet (`mainloop`) |
| GIL | Sperre: nur ein Thread führt gleichzeitig Python-Code aus |
| Idempotent | mehrfach ausführen = gleiches Ergebnis wie einmal |
| IPC | Kommunikation zwischen Prozessen (hier: TCP auf 127.0.0.1) |
| JSON | Textformat für Daten |
| LHM | LibreHardwareMonitor |
| Mutex | Sperre; ein benannter Mutex existiert systemweit nur einmal |
| NVML | Nvidias Bibliothek zum Abfragen der Grafikkarte |
| pythonnet / clr | Brücke zwischen Python und .NET |
| Port | Nummer, unter der ein Programm Netzwerkverbindungen annimmt |
| Prozess | ein laufendes Programm mit eigenem Speicher |
| Queue | thread-sichere Warteschlange |
| Snapshot | eine Messung aller gebrauchten Sensoren zu einem Zeitpunkt (Ergebnis von `collect()`) |
| Starter | kleine `.exe` (C#), die ein Programm mit relativen Pfaden startet und sich beendet |
| Thread | paralleler Ablauf innerhalb eines Prozesses |
| Tray / Infobereich | Symbole unten rechts neben der Uhr |
| UAC | Benutzerkontensteuerung (die „Möchten Sie zulassen …“-Abfrage) |
| WMI / WQL | Windows-Verwaltungsdaten / die SQL-ähnliche Abfragesprache dafür |
| Widget | Bedienelement einer GUI (Knopf, Text, Liste …) |

---

## 10. Alle Links gesammelt

### Python allgemein

- https://docs.python.org/3/tutorial/ – Offizielles Tutorial
- https://py-tutorial-de.readthedocs.io/ – Tutorial auf Deutsch
- https://realpython.com/ – Viele gute Artikel
- https://peps.python.org/pep-0008/ – Stilleitfaden
- https://docs.python.org/3/tutorial/modules.html – Module, import, `__pycache__`
- https://docs.python.org/3/tutorial/classes.html – Klassen
- https://docs.python.org/3/tutorial/errors.html – Ausnahmen
- https://docs.python.org/3/library/dataclasses.html
- https://docs.python.org/3/library/pathlib.html
- https://docs.python.org/3/library/json.html
- https://docs.python.org/3/howto/logging.html
- https://docs.python.org/3/howto/regex.html – Reguläre Ausdrücke (+ https://regex101.com/)
- https://docs.python.org/3/library/fnmatch.html
- https://docs.python.org/3/library/importlib.html
- https://docs.python.org/3/library/subprocess.html
- https://docs.python.org/3/library/ctypes.html
- https://docs.python.org/3/library/site.html
- https://docs.python.org/3/using/windows.html – Python unter Windows, `._pth`-Dateien
- https://peps.python.org/pep-0514/ – Python in der Registry
- https://pip.pypa.io/en/stable/user_guide/

### Threads, Netzwerk

- https://docs.python.org/3/library/threading.html
- https://docs.python.org/3/library/queue.html
- https://realpython.com/intro-to-python-threading/
- https://docs.python.org/3/howto/sockets.html
- https://realpython.com/python-sockets/
- https://www.json.org/json-de.html

### GUI

- https://tkdocs.com/tutorial/ – tkinter/ttk, sehr empfehlenswert
- https://docs.python.org/3/library/tkinter.html
- https://docs.python.org/3/library/tkinter.ttk.html
- https://realpython.com/python-gui-tkinter/
- https://customtkinter.tomschimansky.com/documentation/
- https://github.com/TomSchimansky/CustomTkinter
- https://pystray.readthedocs.io/
- https://pillow.readthedocs.io/

### .NET, Hardware

- https://pythonnet.github.io/
- https://learn.microsoft.com/de-de/dotnet/core/introduction
- https://learn.microsoft.com/de-de/dotnet/csharp/language-reference/compiler-options/ – csc.exe (Starter)
- https://github.com/LibreHardwareMonitor/LibreHardwareMonitor
- https://pawnio.eu/
- https://docs.nvidia.com/deploy/nvml-api/
- https://learn.microsoft.com/de-de/windows/win32/wmisdk/about-wmi
- https://learn.microsoft.com/de-de/windows/win32/wmisdk/wql-sql-for-wmi
- https://learn.microsoft.com/de-de/windows/win32/cimwin32prov/win32-provider – alle Win32_…-Klassen
- https://pci-ids.ucw.cz/ – PCI-Hersteller-/Geräte-IDs
- http://www.linux-usb.org/usb.ids – USB-IDs

### Windows

- https://learn.microsoft.com/de-de/windows/security/application-security/application-control/user-account-control/
- https://learn.microsoft.com/de-de/windows/win32/secauthz/mandatory-integrity-control
- https://learn.microsoft.com/de-de/windows/win32/taskschd/task-scheduler-start-page
- https://learn.microsoft.com/en-us/powershell/module/scheduledtasks/register-scheduledtask
- https://learn.microsoft.com/de-de/windows/win32/api/shellapi/nf-shellapi-shellexecuteexw
- https://learn.microsoft.com/de-de/windows/win32/api/synchapi/nf-synchapi-createmutexw
- https://learn.microsoft.com/de-de/windows/win32/api/processthreadsapi/nf-processthreadsapi-setprocessinformation
- https://devblogs.microsoft.com/performance-diagnostics/introducing-ecoqos/
- https://learn.microsoft.com/de-de/windows/win32/hidpi/high-dpi-desktop-application-development-on-windows
- https://learn.microsoft.com/de-de/windows/win32/shell/appids

### Skripte und Werkzeuge

- https://learn.microsoft.com/de-de/powershell/scripting/overview
- https://learn.microsoft.com/de-de/powershell/module/microsoft.powershell.core/about/about_execution_policies
- https://learn.microsoft.com/de-de/powershell/scripting/whats-new/differences-from-windows-powershell
- https://ss64.com/nt/ – Nachschlagewerk für cmd/Batch
- https://ss64.com/ps/ – Nachschlagewerk für PowerShell
- https://learn.microsoft.com/de-de/windows/package-manager/winget/
- https://learn.microsoft.com/de-de/windows-server/administration/windows-commands/robocopy

### Git

- https://git-scm.com/book/de/v2
- https://git-scm.com/docs/gitignore
- https://git-scm.com/docs/gitattributes
