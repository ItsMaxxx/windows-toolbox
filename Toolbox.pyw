"""Doppelklick startet die Toolbox-GUI (.pyw = ohne Konsolenfenster)."""

import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).resolve().parent / "src" / "gui" / "toolbox.py"), run_name="__main__")
