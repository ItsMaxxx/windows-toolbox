"""
Der Teil von Einrichten.cmd, der Adminrechte braucht. einrichten.ps1 startet ihn nach einer UAC-Abfrage mit dem
Python aus runtime\\ – und nur mit den Schritten, die noch fehlen:

  --pawnio     PawnIO installieren (Treiber für CPU- und Mainboard-Sensoren, über winget)
  --aufgabe    geplante Aufgabe HardwareMonitor auf diesen Ordner einrichten (Autostart beim Anmelden)

Exitcode 0 = alles geklappt.
"""

import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True                   # keine __pycache__-Ordner anlegen
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "gui"))
import winutil  # noqa: E402

AUFGABE = "HardwareMonitor"                      # wie DEFAULT_TASK in hardware_monitor_gui.py
SCRIPT = ROOT / "src" / "hardware_monitor" / "hardware_monitor.py"
EXE = ROOT / "runtime" / "HardwareMonitor.exe"


def pawnio_installieren():
    print("PawnIO wird installiert …")
    try:
        ergebnis = subprocess.run(["winget", "install", "--id", "namazso.PawnIO", "--exact",
                                   "--accept-package-agreements", "--accept-source-agreements"])
    except OSError:
        print("FEHLER: winget nicht gefunden. PawnIO bitte von Hand installieren (siehe README).")
        return False
    if ergebnis.returncode != 0:
        print(f"FEHLER: winget meldet Code {ergebnis.returncode}.")
        return False
    return True


def aufgabe_einrichten():
    print(f"Aufgabe „{AUFGABE}“ wird eingerichtet …")
    vorher = winutil.task_info(AUFGABE)
    ergebnis = winutil.powershell(winutil.task_command(AUFGABE, SCRIPT, EXE))
    if ergebnis is None or ergebnis.returncode != 0:
        print("FEHLER:", ergebnis.stderr.strip() if ergebnis else "PowerShell nicht gefunden")
        return False
    if vorher and vorher.get("state") == "Disabled":     # Autostart war bewusst aus -> so lassen
        winutil.set_task_enabled(AUFGABE, False)
        print("   (Autostart bleibt ausgeschaltet, wie vorher)")
    return True


def main():
    ok = True
    if "--pawnio" in sys.argv:
        ok = pawnio_installieren() and ok
    if "--aufgabe" in sys.argv:
        ok = aufgabe_einrichten() and ok
    if not ok:
        input("\nEnter drücken zum Schließen …")     # Fenster offen lassen, damit man den Fehler lesen kann
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
