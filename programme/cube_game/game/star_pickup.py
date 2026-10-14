"""
A star dropped by a killed enemy – the shop's currency. Fly over it to collect it; close to the ship it gets pulled in
(the closer, the faster). It stays where it fell until it's collected, also outside the window.
"""

import math

import pygame

from engine import Entity
from game.icons import STAR_COLOR, draw_star

SIZE = 16                   # hitbox
MAGNET_RADIUS = 130         # pixels around the ship in which stars get pulled in …
MAGNET_SPEED = 260          # … at this speed at the edge of the radius, three times as fast right at the ship


class StarPickup(Entity):
    currency = "stars"          # what collecting it gives

    def __init__(self, position):
        super().__init__(0, 0, SIZE, SIZE, STAR_COLOR)
        self.rect.center = position
        self.age = 0.0

    def update(self, dt, ship):
        self.age += dt
        to_ship = pygame.Vector2(ship.rect.center) - self.rect.center
        distance = to_ship.length()
        if 0 < distance < MAGNET_RADIUS:
            pull = MAGNET_SPEED * (1 + 2 * (1 - distance / MAGNET_RADIUS))
            self.rect.move_ip(to_ship / distance * min(pull * dt, distance))

    def draw(self, surface, offset):
        bob = math.sin(self.age * 5) * 2                # floats up and down a little
        center = pygame.Vector2(self.rect.center) - offset + (0, bob)
        draw_star(surface, center, SIZE / 2 + 1, self.color)
