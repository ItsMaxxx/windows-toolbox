"""
Base class for abilities in the ship's two ability slots. An ability has a cooldown; the player triggers it with its
key (see ABILITY_KEYS in settings.py), which calls use().

A real ability is a subclass that sets name and cooldown_time (in __init__, so shop cards can change it per ability)
and overrides what it needs:
  - activate(ship, target): what happens when it's triggered; returns new projectiles (a list, may be empty),
  - update(dt, ship): every tick (call super() so the cooldown runs down),
  - draw(surface, offset, ship): extra effects on screen (e.g. a trail).
"""


class Ability:
    name = "Ability"
    cooldown_time = 0.0         # seconds after use until it can be used again

    def __init__(self):
        self.cooldown = 0.0     # seconds left until it's ready

    @property
    def ready(self):
        return self.cooldown <= 0

    def use(self, ship, target):
        """The player pressed the key. target: the mouse in world coordinates. Returns new projectiles."""
        if not self.ready:
            return []
        self.cooldown = self.cooldown_time
        return self.activate(ship, target)

    def activate(self, ship, target):
        return []

    def update(self, dt, ship):
        self.cooldown = max(0.0, self.cooldown - dt)

    def draw(self, surface, offset, ship):
        """Drawn below the ship."""

    def stat_lines(self):
        """(name, value) rows for the inventory."""
        return [("Cooldown", f"{self.cooldown_time:g} s")]
