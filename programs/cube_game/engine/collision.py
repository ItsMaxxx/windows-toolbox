"""
Collision helpers for axis-aligned rectangles (AABB).
"""

import math
import random
from collections import defaultdict


def keep_inside(rect, bounds):
    """Pushes rect back inside bounds if it sticks out. Returns True if it had to be pushed (it hit a wall)."""
    if bounds.contains(rect):
        return False
    rect.clamp_ip(bounds)
    return True


def overlaps(a, b):
    """True if the two rectangles overlap."""
    return a.colliderect(b)


def push_apart(a, b, weight_a=1, weight_b=1, gap=0):
    """If the rectangles overlap (or are closer than gap), moves them apart along the axis where they overlap less
    (the shorter way out) until gap pixels are between them. The heavier one moves less: with equal weights both move
    half, against a much heavier one the light one does nearly all of it. A weight of math.inf never moves at all (like
    a wall). Returns True if they had to be moved."""
    dx = b.centerx - a.centerx
    overlap_x = (a.width + b.width) / 2 + gap - abs(dx)
    if overlap_x <= 0:
        return False
    dy = b.centery - a.centery
    overlap_y = (a.height + b.height) / 2 + gap - abs(dy)
    if overlap_y <= 0:
        return False
    if math.inf in (weight_a, weight_b):              # an immovable one: the other does all of it (two: nobody moves)
        share_a, share_b = float(weight_a != math.inf and weight_b == math.inf), float(weight_b != math.inf
                                                                                         and weight_a == math.inf)
    else:
        share_a = weight_b / (weight_a + weight_b)    # the part of the way a has to go
        share_b = 1 - share_a
    if overlap_x < overlap_y:
        sign = (dx > 0) - (dx < 0) or random.choice((-1, 1))   # exactly on top of each other: pick a side
        a.x -= sign * overlap_x * share_a
        b.x += sign * overlap_x * share_b
    else:
        sign = (dy > 0) - (dy < 0) or random.choice((-1, 1))
        a.y -= sign * overlap_y * share_a
        b.y += sign * overlap_y * share_b
    return True


def close(a, b, distance):
    """True if the rectangles are at most distance apart (or overlap)."""
    return a.colliderect(b.inflate(2 * distance, 2 * distance))


def nearby_pairs(entities, cell_size):
    """Every pair of entities that are close enough to touch – without checking each against each (n² pairs).

    Spatial hash: the world is cut into a grid of cell_size squares, every entity is put into the cell its centre is
    in. Two entities can only touch if their cells are neighbours, so only those are compared. cell_size must be at
    least as big as the biggest entity (plus the gap, if they are kept apart by one)."""
    grid = defaultdict(list)
    for index, entity in enumerate(entities):
        x, y = entity.rect.center
        grid[(int(x // cell_size), int(y // cell_size))].append((index, entity))
    for (cell_x, cell_y), cell in grid.items():
        for index, entity in cell:
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for other_index, other in grid.get((cell_x + dx, cell_y + dy), ()):
                        if index < other_index:         # each pair only once
                            yield entity, other
