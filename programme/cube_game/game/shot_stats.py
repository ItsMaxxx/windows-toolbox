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
