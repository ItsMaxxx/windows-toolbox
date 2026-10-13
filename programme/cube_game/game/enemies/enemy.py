"""
Base class for all enemies. Every enemy type is a subclass (class Charger(Enemy): …) that inherits everything here
and only changes what's different: its values (class attributes like max_hp, speed, color) and its behaviour
(act(), draw_details()).

The default behaviour – run straight at the ship – is in act(). update() is called every tick and returns the
projectiles the enemy fires (a list, usually empty). Enemies often start outside the window: positions are screen
pixels, so they simply walk in from the desktop.
"""

import math

import pygame

from engine import Entity
from game.projectile import Projectile

HIT_FLASH = 0.1             # seconds an enemy flashes white after a hit
FLASH_COLOR = (255, 255, 255)
PIP_SIZE = (6, 4)           # health pips above a damaged enemy
PIP_EMPTY = (70, 70, 70)


class Enemy(Entity):
    name = "Enemy"
    max_hp = 1
    speed = 100             # pixels per second
    size = 28               # pixels (square hitbox)
    color = (255, 40, 40)
    contact_damage = 1      # damage when it touches the ship (0 = harmless to touch)

    def __init__(self, position):
        super().__init__(0, 0, self.size, self.size, self.color)
        self.rect.center = position
        self.hp = self.max_hp
        self.flash = 0.0

    @property
    def alive(self):
        return self.hp > 0

    @property
    def center(self):
        return pygame.Vector2(self.rect.center)

    def take_damage(self, amount):
        self.hp -= amount
        self.flash = HIT_FLASH

    # --- helpers for subclasses ---

    def distance_to(self, point):
        return self.center.distance_to(point)

    def direction_to(self, point):
        """Unit vector towards point (or (0, 0) if it's right here)."""
        offset = pygame.Vector2(point) - self.center
        return offset.normalize() if offset.length_squared() > 0 else pygame.Vector2()

    def move(self, direction, speed, dt):
        self.rect.move_ip(pygame.Vector2(direction) * speed * dt)

    def shoot(self, target, stats):
        """A projectile from the centre towards target, with the snapshot stats."""
        direction = self.direction_to(target)
        return Projectile(self.center, direction if direction.length_squared() else (1, 0), stats)

    # --- every tick ---

    def update(self, dt, ship):
        self.flash = max(0.0, self.flash - dt)
        return self.act(dt, ship)

    def act(self, dt, ship):
        """Behaviour. Default: run straight at the ship, never shoot."""
        self.move(self.direction_to(ship.rect.center), self.speed, dt)
        return []

    # --- drawing ---

    def draw(self, surface, offset):
        rect = self.rect.move(-offset[0], -offset[1])
        self.draw_details(surface, rect, offset)
        pygame.draw.rect(surface, FLASH_COLOR if self.flash else self.color, rect)
        if self.hp < self.max_hp:
            self.draw_health(surface, rect)

    def draw_details(self, surface, rect, offset):
        """Extras below the body (barrel, laser, warning line, …). rect: the body in window coordinates."""

    def draw_health(self, surface, rect):
        """One pip per hit point above the enemy – filled ones are left."""
        width, height = PIP_SIZE
        total = self.max_hp * width + (self.max_hp - 1) * 2
        left = rect.centerx - total / 2
        for index in range(self.max_hp):
            color = self.color if index < math.ceil(self.hp) else PIP_EMPTY
            pygame.draw.rect(surface, color, (left + index * (width + 2), rect.top - height - 4, width, height))
