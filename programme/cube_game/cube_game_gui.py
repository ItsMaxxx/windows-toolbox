"""
Cube Game page in the toolbox GUI (building blocks from toolbox/base.py).

A play button and the game's settings: the game itself (cube_game.py) runs as a separate program with its own window
– see README.md in this folder.

The settings live in daten\\cube_game.json under "settings" – the same file holds the game's progress (cores, skill
tree, …), which only the game writes. So this page reads and writes just "settings" (load/save below), and the game
leaves them alone (game/profile.py).
All texts live in i18n.json – only their IDs are here: t("page.…") (see toolbox\\i18n.py).
"""

import json
import subprocess
from pathlib import Path

import daten
import i18n
import winutil
from base import MUTED, Button, Buttons, Section, Switch, Text, ToolPage

FOLDER = Path(__file__).resolve().parent
ID_CARD = json.loads((FOLDER / "programm.json").read_text(encoding="utf-8"))
t = i18n.Texte(FOLDER / "i18n.json")

# Created by Setup.exe (like the Hardware Monitor's): the launcher CubeGame.exe – Task Manager then shows "Cube Game"
# instead of "Python". If it's missing, the page starts the script directly with the toolbox's Python.
LAUNCHER = FOLDER / ID_CARD["starter"]
SCRIPT = FOLDER / ID_CARD["skript"]
IMAGES = FOLDER / "assets" / "images"           # picture files for enemies (game/skins/skin.py)


class CubeGamePage(ToolPage):
    defaults = {"key_display": True}            # like SETTINGS in game/profile.py

    def layout(self):
        return [
            Section(t("page.play"),
                    Text(t("page.controls"), color=MUTED),
                    Buttons(Button(t("page.play.button"), self.play, ziel=self.play_target))),
            Section(t("page.settings"),
                    Switch(t("page.key_display"), key="key_display"),
                    Text(t("page.key_display.hint"), color=MUTED)),
            Section(t("page.skins"),
                    Text(t("page.skins.hint"), color=MUTED),
                    Buttons(Button(t("page.skins.open"), lambda: self.open(IMAGES), width=170, style="grau",
                                   ziel=IMAGES))),
            Section(t("page.advanced"),
                    Buttons(Button(t("page.open_folder"), lambda: self.open(FOLDER), width=150, style="grau",
                                   ziel=FOLDER))),
        ]

    def load(self):
        """Only the "settings" part of daten\\cube_game.json."""
        stored = daten.lesen(self.settings_file, {}).get("settings")
        values = dict(self.defaults)
        if isinstance(stored, dict):
            values.update({key: stored[key] for key in values if isinstance(stored.get(key), type(values[key]))})
        return values

    def save(self):
        """Writes the settings into "settings" of daten\\cube_game.json – the rest (the game's progress) is read fresh
        right before, so it's kept exactly as the game last saved it."""
        settings = self.data
        self.data = daten.lesen(self.settings_file, {})
        self.data["settings"] = dict(settings)
        try:
            super().save()
        finally:
            self.data = settings

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


SEITE = CubeGamePage
