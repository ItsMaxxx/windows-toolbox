"""
The player's ship: moves with W A S D and always points at the mouse.

It has 2 weapon slots (slot 1: left mouse button, slot 2: right mouse button) and 2 ability slots (keys in
settings.ABILITY_KEYS). A slot holds a Weapon / Ability or None (empty). Weapons and abilities decide everything
about their shots – the ship only says where from and in which direction.
"""

import pygame

from engine import Entity
from game import settings
from game.basic_gun import BasicGun
from game.dash import Dash
from game.rocket import Rocket
from game.ship_shape import draw_ship


class Ship(Entity):
    def __init__(self, center):
        size = settings.SHIP_SIZE
        super().__init__(0, 0, size, size, settings.SHIP_COLOR)
        self.rect.center = center
        self.aim = pygame.Vector2(0, -1)                # direction the nose points in (length 1)
        self.speed = settings.SHIP_SPEED
        self.weapons = [BasicGun(), None]
        self.abilities = [Dash(), Rocket()]
        self.invulnerable = 0.0                         # seconds left in which hits don't count (after a hit)
        self.stars = 0                                  # currency for the shop, dropped by killed enemies

    @staticmethod
    def move_direction():
        """Where W A S D steer right now: length 1, or (0, 0) when standing still."""
        keys = pygame.key.get_pressed()
        # right minus left, down minus up: opposite keys held together give 0, so they cancel each other out
        direction = pygame.Vector2(keys[pygame.K_d] - keys[pygame.K_a], keys[pygame.K_s] - keys[pygame.K_w])
        if direction.length_squared() > 0:
            direction.normalize_ip()            # otherwise diagonal movement would be ~1.4x faster
        return direction

    def update(self, dt, target):
        """target: the point to aim at (the mouse, in world coordinates)."""
        self.rect.move_ip(self.move_direction() * self.speed * dt)

        to_target = pygame.Vector2(target) - self.rect.center
        if to_target.length_squared() > 1:      # mouse right on the ship: keep the last direction
            self.aim = to_target.normalize()

        self.invulnerable = max(0.0, self.invulnerable - dt)
        for weapon in self.weapons:
            if weapon:
                weapon.update(dt)
        for ability in self.abilities:
            if ability:
                ability.update(dt, self)

    def hit(self):
        """Something hit the ship. True if it counts – False while still invulnerable from the last hit."""
        if self.invulnerable > 0:
            return False
        self.invulnerable = settings.INVULNERABLE_TIME
        return True

    def stat_groups(self):
        """All stats, grouped by part: [(title, [(name, value), …]), …] – the ship itself, then every weapon and
        ability in a slot. Shown in the shop."""
        groups = [("Ship", [("Move speed", f"{self.speed:g} px/s")])]
        for item in self.weapons + self.abilities:
            if item:
                groups.append((item.name, item.stat_lines()))
        return groups

    def nose(self):
        """Where shots come out (world coordinates)."""
        return pygame.Vector2(self.rect.center) + self.aim * settings.SHIP_SIZE * 0.6

    def fire(self, slot):
        """Fires the weapon in slot (0 or 1) from the nose. Returns the new projectiles – empty if the slot is empty
        or the weapon is still cooling down."""
        weapon = self.weapons[slot]
        if weapon is None:
            return []
        return weapon.fire(self.nose(), self.aim)

    def use_ability(self, slot, target):
        """Triggers the ability in slot (0 or 1). target: the mouse in world coordinates. Returns new projectiles."""
        ability = self.abilities[slot]
        if ability is None:
            return []
        return ability.use(self, target)

    def draw(self, surface, offset):
        for ability in self.abilities:
            if ability:
                ability.draw(surface, offset, self)
        if self.invulnerable and int(self.invulnerable * 10) % 2:      # blinks while invulnerable
            return
        center = pygame.Vector2(self.rect.center) - offset
        draw_ship(surface, center, self.aim, settings.SHIP_SIZE, self.color)
