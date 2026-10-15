"""
The main menu shown at start: title, a ship that looks at the mouse, Play (leads to the game menu) and Quit.
"""

import pygame

from engine import Scene
from engine.button import Button
from engine.desktop import work_area
from engine.menu import Menu
from engine.ui import draw_text
from game import settings, ship_data
from game.ship_shape import draw_ship


class MainMenuScene(Scene):
    def __init__(self):
        super().__init__()
        self.rect = pygame.Rect((0, 0), settings.MENU_WINDOW_SIZE)
        self.rect.center = work_area().center
        self.menu = Menu([Button("Play", self.play), Button("Quit", self.quit)])

    def window_rect(self):
        return self.rect

    def enter(self):
        self.engine.grab_mouse(False)
        self.engine.move_window(self.rect)

    def play(self):
        from game.game_menu_scene import GameMenuScene     # imported here: the game menu also imports this file
        self.engine.change_scene(GameMenuScene())

    def quit(self):
        self.engine.stop()

    def handle_event(self, event):
        self.menu.handle_event(event)

    def draw(self, surface):
        area = surface.get_rect()
        surface.fill(settings.BACKGROUND)
        pygame.draw.rect(surface, settings.BORDER, area, settings.BORDER_WIDTH)

        ship_center = pygame.Vector2(area.centerx, 80)
        aim = pygame.Vector2(pygame.mouse.get_pos()) - ship_center
        if aim.length_squared() < 1:
            aim = pygame.Vector2(0, -1)
        draw_ship(surface, ship_center, aim.normalize(), 46, ship_data.current()["color"])

        draw_text(surface, "CUBE GAME", 80, settings.TEXT, midtop=(area.centerx, 130))
        draw_text(surface, "the window is the arena", 26, settings.TEXT_MUTED, midtop=(area.centerx, 192))
        self.menu.draw(surface, (area.centerx, 250))
        controls = draw_text(surface, "SHIFT dash  ·  SPACE rocket  ·  TAB inventory  ·  T shop  ·  ESC menu", 20,
                             settings.TEXT, alpha=settings.HINT_ALPHA * 2, midbottom=(area.centerx, area.bottom - 16))
        draw_text(surface, "W A S D move  ·  mouse aim  ·  left click shoot", 20, settings.TEXT,
                  alpha=settings.HINT_ALPHA * 2, midbottom=(area.centerx, controls.top - 4))
