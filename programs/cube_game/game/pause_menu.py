"""
The menu that opens with Esc during the game: Resume, Game menu (leaves the run – collected cores are kept), Quit.
The game is paused while it's open, and the window shows only this menu (SIZE is the window size then).
"""

from engine.button import Button
from engine.menu import Menu
from engine.ui import draw_panel, draw_text
from game import settings

SIZE = (340, 300)


class PauseMenu:
    def __init__(self, resume, game_menu, quit_game):
        self.menu = Menu([Button("Resume", resume), Button("Game menu", game_menu), Button("Quit", quit_game)])

    def open(self):
        self.menu.selected = 0                  # always start on "Resume"

    def handle_event(self, event):
        self.menu.handle_event(event)

    def draw(self, surface):
        panel = surface.get_rect()
        draw_panel(surface, panel, radius=0)
        draw_text(surface, "PAUSED", 44, settings.TEXT, midtop=(panel.centerx, panel.top + 26))
        self.menu.draw(surface, (panel.centerx, panel.top + 90))
