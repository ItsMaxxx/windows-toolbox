"""
Artillery: olive, slow, a bit tougher. It's either moving or set up (sieged) – in between it sets up or packs up:

  MOVING     – walks towards the ship. Once it has been seen (completely inside a window at least once: the arena or
               an extra window, a watchtower's or the radar's) and the ship is between min_range (+ RANGE_MARGIN) and
               fire_range, it sets up. Seen and the ship too close, it backs away until it isn't.
  SETTING_UP – its feet come out (setup_time). From here on it's rooted: it doesn't move at all, not even when other
               enemies push.
  SIEGED     – its barrel turns towards the ship (turn_speed); it fires while the ship is within fire_cone in front of
               it.
  PACKING    – the setup played backwards (pack_time), then it moves again. It packs up when the ship gets too close
               (min_range) or out of reach (fire_range + RANGE_MARGIN) while it's setting up or sieged.

When it fires, it doesn't shoot at the ship directly: it marks a spot near where the ship is right now (up to
aim_spread off, anywhere around it) with a red circle (an ArtilleryStrike). The circle slowly fills up – when it's
full, the shell lands and everything in it gets hit. Keep moving and it can't hurt you; stand still and it will.
"""

import math
import random

import pygame

from game.artillery_strike import ArtilleryStrike
from game.enemies.enemy import Enemy
from game.skins.artillery import ArtillerySkin

MOVING, SETTING_UP, SIEGED, PACKING = "moving", "setting up", "sieged", "packing"
RECOIL_TIME = 0.6           # seconds the barrel takes to slide back out after a shot (only for the skin)
ROOTED_MASS = math.inf      # immovable: pushing enemies have to go around it
RANGE_MARGIN = 40           # pixels: it sets up a bit inside its range and packs up a bit outside – no flickering


class Artillery(Enemy):
    key = "artillery"
    name = "Artillery"
    skin = ArtillerySkin()
    stats = {                       # fallback – see data/enemies.json
        "max_hp": 3, "speed": 60, "size": 32, "contact_damage": 1,
        "fire_range": 900,          # sets up (once it has been seen) and fires when the ship is at most this far away …
        "min_range": 220,           # … and at least this far – closer, it packs up and backs away
        "setup_time": 1.0,          # seconds its feet take to come out
        "pack_time": 0.8,           # seconds to pack up again
        "reload_time": 3.5,         # seconds between two shots
        "turn_speed": 60,           # degrees per second the barrel turns towards the ship
        "fire_cone": 16,            # degrees: fires only while the ship is within this cone in front of it
        "fill_time": 1.5,           # seconds the circle takes to fill up – the warning
        "aim_spread": 60,           # the circle's centre lands up to this far from the ship
        "blast_radius": 80,
        "blast_damage": 2,
    }

    def __init__(self, position, roster=None):
        super().__init__(position, roster)
        self.state = MOVING
        self.deploy = 0.0           # 0 packed up … 1 set up (how far the feet are out – the skin shows it)
        self.timer = 0.0            # seconds until the next shot (counts while sieged)
        self.recoil = 0.0           # 1 right after a shot, back to 0 within RECOIL_TIME (the skin's barrel kick)

    @property
    def rooted(self):
        return self.state != MOVING

    @property
    def mass(self):
        return ROOTED_MASS if self.rooted else super().mass

    def act(self, dt, ship):
        target = ship.rect.center
        distance = self.distance_to(target)
        self.turn_towards(target, dt)
        self.recoil = max(0.0, self.recoil - dt / RECOIL_TIME)
        min_range, fire_range = self.stat("min_range"), self.stat("fire_range")

        if self.state == MOVING:
            if self.seen and distance < min_range + RANGE_MARGIN:
                self.move(-self.direction_to(target), self.stat("speed"), dt)      # too close: back off
            elif self.seen and distance <= fire_range:
                self.state = SETTING_UP
            else:
                self.move(self.direction_to(target), self.stat("speed"), dt)
            return []
        if self.state in (SETTING_UP, SIEGED) and (distance < min_range or distance > fire_range + RANGE_MARGIN):
            self.state = PACKING
        if self.state == SETTING_UP:
            self.deploy = min(1.0, self.deploy + dt / self.stat("setup_time"))
            if self.deploy >= 1:
                self.state = SIEGED
            return []
        if self.state == PACKING:
            self.deploy = max(0.0, self.deploy - dt / self.stat("pack_time"))
            if self.deploy <= 0:
                self.state = MOVING
            return []

        self.timer -= dt                                # SIEGED
        if self.timer > 0 or not self.facing(target):
            return []
        self.timer = self.stat("reload_time")
        self.recoil = 1.0
        spot = pygame.Vector2(target) + self.spread()
        return [ArtilleryStrike(spot, self.stat("blast_radius"), self.stat("fill_time"), self.stat("blast_damage"))]

    def spread(self):
        """A random offset up to aim_spread long, evenly over the whole disc (the square root keeps the middle from
        getting more hits than the edge)."""
        distance = self.stat("aim_spread") * math.sqrt(random.random())
        return pygame.Vector2(distance, 0).rotate(random.uniform(0, 360))
