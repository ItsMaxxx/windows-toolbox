"""
An explosion: a shockwave ring that expands to its radius and fades out – the rocket's blast, or an enemy dying.
Only the visual: damage and wall push happen once when it's created (PlayScene.explode).
"""

import pygame

DURATION = 0.35             # seconds until the ring has reached its full size and is gone


class Explosion:
    def __init__(self, position, radius, color):
        self.position = pygame.Vector2(position)
        self.radius = radius
        self.color = color
        self.age = 0.0

    @property
    def done(self):
        return self.age >= DURATION

    def update(self, dt):
        self.age += dt

    def draw(self, surface, offset):
        progress = min(self.age / DURATION, 1)
        radius = self.radius * (1 - (1 - progress) ** 3)        # fast at first, then slowing down
        fade = 1 - progress                                     # the background is black, so darker = more faded
        color = [round(channel * fade) for channel in self.color]
        width = max(1, round(10 * fade))
        center = self.position - offset
        if radius > width:
            pygame.draw.circle(surface, color, center, radius, width)
