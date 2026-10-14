"""
Charger: big and orange. Walks towards the ship; once it's close, it winds up (a warning line shows where it's
aiming), then charges in a straight line at high speed and needs a moment to recover. Hits hard on contact. While
charging it's very heavy and rams other enemies out of its way.
"""

import pygame

from game.enemies.enemy import Enemy
from game.skins.charger import ChargerSkin

APPROACH, WINDUP, CHARGE, RECOVER = "approach", "windup", "charge", "recover"


class Charger(Enemy):
    key = "charger"
    name = "Charger"
    melee = True
    skin = ChargerSkin()
    stats = {                       # fallback – see data/enemies.json
        "max_hp": 3, "speed": 85, "size": 34, "contact_damage": 2,
        "charge_range": 280,        # starts winding up when the ship is this close
        "windup_time": 0.55,        # seconds of warning before it charges – it keeps turning towards the ship meanwhile
        "charge_speed": 700,
        "charge_time": 0.5,
        "recover_time": 0.8,        # stands still afterwards – the moment to shoot it
        "charge_mass": 20,          # times its normal mass while charging
    }

    def __init__(self, position, roster=None):
        super().__init__(position, roster)
        self.state = APPROACH
        self.timer = 0.0
        self.charge_direction = pygame.Vector2(1, 0)

    @property
    def winding_up(self):
        return self.state == WINDUP

    @property
    def mass(self):
        return super().mass * (self.stat("charge_mass") if self.state == CHARGE else 1)

    def act(self, dt, ship):
        target = self.target(ship)
        if self.state == APPROACH:
            self.move(self.direction_to(target), self.stat("speed"), dt)
            if self.distance_to(target) <= self.stat("charge_range"):
                self.state, self.timer = WINDUP, self.stat("windup_time")
        elif self.state == WINDUP:
            direction = self.direction_to(target)
            if direction.length_squared():
                self.charge_direction = direction
            self.timer -= dt
            if self.timer <= 0:
                self.state, self.timer = CHARGE, self.stat("charge_time")     # direction is locked from here on
        elif self.state == CHARGE:
            self.move(self.charge_direction, self.stat("charge_speed"), dt)
            self.timer -= dt
            if self.timer <= 0:
                self.state, self.timer = RECOVER, self.stat("recover_time")
        else:
            self.timer -= dt
            if self.timer <= 0:
                self.state = APPROACH
        return []
