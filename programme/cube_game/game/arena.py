"""
The arena is the game window itself: a rectangle on the screen that keeps shrinking towards its centre. A shot that
hits one of its edges pushes exactly that edge back out – but never beyond the usable desktop.
"""

import pygame

from engine.collision import keep_inside
from game import settings

SIDES = ("left", "right", "top", "bottom")


class Arena:
    def __init__(self, bounds):
        """bounds: the area the window may never leave (the desktop without the taskbar)."""
        self.bounds = pygame.FRect(bounds)
        self.rect = pygame.FRect((0, 0), settings.WINDOW_START_SIZE)
        self.rect.center = self.bounds.center
        self.pending = dict.fromkeys(SIDES, 0.0)     # how far each edge still has to move out after hits

    def window_rect(self):
        """The arena as a whole-pixel rectangle for the window. Every edge is rounded on its own, so the opposite edge
        doesn't wobble when one edge moves."""
        left, top = round(self.rect.left), round(self.rect.top)
        return pygame.Rect(left, top, round(self.rect.right) - left, round(self.rect.bottom) - top)

    def update(self, dt):
        self.squeeze(settings.SHRINK_SPEED * dt)
        self._expand(dt)

    def squeeze(self, distance):
        """Moves every edge inwards by distance (not below the minimum size) – each tick a little, and all at once
        when the ship is hit."""
        min_width, min_height = settings.WINDOW_MIN_SIZE
        step_x = min(distance, max(0.0, (self.rect.width - min_width) / 2))
        step_y = min(distance, max(0.0, (self.rect.height - min_height) / 2))
        self.rect.inflate_ip(-2 * step_x, -2 * step_y)       # inflate keeps the centre in place

    def _expand(self, dt):
        for side, distance in self.pending.items():
            step = min(distance, settings.PUSH_SPEED * dt)
            if step <= 0:
                continue
            self.pending[side] -= step
            if side == "left":
                self.rect.update(self.rect.left - step, self.rect.top, self.rect.width + step, self.rect.height)
            elif side == "right":
                self.rect.width += step
            elif side == "top":
                self.rect.update(self.rect.left, self.rect.top - step, self.rect.width, self.rect.height + step)
            else:
                self.rect.height += step
        self.rect = self.rect.clip(self.bounds)

    def push(self, side, distance):
        """Hit on an edge: it moves out by distance (smoothly, over the next ticks)."""
        self.pending[side] += distance

    def side_hit(self, point):
        """Which edge point has crossed ("left", "right", "top", "bottom") – or None while it's inside.
        Past a corner, the edge it is further beyond wins."""
        overshoot = {
            "left": self.rect.left - point[0],
            "right": point[0] - self.rect.right,
            "top": self.rect.top - point[1],
            "bottom": point[1] - self.rect.bottom,
        }
        side = max(overshoot, key=overshoot.get)
        return side if overshoot[side] > 0 else None

    def sides_within(self, point, radius):
        """The edges that are at most radius away from point (a point inside the arena)."""
        distance = {
            "left": point[0] - self.rect.left,
            "right": self.rect.right - point[0],
            "top": point[1] - self.rect.top,
            "bottom": self.rect.bottom - point[1],
        }
        return [side for side in SIDES if distance[side] <= radius]

    def contain(self, entity):
        """Keeps entity inside the arena (shrinking edges push it along). True if it touched an edge."""
        return keep_inside(entity.rect, self.rect)

    def draw(self, surface, offset):
        """Background and an outline along the edges (the arena fills the whole window)."""
        surface.fill(settings.BACKGROUND)
        rect = self.window_rect().move(-offset[0], -offset[1])
        pygame.draw.rect(surface, settings.BORDER, rect, settings.BORDER_WIDTH)
