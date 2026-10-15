"""
Last Bastion page in the toolbox GUI (building blocks from toolbox/base.py).

The game has its own git repository, separate from the toolbox – this page only knows where it is on this PC: the
folder chosen here (data\\last_bastion.json, "game_folder"), otherwise last-bastion next to the toolbox folder.
From there it opens DESIGN.md and starts dist\\LastBastion.exe (the agreement with the game repo, see its DESIGN.md,
section 12.7). The page is all there is in the toolbox – no script, no starter.
All texts live in i18n.json – only their IDs are here: t("page.…") (see toolbox\\i18n.py).
"""

import subprocess
from pathlib import Path
from tkinter import filedialog

import i18n
from base import BAD, GOOD, MUTED, Button, Buttons, Section, Text, ToolPage

FOLDER = Path(__file__).resolve().parent
DEFAULT_GAME_FOLDER = FOLDER.parents[2] / "last-bastion"     # next to the toolbox folder, e.g. E:\Software\last-bastion
t = i18n.Texts(FOLDER / "i18n.json")

# Paths inside the game repo – keep them in line with its DESIGN.md (12.7)
DESIGN = "DESIGN.md"
GAME_EXE = Path("dist") / "LastBastion.exe"


class LastBastionPage(ToolPage):
    defaults = {"game_folder": ""}          # empty = DEFAULT_GAME_FOLDER

    def layout(self):
        return [
            Section(t("page.folder"),
                    Text(t("page.folder.hint"), color=MUTED),
                    Text(name="folder_status", color=MUTED),
                    Buttons(Button(t("page.folder.choose"), self.choose_folder, width=170),
                            Button(t("page.open_folder"), lambda: self.open(self.game_folder()), width=150,
                                   style="gray", target=self.game_folder))),
            Section(t("page.design"),
                    Text(t("page.design.hint"), color=MUTED),
                    Buttons(Button(t("page.design.open"), lambda: self.open(self.game_folder() / DESIGN), width=190,
                                   target=lambda: self.game_folder() / DESIGN))),
            Section(t("page.play"),
                    Text(t("page.play.hint"), color=MUTED),
                    Buttons(Button(t("page.play.button"), self.play, style="gray",
                                   target=lambda: self.game_folder() / GAME_EXE))),
        ]

    def game_folder(self):
        chosen = self.data.get("game_folder")
        return Path(chosen) if chosen else DEFAULT_GAME_FOLDER

    def refresh(self, *keys):
        super().refresh(*keys)
        if "folder_status" in self.w:
            self.show_status()

    def show_status(self):
        """Below the hint: where the game is – or that it isn't there."""
        folder = self.game_folder()
        if not folder.is_dir():
            text, color = t("page.folder.missing", path=folder), BAD
        elif not (folder / GAME_EXE).exists():
            text, color = t("page.folder.not_built", path=folder), MUTED
        else:
            text, color = t("page.folder.ok", path=folder), GOOD
        self.w["folder_status"].configure(text=text, text_color=color)

    def choose_folder(self):
        start = self.game_folder() if self.game_folder().is_dir() else FOLDER.parents[2]
        chosen = filedialog.askdirectory(parent=self.winfo_toplevel(), initialdir=str(start),
                                         title=t("page.folder.choose"))
        if chosen:
            # The default folder is not saved as a path – the page then still finds it after moving both folders
            self.set("game_folder", "" if Path(chosen) == DEFAULT_GAME_FOLDER else str(Path(chosen)))

    def play(self):
        exe = self.game_folder() / GAME_EXE
        if not exe.exists():
            self.app.toast(t("page.not_built"), error=True)
            return
        try:
            subprocess.Popen([str(exe)], cwd=str(exe.parent))
        except OSError:
            self.app.toast(t("page.start_failed"), error=True)


PAGE = LastBastionPage
