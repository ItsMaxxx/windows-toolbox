# Last Bastion – entry point. The concept is in DESIGN.md, folder layout and rules in README.md.
#
# Placeholder until the first prototype exists: shows a note and exits. Replace it with the game's start
# (like cube_game.py) – the launcher LastBastion.exe and the toolbox's "Play" button start this file.

import ctypes
import sys
from pathlib import Path

FOLDER = Path(__file__).resolve().parent
sys.path.insert(0, str(FOLDER.parents[1] / "toolbox"))     # i18n.py: texts in the language chosen in the toolbox

import i18n  # noqa: E402

t = i18n.Texte(FOLDER / "i18n.json")


def main():
    ctypes.windll.user32.MessageBoxW(None, t("placeholder.text"), t("placeholder.title"), 0x40)   # MB_ICONINFORMATION


if __name__ == "__main__":
    main()
