"""
The basic gun: the weapon the ship starts with in weapon slot 1. Single white shots in a straight line.
"""

from game.weapon import Weapon


class BasicGun(Weapon):
    name = "Basic gun"

    def __init__(self):
        super().__init__(damage=1, fire_rate=6, shot_speed=950, shot_size=6, wall_push=15, color=(255, 255, 255))
