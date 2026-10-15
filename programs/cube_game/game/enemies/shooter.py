"""
Shooter: purple. Runs towards the ship until it's within shooting distance, then stays there and fires slow shots.
Its barrel turns towards the ship at turn_speed; it only fires while the ship is within fire_cone in front of it, and
the shot goes where the barrel points.
"""

import random

from game.enemies.enemy import Enemy
from game.skins.shooter import ShooterSkin


class Shooter(Enemy):
    key = "shooter"
    name = "Shooter"
    skin = ShooterSkin()
    shot_color = (200, 90, 255)
    stats = {                       # fallback – see data/enemies.json
        "base_hp": 2, "speed": 95, "size": 28, "contact_damage": 25,
        "shooting_distance": 320,   # stops walking when the ship is this close
        "fire_range": 520,          # fires when the ship is at most this far away
        "fire_interval": 1.5,       # seconds between shots
        "turn_speed": 140,          # degrees per second its barrel turns towards the ship
        "fire_cone": 20,            # degrees: fires only while the ship is within this cone in front of it
        "projectile_damage": 25, "projectile_speed": 380, "projectile_size": 10,
    }

    def __init__(self, position, roster=None):
        super().__init__(position, roster)
        self.cooldown = random.uniform(0.5, self.stat("fire_interval"))    # so a group doesn't fire in sync

    def act(self, dt, ship):
        target = ship.rect.center
        distance = self.distance_to(target)
        self.turn_towards(target, dt)
        if distance > self.stat("shooting_distance"):
            self.move(self.direction_to(target), self.stat("speed"), dt)
        self.cooldown = max(0.0, self.cooldown - dt)
        if self.cooldown <= 0 and distance <= self.stat("fire_range") and self.facing(target):
            self.cooldown = self.stat("fire_interval")
            return [self.shoot_ahead(self.shot_stats(self.shot_color))]
        return []
