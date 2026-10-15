"""Charger: a big orange square; while winding up, a dark warning line shows where it's going to charge."""

import pygame

from game.skins.skin import Skin

WARNING_LENGTH = 160
WARNING_COLOR = (130, 70, 15)


class ChargerSkin(Skin):
    color = (255, 140, 30)

    def draw_below(self, surface, enemy, rect):
        if enemy.winding_up:
            start = pygame.Vector2(rect.center)
            pygame.draw.line(surface, WARNING_COLOR, start, start + enemy.charge_direction * WARNING_LENGTH, 4)
