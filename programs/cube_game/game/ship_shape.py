"""
The ship's shape, drawable anywhere and at any size: in the game, as dash afterimages, in the menu and the inventory.
"""

import pygame


def draw_ship(surface, center, aim, size, color):
    """An arrowhead: nose towards aim, two wing tips at the back, a notch in between."""
    center = pygame.Vector2(center)
    aim = pygame.Vector2(aim)
    points = [
        center + aim * size * 0.6,                      # nose
        center + aim.rotate(140) * size * 0.5,          # wing tip
        center - aim * size * 0.15,                     # notch at the back
        center + aim.rotate(-140) * size * 0.5,         # other wing tip
    ]
    pygame.draw.polygon(surface, color, points)
