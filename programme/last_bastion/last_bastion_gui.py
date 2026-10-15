"""
Last Bastion page in the toolbox GUI (building blocks from toolbox/base.py).

The design document (DESIGN.md), a play button and the folder. The game itself (last_bastion.py) runs as a separate
program with its own window – see README.md in this folder.
All texts live in i18n.json – only their IDs are here: t("page.…") (see toolbox\\i18n.py).
"""

import json
import subprocess
from pathlib import Path

import i18n
import winutil
from base import MUTED, Button, Buttons, Section, Text, ToolPage

FOLDER = Path(__file__).resolve().parent
ID_CARD = json.loads((FOLDER / "programm.json").read_text(encoding="utf-8"))
t = i18n.Texte(FOLDER / "i18n.json")

# Created by Setup.exe (like the Cube Game's): the launcher LastBastion.exe – Task Manager then shows "Last Bastion"
# instead of "Python". If it's missing, the page starts the script directly with the toolbox's Python.
LAUNCHER = FOLDER / ID_CARD["starter"]
SCRIPT = FOLDER / ID_CARD["skript"]
DESIGN = FOLDER / "DESIGN.md"


class LastBastionPage(ToolPage):

    def layout(self):
        return [
            Section(t("page.design"),
                    Text(t("page.design.hint"), color=MUTED),
                    Buttons(Button(t("page.design.open"), lambda: self.open(DESIGN), width=190, ziel=DESIGN))),
            Section(t("page.play"),
                    Text(t("page.play.hint"), color=MUTED),
                    Buttons(Button(t("page.play.button"), self.play, style="grau", ziel=self.play_target))),
            Section(t("page.advanced"),
                    Buttons(Button(t("page.open_folder"), lambda: self.open(FOLDER), width=150, style="grau",
                                   ziel=FOLDER))),
        ]

    def command(self):
        return [str(LAUNCHER)] if LAUNCHER.exists() else [winutil.pythonw_exe(), str(SCRIPT)]

    def play_target(self):
        """What "Play" starts – shown in the bottom left on hover."""
        return " ".join(self.command())

    def play(self):
        try:
            subprocess.Popen(self.command(), cwd=str(FOLDER))
        except OSError:
            self.app.toast(t("page.start_failed"), error=True)


SEITE = LastBastionPage
