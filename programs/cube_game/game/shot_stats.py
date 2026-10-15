"""
Snapshot of a weapon's (or ability's) shot values at the moment a shot is fired.

Frozen (can't be changed afterwards): upgrades only affect shots fired *after* them, and nothing can change a shot's
values by accident. Effects on a shot in flight (slowing, redirecting, …) don't touch the snapshot – they change the
projectile's own state instead, see Projectile.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ShotStats:
    damage: float
    speed: float                # pixels per second at the start
    wall_push: float            # pixels a hit edge moves out
    size: float                 # diameter in pixels
    color: tuple                # (r, g, b)
    acceleration: float = 0     # pixels per second², the shot gets faster the longer it flies
    blast_radius: float = 0     # > 0: explodes at its end – damage and wall push for everything within this radius
    pierce: int = 0             # flies on through this many enemies (hurting each), stops at the next one
    pierce_push: float = 1      # wall push × this for every enemy it went through
    burn_time: float = 0        # > 0 (with a blast): leaves burning ground behind for this many seconds …
    burn_damage: float = 0      # … that does this much damage per second to enemies in it …
    burn_radius: float = 0      # … within this radius
    slow: float = 0             # > 0 (with a blast): leaves a slowing field behind – enemies in it this share slower …
    slow_radius: float = 0      # … within this radius …
    slow_time: float = 0        # … for this many seconds
