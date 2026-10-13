"""
The rocket in flight: a normal Projectile (snapshot, target, acceleration, slow/redirect all work the same) that just
looks different – a body with fins and a flickering flame.
"""

import random

import pygame

from game.projectile import Projectile

FLAME = (255, 170, 40)
FINS = (150, 40, 30)


class RocketProjectile(Projectile):
    def draw(self, surface, offset):
        center = pygame.Vector2(self.rect.center) - offset
        forward = self.direction
        side = forward.rotate(90)
        width = self.stats.size
        length = width * 2.8
        tip = center + forward * length / 2
        back = center - forward * length / 2

        flame_size = width * random.uniform(0.35, 0.6)
        pygame.draw.circle(surface, FLAME, back - forward * flame_size, flame_size)
        for sign in (1, -1):        # two fins at the back
            pygame.draw.polygon(surface, FINS, [back + forward * width * 0.8 + side * sign * width * 0.4,
                                                back + side * sign * width * 0.9,
                                                back + side * sign * width * 0.3])
        pygame.draw.polygon(surface, self.color, [
            tip,
            center + forward * length * 0.2 + side * width / 2,
            back + side * width / 2,
            back - side * width / 2,
            center + forward * length * 0.2 - side * width / 2,
        ])
