"""
An artillery strike: a spot on the ground that gets hit after a delay. Fired by the Artillery enemy at the ship's
position. While it's on its way, a red circle fills up (game/effects/target_marker.py); when it's full, update()
returns True once – the scene then hurts the ship if it's in the circle and shows the blast
(game/effects/artillery_blast.py).
"""

import pygame

from game.effects.target_marker import draw_target_marker


class ArtilleryStrike:
    def __init__(self, center, radius, delay, damage):
        self.center = pygame.Vector2(center)
        self.radius = radius
        self.delay = delay              # seconds until it lands
        self.damage = damage
        self.age = 0.0
        self.landed = False

    @property
    def progress(self):
        """0 just fired, 1 lands now."""
        return min(1.0, self.age / self.delay) if self.delay > 0 else 1.0

    def update(self, dt):
        """True in the tick it lands (only once)."""
        self.age += dt
        if self.landed or self.age < self.delay:
            return False
        self.landed = True
        return True

    def hits(self, rect):
        """True if any part of rect is inside the circle."""
        nearest = (min(max(self.center.x, rect.left), rect.right), min(max(self.center.y, rect.top), rect.bottom))
        return self.center.distance_to(nearest) <= self.radius

    def draw(self, surface, offset):
        draw_target_marker(surface, self.center - offset, self.radius, self.progress, self.age)
