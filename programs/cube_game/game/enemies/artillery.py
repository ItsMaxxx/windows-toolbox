"""
Artillery: olive, slow, a bit tougher. It's either moving or set up (sieged) – in between it sets up or packs up:

  MOVING     – walks towards the ship. Once it has been seen (completely inside a window at least once: the arena or
               an extra window, a watchtower's or the radar's) and the ship is between min_range (+ RANGE_MARGIN) and
               fire_range, it sets up. Seen and the ship too close, it backs away until it isn't.
  SETTING_UP – its feet come out (setup_time). From here on it's rooted: it doesn't move at all, not even when other
               enemies push.
  SIEGED     – it turns towards the ship (turn_speed); it fires while the ship is within fire_cone in front of it.
  PACKING    – the setup played backwards (pack_time), then it moves again. It packs up when the ship gets too close
               (min_range) or out of reach (fire_range + RANGE_MARGIN) while it's setting up or sieged.

It's a catapult: its arm lies back with a shell in the bucket (arm ≈ ARM_REST degrees, loaded). Firing, the arm swings
forward over the top (swing_time, faster and faster) and lets go of the shell at the top (ARM_RELEASE); then it cranks
back during the reload and takes the next shell. The skin draws the arm from arm and loaded.

The shell doesn't fly at the ship directly: it's lobbed at a spot near where the ship is at the moment it's let go (up
to aim_spread off, anywhere around it), marked with a red circle (an ArtilleryStrike). It's in the air for fill_time on
an arc – arc_height pixels high plus arc_steepness per pixel of distance, highest at arc_peak of the way – while the
circle fills; when it lands, everything in the circle gets hit. Keep moving and it can't hurt you; stand still and it
will. launch() makes the shell – the Cluster (its evolution) throws a splitter shell instead.
"""

import math
import random

import pygame

from game.artillery_strike import ArtilleryStrike, arc_for
from game.enemies.enemy import Enemy
from game.skins.artillery import ARM_LENGTH, ArtillerySkin

MOVING, SETTING_UP, SIEGED, PACKING = "moving", "setting up", "sieged", "packing"
ARM_REST = 15               # degrees: the catapult's arm lying back (0 would be flat on the ground behind it) …
ARM_RELEASE = 90            # … straight up: here it lets go of the shell …
ARM_FORWARD = 120           # … and here it stops, thrown forward
CRANK_SHARE = 0.7           # part of the reload it takes to crank the arm back (then it's loaded and waits)
PACK_ARM_SPEED = 200        # degrees per second the arm folds back while it packs up or walks
ROOTED_MASS = math.inf      # immovable: pushing enemies have to go around it
RANGE_MARGIN = 40           # pixels: it sets up a bit inside its range and packs up a bit outside – no flickering


class Artillery(Enemy):
    key = "artillery"
    name = "Artillery"
    skin = ArtillerySkin()
    stats = {                       # fallback – see data/enemies.json
        "base_hp": 3, "speed": 60, "size": 32, "contact_damage": 25,
        "fire_range": 900,          # sets up (once it has been seen) and fires when the ship is at most this far away …
        "min_range": 220,           # … and at least this far – closer, it packs up and backs away
        "setup_time": 1.0,          # seconds its feet take to come out
        "pack_time": 0.8,           # seconds to pack up again
        "reload_time": 3.5,         # seconds between two shots
        "turn_speed": 60,           # degrees per second the barrel turns towards the ship
        "fire_cone": 16,            # degrees: fires only while the ship is within this cone in front of it
        "fill_time": 1.5,           # seconds the shell flies – the circle fills up meanwhile (the warning)
        "aim_spread": 60,           # the circle's centre lands up to this far from the ship
        "blast_radius": 80,
        "blast_damage": 50,
        "swing_time": 0.3,          # seconds the arm takes to swing forward
        "arc_height": 60,           # pixels the shell flies up (at its highest) …
        "arc_steepness": 0.15,      # … plus this many per pixel it's thrown
        "arc_peak": 0.5,            # where on its way it's highest (0.5 halfway, less: up steeply, down long)
        "shell_size": 14,
    }

    def __init__(self, position, roster=None):
        super().__init__(position, roster)
        self.state = MOVING
        self.deploy = 0.0           # 0 packed up … 1 set up (how far the feet are out – the skin shows it)
        self.timer = 0.0            # seconds until the next shot (counts while sieged)
        self.arm = ARM_REST         # degrees the catapult's arm stands at (the skin draws it)
        self.loaded = False         # a shell in the bucket – it takes one once it's set up
        self.swing = None           # seconds into the swing while it swings forward, else None

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
        if self.state != SIEGED:                        # walking or packing: fold the arm back, no throw
            self.swing = None
            self.arm = max(ARM_REST, self.arm - PACK_ARM_SPEED * dt)
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
                self.loaded = self.loaded or self.arm <= ARM_REST
            return []
        if self.state == PACKING:
            self.deploy = max(0.0, self.deploy - dt / self.stat("pack_time"))
            if self.deploy <= 0:
                self.state = MOVING
            return []

        if self.swing is not None:                      # SIEGED: swinging forward – lets go at the top
            return self.swing_arm(dt, target)
        self.timer -= dt
        reload = self.stat("reload_time")
        if not self.loaded:                             # cranking back, then the next shell goes in
            back = (ARM_FORWARD - ARM_REST) * dt / max(0.05, reload * CRANK_SHARE)
            self.arm = max(ARM_REST, self.arm - back)
            self.loaded = self.arm <= ARM_REST
        if self.timer > 0 or not self.loaded or not self.facing(target):
            return []
        self.timer = reload
        self.swing = 0.0
        return []

    def swing_arm(self, dt, target):
        """One tick of the swing: the arm speeds up like a catapult's (the square of the time); at ARM_RELEASE the shell
        goes. Returns the shell in that tick."""
        self.swing += dt
        part = min(1.0, self.swing / max(0.01, self.stat("swing_time")))
        self.arm = ARM_REST + (ARM_FORWARD - ARM_REST) * part ** 2
        thrown = []
        if self.loaded and self.arm >= ARM_RELEASE:
            self.loaded = False
            thrown.append(self.launch(pygame.Vector2(target) + self.spread()))
        if part >= 1:
            self.swing = None
        return thrown

    def launch(self, spot):
        """The shell for spot, thrown from the bucket at the top of the swing."""
        return ArtilleryStrike(self.center, spot, self.stat("blast_radius"), self.stat("fill_time"),
                               self.stat("blast_damage"), self.arc(spot), size=self.stat("shell_size"))

    def arc(self, spot):
        return arc_for(self.center, spot, self.stat("arc_height"), self.stat("arc_steepness"), self.stat("arc_peak"),
                       self.size * ARM_LENGTH)

    def spread(self):
        """A random offset up to aim_spread long, evenly over the whole disc (the square root keeps the middle from
        getting more hits than the edge)."""
        distance = self.stat("aim_spread") * math.sqrt(random.random())
        return pygame.Vector2(distance, 0).rotate(random.uniform(0, 360))
