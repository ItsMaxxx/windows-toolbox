"""
Seite des Cube Game in der Toolbox-GUI (Bausteine aus toolbox/base.py).

Nur ein Startknopf: Das Spiel selbst (cube_game.py) läuft als eigenes Programm mit eigenem Fenster und wird von Hand
geschrieben – siehe README.md in diesem Ordner. Einstellungen/Rekord kommen hierher, sobald das Spiel sie hat.
"""

import json
import subprocess
from pathlib import Path

import winutil
from base import MUTED, Button, Buttons, Section, Text, ToolPage

FOLDER = Path(__file__).resolve().parent
AUSWEIS = json.loads((FOLDER / "programm.json").read_text(encoding="utf-8"))

# Von Setup.exe angelegt (wie beim Hardware-Monitor): der Starter CubeGame.exe – im Task-Manager steht dann
# „Cube Game“ statt „Python“. Fehlt er noch, startet die Seite das Skript direkt mit dem Python der Toolbox.
STARTER = FOLDER / AUSWEIS["starter"]
SKRIPT = FOLDER / AUSWEIS["skript"]


class CubeGamePage(ToolPage):
    def layout(self):
        return [
            Section("Spielen",
                    Text("W A S D bewegen", color=MUTED),
                    Buttons(Button("Spielen", self.spielen, ziel=self.spiel_ziel))),
            Section("Erweitert",
                    Buttons(Button("Ordner öffnen", lambda: self.open(FOLDER), width=150, style="grau",
                                   ziel=FOLDER))),
        ]

    def befehl(self):
        return [str(STARTER)] if STARTER.exists() else [winutil.pythonw_exe(), str(SKRIPT)]

    def spiel_ziel(self):
        """Was „Spielen“ startet – steht beim Drüberfahren unten links."""
        return " ".join(self.befehl())

    def spielen(self):
        befehl = self.befehl()
        try:
            subprocess.Popen(befehl, cwd=str(FOLDER))
        except OSError:
            self.app.toast("Cube Game konnte nicht gestartet werden", error=True)


SEITE = CubeGamePage
