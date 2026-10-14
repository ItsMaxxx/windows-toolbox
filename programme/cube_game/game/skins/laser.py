"""Laser: an amber square (with the tier 2 frame) and a thick barrel. While it aims, a line like the Sniper's but
thicker – dim while it follows the ship, bright once it's locked (the moment to get out of the way). The beam itself is
drawn by game/laser_beam.py."""

import pygame

from game.skins.skin import Skin

AIM_LENGTH = 3000
AIM_COLOR = (110, 75, 20)
AIM_LOCKED = (255, 190, 70)
BARREL_COLOR = (255, 215, 140)


class LaserSkin(Skin):
    color = (225, 150, 25)
    beam_color = (255, 200, 80)

    def draw_below(self, surface, enemy, rect):
        start = pygame.Vector2(rect.center)
        if enemy.aiming:
            color, width = (AIM_LOCKED, 4) if enemy.locked else (AIM_COLOR, 3)
            pygame.draw.line(surface, color, start, start + enemy.aim * AIM_LENGTH, width)
        pygame.draw.line(surface, BARREL_COLOR, start, start + enemy.aim * enemy.size * 1.1, 7)
