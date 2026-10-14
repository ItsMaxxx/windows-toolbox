"""Carrier: a big teal square with a dark hangar in the middle that grows until the next critter comes out."""

import pygame

from game.skins.skin import Skin

HANGAR_COLOR = (15, 70, 55)


class CarrierSkin(Skin):
    color = (40, 190, 150)

    def draw_above(self, surface, enemy, rect):
        side = enemy.size * 0.6 * enemy.hangar_progress
        hangar = pygame.Rect(0, 0, side, side)
        hangar.center = rect.center
        pygame.draw.rect(surface, HANGAR_COLOR, hangar)
