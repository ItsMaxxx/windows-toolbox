"""
The radar (skill tree "Radar", under the watchtower): every `cooldown` seconds it looks for the biggest group of enemies
outside what you can see (the arena and the extra windows) and opens a light blue window over it for `duration`
seconds – size × size pixels, without a frame (Engine.open_view, drawn by the scene). If there's no enemy out of sight
(on a monitor), it looks again every RETRY seconds.

Finding the group: the enemies out of sight are sorted into a grid of size × size cells; the fullest cell wins, the
window goes over the middle of the enemies around it (once more: everything within the window around that middle).

The base values are in data/radar.json (explained in data/README.md), what each level of the skill tree's "Scan
size" / "Scan rate" / "Scan time" adds in data/skilltree.json; reload() reads radar.json again – the game menu calls it
every time it opens (via difficulty.reload()).
"""

import json
from pathlib import Path

import pygame

FILE = Path(__file__).resolve().parents[1] / "data" / "radar.json"
DEFAULTS = {
    "size": 150,                    # side length of the window (pixels)
    "cooldown": 4,                  # seconds from the end of one scan to the next …
    "duration": 2.5,                # seconds a scan stays open
    "min_cooldown": 1,              # … never shorter than this, whatever the skill tree adds
}
MUST_BE_POSITIVE = {"size", "cooldown", "duration", "min_cooldown"}
STATS = dict(DEFAULTS)
RETRY = 1.0                         # seconds until it looks again when there was nothing to scan


def reload(warnings):
    """Reads data/radar.json again into STATS. Problems are added to warnings (a list)."""
    try:
        data = json.loads(FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("should be { … }")
    except (OSError, ValueError) as error:
        warnings.append(f"radar.json: can't be read ({error}) – using built-in values")
        data = {}
    STATS.clear()
    STATS.update(DEFAULTS)
    for name, value in data.items():
        if name not in DEFAULTS:
            warnings.append(f"radar.json: unknown value \"{name}\" – ignored")
        elif (isinstance(value, bool) or not isinstance(value, (int, float))
              or value < 0 or (value == 0 and name in MUST_BE_POSITIVE)):
            warnings.append(f"radar.json {name}: {json.dumps(value)} is not valid – using {DEFAULTS[name]}")
        else:
            STATS[name] = value


class Radar:
    def __init__(self, more_size=0, more_cooldown=0, more_duration=0):
        """What the skill tree's radar upgrades add to the base values (pixels, seconds, seconds)."""
        stats = STATS
        self.size = max(1, round(stats["size"] + more_size))
        self.cooldown = max(stats["min_cooldown"], stats["cooldown"] + more_cooldown)
        self.duration = max(0.1, stats["duration"] + more_duration)
        self.timer = self.cooldown          # seconds until the next scan
        self.rect = None                    # the scanned area while a scan is open (screen pixels)
        self.remaining = 0.0                # seconds the open scan stays
        self.view = None                    # its window (set by the scene) – None while closed / if there's none

    def update(self, dt, enemies, seen, desktop):
        """seen: the rectangles the player already sees. Returns "open" when a scan starts (rect is set), "close" when
        it ends, else None."""
        if self.rect is not None:
            self.remaining -= dt
            if self.remaining > 0:
                return None
            self.rect, self.timer = None, self.cooldown
            return "close"
        self.timer -= dt
        if self.timer > 0:
            return None
        self.rect = self.find_group(enemies, seen, desktop)
        if self.rect is None:
            self.timer = RETRY
            return None
        self.remaining = self.duration
        return "open"

    def find_group(self, enemies, seen, desktop):
        """The window over the biggest group of enemies out of sight (see the top of this file) – None if there's
        none."""
        hidden = [pygame.Vector2(enemy.rect.center) for enemy in enemies
                  if desktop.contains(enemy.rect.center)
                  and not any(rect.collidepoint(enemy.rect.center) for rect in seen)]
        if not hidden:
            return None
        cells = {}
        for point in hidden:
            cells.setdefault((int(point.x // self.size), int(point.y // self.size)), []).append(point)
        group = max(cells.values(), key=len)
        middle = sum(group, pygame.Vector2()) / len(group)
        rect = pygame.Rect(0, 0, self.size, self.size)
        rect.center = (round(middle.x), round(middle.y))
        group = [point for point in hidden if rect.collidepoint(point)] or group      # also those across the cell edge
        middle = sum(group, pygame.Vector2()) / len(group)
        rect.center = (round(middle.x), round(middle.y))
        area = desktop.area_at(rect.center)
        return rect.clamp(area).clip(area)
