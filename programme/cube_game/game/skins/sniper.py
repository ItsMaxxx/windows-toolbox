"""Sniper: a small yellow square with a thin barrel; while aiming, a laser – dim while it follows the ship, bright and
thicker once it's locked (the moment to dodge)."""

import pygame

from game.skins.skin import Skin

LASER_LENGTH = 3000
LASER_COLOR = (110, 95, 30)
LASER_LOCKED = (255, 235, 90)
BARREL_COLOR = (255, 245, 170)


class SniperSkin(Skin):
    color = (235, 205, 50)

    def draw_below(self, surface, enemy, rect):
        start = pygame.Vector2(rect.center)
        if enemy.aiming:
            color, width = (LASER_LOCKED, 2) if enemy.locked else (LASER_COLOR, 1)
            pygame.draw.line(surface, color, start, start + enemy.aim * LASER_LENGTH, width)
        pygame.draw.line(surface, BARREL_COLOR, start, start + enemy.aim * enemy.size * 1.1, 4)
