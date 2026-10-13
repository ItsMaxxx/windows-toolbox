"""
Was hardware_monitor.py und seine Seite in der Toolbox (hardware_monitor_gui.py) gemeinsam brauchen: Startwerte,
erlaubte Werte, Laden und Speichern von daten\\hardware_monitor.json, Port und Name der Aufgabe – und t, die Texte
aus i18n.json (siehe toolbox\\i18n.py).

Eigene Datei, weil die Toolbox hardware_monitor.py nicht importieren kann – das lädt beim Import LibreHardwareMonitor.
Port und Aufgabe stehen in programm.json, weil auch setup\\setup.ps1 sie braucht.
"""

import json
import re
import sys
from pathlib import Path

ORDNER = Path(__file__).resolve().parent
sys.path.append(str(ORDNER.parents[1] / "toolbox"))     # daten.py (gemeinsam mit der Toolbox)
import daten  # noqa: E402
import i18n  # noqa: E402

AUSWEIS = json.loads((ORDNER / "programm.json").read_text(encoding="utf-8"))
IPC_PORT = AUSWEIS["port"]             # lokale Fernsteuerung durch die Toolbox (nur von diesem PC aus erreichbar)
AUFGABE = AUSWEIS["aufgabe"]           # geplante Aufgabe, die den Monitor beim Anmelden mit Adminrechten startet
SETTINGS_FILE = daten.einstellungen(AUSWEIS["id"])
LOG_FILE = daten.log(AUSWEIS["id"])
t = i18n.Texte(ORDNER / "i18n.json")   # alle Texte des Hardware-Monitors: t("id") in der gewählten Sprache

# Auswahl im Rechtsklick-Menü und in der Toolbox (Sekunden)
ICON_RATES = (1, 2, 5, 10)      # Taskleisten-Icons (liest nur CPU und GPU)
POPUP_RATES = (0.5, 1, 2, 5)    # geöffnetes Fenster (liest die Geräte des gewählten Tabs)
EFFIZIENZ = ("auto", "an", "aus")

# Startwerte. Geändert wird über das Rechtsklick-Menü oder die Toolbox; beides landet in daten\hardware_monitor.json.
DEFAULT_SETTINGS = {
    "icon_interval": 2,
    "popup_interval": 1,
    "icon_order": ["cpu", "gpu"],    # Reihenfolge in der Taskleiste (wirkt nach Neustart des Programms)
    "cpu_sensor": "auto",            # "auto" = erster vorhandener aus CPU_SENSORS, sonst ein Sensorname
    "gpu_sensor": "auto",
    # Ampelfarbe der Temperaturen: ab warn gelb, ab hot rot – getrennt, weil CPUs unter Last deutlich heißer werden
    # dürfen (Ryzen und Intel drosseln sich erst bei etwa 90–100 °C, Grafikkarten meist schon ab etwa 83 °C).
    "cpu_warn_temp": 75,
    "cpu_hot_temp": 90,
    "gpu_warn_temp": 70,
    "gpu_hot_temp": 83,
    "window": "",                    # Größe und Position des Detailfensters, z. B. "480x640+1420+380" (merkt es sich selbst)
    "effizienzmodus": "auto",        # "auto" = nur bei geschlossenem Fenster, "an" = immer, "aus" = nie
}


def load_settings():
    """Liest die Einstellungen; alles Fehlende oder Ungültige bekommt den Startwert."""
    s = daten.lesen(SETTINGS_FILE, DEFAULT_SETTINGS)
    start = DEFAULT_SETTINGS
    if s["icon_interval"] not in ICON_RATES:
        s["icon_interval"] = start["icon_interval"]
    if s["popup_interval"] not in POPUP_RATES:
        s["popup_interval"] = start["popup_interval"]
    if not isinstance(s["icon_order"], list) or sorted(s["icon_order"]) != ["cpu", "gpu"]:
        s["icon_order"] = list(start["icon_order"])
    for key in ("cpu_sensor", "gpu_sensor"):
        s[key] = s[key].strip() if isinstance(s[key], str) and s[key].strip() else start[key]
    for kind in ("cpu", "gpu"):
        warn, hot = s[f"{kind}_warn_temp"], s[f"{kind}_hot_temp"]
        if not (isinstance(warn, (int, float)) and isinstance(hot, (int, float)) and 20 <= warn < hot <= 120):
            s[f"{kind}_warn_temp"], s[f"{kind}_hot_temp"] = start[f"{kind}_warn_temp"], start[f"{kind}_hot_temp"]
    s.pop("warn_temp", None)                     # früher eine Ampel für beide – ersetzt durch die Werte oben
    s.pop("hot_temp", None)
    if not (isinstance(s["window"], str) and re.fullmatch(r"\d+x\d+\+-?\d+\+-?\d+", s["window"])):
        s["window"] = start["window"]
    if s["effizienzmodus"] not in EFFIZIENZ:
        s["effizienzmodus"] = start["effizienzmodus"]
    return s


def save_settings(settings):
    """Speichert die Einstellungen. Wirft OSError, wenn es nicht klappt."""
    daten.schreiben(SETTINGS_FILE, settings)
