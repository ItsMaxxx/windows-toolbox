"""
Sniper: small and yellow, dies to one hit. Keeps a long distance – often from outside the window. It aims with a
visible laser, stops following the ship just before it fires, then fires one very fast shot.
"""

import pygame

from game.enemies.enemy import Enemy
from game.shot_stats import ShotStats

SHOT = ShotStats(damage=2, speed=1400, wall_push=0, size=6, color=(255, 235, 90))
PREFERRED_DISTANCE = 650    # walks closer when further away, backs off when much closer
DISTANCE_TOLERANCE = (150, 80)      # (closer than preferred - 150: back off, further than preferred + 80: walk closer)
FIRE_RANGE = 900            # starts aiming when the ship is at most this far away
AIM_TIME = 1.2              # seconds the laser is visible before the shot
LOCK_TIME = 0.3             # the last part of aiming: the laser stops following – the moment to dodge
RELOAD_TIME = 2.2
LASER_LENGTH = 3000
LASER_COLOR = (110, 95, 30)
LASER_LOCKED = (255, 235, 90)
BARREL_COLOR = (255, 245, 170)


class Sniper(Enemy):
    name = "Sniper"
    max_hp = 1
    speed = 80
    size = 22
    color = (235, 205, 50)
    contact_damage = 1

    def __init__(self, position):
        super().__init__(position)
        self.aiming = False
        self.timer = RELOAD_TIME / 2
        self.aim = pygame.Vector2(1, 0)

    @property
    def locked(self):
        return self.aiming and self.timer <= LOCK_TIME

    def act(self, dt, ship):
        target = ship.rect.center
        distance = self.distance_to(target)
        direction = self.direction_to(target)
        if not self.locked and direction.length_squared():
            self.aim = direction

        if not self.aiming:                         # only walks while not aiming
            closer, further = DISTANCE_TOLERANCE
            if distance > PREFERRED_DISTANCE + further:
                self.move(direction, self.speed, dt)
            elif distance < PREFERRED_DISTANCE - closer:
                self.move(-direction, self.speed, dt)

        self.timer -= dt
        if self.timer > 0:
            return []
        if not self.aiming:
            if distance <= FIRE_RANGE:
                self.aiming, self.timer = True, AIM_TIME
            return []
        self.aiming, self.timer = False, RELOAD_TIME
        return [self.shoot(self.center + self.aim, SHOT)]

    def draw_details(self, surface, rect, offset):
        start = pygame.Vector2(rect.center)
        if self.aiming:
            color, width = (LASER_LOCKED, 2) if self.locked else (LASER_COLOR, 1)
            pygame.draw.line(surface, color, start, start + self.aim * LASER_LENGTH, width)
        pygame.draw.line(surface, BARREL_COLOR, start, start + self.aim * self.size * 1.1, 4)
