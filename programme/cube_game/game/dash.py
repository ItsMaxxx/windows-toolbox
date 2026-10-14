"""
Dash (Shift): a quick burst in the direction you're moving – or towards the mouse if you're standing still.
The arena still keeps the ship inside, so you can't dash through a wall. Leaves a short trail of afterimages.
Its values come from data/abilities.json ("dash"); distance and cooldown are on the ability, so cards can change them.
"""

import pygame

from game import ability_data
from game.ability import Ability
from game.ship_shape import draw_ship

TRAIL_TIME = 0.25           # seconds an afterimage stays visible


class Dash(Ability):
    key = "dash"                    # its section in data/abilities.json
    name = "Dash"

    def __init__(self):
        super().__init__()
        stats = ability_data.STATS[self.key]
        self.cooldown_time = stats["cooldown"]
        self.distance = stats["distance"]   # pixels
        self.duration = stats["duration"]   # seconds the dash takes
        self.time_left = 0.0                # > 0 while dashing
        self.direction = pygame.Vector2()
        self.trail = []                     # afterimages: [position, aim, age]

    def activate(self, ship, target):
        moving = ship.move_direction()          # read now, so Shift together with a direction key goes that way
        self.direction = moving if moving.length_squared() else pygame.Vector2(ship.aim)
        self.time_left = self.duration
        return []

    def update(self, dt, ship):
        super().update(dt, ship)
        if self.time_left > 0:
            step = min(dt, self.time_left)
            ship.rect.move_ip(self.direction * (self.distance / self.duration) * step)
            self.time_left -= step
            self.trail.append([pygame.Vector2(ship.rect.center), pygame.Vector2(ship.aim), 0.0])
        for afterimage in self.trail:
            afterimage[2] += dt
        self.trail = [afterimage for afterimage in self.trail if afterimage[2] < TRAIL_TIME]

    def draw(self, surface, offset, ship):
        for position, aim, age in self.trail:
            fade = 0.5 * (1 - age / TRAIL_TIME)             # the background is black, so darker = more faded
            color = [round(channel * fade) for channel in ship.color]
            draw_ship(surface, position - offset, aim, ship.rect.width, color)

    def stat_lines(self):
        return [("Distance", f"{self.distance:g} px")] + super().stat_lines()
