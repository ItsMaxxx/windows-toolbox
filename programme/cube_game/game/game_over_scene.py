"""
The game over screen after the ship was crushed: how the run went (time, kills, cores) and Retry, Game menu, Main
menu. The window becomes a small panel where the arena was.

Input is ignored for a moment at the start: the player may still be clicking or holding a key from the run, and that
shouldn't press a button right away.
"""

from dataclasses import dataclass

import pygame

from engine import Scene
from engine.button import Button
from engine.desktop import Desktop
from engine.menu import Menu
from engine.ui import draw_panel, draw_text
from game import settings
from game.difficulty import DIFFICULTIES
from game.icons import draw_core

SIZE = (440, 490)
INPUT_DELAY = 0.6               # seconds before the buttons react
NEW_BEST_COLOR = (255, 215, 60)
LINE = (50, 50, 58)


@dataclass(frozen=True)
class RunResult:
    time: float                 # seconds survived
    kills: int
    cores: int                  # collected in this run
    difficulty: str             # key in DIFFICULTIES
    new_best: bool
    unlocked: str | None = None # level unlocked in this run
    cleared: bool = False       # the level's goal was reached in this run for the first time (only then it's shown)


def format_time(seconds):
    minutes, seconds = divmod(int(seconds), 60)
    return f"{minutes:02}:{seconds:02}"


class GameOverScene(Scene):
    def __init__(self, profile, result, center):
        super().__init__()
        self.profile = profile
        self.result = result
        self.rect = pygame.Rect((0, 0), SIZE)
        self.rect.center = center
        self.rect.clamp_ip(Desktop.current(settings.ALL_MONITORS).area_at(center))
        self.waited = 0.0
        self.menu = Menu([Button("Retry", self.retry), Button("Game menu", self.to_game_menu),
                          Button("Main menu", self.to_main_menu)])

    def enter(self):
        self.engine.grab_mouse(False)
        self.engine.move_window(self.rect)

    # --- actions ---

    def retry(self):
        from game.play_scene import PlayScene
        self.engine.change_scene(PlayScene(self.profile))

    def to_game_menu(self):
        from game.game_menu_scene import GameMenuScene
        self.engine.change_scene(GameMenuScene(self.profile))

    def to_main_menu(self):
        from game.main_menu_scene import MainMenuScene
        self.engine.change_scene(MainMenuScene())

    # --- events, logic, drawing ---

    def handle_event(self, event):
        if self.waited >= INPUT_DELAY:
            self.menu.handle_event(event)

    def update(self, dt):
        self.waited += dt

    def draw(self, surface):
        panel = surface.get_rect()
        draw_panel(surface, panel, radius=0)
        draw_text(surface, "GAME OVER", 56, settings.TEXT, midtop=(panel.centerx, 24))
        draw_text(surface, "crushed by the walls", 24, settings.TEXT_MUTED, midtop=(panel.centerx, 74))

        result = self.result
        rows = [("Time", format_time(result.time)), ("Kills", str(result.kills)),
                ("Cores", f"+{result.cores}   (total {self.profile.cores})"),
                ("Level", DIFFICULTIES[result.difficulty].name)]
        left, right, y = 60, panel.right - 60, 116
        for name, value in rows:
            draw_text(surface, name, 24, settings.TEXT_MUTED, topleft=(left, y))
            value_rect = draw_text(surface, value, 24, settings.TEXT, topright=(right, y))
            if name == "Cores":
                draw_core(surface, (value_rect.left - 12, value_rect.centery - 1), 8)
            pygame.draw.line(surface, LINE, (left, y + 22), (right, y + 22))
            y += 30
        y += 6
        parts = [f"{DIFFICULTIES[result.difficulty].name.upper()} CLEARED!"] if result.cleared else []
        if result.unlocked:
            parts.append(f"{DIFFICULTIES[result.unlocked].name.upper()} UNLOCKED!")
        if parts:
            y = draw_text(surface, "  ".join(parts), 28, NEW_BEST_COLOR, midtop=(panel.centerx, y)).bottom + 8
        if result.new_best:
            draw_text(surface, "NEW BEST TIME!", 28, NEW_BEST_COLOR, midtop=(panel.centerx, y))

        self.menu.draw(surface, (panel.centerx, 310))
