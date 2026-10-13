"""
Charger: big and orange. Walks towards the ship; once it's close, it winds up (a warning line shows where it's
aiming), then charges in a straight line at high speed and needs a moment to recover. Hits hard on contact.
"""

import pygame

from game.enemies.enemy import Enemy

APPROACH, WINDUP, CHARGE, RECOVER = "approach", "windup", "charge", "recover"
CHARGE_RANGE = 280          # starts winding up when the ship is this close
WINDUP_TIME = 0.55          # seconds of warning before it charges – it keeps turning towards the ship meanwhile
CHARGE_SPEED = 700
CHARGE_TIME = 0.5
RECOVER_TIME = 0.8          # stands still afterwards – the moment to shoot it
WARNING_LENGTH = 160
WARNING_COLOR = (130, 70, 15)


class Charger(Enemy):
    name = "Charger"
    max_hp = 3
    speed = 85
    size = 34
    color = (255, 140, 30)
    contact_damage = 2

    def __init__(self, position):
        super().__init__(position)
        self.state = APPROACH
        self.timer = 0.0
        self.charge_direction = pygame.Vector2(1, 0)

    def act(self, dt, ship):
        target = ship.rect.center
        if self.state == APPROACH:
            self.move(self.direction_to(target), self.speed, dt)
            if self.distance_to(target) <= CHARGE_RANGE:
                self.state, self.timer = WINDUP, WINDUP_TIME
        elif self.state == WINDUP:
            direction = self.direction_to(target)
            if direction.length_squared():
                self.charge_direction = direction
            self.timer -= dt
            if self.timer <= 0:
                self.state, self.timer = CHARGE, CHARGE_TIME     # direction is locked from here on
        elif self.state == CHARGE:
            self.move(self.charge_direction, CHARGE_SPEED, dt)
            self.timer -= dt
            if self.timer <= 0:
                self.state, self.timer = RECOVER, RECOVER_TIME
        else:
            self.timer -= dt
            if self.timer <= 0:
                self.state = APPROACH
        return []

    def draw_details(self, surface, rect, offset):
        if self.state == WINDUP:
            start = pygame.Vector2(rect.center)
            pygame.draw.line(surface, WARNING_COLOR, start, start + self.charge_direction * WARNING_LENGTH, 4)
