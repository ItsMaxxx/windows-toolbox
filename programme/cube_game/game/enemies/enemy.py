"""
Base class for all enemies. Every enemy type is a subclass (class Charger(Enemy): …) that inherits everything here
and only changes what's different: its key, stats, behaviour (act()) and skin. How it looks is entirely in its skin
(game/skins/) – this file and the subclasses only decide what it does.

Damage to the ship (contact_damage, shot_damage, blast_damage) is in pixels: how far the arena's edges move in on
average (Arena.hit). Watchtowers take the same numbers off their HP.

Stats (HP, speed, size, contact damage and every number of the behaviour) are read with self.stat("speed"): the value
for this run (data/enemies.json and the difficulty's enemy_stats, put together by the roster – see roster.py) with the
buffs on top (buff.py). The stats dict in each class is only the fallback if data/enemies.json lacks a value – the
real values are in that file. Buffed enemies glow (drawn by the skin).

The default behaviour – run straight at the ship – is in act(). update() is called every tick and returns the
projectiles the enemy fires (a list, usually empty). Enemies it creates (a Carrier's critters) go into self.spawned;
the scene takes them from there. Enemies often start outside the window: positions are screen pixels, so they simply
walk in from the desktop.

Enemies can't overlap: the scene pushes touching ones apart every tick, the heavier one moves less (see mass).

Facing: every enemy has a direction it faces (aim). Ranged enemies turn it towards the ship at a limited speed
(turn_towards, their stat "turn_speed" in degrees per second) and only shoot while the ship is within their
"fire_cone" in front of them (facing) – their shots go where they face, not straight at the ship. Fly round them fast
enough and they can't keep up.

Shots of the player first ask blocks(): an enemy can stop a shot without being hurt (the shield enemy's shield).

Tiers: the plain types are tier 1. Some have an evolution (tier 2, roster.EVOLUTIONS): a stronger version that can
spawn in its place on harder levels (the level's "evolutions"). Their skins get a dark frame inside the body.
"""

import pygame

from engine import Entity
from game.projectile import Projectile
from game.shot_stats import ShotStats
from game.skins.skin import Skin

HIT_FLASH = 0.1             # seconds an enemy flashes white after a hit


class Enemy(Entity):
    key = "enemy"           # its name in the data files
    name = "Enemy"
    tier = 1                # 2: the evolution of a tier 1 type (roster.EVOLUTIONS)
    skin = Skin()           # how it looks (game/skins/)
    drops_loot = True       # leaves a star (with the shop unlocked) and, rarely, a core when killed
    melee = False           # only fights by touching – then a watchtower nearby can lure it away from the ship
    shielded = False        # has a shield that can block the player's shots (blocks())
    stats = {               # fallback only – the real values are in data/enemies.json
        "max_hp": 1,
        "speed": 100,           # pixels per second
        "size": 28,             # pixels (square hitbox) – read at spawn
        "contact_damage": 25,   # pixels the edges move in when it touches the ship (0 = harmless to touch)
    }

    def __init__(self, position, roster=None):
        """roster: the run's EnemyRoster (where the values come from). None: the standard values, no difficulty."""
        if roster is None:
            from game.enemies.roster import EnemyRoster     # imported here: the roster imports every enemy type
            roster = EnemyRoster()
        self.roster = roster
        self.base = roster.stats[self.key]
        self.buffs = []         # on this enemy only (buffs on all enemies are in roster.buffs)
        size = self.stat("size")
        super().__init__(0, 0, size, size, self.skin.color)     # color: for the death explosion, markers, …
        self.rect.center = position
        self.hp = self.stat("max_hp")
        self.flash = 0.0
        self.seen = False       # set by the scene once it has been completely inside a window (arena or extra)
        self.spawned = []       # enemies created this tick – the scene moves them into its list
        self.lure = None        # a watchtower it goes for instead of the ship (set by the scene, melee enemies only)
        self.aim = pygame.Vector2(1, 0)     # the direction it faces (length 1)

    def stat(self, name):
        """The value for this run with every active buff: (value + adds) × factors."""
        add, factor = 0, 1
        for buff in self.active_buffs():
            if buff.stat == name:
                add += buff.add
                factor *= buff.factor
        return (self.base[name] + add) * factor

    def active_buffs(self):
        return self.buffs + self.roster.buffs_for(self) if self.roster.buffs else self.buffs

    @property
    def alive(self):
        return self.hp > 0

    @property
    def size(self):
        return self.rect.width

    @property
    def mass(self):
        """How hard it is to push: bigger enemies shove smaller ones out of the way."""
        return self.size ** 2

    @property
    def center(self):
        return pygame.Vector2(self.rect.center)

    def take_damage(self, amount):
        self.hp -= amount
        self.flash = HIT_FLASH

    # --- helpers for subclasses ---

    def distance_to(self, point):
        return self.center.distance_to(point)

    def direction_to(self, point):
        """Unit vector towards point (or (0, 0) if it's right here)."""
        offset = pygame.Vector2(point) - self.center
        return offset.normalize() if offset.length_squared() > 0 else pygame.Vector2()

    def move(self, direction, speed, dt):
        self.rect.move_ip(pygame.Vector2(direction) * speed * dt)

    def turn_towards(self, point, dt):
        """Turns aim towards point by at most turn_speed degrees per second."""
        wanted = self.direction_to(point)
        if not wanted.length_squared():
            return
        angle = self.aim.angle_to(wanted)
        angle = (angle + 180) % 360 - 180                   # the shorter way round: -180 … 180
        step = self.stat("turn_speed") * dt
        self.aim = self.aim.rotate(max(-step, min(step, angle)))

    def facing(self, point, cone=None):
        """True if point lies within the cone (degrees, all of it – None: the "fire_cone" stat) in front of it."""
        wanted = self.direction_to(point)
        if not wanted.length_squared():
            return True
        cone = self.stat("fire_cone") if cone is None else cone
        return abs((self.aim.angle_to(wanted) + 180) % 360 - 180) <= cone / 2

    def shoot_ahead(self, stats):
        """A projectile from the centre in the direction it faces."""
        return Projectile(self.center, self.aim, stats)

    def on_hit_ship(self, ship):
        """It just hurt the ship by touching it (the hit counted) – e.g. to knock it back. Most enemies don't."""

    def blocks(self, projectile):
        """True if it stops the player's projectile without being hurt (a shield) – most enemies don't."""
        return False

    def keep_distance(self, target, preferred, back_off, close_in, dt):
        """Walks closer when further than preferred + close_in, backs off when closer than preferred - back_off."""
        distance = self.distance_to(target)
        direction = self.direction_to(target)
        if distance > preferred + close_in:
            self.move(direction, self.stat("speed"), dt)
        elif distance < preferred - back_off:
            self.move(-direction, self.stat("speed"), dt)

    def shot_stats(self, color):
        """The values of its shots: shot_damage, shot_speed, shot_size."""
        return ShotStats(damage=self.stat("shot_damage"), speed=self.stat("shot_speed"), wall_push=0,
                         size=self.stat("shot_size"), color=color)

    def shoot(self, target, stats):
        """A projectile from the centre towards target, with the snapshot stats."""
        direction = self.direction_to(target)
        return Projectile(self.center, direction if direction.length_squared() else (1, 0), stats)

    # --- every tick ---

    def update(self, dt, ship):
        self.flash = max(0.0, self.flash - dt)
        for buff in self.buffs:
            buff.update(dt)
        self.buffs = [buff for buff in self.buffs if not buff.expired]
        return self.act(dt, ship)

    def act(self, dt, ship):
        """Behaviour. Default: run straight at the ship (or the watchtower luring it), never shoot."""
        self.move(self.direction_to(self.target(ship)), self.stat("speed"), dt)
        return []

    def target(self, ship):
        """Where it's heading: the watchtower luring it, if there is one, else the ship."""
        if self.lure is not None and self.lure.alive:
            return self.lure.rect.center
        return ship.rect.center

    # --- drawing: all in the skin ---

    def draw(self, surface, offset):
        self.skin.draw(surface, self, self.rect.move(-offset[0], -offset[1]))
