"""
Points of interest: things that appear on the desktop, out of sight (not in the arena or an extra window). Until
someone has seen one, it's only a "?" – a marker at the window's edge shows where it is. Once it's in sight (the arena,
a watchtower's window, a radar scan), it's revealed: then you know what it is.

The ship can't leave the arena, so a point is reached when the arena or a standing watchtower's window covers it:
push the walls that way, or throw a tower there. Radar scans only reveal.

Finds (good for the player) come from the skill tree ("Points of interest" behind the watchtower: how often, which
kinds; the radar's "Find" upgrade lets a scan look for one now and then):
  - chest:  a pile of stars,
  - magnet: for a while every star and core anywhere flies to the ship,
  - repair: every edge springs out a bit (no armor, no falloff).
Threats come from the level (a phase's "points"):
  - totem: while it stands, every enemy is faster and hits harder (violet outline) – reach it to break it,
  - nest:  keeps sending out enemies (the level's types) – reach it to break it,
  - storm: a wide area; while the arena reaches into it, the walls move in faster. It can't be broken, only waited out.
Every point vanishes after its lifetime.

All the values are in data/points.json (explained in data/README.md); reload() reads it again – the game menu calls it
every time it opens (via difficulty.reload()).
"""

import copy
import json
import math
import random
from pathlib import Path

import pygame

from engine.sprite_cache import PICTURES
from engine.ui import draw_text
from game.effects.explosion import Explosion
from game.enemies.buff import Buff
from game.enemies.roster import ENEMY_TYPES
from game.icons import STAR_COLOR, draw_star

FILE = Path(__file__).resolve().parents[1] / "data" / "points.json"
DEFAULTS = {
    "finds": {"first": 25, "interval": 45, "min_interval": 15, "lifetime": 40},    # the skill tree's finds
    "place": {"min_distance": 200, "max_distance": 650},     # pixels beyond the arena where a point appears
    "chest": {"stars": 20},
    "magnet": {"time": 8, "speed": 900},
    "repair": {"push": 60},
    "totem": {"lifetime": 50, "speed": 1.15, "damage": 1.2},
    "nest": {"lifetime": 40, "interval": 2.5},
    "storm": {"lifetime": 30, "radius": 220, "shrink_speed": 10},
}
MUST_BE_POSITIVE = {"interval", "min_interval", "lifetime", "time", "speed", "radius", "max_distance"}
STATS = copy.deepcopy(DEFAULTS)
FINDS = ("chest", "magnet", "repair")       # good for the player – from the skill tree
THREATS = ("totem", "nest", "storm")        # bad – from the level
KINDS = FINDS + THREATS
NAMES = {"chest": "Star chest", "magnet": "Magnet", "repair": "Repair kit", "totem": "Totem", "nest": "Nest",
         "storm": "Storm"}
SIZE = 30                   # a point's square (pixels)
PLACE_TRIES = 30
FIND_COLOR = (110, 220, 140)
THREAT_COLOR = (235, 70, 70)
HIDDEN_COLOR = (235, 235, 235)
TOTEM_COLOR = (170, 90, 255)            # also the outline of the enemies it buffs
STORM_FILL = (70, 110, 190, 70)
STORM_RIM = (140, 185, 255)
DAMAGE_STATS = ("contact_damage", "projectile_damage", "blast_damage")
MARKER_INSET = 10           # the arrows at the window's edge: distance from it …
ARROW = 9                   # … and their size


def reload(warnings):
    """Reads data/points.json again into STATS. Problems are added to warnings (a list)."""
    try:
        data = json.loads(FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("should be { … }")
    except (OSError, ValueError) as error:
        warnings.append(f"points.json: can't be read ({error}) – using built-in values")
        data = {}
    STATS.clear()
    STATS.update(copy.deepcopy(DEFAULTS))
    for key in data.keys() - DEFAULTS.keys():
        warnings.append(f"points.json: unknown entry \"{key}\" – ignored")
    for key, values in STATS.items():
        entry = data.get(key, {})
        if not isinstance(entry, dict):
            warnings.append(f"points.json {key}: should be {{ … }} – using built-in values")
            continue
        for name, value in entry.items():
            if name not in values:
                warnings.append(f"points.json {key}: unknown value \"{name}\" – ignored")
            elif (isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0
                  or (value == 0 and name in MUST_BE_POSITIVE)):
                warnings.append(f"points.json {key}.{name}: {json.dumps(value)} is not valid – using {values[name]}")
            else:
                values[name] = value


class Point:
    """One point of interest in the world."""

    def __init__(self, kind, position):
        self.kind = kind
        self.position = pygame.Vector2(position)
        values = STATS[kind] if kind in THREATS else STATS["finds"]
        self.lifetime = values["lifetime"]
        self.age = 0.0
        self.revealed = False
        self.done = False
        self.timer = STATS["nest"]["interval"] if kind == "nest" else 0.0     # the nest's next enemy
        self.buffs = []                                                     # the totem's, on every enemy

    @property
    def threat(self):
        return self.kind in THREATS

    @property
    def rect(self):
        rect = pygame.Rect(0, 0, SIZE, SIZE)
        rect.center = self.position
        return rect

    def in_sight(self, rects):
        """Seen in one of rects: its middle – the storm as soon as its area reaches into one."""
        if self.kind == "storm":
            return any(distance_to_rect(self.position, rect) < self.radius for rect in rects)
        return any(rect.collidepoint(self.position) for rect in rects)

    @property
    def radius(self):
        """How far it reaches: the storm's area, else just its square."""
        return STATS["storm"]["radius"] if self.kind == "storm" else SIZE / 2

    def draw(self, surface, offset):
        center = self.position - offset
        left = 1 - self.age / self.lifetime
        if self.kind == "storm":
            draw_storm_area(surface, center, self.radius, self.age)
        color = THREAT_COLOR if self.threat else FIND_COLOR
        pygame.draw.arc(surface, color, pygame.Rect(center.x - SIZE * 0.8, center.y - SIZE * 0.8, SIZE * 1.6,
                                                    SIZE * 1.6), math.pi / 2, math.pi / 2 + 2 * math.pi * left, 2)
        draw_point_icon(surface, center, self.kind, SIZE)


class Points:
    """The run's points of interest: new finds now and then (finds: from the skill tree, None without), the level's
    threats, what they do, and their markers."""

    def __init__(self, finds=None):
        """finds: {"kinds": [...], "interval": seconds, "find_chance": 0 … 1} from skill_tree.start_finds()."""
        self.finds = finds
        self.points = []
        self.timer = STATS["finds"]["first"]
        self.magnet = 0.0               # seconds the magnet still pulls

    def update(self, dt, scene):
        if self.finds and self.finds["kinds"]:
            self.timer -= dt
            if self.timer <= 0:
                self.timer = max(STATS["finds"]["min_interval"], self.finds["interval"])
                self.place(random.choice(self.finds["kinds"]), scene)
        for kind in scene.spawner.points:
            self.place(kind, scene)
        scene.spawner.points.clear()

        field = scene.field()
        scanned = scene.radar.rect if scene.radar is not None else None
        reach = [scene.arena.rect] + [tower.area for tower in scene.towers if tower.area is not None]
        storm = 0.0
        for point in self.points:
            point.age += dt
            if not point.revealed and (point.in_sight(field.sight)
                                       or (scanned is not None and point.in_sight([scanned]))):
                point.revealed = True
            if point.kind == "storm":
                if distance_to_rect(point.position, scene.arena.rect) < point.radius:
                    storm += STATS["storm"]["shrink_speed"]
            elif any(area.collidepoint(point.position) for area in reach):
                point.revealed = True
                self.reach(point, scene)
            elif point.kind == "nest":
                point.timer -= dt
                if point.timer <= 0:
                    point.timer = STATS["nest"]["interval"]
                    self.hatch(point, scene)
            if point.age >= point.lifetime:
                point.done = True
        scene.arena.storm_speed = storm
        for point in self.points:
            if point.done and point.buffs:
                scene.roster.buffs = [buff for buff in scene.roster.buffs if buff not in point.buffs]
        self.points = [point for point in self.points if not point.done]

        self.magnet = max(0.0, self.magnet - dt)
        if self.magnet:
            ship = pygame.Vector2(scene.ship.rect.center)
            step = STATS["magnet"]["speed"] * dt
            for pickup in scene.pickups:
                to_ship = ship - pickup.rect.center
                if to_ship.length() > 1:
                    pickup.rect.move_ip(to_ship.normalize() * min(step, to_ship.length()))

    def place(self, kind, scene):
        """A new point of kind somewhere out of sight, min_distance … max_distance beyond the arena, on a monitor."""
        arena = scene.arena.rect
        center = pygame.Vector2(arena.center)
        reach = pygame.Vector2(arena.size).length() / 2
        sight = scene.field().sight
        low, high = STATS["place"]["min_distance"], max(STATS["place"]["min_distance"], STATS["place"]["max_distance"])
        for _ in range(PLACE_TRIES):
            spot = center + pygame.Vector2(reach + random.uniform(low, high), 0).rotate(random.uniform(0, 360))
            area = pygame.Rect(0, 0, SIZE, SIZE)
            area.center = spot
            if scene.desktop.covers(area) and not any(rect.colliderect(area) for rect in sight):
                point = Point(kind, spot)
                if kind == "totem":
                    values = STATS["totem"]
                    point.buffs = ([Buff("speed", factor=values["speed"], source="totem", color=TOTEM_COLOR)]
                                   + [Buff(stat, factor=values["damage"], source="totem") for stat in DAMAGE_STATS])
                    scene.roster.buffs += point.buffs
                self.points.append(point)
                return point
        return None                     # no room out of sight (the arena fills the screen) – no point this time

    def reach(self, point, scene):
        """The arena or a watchtower got to it: a find does its thing, a totem or nest breaks."""
        point.done = True
        name = NAMES[point.kind]
        if point.kind == "chest":
            scene.ship.stars += STATS["chest"]["stars"]
            scene.notify(f"{name}: +{STATS['chest']['stars']:g} stars")
        elif point.kind == "magnet":
            self.magnet = STATS["magnet"]["time"]
            scene.notify(f"{name}: everything flies to you")
        elif point.kind == "repair":
            for side in scene.arena.pending:
                scene.arena.pending[side] += STATS["repair"]["push"]
            scene.notify(f"{name}: the walls spring out")
        else:
            scene.notify(f"{name} destroyed")
        scene.explosions.append(explosion(point))

    @staticmethod
    def hatch(point, scene):
        """The nest sends out one enemy – one of the types the level brings right now."""
        weights = scene.spawner.weights()
        if not weights:
            return
        key = random.choices(list(weights), weights=list(weights.values()))[0]
        if getattr(ENEMY_TYPES[key], "spawns_outside", False):
            key = "basic"               # a Pusher has to come from beyond the map
        enemy = scene.spawner.create(key, point.position)
        enemy.arena, enemy.spawner = scene.arena, scene.spawner
        scene.enemies.append(enemy)

    def draw(self, surface, offset, area):
        for point in self.points:
            if point.rect.inflate(2 * point.radius, 2 * point.radius).colliderect(area):
                point.draw(surface, offset)

    def draw_markers(self, surface, offset, field):
        """An arrow at the window's edge for every point out of sight, pointing at it – with a "?" until it's
        revealed, then its icon (green: a find, red: a threat). A storm reaching into the window needs none."""
        inside = surface.get_rect().inflate(-2 * MARKER_INSET, -2 * MARKER_INSET)
        middle = pygame.Vector2(inside.center)
        for point in self.points:
            if point.in_sight(field.sight):
                continue
            position = point.position - offset
            spot = pygame.Vector2(min(max(position.x, inside.left), inside.right),
                                  min(max(position.y, inside.top), inside.bottom))
            direction = position - spot
            direction = direction.normalize() if direction.length_squared() else (spot - middle).normalize()
            color = HIDDEN_COLOR if not point.revealed else THREAT_COLOR if point.threat else FIND_COLOR
            tip = spot + direction * ARROW
            side = direction.rotate(90) * ARROW * 0.7
            pygame.draw.polygon(surface, color, [tip, spot - side, spot + side])
            label = spot - direction * (ARROW + 8)
            if point.revealed:
                draw_point_icon(surface, label, point.kind, 16)
            else:
                draw_text(surface, "?", 24, color, center=label)


def distance_to_rect(point, rect):
    dx = max(rect.left - point[0], 0, point[0] - rect.right)
    dy = max(rect.top - point[1], 0, point[1] - rect.bottom)
    return math.hypot(dx, dy)


def explosion(point):
    return Explosion(point.position, SIZE * 2, THREAT_COLOR if point.threat else FIND_COLOR)


# --- looks ---

def draw_storm_area(surface, center, radius, age):
    """The storm: a blue-grey disc with a pulsing rim and turning arcs."""
    disc = PICTURES.get(("storm", round(radius)), lambda: storm_disc(round(radius)))
    surface.blit(disc, (center[0] - disc.get_width() / 2, center[1] - disc.get_height() / 2))
    pulse = 0.6 + 0.4 * math.sin(age * 4)
    pygame.draw.circle(surface, [round(channel * pulse) for channel in STORM_RIM], center, radius, 3)
    for index in range(5):
        start = age * (1.2 + 0.25 * index) + index * 1.3
        reach = radius * (0.3 + 0.14 * index)
        pygame.draw.arc(surface, STORM_RIM, pygame.Rect(center[0] - reach, center[1] - reach, 2 * reach,
                                                        2 * reach), start, start + 1.4, 2)


def storm_disc(radius):
    disc = pygame.Surface((2 * radius, 2 * radius), pygame.SRCALPHA)
    pygame.draw.circle(disc, STORM_FILL, (radius, radius), radius)
    return disc


def draw_point_icon(surface, center, kind, size):
    """A point's icon, size pixels across."""
    x, y = center
    half = size / 2
    if kind == "chest":
        box = pygame.Rect(0, 0, size, size * 0.7)
        box.center = (x, y + size * 0.1)
        pygame.draw.rect(surface, (150, 95, 45), box, border_radius=3)
        pygame.draw.line(surface, (90, 55, 25), (box.left, box.top + box.height * 0.35),
                         (box.right - 1, box.top + box.height * 0.35), 2)
        draw_star(surface, (x, y + size * 0.1), size * 0.25, STAR_COLOR)
    elif kind == "magnet":
        width = max(3, round(size * 0.22))
        bow = pygame.Rect(x - half * 0.8, y - half * 0.8, size * 0.8, size * 0.8)
        pygame.draw.arc(surface, (220, 50, 50), bow, math.pi, 2 * math.pi, width)
        for edge in (bow.left + width / 2, bow.right - width / 2):
            pygame.draw.line(surface, (220, 50, 50), (edge, y), (edge, y - half * 0.6), width)
            pygame.draw.line(surface, (230, 230, 230), (edge, y - half * 0.6), (edge, y - half * 0.85), width)
    elif kind == "repair":
        thick = max(3, round(size * 0.28))
        pygame.draw.rect(surface, FIND_COLOR, (x - half * 0.8, y - thick / 2, size * 0.8, thick))
        pygame.draw.rect(surface, FIND_COLOR, (x - thick / 2, y - half * 0.8, thick, size * 0.8))
    elif kind == "totem":
        pole = pygame.Rect(0, 0, size * 0.45, size)
        pole.center = center
        pygame.draw.rect(surface, TOTEM_COLOR, pole, border_radius=3)
        pygame.draw.circle(surface, (30, 10, 50), (x, y - size * 0.18), size * 0.12)
        pygame.draw.circle(surface, (255, 255, 255), (x, y - size * 0.18), max(1, size * 0.05))
    elif kind == "nest":
        pygame.draw.circle(surface, (120, 30, 30), center, half * 0.9)
        for index in range(5):
            spot = pygame.Vector2(x, y) + pygame.Vector2(half * 0.45, 0).rotate(index * 72)
            pygame.draw.circle(surface, THREAT_COLOR, spot, max(1.5, size * 0.09))
    elif kind == "storm":
        for index in range(3):
            reach = half * (0.35 + 0.3 * index)
            pygame.draw.arc(surface, (170, 180, 205), pygame.Rect(x - reach, y - reach, 2 * reach, 2 * reach),
                            index * 2.1, index * 2.1 + 3.6, 2)
