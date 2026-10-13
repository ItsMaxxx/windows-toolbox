"""
Spawner: creates enemies at regular intervals, far outside the window on the desktop – out of the player's reach –
from where they come in. The intervals get shorter over time; which type comes is random, weighted.

Swarms: once per second there's a small chance that a whole group of basic enemies appears at one spot. The longer
the game goes on, the more likely swarms get and the bigger they are.
"""

import random

import pygame

from game.enemies.basic import BasicEnemy
from game.enemies.charger import Charger
from game.enemies.shooter import Shooter
from game.enemies.sniper import Sniper

TYPES = [(BasicEnemy, 50), (Charger, 20), (Shooter, 20), (Sniper, 10)]     # (type, weight)
FIRST_SPAWN = 2.0           # seconds until the first enemy
START_INTERVAL = 2.6        # seconds between enemies at the start …
MIN_INTERVAL = 0.9          # … getting shorter down to this
INTERVAL_DROP = 0.012       # seconds less per second played
SPAWN_DISTANCE = (250, 500) # pixels beyond the window's corners
MAX_ENEMIES = 25            # regular spawns stop at this many enemies …
MAX_WITH_SWARMS = 120       # … swarms may go up to this many

SWARM_START_CHANCE = 0.02   # chance per second at the start …
SWARM_CHANCE_GROWTH = 0.0008    # … plus this much per second played …
SWARM_MAX_CHANCE = 0.15     # … up to this
SWARM_START_SIZE = 6        # enemies in a swarm at the start …
SWARM_GROWTH_TIME = 10      # … one more every this many seconds …
SWARM_MAX_SIZE = 40         # … up to this
SWARM_MIN_GAP = 6           # seconds at least between two swarms
SWARM_SPACING = 14          # how tightly packed a swarm is (pixels)


class Spawner:
    def __init__(self, bounds):
        """bounds: where enemies may appear (the desktop)."""
        self.bounds = pygame.Rect(bounds)
        self.timer = FIRST_SPAWN
        self.elapsed = 0.0
        self.swarm_timer = 1.0              # next swarm roll in … seconds
        self.since_swarm = SWARM_MIN_GAP    # seconds since the last swarm

    @property
    def interval(self):
        return max(MIN_INTERVAL, START_INTERVAL - INTERVAL_DROP * self.elapsed)

    @property
    def swarm_chance(self):
        return min(SWARM_MAX_CHANCE, SWARM_START_CHANCE + SWARM_CHANCE_GROWTH * self.elapsed)

    @property
    def swarm_size(self):
        return min(SWARM_MAX_SIZE, SWARM_START_SIZE + int(self.elapsed / SWARM_GROWTH_TIME))

    def update(self, dt, arena, enemy_count):
        """Returns the new enemies (a list, usually empty). arena: the window's rectangle on the screen."""
        self.elapsed += dt
        self.since_swarm += dt
        new = self.swarm(arena, enemy_count, dt)
        self.timer -= dt
        if self.timer <= 0 and enemy_count + len(new) < MAX_ENEMIES:
            self.timer = self.interval
            enemy_type = random.choices([t for t, _ in TYPES], weights=[w for _, w in TYPES])[0]
            new.append(enemy_type(self.spawn_point(arena)))
        return new

    def swarm(self, arena, enemy_count, dt):
        """Once per second: maybe a swarm – a group of basic enemies packed around one spawn point."""
        self.swarm_timer -= dt
        if self.swarm_timer > 0:
            return []
        self.swarm_timer += 1.0
        if self.since_swarm < SWARM_MIN_GAP or random.random() >= self.swarm_chance:
            return []
        size = min(self.swarm_size, MAX_WITH_SWARMS - enemy_count)
        if size <= 0:
            return []
        self.since_swarm = 0.0
        center = self.spawn_point(arena)
        radius = SWARM_SPACING * size ** 0.5
        swarm = []
        for _ in range(size):
            point = center + pygame.Vector2(random.uniform(0, radius), 0).rotate(random.uniform(0, 360))
            point.x = min(max(point.x, self.bounds.left), self.bounds.right - 1)
            point.y = min(max(point.y, self.bounds.top), self.bounds.bottom - 1)
            swarm.append(BasicEnemy(point))
        return swarm

    def spawn_point(self, arena):
        """A random point around the window, SPAWN_DISTANCE beyond its corners, on the desktop."""
        center = pygame.Vector2(arena.center)
        reach = pygame.Vector2(arena.size).length() / 2           # centre to corner
        for _ in range(20):
            point = center + pygame.Vector2(reach + random.uniform(*SPAWN_DISTANCE), 0).rotate(random.uniform(0, 360))
            if self.bounds.collidepoint(point):
                return point
        # the window fills almost the whole desktop: put it on the desktop's edge
        return pygame.Vector2(min(max(point.x, self.bounds.left), self.bounds.right - 1),
                              min(max(point.y, self.bounds.top), self.bounds.bottom - 1))
