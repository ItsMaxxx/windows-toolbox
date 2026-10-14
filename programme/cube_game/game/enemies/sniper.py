"""
Sniper: small and yellow, dies to one hit. Keeps a long distance – often from outside the window. It aims with a
visible laser that turns towards the ship at turn_speed, stops following just before it fires, then fires one very
fast shot along the laser. It only starts aiming while the ship is within fire_cone in front of it.
"""

from game.enemies.enemy import Enemy
from game.skins.sniper import SniperSkin

SHOT_COLOR = (255, 235, 90)


class Sniper(Enemy):
    key = "sniper"
    name = "Sniper"
    skin = SniperSkin()
    stats = {                       # fallback – see data/enemies.json
        "base_hp": 1, "speed": 80, "size": 22, "contact_damage": 25,
        "preferred_distance": 650,  # walks closer when further than this + close_in …
        "back_off": 150,            # … backs off when closer than this - back_off
        "close_in": 80,
        "fire_range": 900,          # starts aiming when the ship is at most this far away
        "aim_time": 1.2,            # seconds the laser is visible before the shot
        "lock_time": 0.3,           # the last part of aiming: the laser stops following – the moment to dodge
        "reload_time": 2.2,
        "turn_speed": 70,           # degrees per second the laser turns towards the ship
        "fire_cone": 30,            # degrees: starts aiming only while the ship is within this cone in front of it
        "projectile_damage": 50, "projectile_speed": 1400, "projectile_size": 6,
    }

    def __init__(self, position, roster=None):
        super().__init__(position, roster)
        self.aiming = False
        self.timer = self.stat("reload_time") / 2

    @property
    def locked(self):
        return self.aiming and self.timer <= self.stat("lock_time")

    def act(self, dt, ship):
        target = ship.rect.center
        if not self.locked:
            self.turn_towards(target, dt)

        if not self.aiming:                         # only walks while not aiming
            self.keep_distance(target, self.stat("preferred_distance"), self.stat("back_off"),
                               self.stat("close_in"), dt)

        self.timer -= dt
        if self.timer > 0:
            return []
        if not self.aiming:
            if self.distance_to(target) <= self.stat("fire_range") and self.facing(target):
                self.aiming, self.timer = True, self.stat("aim_time")
            return []
        self.aiming, self.timer = False, self.stat("reload_time")
        return [self.fire()]

    def fire(self):
        """The shot at the end of aiming: one fast bullet where it faces."""
        return self.shoot_ahead(self.shot_stats(SHOT_COLOR))
