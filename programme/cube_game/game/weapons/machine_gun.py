"""
The machine gun: many small, weak shots that spread a lot – each one goes off in a random direction within the spread
(degrees, the whole cone). Missing isn't wasted: a shot that misses flies on and pushes the wall.

Its skill tree upgrades for damage and attack speed make it spread more, too (spread_per_upgrade degrees per level);
"Precision" makes it spread less.
"""

import random

import pygame

from game.weapons import data
from game.weapons.weapon import Weapon


class MachineGun(Weapon):
    key = "machine_gun"
    name = "Machine gun"
    color = (255, 190, 90)
    description = "Very fast, weak shots that spread a lot."
    ATTRIBUTES = dict(Weapon.ATTRIBUTES, spread="spread")
    SPREADING = ("damage", "attack_speed")      # skill tree upgrades that add to the spread

    def apply_tree(self, name, levels):
        super().apply_tree(name, levels)
        if name in self.SPREADING:
            self.upgrade("spread", data.STATS[self.key]["spread_per_upgrade"] * levels)

    def make_projectile(self, origin, direction):
        angle = random.uniform(-self.spread / 2, self.spread / 2)
        return super().make_projectile(origin, pygame.Vector2(direction).rotate(angle))

    def stat_lines(self):
        return super().stat_lines() + [("Spread", f"{self.spread:g}°")]
