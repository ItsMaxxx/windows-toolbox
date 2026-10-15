"""
The weapons for the ship's two weapon slots. WEAPON_TYPES has every weapon type by its key (the key is also the name
of its section in data/weapons.json, of its unlock node in the skill tree and in the saved loadout).

The gun is always there; the others are unlocked in the skill tree (unlocked()).
A new weapon goes into its own file here and into WEAPON_TYPES.
"""

from game.weapons.cannon import Cannon
from game.weapons.gun import Gun
from game.weapons.laser import Laser
from game.weapons.machine_gun import MachineGun

WEAPON_TYPES = {weapon.key: weapon for weapon in (Gun, MachineGun, Cannon, Laser)}
STARTER = Gun.key


def unlocked(profile, key):
    """True if the player may put this weapon into a slot: the gun always, the others once their node is bought."""
    return key == STARTER or profile.owns(key)
