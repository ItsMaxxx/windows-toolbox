"""
Laser: the Sniper's evolution (tier 2). Aims like a Sniper – a line that follows the ship, then stops following just
before it fires – but its line is thicker, and instead of a bullet it fires a beam along it that lasts beam_time
(half a second): touching the beam while it's on hurts. While the beam is on, the Laser neither moves nor turns.
Killing it switches its beam off.
"""

from game.enemies.sniper import Sniper
from game.laser_beam import LaserBeam
from game.skins.laser import LaserSkin


class Laser(Sniper):
    key = "laser"
    name = "Laser"
    tier = 2
    skin = LaserSkin()
    stats = {                       # fallback – see data/enemies.json
        "base_hp": 2, "speed": 70, "size": 26, "contact_damage": 25,
        "preferred_distance": 650, "back_off": 150, "close_in": 80,
        "fire_range": 900, "aim_time": 1.5, "lock_time": 0.4, "reload_time": 3.0, "turn_speed": 60, "fire_cone": 30,
        "projectile_damage": 50,          # pixels, when the ship touches the beam (once per beam)
        "beam_time": 0.5,           # seconds the beam is on
        "beam_width": 16,           # pixels
    }

    def __init__(self, position, roster=None):
        super().__init__(position, roster)
        self.beam = None            # the beam while it's on

    @property
    def firing(self):
        return self.beam is not None and not self.beam.done

    def act(self, dt, ship):
        if self.firing:
            return []               # stands still, doesn't turn – and reloading starts once the beam is off
        self.beam = None
        return super().act(dt, ship)

    def fire(self):
        self.beam = LaserBeam(self, self.stat("beam_width"), self.stat("beam_time"), self.stat("projectile_damage"),
                              self.skin.beam_color)
        return self.beam
