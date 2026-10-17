"""
Spawner: creates enemies at regular intervals, far outside the window on the desktop – out of the player's reach –
from where they come in. The intervals get shorter over time; which type comes is random, weighted – each type only
once its time has come ("after"), and its weight grows by "growth" every minute after that, so the stronger types
become more and more common.

Phases: stretches of the run (from … to …) that change the weights – e.g. three times as many snipers for 40 seconds –
and/or the time between two enemies, buff the enemies (as roster buffs that last as long as the phase) and/or bring a
few extra enemies once, when they start (each at its own spawn point). A phase can announce itself on screen: its text
goes into announcements, which the scene shows and empties. A phase with options ("one_of") gets one of them, picked at
random when the run starts – so a level doesn't play the same every time. A phase with "every" starts again and again
(repeat_phases()): each time it's added to the phases as a phase of its own, with its options picked anew.

Swarms: once per second there's a small chance that a whole group of enemies appears at one spot. A kind of swarm
can have a leader (a Commander): it comes right in the swarm's middle, the others around it. Every enemy of a swarm
gets the same swarm object (enemy.swarm), so the scene can mark the group as one. The longer the game
goes on, the more likely swarms get and the bigger they are. A difficulty can have several kinds of swarms (basic,
charger, …), each with its own chance and timing. A swarm appears further away than single enemies: its centre is on
the edge of the map (the desktop), so part of it is still beyond the edge and walks in from there – and even its
nearest enemy is at least SWARM_GAP away from the window.

Evolutions: every enemy the spawner makes – alone or in a swarm – may come as its evolution instead (a Fat Guy instead
of a Basic, …), with the chance the level gives for its type right now (its "evolutions", growing over time).

The extra windows (watchtowers, radar) count as part of what the player sees: no enemy appears inside one, and swarms
keep SWARM_GAP from them, too.

All the numbers come from the difficulty (data/difficulties/*.json, see game/difficulty.py); the enemies themselves
are made by the run's roster, with the run's values (roster.py).
"""

import math
import random
from dataclasses import replace

import pygame

from game.difficulty import chosen, evolution_chance
from game.enemies.buff import Buff
from game.enemies.roster import ENEMY_TYPES, EVOLUTIONS, apply

SPAWN_DISTANCE = (250, 500) # pixels beyond the window's corners
SWARM_SPACING = 14          # how tightly packed a swarm is (pixels)
SWARM_GAP = 300             # pixels at least between a swarm's nearest enemy and the window
SWARM_TRIES = 24            # random directions tried to find an edge far enough away
MIN_INTERVAL = 0.1          # seconds between enemies, whatever the phases say
OUTSIDE_DISTANCE = 60       # pixels beyond the edge of the map where a Pusher appears


class Spawner:
    def __init__(self, desktop, difficulty, roster):
        """desktop: where enemies may appear (on a monitor – engine/desktop.py). difficulty: a Difficulty
        (game/difficulty.py). roster: the run's EnemyRoster, which makes the enemies."""
        self.desktop = desktop
        self.roster = roster
        self.spawning = difficulty.spawning
        self.enemies = difficulty.enemies
        self.swarms = difficulty.swarms
        self.phases = [chosen(phase) for phase in difficulty.phases if not phase.every]   # one_of: picked now
        self.repeating = [[phase, phase.start] for phase in difficulty.phases if phase.every]  # [phase, next start]
        self.evolutions = difficulty.evolutions
        self.timer = self.spawning.first_spawn
        self.elapsed = 0.0
        self.swarm_timer = 1.0                  # next swarm roll in … seconds
        self.since_swarm = [swarms.min_gap for swarms in self.swarms]   # per kind: seconds since its last swarm
        self.started = set()                    # indexes of the phases that have begun
        self.announcements = []                 # texts of phases that just began – the scene shows and empties it
        self.points = []                        # kinds of points of interest phases just placed – game/points.py
        self.windows = []                       # the extra windows' rectangles (set by update())

    @property
    def interval(self):
        """Seconds between two enemies right now: the level's (getting shorter over time), changed by the active
        phases' spawn_interval (in file order) – a phase may go below min_interval."""
        spawning = self.spawning
        interval = max(spawning.min_interval, spawning.start_interval - spawning.interval_drop * self.elapsed)
        for phase in self.active_phases():
            if phase.spawn_interval:
                interval = apply(interval, *phase.spawn_interval)
        return max(MIN_INTERVAL, interval)

    def swarm_chance(self, swarms):
        return min(swarms.max_chance, swarms.start_chance + swarms.chance_growth * self.elapsed)

    def swarm_size(self, swarms):
        return min(swarms.max_size, swarms.start_size + int(self.elapsed / swarms.growth_time))

    def active_phases(self):
        return [phase for phase in self.phases
                if phase.start <= self.elapsed and (phase.end is None or self.elapsed < phase.end)]

    def weights(self):
        """type -> how likely it is right now (only types above 0): each entry's weight once its time has come, plus
        its growth per minute since then, changed by the active phases (in file order) – so a phase's "+20" can bring
        a type early, its "x3" only multiplies what's there."""
        weights = {}
        for entry in self.enemies:
            if self.elapsed >= entry.after:
                minutes = (self.elapsed - entry.after) / 60
                weights[entry.type] = weights.get(entry.type, 0) + entry.weight + entry.growth * minutes
        for phase in self.active_phases():
            for key, operation, number in phase.weights:
                weights[key] = apply(weights.get(key, 0), operation, number)
        return {key: weight for key, weight in weights.items() if weight > 0}

    def update(self, dt, arena, windows=()):
        """Returns the new enemies (a list, usually empty). arena: the window's rectangle on the screen, windows: the
        extra windows' rectangles (nothing appears in them)."""
        self.windows = list(windows)
        self.elapsed += dt
        self.repeat_phases()
        new = self.start_phases(arena)
        new += self.swarm(arena, dt)
        self.timer -= dt
        if self.timer <= 0:
            self.timer = self.interval
            weights = self.weights()
            if weights:
                key = random.choices(list(weights), weights=list(weights.values()))[0]
                new.append(self.create(key, self.point_for(key, arena)))
        return new

    def create(self, key, position):
        """An enemy of type key – or, with the level's chance for that type right now, its evolution."""
        chance = max((evolution_chance(entry, self.elapsed) for entry in self.evolutions if entry.type == key),
                     default=0.0)
        if chance and random.random() < chance:
            key = EVOLUTIONS[key]
        return self.roster.create(key, position)

    def repeat_phases(self):
        """Phases with "every" whose next time has come: a copy of each goes into the phases, starting now (as long as
        the first time, with one of its options picked anew)."""
        for entry in self.repeating:
            phase, start = entry
            while start <= self.elapsed:
                end = None if phase.end is None else start + phase.end - phase.start
                self.phases.append(replace(chosen(phase), start=start, end=end, every=0))
                start += phase.every
            entry[1] = start

    def start_phases(self, arena):
        """Phases whose time has come: their buffs go on all enemies (until the phase ends), their text is shown, a
        faster spawn_interval counts right away. Returns their extra enemies."""
        new = []
        for index, phase in enumerate(self.phases):
            if index in self.started or self.elapsed < phase.start:
                continue
            self.started.add(index)
            if phase.end is not None and self.elapsed >= phase.end:
                continue                        # already over (only if a single tick skipped all of it)
            duration = None if phase.end is None else phase.end - self.elapsed
            for target, stat, operation, number in phase.enemy_stats:
                add, factor = (number, 1) if operation == "add" else (0, number)
                self.roster.buffs.append(Buff(stat, add=add, factor=factor, duration=duration,
                                              target=None if target == "all" else target))
            if phase.announce:
                self.announcements.append(phase.announce)
            for key, count in phase.spawn:
                new += [self.create(key, self.point_for(key, arena)) for _ in range(count)]
            for kind, count in phase.points:
                self.points += [kind] * count
            if phase.spawn_interval:
                self.timer = min(self.timer, self.interval)     # don't wait out the old, longer gap
        return new

    def swarm(self, arena, dt):
        """Once per second, for each kind of swarm: maybe one – a group of enemies packed around one spawn point."""
        self.since_swarm = [seconds + dt for seconds in self.since_swarm]
        self.swarm_timer -= dt
        if self.swarm_timer > 0:
            return []
        self.swarm_timer += 1.0
        new = []
        for index, swarms in enumerate(self.swarms):
            if (self.elapsed < swarms.after or self.since_swarm[index] < swarms.min_gap
                    or random.random() >= self.swarm_chance(swarms)):
                continue
            self.since_swarm[index] = 0.0
            size = self.swarm_size(swarms)
            radius = SWARM_SPACING * size ** 0.5
            center = self.swarm_point(arena, radius)
            group = Swarm(swarms.type)
            hole = 0                                # the leader's place in the middle stays free
            if swarms.leader and random.random() < swarms.leader_chance:
                leader = self.roster.create(swarms.leader, center)
                leader.swarm = group
                new.append(leader)
                hole = leader.size
            for _ in range(size):
                point = center + pygame.Vector2(random.uniform(hole, radius + hole), 0).rotate(random.uniform(0, 360))
                enemy = self.create(swarms.type, point)             # beyond the map's edge is fine
                enemy.swarm = group
                new.append(enemy)
        return new

    def swarm_point(self, arena, radius):
        """Where a swarm's centre goes: on the edge of the map, in a random direction from the window – one that's at
        least SWARM_GAP + radius away from it and every extra window. If the map has no such edge (the window fills
        almost all of it), the farthest edge found, moved out beyond it as far as needed."""
        center = pygame.Vector2(arena.center)
        needed = SWARM_GAP + radius
        farthest, farthest_room, farthest_direction = None, -1.0, None
        for _ in range(SWARM_TRIES):
            direction = pygame.Vector2(1, 0).rotate(random.uniform(0, 360))
            point = center + direction * self.distance_to_edge(center, direction)
            room = self.room(point, arena)
            if room >= needed:
                return point
            if room > farthest_room:
                farthest, farthest_room, farthest_direction = point, room, direction
        point = farthest
        for _ in range(5):                      # each step gets at least as far as missing; a few are plenty
            room = self.room(point, arena)
            if room >= needed:
                break
            point = point + farthest_direction * (needed - room)
        return point

    def room(self, point, arena):
        """How far point is from what the player sees: the window and the extra windows."""
        return min(distance_to_rect(point, rect) for rect in [arena, *self.windows])

    def distance_to_edge(self, start, direction):
        """How far from start (inside the map) along direction until the edge of the map."""
        bounds = self.desktop.bounds
        steps = []
        if direction.x:
            steps.append(((bounds.right if direction.x > 0 else bounds.left) - start.x) / direction.x)
        if direction.y:
            steps.append(((bounds.bottom if direction.y > 0 else bounds.top) - start.y) / direction.y)
        return max(0.0, min(steps))

    def point_for(self, key, arena):
        """Where an enemy of type key appears: the Pusher beyond the edge of the map, the others around the window."""
        if getattr(ENEMY_TYPES[key], "spawns_outside", False):
            return self.outside_point(arena)
        return self.spawn_point(arena)

    def outside_point(self, arena):
        """A point OUTSIDE_DISTANCE beyond the edge of the map, in a random direction from the window."""
        center = pygame.Vector2(arena.center)
        direction = pygame.Vector2(1, 0).rotate(random.uniform(0, 360))
        return center + direction * (self.distance_to_edge(center, direction) + OUTSIDE_DISTANCE)

    def spawn_point(self, arena):
        """A random point around the window, SPAWN_DISTANCE beyond its corners, on a monitor – not in an extra
        window."""
        center = pygame.Vector2(arena.center)
        reach = pygame.Vector2(arena.size).length() / 2           # centre to corner
        for _ in range(20):
            point = center + pygame.Vector2(reach + random.uniform(*SPAWN_DISTANCE), 0).rotate(random.uniform(0, 360))
            if self.desktop.contains(point) and not any(window.collidepoint(point) for window in self.windows):
                return point
        # the window fills almost the whole desktop: put it on the nearest monitor's edge
        return self.desktop.clamp_point(point)


class Swarm:
    """One swarm: what its enemies share (enemy.swarm) – the type it's made of, for its marker."""

    def __init__(self, kind):
        self.kind = kind


def distance_to_rect(point, rect):
    """0 inside rect, else the distance to its nearest point."""
    dx = max(rect.left - point[0], 0, point[0] - rect.right)
    dy = max(rect.top - point[1], 0, point[1] - rect.bottom)
    return math.hypot(dx, dy)
