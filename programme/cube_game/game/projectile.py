"""
A shot: flies until it leaves the arena (and pushes that edge out) – or, with a target, until it reaches it.
Shots with a blast radius explode at their end (see PlayScene.explode).

Everything comes from the weapon or ability that fired it – nothing from settings.

Two kinds of values:
  - stats (ShotStats): the snapshot at the moment of firing – never changes.
  - direction, base_speed, speed_factor, target: the shot's own state in flight – effects change these.
    base_speed starts at stats.speed and grows by stats.acceleration (rockets get faster the longer they fly).

Effects from the outside, for example:
  - redirect(new_direction): onto a different path for good (e.g. an enemy that deflects shots). A shot with a target
    forgets it then and flies on until it hits an edge.
  - slow(factor): slowed for the current tick only. An area (AoE) calls it every tick for each shot inside it;
    once the shot leaves the area, nobody calls it any more and it's back to full speed by itself.
    Several slows stack (multiply). Effects must run *before* Projectile.update() in the tick.
"""

import pygame

from engine import Entity


class Projectile(Entity):
    def __init__(self, position, direction, stats, target=None):
        """target: point (world coordinates) where the shot ends, e.g. where a rocket explodes – or None."""
        super().__init__(0, 0, stats.size, stats.size, stats.color)
        self.rect.center = position
        self.stats = stats
        self.direction = pygame.Vector2(direction).normalize()
        self.base_speed = stats.speed
        self.speed_factor = 1.0             # 1 = normal speed; reset after every tick
        self.target = pygame.Vector2(target) if target is not None else None
        self.arrived = False                # True once it has reached its target

    @property
    def speed(self):
        """Current speed in pixels per second (base speed × effects this tick)."""
        return self.base_speed * self.speed_factor

    def redirect(self, direction):
        """Changes the flight path for good."""
        self.direction = pygame.Vector2(direction).normalize()
        self.target = None

    def slow(self, factor):
        """Slows the shot for this tick, e.g. factor 0.5 = half speed."""
        self.speed_factor *= factor

    def update(self, dt):
        step = self.speed * dt
        if self.target is not None and self.target.distance_to(self.rect.center) <= step:
            self.rect.center = self.target          # don't fly past the target
            self.arrived = True
        else:
            self.rect.move_ip(self.direction * step)
        self.base_speed += self.stats.acceleration * dt
        self.speed_factor = 1.0             # effects have to be applied again next tick

    def draw(self, surface, offset):
        center = pygame.Vector2(self.rect.center) - offset
        pygame.draw.circle(surface, self.color, center, self.stats.size / 2)
