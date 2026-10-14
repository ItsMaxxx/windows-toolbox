"""
Carrier: big, slow and teal. Follows the ship at a medium distance – further away than a Shooter, closer than a
Sniper – and keeps releasing Critters from its hangar (its skin shows a dark square growing until the next comes out).
The first time, a whole group comes out at once. Only a few of its critters can be alive at once; kill the Carrier,
or it never stops.
"""

import random

import pygame

from game.enemies.enemy import Enemy
from game.skins.carrier import CarrierSkin


class Carrier(Enemy):
    key = "carrier"
    name = "Carrier"
    skin = CarrierSkin()
    stats = {                       # fallback – see data/enemies.json
        "max_hp": 6, "speed": 75, "size": 40, "contact_damage": 25,
        "preferred_distance": 480,  # between the Shooter (320) and the Sniper (650)
        "back_off": 100,
        "close_in": 60,
        "spawn_range": 900,         # releases critters when the ship is at most this far away
        "spawn_interval": 0.9,      # seconds between two critters
        "max_critters": 8,          # alive at once, per carrier
        "first_wave": 5,            # critters released at once the first time
    }

    def __init__(self, position, roster=None):
        super().__init__(position, roster)
        self.timer = self.stat("spawn_interval")
        self.critters = []
        self.first_wave = True

    @property
    def hangar_progress(self):
        """0 right after a critter came out, 1 when the next one is ready."""
        return 1 - min(1.0, self.timer / self.stat("spawn_interval"))

    def act(self, dt, ship):
        target = ship.rect.center
        self.keep_distance(target, self.stat("preferred_distance"), self.stat("back_off"), self.stat("close_in"), dt)

        self.critters = [critter for critter in self.critters if critter.alive]
        self.timer = max(0.0, self.timer - dt)      # 0: hangar full – the next critter comes out once there's room
        if (self.timer == 0 and len(self.critters) < int(self.stat("max_critters"))
                and self.distance_to(target) <= self.stat("spawn_range")):
            self.timer = self.stat("spawn_interval")
            for _ in range(int(self.stat("first_wave")) if self.first_wave else 1):
                self.release_critter()
            self.first_wave = False
        return []

    def release_critter(self):
        """A new critter right next to the carrier, on a random side (not on top of it, so they don't shove)."""
        critter = self.roster.create("critter", self.center)
        side = pygame.Vector2((self.size + critter.size) / 2 + 4, 0).rotate(random.uniform(0, 360))
        critter.rect.center = self.center + side
        self.critters.append(critter)
        self.spawned.append(critter)
