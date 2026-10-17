"""Commander: a gold square with a dark crown on it, and a thin ring showing how far its aura reaches."""

import pygame

from game.skins.skin import Skin

AURA_COLOR = (255, 200, 40)         # the outline of the enemies it buffs
RING_COLOR = (110, 85, 20)          # its aura's ring – dim, so it doesn't cover the fight


class CommanderSkin(Skin):
    color = (235, 180, 30)

    def draw_below(self, surface, enemy, rect):
        pygame.draw.circle(surface, RING_COLOR, rect.center, enemy.stat("aura_radius"), 1)

    def draw_above(self, surface, enemy, rect):
        """A small crown: three points on a band, in the body's dark shade."""
        dark = [round(channel * 0.35) for channel in self.color]
        width, height = rect.width * 0.6, rect.height * 0.35
        left, bottom = rect.centerx - width / 2, rect.centery + height / 2
        points = [(left, bottom), (left, bottom - height), (left + width * 0.25, bottom - height * 0.45),
                  (left + width * 0.5, bottom - height), (left + width * 0.75, bottom - height * 0.45),
                  (left + width, bottom - height), (left + width, bottom)]
        pygame.draw.polygon(surface, dark, points)
