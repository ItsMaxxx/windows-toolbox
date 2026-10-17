"""
Base class for abilities in the ship's two ability slots. An ability has a cooldown; the player triggers it with its
key (see ABILITY_KEYS in settings.py), which calls use().

Charges: an ability can be stored up to max_charges times (1 for most). Every use takes one; while it has fewer than
max_charges, the cooldown runs and gives one back each time it's over. With one charge that's a plain cooldown.

A real ability is a subclass that sets name and cooldown_time (in __init__, so shop cards can change it per ability)
and overrides what it needs:
  - activate(ship, target): what happens when it's triggered; returns new projectiles (a list, may be empty),
  - update(dt, ship): every tick (call super() so the cooldown runs down),
  - draw(surface, offset, ship): extra effects on screen (e.g. a trail).
"""


class Ability:
    name = "Ability"
    cooldown_time = 0.0         # seconds after use until it can be used again (until one charge is back)
    max_charges = 1
    protects = False            # True while it keeps the ship from being hit (the dash)

    def __init__(self):
        self.cooldown = 0.0     # seconds left until the next charge is back (0 while all are there)
        self.charges = self.max_charges

    @property
    def ready(self):
        return self.charges > 0

    def use(self, ship, target):
        """The player pressed the key. target: the mouse in world coordinates. Returns new projectiles."""
        if not self.ready:
            return []
        if self.charges >= self.max_charges:    # all were there: the cooldown starts now
            self.cooldown = self.cooldown_time
        self.charges -= 1
        return self.activate(ship, target)

    def activate(self, ship, target):
        return []

    def update(self, dt, ship):
        if self.charges >= self.max_charges:
            self.charges, self.cooldown = self.max_charges, 0.0
            return
        self.cooldown -= dt
        if self.cooldown <= 0:                  # one back – and the next one starts filling if any is missing
            self.charges += 1
            self.cooldown = self.cooldown_time + self.cooldown if self.charges < self.max_charges else 0.0

    def draw(self, surface, offset, ship):
        """Drawn below the ship."""

    def stat_lines(self):
        """(name, value) rows for the inventory."""
        return [("Cooldown", f"{self.cooldown_time:g} s")]
