"""
A core dropped by a killed enemy (rarely) – the meta currency, kept between runs and spent in the game menu's skill
tree. Behaves like a star (pulled in close to the ship, stays until collected), only looks different.
"""

import math

import pygame

from game.icons import CORE_COLOR, draw_core
from game.star_pickup import SIZE, StarPickup


class CorePickup(StarPickup):
    currency = "cores"

    def __init__(self, position):
        super().__init__(position)
        self.color = CORE_COLOR

    def draw(self, surface, offset):
        bob = math.sin(self.age * 5) * 2
        center = pygame.Vector2(self.rect.center) - offset + (0, bob)
        glow = 0.5 + 0.5 * math.sin(self.age * 8)               # a pulsing ring, so it stands out among the stars
        ring = [round(channel * (0.25 + 0.35 * glow)) for channel in self.color]
        pygame.draw.circle(surface, ring, center, SIZE * 0.95, 2)
        draw_core(surface, center, SIZE / 2 + 1, self.color)
