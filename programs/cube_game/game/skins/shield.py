"""Shield: a steel blue square with a big light shield in front of it (across the direction it faces); while it winds up
for a dash, a dark warning line shows where it's going – like the Charger's."""

import pygame

from game.skins.skin import Skin

SHIELD_COLOR = (200, 220, 245)
SHIELD_EDGE = (120, 150, 190)
SHIELD_THICKNESS = 7
WARNING_LENGTH = 200
WARNING_COLOR = (40, 70, 120)


class ShieldSkin(Skin):
    color = (70, 110, 170)

    def draw_below(self, surface, enemy, rect):
        if enemy.winding_up:
            start = pygame.Vector2(rect.center)
            pygame.draw.line(surface, WARNING_COLOR, start, start + enemy.aim * WARNING_LENGTH, 4)

    def draw_above(self, surface, enemy, rect):
        offset = pygame.Vector2(rect.center) - enemy.center         # world -> window
        start, end = (point + offset for point in enemy.shield_line())
        pygame.draw.line(surface, SHIELD_EDGE, start, end, SHIELD_THICKNESS + 2)
        pygame.draw.line(surface, SHIELD_COLOR, start, end, SHIELD_THICKNESS)
