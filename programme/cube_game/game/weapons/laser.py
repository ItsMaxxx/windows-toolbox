"""
The laser: looks like a continuous beam, but is really a stream of very fast, tiny bolts (attack_speed per second).
That way it works like every other shot – shields block it, it flies into watchtower and radar windows, a bolt either
hits or pushes the wall.

Each bolt is drawn as a line reaching back to where the one before it is (trail = distance between two bolts), so
together they form one beam. Each one does very little damage, but the beam pushes the walls hard. Its values are
per bolt; the inventory shows them per second.
"""

import pygame

from game.projectile import Projectile
from game.weapons.weapon import Weapon

GLOW_WIDTH = 2.5            # the soft glow around the beam, in bolt sizes
CORE_COLOR = (225, 255, 235)


class LaserBolt(Projectile):
    def __init__(self, position, direction, stats, trail):
        super().__init__(position, direction, stats)
        self.origin = pygame.Vector2(position)
        self.trail = trail                  # pixels the line reaches back – never behind where it was fired

    def draw(self, surface, offset):
        head = pygame.Vector2(self.rect.center)
        tail = head - self.direction * min(self.trail, head.distance_to(self.origin))
        glow = [round(channel * 0.35) for channel in self.color]
        width = self.stats.size
        pygame.draw.line(surface, glow, head - offset, tail - offset, max(1, round(width * GLOW_WIDTH)))
        pygame.draw.line(surface, self.color, head - offset, tail - offset, max(1, round(width)))
        pygame.draw.line(surface, CORE_COLOR, head - offset, tail - offset, max(1, round(width / 3)))


class Laser(Weapon):
    key = "laser"
    name = "Laser"
    color = (90, 255, 160)
    description = "A beam: barely hurts enemies, pushes walls hard."

    def make_projectile(self, origin, direction):
        gap = self.shot_speed / self.fire_rate          # how far apart two bolts fly
        return LaserBolt(origin, direction, self.shot_stats(), trail=gap * 1.1)

    def stat_lines(self):
        rate = self.fire_rate
        return [
            ("Damage", f"{self.damage * rate:.3g}/s"),
            ("Wall push", f"{self.wall_push * rate:.3g} px/s"),
            ("Beam speed", f"{self.shot_speed:g} px/s"),
            ("Energy use", f"{self.energy_cost * rate:.3g}/s"),
        ]
