"""
hardware_monitor.py – Hardware-Monitor im Infobereich der Taskleiste.
Zeigt CPU- und GPU-Temperatur als zwei Zahlen; ein Klick auf eines der Icons öffnet ein Fenster
mit fast allen Hardware-Messwerten,
aufgeteilt in Tabs (Temperaturen, CPU, GPU, RAM, Mainboard, Laufwerke, Netzwerk, Weitere).

Voraussetzungen:
  - PawnIO installiert:            winget install namazso.PawnIO
  - LibreHardwareMonitor-Release (LibreHardwareMonitor.zip) entpackt nach src/hardware_monitor/lhm
  - Python-Pakete:                 pip install pythonnet pystray pillow
  - Start mit Adminrechten (sonst fehlen CPU- und Mainboard-Werte)

Aufruf:
  pythonw hardware_monitor.py          -> Tray-Icons (ohne Konsolenfenster)
  python  hardware_monitor.py --list   -> listet alle Sensoren auf (zum Anpassen der Namen)

Sparsam im Hintergrund: Solange das Fenster zu ist, werden nur CPU und GPU gelesen.
Die Aktualisierungsraten lassen sich per Rechtsklick aufs Icon einstellen; alle weiteren
Einstellungen über die Toolbox-GUI. Gespeichert wird in hardware_monitor_settings.json neben dem Skript.
Die GUI steuert das Programm über eine lokale Verbindung (127.0.0.1, Port IPC_PORT).

Fehler landen in hardware_monitor.log neben dem Skript (pythonw hat keine Konsole).
"""

import ctypes
import fnmatch
import json
import logging
import os
import socket
import queue
import re
import sys
import threading
import time
from ctypes import wintypes
from pathlib import Path

# ---------- Einstellungen ----------
# Ordner mit LibreHardwareMonitorLib.dll: zuerst lhm\ neben diesem Skript, dann im Repo, dann C:\Tools\lhm
SCRIPT_DIR = Path(__file__).resolve().parent
LHM_CANDIDATES = [SCRIPT_DIR / "lhm", SCRIPT_DIR.parents[1] / "lhm", Path(r"C:\Tools\lhm")]
LHM_DIR = next((str(d) for d in LHM_CANDIDATES if (d / "LibreHardwareMonitorLib.dll").exists()),
               str(LHM_CANDIDATES[0]))

# Auswahl im Rechtsklick-Menü (Sekunden)
ICON_RATES = (1, 2, 5, 10)      # Taskleisten-Icons (liest nur CPU und GPU)
POPUP_RATES = (0.5, 1, 2, 5)    # geöffnetes Fenster (liest alles)

# Startwerte. Geändert wird über das Rechtsklick-Menü oder die Toolbox-GUI;
# beides landet in hardware_monitor_settings.json neben dem Skript.
DEFAULT_SETTINGS = {
    "icon_interval": 2,
    "popup_interval": 1,
    "icon_order": ["cpu", "gpu"],    # Reihenfolge in der Taskleiste (wirkt nach Neustart des Programms)
    "cpu_sensor": "auto",            # "auto" = erster vorhandener aus CPU_SENSORS, sonst ein Sensorname
    "gpu_sensor": "auto",
    "warn_temp": 60,                 # ab hier gelb
    "hot_temp": 80,                  # ab hier rot
    "hidden": [],                    # Sensoren, die im Fenster ausgeblendet werden (Muster, * als Platzhalter)
}
SETTINGS_FILE = Path(__file__).with_name("hardware_monitor_settings.json")

# Bei "auto": welcher Sensor im Tray-Icon angezeigt wird – der erste aus der Liste, den es gibt
CPU_SENSORS = ("Core (Tctl/Tdie)", "CPU Package", "Core Average")
GPU_SENSORS = ("GPU Core", "GPU Hot Spot")

# Lokale Fernsteuerung für die Toolbox-GUI (nur von diesem PC aus erreichbar)
IPC_PORT = 47815

# Welche Hardware ausgelesen wird. Was du nicht brauchst, einfach rausnehmen.
ENABLED_HARDWARE = (
    "IsCpuEnabled", "IsGpuEnabled", "IsMemoryEnabled", "IsMotherboardEnabled",
    "IsControllerEnabled", "IsStorageEnabled", "IsNetworkEnabled",
    "IsPsuEnabled", "IsBatteryEnabled", "IsPowerMonitorEnabled",
)

logging.basicConfig(
    filename=Path(__file__).with_suffix(".log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

# ---------- LibreHardwareMonitor laden ----------
sys.path.append(LHM_DIR)
import clr  # pythonnet  # noqa: E402
clr.AddReference("LibreHardwareMonitorLib")
from LibreHardwareMonitor.Hardware import Computer, HardwareType, SensorType  # noqa: E402

pc = Computer()
for prop in ENABLED_HARDWARE:
    try:
        setattr(pc, prop, True)
    except Exception:                    # ältere LHM-Versionen kennen nicht alle Schalter
        pass
pc.Open()


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

# Sensortyp -> deutsche Überschrift im Popup. Die Reihenfolge hier ist auch die Reihenfolge im Popup.
TYPE_LABELS = {
    "Temperature": "Temperatur", "Load": "Auslastung", "Clock": "Takt", "Frequency": "Frequenz",
    "Power": "Leistung", "Voltage": "Spannung", "Current": "Stromstärke", "Energy": "Energie",
    "Fan": "Lüfter", "Control": "Lüftersteuerung", "Flow": "Durchfluss", "Data": "Daten",
    "SmallData": "Speicher", "Throughput": "Durchsatz", "Level": "Zustand", "Factor": "Faktor",
    "TimeSpan": "Zeit", "Timing": "Timing", "Noise": "Lautstärke", "Conductivity": "Leitfähigkeit",
    "Humidity": "Luftfeuchtigkeit",
}
SENSOR_TYPES = enum_table(SensorType, tuple(TYPE_LABELS))

# Hardwaretyp -> Tab im Popup
HW_TAB = {
    "Cpu": "CPU", "GpuNvidia": "GPU", "GpuAmd": "GPU", "GpuIntel": "GPU", "Memory": "RAM",
    "Motherboard": "Mainboard", "SuperIO": "Mainboard", "EmbeddedController": "Mainboard",
    "Storage": "Laufwerke", "Network": "Netzwerk",
}
TAB_ORDER = ("Temperaturen", "CPU", "GPU", "RAM", "Mainboard", "Laufwerke", "Netzwerk", "Weitere")


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


def collect(full=True):
    """Liest die Sensoren der aktivierten Geräte.

    full=True:  alle Geräte (fürs geöffnete Fenster)
    full=False: nur CPU und GPU (reicht für die Tray-Icons und spart Rechenzeit)

    Ergebnis (ein "Snapshot"):
      hardware: [{"id", "tab", "kind" ("cpu"/"gpu"/None), "name",
                  "sensors": [{"id", "type", "name", "value"}, ...]}, ...]
      cpu / gpu: der jeweils fürs Tray-Icon ausgewählte Temperatursensor (oder None)
    """
    hardware = []
    for top in pc.Hardware:
        top_type = enum_name(top.HardwareType, HW_TYPES)
        tab = HW_TAB.get(top_type, "Weitere")
        kind = "cpu" if top_type == "Cpu" else "gpu" if top_type.startswith("Gpu") else None
        if not full and kind is None:
            continue                             # andere Hardware gar nicht erst ansprechen
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
                    "tab": tab,
                    "kind": kind if depth == 0 else None,
                    "name": str(hw.Name) if depth == 0 else f"{top.Name} – {hw.Name}",
                    "sensors": sensors,
                })
        except Exception:
            logging.exception("Fehler beim Auslesen von %s", top.Name)

    return {
        "hardware": hardware,
        "cpu": pick(hardware, "cpu", sensor_priority("cpu_sensor", CPU_SENSORS)),
        "gpu": pick(hardware, "gpu", sensor_priority("gpu_sensor", GPU_SENSORS)),
    }


def sensor_priority(key, defaults):
    """Gewählter Sensor zuerst; falls es ihn nicht gibt, greift die automatische Reihenfolge."""
    chosen = SETTINGS.get(key, "auto")
    return defaults if chosen == "auto" else (chosen,) + defaults


# ---------- Einstellungen speichern / laden ----------
def load_settings():
    """Liest die Einstellungen; alles Fehlende oder Ungültige bekommt den Startwert."""
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
    if isinstance(saved.get("hidden"), list):
        settings["hidden"] = [p for p in saved["hidden"] if isinstance(p, str) and p.strip()]
    return settings


def save_settings(settings):
    try:
        SETTINGS_FILE.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError:
        logging.exception("Einstellungen konnten nicht gespeichert werden")


SETTINGS = load_settings()       # wird bei "reload" (aus der GUI) an Ort und Stelle aktualisiert


def is_hidden(sensor_name):
    """True, wenn der Sensor laut Einstellungen im Fenster ausgeblendet werden soll."""
    name = sensor_name.lower()
    return any(fnmatch.fnmatchcase(name, pattern.lower()) for pattern in SETTINGS["hidden"])


def rate_label(seconds):
    if seconds == 1:
        return "1 Sekunde"
    return f"{seconds:g} Sekunden".replace(".", ",")


# ---------- Werte formatieren ----------
def num(value, decimals):
    return f"{value:.{decimals}f}".replace(".", ",")      # deutsches Komma


def fmt_rate(bytes_per_s):
    for unit in ("B/s", "KB/s", "MB/s", "GB/s"):
        if bytes_per_s < 1024 or unit == "GB/s":
            return f"{num(bytes_per_s, 0 if unit == 'B/s' else 1)} {unit}"
        bytes_per_s /= 1024


UNITS = {   # Sensortyp -> (Nachkommastellen, Einheit)
    "Temperature": (0, "°C"), "Load": (0, "%"), "Control": (0, "%"), "Level": (0, "%"),
    "Humidity": (0, "%"), "Clock": (0, "MHz"), "Frequency": (0, "Hz"), "Power": (1, "W"),
    "Voltage": (3, "V"), "Current": (2, "A"), "Energy": (0, "mWh"), "Fan": (0, "RPM"),
    "Flow": (0, "L/h"), "Data": (1, "GB"), "SmallData": (0, "MB"), "Timing": (1, "ns"),
    "Noise": (0, "dBA"), "Conductivity": (0, "µS/cm"), "Factor": (2, ""),
}


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


if "--list" in sys.argv:
    collect()            # erste Messung verwerfen: manche Sensoren liefern direkt nach Open() noch 0
    time.sleep(1)
    for hw in collect()["hardware"]:
        print(f"\n[{hw['tab']}] {hw['name']}")
        for s in hw["sensors"]:
            print(f"    {TYPE_LABELS.get(s['type'], s['type']):16} {s['name']:32} {fmt_value(s['type'], s['value'])}")
    pc.Close()
    sys.exit()


# ---------- Erklärungen für den Hover-Tooltip ----------
# (Sensortyp, Muster, Text) – das Muster muss auf den ganzen Sensornamen passen. {0} wird durch die
# erste Klammergruppe im Muster ersetzt (z. B. die Nummer bei "CCD1"). Neue Sensoren einfach ergänzen.
# Wichtig ist der Sensortyp: "GPU Core" ist z. B. sowohl eine Temperatur als auch eine Auslastung und ein Takt.
SENSOR_INFO = [
    # --- Temperaturen: CPU ---
    ("Temperature", r"Core \(Tctl/Tdie\)", "Die Steuertemperatur des Prozessors, nach der Mainboard und Lüfter "
                                           "regeln – der wichtigste CPU-Wert."),
    ("Temperature", r"Core \(Tctl\)", "Steuertemperatur für die Lüfterregelung; bei einigen Ryzen-Modellen absichtlich "
                                      "um einen festen Wert höher als die echte Temperatur."),
    ("Temperature", r"Core \(Tdie\)", "Die tatsächliche Temperatur des Prozessor-Chips, ohne den Lüfter-Aufschlag von Tctl."),
    ("Temperature", r"CCD(\d+) \(Tdie\)", "Temperatur von Kern-Chip Nr. {0} (Core Complex Die) – hier sitzen die "
                                          "eigentlichen CPU-Kerne."),
    ("Temperature", r"CCDs Max \(Tdie\)", "Der höchste Wert aller Kern-Chips (CCDs)."),
    ("Temperature", r"CCDs Average \(Tdie\)", "Der Durchschnitt aller Kern-Chips (CCDs)."),
    ("Temperature", r"SoC", "Temperatur des I/O-Teils der CPU mit Speicher-Controller und PCIe-Anbindung."),
    ("Temperature", r"CPU Package", "Gesamttemperatur des Prozessors, meist so hoch wie der heißeste Kern – der "
                                    "wichtigste Wert bei Intel."),
    ("Temperature", r"Core Max", "Die Temperatur des aktuell heißesten CPU-Kerns."),
    ("Temperature", r"Core Average", "Der Durchschnitt über alle CPU-Kerne."),
    ("Temperature", r"CPU Core #(\d+)", "Temperatur von CPU-Kern Nr. {0}."),
    ("Temperature", r"Distance to TjMax", "Abstand bis zu der Temperatur, ab der sich die CPU drosselt – hier ist ein "
                                          "höherer Wert besser."),
    # --- Temperaturen: GPU ---
    ("Temperature", r"GPU Core", "Die durchschnittliche Temperatur des Grafikchips – der klassische GPU-Wert."),
    ("Temperature", r"GPU Hot Spot", "Die heißeste Stelle auf dem Grafikchip; liegt normalerweise 10–20 °C über "
                                     "GPU Core, deutlich mehr kann auf schlechten Kühlerkontakt hindeuten."),
    ("Temperature", r"GPU Memory Junction", "Die heißeste Stelle im Grafikspeicher (VRAM); unter Last sind hier Werte "
                                            "bis knapp 100 °C noch normal."),
    ("Temperature", r"GPU Memory", "Temperatur des Grafikspeichers (VRAM)."),
    ("Temperature", r"GPU VR .+", "Temperatur eines Spannungswandlers, der Grafikchip oder Speicher mit Strom versorgt."),
    ("Temperature", r"GPU Liquid", "Temperatur der Kühlflüssigkeit bei wassergekühlten Grafikkarten."),
    # --- Temperaturen: Mainboard / Laufwerke ---
    ("Temperature", r"CPU", "CPU-Temperatur, gemessen vom Sensor auf dem Mainboard – meist weniger genau als Tctl/Tdie."),
    ("Temperature", r"System|Motherboard", "Temperatur auf dem Mainboard, ungefähr die Lufttemperatur im Gehäuse."),
    ("Temperature", r"PCH|Chipset", "Temperatur des Chipsatzes auf dem Mainboard."),
    ("Temperature", r"VRM.*", "Temperatur der Spannungswandler, die die CPU mit Strom versorgen."),
    ("Temperature", r"Temperature #(\d+)", "Unbenannter Temperaturfühler Nr. {0} am Mainboard; was er misst, hängt "
                                           "vom Board ab."),
    ("Temperature", r"Temperature( \d+)?", "Temperatur des Laufwerks (Controller oder Speicherchips)."),
    ("Temperature", r"Composite Temperature", "Zusammengefasste Temperatur der SSD, nach der sie sich ggf. drosselt."),
    # --- Auslastung ---
    ("Load", r"CPU Total", "Gesamtauslastung aller CPU-Kerne."),
    ("Load", r"CPU Core Max", "Auslastung des gerade am stärksten belasteten Kerns."),
    ("Load", r"CPU Core #(\d+)(?: Thread #(\d+))?", "Auslastung von CPU-Kern Nr. {0}."),
    ("Load", r"GPU Core", "Wie stark die Recheneinheiten der Grafikkarte gerade arbeiten."),
    ("Load", r"GPU Memory Controller", "Auslastung der Anbindung zwischen Grafikchip und Grafikspeicher."),
    ("Load", r"GPU Video Engine", "Auslastung der Videoeinheit (Abspielen und Aufnehmen von Videos)."),
    ("Load", r"GPU Bus", "Auslastung der PCIe-Verbindung zwischen Grafikkarte und Mainboard."),
    ("Load", r"GPU Memory", "Anteil des belegten Grafikspeichers (VRAM)."),
    ("Load", r"D3D .+", "Auslastung laut Windows für diesen Teil der Grafikkarte (z. B. 3D, Kopieren, Video)."),
    ("Load", r"Memory", "Anteil des belegten Arbeitsspeichers."),
    ("Load", r"Virtual Memory", "Anteil des belegten Arbeitsspeichers inklusive Auslagerungsdatei."),
    ("Load", r"Used Space", "Wie voll das Laufwerk ist."),
    ("Load", r"(Total|Read|Write) Activity", "Wie viel Prozent der Zeit das Laufwerk gerade beschäftigt ist."),
    ("Load", r"Network Utilization", "Auslastung der Netzwerkverbindung im Verhältnis zu ihrer Maximalgeschwindigkeit."),
    # --- Takt ---
    ("Clock", r"Core #(\d+)", "Aktueller Takt von CPU-Kern Nr. {0}."),
    ("Clock", r"Bus Speed", "Grundtakt, aus dem sich per Multiplikator der CPU-Takt ergibt (meist rund 100 MHz)."),
    ("Clock", r"Cores \(Average.*\)", "Durchschnittlicher Takt aller CPU-Kerne."),
    ("Clock", r"GPU Core", "Aktueller Takt des Grafikchips."),
    ("Clock", r"GPU Memory", "Aktueller Takt des Grafikspeichers."),
    ("Clock", r"GPU Shader", "Takt der Shader-Einheiten der Grafikkarte."),
    # --- Leistung ---
    ("Power", r"(CPU )?Package", "Gesamter Stromverbrauch des Prozessors."),
    ("Power", r"Core #(\d+) \(SMU\)", "Stromverbrauch von Kern Nr. {0}, gemeldet vom Prozessor selbst."),
    ("Power", r"Cores", "Stromverbrauch aller Kerne zusammen."),
    ("Power", r"SoC", "Stromverbrauch des I/O-Teils der CPU."),
    ("Power", r"GPU (Package|Power)", "Gesamter Stromverbrauch der Grafikkarte."),
    # --- Spannung ---
    ("Voltage", r"Core \(SVI\d? ?TFN\)", "Kernspannung der CPU, gemeldet vom Spannungsregler."),
    ("Voltage", r"SoC \(SVI\d? ?TFN\)", "Spannung des I/O-Teils der CPU."),
    ("Voltage", r"Vcore|CPU Core|CPU VCore", "Kernspannung der CPU, gemessen vom Mainboard."),
    ("Voltage", r"\+?(12|5|3[.,]3)V", "Spannung der {0}-Volt-Leitung vom Netzteil; sollte nahe am Sollwert liegen "
                                      "(etwa ±5 %)."),
    ("Voltage", r"VBat|Vbat|CMOS Battery|Battery", "Spannung der Knopfzelle auf dem Mainboard; liegt sie unter etwa "
                                                   "2,8 V, sollte sie bald getauscht werden."),
    ("Voltage", r"GPU Core", "Spannung des Grafikchips."),
    # --- Lüfter ---
    ("Fan", r"GPU Fan( \d+)?", "Drehzahl des Grafikkarten-Lüfters; 0 RPM im Leerlauf ist normal, viele Karten "
                               "stoppen ihre Lüfter dann."),
    ("Fan", r"Fan #(\d+)", "Drehzahl des Lüfteranschlusses Nr. {0} auf dem Mainboard."),
    ("Fan", r"Pump.*", "Drehzahl der Pumpe einer Wasserkühlung."),
    ("Control", r"GPU Fan( \d+)?", "Wie stark der Grafikkarten-Lüfter angesteuert wird (Prozent der Maximaldrehzahl)."),
    ("Control", r"Fan( Control)? #(\d+)", "Wie stark der Lüfteranschluss auf dem Mainboard angesteuert wird."),
    # --- Speicher / Daten ---
    ("Data", r"Memory Used", "Belegter Arbeitsspeicher."),
    ("Data", r"Memory Available", "Noch freier Arbeitsspeicher."),
    ("Data", r"Virtual Memory Used", "Belegter Arbeitsspeicher inklusive Auslagerungsdatei auf der SSD."),
    ("Data", r"Virtual Memory Available", "Noch freier Speicher inklusive Auslagerungsdatei."),
    ("Data", r"Data Read", "Insgesamt von diesem Laufwerk gelesene Datenmenge über seine ganze Lebensdauer."),
    ("Data", r"Data Written", "Insgesamt auf dieses Laufwerk geschriebene Datenmenge über seine ganze Lebensdauer."),
    ("Data", r"Data Uploaded", "Hochgeladene Datenmenge seit dem Verbinden des Adapters."),
    ("Data", r"Data Downloaded", "Heruntergeladene Datenmenge seit dem Verbinden des Adapters."),
    ("SmallData", r"GPU Memory Used", "Belegter Grafikspeicher (VRAM)."),
    ("SmallData", r"GPU Memory Free", "Noch freier Grafikspeicher (VRAM)."),
    ("SmallData", r"GPU Memory Total", "Gesamtgröße des Grafikspeichers (VRAM)."),
    ("SmallData", r"D3D Dedicated Memory Used", "Grafikspeicher, den Windows-Programme gerade belegen."),
    ("SmallData", r"D3D Shared Memory Used", "Arbeitsspeicher, den die Grafikkarte zusätzlich mitbenutzt – steigt, "
                                             "wenn der Grafikspeicher knapp wird."),
    # --- Durchsatz ---
    ("Throughput", r"Read Rate", "Aktuelle Lesegeschwindigkeit des Laufwerks."),
    ("Throughput", r"Write Rate", "Aktuelle Schreibgeschwindigkeit des Laufwerks."),
    ("Throughput", r"Upload Speed", "Aktuelle Upload-Geschwindigkeit."),
    ("Throughput", r"Download Speed", "Aktuelle Download-Geschwindigkeit."),
    ("Throughput", r"GPU PCIe Rx", "Daten, die die Grafikkarte gerade über PCIe empfängt."),
    ("Throughput", r"GPU PCIe Tx", "Daten, die die Grafikkarte gerade über PCIe sendet."),
    # --- Zustand ---
    ("Level", r"Available Spare", "Reserve-Speicherzellen der SSD für defekte Zellen; sinkt im Laufe der Zeit."),
    ("Level", r"Remaining Life", "Geschätzte verbleibende Lebensdauer der SSD."),
    ("Level", r"Percentage Used", "Verbrauchter Anteil der vom Hersteller angegebenen Lebensdauer der SSD."),
    ("Level", r"Charge Level", "Ladestand des Akkus."),
    ("Level", r"Degradation Level", "Wie stark der Akku gegenüber neu an Kapazität verloren hat."),
]

TYPE_INFO = {   # Rückfall, wenn kein genauerer Eintrag oben passt
    "Temperature": "Ein Temperaturfühler dieser Komponente.",
    "Load": "Auslastung in Prozent.",
    "Clock": "Taktfrequenz in Megahertz (Millionen Takte pro Sekunde).",
    "Power": "Aktuelle Leistungsaufnahme in Watt.",
    "Voltage": "Gemessene Spannung in Volt.",
    "Current": "Gemessene Stromstärke in Ampere.",
    "Fan": "Lüfterdrehzahl in Umdrehungen pro Minute.",
    "Control": "Ansteuerung eines Lüfters oder einer Pumpe in Prozent.",
    "Data": "Eine Datenmenge.",
    "SmallData": "Eine Speichermenge.",
    "Throughput": "Aktuelle Übertragungsgeschwindigkeit.",
    "Level": "Füllstand bzw. Zustand in Prozent.",
}


def explain(sensor_type, sensor_name):
    for t, pattern, text in SENSOR_INFO:
        if t == sensor_type:
            match = re.fullmatch(pattern, sensor_name)
            if match:
                return text.format(*(g or "" for g in match.groups()))
    return TYPE_INFO.get(sensor_type, "Messwert laut LibreHardwareMonitor.")


# ---------- Ab hier: Tray-Icons und Popup ----------
import tkinter as tk  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402
import pystray  # noqa: E402

STRIPE = {"cpu": (70, 140, 255), "gpu": (118, 185, 0)}     # Farbstreifen: blau = CPU, grün = GPU
TAB_ACCENT = {
    "CPU": STRIPE["cpu"], "GPU": STRIPE["gpu"], "RAM": (235, 150, 60), "Mainboard": (40, 185, 170),
    "Laufwerke": (175, 110, 255), "Netzwerk": (60, 170, 235), "Weitere": (150, 150, 150),
}
BAR_TYPES = {"Temperature", "Load", "Control", "Level", "Humidity"}     # Werte von 0–100 bekommen einen Balken
EMPTY = {"hardware": [], "cpu": None, "gpu": None, "loading": True}    # bevor die erste volle Messung da ist


def load_font(size):
    try:
        return ImageFont.truetype("arialbd.ttf", size)
    except OSError:                       # außerhalb von Windows gibt es kein Arial
        return ImageFont.load_default(size)


FONT_BIG = load_font(44)     # für 2 Zeichen
FONT_SMALL = load_font(31)   # für 3 Zeichen, z. B. "100"


def temp_color(value):
    if value is None:
        return (160, 160, 160)
    if value < SETTINGS["warn_temp"]:
        return (90, 210, 120)    # grün
    if value < SETTINGS["hot_temp"]:
        return (245, 190, 40)    # gelb
    return (235, 60, 60)         # rot


def hex_color(rgb):
    return "#%02x%02x%02x" % rgb


def make_icon(kind, value):
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    text = "--" if value is None else f"{value:.0f}"
    font = FONT_BIG if len(text) <= 2 else FONT_SMALL
    d.text((32, 27), text, font=font, fill=temp_color(value), anchor="mm")
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


def already_running():
    """True, wenn das Programm schon läuft (wichtig, falls ein Launcher es doppelt startet)."""
    global _mutex
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        _mutex = kernel32.CreateMutexW(None, False, "Local\\HardwareMonitor_SingleInstance")
        return ctypes.get_last_error() == 183           # ERROR_ALREADY_EXISTS
    except Exception:
        return False


def work_area():
    """Bildschirmbereich ohne Taskleiste: (links, oben, rechts, unten) in Pixeln."""
    try:
        rect = wintypes.RECT()
        ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0)  # SPI_GETWORKAREA
        return rect.left, rect.top, rect.right, rect.bottom
    except Exception:
        return None


def round_corners(window):
    """Abgerundete Ecken wie bei Windows-11-Flyouts."""
    try:
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        pref = ctypes.c_int(2)                                        # DWMWCP_ROUND
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(pref), ctypes.sizeof(pref))
    except Exception:
        pass


# ---------- Popup-Fenster ----------
BG, BORDER, FG, SUB, TRACK = "#2b2b2b", "#454545", "#f0f0f0", "#9a9a9a", "#444444"
TAB_ACTIVE, TAB_HOVER = "#4c9aff", "#3a3a3a"
CLOSE_HOVER = "#c42b1c"
TIP_BG, TIP_BORDER = "#3a3a3a", "#5a5a5a"
POPUP_WIDTH = 470            # bei 100 % Skalierung, wächst automatisch mit
MAX_HEIGHT_SHARE = 0.75      # höchstens 75 % der Bildschirmhöhe, danach wird gescrollt


def tab_content(snap, tab):
    """Die Geräte (mit ihren sichtbaren Sensoren), die im jeweiligen Tab angezeigt werden."""
    groups = []
    for hw in snap["hardware"]:
        if tab == "Temperaturen":
            if hw["kind"] not in ("cpu", "gpu"):
                continue
            sensors = [s for s in hw["sensors"] if s["type"] == "Temperature"]
        elif hw["tab"] == tab:
            sensors = hw["sensors"]
        else:
            continue
        sensors = [s for s in sensors if not is_hidden(s["name"])]       # in der GUI ausgeblendete weglassen
        if sensors:
            groups.append(dict(hw, sensors=sensors))
    return groups


def available_tabs(snap):
    return [tab for tab in TAB_ORDER if tab_content(snap, tab)]


class Popup:
    def __init__(self, app):
        self.app = app
        self.root = app.root
        self.scale = self.root.winfo_fpixels("1i") / 96          # 1.0 bei 100 %, 1.5 bei 150 %
        self.win = None
        self.tip_job = None
        self.closed_at = 0.0
        self.signature = None
        self.rows = {}
        self.tab = "Temperaturen"                # bleibt erhalten, solange das Programm läuft

    def px(self, value):
        return int(value * self.scale)

    # --- öffnen / schließen ---
    def toggle(self):
        if self.win:
            self.close()
        elif time.monotonic() - self.closed_at > 0.3:
            # Der Klick aufs Icon hat das Popup evtl. gerade per Fokusverlust geschlossen -> nicht sofort wieder öffnen
            self.open()

    def open(self):
        w = tk.Toplevel(self.root)
        self.win = w
        w.overrideredirect(True)                 # kein Fensterrahmen, keine Titelleiste
        w.attributes("-topmost", True)
        w.configure(bg=BORDER)

        outer = tk.Frame(w, bg=BG)
        outer.pack(padx=1, pady=1, fill="both", expand=True)     # 1 px Rahmen in BORDER-Farbe
        self.outer = outer

        # Kopfzeile mit ✕
        header = tk.Frame(outer, bg=BG)
        header.pack(fill="x", padx=self.px(16), pady=(self.px(12), self.px(6)))
        tk.Label(header, text="Hardware", bg=BG, fg=FG, font=("Segoe UI Semibold", 11)).pack(side="left")
        close = tk.Label(header, text="✕", bg=BG, fg=FG, font=("Segoe UI", 11), width=3, cursor="hand2")
        close.pack(side="right")
        close.bind("<Enter>", lambda e: close.config(bg=CLOSE_HOVER, fg="white"))
        close.bind("<Leave>", lambda e: close.config(bg=BG, fg=FG))
        close.bind("<Button-1>", lambda e: self.app.quit())

        # Tab-Leiste
        self.tabbar = tk.Frame(outer, bg=BG)
        self.tabbar.pack(fill="x", padx=self.px(10))
        tk.Frame(outer, bg=BORDER, height=1).pack(fill="x")

        # Scrollbarer Inhalt: Canvas mit Frame darin + schmale eigene Scrollleiste
        area = tk.Frame(outer, bg=BG)
        area.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(area, bg=BG, highlightthickness=0, bd=0, width=self.px(POPUP_WIDTH),
                                yscrollincrement=self.px(24))
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar = tk.Canvas(area, bg=BG, highlightthickness=0, bd=0, width=self.px(8))
        self.scrollbar.pack(side="right", fill="y")
        self.thumb = self.scrollbar.create_rectangle(0, 0, 0, 0, fill="#5a5a5a", width=0)
        self.inner = tk.Frame(self.canvas, bg=BG)
        self.inner_id = self.canvas.create_window(0, 0, window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.on_scroll)
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.inner_id, width=e.width))
        w.bind_all("<MouseWheel>", self.on_wheel)

        # Tooltip: ein Label im Popup selbst, das bei Bedarf über den Inhalt gelegt wird
        # (ein eigenes Fenster würde dem Popup den Fokus klauen und es schließen)
        self.tip = tk.Label(outer, bg=TIP_BG, fg=FG, font=("Segoe UI", 9), justify="left", anchor="w",
                            padx=self.px(8), pady=self.px(6),
                            highlightthickness=1, highlightbackground=TIP_BORDER)

        self.signature = None
        self.refresh()                           # zeigt erst die letzten bekannten Werte …
        round_corners(w)
        self.app.popup_opened()                  # … und fordert sofort eine frische volle Messung an

        w.bind("<Escape>", lambda e: self.close())
        w.bind("<FocusOut>", lambda e: self.root.after(80, self.close_if_unfocused))
        w.focus_force()

    def close_if_unfocused(self):
        try:
            unfocused = self.win is not None and self.win.focus_get() is None
        except (KeyError, tk.TclError):
            unfocused = True
        if unfocused:
            self.close()

    def close(self):
        self.cancel_tip()
        if self.win:
            self.app.popup_closed()              # ab jetzt wieder nur CPU und GPU lesen
            self.win.unbind_all("<MouseWheel>")
            self.win.destroy()
            self.win = None
            self.closed_at = time.monotonic()

    def place(self):
        """Höhe an den Inhalt anpassen und unten rechts über der Taskleiste positionieren."""
        self.win.update_idletasks()
        area = work_area() or (0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight())
        content = self.inner.winfo_reqheight()
        chrome = self.win.winfo_reqheight() - self.canvas.winfo_reqheight()     # Kopfzeile, Tabs, Rahmen
        max_canvas = int((area[3] - area[1]) * MAX_HEIGHT_SHARE) - chrome
        self.canvas.configure(height=max(self.px(60), min(content, max_canvas)),
                              scrollregion=(0, 0, 0, content))
        self.win.update_idletasks()
        width, height = self.win.winfo_reqwidth(), self.win.winfo_reqheight()
        margin = self.px(12)
        self.win.geometry(f"+{area[2] - width - margin}+{area[3] - height - margin}")

    # --- Scrollen ---
    def on_scroll(self, first, last):
        first, last = float(first), float(last)
        height = self.scrollbar.winfo_height()
        if last - first >= 1:
            self.scrollbar.coords(self.thumb, 0, 0, 0, 0)            # alles sichtbar -> keine Leiste
        else:
            self.scrollbar.coords(self.thumb, self.px(2), first * height, self.px(6), last * height)

    def on_wheel(self, event):
        self.hide_tip()
        self.canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")

    # --- Tabs ---
    def build_tabs(self, tabs):
        for child in self.tabbar.winfo_children():
            child.destroy()
        for name in tabs:
            active = name == self.tab
            cell = tk.Frame(self.tabbar, bg=BG, cursor="hand2")
            cell.pack(side="left")
            label = tk.Label(cell, text=name, bg=BG, fg=FG if active else SUB, cursor="hand2",
                             font=("Segoe UI Semibold" if active else "Segoe UI", 9),
                             padx=self.px(7), pady=self.px(5))
            label.pack()
            tk.Frame(cell, bg=TAB_ACTIVE if active else BG, height=self.px(2)).pack(fill="x")
            for widget in (cell, label):
                widget.bind("<Button-1>", lambda e, n=name: self.switch_tab(n))
                if not active:
                    widget.bind("<Enter>", lambda e, l=label: l.config(bg=TAB_HOVER))
                    widget.bind("<Leave>", lambda e, l=label: l.config(bg=BG))

    def switch_tab(self, name):
        if name != self.tab:
            self.tab = name
            self.signature = None                # erzwingt Neuaufbau
            self.canvas.yview_moveto(0)
            self.refresh()

    # --- Tooltip ---
    def add_tooltip(self, widgets, line, anchor, text):
        """Zeigt `text` an, wenn die Maus kurz über einem der `widgets` verweilt."""
        def enter(_event):
            self.cancel_tip()
            self.tip_job = self.root.after(400, lambda: self.show_tip(line, anchor, text))

        def leave(_event):
            self.cancel_tip()
            # kurz warten: beim Wechsel zwischen Zeile und Beschriftung kommt sofort wieder ein enter
            self.tip_job = self.root.after(100, self.hide_tip)

        for widget in widgets:
            widget.bind("<Enter>", enter, add="+")
            widget.bind("<Leave>", leave, add="+")

    def show_tip(self, line, anchor, text):
        if not self.win:
            return
        width = self.outer.winfo_width() - 2 * self.px(16)
        self.tip.config(text=text, wraplength=width - 2 * self.px(9))
        self.tip.update_idletasks()
        height = self.tip.winfo_reqheight()

        # unter der Zeile anzeigen – oder darüber, wenn unten kein Platz mehr ist
        top = self.outer.winfo_rooty()
        y = anchor.winfo_rooty() - top + anchor.winfo_height() + self.px(4)
        if y + height > self.outer.winfo_height() - self.px(4):
            y = max(0, line.winfo_rooty() - top - height - self.px(4))
        self.tip.place(x=self.px(16), y=y, width=width)
        self.tip.lift()

    def hide_tip(self):
        self.tip_job = None
        if self.win:
            self.tip.place_forget()

    def cancel_tip(self):
        if self.tip_job:
            self.root.after_cancel(self.tip_job)
            self.tip_job = None

    # --- Inhalt ---
    def group_header(self, parent, text, color, first):
        head = tk.Frame(parent, bg=BG)
        head.pack(fill="x", pady=(0 if first else self.px(14), self.px(2)))
        tk.Frame(head, bg=hex_color(color), width=self.px(4), height=self.px(16)).pack(side="left", padx=(0, self.px(8)))
        tk.Label(head, text=text, bg=BG, fg=FG, font=("Segoe UI Semibold", 10), justify="left",
                 wraplength=self.px(POPUP_WIDTH - 60)).pack(side="left")

    def add_row(self, parent, sensor, accent, big=False, in_icon=False):
        line = tk.Frame(parent, bg=BG)
        line.pack(fill="x", pady=(self.px(4) if big else self.px(2), 0))
        name_label = tk.Label(line, text=sensor["name"], bg=BG, fg=FG if in_icon else SUB,
                              font=("Segoe UI Semibold" if in_icon else "Segoe UI", 9))
        name_label.pack(side="left")
        hover = [line, name_label]
        if in_icon:
            marker = tk.Label(line, text="im Icon", bg=BG, fg=hex_color(accent), font=("Segoe UI", 8))
            marker.pack(side="left", padx=(self.px(6), 0))
            hover.append(marker)
        value_label = tk.Label(line, bg=BG, fg=FG, font=("Segoe UI Semibold", 11 if big else 9))
        value_label.pack(side="right")
        hover.append(value_label)

        bar = fill = None
        if sensor["type"] in BAR_TYPES:
            bar = tk.Canvas(parent, height=self.px(4 if big else 3), bg=TRACK, highlightthickness=0, bd=0)
            bar.pack(fill="x", pady=(self.px(2), 0))
            fill = bar.create_rectangle(0, 0, 0, self.px(4), width=0)
            hover.append(bar)

        self.add_tooltip(hover, line, bar or line, explain(sensor["type"], sensor["name"]))
        self.rows[sensor["id"]] = (value_label, bar, fill, accent)

    def build_body(self, snap, tabs):
        self.cancel_tip()
        self.tip.place_forget()
        self.build_tabs(tabs)
        for child in self.inner.winfo_children():
            child.destroy()
        self.rows = {}

        body = tk.Frame(self.inner, bg=BG)
        body.pack(fill="both", expand=True, padx=self.px(16), pady=(self.px(12), self.px(14)))
        groups = tab_content(snap, self.tab)

        if not groups:
            text = ("Lade Sensordaten …" if snap.get("loading")
                    else "Keine Sensordaten.\nLäuft das Programm mit Adminrechten?")
            tk.Label(body, text=text, bg=BG, fg=SUB, font=("Segoe UI", 9), justify="left").pack(anchor="w")
            return

        if self.tab == "Temperaturen":                 # Übersicht wie bisher: CPU und GPU mit großen Werten
            for i, hw in enumerate(groups):
                accent = STRIPE[hw["kind"]]
                self.group_header(body, f'{hw["kind"].upper()}  ·  {hw["name"]}', accent, i == 0)
                picked = snap[hw["kind"]]
                for s in hw["sensors"]:
                    in_icon = picked is not None and picked["sensor"] == s["id"]
                    self.add_row(body, s, accent, big=True, in_icon=in_icon)
            return

        accent = TAB_ACCENT.get(self.tab, TAB_ACCENT["Weitere"])
        for i, hw in enumerate(groups):
            self.group_header(body, hw["name"], accent, i == 0)
            for sensor_type, label in TYPE_LABELS.items():          # nach Sensortyp gruppiert
                sensors = [s for s in hw["sensors"] if s["type"] == sensor_type]
                if not sensors:
                    continue
                tk.Label(body, text=label.upper(), bg=BG, fg=SUB, font=("Segoe UI", 7)).pack(
                    anchor="w", pady=(self.px(8), 0))
                for s in sensors:
                    self.add_row(body, s, accent)

    def update_values(self, snap):
        for hw in tab_content(snap, self.tab):
            for s in hw["sensors"]:
                value_label, bar, fill, accent = self.rows[s["id"]]
                is_temp = s["type"] == "Temperature"
                color = hex_color(temp_color(s["value"])) if is_temp else FG
                value_label.config(text=fmt_value(s["type"], s["value"]), fg=color)
                if bar is not None:
                    share = max(0.0, min(s["value"], 100.0)) / 100
                    bar.coords(fill, 0, 0, bar.winfo_width() * share, self.px(4))
                    bar.itemconfig(fill, fill=color if is_temp else hex_color(accent))

    def refresh(self):
        """Wird aufgerufen, sobald neue Messwerte da sind (und beim Öffnen bzw. Tab-Wechsel)."""
        if not self.win:
            return
        snap = self.app.snapshot()
        tabs = available_tabs(snap)
        if tabs and self.tab not in tabs:
            self.tab = tabs[0]
        signature = (self.tab, tuple(tabs),
                     tuple((hw["id"], tuple(s["id"] for s in hw["sensors"])) for hw in tab_content(snap, self.tab)))
        if signature != self.signature:          # Tab oder Sensoren haben sich geändert -> Inhalt neu aufbauen
            self.build_body(snap, tabs)
            self.signature = signature
            self.place()
        self.update_values(snap)


# ---------- Programm ----------
class HardwareMonitorApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()                     # Hauptfenster unsichtbar, nur das Popup wird angezeigt
        self.popup = Popup(self)

        self.stop = threading.Event()
        self.wake = threading.Event()            # weckt den Mess-Thread vorzeitig (Fenster geöffnet, Rate geändert)
        self.popup_open = threading.Event()
        self.lock = threading.Lock()
        self.latest = EMPTY                      # letzte VOLLE Messung, nur fürs Fenster
        self.shown = {}                          # was gerade in den Icons steht -> nur bei Änderung neu zeichnen
        self.ui_queue = queue.Queue()            # Nachrichten aus den anderen Threads an tkinter
        self.settings = SETTINGS                 # dieselben Einstellungen wie überall im Skript
        self.order = list(self.settings["icon_order"])
        self.ready = {kind: threading.Event() for kind in self.order}
        self.current = {"cpu": None, "gpu": None}    # aktuelle Icon-Werte, für die Statusabfrage der GUI

        self.icons = {
            kind: pystray.Icon(f"hardware_monitor_{kind}", make_icon(kind, None), kind.upper(), self.make_menu())
            for kind in self.order
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

    # --- Fenster meldet sich ---
    def popup_opened(self):
        self.popup_open.set()
        self.wake.set()                          # sofort eine volle Messung machen

    def popup_closed(self):
        self.popup_open.clear()

    def snapshot(self):
        with self.lock:
            return self.latest

    # --- Hintergrund-Thread: misst und aktualisiert die Icons ---
    def measure(self, full):
        try:
            return collect(full)
        except Exception:
            logging.exception("Fehler beim Auslesen der Sensoren")
            return dict(EMPTY, loading=False)

    def update_icons(self, snap):
        for kind, icon in self.icons.items():
            info = snap[kind]
            value = info["value"] if info else None
            self.current[kind] = None if value is None else round(value, 1)
            text = "--" if value is None else f"{value:.0f}"
            if self.shown.get(kind) == text:
                continue                         # gleiche Zahl wie vorher -> nichts neu zeichnen
            self.shown[kind] = text
            icon.icon = make_icon(kind, value)
            shown = "–" if value is None else f"{text} °C"
            icon.title = f"{kind.upper()}: {shown}  ·  Klick für Details"

    def sensor_loop(self):
        """Fenster zu: alle `icon_interval` Sekunden nur CPU und GPU lesen.
        Fenster offen: alle `popup_interval` Sekunden alles lesen (die Icons bekommen die Werte mit)."""
        try:
            self.measure(full=True)              # einmal alles "anwärmen": die erste Messung liefert teils 0
            next_icon = next_full = 0.0
            while not self.stop.is_set():
                now = time.monotonic()
                popup_open = self.popup_open.is_set()

                if popup_open and now >= next_full:
                    snap = self.measure(full=True)
                    with self.lock:
                        self.latest = snap
                    self.ui_queue.put("data")    # Fenster neu zeichnen lassen
                    self.update_icons(snap)
                    next_full = now + self.settings["popup_interval"]
                    next_icon = now + self.settings["icon_interval"]
                elif now >= next_icon:
                    self.update_icons(self.measure(full=False))
                    next_icon = now + self.settings["icon_interval"]

                due = min(next_icon, next_full) if popup_open else next_icon
                self.wake.wait(max(0.05, due - time.monotonic()))
                if self.wake.is_set():           # Fenster geöffnet oder Rate geändert -> sofort neu planen
                    self.wake.clear()
                    next_icon = next_full = 0.0
        finally:
            pc.Close()

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
                server.settimeout(0.5)                   # regelmäßig nachsehen, ob beendet werden soll
            except OSError:
                server.close()
                server = None
                if not logged:                           # Port noch belegt (z. B. direkt nach Neustart) -> später nochmal
                    logging.warning("Port %s belegt – Fernsteuerung wird später erneut versucht", IPC_PORT)
                    logged = True
                self.stop.wait(2)
        if server is None:
            return
        with server:
            while not self.stop.is_set():
                try:
                    conn, _ = server.accept()
                except socket.timeout:
                    continue
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
                    "order": self.order}
        if command in ("reload", "quit"):
            self.ui_queue.put(command)
            return {"ok": True}
        return {"ok": False, "error": f"Unbekannter Befehl: {command}"}

    def reload_settings(self):
        """Die GUI hat Einstellungen geändert -> neu einlesen und überall übernehmen."""
        SETTINGS.update(load_settings())
        self.shown.clear()                       # Icons neu zeichnen (z. B. neue Farbgrenzen)
        for icon in self.icons.values():
            icon.update_menu()
        self.popup.signature = None              # Fenster neu aufbauen (ausgeblendete Werte)
        self.popup.refresh()
        self.wake.set()

    # --- tkinter-Seite ---
    def poll_queue(self):
        try:
            while True:
                message = self.ui_queue.get_nowait()
                if message == "toggle":
                    self.popup.toggle()
                elif message == "data":
                    self.popup.refresh()
                elif message == "reload":
                    self.reload_settings()
                elif message == "quit":
                    self.quit()
                    return
        except queue.Empty:
            pass
        self.root.after(100, self.poll_queue)

    def quit(self):
        self.stop.set()
        self.wake.set()                          # Mess-Thread nicht erst ausschlafen lassen
        self.popup.close()
        for icon in self.icons.values():
            icon.stop()
        self.root.quit()

    def run(self):
        # Icons nacheinander anmelden, damit die Reihenfolge in der Taskleiste immer gleich ist
        for kind in self.order:
            self.icons[kind].run_detached(setup=lambda ic, k=kind: (setattr(ic, "visible", True), self.ready[k].set()))
            self.ready[kind].wait(timeout=5)
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
