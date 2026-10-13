"""
Shooter: purple. Runs towards the ship until it's within shooting distance, then stays there and fires slow shots
at it.
"""

import random

import pygame

from game.enemies.enemy import Enemy
from game.shot_stats import ShotStats

SHOT = ShotStats(damage=1, speed=380, wall_push=0, size=10, color=(200, 90, 255))
SHOOTING_DISTANCE = 320     # stops walking when the ship is this close
FIRE_RANGE = 520            # fires when the ship is at most this far away
FIRE_INTERVAL = 1.5         # seconds between shots
BARREL_COLOR = (220, 160, 255)


class Shooter(Enemy):
    name = "Shooter"
    max_hp = 2
    speed = 95
    size = 28
    color = (160, 60, 230)
    contact_damage = 1

    def __init__(self, position):
        super().__init__(position)
        self.cooldown = random.uniform(0.5, FIRE_INTERVAL)     # so a group doesn't fire in sync
        self.aim = pygame.Vector2(1, 0)

    def act(self, dt, ship):
        target = ship.rect.center
        distance = self.distance_to(target)
        direction = self.direction_to(target)
        if direction.length_squared():
            self.aim = direction
        if distance > SHOOTING_DISTANCE:
            self.move(direction, self.speed, dt)
        self.cooldown -= dt
        if self.cooldown <= 0 and distance <= FIRE_RANGE:
            self.cooldown = FIRE_INTERVAL
            return [self.shoot(target, SHOT)]
        return []

    def draw_details(self, surface, rect, offset):
        start = pygame.Vector2(rect.center)
        pygame.draw.line(surface, BARREL_COLOR, start, start + self.aim * self.size * 1.15, 6)
