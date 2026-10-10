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
from ctypes import wintypes
from pathlib import Path
from tkinter import ttk

import hardwaredaten

INHALT_DATEI = Path(__file__).with_name("detailfenster_inhalt.py")
ICON_DATEI = Path(__file__).resolve().parents[1] / "gui" / "toolbox.ico"


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


def num(value, decimals):
    return f"{value:.{decimals}f}".replace(".", ",")      # deutsches Komma


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
    decimals, unit = UNITS.get(sensor_type, (1, ""))
    return f"{num(value, decimals)} {unit}".strip()


AMPEL = {"grau": (143, 163, 184), "gruen": (61, 220, 151), "gelb": (245, 196, 81), "rot": (255, 100, 100)}


def temp_stufe(value, settings):
    """"gruen", "gelb" oder "rot" je nach den Grenzen aus den Einstellungen ("grau" ohne Wert)."""
    if value is None:
        return "grau"
    if value < settings["warn_temp"]:
        return "gruen"
    return "gelb" if value < settings["hot_temp"] else "rot"


def temp_color(value, settings):
    """Ampelfarbe (RGB) für eine Temperatur – dieselbe in Tray-Icons und Fenster."""
    return AMPEL[temp_stufe(value, settings)]


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
def benoetigte_geraete(tab):
    """Welche Geräte der Mess-Thread für diesen Tab lesen muss (None = alle)."""
    if ist_hwdaten(tab):
        return set()                                     # nichts messen, nur die Icons laufen weiter
    if any(isinstance(g, AlleSensoren) for g in tab.gruppen):
        return None
    return {g.geraet for g in tab.gruppen}


def ist_hwdaten(tab):
    return any(isinstance(g, Hardwaredaten) for g in tab.gruppen)


def hwdaten_zeilen(daten):
    """Wie zeilen(), nur für den Tab Hardwaredaten: Bereich -> Gerät -> Felder. Felder stehen als "Info"-Sensor drin."""
    result = []
    for b, (bereich, geraete) in enumerate(daten):
        result.append((f"b{b}", "", bereich, None))
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
            rows = [(wert.text or s["name"], s) for wert in gruppe.werte for s in hw["sensors"] if wert.passt(s)]
            if rows:
                result.append((head, "", gruppe.titel or hw["name"], None))
                result += [(f"{head}|{i}", head, text, s) for i, (text, s) in enumerate(rows)]
    return result


# ---------- Windows-Helfer ----------
def arbeitsbereich(x, y):
    """Bildschirmbereich ohne Taskleiste (links, oben, rechts, unten) des Bildschirms am Punkt x, y – oder None."""
    class MONITORINFO(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_ulong), ("rcMonitor", ctypes.c_long * 4),
                    ("rcWork", ctypes.c_long * 4), ("dwFlags", ctypes.c_ulong)]

    try:
        user32 = ctypes.windll.user32
        user32.MonitorFromPoint.restype = ctypes.c_void_p
        user32.MonitorFromPoint.argtypes = [wintypes.POINT, ctypes.c_ulong]
        monitor = user32.MonitorFromPoint(wintypes.POINT(x, y), 0)     # 0 = None, wenn dort kein Bildschirm ist
        if not monitor:
            return None
        info = MONITORINFO(cbSize=ctypes.sizeof(MONITORINFO))
        user32.GetMonitorInfoW.argtypes = [ctypes.c_void_p, ctypes.POINTER(MONITORINFO)]
        return tuple(info.rcWork) if user32.GetMonitorInfoW(monitor, ctypes.byref(info)) else None
    except (AttributeError, OSError):                    # außerhalb von Windows
        return None


def dunkle_titelleiste(window):
    """Windows-Titelleiste im dunklen Design (passend zum Fensterinhalt)."""
    try:
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        on = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(on), ctypes.sizeof(on))  # IMMERSIVE_DARK_MODE
    except (AttributeError, OSError):
        pass


# ---------- Das Fenster ----------
# dieselben Farben wie die dunkle Toolbox (src/gui/base.py)
BG, BG_LIST, FG, SUB, HOVER, AKZENT = "#0a1d2c", "#152736", "#e2e8f0", "#8fa3b8", "#213443", "#3ddc97"
GROESSE = (560, 640)             # Startgröße bei 100 % Skalierung
TITELLEISTE = 32                 # Höhe der Windows-Titelleiste (zählt bei der Fenstergröße nicht mit)
HINWEIS = "Maus über einen Wert halten, um ihn erklärt zu bekommen. Klick auf einen Gerätenamen kopiert ihn."


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
        self.sensoren = {}                               # Zeilen-Schlüssel -> Sensor (für die Erklärung)
        self.kopierbar = {}                              # Zeilen-Schlüssel -> Text, den ein Klick kopiert
        self.knoepfe = {}                                # je Treeview: Bereichszeile -> „Kopieren“-Button darüber
        self.meldung_job = None                          # „… kopiert“ steht gerade in der Fußzeile
        self.hwdaten = None                              # zuletzt gelesene Hardwaredaten (hardwaredaten.lesen())
        self.hwdaten_aktuell = False                     # False = beim nächsten Anzeigen neu lesen
        self.hwdaten_thread = None

        win = self.win = tk.Toplevel(root)
        win.withdraw()
        win.title("Hardware-Monitor")
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
                        troughcolor=BG_LIST, focuscolor=BG, font=("Segoe UI", 9))
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
        style.map("Treeview", background=[("selected", BG_LIST)], foreground=[("selected", FG)])
        style.configure("Knopf.TButton", background=HOVER, foreground=AKZENT, bordercolor=HOVER, lightcolor=HOVER,
                        darkcolor=HOVER, focuscolor=HOVER, borderwidth=0, padding=(self.px(8), self.px(2)), width=0)
        style.map("Knopf.TButton", background=[("pressed", FG), ("active", AKZENT)],
                  foreground=[("active", BG)], lightcolor=[("active", AKZENT)], darkcolor=[("active", AKZENT)],
                  bordercolor=[("active", AKZENT)])
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
        self.tabs, self.signatur = [], {}
        self.ausgeblendet_fuer = None                    # neue Tabs sind alle sichtbar

        self.knoepfe = {}
        for tab in tabs:
            frame = ttk.Frame(self.notebook)
            if ist_hwdaten(tab):                         # oben eine Leiste zum Kopieren von allem
                leiste = ttk.Frame(frame)
                leiste.pack(side="top", fill="x", pady=(self.px(6), self.px(4)))
                for text, als_text, meldung, hilfe in (
                        ("⧉  Modellnamen kopieren", hardwaredaten.modellnamen_als_text, "Modellnamen kopiert",
                         "Kopiert nur die Modellnamen aller Komponenten, nach Bereichen sortiert."),
                        ("⧉  Alles kopieren", hardwaredaten.alles_als_text, "Alle Hardwaredaten kopiert",
                         "Kopiert alle Hardwaredaten als Text.")):
                    knopf = ttk.Button(leiste, text=text, style="Knopf.TButton", cursor="hand2",
                                       command=lambda f=als_text, m=meldung: self.alles_kopieren(f, m))
                    knopf.pack(side="right", padx=(self.px(6), 0))
                    knopf.bind("<Enter>", lambda e, h=hilfe: self.fusszeile(h))
                    knopf.bind("<Leave>", lambda e: self.fusszeile(HINWEIS))
            tree = ttk.Treeview(frame, columns=("wert", "balken"), show="tree", selectmode="none")
            if ist_hwdaten(tab):                         # Feldname links, langer Wert (IDs) daneben
                tree.column("#0", width=self.px(300), stretch=True)     # breit genug für lange Gerätenamen
                tree.column("wert", width=self.px(260), stretch=True, anchor="w")
                tree.column("balken", width=0, minwidth=0, stretch=False)
            else:
                tree.column("#0", width=self.px(250), stretch=True)
                tree.column("wert", width=self.px(100), stretch=False, anchor="e")
                tree.column("balken", width=self.px(100), stretch=False, anchor="center")
            tree.tag_configure("bereich", foreground=SUB, font=("Segoe UI Semibold", 9))
            tree.tag_configure("gruppe", font=("Segoe UI Semibold", 10))
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
            tree.bind("<Motion>", lambda e, t=tree: self.erklaeren(t.identify_row(e.y)))
            tree.bind("<Leave>", lambda e: self.erklaeren(None))
            tree.bind("<Button-1>", lambda e, t=tree: self.kopieren(t, e))
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
        """Position und Größe merken (in hardware_monitor_settings.json)."""
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
                            foreground=hex_color(temp_color(value, self.app.settings)))

        tab, tree = self.aktiver_tab()
        info = ist_hwdaten(tab)
        if info:
            self.hwdaten_laden()
            rows = hwdaten_zeilen(self.hwdaten or [])
            leer = ("Keine Hardwaredaten gefunden (Details in hardware_monitor.log)." if self.hwdaten == []
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
            tree.delete(*tree.get_children())
            for key, parent, text, sensor in rows:
                if sensor:
                    tag = ()
                elif not parent:                         # oberste Ebene: Gerät – bei Hardwaredaten der Bereich
                    tag = ("bereich",) if info else ("gruppe",)
                else:                                    # zweite Ebene: Sensortyp – bei Hardwaredaten das Gerät
                    tag = ("gruppe",) if info else ("typ",)
                tree.insert(parent, "end", iid=key, text=text, open=True, tags=tag)
            if not rows:
                tree.insert("", "end", iid="leer", text=leer, tags=("hinweis",))
            self.signatur[tree] = signatur
            if info:
                self.knoepfe_bauen(tree, [(key, text) for key, parent, text, _ in rows if not parent])

        self.sensoren, self.kopierbar = {}, {}
        for key, _, text, sensor in rows:
            if sensor is None:
                if "gruppe" in tree.item(key, "tags"):  # Gerätename -> Klick kopiert ihn
                    self.kopierbar[key] = text
                continue
            self.sensoren[key] = sensor
            if sensor["type"] == "Info":                 # Hardwaredaten: fester Wert, Klick kopiert ihn
                self.kopierbar[key] = sensor["value"]
                tree.item(key, values=(sensor["value"], ""))
                continue
            is_temp = sensor["type"] == "Temperature"
            values = (fmt_value(sensor["type"], sensor["value"]),
                      balken(sensor["value"]) if sensor["type"] in BAR_TYPES else "")
            tree.item(key, values=values,
                      tags=(temp_stufe(sensor["value"], self.app.settings),) if is_temp else ())

    def erklaeren(self, key):
        self.aktiver_tab()[1].configure(cursor="hand2" if key in self.kopierbar else "")
        if self.fehler or self.meldung_job:
            return                                       # Fehlermeldung bzw. „… kopiert“ stehen lassen
        sensor = self.sensoren.get(key)
        if sensor and sensor["type"] == "Info":
            erklaerung = hardwaredaten.ERKLAERUNGEN.get(sensor["name"])
            text = (f"{sensor['name']}: {sensor['value']}\n"     # voller Wert, falls die Spalte zu schmal ist
                    f"{erklaerung + ' ' if erklaerung else ''}Klick kopiert den Wert.")
        elif sensor:
            text = f"{sensor['name']}: {erklaere(sensor, self.inhalt)}"
        elif key in self.kopierbar:
            text = f"Klick kopiert „{self.kopierbar[key]}“."
        else:
            text = HINWEIS
        self.fuss.configure(text=text, foreground=SUB)

    def fusszeile(self, text):
        """Hilfetext der Buttons (Maus drüber) – Fehlermeldung und „… kopiert“ haben Vorrang."""
        if not (self.fehler or self.meldung_job):
            self.fuss.configure(text=text, foreground=SUB)

    # --- Kopieren ---
    def kopieren(self, tree, event):
        """Klick auf einen Gerätenamen (oder bei Hardwaredaten auf einen Wert) kopiert ihn in die Zwischenablage."""
        if tree.identify_element(event.x, event.y).endswith("indicator"):
            return                                       # Klick aufs Dreieck klappt nur auf/zu
        text = self.kopierbar.get(tree.identify_row(event.y))
        if text:
            self.zwischenablage(text, f"„{text}“ kopiert")

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
            knopf.bind("<Enter>", lambda e, b=bereich: self.fusszeile(f"Kopiert alle Daten zu „{b}“ als Text."))
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

    def bereich_kopieren(self, bereich):
        geraete = dict(self.hwdaten or []).get(bereich)
        if geraete:
            self.zwischenablage(hardwaredaten.als_text(bereich, geraete), f"Alle Daten zu „{bereich}“ kopiert")

    def alles_kopieren(self, als_text, meldung):
        """Die Buttons oben im Tab: alle Bereiche auf einmal (als_text aus hardwaredaten.py)."""
        if self.hwdaten:
            self.zwischenablage(als_text(self.hwdaten), meldung)
        else:
            self.bestaetigen("Die Hardwaredaten werden noch gelesen – gleich noch einmal versuchen.", farbe=SUB)

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
