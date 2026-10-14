"""
A mine, left behind by the dash once the skill tree's "Mines" is bought (Dash.mines): it lies where the dash started
and goes off when an enemy touches it or the shrinking wall reaches it – a blast like the rocket's (PlayScene.explode):
damage to every enemy within the radius, and the wall it reaches is pushed out. It never goes away by itself.
With "Slow field" bought, the blast leaves a field behind that slows the enemies in it (game/effects/slow_field.py).

To the play scene it's just a player shot that doesn't move (speed 0, no target): touching an enemy or leaving the
field ends it, and its blast radius makes it explode there. Its values are "mine" in data/abilities.json plus the
skill tree's "Power", the slow field's "slow_field" there plus its upgrades – no cards change them.
"""

import math
from dataclasses import replace

import pygame

from game.projectile import Projectile
from game.shot_stats import ShotStats

COLOR = (255, 90, 60)           # the blast
BODY = (110, 110, 120)
LIGHT = (255, 60, 40)
BLINK_TIME = 0.8                # seconds per blink of its light


class Mine(Projectile):
    def __init__(self, position, values, slow_field=None):
        """values: "mine" from data/abilities.json ({"damage", "blast_radius", "wall_push", "size"}). slow_field: the
        slow field's {"slow" (percent), "size", "duration"} with its upgrades – None without it."""
        stats = ShotStats(damage=values["damage"], speed=0, wall_push=values["wall_push"], size=values["size"],
                          color=COLOR, blast_radius=values["blast_radius"])
        if slow_field:
            stats = replace(stats, slow=slow_field["slow"] / 100, slow_radius=slow_field["size"] / 2,
                            slow_time=slow_field["duration"])
        super().__init__(position, (1, 0), stats)
        self.age = 0.0

    def update(self, dt):
        super().update(dt)
        self.age += dt

    def draw(self, surface, offset):
        center = pygame.Vector2(self.rect.center) - offset
        radius = self.stats.size / 2
        pygame.draw.circle(surface, BODY, center, radius)
        if math.sin(self.age / BLINK_TIME * 2 * math.pi) > 0:      # blinks: on half the time
            pygame.draw.circle(surface, LIGHT, center, max(1.0, radius * 0.45))
