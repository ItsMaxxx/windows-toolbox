"""
Shield: the Charger's evolution (tier 2) – a steel blue cube behind a big shield. It turns very slowly (turn_speed) and only ever moves where its shield
points – so it comes at you in a wide arc, and you can get round it.

The shield blocks the player's shots from the front (blocks()): a shot that hits the shield itself, or the body from
within shield_arc in front, is gone with a spark (game/effects/spark.py) – it doesn't push a wall either. Blasts
(rockets) hurt it from every side.

Its dash – an upgraded Charger's: when the ship is within dash_range and in front of its shield (dash_cone), it winds
up (a warning line), then dashes shield first in a straight line, very heavy (dash_mass), and needs a moment to
recover. Hit by the dash, the ship is knocked back (knockback pixels) and stunned for stun_time.
"""

from game.enemies.enemy import Enemy
from game.skins.shield import ShieldSkin

APPROACH, WINDUP, DASH, RECOVER = "approach", "windup", "dash", "recover"
SHIELD_GAP = 4              # pixels between the body and the shield


class ShieldBearer(Enemy):
    key = "shield"
    name = "Shield"
    tier = 2                        # the Charger's evolution
    melee = True
    shielded = True
    skin = ShieldSkin()
    stats = {                       # fallback – see data/enemies.json
        "base_hp": 4, "speed": 55, "size": 30, "contact_damage": 50,
        "turn_speed": 40,           # degrees per second – very slow
        "shield_width": 54,         # pixels: how long the shield is (across, in front of the body)
        "shield_arc": 150,          # degrees: shots that hit the body from within this cone in front are blocked, too
        "dash_range": 300,          # winds up when the ship is this close …
        "dash_cone": 20,            # … and within this cone in front of the shield
        "windup_time": 0.7,
        "dash_speed": 650,
        "dash_time": 0.5,
        "recover_time": 1.2,        # stands still afterwards – the moment to get round it
        "dash_mass": 30,            # times its normal mass while dashing
        "knockback": 70,            # pixels the ship is knocked back when the dash hits it …
        "stun_time": 0.5,           # … and seconds it's stunned (can't move, shoot or use abilities)
    }

    def __init__(self, position, roster=None):
        super().__init__(position, roster)
        self.state = APPROACH
        self.timer = 0.0

    @property
    def winding_up(self):
        return self.state == WINDUP

    @property
    def mass(self):
        return super().mass * (self.stat("dash_mass") if self.state == DASH else 1)

    def act(self, dt, ship):
        target = self.target(ship)
        if self.state == APPROACH:
            self.turn_towards(target, dt)
            self.move(self.aim, self.stat("speed"), dt)         # only ever where the shield points
            if self.distance_to(target) <= self.stat("dash_range") and self.facing(target, self.stat("dash_cone")):
                self.state, self.timer = WINDUP, self.stat("windup_time")
        elif self.state == WINDUP:
            self.turn_towards(target, dt)                       # still turning (slowly) while it winds up
            self.timer -= dt
            if self.timer <= 0:
                self.state, self.timer = DASH, self.stat("dash_time")     # the direction is locked from here on
        elif self.state == DASH:
            self.move(self.aim, self.stat("dash_speed"), dt)
            self.timer -= dt
            if self.timer <= 0:
                self.state, self.timer = RECOVER, self.stat("recover_time")
        else:
            self.timer -= dt
            if self.timer <= 0:
                self.state = APPROACH
        return []

    def on_hit_ship(self, ship):
        if self.state == DASH:
            ship.knock(self.aim, self.stat("knockback"), self.stat("stun_time"))

    def shield_line(self):
        """The shield as a line (two points) in front of the body, across the direction it faces."""
        middle = self.center + self.aim * (self.size / 2 + SHIELD_GAP)
        across = self.aim.rotate(90) * self.stat("shield_width") / 2
        return middle - across, middle + across

    def blocks(self, projectile):
        """True if projectile hits the shield, or the body from the front (it came from within shield_arc)."""
        start, end = self.shield_line()
        if projectile.rect.clipline(start, end):
            return True
        if not projectile.rect.colliderect(self.rect):
            return False
        came_from = -projectile.direction
        return abs((self.aim.angle_to(came_from) + 180) % 360 - 180) <= self.stat("shield_arc") / 2
