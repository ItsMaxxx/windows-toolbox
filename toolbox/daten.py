"""
Wo gespeicherte Daten liegen: im Ordner daten\\ im Hauptordner – getrennt vom Code und von runtime\\.

    daten\\toolbox.json              Einstellungen der Toolbox selbst
    daten\\<programm>.json           eine Datei pro Programm, z. B. hardware_monitor.json
    daten\\logs\\<programm>.log       Fehler und Hinweise (pythonw hat keine Konsole)

Zum Sichern oder Mitnehmen reicht daten\\. Programmseiten bekommen ihre Datei automatisch (ToolPage.settings_file),
eigenständige Programme holen sie mit daten.einstellungen("<programm>").
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATEN_DIR = ROOT / "daten"
LOG_DIR = DATEN_DIR / "logs"


def einstellungen(programm):
    """daten\\<programm>.json – z. B. einstellungen("toolbox") oder einstellungen("hardware_monitor")."""
    return _datei(DATEN_DIR / f"{programm}.json", programm, f"{programm}_settings.json")


def log(programm):
    """daten\\logs\\<programm>.log"""
    return _datei(LOG_DIR / f"{programm}.log", programm, f"{programm}.log")


def _datei(pfad, programm, alter_name):
    """Legt den Ordner an und zieht die Datei einmalig von ihrem alten Ort um, falls sie dort noch liegt:
    daten\\<alter_name> (Oktober 2026) bzw. src\\<ordner>\\<alter_name> (davor, neben dem Skript)."""
    ordner = "gui" if programm == "toolbox" else programm
    frueher = [DATEN_DIR / alter_name, ROOT / "src" / ordner / alter_name]
    try:
        pfad.parent.mkdir(parents=True, exist_ok=True)
        alt = next((f for f in frueher if f.exists()), None)
        if alt is not None and not pfad.exists():
            alt.replace(pfad)
    except OSError:
        pass        # z. B. ein Log, das ein noch laufendes altes Programm offen hält – klappt beim nächsten Start
    return pfad
