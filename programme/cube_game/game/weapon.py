"""
Base class for weapons. A weapon sits in one of the ship's weapon slots and decides everything about its shots:
damage, attack speed, projectile speed and size, wall push, colour. Each weapon has its own cooldown.

New weapon = subclass with its own values (see basic_gun.py); override fire() for different patterns
(e.g. a shotgun that returns several projectiles at once).
"""

from game.projectile import Projectile
from game.shot_stats import ShotStats

READY = 1e-9        # cooldowns at or below this count as 0 – 1/6 s minus 10 × 1/60 s leaves a tiny float remainder


class Weapon:
    name = "Weapon"

    def __init__(self, damage, fire_rate, shot_speed, shot_size, wall_push, color):
        self.damage = damage
        self.fire_rate = fire_rate          # shots per second
        self.shot_speed = shot_speed        # pixels per second
        self.shot_size = shot_size          # diameter in pixels
        self.wall_push = wall_push          # pixels the hit edge moves out
        self.color = color
        self.cooldown = 0.0                 # seconds until the next shot is possible

    def update(self, dt):
        # may go up to one tick below 0: the leftover time carries over to the next shot, so rates that don't fit
        # the 60 ticks evenly (e.g. 7/s) are still right on average
        self.cooldown = max(self.cooldown - dt, -dt)

    def shot_stats(self):
        """Snapshot of the current values – every shot gets its own copy when it's fired."""
        return ShotStats(damage=self.damage, speed=self.shot_speed, wall_push=self.wall_push, size=self.shot_size,
                         color=self.color)

    def fire(self, origin, direction):
        """New projectiles (a list, so weapons can fire several at once) – empty while cooling down."""
        if self.cooldown > READY:
            return []
        self.cooldown += 1 / self.fire_rate
        return [Projectile(origin, direction, self.shot_stats())]

    def stat_lines(self):
        """(name, value) rows for the inventory."""
        return [
            ("Damage", f"{self.damage:g}"),
            ("Attack speed", f"{self.fire_rate:g}/s"),
            ("Wall push", f"{self.wall_push:g} px"),
            ("Projectile speed", f"{self.shot_speed:g} px/s"),
        ]
