"""
A laser beam: fired by the Laser enemy along the line it aimed. It starts at the Laser (and stays with it), goes in a
fixed direction far beyond the screen and is on for a moment (duration). Everything touching it in that time gets hurt
once: the ship (if the hit counts – it may still be invulnerable). The scene asks hits() every
tick; the beam remembers who it already hurt. If the Laser dies, the beam goes out.
"""

import pygame

LENGTH = 3000               # pixels – far enough to cross any screen
CORE_COLOR = (255, 255, 235)
FADE_FROM = 0.6             # the last part of its time it gets thinner


class LaserBeam:
    def __init__(self, source, width, duration, damage, color):
        """source: the enemy firing it (the beam starts at its centre)."""
        self.source = source
        self.direction = pygame.Vector2(source.aim)
        self.width = width
        self.duration = duration
        self.damage = damage
        self.color = color
        self.age = 0.0
        self.hurt = []              # what it has already hurt (the ship)

    @property
    def done(self):
        return self.age >= self.duration or not self.source.alive

    @property
    def line(self):
        start = self.source.center
        return start, start + self.direction * LENGTH

    def update(self, dt):
        self.age += dt

    def hits(self, rect):
        """True if the beam touches rect."""
        return bool(pygame.Rect(rect).inflate(self.width, self.width).clipline(*self.line))

    def draw(self, surface, offset):
        start, end = (point - offset for point in self.line)
        progress = self.age / self.duration if self.duration else 1.0
        fade = 1.0 if progress < FADE_FROM else max(0.2, (1 - progress) / (1 - FADE_FROM))
        pygame.draw.line(surface, self.color, start, end, max(2, round(self.width * fade)))
        pygame.draw.line(surface, CORE_COLOR, start, end, max(1, round(self.width * fade / 3)))
