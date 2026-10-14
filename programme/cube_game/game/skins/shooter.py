"""Shooter: a purple square with a barrel pointing at the ship."""

import pygame

from game.skins.skin import Skin

BARREL_COLOR = (220, 160, 255)


class ShooterSkin(Skin):
    color = (160, 60, 230)

    def draw_below(self, surface, enemy, rect):
        start = pygame.Vector2(rect.center)
        pygame.draw.line(surface, BARREL_COLOR, start, start + enemy.aim * enemy.size * 1.15, 6)
