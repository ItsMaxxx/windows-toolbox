"""
Das Detailfenster des Hardware-Monitors (tkinter + ttk).

WAS im Fenster steht, steht in detailfenster_inhalt.py – nur dort musst du etwas ändern, z. B.:

    Tab("GPU",
        Gruppe("gpu",
               Wert("GPU Core", typ="Temperatur"),
               Wert("GPU Fan *", typ="Lüfter")))

Diese Datei baut daraus das Fenster und muss normalerweise nicht angefasst werden – wie base.py bei der Toolbox.
Änderungen an detailfenster_inhalt.py werden beim nächsten Öffnen des Fensters übernommen (kein Neustart nötig).
"""

import ctypes
import fnmatch
import importlib
import logging
import re
import threading
import tkinter as tk
import tkinter.font as tkfont
from ctypes import wintypes
from pathlib import Path
from tkinter import ttk

import hardwaredaten
from hardwaredaten import num

INHALT_DATEI = Path(__file__).with_name("detailfenster_inhalt.py")
ICON_DATEI = Path(__file__).resolve().parents[2] / "toolbox" / "programm.ico"     # ⚒ auf Grün, wie alle Programme
# Fenstertitel: der Pfad des Programms, wie der Explorer seinen Ordner zeigt. Im Task-Manager steht er dann unter
# „Hardware-Monitor“ und zeigt, welche Kopie läuft (z. B. nach dem Verschieben des Ordners).
PROGRAMM_DATEI = Path(__file__).resolve().with_name("hardware_monitor.py")


# ---------- Bausteine für detailfenster_inhalt.py ----------
class Tab:
    """Ein Tab im Fenster: Titel und darin die Gruppen (oder AlleSensoren() bzw. Hardwaredaten())."""

    def __init__(self, titel, *gruppen):
        self.titel, self.gruppen = titel, gruppen


class Gruppe:
    """Werte eines Geräts, mit dem Gerätenamen als Überschrift.

    geraet: "cpu", "gpu", "ram", "mainboard", "laufwerk", "netzwerk", "akku" oder "weitere"
            (steht bei `hardware_monitor.py --list` in eckigen Klammern).
            Gibt es mehrere passende Geräte (z. B. drei Laufwerke), erscheint die Gruppe für jedes einmal.
            Hat der PC keins davon (z. B. keinen Akku), wird der Tab ausgeblendet.
    name:   nur Geräte, deren Name hierzu passt (* als Platzhalter), z. B. name="Total Memory"
    titel:  eigene Überschrift statt des Gerätenamens
    werte:  Wert(...)-Zeilen und Abschnitt(...)e (einklappbare Unterpunkte, z. B. alle Lüfter)
    """

    def __init__(self, geraet, *werte, name="*", titel=None):
        self.geraet, self.werte, self.name, self.titel = geraet, werte, name, titel


class Wert:
    """Eine Zeile im Fenster.

    sensor: Sensorname wie bei `hardware_monitor.py --list`; * als Platzhalter (z. B. "Fan #*" = alle Lüfter).
    typ:    nur nötig, wenn es den Namen mehrfach gibt ("GPU Core" ist Temperatur, Auslastung und Takt) –
            deutsch wie in --list ("Temperatur") oder englisch ("Temperature").
    text:   eigene Beschriftung statt des Sensornamens.
    ohne:   Sensoren, die trotz Platzhalter nicht dazugehören, z. B. ohne="*Distance*" bei "CPU Core #*".
    """

    def __init__(self, sensor, typ=None, text=None, ohne=None):
        self.sensor, self.text, self.ohne = sensor, text, ohne
        self.typ = LABEL_TYPES.get(typ, typ)            # "Temperatur" -> "Temperature"

    def passt(self, s):
        name = s["name"].lower()
        return ((self.typ is None or s["type"] == self.typ)
                and fnmatch.fnmatchcase(name, self.sensor.lower())
                and not (self.ohne and fnmatch.fnmatchcase(name, self.ohne.lower())))


class Abschnitt:
    """Ein einklappbarer Unterpunkt in einer Gruppe, z. B. alle Lüfter. Ohne passende Sensoren fehlt er.

    titel:      Beschriftung des Unterpunkts
    werte:      Wert(...)-Zeilen wie in einer Gruppe
    eine_zeile: Werte mit demselben Namen in EINER Zeile: der erste als Wert, der zweite als Balken mit Prozent
                dahinter – z. B. Fan #1 mit Drehzahl und Ansteuerung. „Control“ im Namen zählt dabei nicht mit,
                „Fan Control #1“ gehört also zu „Fan #1“.
    """

    def __init__(self, titel, *werte, eine_zeile=False):
        self.titel, self.werte, self.eine_zeile = titel, werte, eine_zeile

    def zeilen(self, sensors):
        """[(Text, Sensor)] in Anzeigereihenfolge. Bei eine_zeile hat der Sensor unter "balken" den zweiten Wert."""
        rows, gesehen = [], set()
        for wert in self.werte:
            for s in sensors:
                if wert.passt(s) and s["id"] not in gesehen:     # passt zu zwei Mustern (*Fan*, *Pump*) -> nur einmal
                    gesehen.add(s["id"])
                    rows.append((wert.text or s["name"], s))
        if not self.eine_zeile:
            return rows
        zeilen = {}                                      # Name ohne „Control“ -> [Text, Sensor]; dict hält die Reihenfolge
        for text, s in rows:
            name = re.sub(r"\s*\bControl\b", "", s["name"])
            if name not in zeilen:
                zeilen[name] = [text, s]
            elif "balken" not in zeilen[name][1]:
                zeilen[name][1] = {**zeilen[name][1], "balken": s}      # Kopie: der Snapshot bleibt unverändert
        return [tuple(zeile) for zeile in zeilen.values()]


class AlleSensoren:
    """Alles, was LibreHardwareMonitor findet – nach Gerät und Sensortyp sortiert. Gut zum Nachschlagen von Namen."""


class Hardwaredaten:
    """Feste Daten der Hardware: Hersteller, Modell, Hersteller- und Produkt-IDs, Seriennummern, Treiber.
    Wird beim Öffnen des Fensters einmal über Windows gelesen (hardwaredaten.py), nicht laufend gemessen."""


# ---------- Werte anzeigen ----------
# Sensortyp -> deutscher Name (wie bei --list). Die Reihenfolge gilt auch im Tab mit AlleSensoren().
TYPE_LABELS = {
    "Temperature": "Temperatur", "Load": "Auslastung", "Clock": "Takt", "Frequency": "Frequenz",
    "Power": "Leistung", "Voltage": "Spannung", "Current": "Stromstärke", "Energy": "Energie",
    "Fan": "Lüfter", "Control": "Lüftersteuerung", "Flow": "Durchfluss", "Data": "Daten",
    "SmallData": "Speicher", "Throughput": "Durchsatz", "Level": "Zustand", "Factor": "Faktor",
    "TimeSpan": "Zeit", "Timing": "Timing", "Noise": "Lautstärke", "Conductivity": "Leitfähigkeit",
    "Humidity": "Luftfeuchtigkeit",
}
LABEL_TYPES = {label: typ for typ, label in TYPE_LABELS.items()}

UNITS = {   # Sensortyp -> (Nachkommastellen, Einheit)
    "Temperature": (0, "°C"), "Load": (0, "%"), "Control": (0, "%"), "Level": (0, "%"),
    "Humidity": (0, "%"), "Clock": (0, "MHz"), "Frequency": (0, "Hz"), "Power": (1, "W"),
    "Voltage": (3, "V"), "Current": (2, "A"), "Fan": (0, "RPM"),
    "Flow": (0, "L/h"), "Data": (1, "GB"), "SmallData": (0, "MB"), "Timing": (1, "ns"),
    "Noise": (0, "dBA"), "Conductivity": (0, "µS/cm"), "Factor": (2, ""),
}
BAR_TYPES = {"Temperature", "Load", "Control", "Level", "Humidity"}      # Werte von 0–100 bekommen einen Balken
OHNE_AMPEL = ("*Distance to TjMax", "Warning Temperature", "Critical Temperature")   # Grenzwerte, keine Messwerte


def fmt_rate(bytes_per_s):
    for unit in ("B/s", "KB/s", "MB/s", "GB/s"):
        if bytes_per_s < 1024 or unit == "GB/s":
            return f"{num(bytes_per_s, 0 if unit == 'B/s' else 1)} {unit}"
        bytes_per_s /= 1024


def fmt_value(sensor_type, value):
    if sensor_type == "Throughput":
        return fmt_rate(value)
    if sensor_type == "TimeSpan":
        minutes = int(value // 60)
        return f"{minutes // 60}:{minutes % 60:02d} h"
    if sensor_type == "Data" and value >= 1024:          # große Datenmengen lesbarer in TB
        return f"{num(value / 1024, 2)} TB"
    if sensor_type == "Energy":                          # LHM liefert mWh, z. B. Akku-Kapazität
        return f"{num(value / 1000, 1)} Wh"
    if sensor_type == "SmallData" and value >= 1024:     # z. B. Grafikspeicher lieber in GB
        return f"{num(value / 1024, 1)} GB"
    if sensor_type == "Factor" and value == int(value):  # Zähler wie Power On Hours ohne ",00"
        return num(value, 0)
    decimals, unit = UNITS.get(sensor_type, (1, ""))
    return f"{num(value, decimals)} {unit}".strip()


AMPEL = {"grau": (143, 163, 184), "gruen": (61, 220, 151), "gelb": (245, 196, 81), "rot": (255, 100, 100)}


def temp_stufe(value, settings, kind):
    """"gruen", "gelb" oder "rot" je nach den Grenzen aus den Einstellungen ("grau" ohne Wert).
    kind: "cpu" oder "gpu" – beide haben eigene Grenzen."""
    if value is None:
        return "grau"
    if value < settings[f"{kind}_warn_temp"]:
        return "gruen"
    return "gelb" if value < settings[f"{kind}_hot_temp"] else "rot"


def temp_color(value, settings, kind):
    """Ampelfarbe (RGB) für eine Temperatur – dieselbe in Tray-Icons und Fenster."""
    return AMPEL[temp_stufe(value, settings, kind)]


def hex_color(rgb):
    return "#%02x%02x%02x" % rgb


def balken(value):
    """Kleiner Text-Balken für Werte von 0–100, z. B. ████░░░░░░ für 40 %."""
    filled = round(max(0.0, min(value, 100.0)) / 10)
    return "█" * filled + "░" * (10 - filled)


def erklaere(sensor, inhalt):
    """Erklärtext aus ERKLAERUNGEN in detailfenster_inhalt.py (erster passender Eintrag)."""
    for typ, muster, text in getattr(inhalt, "ERKLAERUNGEN", []):
        if typ == sensor["type"]:
            match = re.fullmatch(muster, sensor["name"])
            if match:
                return text.format(*(g or "" for g in match.groups()))
    return getattr(inhalt, "TYP_ERKLAERUNGEN", {}).get(sensor["type"], "Messwert laut LibreHardwareMonitor.")


# ---------- Vom Inhalt zur Liste ----------
def sichtbare_zeilen(tree, parent=""):
    """Alle Zeilen einer Treeview in Anzeigereihenfolge – ohne die in zugeklappten Bereichen."""
    for key in tree.get_children(parent):
        yield key
        if tree.item(key, "open"):
            yield from sichtbare_zeilen(tree, key)


def vorfahren(tree, key):
    """Die übergeordneten Zeilen von key (für die Einrückung beim Kopieren)."""
    while key := tree.parent(key):
        yield key


def benoetigte_geraete(tab):
    """Welche Geräte der Mess-Thread für diesen Tab lesen muss (None = alle)."""
    if ist_hwdaten(tab):
        return set()                                     # nichts messen, nur die Icons laufen weiter
    if any(isinstance(g, AlleSensoren) for g in tab.gruppen):
        return None
    return {g.geraet for g in tab.gruppen}


def ist_hwdaten(tab):
    return any(isinstance(g, Hardwaredaten) for g in tab.gruppen)


def mit_prozent(tab):
    """True, wenn im Tab Zeilen mit zwei Werten stehen (Abschnitt mit eine_zeile) – Balken bekommen dann „97 %“."""
    return any(isinstance(w, Abschnitt) and w.eine_zeile for g in tab.gruppen for w in getattr(g, "werte", ()))


def hwdaten_zeilen(daten, uebersicht=False):
    """Wie zeilen(), nur für den Tab Hardwaredaten: Bereich -> Gerät -> Felder. Felder stehen als "Info"-Sensor drin.
    uebersicht=True: nur Bereich -> Modellnamen, gleiche Geräte zusammengefasst („2× …“)."""
    result = []
    for b, (bereich, geraete) in enumerate(daten):
        result.append((f"b{b}", "", bereich, None))
        if uebersicht:
            result += [(f"b{b}|{g}", f"b{b}", name, None) for g, name in enumerate(hardwaredaten.modellnamen(geraete))]
            continue
        for g, (name, felder) in enumerate(geraete):
            head = f"b{b}|{g}"
            result.append((head, f"b{b}", name, None))
            result += [(f"{head}|{i}", head, feld, {"type": "Info", "name": feld, "value": wert})
                       for i, (feld, wert) in enumerate(felder)]
    return result


def zeilen(tab, snap):
    """Was der Tab gerade zeigt, als Liste von (Schlüssel, Eltern-Schlüssel, Text, Sensor oder None).
    Überschriften haben keinen Sensor. Die Schlüssel bleiben gleich, solange sich nichts am Aufbau ändert."""
    result = []
    for nr, gruppe in enumerate(tab.gruppen):
        for hw in snap["hardware"]:
            head = f"{nr}|{hw['id']}"
            if isinstance(gruppe, AlleSensoren):
                result.append((head, "", hw["name"], None))
                for typ, label in TYPE_LABELS.items():          # nach Sensortyp sortiert
                    sensors = [s for s in hw["sensors"] if s["type"] == typ]
                    if sensors:
                        result.append((f"{head}|{typ}", head, label, None))
                        result += [(f"{head}|{typ}|{i}", f"{head}|{typ}", s["name"], s) for i, s in enumerate(sensors)]
                continue
            if hw["geraet"] != gruppe.geraet or not fnmatch.fnmatchcase(hw["name"].lower(), gruppe.name.lower()):
                continue
            rows = []
            for i, wert in enumerate(gruppe.werte):
                if isinstance(wert, Abschnitt):                  # Unterpunkt mit eigenen Zeilen darunter
                    unter = wert.zeilen(hw["sensors"])
                    if unter:
                        key = f"{head}|{wert.titel}"
                        rows.append((key, head, wert.titel, None))
                        rows += [(f"{key}|{j}", key, text, s) for j, (text, s) in enumerate(unter)]
                else:
                    rows += [(f"{head}|{i}|{j}", head, wert.text or s["name"], s)
                             for j, s in enumerate(s for s in hw["sensors"] if wert.passt(s))]
            if rows:
                result.append((head, "", gruppe.titel or hw["name"], None))
                result += rows
    return result


# ---------- Windows-Helfer ----------
def arbeitsbereich(x, y):
    """Bildschirmbereich ohne Taskleiste (links, oben, rechts, unten) des Bildschirms am Punkt x, y – oder None."""
    class MONITORINFO(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_ulong), ("rcMonitor", ctypes.c_long * 4),
                    ("rcWork", ctypes.c_long * 4), ("dwFlags", ctypes.c_ulong)]

    user32 = ctypes.windll.user32
    user32.MonitorFromPoint.restype = ctypes.c_void_p
    user32.MonitorFromPoint.argtypes = [wintypes.POINT, ctypes.c_ulong]
    monitor = user32.MonitorFromPoint(wintypes.POINT(x, y), 0)         # 0 = None, wenn dort kein Bildschirm ist
    if not monitor:
        return None
    info = MONITORINFO(cbSize=ctypes.sizeof(MONITORINFO))
    user32.GetMonitorInfoW.argtypes = [ctypes.c_void_p, ctypes.POINTER(MONITORINFO)]
    return tuple(info.rcWork) if user32.GetMonitorInfoW(monitor, ctypes.byref(info)) else None


def dunkle_titelleiste(window):
    """Windows-Titelleiste im dunklen Design (passend zum Fensterinhalt)."""
    hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
    on = ctypes.c_int(1)
    ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(on), ctypes.sizeof(on))  # IMMERSIVE_DARK_MODE


# ---------- Das Fenster ----------
# dieselben Farben wie die dunkle Toolbox (toolbox/base.py) – das Fenster nutzt ttk statt CustomTkinter
BG, BG_LIST, FG, SUB, HOVER, AKZENT = "#0a1d2c", "#152736", "#e2e8f0", "#8fa3b8", "#213443", "#3ddc97"
MARKIERT = "#1d4f47"             # markierte Zeilen (wie gewählte Einträge in der Toolbox)
SCHRIFT, SCHRIFT_GRUPPE = ("Segoe UI", 9), ("Segoe UI Semibold", 10)       # Zeilen bzw. Gerätenamen
GROESSE = (560, 640)             # Startgröße bei 100 % Skalierung
TITELLEISTE = 32                 # Höhe der Windows-Titelleiste (zählt bei der Fenstergröße nicht mit)
HINWEIS = ("Klick auf einen Wert oder Gerätenamen kopiert ihn. Mehrere Zeilen: markieren (ziehen, Strg- oder "
           "Umschalt+Klick, Strg+A) und mit Strg+C kopieren. Maus über einen Wert erklärt ihn.")


class Detailfenster:
    """Ein normales Fenster: verschieb- und vergrößerbar, ✕ blendet es nur aus. Position und Größe werden gespeichert.

    app (HardwareMonitorApp) liefert: settings, kinds (die angezeigten Icons), current, vorhanden, snapshot() und
    fenster_braucht(geraete) – sagt dem Mess-Thread, welche Geräte gerade gebraucht werden (False = Fenster zu).
    """

    def __init__(self, root, app):
        self.app = app
        self.scale = root.winfo_fpixels("1i") / 96      # 1.0 bei 100 %, 1.5 bei 150 %
        self.inhalt = None                               # das Modul detailfenster_inhalt
        self.inhalt_stand = None                         # Änderungszeit der Datei beim letzten Laden
        self.fehler = None                               # Fehlermeldung, falls die Datei nicht geladen werden konnte
        self.tabs = []                                   # [(Tab, Treeview)]
        self.ausgeblendet_fuer = None                    # vorhandene Geräte, nach denen Tabs zuletzt ausgeblendet wurden
        self.signatur = {}                               # je Treeview: Aufbau beim letzten Zeichnen
        self.zugeklappt = {}                             # je Treeview: Schlüssel der zugeklappten Bereiche
        self.sensoren = {}                               # Zeilen-Schlüssel -> Sensor (für die Erklärung)
        self.kopierbar = {}                              # Zeilen-Schlüssel -> (Spalte, Text), den ein Klick kopiert
        self.druck = None                                # gedrückte Maustaste in der Liste: Klick oder Ziehen?
        self.schriften = {}                              # zum Ausmessen der Texte (ueber_wert)
        self.knoepfe = {}                                # je Treeview: Bereichszeile -> „Kopieren“-Button darüber
        self.meldung_job = None                          # „… kopiert“ steht gerade in der Fußzeile
        self.hwdaten = None                              # zuletzt gelesene Hardwaredaten (hardwaredaten.lesen())
        self.hwdaten_aktuell = False                     # False = beim nächsten Anzeigen neu lesen
        self.hwdaten_thread = None
        self.hwdaten_neu = None                          # Ergebnis des Lese-Threads, bis hwdaten_warten() es übernimmt

        win = self.win = tk.Toplevel(root)
        self.hw_ansicht = tk.StringVar(win, "uebersicht")    # Unterreiter im Tab Hardwaredaten: uebersicht / details
        win.withdraw()
        win.title(str(PROGRAMM_DATEI))                   # Pfad wie beim Explorer – siehe PROGRAMM_DATEI
        win.configure(bg=BG)
        win.minsize(self.px(320), self.px(240))
        try:
            win.iconbitmap(str(ICON_DATEI))
        except tk.TclError:
            pass
        self.stil(win)

        # Kopfzeile: die beiden Icon-Werte groß
        kopf = ttk.Frame(win)
        kopf.pack(fill="x", padx=self.px(14), pady=(self.px(10), self.px(4)))
        self.kopf = {}
        for kind in app.kinds:                           # wie die Taskleisten-Icons – ohne GPU-Temperatur nur CPU
            ttk.Label(kopf, text=kind.upper(), style="KopfName.TLabel").pack(side="left", padx=(0, self.px(6)))
            self.kopf[kind] = ttk.Label(kopf, text="–", style="KopfWert.TLabel")
            self.kopf[kind].pack(side="left", padx=(0, self.px(24)))

        # rechts daneben: „Daten werden geladen …“, bis die erste passende Messung da ist, danach „● Live“
        self.status = ttk.Label(kopf, style="KopfName.TLabel")
        self.status.pack(side="right")
        self.live = None                                 # True = „● Live“ steht schon da (bleibt bis zum Schließen)
        self.status_setzen(False)

        self.notebook = ttk.Notebook(win)
        self.notebook.pack(fill="both", expand=True, padx=self.px(8))
        self.notebook.bind("<<NotebookTabChanged>>", lambda e: (self.melden(), self.aktualisieren()))

        self.fuss = ttk.Label(win, text=HINWEIS, style="Fuss.TLabel", justify="left")
        self.fuss.pack(fill="x", padx=self.px(14), pady=self.px(8))
        self.fuss.bind("<Configure>", lambda e: self.fuss.configure(wraplength=e.width))

        win.protocol("WM_DELETE_WINDOW", self.verstecken)          # ✕ blendet nur aus
        for taste in ("<Control-c>", "<Control-C>"):
            win.bind(taste, lambda e: self.auswahl_kopieren())
        for taste in ("<Control-a>", "<Control-A>"):
            win.bind(taste, lambda e: self.alles_markieren())
        win.bind("<Escape>", lambda e: self.tabs and self.aktiver_tab()[1].selection_set(()))
        for event in ("<Map>", "<Unmap>"):                           # minimiert = nichts messen
            win.bind(event, lambda e: e.widget is win and self.sichtbarkeit())
        win.update_idletasks()
        dunkle_titelleiste(win)

    def px(self, value):
        return int(value * self.scale)

    def stil(self, win):
        style = ttk.Style(win)
        style.theme_use("clam")                          # das einzige eingebaute Design, das sich dunkel färben lässt
        style.configure(".", background=BG, foreground=FG, bordercolor=BG, lightcolor=BG, darkcolor=BG,
                        troughcolor=BG_LIST, focuscolor=BG, font=SCHRIFT)
        style.configure("KopfName.TLabel", foreground=SUB, font=("Segoe UI", 11))
        style.configure("KopfWert.TLabel", font=("Segoe UI Semibold", 18))
        style.configure("Fuss.TLabel", foreground=SUB)
        style.configure("TNotebook", borderwidth=0, tabmargins=(0, 0, 0, 0))
        style.configure("TNotebook.Tab", background=BG, foreground=SUB, borderwidth=0,
                        padding=(self.px(8), self.px(4)))
        style.map("TNotebook.Tab", background=[("selected", BG_LIST), ("active", HOVER)],
                  foreground=[("selected", AKZENT), ("active", FG)],
                  expand=[("selected", (0, 0, 0, 0))])  # gewählten Tab nicht vergrößern (sonst wird es eng)
        style.configure("Treeview", background=BG_LIST, fieldbackground=BG_LIST, foreground=FG, borderwidth=0,
                        rowheight=self.px(22))
        style.map("Treeview", background=[("selected", MARKIERT)], foreground=[("selected", FG)],
                  bordercolor=[("focus", BG)])           # kein heller Rahmen, wenn die Liste den Fokus hat
        style.configure("Knopf.TButton", background=HOVER, foreground=AKZENT, bordercolor=HOVER, lightcolor=HOVER,
                        darkcolor=HOVER, focuscolor=HOVER, borderwidth=0, padding=(self.px(8), self.px(2)), width=0)
        style.map("Knopf.TButton", background=[("pressed", FG), ("active", AKZENT)],
                  foreground=[("active", BG)], lightcolor=[("active", AKZENT)], darkcolor=[("active", AKZENT)],
                  bordercolor=[("active", AKZENT)])
        # Unterreiter im Tab Hardwaredaten: Radiobuttons ohne Punkt, gefärbt wie die Tabs darüber
        style.configure("Unterreiter.Toolbutton", background=BG, foreground=SUB, bordercolor=BG, lightcolor=BG,
                        darkcolor=BG, borderwidth=0, padding=(self.px(8), self.px(2)))
        style.map("Unterreiter.Toolbutton", background=[("selected", BG_LIST), ("active", HOVER)],
                  foreground=[("selected", AKZENT), ("active", FG)], lightcolor=[("selected", BG_LIST)],
                  darkcolor=[("selected", BG_LIST)], bordercolor=[("selected", BG_LIST)])
        style.configure("Vertical.TScrollbar", background=HOVER, troughcolor=BG_LIST, bordercolor=BG_LIST,
                        arrowcolor=SUB, lightcolor=HOVER, darkcolor=HOVER, gripcount=0)

    # --- Inhalt laden ---
    def inhalt_laden(self):
        """Liest detailfenster_inhalt.py (neu), falls sie sich seit dem letzten Mal geändert hat."""
        try:
            stand = INHALT_DATEI.stat().st_mtime
        except OSError:
            stand = None
        if self.inhalt is not None and stand == self.inhalt_stand:
            return
        try:
            if self.inhalt is None:
                import detailfenster_inhalt as modul
            else:
                modul = importlib.reload(self.inhalt)
            tabs = list(modul.FENSTER)
        except Exception as fehler:                      # Tippfehler in der Datei -> Fenster läuft trotzdem
            logging.exception("detailfenster_inhalt.py konnte nicht geladen werden")
            self.inhalt_stand = stand
            if not self.tabs:
                self.tabs_bauen([Tab("Alles", AlleSensoren())])
            self.fehler = f"⚠  Fehler in detailfenster_inhalt.py (Details im Log): {fehler}"
            self.fuss.configure(text=self.fehler, foreground=hex_color(AMPEL["rot"]))
            return
        self.inhalt, self.inhalt_stand, self.fehler = modul, stand, None
        self.fuss.configure(text=HINWEIS, foreground=SUB)
        self.tabs_bauen(tabs)

    def tabs_bauen(self, tabs):
        gewaehlt = self.aktiver_tab()[0].titel if self.tabs else None
        for tab_frame in self.notebook.tabs():
            self.notebook.forget(tab_frame)
        for _, tree in self.tabs:
            tree.master.destroy()
        self.tabs, self.signatur, self.zugeklappt = [], {}, {}
        self.ausgeblendet_fuer = None                    # neue Tabs sind alle sichtbar

        self.knoepfe = {}
        for tab in tabs:
            frame = ttk.Frame(self.notebook)
            if ist_hwdaten(tab):                         # oben: Unterreiter Übersicht / Details und „Alles kopieren“
                leiste = ttk.Frame(frame)
                leiste.pack(side="top", fill="x", pady=(self.px(6), self.px(4)))
                for text, wert, hilfe in (
                        ("Übersicht", "uebersicht", "Nur die Modellnamen aller Komponenten, nach Bereichen sortiert."),
                        ("Details", "details", "Alle Hardwaredaten: Hersteller, Modell, IDs, Seriennummern, Treiber.")):
                    reiter = ttk.Radiobutton(leiste, text=text, value=wert, variable=self.hw_ansicht,
                                             style="Unterreiter.Toolbutton", cursor="hand2",
                                             command=self.aktualisieren)
                    reiter.pack(side="left")
                    reiter.bind("<Enter>", lambda e, h=hilfe: self.fusszeile(h))
                    reiter.bind("<Leave>", lambda e: self.fusszeile(HINWEIS))
                knopf = ttk.Button(leiste, text="⧉  Alles kopieren", style="Knopf.TButton", cursor="hand2",
                                   command=self.alles_kopieren)
                knopf.pack(side="right")
                knopf.bind("<Enter>", lambda e: self.fusszeile(
                    "Kopiert alle Modellnamen als Text." if self.uebersicht() else
                    "Kopiert alle Hardwaredaten als Text (mit Computername und Datum)."))
                knopf.bind("<Leave>", lambda e: self.fusszeile(HINWEIS))
            tree = ttk.Treeview(frame, columns=("wert", "balken"), show="tree", selectmode="extended")
            if ist_hwdaten(tab):                         # Feldname links, langer Wert (IDs) daneben
                tree.column("#0", width=self.px(300), stretch=True)     # breit genug für lange Gerätenamen
                tree.column("wert", width=self.px(260), stretch=True, anchor="w")
                tree.column("balken", width=0, minwidth=0, stretch=False)
            else:
                tree.column("#0", width=self.px(250), stretch=True)
                tree.column("wert", width=self.px(100), stretch=False, anchor="e")
                if mit_prozent(tab):                     # Balken mit „97 %“ dahinter: breiter, alle Balken links
                    tree.column("balken", width=self.px(140), stretch=False, anchor="w")
                else:
                    tree.column("balken", width=self.px(100), stretch=False, anchor="center")
            tree.tag_configure("bereich", foreground=SUB, font=("Segoe UI Semibold", 9))
            tree.tag_configure("gruppe", font=SCHRIFT_GRUPPE)
            tree.tag_configure("typ", foreground=SUB, font=("Segoe UI", 8))
            tree.tag_configure("hinweis", foreground=SUB)
            for stufe, rgb in AMPEL.items():             # Temperaturzeilen in Ampelfarbe
                tree.tag_configure(stufe, foreground=hex_color(rgb))
            scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
            # die „Kopieren“-Buttons liegen über der Liste und wandern beim Scrollen, Auf-/Zuklappen und Vergrößern mit
            tree.configure(yscrollcommand=lambda *a, s=scroll, t=tree: (s.set(*a), self.knoepfe_platzieren(t)))
            for event in ("<Configure>", "<<TreeviewOpen>>", "<<TreeviewClose>>"):
                tree.bind(event, lambda e, t=tree: self.win.after_idle(self.knoepfe_platzieren, t))
            scroll.pack(side="right", fill="y")
            tree.pack(side="left", fill="both", expand=True)
            tree.bind("<Motion>", lambda e, t=tree: self.erklaeren(t, e))
            tree.bind("<Leave>", lambda e, t=tree: self.erklaeren(t, None))
            # Markieren per Klick, Strg+Klick und Umschalt+Klick macht ttk selbst – dazu kommen Ziehen und Kopieren
            tree.bind("<ButtonPress-1>", lambda e, t=tree: self.druecken(t, e))
            tree.bind("<B1-Motion>", lambda e, t=tree: self.ziehen(t, e))
            tree.bind("<ButtonRelease-1>", lambda e, t=tree: self.loslassen(t, e))
            tree.bind("<Button-3>", lambda e, t=tree: self.kontextmenue(t, e))
            self.notebook.add(frame, text=tab.titel)
            self.tabs.append((tab, tree))

        titel = [tab.titel for tab, _ in self.tabs]
        if gewaehlt in titel:
            self.notebook.select(titel.index(gewaehlt))

    def aktiver_tab(self):
        return self.tabs[self.notebook.index("current")]     # zählt ausgeblendete Tabs mit, passt also zu self.tabs

    def tabs_ausblenden(self):
        """Tabs für Geräte ausblenden, die es auf diesem PC nicht gibt (z. B. Mainboard-Sensoren am Laptop).
        Geht erst, wenn nach dem Start alle Hardware geladen ist – vorher sind alle Tabs zu sehen."""
        vorhanden = self.app.vorhanden
        if vorhanden is None or vorhanden == self.ausgeblendet_fuer:
            return
        self.ausgeblendet_fuer = vorhanden               # vor hide(): das löst einen Tabwechsel und damit uns erneut aus
        for tab, tree in self.tabs:
            geraete = benoetigte_geraete(tab)            # leer bei Hardwaredaten, None bei AlleSensoren -> bleiben
            if geraete and not geraete & vorhanden:
                self.notebook.hide(tree.master)

    # --- Zeigen / verstecken ---
    def sichtbar(self):
        return self.win.state() in ("normal", "zoomed")      # zoomed = maximiert

    def umschalten(self):
        self.verstecken() if self.sichtbar() else self.zeigen()

    def zeigen(self):
        self.inhalt_laden()
        if self.win.state() == "withdrawn":
            self.platzieren()
        self.win.deiconify()
        self.win.lift()
        self.win.focus_force()
        self.aktualisieren()

    def verstecken(self):
        self.speichern()
        self.win.withdraw()

    def platzieren(self):
        """Gespeicherte Position – oder beim ersten Mal unten rechts auf dem Bildschirm, wo geklickt wurde."""
        saved = self.app.settings.get("window", "")
        match = re.fullmatch(r"(\d+)x(\d+)\+(-?\d+)\+(-?\d+)", saved)
        if match:
            w, h, x, y = map(int, match.groups())
            if arbeitsbereich(x + w // 2, y + h // 2):   # liegt noch auf einem angeschlossenen Bildschirm?
                self.win.geometry(saved)
                return
        mx, my = self.win.winfo_pointerxy()
        left, top, right, bottom = (arbeitsbereich(mx, my)
                                    or (0, 0, self.win.winfo_screenwidth(), self.win.winfo_screenheight()))
        w, h = self.px(GROESSE[0]), min(self.px(GROESSE[1]), bottom - top - self.px(24 + TITELLEISTE))
        self.win.geometry(f"{w}x{h}+{right - w - self.px(12)}+{bottom - h - self.px(12 + TITELLEISTE)}")

    def speichern(self):
        """Position und Größe merken (in daten\\hardware_monitor.json)."""
        if self.sichtbar():
            self.app.fenster_geometrie(self.win.geometry())

    def sichtbarkeit(self):
        """Fenster geöffnet oder wiederhergestellt -> sofort messen lassen; versteckt oder minimiert -> nichts messen."""
        if not self.sichtbar():
            self.status_setzen(False, neu=True)          # beim nächsten Öffnen erst wieder „Daten werden geladen …“
            self.hwdaten_aktuell = False                 # beim nächsten Öffnen neu lesen (z. B. neue USB-Geräte)
        self.melden()

    def status_setzen(self, geladen, neu=False):
        """Oben rechts: „● Live“, sobald nach dem Öffnen die ersten Werte da sind, vorher „Daten werden geladen …“.
        Einmal „Live“, bleibt es dabei bis zum Schließen – auch wenn ein Tabwechsel kurz auf neue Werte wartet.
        neu=True setzt zurück (Fenster geschlossen oder minimiert)."""
        live = bool(geladen or (self.live and not neu))
        if live != self.live:
            self.live = live
            self.status.configure(text="●  Live" if live else "Daten werden geladen …",
                                  foreground=AKZENT if live else SUB)

    def melden(self):
        """Dem Mess-Thread sagen, was gebraucht wird: die Geräte des gewählten Tabs – oder nichts (Fenster zu)."""
        if self.sichtbar() and self.tabs:
            self.app.fenster_braucht(benoetigte_geraete(self.aktiver_tab()[0]))
        else:
            self.app.fenster_braucht(False)

    # --- Werte anzeigen ---
    def aktualisieren(self):
        """Neue Messwerte eintragen. Ändert sich der Aufbau (anderer Tab, neue Sensoren), wird die Liste neu gefüllt."""
        if not self.sichtbar() or not self.tabs:
            return
        self.tabs_ausblenden()
        snap = self.app.snapshot()
        for kind, label in self.kopf.items():
            value = self.app.current.get(kind)
            label.configure(text="–" if value is None else f"{value:.0f} °C",
                            foreground=hex_color(temp_color(value, self.app.settings, kind)))

        tab, tree = self.aktiver_tab()
        info = ist_hwdaten(tab)
        if info:
            self.hwdaten_laden()
            rows = hwdaten_zeilen(self.hwdaten or [], self.uebersicht())
            leer = ("Keine Hardwaredaten gefunden (Details in daten\\logs\\hardware_monitor.log)." if self.hwdaten == []
                    else "Lese Hardwaredaten …")
            geladen = self.hwdaten_aktuell
        else:
            gebraucht, gemessen = benoetigte_geraete(tab), snap.get("geraete")
            if gemessen is not None and (gebraucht is None or not gebraucht <= gemessen):
                rows = []                                # passende Messung kommt gleich
                leer = "Lade Sensordaten …"
                geladen = False
            else:
                rows = zeilen(tab, snap)
                leer = "Keine passenden Sensoren – die Namen zeigt „python hardware_monitor.py --list“."
                geladen = True
            if snap.get("loading"):                      # direkt nach dem Programmstart wird noch Hardware nachgeladen
                leer = "Lade Sensordaten …"
                geladen = False
        self.status_setzen(geladen)

        signatur = [(key, parent, text) for key, parent, text, _ in rows] or [leer]
        if signatur != self.signatur.get(tree):
            zu = self.zugeklappt.setdefault(tree, set())  # zugeklappte Bereiche bleiben zu (z. B. nach einem Tabwechsel)
            for key in sichtbare_zeilen(tree):
                if tree.get_children(key):
                    (zu.add if not tree.item(key, "open") else zu.discard)(key)
            tree.delete(*tree.get_children())
            for key, parent, text, sensor in rows:
                if sensor:
                    tag = ()
                elif not parent:                         # oberste Ebene: Gerät – bei Hardwaredaten der Bereich
                    tag = ("bereich",) if info else ("gruppe",)
                else:                                    # zweite Ebene: Sensortyp – bei Hardwaredaten das Gerät
                    tag = ("gruppe",) if info else ("typ",)
                tree.insert(parent, "end", iid=key, text=text, open=key not in zu, tags=tag)
            if not rows:
                tree.insert("", "end", iid="leer", text=leer, tags=("hinweis",))
            self.signatur[tree] = signatur
            if info:
                self.hw_spalten(tree)
                self.knoepfe_bauen(tree, [(key, text) for key, parent, text, _ in rows if not parent])

        self.sensoren, self.kopierbar = {}, {}
        geraet_von = {s["id"]: hw["geraet"] for hw in snap["hardware"] for s in hw["sensors"]}
        for key, _, text, sensor in rows:
            if sensor is None:
                if "gruppe" in tree.item(key, "tags"):  # Gerätename -> Klick darauf kopiert ihn
                    self.kopierbar[key] = ("#0", text)
                continue
            self.sensoren[key] = sensor
            if sensor["type"] == "Info":                 # Hardwaredaten: fester Wert, Klick darauf kopiert ihn
                self.kopierbar[key] = ("#1", sensor["value"])
                tree.item(key, values=(sensor["value"], ""))
                continue
            is_temp = (sensor["type"] == "Temperature"
                       and not any(fnmatch.fnmatchcase(sensor["name"], m) for m in OHNE_AMPEL))
            wert = fmt_value(sensor["type"], sensor["value"])
            leiste = balken(sensor["value"]) if sensor["type"] in BAR_TYPES else ""
            # Grafikkarte nach den GPU-Grenzen, alles andere (CPU, Mainboard, Laufwerke …) nach den CPU-Grenzen
            kind = "gpu" if geraet_von.get(sensor["id"]) == "gpu" else "cpu"
            tags = (temp_stufe(sensor["value"], self.app.settings, kind),) if is_temp else ()
            neben = sensor.get("balken")                 # zweiter Wert in derselben Zeile, z. B. Lüfter-Ansteuerung
            if neben:
                leiste = f"{balken(neben['value'])}  {fmt_value(neben['type'], neben['value'])}"
                if sensor["type"] == "Fan" and sensor["value"] == 0:
                    wert, tags = "steht", ("grau",)      # angesteuert, dreht sich aber nicht (oder nichts angeschlossen)
            self.kopierbar[key] = ("#1", wert)           # Messwert, so wie er gerade dasteht
            tree.item(key, values=(wert, leiste), tags=tags)

    def erklaeren(self, tree, event):
        """Maus über der Liste (event None = verlassen): Hand-Cursor genau über kopierbaren Werten, in der Fußzeile
        die Erklärung der Zeile."""
        key = tree.identify_row(event.y) if event else None
        tree.configure(cursor="hand2" if key and self.ueber_wert(tree, key, event.x) else "")
        if self.fehler or self.meldung_job:
            return                                       # Fehlermeldung bzw. „… kopiert“ stehen lassen
        sensor = self.sensoren.get(key)
        if sensor and sensor["type"] == "Info":
            erklaerung = hardwaredaten.ERKLAERUNGEN.get(sensor["name"])
            text = (f"{sensor['name']}: {sensor['value']}\n"     # voller Wert, falls die Spalte zu schmal ist
                    f"{erklaerung + ' ' if erklaerung else ''}Klick auf den Wert kopiert ihn.")
        elif sensor:
            text = f"{sensor['name']}: {erklaere(sensor, self.inhalt)}"
            if sensor.get("balken"):
                text += f" Der Balken: {erklaere(sensor['balken'], self.inhalt)}"
            if sensor.get("balken") and sensor["type"] == "Fan" and sensor["value"] == 0:
                text += (" „steht“: Der Anschluss wird angesteuert, aber nichts dreht sich – meist ist dort kein "
                         "Lüfter angeschlossen, oder er stoppt gerade im Leerlauf.")
        elif key in self.kopierbar:
            text = f"Klick auf den Namen kopiert „{self.kopierbar[key][1]}“."
        else:
            text = HINWEIS
        self.fuss.configure(text=text, foreground=SUB)

    def fusszeile(self, text):
        """Hilfetext der Buttons (Maus drüber) – Fehlermeldung und „… kopiert“ haben Vorrang."""
        if not (self.fehler or self.meldung_job):
            self.fuss.configure(text=text, foreground=SUB)

    # --- Markieren und Kopieren ---
    # Ein Klick markiert die Zeile (das macht ttk, ebenso Strg+Klick und Umschalt+Klick). Liegt er genau auf einem
    # Wert oder Gerätenamen, wird der zusätzlich kopiert – auf der Beschriftung davor oder im Leeren dahinter nicht.
    # Mit gedrückter Maustaste über mehrere Zeilen ziehen markiert alle dazwischen; Strg+C kopiert die markierten.
    def druecken(self, tree, event):
        """Maustaste gedrückt: nur merken, wo – erst beim Loslassen steht fest, ob es ein Klick war oder Ziehen."""
        key = tree.identify_row(event.y)
        tree.focus_set()
        if not key:
            tree.selection_set(())                       # Klick ins Leere hebt die Markierung auf
        self.druck = {"key": key, "x": event.x, "gezogen": False,
                      "taste": bool(event.state & 0x0005),          # Umschalt oder Strg: nur markieren
                      "dreieck": tree.identify_element(event.x, event.y).endswith("indicator")}  # nur auf-/zuklappen

    def ziehen(self, tree, event):
        """Mit gedrückter Maustaste über mehrere Zeilen: alle dazwischen markieren. Am Rand wird mitgescrollt."""
        d = self.druck
        if not d or not d["key"] or d["taste"] or d["dreieck"]:
            return
        if event.y < 0:
            tree.yview_scroll(-1, "units")
            key = tree.identify_row(1)
        elif event.y >= tree.winfo_height():
            tree.yview_scroll(1, "units")
            key = tree.identify_row(tree.winfo_height() - 2)
        else:
            key = tree.identify_row(event.y)
        if not key or (key == d["key"] and not d["gezogen"]):
            return
        zeilen = list(sichtbare_zeilen(tree))
        if d["key"] not in zeilen or key not in zeilen:  # Liste wurde inzwischen neu aufgebaut
            return
        d["gezogen"] = True
        a, b = sorted((zeilen.index(d["key"]), zeilen.index(key)))
        tree.selection_set(zeilen[a:b + 1])

    def loslassen(self, tree, event):
        """Ein einfacher Klick (nicht gezogen, ohne Strg/Umschalt) genau auf einen Wert kopiert ihn."""
        d, self.druck = self.druck, None
        if not d or d["gezogen"] or d["taste"] or d["dreieck"] or tree.identify_row(event.y) != d["key"]:
            return
        text = self.ueber_wert(tree, d["key"], d["x"])
        if text:
            self.zwischenablage(text, f"„{text}“ kopiert")

    def ueber_wert(self, tree, key, x):
        """Der Text, den ein Klick an Stelle x in Zeile key kopiert – nur direkt auf dem Wert bzw. Gerätenamen, nicht
        auf der Beschriftung daneben (z. B. „Produkt-ID“) oder im Leeren dahinter. Sonst None."""
        spalte, text = self.kopierbar.get(key, (None, None))
        box = tree.bbox(key, spalte) if text and tree.identify_column(x) == spalte else ""
        if not box:
            return None
        links, oben, breite, hoehe = box
        schrift = SCHRIFT_GRUPPE if "gruppe" in tree.item(key, "tags") else SCHRIFT
        if schrift not in self.schriften:
            self.schriften[schrift] = tkfont.Font(self.win, font=schrift)
        laenge = self.schriften[schrift].measure(text)
        if spalte == "#0":                               # Name: beginnt hinter Einrückung und Dreieck
            start = links
            while start < links + breite and tree.identify_element(start, oben + hoehe // 2) != "text":
                start += 1
        elif str(tree.column(spalte, "anchor")) == "e":  # Messwerte stehen rechtsbündig (str: Tk liefert ein Tcl-Objekt)
            start = links + breite - self.px(5) - laenge
        else:
            start = links + self.px(5)                   # ttk lässt links etwa 5 px frei
        return text if start - self.px(4) <= x <= start + laenge + self.px(4) else None

    def zeile_als_text(self, tree, key):
        """Eine Zeile zum Kopieren: „Feld: Wert“ – Überschriften (Gerät, Bereich, Sensortyp) nur mit ihrem Namen."""
        spalte, wert = self.kopierbar.get(key, (None, None))
        name = tree.item(key, "text")
        neben = self.sensoren.get(key, {}).get("balken")
        if neben:                                        # z. B. „Fan #2: 2523 RPM, 97 %“
            wert = f"{wert}, {fmt_value(neben['type'], neben['value'])}"
        return f"{name}: {wert}" if spalte == "#1" else name

    def auswahl_kopieren(self):
        """Strg+C: die markierten Zeilen des Tabs als Text, eingerückt wie in der Liste."""
        if not self.tabs:
            return
        tree = self.aktiver_tab()[1]
        markiert = set(tree.selection())
        zeilen = [key for key in sichtbare_zeilen(tree) if key in markiert and key != "leer"]
        if not zeilen:
            self.bestaetigen("Nichts markiert – Zeilen anklicken oder mit gedrückter Maustaste darüberziehen.",
                             farbe=SUB)
            return
        tiefe = {key: len(list(vorfahren(tree, key))) for key in zeilen}
        oben = min(tiefe.values())
        text = "\n".join("  " * (tiefe[key] - oben) + self.zeile_als_text(tree, key) for key in zeilen)
        self.zwischenablage(text, "1 Zeile kopiert" if len(zeilen) == 1 else f"{len(zeilen)} Zeilen kopiert")

    def alles_markieren(self):
        """Strg+A: alle sichtbaren Zeilen des Tabs (zugeklappte bleiben außen vor)."""
        if self.tabs:
            tree = self.aktiver_tab()[1]
            tree.selection_set([key for key in sichtbare_zeilen(tree) if key != "leer"])
        return "break"

    def kontextmenue(self, tree, event):
        """Rechtsklick: Wert kopieren, markierte Zeilen kopieren, alles markieren. Eine nicht markierte Zeile wird
        vorher markiert (wie im Explorer)."""
        key = tree.identify_row(event.y)
        if key and key not in tree.selection():
            tree.selection_set(key)
        menue = tk.Menu(self.win, tearoff=False, bg=BG_LIST, fg=FG, activebackground=HOVER, activeforeground=FG,
                        disabledforeground=SUB, bd=0, font=SCHRIFT)
        spalte, wert = self.kopierbar.get(key, (None, None))
        menue.add_command(label="Wert kopieren" if spalte == "#1" else "Namen kopieren",
                          state="normal" if wert else "disabled",
                          command=lambda: self.zwischenablage(wert, f"„{wert}“ kopiert"))
        menue.add_command(label="Markierte Zeilen kopieren", accelerator="Strg+C", command=self.auswahl_kopieren)
        menue.add_separator()
        menue.add_command(label="Alles markieren", accelerator="Strg+A", command=self.alles_markieren)
        menue.tk_popup(event.x_root, event.y_root)

    def zwischenablage(self, text, meldung):
        self.win.clipboard_clear()
        self.win.clipboard_append(text)
        self.bestaetigen(meldung)

    def bestaetigen(self, meldung, farbe=AKZENT):
        """Kurze Meldung in der Fußzeile, nach 2 s (bzw. 4 s bei Fehlern) wieder der Hinweis."""
        if self.meldung_job:
            self.win.after_cancel(self.meldung_job)
        self.fuss.configure(text=("✓  " if farbe == AKZENT else "⚠  ") + meldung, foreground=farbe)
        self.meldung_job = self.win.after(2000 if farbe == AKZENT else 4000, self.meldung_ende)

    def knoepfe_bauen(self, tree, bereiche):
        """Ein echter „Kopieren“-Button rechts in jeder Bereichszeile (bereiche: [(Zeilen-Schlüssel, Bereich)])."""
        for knopf in self.knoepfe.pop(tree, {}).values():
            knopf.destroy()
        self.knoepfe[tree] = {}
        for key, bereich in bereiche:
            knopf = ttk.Button(tree, text="⧉  Kopieren", style="Knopf.TButton", cursor="hand2",
                               command=lambda b=bereich: self.bereich_kopieren(b))
            knopf.bind("<Enter>", lambda e, b=bereich: self.fusszeile(
                f"Kopiert {'die Modellnamen' if self.uebersicht() else 'alle Daten'} zu „{b}“ als Text."))
            knopf.bind("<Leave>", lambda e: self.fusszeile(HINWEIS))
            self.knoepfe[tree][key] = knopf
        self.win.after_idle(self.knoepfe_platzieren, tree)

    def knoepfe_platzieren(self, tree):
        """Buttons auf die Höhe ihrer Zeile setzen – oder ausblenden, wenn die Zeile gerade nicht zu sehen ist."""
        for key, knopf in self.knoepfe.get(tree, {}).items():
            box = tree.bbox(key) if tree.exists(key) else ""
            if box:
                _, y, _, h = box
                knopf.place(relx=1.0, x=-self.px(4), y=y + 1, height=h - 2, anchor="ne")
            else:
                knopf.place_forget()

    def uebersicht(self):
        """True, solange im Tab Hardwaredaten der Unterreiter „Übersicht“ (nur Modellnamen) gewählt ist."""
        return self.hw_ansicht.get() == "uebersicht"

    def hw_spalten(self, tree):
        """Übersicht: nur Namen, die bekommen die ganze Breite (sonst werden lange CPU-Namen abgeschnitten).
        Details: Feldname links, Wert daneben – Aufteilung wie in tabs_bauen (300 : 260)."""
        breite = max(tree.winfo_width(), self.px(560))
        if self.uebersicht():
            tree.column("wert", width=0, stretch=False)
            tree.column("#0", width=breite)
        else:
            tree.column("wert", width=breite * 260 // 560, stretch=True)
            tree.column("#0", width=breite - breite * 260 // 560)

    def bereich_kopieren(self, bereich):
        """„Kopieren“ in einer Bereichszeile: so, wie der Bereich gerade angezeigt wird."""
        geraete = dict(self.hwdaten or []).get(bereich)
        if not geraete:
            return
        if self.uebersicht():
            self.zwischenablage(hardwaredaten.modellnamen_als_text([(bereich, geraete)]),
                                f"Modellnamen zu „{bereich}“ kopiert")
        else:
            self.zwischenablage(hardwaredaten.als_text(bereich, geraete), f"Alle Daten zu „{bereich}“ kopiert")

    def alles_kopieren(self):
        """„Alles kopieren“ oben im Tab: alle Bereiche so, wie der gewählte Unterreiter sie zeigt."""
        if not self.hwdaten:
            self.bestaetigen("Die Hardwaredaten werden noch gelesen – gleich noch einmal versuchen.", farbe=SUB)
        elif self.uebersicht():
            self.zwischenablage(hardwaredaten.modellnamen_als_text(self.hwdaten), "Alle Modellnamen kopiert")
        else:
            self.zwischenablage(hardwaredaten.alles_als_text(self.hwdaten), "Alle Hardwaredaten kopiert")

    def meldung_ende(self):
        self.meldung_job = None
        if self.fehler:
            self.fuss.configure(text=self.fehler, foreground=hex_color(AMPEL["rot"]))
        else:
            self.fuss.configure(text=HINWEIS, foreground=SUB)

    # --- Hardwaredaten ---
    def hwdaten_laden(self):
        """Liest die Hardwaredaten im Hintergrund – beim ersten Anzeigen und nach jedem erneuten Öffnen des Fensters.
        Bis dahin bleiben die alten Daten stehen."""
        if self.hwdaten_aktuell or self.hwdaten_thread:
            return

        def lesen():
            try:
                self.hwdaten_neu = hardwaredaten.lesen()
            except Exception:
                logging.exception("Hardwaredaten konnten nicht gelesen werden")
                self.hwdaten_neu = self.hwdaten or []

        self.hwdaten_thread = threading.Thread(target=lesen, daemon=True)
        self.hwdaten_thread.start()
        self.win.after(100, self.hwdaten_warten)

    def hwdaten_warten(self):
        if self.hwdaten_thread.is_alive():
            self.win.after(100, self.hwdaten_warten)
            return
        self.hwdaten_thread = None
        self.hwdaten, self.hwdaten_aktuell = self.hwdaten_neu, True
        self.aktualisieren()
