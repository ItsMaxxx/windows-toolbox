"""
Dash (Shift): a quick burst in the direction you're moving – or towards the mouse if you're standing still.
The arena still keeps the ship inside, so you can't dash through a wall. Leaves a short trail of afterimages.
Its values come from data/abilities.json ("dash"); distance and cooldown are on the ability, so cards can change them.
With more than one charge (skill tree "Charges") it can dash again right away – once the dash before is over.
The skill tree's "Mines" (mines: "mine" from data/abilities.json, None without it): every dash leaves a mine where it
started (game/mine.py). "Slow field" (slow_field: its values with the upgrades, None without it): the mine's blast
slows the enemies in it for a while.
"""

import pygame

from game import ability_data
from game.ability import Ability
from game.mine import Mine
from game.ship_shape import draw_ship

TRAIL_TIME = 0.25           # seconds an afterimage stays visible


class Dash(Ability):
    key = "dash"                    # its section in data/abilities.json
    name = "Dash"
    ATTRIBUTES = {"distance": "distance", "charges": "max_charges"}      # what the skill tree upgrades

    def __init__(self):
        super().__init__()
        stats = ability_data.STATS[self.key]
        self.cooldown_time = stats["cooldown"]
        self.max_charges = round(stats["charges"])
        self.charges = self.max_charges
        self.distance = stats["distance"]   # pixels
        self.duration = stats["duration"]   # seconds the dash takes
        self.time_left = 0.0                # > 0 while dashing
        self.direction = pygame.Vector2()
        self.trail = []                     # afterimages: [position, aim, age]
        self.mines = None                   # {"damage", "blast_radius", "wall_push", "size"} once "Mines" is bought
        self.slow_field = None              # {"slow", "size", "duration"} once "Slow field" is bought

    @property
    def ready(self):
        return super().ready and self.time_left <= 0      # not again in the middle of a dash

    def upgrade(self, name, amount):
        """Adds amount to the value name ("distance" or "charges") – the skill tree's upgrades."""
        attribute = self.ATTRIBUTES[name]
        setattr(self, attribute, max(0, round(getattr(self, attribute) + amount, 6)))
        self.max_charges = max(1, round(self.max_charges))
        self.charges = self.max_charges

    def activate(self, ship, target):
        moving = ship.move_direction()          # read now, so Shift together with a direction key goes that way
        self.direction = moving if moving.length_squared() else pygame.Vector2(ship.aim)
        self.time_left = self.duration
        return [Mine(ship.rect.center, self.mines, self.slow_field)] if self.mines else []

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
        return ([("Distance", f"{self.distance:g} px"), ("Charges", str(self.max_charges))] + super().stat_lines()
                + ([("Mines", f"{self.mines['damage']:g} damage")] if self.mines else [])
                + ([("Slow field", f"{self.slow_field['slow']:g} % · {self.slow_field['size']:g} px · "
                                   f"{self.slow_field['duration']:g} s")] if self.mines and self.slow_field else []))
