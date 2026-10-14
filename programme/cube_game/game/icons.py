"""
Small icons drawn from shapes – pygame's built-in font has no ★ or → characters.
"""

import pygame

STAR_COLOR = (255, 215, 60)
CORE_COLOR = (90, 225, 255)


def draw_star(surface, center, radius, color=STAR_COLOR):
    """A five-pointed star."""
    center = pygame.Vector2(center)
    points = [center + pygame.Vector2(0, -radius * (1 if index % 2 == 0 else 0.45)).rotate(index * 36)
              for index in range(10)]
    pygame.draw.polygon(surface, color, points)


def draw_core(surface, center, radius, color=CORE_COLOR):
    """A small cube seen from above at an angle: a bright top, a medium left and a dark right side."""
    x, y = center
    side = radius * 0.87                        # cos 30°: the cube's corners left and right
    top = [(x, y - radius), (x + side, y - radius / 2), (x, y), (x - side, y - radius / 2)]
    left = [(x - side, y - radius / 2), (x, y), (x, y + radius), (x - side, y + radius / 2)]
    right = [(x + side, y - radius / 2), (x, y), (x, y + radius), (x + side, y + radius / 2)]
    for points, shade in ((top, 1.0), (left, 0.7), (right, 0.45)):
        pygame.draw.polygon(surface, [round(channel * shade) for channel in color], points)


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


def draw_watchtower_icon(surface, center, color):
    """A small watchtower from above: a square with a dark lens."""
    rect = pygame.Rect(0, 0, 13, 13)
    rect.center = center
    pygame.draw.rect(surface, color, rect, border_radius=2)
    pygame.draw.circle(surface, (0, 0, 0), rect.center, 3)
