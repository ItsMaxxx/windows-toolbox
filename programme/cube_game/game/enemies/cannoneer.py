"""
Cannoneer: the Shooter's evolution (tier 2). Very slow and dark purple; behaves like a Shooter, but fires a huge
cannon ball that crawls through the air – easy to see coming, but a hit does massive damage. It stays further away than
a Shooter and turns its heavy barrel slowly.
"""

import pygame

from game.enemies.shooter import Shooter
from game.projectile import Projectile
from game.skins.cannoneer import CannoneerSkin

BALL_RING = (235, 170, 255)


class CannonBall(Projectile):
    """A big dark ball with a bright ring – so it stands out from small bullets."""

    def draw(self, surface, offset):
        center = pygame.Vector2(self.rect.center) - offset
        radius = self.stats.size / 2
        pygame.draw.circle(surface, self.color, center, radius)
        pygame.draw.circle(surface, BALL_RING, center, radius, 3)


class Cannoneer(Shooter):
    key = "cannoneer"
    name = "Cannoneer"
    tier = 2
    skin = CannoneerSkin()
    shot_color = (95, 30, 140)
    stats = {                       # fallback – see data/enemies.json
        "max_hp": 5, "speed": 45, "size": 36, "contact_damage": 25,
        "shooting_distance": 380, "fire_range": 650, "fire_interval": 4.0, "turn_speed": 60, "fire_cone": 14,
        "shot_damage": 100, "shot_speed": 140, "shot_size": 44,
    }

    def shoot_ahead(self, stats):
        return CannonBall(self.center, self.aim, stats)
