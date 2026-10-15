# Cube Game – entry point: starts the engine with the main menu.
# Folder layout and roadmap: README.md in this folder.
#
# Run for testing (error messages then show up in the terminal):
#     runtime\python.exe programs\cube_game\cube_game.py

import ctypes
import sys
from pathlib import Path

# The toolbox's Python (runtime\, embedded) does not put the script's folder on sys.path by itself – without this line
# "import engine" and "import game" would not be found.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from engine import Engine  # noqa: E402
from game import settings  # noqa: E402
from game.main_menu_scene import MainMenuScene  # noqa: E402


def main():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)      # sharp window instead of blurry upscaling by Windows
    except (AttributeError, OSError):
        pass
    scene = MainMenuScene()
    engine = Engine(settings.TITLE, scene.window_rect())
    engine.run(scene)


if __name__ == "__main__":
    main()
