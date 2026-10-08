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
import tkinter as tk
from ctypes import wintypes
from pathlib import Path
from tkinter import ttk

INHALT_DATEI = Path(__file__).with_name("detailfenster_inhalt.py")
ICON_DATEI = Path(__file__).resolve().parents[1] / "gui" / "toolbox.ico"


# ---------- Bausteine für detailfenster_inhalt.py ----------
class Tab:
    """Ein Tab im Fenster: Titel und darin die Gruppen (oder AlleSensoren())."""

    def __init__(self, titel, *gruppen):
        self.titel, self.gruppen = titel, gruppen


class Gruppe:
    """Werte eines Geräts, mit dem Gerätenamen als Überschrift.

    geraet: "cpu", "gpu", "ram", "mainboard", "laufwerk", "netzwerk" oder "weitere"
            (steht bei `hardware_monitor.py --list` in eckigen Klammern).
            Gibt es mehrere passende Geräte (z. B. drei Laufwerke), erscheint die Gruppe für jedes einmal.
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
    """

    def __init__(self, sensor, typ=None, text=None):
        self.sensor, self.text = sensor, text
        self.typ = LABEL_TYPES.get(typ, typ)            # "Temperatur" -> "Temperature"

    def passt(self, s):
        return ((self.typ is None or s["type"] == self.typ)
                and fnmatch.fnmatchcase(s["name"].lower(), self.sensor.lower()))


class AlleSensoren:
    """Alles, was LibreHardwareMonitor findet – nach Gerät und Sensortyp sortiert. Gut zum Nachschlagen von Namen."""


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
    "Voltage": (3, "V"), "Current": (2, "A"), "Energy": (0, "mWh"), "Fan": (0, "RPM"),
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
    if sensor_type == "SmallData" and value >= 1024:     # z. B. Grafikspeicher lieber in GB
        return f"{num(value / 1024, 1)} GB"
    decimals, unit = UNITS.get(sensor_type, (1, ""))
    return f"{num(value, decimals)} {unit}".strip()


AMPEL = {"grau": (160, 160, 160), "gruen": (90, 210, 120), "gelb": (245, 190, 40), "rot": (235, 60, 60)}


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
    if any(isinstance(g, AlleSensoren) for g in tab.gruppen):
        return None
    return {g.geraet for g in tab.gruppen}


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
BG, BG_LIST, FG, SUB, HOVER = "#202020", "#2b2b2b", "#f0f0f0", "#9a9a9a", "#3a3a3a"
GROESSE = (560, 640)             # Startgröße bei 100 % Skalierung
TITELLEISTE = 32                 # Höhe der Windows-Titelleiste (zählt bei der Fenstergröße nicht mit)
HINWEIS = "Maus über einen Wert halten, um ihn erklärt zu bekommen."


class Detailfenster:
    """Ein normales Fenster: verschieb- und vergrößerbar, ✕ blendet es nur aus. Position und Größe werden gespeichert.

    app (HardwareMonitorApp) liefert: settings, order, current, snapshot() und
    fenster_braucht(geraete) – sagt dem Mess-Thread, welche Geräte gerade gebraucht werden (False = Fenster zu).
    """

    def __init__(self, root, app):
        self.app = app
        self.scale = root.winfo_fpixels("1i") / 96      # 1.0 bei 100 %, 1.5 bei 150 %
        self.inhalt = None                               # das Modul detailfenster_inhalt
        self.inhalt_stand = None                         # Änderungszeit der Datei beim letzten Laden
        self.fehler = None                               # Fehlermeldung, falls die Datei nicht geladen werden konnte
        self.tabs = []                                   # [(Tab, Treeview)]
        self.signatur = {}                               # je Treeview: Aufbau beim letzten Zeichnen
        self.sensoren = {}                               # Zeilen-Schlüssel -> Sensor (für die Erklärung)

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
        for kind in app.order:
            ttk.Label(kopf, text=kind.upper(), style="KopfName.TLabel").pack(side="left", padx=(0, self.px(6)))
            self.kopf[kind] = ttk.Label(kopf, text="–", style="KopfWert.TLabel")
            self.kopf[kind].pack(side="left", padx=(0, self.px(24)))

        self.notebook = ttk.Notebook(win)
        self.notebook.pack(fill="both", expand=True, padx=self.px(8))
        self.notebook.bind("<<NotebookTabChanged>>", lambda e: (self.melden(), self.aktualisieren()))

        self.fuss = ttk.Label(win, text=HINWEIS, style="Fuss.TLabel", justify="left")
        self.fuss.pack(fill="x", padx=self.px(14), pady=self.px(8))
        self.fuss.bind("<Configure>", lambda e: self.fuss.configure(wraplength=e.width))

        win.protocol("WM_DELETE_WINDOW", self.verstecken)          # ✕ blendet nur aus
        for event in ("<Map>", "<Unmap>"):                           # minimiert = nichts messen
            win.bind(event, lambda e: e.widget is win and self.melden())
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
                  foreground=[("selected", FG), ("active", FG)],
                  expand=[("selected", (0, 0, 0, 0))])  # gewählten Tab nicht vergrößern (sonst wird es eng)
        style.configure("Treeview", background=BG_LIST, fieldbackground=BG_LIST, foreground=FG, borderwidth=0,
                        rowheight=self.px(22))
        style.map("Treeview", background=[("selected", BG_LIST)], foreground=[("selected", FG)])
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

        for tab in tabs:
            frame = ttk.Frame(self.notebook)
            tree = ttk.Treeview(frame, columns=("wert", "balken"), show="tree", selectmode="none")
            tree.column("#0", width=self.px(250), stretch=True)
            tree.column("wert", width=self.px(100), stretch=False, anchor="e")
            tree.column("balken", width=self.px(100), stretch=False, anchor="center")
            tree.tag_configure("gruppe", font=("Segoe UI Semibold", 10))
            tree.tag_configure("typ", foreground=SUB, font=("Segoe UI", 8))
            tree.tag_configure("hinweis", foreground=SUB)
            for stufe, rgb in AMPEL.items():             # Temperaturzeilen in Ampelfarbe
                tree.tag_configure(stufe, foreground=hex_color(rgb))
            scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
            tree.configure(yscrollcommand=scroll.set)
            scroll.pack(side="right", fill="y")
            tree.pack(side="left", fill="both", expand=True)
            tree.bind("<Motion>", lambda e, t=tree: self.erklaeren(t.identify_row(e.y)))
            tree.bind("<Leave>", lambda e: self.erklaeren(None))
            self.notebook.add(frame, text=tab.titel)
            self.tabs.append((tab, tree))

        titel = [tab.titel for tab, _ in self.tabs]
        if gewaehlt in titel:
            self.notebook.select(titel.index(gewaehlt))

    def aktiver_tab(self):
        return self.tabs[self.notebook.index("current")]

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
        snap = self.app.snapshot()
        for kind, label in self.kopf.items():
            value = self.app.current.get(kind)
            label.configure(text="–" if value is None else f"{value:.0f} °C",
                            foreground=hex_color(temp_color(value, self.app.settings)))

        tab, tree = self.aktiver_tab()
        gebraucht, gemessen = benoetigte_geraete(tab), snap.get("geraete")
        if gemessen is not None and (gebraucht is None or not gebraucht <= gemessen):
            rows = []                                    # passende Messung kommt gleich
            leer = "Lade Sensordaten …"
        else:
            rows = zeilen(tab, snap)
            leer = "Keine passenden Sensoren – die Namen stehen im Tab mit AlleSensoren()."
        if snap.get("loading"):
            leer = "Lade Sensordaten …"

        signatur = [(key, parent, text) for key, parent, text, _ in rows] or [leer]
        if signatur != self.signatur.get(tree):
            tree.delete(*tree.get_children())
            for key, parent, text, sensor in rows:
                tag = () if sensor else ("gruppe",) if not parent else ("typ",)
                tree.insert(parent, "end", iid=key, text=text, open=True, tags=tag)
            if not rows:
                tree.insert("", "end", iid="leer", text=leer, tags=("hinweis",))
            self.signatur[tree] = signatur

        self.sensoren = {}
        for key, _, _, sensor in rows:
            if sensor is None:
                continue
            self.sensoren[key] = sensor
            is_temp = sensor["type"] == "Temperature"
            tree.item(key, values=(fmt_value(sensor["type"], sensor["value"]),
                                   balken(sensor["value"]) if sensor["type"] in BAR_TYPES else ""),
                      tags=(temp_stufe(sensor["value"], self.app.settings),) if is_temp else ())

    def erklaeren(self, key):
        if self.fehler:
            return                                       # Fehlermeldung zum Inhalt stehen lassen
        sensor = self.sensoren.get(key)
        self.fuss.configure(text=f"{sensor['name']}: {erklaere(sensor, self.inhalt)}" if sensor else HINWEIS)
