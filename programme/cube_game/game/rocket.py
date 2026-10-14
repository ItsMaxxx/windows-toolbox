"""
Rocket (Space): a fat rocket that flies to where the mouse was when it was launched. It starts slow, gets faster the
further it flies and explodes there in a red shockwave: big radius, damage, and every arena edge within the radius is
pushed out a lot. If the window shrinks so the target ends up outside, it explodes where it hits the wall.

Damage, blast radius, wall push and cooldown are values of the ability itself, so shop cards can raise them; every
launch takes a snapshot of them (ShotStats). They start at the values in data/abilities.json ("rocket" – weak at
first, like its speed and size) and grow with its skill tree upgrades (upgrade()). The skill tree's "Burning ground"
(burning: its values from data/skilltree.json, None without it): the blast leaves burning ground behind
(game/effects/burning_ground.py).
"""

from dataclasses import replace

import pygame

from game import ability_data
from game.ability import Ability
from game.rocket_projectile import RocketProjectile
from game.shot_stats import ShotStats

COLOR = (255, 70, 50)


class Rocket(Ability):
    key = "rocket"                  # its section in data/abilities.json
    name = "Rocket"
    ATTRIBUTES = {"cooldown": "cooldown_time", "damage": "damage", "blast_radius": "blast_radius",
                  "wall_push": "wall_push"}

    def __init__(self):
        super().__init__()
        stats = ability_data.STATS[self.key]
        for name, attribute in self.ATTRIBUTES.items():
            setattr(self, attribute, stats[name])
        self.min_cooldown = stats["min_cooldown"]
        self.speed, self.acceleration, self.size = stats["speed"], stats["acceleration"], stats["size"]
        self.burning = None             # {"duration", "damage_per_second", "radius"} once "Burning ground" is bought

    def upgrade(self, name, amount):
        """Adds amount to the value name (e.g. "blast_radius") – the skill tree's upgrades."""
        attribute = self.ATTRIBUTES[name]
        value = round(getattr(self, attribute) + amount, 6)
        setattr(self, attribute, max(self.min_cooldown if name == "cooldown" else 0, value))

    def shot_stats(self):
        stats = ShotStats(damage=self.damage, speed=self.speed, wall_push=self.wall_push, size=self.size, color=COLOR,
                          acceleration=self.acceleration, blast_radius=self.blast_radius)
        if not self.burning:
            return stats
        burning = self.burning
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
