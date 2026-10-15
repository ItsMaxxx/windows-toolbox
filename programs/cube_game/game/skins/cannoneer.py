"""Cannoneer: a big dark purple square (with the tier 2 frame) and a short, very thick barrel."""

import pygame

from game.skins.skin import Skin

BARREL_COLOR = (190, 120, 240)


class CannoneerSkin(Skin):
    color = (120, 40, 180)

    def draw_below(self, surface, enemy, rect):
        start = pygame.Vector2(rect.center)
        pygame.draw.line(surface, BARREL_COLOR, start, start + enemy.aim * enemy.size * 0.95, 16)
