"""
Rocket (Space): a fat rocket that flies to where the mouse was when it was launched. It starts slow, gets faster the
further it flies and explodes there in a red shockwave: big radius, damage, and every arena edge within the radius is
pushed out a lot. If the window shrinks so the target ends up outside, it explodes where it hits the wall.

Damage, blast radius, wall push and cooldown are values of the ability itself, so shop cards can raise them; every
launch takes a snapshot of them (ShotStats).
"""

import pygame

from game.ability import Ability
from game.rocket_projectile import RocketProjectile
from game.shot_stats import ShotStats

SPEED = 120                 # pixels per second at launch …
ACCELERATION = 2200         # … getting faster by this much every second
SIZE = 12
COLOR = (255, 70, 50)


class Rocket(Ability):
    name = "Rocket"

    def __init__(self):
        super().__init__()
        self.cooldown_time = 5.0
        self.damage = 5
        self.blast_radius = 150
        self.wall_push = 120

    def shot_stats(self):
        return ShotStats(damage=self.damage, speed=SPEED, wall_push=self.wall_push, size=SIZE, color=COLOR,
                         acceleration=ACCELERATION, blast_radius=self.blast_radius)

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
        ] + super().stat_lines()
