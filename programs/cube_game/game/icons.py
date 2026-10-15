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


# --- level indicators (game menu, Levels tab) – size: about the icon's width in pixels ---

def draw_swarm_icon(surface, center, color, size=14):
    """A swarm: a small cluster of squares."""
    x, y = center
    side = max(3, round(size * 0.3))
    for dx, dy in ((-0.35, -0.3), (0.3, -0.35), (0, 0.05), (-0.38, 0.38), (0.35, 0.35)):
        square = pygame.Rect(0, 0, side, side)
        square.center = (x + dx * size, y + dy * size)
        pygame.draw.rect(surface, color, square)


def draw_wave_icon(surface, center, color, size=14):
    """A wave of one type (a phase with more of it): a warning triangle with an exclamation mark."""
    x, y = center
    half = size / 2
    pygame.draw.polygon(surface, color, [(x, y - half), (x + half, y + half * 0.8), (x - half, y + half * 0.8)], 2)
    pygame.draw.line(surface, color, (x, y - half * 0.25), (x, y + half * 0.25), 2)
    pygame.draw.rect(surface, color, (x - 1, y + half * 0.45, 2, 2))


def draw_damage_icon(surface, center, color, size=14):
    """Enemies hit harder: a spiky burst."""
    center = pygame.Vector2(center)
    points = [center + pygame.Vector2(0, -size / 2 * (1 if index % 2 == 0 else 0.45)).rotate(index * 22.5)
              for index in range(16)]
    pygame.draw.polygon(surface, color, points)


def draw_hp_icon(surface, center, color, size=14):
    """Enemies get more hit points: a thick plus."""
    x, y = center
    long, thick = size, max(3, round(size * 0.32))
    pygame.draw.rect(surface, color, (x - long / 2, y - thick / 2, long, thick))
    pygame.draw.rect(surface, color, (x - thick / 2, y - long / 2, thick, long))


def draw_wall_icon(surface, center, color, size=14):
    """Harder walls: a little brick wall – a block with dark mortar lines (two rows of bricks, offset)."""
    wall = pygame.Rect(0, 0, size, round(size * 0.8))
    wall.center = center
    pygame.draw.rect(surface, color, wall)
    mortar = [round(channel * 0.3) for channel in color]
    middle = wall.centery
    pygame.draw.line(surface, mortar, (wall.left, middle), (wall.right - 1, middle))
    pygame.draw.line(surface, mortar, (wall.centerx, wall.top), (wall.centerx, middle))
    for x in (wall.left + wall.width // 4, wall.right - wall.width // 4):
        pygame.draw.line(surface, mortar, (x, middle), (x, wall.bottom - 1))


def draw_notice_icon(surface, center, color, size=14):
    """Something else is announced: a diamond."""
    x, y = center
    half = size / 2
    pygame.draw.polygon(surface, color, [(x, y - half), (x + half, y), (x, y + half), (x - half, y)])


def draw_check(surface, center, color, size=14):
    """A tick: cleared."""
    x, y = center
    pygame.draw.lines(surface, color, False, [(x - size / 2, y), (x - size / 8, y + size * 0.38),
                                               (x + size / 2, y - size * 0.4)], 3)
