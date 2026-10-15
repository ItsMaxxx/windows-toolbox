"""
A spark: a few short streaks flying apart and fading – a shot that a shield blocked. Only the visual.
"""

import random

import pygame

DURATION = 0.2              # seconds until it's gone
STREAKS = 6
REACH = (10, 22)            # pixels the streaks fly
COLOR = (255, 240, 200)


class Spark:
    def __init__(self, position, direction):
        """direction: where the streaks fly (roughly – the shot bounces back off the shield)."""
        self.position = pygame.Vector2(position)
        base = pygame.Vector2(direction) if pygame.Vector2(direction).length_squared() else pygame.Vector2(1, 0)
        self.streaks = [base.normalize().rotate(random.uniform(-70, 70)) * random.uniform(*REACH)
                        for _ in range(STREAKS)]
        self.age = 0.0

    @property
    def done(self):
        return self.age >= DURATION

    def update(self, dt):
        self.age += dt

    def draw(self, surface, offset):
        progress = min(self.age / DURATION, 1)
        fade = 1 - progress
        color = [round(channel * fade) for channel in COLOR]
        center = self.position - offset
        for streak in self.streaks:
            pygame.draw.line(surface, color, center + streak * progress * 0.4, center + streak * progress, 2)
