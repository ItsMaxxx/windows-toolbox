"""
Liste aller Programme in der Toolbox.

Neues Programm hinzufügen:
  1. Seite als Unterklasse von ToolPage schreiben (siehe hardware_monitor.py als Beispiel)
  2. Hier unten eine Zeile in TOOLS ergänzen
In der Seitenleiste wird automatisch alphabetisch sortiert.
"""

from .base import ToolInfo
from .platzhalter import PlatzhalterPage
from .hardware_monitor import HardwareMonitorPage

CATEGORIES = ["Allgemein", "Werkzeuge", "Medien", "Netzwerk"]     # Tabs oben, in dieser Reihenfolge

TOOLS = [
    ToolInfo("hardware_monitor", "Hardware-Monitor", "Allgemein",
             "CPU- und GPU-Temperatur in der Taskleiste; ein Klick aufs Icon zeigt fast alle Hardware-Werte "
             "(hardware_monitor).",
             HardwareMonitorPage),
    ToolInfo("xxx-werkzeuge", "XXX", "Werkzeuge", "Platzhalter", PlatzhalterPage),
    ToolInfo("xxx-medien", "XXX", "Medien", "Platzhalter", PlatzhalterPage),
    ToolInfo("xxx-netzwerk", "XXX", "Netzwerk", "Platzhalter", PlatzhalterPage),
]
