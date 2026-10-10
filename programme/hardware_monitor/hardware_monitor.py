"""
hardware_monitor.py – Hardware-Monitor im Infobereich der Taskleiste.
Zeigt CPU- und GPU-Temperatur als zwei Zahlen; ein Klick auf eines der Icons öffnet das Detailfenster.

Dateien:
  hardware_monitor.py         dieses Programm: Sensoren lesen, Tray-Icons, Fernsteuerung durch die Toolbox
  detailfenster_inhalt.py     WAS im Detailfenster steht (Tabs, Werte) – hier passt du das Fenster an
  detailfenster.py            baut das Fenster daraus (muss normalerweise nicht angefasst werden)

Voraussetzungen:
  - PawnIO installiert:            winget install namazso.PawnIO
  - LibreHardwareMonitor-Release (LibreHardwareMonitor.zip) entpackt nach lhm/ in diesem Ordner (macht Setup.exe)
  - Python-Pakete:                 pip install pythonnet pystray pillow
  - Start mit Adminrechten (sonst fehlen CPU- und Mainboard-Werte)

Aufruf:
  pythonw hardware_monitor.py          -> Tray-Icons (ohne Konsolenfenster)
  python  hardware_monitor.py --list   -> listet alle Sensoren auf (zum Anpassen der Namen)

Sparsam im Hintergrund: Solange das Fenster zu ist, werden nur CPU und GPU gelesen, die GPU-Temperatur
bei Nvidia-Karten direkt über nvml.dll statt über LHM (ein Bruchteil des Aufwands). Beim Start wird zuerst nur
CPU und GPU geöffnet, damit die Icons sofort da sind; die übrige Hardware lädt danach im Hintergrund nach.
Die Aktualisierungsraten lassen sich per Rechtsklick aufs Icon einstellen; alle weiteren
Einstellungen über die Toolbox-GUI. Gespeichert wird in daten/hardware_monitor.json.
Die GUI steuert das Programm über eine lokale Verbindung (127.0.0.1, Port IPC_PORT).

Fehler landen in daten/logs/hardware_monitor.log (pythonw hat keine Konsole).
"""

import ctypes
import json
import logging
import os
import queue
import re
import socket
import sys
import threading
import time
from pathlib import Path

sys.dont_write_bytecode = True                              # keine __pycache__-Ordner anlegen (wie bei der Toolbox)
sys.path.insert(0, str(Path(__file__).resolve().parent))    # detailfenster finden – auch beim Start mit python -m
sys.path.append(str(Path(__file__).resolve().parents[2] / "toolbox"))   # daten.py (gemeinsam mit der Toolbox)
import daten  # noqa: E402
from detailfenster import TYPE_LABELS, Detailfenster, fmt_value, temp_color  # noqa: E402


# ---------- Einstellungen ----------
# Ordner mit LibreHardwareMonitorLib.dll: lhm\ neben diesem Skript (legt Setup.exe an, siehe "downloads" in
# programm.json), sonst runtime\lhm (dort lag es kurzzeitig), sonst C:\Tools\lhm
SCRIPT_DIR = Path(__file__).resolve().parent
LHM_CANDIDATES = [SCRIPT_DIR / "lhm", SCRIPT_DIR.parents[1] / "runtime" / "lhm", Path(r"C:\Tools\lhm")]
LHM_DIR = next((str(d) for d in LHM_CANDIDATES if (d / "LibreHardwareMonitorLib.dll").exists()),
               str(LHM_CANDIDATES[0]))

# Auswahl im Rechtsklick-Menü (Sekunden)
ICON_RATES = (1, 2, 5, 10)      # Taskleisten-Icons (liest nur CPU und GPU)
POPUP_RATES = (0.5, 1, 2, 5)    # geöffnetes Fenster (liest die Geräte des gewählten Tabs)

# Startwerte. Geändert wird über das Rechtsklick-Menü oder die Toolbox-GUI;
# beides landet in daten/hardware_monitor.json.
DEFAULT_SETTINGS = {
    "icon_interval": 2,
    "popup_interval": 1,
    "icon_order": ["cpu", "gpu"],    # Reihenfolge in der Taskleiste (wirkt nach Neustart des Programms)
    "cpu_sensor": "auto",            # "auto" = erster vorhandener aus CPU_SENSORS, sonst ein Sensorname
    "gpu_sensor": "auto",
    "warn_temp": 60,                 # ab hier gelb
    "hot_temp": 80,                  # ab hier rot
    "window": "",                    # Größe und Position des Detailfensters, z. B. "480x640+1420+380" (merkt es sich selbst)
    "effizienzmodus": "auto",        # "auto" = nur bei geschlossenem Fenster, "an" = immer, "aus" = nie
}
EFFIZIENZ = ("auto", "an", "aus")
SETTINGS_FILE = daten.einstellungen("hardware_monitor")

# Bei "auto": welcher Sensor im Tray-Icon angezeigt wird – der erste aus der Liste, den es gibt
CPU_SENSORS = ("Core (Tctl/Tdie)", "CPU Package", "Core Average")
GPU_SENSORS = ("GPU Core", "GPU Hot Spot")

# Lokale Fernsteuerung für die Toolbox-GUI (nur von diesem PC aus erreichbar)
IPC_PORT = 47815

# Welche Hardware ausgelesen wird. Was du nicht brauchst, einfach rausnehmen.
# Beim Start nur CPU und GPU – das reicht für die Icons und dauert nur Sekundenbruchteile.
FAST_HARDWARE = ("IsCpuEnabled", "IsGpuEnabled")
# Der Rest wird danach im Hintergrund nachgeladen: allein der RAM braucht beim Öffnen ~8 s
# (LHM liest die Daten der Speicherriegel über den SMBus).
LATER_HARDWARE = (
    "IsMemoryEnabled", "IsMotherboardEnabled", "IsControllerEnabled", "IsStorageEnabled",
    "IsNetworkEnabled", "IsPsuEnabled", "IsBatteryEnabled", "IsPowerMonitorEnabled",
)

logging.basicConfig(
    filename=daten.log("hardware_monitor"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

# ---------- LibreHardwareMonitor laden ----------
sys.path.append(LHM_DIR)
import clr  # pythonnet  # noqa: E402
clr.AddReference("LibreHardwareMonitorLib")
from LibreHardwareMonitor.Hardware import Computer, HardwareType, SensorType  # noqa: E402


def enable_hardware(props):
    """Schaltet Hardware-Gruppen ein. Nach pc.Open() fügt LHM die Geräte dabei sofort hinzu.

    Bewusst über SetValue statt `pc.IsMemoryEnabled = True`: pythonnet gibt die Python-Sperre (GIL) nur bei
    .NET-Methodenaufrufen frei, nicht bei Zuweisungen. Sonst stünden während der ~8 s fürs RAM alle anderen
    Threads still – Klicks aufs Icon, das Fenster und die Statusabfrage der Toolbox.
    """
    for prop in props:
        info = pc.GetType().GetProperty(prop)
        if info is None:                 # ältere LHM-Versionen kennen nicht alle Schalter
            logging.warning("Hardware-Gruppe %s gibt es in dieser LHM-Version nicht", prop)
            continue
        try:
            info.SetValue(pc, True)
        except Exception:
            logging.exception("Hardware-Gruppe %s konnte nicht eingeschaltet werden", prop)


pc = Computer()
enable_hardware(FAST_HARDWARE)
pc.Open()


# ---------- GPU-Temperatur direkt vom Nvidia-Treiber ----------
class NvidiaTemp:
    """Liest die GPU-Temperatur über nvml.dll (gehört zum Nvidia-Treiber, liegt in System32).

    Für die Icons viel sparsamer als LHM: LHM aktualisiert bei jedem Update alle GPU-Werte (~90 ms),
    NVML liefert nur die eine Temperatur (Bruchteil einer Millisekunde). Es ist derselbe Wert wie „GPU Core“.
    Ohne Nvidia-Karte ist available False und alles läuft wie bisher über LHM.
    """
    NVML_TEMPERATURE_GPU = 0

    def __init__(self):
        self.available = False
        try:
            self.dll = ctypes.WinDLL("nvml.dll")
            self.handle = ctypes.c_void_p()
            if (self.dll.nvmlInit_v2() == 0                              # 0 = NVML_SUCCESS
                    and self.dll.nvmlDeviceGetHandleByIndex_v2(0, ctypes.byref(self.handle)) == 0):
                self.available = True                                    # erste Nvidia-Karte
        except (OSError, AttributeError):                                # keine nvml.dll -> keine Nvidia-Karte
            pass

    def read(self):
        temp = ctypes.c_uint()
        if self.dll.nvmlDeviceGetTemperature(self.handle, self.NVML_TEMPERATURE_GPU, ctypes.byref(temp)) != 0:
            return None
        return float(temp.value)

    def close(self):
        if self.available:
            self.dll.nvmlShutdown()


nvidia = NvidiaTemp()


def enum_table(enum, names):
    """Übersetzt .NET-Enum-Werte in ihre Namen als Text (nur die, die es in dieser LHM-Version gibt)."""
    return [(getattr(enum, n), n) for n in names if hasattr(enum, n)]


def enum_name(value, table):
    for enum_value, name in table:
        if value == enum_value:
            return name
    return str(value)


HW_TYPES = enum_table(HardwareType, (
    "Motherboard", "SuperIO", "Cpu", "Memory", "GpuNvidia", "GpuAmd", "GpuIntel", "Storage",
    "Network", "Cooler", "EmbeddedController", "Psu", "Battery", "PowerMonitor"))

SENSOR_TYPES = enum_table(SensorType, tuple(TYPE_LABELS))

# Hardwaretyp von LHM -> Gerät, wie es in detailfenster_inhalt.py bei Gruppe(...) heißt (alles andere: "weitere")
HW_GERAET = {
    "Cpu": "cpu", "GpuNvidia": "gpu", "GpuAmd": "gpu", "GpuIntel": "gpu", "Memory": "ram",
    "Motherboard": "mainboard", "SuperIO": "mainboard", "EmbeddedController": "mainboard",
    "Storage": "laufwerk", "Network": "netzwerk", "Battery": "akku",
}


def walk(hw, depth=0):
    """Liefert ein Gerät und alle Unter-Geräte (z. B. den Sensorchip auf dem Mainboard), jeweils aktualisiert."""
    hw.Update()
    yield hw, depth
    for sub in hw.SubHardware:
        yield from walk(sub, depth + 1)


def pick(hardware, kind, priority):
    """Wählt den Temperatursensor, der in `priority` am weitesten vorne steht."""
    for wanted in priority:
        for hw in hardware:
            if hw["kind"] != kind:
                continue
            for s in hw["sensors"]:
                if s["type"] == "Temperature" and s["name"] == wanted:
                    return {"hw": hw["id"], "sensor": s["id"], "value": s["value"]}
    return None


def collect(geraete=None, icons=("cpu", "gpu")):
    """Liest die Sensoren.

    geraete: welche Geräte gelesen werden, z. B. {"gpu", "laufwerk"} (Namen wie in HW_GERAET); None = alle.
             Die Geräte aus icons werden immer gelesen, ihre Temperatur steht im Icon. Nur für die Icons: collect(set()).
    icons:   welche Icons es gibt – ohne GPU-Icon (keine GPU-Temperatur) muss die GPU nicht mitgelesen werden.

    Ergebnis (ein "Snapshot"):
      hardware: [{"id", "geraet", "kind" ("cpu"/"gpu"/None), "name",
                  "sensors": [{"id", "type", "name", "value"}, ...]}, ...]
      cpu / gpu: der jeweils fürs Tray-Icon ausgewählte Temperatursensor (oder None)
      geraete:   welche Geräte tatsächlich gelesen wurden (None = alle)
    """
    # Wird die GPU nicht gebraucht, reicht fürs GPU-Icon NVML – wenn dort "GPU Core" steht (bei "auto" der Fall).
    # Andere Sensoren (Hot Spot, Memory Junction, …) kennt NVML nicht -> dann wie bisher über LHM.
    use_nvml = geraete is not None and "gpu" not in geraete and "gpu" in icons and nvml_fuer_gpu_icon()
    if geraete is not None:
        geraete = set(geraete) | (set(icons) - ({"gpu"} if use_nvml else set()))
    hardware = []
    for top in pc.Hardware:
        top_type = enum_name(top.HardwareType, HW_TYPES)
        geraet = HW_GERAET.get(top_type, "weitere")
        if geraete is not None and geraet not in geraete:
            continue                             # nicht gebrauchte Hardware gar nicht erst ansprechen
        kind = geraet if geraet in ("cpu", "gpu") else None
        try:
            for hw, depth in walk(top):
                sensors = [
                    {"id": str(s.Identifier), "type": enum_name(s.SensorType, SENSOR_TYPES),
                     "name": str(s.Name), "value": float(s.Value)}
                    for s in hw.Sensors if s.Value is not None
                ]
                if not sensors:
                    continue
                if top_type == "Network" and all(s["value"] == 0 for s in sensors):
                    continue                     # ungenutzte Netzwerkadapter (Bluetooth, VPN, …) weglassen
                hardware.append({
                    "id": str(hw.Identifier),
                    "geraet": geraet,
                    "kind": kind if depth == 0 else None,
                    "name": str(hw.Name) if depth == 0 else f"{top.Name} – {hw.Name}",
                    "sensors": sensors,
                })
        except Exception:
            logging.exception("Fehler beim Auslesen von %s", top.Name)

    if use_nvml:
        gpu = {"hw": None, "sensor": None, "value": nvidia.read()}
    else:
        gpu = pick(hardware, "gpu", sensor_priority("gpu_sensor", GPU_SENSORS))
    return {
        "hardware": hardware,
        "cpu": pick(hardware, "cpu", sensor_priority("cpu_sensor", CPU_SENSORS)),
        "gpu": gpu,
        "geraete": geraete,
    }


def sensor_priority(key, defaults):
    """Gewählter Sensor zuerst; falls es ihn nicht gibt, greift die automatische Reihenfolge."""
    chosen = SETTINGS.get(key, "auto")
    return defaults if chosen == "auto" else (chosen,) + defaults


# ---------- Nur die beiden Icon-Werte ----------
ICON_SENSOREN = {}       # "cpu"/"gpu" -> (Gerät, Sensor) als .NET-Objekte: einmal gesucht, danach direkt gelesen


def nvml_fuer_gpu_icon():
    """GPU-Icon über NVML statt LHM – geht nur für „GPU Core“ (bei "auto" der Fall), andere Sensoren kennt NVML nicht."""
    return nvidia.available and SETTINGS["gpu_sensor"] in ("auto", "GPU Core")


def icon_sensor_suchen(kind, priority):
    """Wie pick(), liefert aber die .NET-Objekte (Gerät, Sensor) statt eines Werts – oder None."""
    geraete = [hw for hw in pc.Hardware if HW_GERAET.get(enum_name(hw.HardwareType, HW_TYPES)) == kind]
    for hw in geraete:
        hw.Update()                              # manche Sensoren gibt es erst nach dem ersten Update
    for wanted in priority:
        for hw in geraete:
            for s in hw.Sensors:
                if s.SensorType == SensorType.Temperature and str(s.Name) == wanted and s.Value is not None:
                    return hw, s
    return None


def gpu_hat_temperatur():
    """Gibt es eine GPU-Temperatur? Intel-Onboard-Grafik (z. B. Iris Xe) meldet keine – dann bleibt das GPU-Icon weg,
    statt dauerhaft „--“ zu zeigen."""
    if nvidia.available:
        return True
    for hw in pc.Hardware:
        if HW_GERAET.get(enum_name(hw.HardwareType, HW_TYPES)) == "gpu":
            hw.Update()                          # manche Sensoren gibt es erst nach dem ersten Update
            if any(s.SensorType == SensorType.Temperature for s in hw.Sensors):
                return True
    return False


def icon_werte(kinds=("cpu", "gpu")):
    """Nur die Temperaturen für die Icons: {"cpu": Wert, "gpu": Wert} (None = keiner da).

    Je Gerät ein Update() und ein einziger gelesener Wert. collect() würde dafür jeden CPU-Sensor (Takt, Last,
    Leistung, Spannung je Kern – bei einem 6-Kerner rund 50) einzeln über pythonnet abfragen.
    kinds: welche Icons es gibt (ohne GPU-Icon wird die GPU gar nicht angesprochen).
    """
    werte = {}
    for kind, key, defaults in (("cpu", "cpu_sensor", CPU_SENSORS), ("gpu", "gpu_sensor", GPU_SENSORS)):
        if kind not in kinds:
            continue
        if kind == "gpu" and nvml_fuer_gpu_icon():
            werte[kind] = nvidia.read()
            continue
        treffer = ICON_SENSOREN.get(kind)
        if treffer:
            treffer[0].Update()
        else:
            treffer = icon_sensor_suchen(kind, sensor_priority(key, defaults))
            if treffer:
                ICON_SENSOREN[kind] = treffer
        value = treffer[1].Value if treffer else None
        if value is None:
            ICON_SENSOREN.pop(kind, None)        # Sensor weg oder (noch) ohne Wert -> beim nächsten Mal neu suchen
        werte[kind] = None if value is None else float(value)
    return werte


# ---------- Einstellungen speichern / laden ----------
def load_settings():
    """Liest die Einstellungen; alles Fehlende oder Ungültige bekommt den Startwert. Schlüssel, die nur die Toolbox
    kennt (z. B. task_name), bleiben unverändert erhalten – sonst löschte save_settings() sie beim nächsten Speichern."""
    settings = json.loads(json.dumps(DEFAULT_SETTINGS))          # tiefe Kopie
    try:
        saved = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return settings                          # keine oder kaputte Datei -> Startwerte
    if not isinstance(saved, dict):
        return settings
    if saved.get("icon_interval") in ICON_RATES:
        settings["icon_interval"] = saved["icon_interval"]
    if saved.get("popup_interval") in POPUP_RATES:
        settings["popup_interval"] = saved["popup_interval"]
    if sorted(saved.get("icon_order") or []) == ["cpu", "gpu"]:
        settings["icon_order"] = list(saved["icon_order"])
    for key in ("cpu_sensor", "gpu_sensor"):
        if isinstance(saved.get(key), str) and saved[key].strip():
            settings[key] = saved[key].strip()
    warn, hot = saved.get("warn_temp"), saved.get("hot_temp")
    if isinstance(warn, (int, float)) and isinstance(hot, (int, float)) and 20 <= warn < hot <= 120:
        settings["warn_temp"], settings["hot_temp"] = warn, hot
    if isinstance(saved.get("window"), str) and re.fullmatch(r"\d+x\d+\+-?\d+\+-?\d+", saved["window"]):
        settings["window"] = saved["window"]
    if saved.get("effizienzmodus") in EFFIZIENZ:
        settings["effizienzmodus"] = saved["effizienzmodus"]
    for key, value in saved.items():
        settings.setdefault(key, value)
    return settings


def save_settings(settings):
    try:
        SETTINGS_FILE.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError:
        logging.exception("Einstellungen konnten nicht gespeichert werden")


SETTINGS = load_settings()       # wird bei "reload" (aus der GUI) an Ort und Stelle aktualisiert


def rate_label(seconds):
    if seconds == 1:
        return "1 Sekunde"
    return f"{seconds:g} Sekunden".replace(".", ",")


if "--list" in sys.argv:
    enable_hardware(LATER_HARDWARE)
    collect()            # erste Messung verwerfen: manche Sensoren liefern direkt nach Open() noch 0
    time.sleep(1)
    print("Für detailfenster_inhalt.py:  [Gerät] -> Gruppe(\"gerät\", …)   Typ und Name -> Wert(\"Name\", typ=\"Typ\")")
    for hw in collect()["hardware"]:
        print(f"\n[{hw['geraet']}] {hw['name']}")
        for s in hw["sensors"]:
            print(f"    {TYPE_LABELS.get(s['type'], s['type']):16} {s['name']:32} {fmt_value(s['type'], s['value'])}")
    pc.Close()
    sys.exit()


# ---------- Ab hier: Tray-Icons und Programm ----------
import tkinter as tk  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402
import pystray  # noqa: E402

STRIPE = {"cpu": (70, 140, 255), "gpu": (118, 185, 0)}     # Farbstreifen: blau = CPU, grün = GPU
EMPTY = {"hardware": [], "cpu": None, "gpu": None, "geraete": set()}    # bevor die erste Messung fürs Fenster da ist


def load_font(size):
    try:
        return ImageFont.truetype("arialbd.ttf", size)
    except OSError:                       # außerhalb von Windows gibt es kein Arial
        return ImageFont.load_default(size)


FONT_BIG = load_font(44)     # für 2 Zeichen
FONT_SMALL = load_font(31)   # für 3 Zeichen, z. B. "100"


def make_icon(kind, value):
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    text = "--" if value is None else f"{value:.0f}"
    font = FONT_BIG if len(text) <= 2 else FONT_SMALL
    d.text((32, 27), text, font=font, fill=temp_color(value, SETTINGS), anchor="mm")
    d.rounded_rectangle([8, 55, 56, 63], radius=4, fill=STRIPE[kind])
    return img


# ---------- Windows-Helfer (ohne Windows einfach wirkungslos) ----------
def set_dpi_aware():
    """Sonst rendert Windows das Fenster bei 125/150 % Skalierung unscharf."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass


_mutex = None


def effizienzmodus(an):
    """Effizienzmodus von Windows 11 (Blatt-Symbol im Task-Manager) ein- oder ausschalten.

    Ein: Windows plant den Prozess stromsparend ein (EcoQoS – niedrige Taktrate, auf Hybrid-CPUs die
    Effizienzkerne) und mit niedrigster Priorität. Für die Icons im Hintergrund reicht das; bei offenem Fenster
    wird ausgeschaltet, damit die Oberfläche flüssig bleibt.
    """
    class PROCESS_POWER_THROTTLING_STATE(ctypes.Structure):
        _fields_ = [("Version", ctypes.c_ulong), ("ControlMask", ctypes.c_ulong), ("StateMask", ctypes.c_ulong)]

    drosseln = 0x1                                  # PROCESS_POWER_THROTTLING_EXECUTION_SPEED
    try:
        kernel32 = ctypes.windll.kernel32
        prozess = ctypes.c_void_p(-1)               # Pseudo-Handle für den eigenen Prozess (GetCurrentProcess)
        state = PROCESS_POWER_THROTTLING_STATE(1, drosseln, drosseln if an else 0)
        kernel32.SetProcessInformation(prozess, 4, ctypes.byref(state), ctypes.sizeof(state))  # 4 = PowerThrottling
        kernel32.SetPriorityClass(prozess, 0x40 if an else 0x20)                 # IDLE_ bzw. NORMAL_PRIORITY_CLASS
    except (AttributeError, OSError):               # außerhalb von Windows / ältere Windows-Versionen
        pass


def already_running():
    """True, wenn das Programm schon läuft (wichtig, falls ein Launcher es doppelt startet)."""
    global _mutex
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        _mutex = kernel32.CreateMutexW(None, False, "Local\\HardwareMonitor_SingleInstance")
        return ctypes.get_last_error() == 183           # ERROR_ALREADY_EXISTS
    except Exception:
        return False


# ---------- Programm ----------
class HardwareMonitorApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()                     # Hauptfenster unsichtbar, angezeigt wird nur das Detailfenster
        self.fenster = None                      # Detailfenster – wird erst beim ersten Öffnen gebaut
        self.fenster_bedarf = False              # was das Fenster gerade zeigt: False = zu, sonst Geräte (None = alle)
        self.hardware_ready = False              # True, sobald die übrige Hardware nachgeladen ist
        self.vorhanden = None                    # Geräte mit Sensoren auf diesem PC, z. B. {"cpu", "gpu", "akku"}

        self.stop = threading.Event()
        self.wake = threading.Event()            # weckt den Mess-Thread vorzeitig (Fenster geöffnet, Rate geändert)
        self.lock = threading.Lock()
        self.latest = EMPTY                      # letzte Messung fürs Fenster
        self.shown = {}                          # was gerade in den Icons steht -> nur bei Änderung neu zeichnen
        self.ui_queue = queue.Queue()            # Nachrichten aus den anderen Threads an tkinter
        self.settings = SETTINGS                 # dieselben Einstellungen wie überall im Skript
        self.order = list(self.settings["icon_order"])
        # Icons, die es wirklich gibt: ohne GPU-Temperatur (Intel-Onboard-Grafik) kein GPU-Icon
        self.kinds = [kind for kind in self.order if kind != "gpu" or gpu_hat_temperatur()]
        if "gpu" not in self.kinds:
            logging.info("Keine GPU-Temperatur gefunden – das GPU-Icon wird nicht angezeigt.")
        self.ready = {kind: threading.Event() for kind in self.kinds}
        self.current = {"cpu": None, "gpu": None}    # aktuelle Icon-Werte, für die Statusabfrage der GUI

        self.icons = {
            kind: pystray.Icon(f"hardware_monitor_{kind}", make_icon(kind, None), kind.upper(), self.make_menu())
            for kind in self.kinds
        }
        self.sensor_thread = threading.Thread(target=self.sensor_loop, daemon=True)
        self.ipc_thread = threading.Thread(target=self.ipc_server, daemon=True)

    # --- Rechtsklick-Menü ---
    def make_menu(self):
        return pystray.Menu(
            pystray.MenuItem("Details anzeigen", lambda icon, item: self.ui_queue.put("toggle"), default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(lambda item: f"Icons aktualisieren: {rate_label(self.settings['icon_interval'])}",
                             self.rate_menu("icon_interval", ICON_RATES)),
            pystray.MenuItem(lambda item: f"Fenster aktualisieren: {rate_label(self.settings['popup_interval'])}",
                             self.rate_menu("popup_interval", POPUP_RATES)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("✕  Beenden", lambda icon, item: self.ui_queue.put("quit")),
        )

    def rate_menu(self, key, rates):
        """Untermenü mit Auswahlpunkten; der aktuell gewählte ist markiert."""
        # pystray zählt die Parameter einer Aktion und akzeptiert genau (icon, item) –
        # daher kleine Fabrikfunktionen statt Lambdas mit Standardwert (s=seconds).
        def action(seconds):
            return lambda icon, item: self.set_rate(key, seconds)

        def checked(seconds):
            return lambda item: self.settings[key] == seconds

        return pystray.Menu(*[
            pystray.MenuItem(rate_label(s), action(s), checked=checked(s), radio=True)
            for s in rates
        ])

    def set_rate(self, key, seconds):
        self.settings[key] = seconds
        save_settings(self.settings)
        for icon in self.icons.values():
            icon.update_menu()                   # Markierung und Beschriftung in beiden Menüs auffrischen
        self.wake.set()                          # neue Rate sofort übernehmen

    # --- Detailfenster ---
    def fenster_umschalten(self):
        if self.fenster is None:
            self.fenster = Detailfenster(self.root, self)
        self.fenster.umschalten()

    def fenster_braucht(self, geraete):
        """Meldet das Fenster: welche Geräte es gerade zeigt (False = zu oder minimiert)."""
        if geraete != self.fenster_bedarf:
            war_zu = self.fenster_bedarf is False
            self.fenster_bedarf = geraete
            if (geraete is False) != war_zu:
                self.effizienz_anwenden()        # bei "auto": nur bei geschlossenem Fenster sparsam laufen
            if geraete is False:                 # alte Werte verwerfen – beim Öffnen sonst kurz „Live“ mit altem Stand
                with self.lock:
                    self.latest = EMPTY
            self.wake.set()                      # sofort passend messen

    def effizienz_anwenden(self):
        """Effizienzmodus laut Einstellung: "auto" nur bei geschlossenem Fenster, "an" immer, "aus" nie."""
        modus = self.settings["effizienzmodus"]
        effizienzmodus(modus == "an" or (modus == "auto" and self.fenster_bedarf is False))

    def fenster_geometrie(self, geometry):
        """Meldet das Fenster beim Schließen: Größe und Position, z. B. "480x640+1420+380"."""
        if self.settings.get("window") != geometry:
            self.settings["window"] = geometry
            save_settings(self.settings)

    def snapshot(self):
        with self.lock:
            return self.latest

    # --- Hintergrund-Thread: misst und aktualisiert die Icons ---
    def measure(self, geraete):
        try:
            snap = collect(geraete, self.kinds)
        except Exception:
            logging.exception("Fehler beim Auslesen der Sensoren")
            snap = dict(EMPTY)
        snap["loading"] = not self.hardware_ready
        return snap

    def measure_icons(self):
        """Nur die beiden Icon-Werte (sparsamer als measure(), siehe icon_werte())."""
        try:
            return icon_werte(self.kinds)
        except Exception:
            logging.exception("Fehler beim Auslesen der Icon-Werte")
            ICON_SENSOREN.clear()                # beim nächsten Mal neu suchen
            return {"cpu": None, "gpu": None}

    def update_icons(self, werte):
        """werte: {"cpu": Temperatur, "gpu": Temperatur} – None, wenn es keinen Wert gibt."""
        for kind, icon in self.icons.items():
            value = werte.get(kind)
            self.current[kind] = None if value is None else round(value, 1)
            text = "--" if value is None else f"{value:.0f}"
            if self.shown.get(kind) == text:
                continue                         # gleiche Zahl wie vorher -> nichts neu zeichnen
            self.shown[kind] = text
            icon.icon = make_icon(kind, value)
            shown = "–" if value is None else f"{text} °C"
            icon.title = f"{kind.upper()}: {shown}  ·  Klick für Details"

    def sensor_loop(self):
        """Fenster zu (oder minimiert): alle `icon_interval` Sekunden nur CPU und GPU lesen.
        Fenster offen: alle `popup_interval` Sekunden die Geräte des gewählten Tabs (die Icons bekommen die Werte mit)."""
        try:
            self.update_icons(self.measure_icons())          # Icons sofort mit echten Werten füllen …
            enable_hardware(LATER_HARDWARE)                  # … dann den Rest nachladen (RAM dauert ~8 s)
            snap = self.measure(None)            # einmal alles "anwärmen": die erste Messung liefert teils 0
            # Das Fenster blendet damit Tabs aus, die es hier nicht gibt (z. B. Mainboard am Laptop, Akku am Desktop)
            self.vorhanden = {hw["geraet"] for hw in snap["hardware"]} or None     # Messung fehlgeschlagen -> alle zeigen
            self.hardware_ready = True
            next_icon = next_window = 0.0
            while not self.stop.is_set():
                now = time.monotonic()
                needed = self.fenster_bedarf

                if needed is not False and now >= next_window:
                    snap = self.measure(needed)
                    with self.lock:
                        if self.fenster_bedarf is not False:     # Fenster nicht während der Messung geschlossen
                            self.latest = snap
                    self.update_icons({k: snap[k]["value"] if snap[k] else None for k in ("cpu", "gpu")})
                    self.ui_queue.put("data")    # Fenster neu zeichnen lassen
                    next_window = now + self.settings["popup_interval"]
                    next_icon = now + self.settings["icon_interval"]
                elif now >= next_icon:
                    self.update_icons(self.measure_icons())
                    next_icon = now + self.settings["icon_interval"]

                due = min(next_icon, next_window) if needed is not False else next_icon
                self.wake.wait(max(0.05, due - time.monotonic()))
                if self.wake.is_set():           # Fenster geöffnet, Tab gewechselt, Rate geändert -> sofort neu planen
                    self.wake.clear()
                    next_icon = next_window = 0.0
        finally:
            pc.Close()
            nvidia.close()

    # --- Fernsteuerung durch die Toolbox-GUI ---
    def ipc_server(self):
        """Wartet auf Befehle der GUI: "status", "reload" oder "quit" (ein Befehl pro Verbindung).

        Nötig, weil dieses Programm mit Adminrechten läuft und die GUI ohne: Windows verbietet der GUI,
        es einfach zu beenden – eine Bitte über eine lokale Verbindung geht aber.
        """
        server = None
        logged = False
        while server is None and not self.stop.is_set():
            try:
                server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                if os.name != "nt":                      # nur Linux/macOS: Port direkt nach Neustart wieder nutzbar
                    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server.bind(("127.0.0.1", IPC_PORT))     # nur von diesem PC aus erreichbar
                server.listen()
            except OSError:
                server.close()
                server = None
                if not logged:                           # Port noch belegt (z. B. direkt nach Neustart) -> später nochmal
                    logging.warning("Port %s belegt – Fernsteuerung wird später erneut versucht", IPC_PORT)
                    logged = True
                self.stop.wait(2)
        if server is None:
            return
        # accept() wartet ohne Timeout, bis sich jemand meldet – kein Aufwachen im Leerlauf. Beim Beenden muss
        # niemand den Thread wecken: er läuft als Daemon und endet mit dem Programm.
        with server:
            while not self.stop.is_set():
                try:
                    conn, _ = server.accept()
                except OSError:
                    break
                with conn:
                    try:
                        conn.settimeout(1)
                        command = conn.recv(64).decode("utf-8", "replace").strip()
                        reply = self.handle_command(command)
                        conn.sendall((json.dumps(reply) + "\n").encode("utf-8"))
                    except OSError:
                        pass

    def handle_command(self, command):
        if command == "status":
            return {"ok": True, "pid": os.getpid(), "cpu": self.current["cpu"], "gpu": self.current["gpu"],
                    "order": self.order, "icons": self.kinds}
        if command in ("reload", "quit"):
            self.ui_queue.put(command)
            return {"ok": True}
        return {"ok": False, "error": f"Unbekannter Befehl: {command}"}

    def reload_settings(self):
        """Die GUI hat Einstellungen geändert -> neu einlesen und überall übernehmen."""
        window = SETTINGS["window"]              # gehört dem Fenster – die Toolbox hat evtl. einen alten Stand
        SETTINGS.update(load_settings())
        SETTINGS["window"] = window
        self.shown.clear()                       # Icons neu zeichnen (z. B. neue Farbgrenzen)
        ICON_SENSOREN.clear()                    # Icon-Sensoren neu suchen (z. B. anderer Sensor gewählt)
        for icon in self.icons.values():
            icon.update_menu()
        self.effizienz_anwenden()                # z. B. in der Toolbox auf „Immer an“ gestellt
        if self.fenster:
            self.fenster.aktualisieren()
        self.wake.set()

    # --- tkinter-Seite ---
    def poll_queue(self):
        try:
            while True:
                message = self.ui_queue.get_nowait()
                if message == "toggle":
                    self.fenster_umschalten()
                elif message == "data" and self.fenster:
                    self.fenster.aktualisieren()
                elif message == "reload":
                    self.reload_settings()
                elif message == "quit":
                    self.quit()
                    return
        except queue.Empty:
            pass
        # Fenster zu: seltener nachsehen (ein Klick aufs Icon reagiert dann höchstens ¼ s später)
        self.root.after(100 if self.fenster_bedarf is not False else 250, self.poll_queue)

    def quit(self):
        self.stop.set()
        self.wake.set()                          # Mess-Thread nicht erst ausschlafen lassen
        if self.fenster:
            self.fenster.speichern()             # Position und Größe merken
        for icon in self.icons.values():
            icon.stop()
        self.root.quit()

    def run(self):
        # Icons nacheinander anmelden, damit die Reihenfolge in der Taskleiste immer gleich ist
        for kind in self.kinds:
            self.icons[kind].run_detached(setup=lambda ic, k=kind: (setattr(ic, "visible", True), self.ready[k].set()))
            self.ready[kind].wait(timeout=5)
        self.effizienz_anwenden()                # Fenster ist zu – bei "auto" also an, bis es geöffnet wird
        self.sensor_thread.start()
        self.ipc_thread.start()
        self.root.after(100, self.poll_queue)
        self.root.mainloop()                     # läuft, bis quit() aufgerufen wird
        self.sensor_thread.join(timeout=5)
        self.root.destroy()


def main():
    if already_running():
        logging.info("Läuft bereits – zweiter Start wird beendet.")
        pc.Close()
        return
    set_dpi_aware()
    try:
        HardwareMonitorApp().run()
    except Exception:
        logging.exception("Unerwarteter Fehler")
        raise


if __name__ == "__main__":
    main()
