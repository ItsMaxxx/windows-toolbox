"""
Living Window: a window that's alive. It drifts to the arena, docks at one of its edges – reaching overlap pixels into
it – and then glides along the edges, round and round the arena. It keeps growing; every spawn_interval seconds an
enemy comes out of it (one of the types the level brings right now). Once it has grown to max_size, it bursts: a
whole group comes out at once (burst_count), and it's gone.

It has no hit points – its size is its life. Every hit shrinks it (damage × shrink_per_damage pixels, after its
armor); below min_size it dies. So shoot it early, while it's small. Out there you see it through a small window of
its own (like the Pusher's – the scene opens it, see PlayScene.update_lookouts).

Other enemies walk through it (solid = False), touching it doesn't hurt.

Gliding: where it is along the arena's edges is one number, the way round from the top left corner, clockwise
(top, right, bottom, left) – so going round a corner is just counting on.
"""

import random

import pygame

from game import armor, settings
from game.enemies.enemy import HIT_FLASH, Enemy
from game.skins.living_window import LivingWindowSkin

DRIFT, DOCKED = "drift", "docked"


def clamp(value, low, high):
    return min(max(value, low), high)


class LivingWindow(Enemy):
    key = "living_window"
    name = "Living Window"
    skin = LivingWindowSkin()
    solid = False
    stats = {                       # fallback – see data/enemies.json
        "base_hp": 1, "speed": 60, "size": 80, "contact_damage": 0,
        "min_size": 30,             # smaller than this: dead
        "max_size": 220,            # this big: it bursts
        "grow_speed": 6,            # pixels per second it grows
        "shrink_per_damage": 6,     # pixels smaller per point of damage
        "overlap": 30,              # how far it reaches into the arena while docked
        "slide_speed": 25,          # pixels per second it glides along the edges
        "spawn_interval": 5,        # seconds between two enemies coming out
        "burst_count": 8,           # enemies coming out when it bursts
    }

    def __init__(self, position, roster=None):
        super().__init__(position, roster)
        self.state = DRIFT
        self.side = None            # the arena's edge it's docked at …
        self.along = 0.0            # … and where along it (screen pixels: x on top/bottom, y on left/right)
        self.turn = random.choice((1, -1))              # 1: clockwise round the arena, -1: the other way
        self.timer = self.stat("spawn_interval")
        self.view = None            # its own window out there (set by the scene)

    @property
    def body(self):
        """What its own window shows: all of it."""
        return self.rect

    def take_damage(self, amount):
        """A hit shrinks it – below min_size it's dead."""
        hit = armor.reduce(amount, self.stat("armor"), settings.MIN_DAMAGE_SHARE) * self.damage_factor
        self.resize(self.rect.width - hit * self.stat("shrink_per_damage"))
        self.flash = HIT_FLASH
        if self.rect.width <= self.stat("min_size"):
            self.hp = 0

    def resize(self, size):
        center = self.rect.center
        self.rect.size = (max(1.0, size), max(1.0, size))
        self.rect.center = center

    def act(self, dt, ship):
        if self.arena is None:
            return []
        self.aim = self.direction_to(ship.rect.center) or self.aim     # its eye follows the ship
        self.resize(self.rect.width + self.stat("grow_speed") * dt)
        if self.rect.width >= self.stat("max_size"):
            self.burst()
            return []
        if self.state == DRIFT:
            self.drift(dt)
        else:
            self.glide(dt)
            self.timer -= dt
            if self.timer <= 0:
                self.timer = self.stat("spawn_interval")
                self.release(1)
        return []

    def drift(self, dt):
        """Towards the nearest edge of the arena; once there, it docks."""
        center = pygame.Vector2(self.rect.center)
        side = self.arena.side_hit(center) or "top"
        along = center.y if side in ("left", "right") else center.x
        spot = self.spot(side, along)
        offset = spot - center
        step = self.stat("speed") * self.speed_factor * dt
        if offset.length() <= step:
            self.state, self.side, self.along = DOCKED, side, along
            self.rect.center = spot
            return
        self.rect.center = center + offset.normalize() * step

    def glide(self, dt):
        """On along the edges – past a corner onto the next one."""
        arena = self.arena.rect
        width, height = arena.width, arena.height
        lengths = {"top": width, "right": height, "bottom": width, "left": height}
        order = ("top", "right", "bottom", "left")
        # where it is, counted clockwise from the top left corner
        into = {"top": clamp(self.along, arena.left, arena.right) - arena.left,
                "right": clamp(self.along, arena.top, arena.bottom) - arena.top,
                "bottom": arena.right - clamp(self.along, arena.left, arena.right),
                "left": arena.bottom - clamp(self.along, arena.top, arena.bottom)}[self.side]
        way = sum(lengths[side] for side in order[:order.index(self.side)]) + into
        way = (way + self.turn * self.stat("slide_speed") * self.speed_factor * dt) % (2 * (width + height))
        for side in order:
            if way <= lengths[side]:
                break
            way -= lengths[side]
        self.side = side
        self.along = {"top": arena.left + way, "right": arena.top + way, "bottom": arena.right - way,
                      "left": arena.bottom - way}[side]
        self.rect.center = self.spot(self.side, self.along)

    def spot(self, side, along):
        """Its centre when docked at side, at along: reaching overlap pixels into the arena."""
        arena = self.arena.rect
        half = self.rect.width / 2
        reach = self.stat("overlap")
        if side in ("left", "right"):
            y = min(max(along, arena.top), arena.bottom)
            return pygame.Vector2(arena.left - half + reach if side == "left" else arena.right + half - reach, y)
        x = min(max(along, arena.left), arena.right)
        return pygame.Vector2(x, arena.top - half + reach if side == "top" else arena.bottom + half - reach)

    def release(self, count):
        """count enemies out of it – the types the level brings right now (via the spawner the scene gave it)."""
        if self.spawner is None:
            return
        from game.enemies.roster import ENEMY_TYPES         # imported here: the roster imports this file
        weights = {key: weight for key, weight in self.spawner.weights().items()
                   if key != self.key and not getattr(ENEMY_TYPES[key], "spawns_outside", False)}
        if not weights:
            return
        for _ in range(count):
            key = random.choices(list(weights), weights=list(weights.values()))[0]
            spot = pygame.Vector2(self.rect.center) + pygame.Vector2(random.uniform(0, self.rect.width / 3), 0).rotate(
                random.uniform(0, 360))
            enemy = self.spawner.create(key, spot)
            enemy.arena, enemy.spawner = self.arena, self.spawner
            self.spawned.append(enemy)

    def burst(self):
        """Grown too big: a whole group comes out, and it's gone (no loot)."""
        self.release(round(self.stat("burst_count")))
        self.hp = 0
        self.drops_loot = False

    def draw(self, surface, offset):
        self.skin.draw_window(surface, self, self.rect.move(-offset[0], -offset[1]))
