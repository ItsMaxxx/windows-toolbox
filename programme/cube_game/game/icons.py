"""
Small icons drawn from shapes – pygame's built-in font has no ★ or → characters.
"""

import pygame

STAR_COLOR = (255, 215, 60)


def draw_star(surface, center, radius, color=STAR_COLOR):
    """A five-pointed star."""
    center = pygame.Vector2(center)
    points = [center + pygame.Vector2(0, -radius * (1 if index % 2 == 0 else 0.45)).rotate(index * 36)
              for index in range(10)]
    pygame.draw.polygon(surface, color, points)


def draw_arrow(surface, start, end, color, width=2):
    """A line from start to end with a small head at the end."""
    start, end = pygame.Vector2(start), pygame.Vector2(end)
    pygame.draw.line(surface, color, start, end, width)
    direction = (end - start).normalize() * 6
    pygame.draw.polygon(surface, color, [end + direction * 0.5, end - direction + direction.rotate(90) * 0.7,
                                         end - direction - direction.rotate(90) * 0.7])


def draw_shop_icon(surface, center, color):
    """A small shopping cart: handle, basket, two wheels."""
    x, y = center
    pygame.draw.line(surface, color, (x - 10, y - 6), (x - 6, y - 6), 2)                     # handle
    pygame.draw.polygon(surface, color, [(x - 6, y - 5), (x + 9, y - 5), (x + 6, y + 2), (x - 4, y + 2)])
    pygame.draw.circle(surface, color, (x - 3, y + 5), 2)
    pygame.draw.circle(surface, color, (x + 5, y + 5), 2)
