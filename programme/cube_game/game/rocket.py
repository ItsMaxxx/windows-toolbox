"""
Rocket (Space): a fat rocket that flies to where the mouse was when it was launched. It starts slow, gets faster the
further it flies and explodes there in a red shockwave: big radius, damage, and every arena edge within the radius is
pushed out a lot. If the window shrinks so the target ends up outside, it explodes where it hits the wall.

Damage, blast radius, wall push and cooldown are values of the ability itself, so shop cards can raise them; every
launch takes a snapshot of them (ShotStats). They start at the values in data/weapons.json ("rocket" – weak at first)
and grow with its skill tree upgrades (apply_tree). The skill tree's "Burning ground" (burning = True): the blast
leaves burning ground behind (game/effects/burning_ground.py).
"""

from dataclasses import replace

import pygame

from game.ability import Ability
from game.rocket_projectile import RocketProjectile
from game.shot_stats import ShotStats
from game.weapons import data

SPEED = 120                 # pixels per second at launch …
ACCELERATION = 2200         # … getting faster by this much every second
SIZE = 12
COLOR = (255, 70, 50)


class Rocket(Ability):
    key = "rocket"                  # its section in data/weapons.json
    name = "Rocket"
    ATTRIBUTES = {"cooldown": "cooldown_time", "damage": "damage", "blast_radius": "blast_radius",
                  "wall_push": "wall_push"}
    MIN_COOLDOWN = 1.5

    def __init__(self):
        super().__init__()
        stats = data.STATS[self.key]
        for name, attribute in self.ATTRIBUTES.items():
            setattr(self, attribute, stats[name])
        self.burning = False

    @classmethod
    def tree_amount(cls, name):
        return data.STATS[cls.key]["tree"][name]

    def apply_tree(self, name, levels):
        """levels levels of the skill tree upgrade name (e.g. "blast_radius")."""
        attribute = self.ATTRIBUTES[name]
        value = round(getattr(self, attribute) + self.tree_amount(name) * levels, 6)
        setattr(self, attribute, max(self.MIN_COOLDOWN if name == "cooldown" else 0, value))

    def shot_stats(self):
        stats = ShotStats(damage=self.damage, speed=SPEED, wall_push=self.wall_push, size=SIZE, color=COLOR,
                          acceleration=ACCELERATION, blast_radius=self.blast_radius)
        if not self.burning:
            return stats
        burning = data.STATS[self.key]["burning"]
        return replace(stats, burn_time=burning["duration"], burn_damage=burning["damage_per_second"],
                       burn_radius=self.blast_radius * burning["radius"])

    def activate(self, ship, target):
        nose = ship.nose()
        direction = pygame.Vector2(target) - nose
        if direction.length_squared() < 1:
            direction = pygame.Vector2(ship.aim)
        return [RocketProjectile(nose, direction, self.shot_stats(), target)]

    def stat_lines(self):
        return [
            ("Damage", f"{self.damage:g}"),
            ("Blast radius", f"{self.blast_radius:g} px"),
            ("Wall push", f"{self.wall_push:g} px"),
        ] + super().stat_lines() + ([("Burning ground", "yes")] if self.burning else [])
