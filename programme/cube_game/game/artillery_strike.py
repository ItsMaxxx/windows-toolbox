"""
An artillery strike: a shell lobbed from the artillery's catapult onto a spot on the ground. It flies on an arc (Arc)
for delay seconds; meanwhile a red circle at the spot fills up (game/effects/target_marker.py). When it lands, update()
returns True once – the scene then hurts the ship and watchtowers in the circle and shows the blast
(game/effects/artillery_blast.py).

The view is from straight above, so a shell's height is shown by drawing it higher up on the screen than the spot it's
over (its shadow stays on the ground) – the catapult's arm in the artillery skin uses the same trick.

A splitter shell (split is a Split – the Cluster's) does no damage itself: where it lands it bursts into split.count
fragments that hop far apart, each a small strike of its own with its own circle (fragments()). Its landing spot only
gets a thin ring.
"""

import math
import random
from dataclasses import dataclass

import pygame

from game.effects.target_marker import draw_landing_marker, draw_target_marker

SHADOW_COLOR = (40, 40, 40)
SHELL_COLOR = (70, 80, 35)
SHELL_RING = (200, 210, 150)
GROW_HEIGHT = 400           # pixels of height at which a shell looks twice as big (closer to the viewer)


@dataclass(frozen=True)
class Arc:
    height: float               # pixels above the ground at the highest point (on top of the start height) …
    peak: float = 0.5           # … reached at this part of the way (0.5: halfway, less: rises steeply, falls long)
    start_height: float = 0.0   # the height it's thrown from (the catapult's bucket)

    def height_at(self, progress):
        """Height at progress (0 thrown … 1 landed): a curve through the peak, plus the start height sinking to 0."""
        peak = min(0.95, max(0.05, self.peak))
        part = (peak - progress) / peak if progress < peak else (progress - peak) / (1 - peak)
        return self.height * (1 - part ** 2) + self.start_height * (1 - progress)


@dataclass(frozen=True)
class Split:
    """How a splitter shell bursts (the Cluster's stats split_…)."""
    count: int                  # fragments
    spread: float               # each lands at most this far from where the shell came down …
    min_spread: float           # … and at least this far
    radius: float               # a fragment's circle
    damage: float
    time: float                 # seconds a fragment flies (its circle fills meanwhile)
    arc_height: float


class ArtilleryStrike:
    def __init__(self, start, center, radius, delay, damage, arc=Arc(0), split=None, size=14,
                 color=SHELL_COLOR):
        """start: where it's thrown from (on the ground), center: where it lands. delay: seconds of flight. split:
        a Split – then it bursts into fragments instead of hurting anything itself."""
        self.start = pygame.Vector2(start)
        self.center = pygame.Vector2(center)
        self.radius = radius
        self.delay = delay              # seconds until it lands
        self.damage = 0 if split else damage
        self.arc = arc
        self.split = split
        self.size = size
        self.color = color
        self.age = 0.0
        self.landed = False

    @property
    def progress(self):
        """0 just fired, 1 lands now."""
        return min(1.0, self.age / self.delay) if self.delay > 0 else 1.0

    def update(self, dt):
        """True in the tick it lands (only once)."""
        self.age += dt
        if self.landed or self.age < self.delay:
            return False
        self.landed = True
        return True

    def hits(self, rect):
        """True if any part of rect is inside the circle."""
        nearest = (min(max(self.center.x, rect.left), rect.right), min(max(self.center.y, rect.top), rect.bottom))
        return self.center.distance_to(nearest) <= self.radius

    def fragments(self):
        """A splitter shell that just landed: its fragments, evenly round the spot (a little off, so it isn't the same
        pattern every time). Other shells: none."""
        split = self.split
        if split is None:
            return []
        count = max(1, round(split.count))
        turn = random.uniform(0, 360)
        made = []
        for index in range(count):
            angle = turn + index * 360 / count + random.uniform(-0.15, 0.15) * 360 / count
            distance = random.uniform(min(split.min_spread, split.spread), split.spread)
            spot = self.center + pygame.Vector2(distance, 0).rotate(angle)
            made.append(ArtilleryStrike(self.center, spot, split.radius, split.time, split.damage,
                                        Arc(split.arc_height), size=self.size * 0.6, color=self.color))
        return made

    def position(self):
        """(over which spot on the ground it is, how high) right now."""
        progress = self.progress
        return self.start.lerp(self.center, progress), self.arc.height_at(progress)

    def draw(self, surface, offset):
        """On the ground: the circle (a thin ring for a splitter) and the shell's shadow."""
        if self.split:
            draw_landing_marker(surface, self.center - offset, self.radius)
        else:
            draw_target_marker(surface, self.center - offset, self.radius, self.progress, self.age)
        ground, height = self.position()
        shadow = self.size / 2 * (1 - 0.5 * min(1.0, height / GROW_HEIGHT))
        pygame.draw.circle(surface, SHADOW_COLOR, ground - offset, max(2, shadow))

    def draw_air(self, surface, offset):
        """The shell in the air (above the enemies) – higher up on the screen the higher it is, a bit bigger too."""
        ground, height = self.position()
        center = ground - offset - (0, height)
        radius = self.size / 2 * (1 + height / GROW_HEIGHT)
        pygame.draw.circle(surface, self.color, center, radius)
        pygame.draw.circle(surface, SHELL_RING, center, radius, 2)
        if self.split:                                  # the fragments inside, so it looks different
            for index in range(max(1, round(self.split.count))):
                dot = center + pygame.Vector2(radius * 0.45, 0).rotate(index * 360 / self.split.count + self.age * 400)
                pygame.draw.circle(surface, SHELL_RING, dot, max(1.5, radius * 0.2))


def arc_for(start, target, height, steepness, peak, start_height):
    """The arc for a throw from start to target: height plus steepness pixels per pixel of distance."""
    distance = math.dist(start, target)
    return Arc(height + steepness * distance, peak, start_height)
