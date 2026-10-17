"""
A buff (or debuff): a temporary change to one of an enemy's stats during a run – flat (add) and/or as a factor.

    Buff("speed", factor=1.5, duration=5)       50 % faster for 5 seconds
    Buff("contact_damage", add=25)              +25 px contact damage until it's removed
    Buff("speed", factor=0.5, duration=2)       a slow (debuff)

All buffs on a stat are combined like this: (value + all adds) × all factors – so a +1 always counts the same, no
matter in which order the buffs came.

A buff with a source (a Commander's) is renewed when it's given again, not stacked – see Enemy.renew_buffs(). Its
color is the outline the enemy gets, so the player sees where the buff came from.

Where a buff goes: enemy.buffs (just that one enemy) or roster.buffs (all enemies of the run, also ones spawned later;
target: only one type, e.g. "charger"). base_hp and size are read when an enemy spawns – buffs on them only affect
enemies spawned while the buff is active.
"""

from dataclasses import dataclass


@dataclass
class Buff:
    stat: str                       # e.g. "speed", "base_hp", "projectile_damage" – a key in the enemy's stats
    add: float = 0                  # flat: added to the value
    factor: float = 1               # multiplied with (value + adds)
    duration: float | None = None   # seconds – None: until it's removed
    target: str | None = None       # only for roster.buffs: an enemy type ("charger") – None: every type
    source: str | None = None       # who gave it ("commander") – such a buff is renewed instead of given twice
    color: tuple | None = None      # the outline it gives the enemy – None: the usual one (buff_glow.COLOR)

    @property
    def expired(self):
        return self.duration is not None and self.duration <= 0

    def update(self, dt):
        if self.duration is not None:
            self.duration -= dt
