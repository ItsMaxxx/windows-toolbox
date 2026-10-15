"""
The player's ship: moves with W A S D and always points at the mouse.

It has 2 weapon slots (slot 1: left mouse button, slot 2: right mouse button – filled from the loadout) and 2 ability
slots (keys in settings.ABILITY_KEYS). A slot holds a Weapon / Ability or None (empty). Weapons and abilities decide
everything about their shots – the ship only says where from and in which direction.

Energy: both weapons share it. Every shot costs its weapon's energy_cost; the ship gets energy_regen back per second,
up to max_energy. Firing both at once empties it faster. Once it's empty, the weapons only fire as fast as it comes
back – a shot goes off as soon as there's enough for it. Abilities don't use energy, only their cooldown.

Hull: armor takes a flat amount off every hit (absorb()), invulnerable_time is how long it can't be hit again after one,
and magnet_radius is how close stars and cores have to be to get pulled in.

Knocked (knock()): pushed back – fast at first, then slowing down (KNOCKBACK_DECAY) – and stunned for a moment: it
can't move, shoot, use abilities or throw towers (the scene asks stunned), only aim. Small dots circle above it then.
"""

import math


import pygame

from engine import Entity
from game import armor, settings, ship_data
from game.dash import Dash
from game.rocket import Rocket
from game.ship_shape import draw_ship
from game.weapons import Gun

KNOCKBACK_DECAY = 12        # per second: how fast a knockback slows down (it covers distance in total)
STUN_DOTS = 3
STUN_COLOR = (255, 230, 120)


class Ship(Entity):
    def __init__(self, center, key=None):
        """key: which ship of data/ships.json – None: the one the file says is flown."""
        stats = ship_data.SHIPS[key] if key else ship_data.current()
        self.size = stats["size"]
        super().__init__(0, 0, self.size, self.size, stats["color"])
        self.name = stats["name"]
        self.rect.center = center
        self.aim = pygame.Vector2(0, -1)                # direction the nose points in (length 1)
        self.speed = stats["speed"]
        self.weapons = [Gun(), None]
        self.max_energy = stats["max_energy"]
        self.energy_regen = stats["energy_regen"]       # per second
        self.energy = self.max_energy
        self.invulnerable_time = stats["invulnerable_time"]
        self.armor = stats["armor"]                     # pixels off every hit
        self.magnet_radius = stats["magnet_radius"]
        self.abilities = [Dash(), Rocket()]
        self.invulnerable = 0.0                         # seconds left in which hits don't count (after a hit)
        self.stars = 0                                  # currency for the shop, dropped by killed enemies
        self.knockback = pygame.Vector2()               # pixels per second it's being pushed (slowing down)
        self.stun = 0.0                                 # seconds left in which it can't act
        self.stun_age = 0.0                             # seconds since the stun began (for the dots)
        self.watchtower = None                          # the watchtower kit (skill tree) – None: can't build any

    @staticmethod
    def move_direction():
        """Where W A S D steer right now: length 1, or (0, 0) when standing still."""
        keys = pygame.key.get_pressed()
        # right minus left, down minus up: opposite keys held together give 0, so they cancel each other out
        direction = pygame.Vector2(keys[pygame.K_d] - keys[pygame.K_a], keys[pygame.K_s] - keys[pygame.K_w])
        if direction.length_squared() > 0:
            direction.normalize_ip()            # otherwise diagonal movement would be ~1.4x faster
        return direction

    @property
    def stunned(self):
        return self.stun > 0

    def knock(self, direction, distance, stun):
        """Pushes it distance pixels in direction (spread over a moment) and stuns it for stun seconds."""
        if pygame.Vector2(direction).length_squared():
            self.knockback = pygame.Vector2(direction).normalize() * distance * KNOCKBACK_DECAY
        if stun > self.stun:
            self.stun, self.stun_age = stun, 0.0

    def upgrade(self, name, amount):
        """The skill tree's ship upgrades: name is "max" or "regen" (the energy) or one of the hull's values
        ("armor", "invulnerable_time")."""
        attribute = {"max": "max_energy", "regen": "energy_regen"}.get(name, name)
        setattr(self, attribute, round(getattr(self, attribute) + amount, 6))
        self.energy = self.max_energy

    def absorb(self, damage):
        """What's left of a hit's damage after the armor: armor pixels less, at least settings.MIN_HIT_SHARE."""
        return armor.reduce(damage, self.armor, settings.MIN_HIT_SHARE)

    def update(self, dt, target):
        """target: the point to aim at (the mouse, in world coordinates)."""
        self.energy = min(self.max_energy, self.energy + self.energy_regen * dt)
        self.stun = max(0.0, self.stun - dt)
        self.stun_age += dt
        if not self.stunned:
            self.rect.move_ip(self.move_direction() * self.speed * dt)
        if self.knockback.length_squared() > 1:
            slowing = math.exp(-KNOCKBACK_DECAY * dt)
            self.rect.move_ip(self.knockback * (1 - slowing) / KNOCKBACK_DECAY)     # exactly the way it slows down
            self.knockback *= slowing
        else:
            self.knockback = pygame.Vector2()

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
        self.invulnerable = self.invulnerable_time
        return True

    def nose(self):
        """Where shots come out (world coordinates)."""
        return pygame.Vector2(self.rect.center) + self.aim * self.size * 0.6

    def fire(self, slot):
        """Fires the weapon in slot (0 or 1) from the nose. Returns the new projectiles – empty if the slot is empty,
        the weapon is still cooling down or there isn't enough energy for a shot."""
        weapon = self.weapons[slot]
        if weapon is None or not weapon.ready or self.energy < weapon.energy_cost:
            return []
        self.energy -= weapon.energy_cost
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
        center = pygame.Vector2(self.rect.center) - offset
        if self.stunned:                                # little dots circling above it (also while it blinks)
            for dot in range(STUN_DOTS):
                angle = self.stun_age * 8 + dot * 2 * math.pi / STUN_DOTS
                spot = center + (math.cos(angle) * 12, -self.size * 0.9 + math.sin(angle) * 4)
                pygame.draw.circle(surface, STUN_COLOR, spot, 2)
        if self.invulnerable and int(self.invulnerable * 10) % 2:      # blinks while invulnerable
            return
        draw_ship(surface, center, self.aim, self.size, self.color)
