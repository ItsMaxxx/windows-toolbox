"""
Burning ground: left behind by a rocket's blast once "Burning ground" is bought in the skill tree. For a few seconds it
burns every enemy in it: every PULSE seconds a pulse of damage (damage per second × PULSE), so the enemies flash with
each pulse instead of glowing white the whole time. It fades out towards the end.

Unlike the other effects it does something: the scene calls pulse() after update() and hurts the enemies within
radius (see PlayScene.update_burning).

Drawing: the glowing ground and its edge are drawn once (engine/sprite_cache.py); every frame they're only copied onto
a reused layer, the embers go on top, and the whole layer is made more see-through as it fades out.
"""

import math
import random

import pygame

from engine.sprite_cache import PICTURES, scratch

PULSE = 0.5                 # seconds between two pulses of damage
FADE_TIME = 0.6             # seconds at the end in which it fades out
GROUND = (255, 90, 30)      # the glowing ground (drawn see-through) …
EMBER = (255, 190, 80)      # … and the embers flickering on it
EMBERS = 18


class BurningGround:
    def __init__(self, position, radius, damage_per_second, duration):
        self.position = pygame.Vector2(position)
        self.radius = radius
        self.damage = damage_per_second * PULSE         # per pulse
        self.duration = duration
        self.age = 0.0
        self.next_pulse = PULSE
        self.pulses = 0                                 # pulses due this tick (read by the scene)
        self.embers = [(pygame.Vector2(radius * math.sqrt(random.random()), 0).rotate(random.uniform(0, 360)),
                        random.uniform(0, math.tau)) for _ in range(EMBERS)]

    @property
    def done(self):
        return self.age >= self.duration

    def update(self, dt):
        self.age += dt
        self.pulses = 0
        while self.age >= self.next_pulse and self.next_pulse <= self.duration:
            self.pulses += 1
            self.next_pulse += PULSE

    def draw(self, surface, offset):
        fade = min(1.0, (self.duration - self.age) / FADE_TIME)
        size = math.ceil(self.radius * 2)
        layer = scratch((size, size))
        center = (size / 2, size / 2)
        layer.blit(PICTURES.get(("burning ground", size, self.radius), lambda: self.make_ground(size)), (0, 0))
        for spot, phase in self.embers:
            flicker = 0.5 + 0.5 * math.sin(self.age * 9 + phase)
            pygame.draw.circle(layer, (*EMBER, round(220 * flicker)), spot + center, 2)
        layer.set_alpha(round(255 * fade))
        surface.blit(layer, self.position - offset - center)

    def make_ground(self, size):
        """The glowing ground and its edge, without embers and not faded yet."""
        ground = pygame.Surface((size, size), pygame.SRCALPHA)
        center = (size / 2, size / 2)
        pygame.draw.circle(ground, (*GROUND, 55), center, self.radius)
        pygame.draw.circle(ground, (*GROUND, 140), center, self.radius, 2)
        return ground
