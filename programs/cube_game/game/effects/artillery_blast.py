"""
The artillery's blast – looks different from the ring of an Explosion: a white flash that fills the whole circle, then
a glowing fireball that shrinks and cools down from yellow over orange to dark red, debris flying outwards, and a
scorch ring that stays a moment longer.
Only the visual: the damage happens once when the strike lands (see artillery_strike.py).
"""

import random

import pygame

DURATION = 0.7              # seconds until everything is gone
FLASH_TIME = 0.06           # the white flash at the start
FIRE_COLORS = [(255, 255, 255), (255, 230, 120), (255, 140, 40), (190, 50, 20), (60, 20, 10)]   # hot to cool
DEBRIS_COUNT = 14
DEBRIS_REACH = (1.0, 2.2)   # how far debris flies, in blast radii (fast at first, then slowing down)
DEBRIS_SIZE = (3, 6)
SCORCH_COLOR = (90, 40, 20)


def fire_color(progress):
    """The colour at progress (0 = start, 1 = end), blended between FIRE_COLORS."""
    position = min(progress, 0.999) * (len(FIRE_COLORS) - 1)
    index, blend = int(position), position - int(position)
    start, end = FIRE_COLORS[index], FIRE_COLORS[index + 1]
    return [round(a + (b - a) * blend) for a, b in zip(start, end)]


class ArtilleryBlast:
    def __init__(self, position, radius):
        self.position = pygame.Vector2(position)
        self.radius = radius
        self.age = 0.0
        self.debris = [(pygame.Vector2(radius, 0).rotate(random.uniform(0, 360)) * random.uniform(*DEBRIS_REACH),
                        random.uniform(*DEBRIS_SIZE)) for _ in range(DEBRIS_COUNT)]

    @property
    def done(self):
        return self.age >= DURATION

    def update(self, dt):
        self.age += dt

    def draw(self, surface, offset):
        center = self.position - offset
        progress = min(self.age / DURATION, 1)
        # scorch ring at the circle's edge, fading out over the whole time
        scorch = [round(channel * (1 - progress)) for channel in SCORCH_COLOR]
        pygame.draw.circle(surface, scorch, center, self.radius, 3)
        if self.age < FLASH_TIME:
            pygame.draw.circle(surface, FIRE_COLORS[0], center, self.radius)
            return
        # fireball: starts as big as the circle, shrinks fast at first
        fire = (self.age - FLASH_TIME) / (DURATION - FLASH_TIME)
        size = self.radius * (1 - fire) ** 2
        if size > 1:
            pygame.draw.circle(surface, fire_color(fire), center, size)
            pygame.draw.circle(surface, fire_color(fire * 0.5), center, size * 0.55)    # hotter core
        # debris: flies out, slows down (distance grows like 1 - (1 - t)²), fades
        travel = 1 - (1 - progress) ** 2
        for reach, piece in self.debris:
            spot = center + reach * travel
            pygame.draw.rect(surface, fire_color(0.3 + 0.7 * progress), (spot.x - piece / 2, spot.y - piece / 2,
                                                                         piece, piece))
