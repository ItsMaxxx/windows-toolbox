"""
Wo gespeicherte Daten liegen: im Ordner daten\\ im Hauptordner – getrennt vom Code und von runtime\\.

    daten\\toolbox.json              Einstellungen der Toolbox selbst
    daten\\<programm>.json           eine Datei pro Programm, z. B. hardware_monitor.json
    daten\\logs\\<programm>.log       Fehler und Hinweise (pythonw hat keine Konsole)

Zum Sichern oder Mitnehmen reicht daten\\. Programmseiten bekommen ihre Datei automatisch (ToolPage.settings_file),
eigenständige Programme holen sie mit daten.einstellungen("<programm>"). Gelesen und geschrieben wird überall mit
lesen() und schreiben().
"""

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATEN_DIR = ROOT / "daten"
LOG_DIR = DATEN_DIR / "logs"


def einstellungen(programm):
    """daten\\<programm>.json – z. B. einstellungen("toolbox") oder einstellungen("hardware_monitor")."""
    DATEN_DIR.mkdir(parents=True, exist_ok=True)
    return DATEN_DIR / f"{programm}.json"


def log(programm):
    """daten\\logs\\<programm>.log"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    return LOG_DIR / f"{programm}.log"


def lesen(datei, startwerte):
    """Startwerte, überschrieben mit dem, was in datei steht. Unbekannte Schlüssel bleiben erhalten, ob die Werte
    gültig sind, prüft der Aufrufer. Fehlt die Datei oder ist sie kaputt, gibt es einfach die Startwerte."""
    daten = copy.deepcopy(startwerte)
    try:
        gespeichert = json.loads(datei.read_text(encoding="utf-8"))
        if isinstance(gespeichert, dict):
            daten.update(gespeichert)
    except (OSError, ValueError):
        pass
    return daten


def schreiben(datei, daten):
    """Speichert daten als lesbares JSON. Wirft OSError, wenn es nicht klappt."""
    datei.write_text(json.dumps(daten, indent=2, ensure_ascii=False), encoding="utf-8")
