"""
Burning ground: left behind by a rocket's blast once "Burning ground" is bought in the skill tree. For a few seconds it
burns every enemy in it: every PULSE seconds a pulse of damage (damage per second × PULSE), so the enemies flash with
each pulse instead of glowing white the whole time. It fades out towards the end.

Unlike the other effects it does something: the scene calls pulse() after update() and hurts the enemies within
radius (see PlayScene.update_burning).
"""

import math
import random

import pygame

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
        layer = pygame.Surface((size, size), pygame.SRCALPHA)
        center = (size / 2, size / 2)
        pygame.draw.circle(layer, (*GROUND, round(55 * fade)), center, self.radius)
        pygame.draw.circle(layer, (*GROUND, round(140 * fade)), center, self.radius, 2)
        for spot, phase in self.embers:
            flicker = 0.5 + 0.5 * math.sin(self.age * 9 + phase)
            pygame.draw.circle(layer, (*EMBER, round(220 * fade * flicker)), spot + center, 2)
        surface.blit(layer, self.position - offset - center)
