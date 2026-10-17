"""
The playing field: the arena plus every extra window (watchtower, radar) connected to it – overlapping or touching it,
or touching another connected window. It's the standard answer to "where is the field?" for everything:

  - the wall is the field's whole outer edge: the arena's edges where no connected window covers them, and the
    windows' edges where neither the arena nor another window continues the field,
  - shots (bullets and rockets alike) fly on through the arena's edge into a connected window; where they reach the
    wall there, they push the arena edge they crossed (wall_hit),
  - blasts happen inside the field (clamp) and push what they reach of the wall the same way: a reached part of the
    arena's edge pushes that edge, a reached part of a window's edge pushes the arena edge the shot crossed
    (walls_within),
  - the mouse is kept inside the field (rects – the engine confines the cursor to them),
  - sight: what the player sees – the arena and every extra window, connected or not (sight, sees) – decides which
    enemies count as seen (artillery digs in), what gets an off-screen marker, where enemies may appear and what the
    radar looks for.

The ship itself stays in the arena. The scene makes a new Field whenever it needs one (PlayScene.field()) – it's just
a few rectangles.
"""

import math

import pygame

from game.arena import SIDES

REACH = 2           # windows this close count as touching (rounded window positions leave no gap)


class Field:
    def __init__(self, arena, windows, lookouts=()):
        """arena: the run's Arena. windows: the screen rectangles of the open extra windows. lookouts: windows that are
        only for seeing (a Pusher's) – they never belong to the field, so shots and the mouse don't go there."""
        self.arena = arena
        self.main = arena.window_rect()
        self.sight = [self.main] + [pygame.Rect(window) for window in windows]
        connected, rest = [], self.sight[1:]
        self.lookouts = [pygame.Rect(window) for window in lookouts]
        self.sight += self.lookouts                 # last in sight
        grown = True
        while grown:                            # windows connected through other windows count, too
            grown = False
            for window in rest[:]:
                if any(window.inflate(REACH, REACH).colliderect(other) for other in [self.main] + connected):
                    connected.append(window)
                    rest.remove(window)
                    grown = True
        self.rects = [self.main] + connected    # the field: where the mouse may go
        self.windows = [window.inflate(REACH, REACH) for window in connected]

    # --- where things are ---

    def in_window(self, point):
        return any(window.collidepoint(point) for window in self.windows)

    def contains(self, point):
        return self.arena.side_hit(point) is None or self.in_window(point)

    def sees(self, rect):
        """True if rect lies completely in the arena or in one extra window (connected or not)."""
        return self.arena.rect.contains(rect) or any(window.contains(rect) for window in self.sight[1:])

    def sees_point(self, point):
        return any(window.collidepoint(point) for window in self.sight)

    def clamp(self, point):
        """point itself if it's in the field, else the nearest point that is."""
        if self.contains(point):
            return pygame.Vector2(point)
        nearest = [pygame.Vector2(min(max(point[0], rect.left), rect.right - 1),
                                  min(max(point[1], rect.top), rect.bottom - 1)) for rect in self.rects]
        return min(nearest, key=lambda candidate: candidate.distance_squared_to(point))

    # --- shots and blasts ---

    def wall_hit(self, projectile):
        """For a shot that has just moved: the arena edge it pushes now ("left", …) – None while it's still in the
        field. Past an edge into a connected window it flies on (projectile.beyond remembers which edge it crossed);
        leaving the field there, it pushes that edge."""
        point = projectile.rect.center
        side = self.arena.side_hit(point)
        if side is None:
            projectile.beyond = None                # (back) inside the arena
            return None
        if self.in_window(point):
            projectile.beyond = projectile.beyond or side
            return None
        return projectile.beyond or side

    def walls_within(self, point, radius, crossed=None):
        """The arena edges a blast at point (radius) pushes: every edge whose open part it reaches – and crossed (the
        arena edge the shot flew through, projectile.beyond) if it reaches the wall along a connected window, just
        like a bullet hitting that wall would."""
        def reaches(segments):
            return any(distance_to_segment(point, segment) <= radius for segment in segments)
        sides = [side for side in SIDES if reaches(self.open_parts(side))]
        if crossed is not None and crossed not in sides and reaches(self.window_walls()):
            sides.append(crossed)
        return sides

    def open_parts(self, side):
        """The parts of an arena edge that are the field's outer wall: [(start, end), …] as points."""
        return edge_parts(self.arena.rect, side, self.windows)

    def window_walls(self):
        """The field's outer wall along the connected windows: their edges where neither the arena nor another window
        continues the field."""
        walls = []
        for index, window in enumerate(self.rects[1:], start=1):
            others = [rect.inflate(REACH, REACH) for number, rect in enumerate(self.rects) if number != index]
            for side in SIDES:
                walls += edge_parts(window, side, others)
        return walls


def edge_parts(rect, side, covers):
    """One edge of rect without the parts lying inside one of covers (rectangles): [(start, end), …] as points."""
    if side in ("left", "right"):
        x = rect.left if side == "left" else rect.right
        covered = [(cover.top, cover.bottom) for cover in covers if cover.left < x < cover.right]
        return [((x, top), (x, bottom)) for top, bottom in subtract((rect.top, rect.bottom), covered)]
    y = rect.top if side == "top" else rect.bottom
    covered = [(cover.left, cover.right) for cover in covers if cover.top < y < cover.bottom]
    return [((left, y), (right, y)) for left, right in subtract((rect.left, rect.right), covered)]


def subtract(interval, cuts):
    """interval (start, end) without the cuts [(start, end), …] – what's left, as a list of intervals."""
    parts = [interval]
    for cut_start, cut_end in cuts:
        parts = [piece for start, end in parts
                 for piece in ((start, min(end, cut_start)), (max(start, cut_end), end)) if piece[1] > piece[0]]
    return parts


def distance_to_segment(point, segment):
    """Distance from point to an axis-parallel segment ((x1, y1), (x2, y2))."""
    (x1, y1), (x2, y2) = segment
    dx = max(x1 - point[0], 0, point[0] - x2)
    dy = max(y1 - point[1], 0, point[1] - y2)
    return math.hypot(dx, dy)
