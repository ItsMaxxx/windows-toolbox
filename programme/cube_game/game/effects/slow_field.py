"""
Slow field: left behind by an exploding mine once "Slow field" is bought in the skill tree. For a few seconds every
enemy in it walks slower (the scene calls enemy.slow() each tick – see PlayScene.slow_enemies). It fades out towards
the end.

Drawing: the field and its edge are drawn once (engine/sprite_cache.py); every frame they're only copied onto a reused
layer, the drifting rings go on top, and the whole layer is made more see-through as it fades out.
"""

import math

import pygame

from engine.sprite_cache import PICTURES, scratch

FADE_TIME = 0.6             # seconds at the end in which it fades out
COLOR = (90, 170, 255)      # drawn see-through
RINGS = 3                   # rings drifting inwards
RING_TIME = 1.2             # seconds a ring takes from the edge to the middle


class SlowField:
    def __init__(self, position, radius, slow, duration):
        """slow: share slower, e.g. 0.2 = 20 % slower."""
        self.position = pygame.Vector2(position)
        self.radius = radius
        self.factor = max(0.0, 1 - slow)        # what the enemies' speed is multiplied with
        self.duration = duration
        self.age = 0.0

    @property
    def done(self):
        return self.age >= self.duration

    def update(self, dt):
        self.age += dt

    def covers(self, enemy):
        return enemy.distance_to(self.position) <= self.radius + enemy.size / 2

    def draw(self, surface, offset):
        fade = max(0.0, min(1.0, (self.duration - self.age) / FADE_TIME))
        size = math.ceil(self.radius * 2) + 2
        layer = scratch((size, size))
        center = (size / 2, size / 2)
        layer.blit(PICTURES.get(("slow field", size, self.radius), lambda: self.make_field(size)), (0, 0))
        for ring in range(RINGS):
            share = 1 - ((self.age / RING_TIME + ring / RINGS) % 1)        # 1 at the edge -> 0 in the middle
            if share * self.radius >= 2:
                pygame.draw.circle(layer, (*COLOR, round(90 * share)), center, share * self.radius, 1)
        layer.set_alpha(round(255 * fade))
        surface.blit(layer, self.position - offset - center)

    def make_field(self, size):
        """The field and its edge, without the rings and not faded yet."""
        field = pygame.Surface((size, size), pygame.SRCALPHA)
        center = (size / 2, size / 2)
        pygame.draw.circle(field, (*COLOR, 45), center, self.radius)
        pygame.draw.circle(field, (*COLOR, 150), center, self.radius, 2)
        return field
