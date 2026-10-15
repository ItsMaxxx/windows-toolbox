"""
The numbers of the weapons: data/weapons.json (every value explained in
data/README.md). reload() reads it again into STATS – the game menu calls it every time it opens (via
difficulty.reload()). What's missing or invalid in the file keeps the value in DEFAULTS, and a warning goes to the game
menu.

Each weapon has:
  - its base values (damage, attack_speed, …) – what its skill tree upgrades add is in data/skilltree.json,
  - upgrade_factor: how strongly the shop's and the cards' weapon upgrades work on it – the cards add the same amount
    to every weapon, so a weapon with many tiny shots (the laser) needs a small factor for damage, or one card would
    make it far too strong.
"""

import copy
import json
from pathlib import Path

FILE = Path(__file__).resolve().parents[2] / "data" / "weapons.json"
UPGRADE_FACTOR = {"damage": 1, "attack_speed": 1, "wall_push": 1, "projectile_speed": 1}     # 1 = like the gun
DEFAULTS = {
    "gun": {
        "damage": 1.5, "attack_speed": 2, "projectile_speed": 880, "projectile_size": 7, "wall_push": 18,
        "energy_use": 8,
        "upgrade_factor": dict(UPGRADE_FACTOR),
    },
    "machine_gun": {
        "damage": 0.5, "attack_speed": 8, "projectile_speed": 950, "projectile_size": 5, "wall_push": 7,
        "energy_use": 3, "spread": 30,
        "upgrade_factor": dict(UPGRADE_FACTOR, damage=0.3, attack_speed=2, wall_push=0.5),
    },
    "cannon": {
        "damage": 4.5, "attack_speed": 0.8, "projectile_speed": 650, "projectile_size": 14, "wall_push": 35,
        "energy_use": 22, "piercing": 1, "pierced_push": 0.5,
        "upgrade_factor": dict(UPGRADE_FACTOR, damage=2, attack_speed=0.2, wall_push=2),
    },
    "laser": {
        "damage": 0.04, "attack_speed": 30, "projectile_speed": 1500, "projectile_size": 4, "wall_push": 2,
        "energy_use": 1,
        "upgrade_factor": dict(UPGRADE_FACTOR, damage=0.02, attack_speed=4, wall_push=0.15),
    },
}
MUST_BE_POSITIVE = {"attack_speed", "projectile_speed", "projectile_size"}
STATS = copy.deepcopy(DEFAULTS)


def reload(warnings):
    """Reads data/weapons.json again into STATS. Problems are added to warnings (a list)."""
    try:
        data = json.loads(FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("should be { … }")
    except (OSError, ValueError) as error:
        warnings.append(f"weapons.json: can't be read ({error}) – using built-in values")
        data = {}
    STATS.clear()
    STATS.update(copy.deepcopy(DEFAULTS))
    merge(STATS, data, DEFAULTS, "", warnings)


def merge(target, data, defaults, where, warnings):
    """Copies the valid values of data (a dict from the file) into target – defaults says which keys exist and what
    they hold. No number may be negative."""
    for key, value in data.items():
        place = f"{where}.{key}" if where else key
        if key not in defaults:
            warnings.append(f"weapons.json {where or 'top level'}: unknown key \"{key}\" – ignored")
        elif isinstance(defaults[key], dict):
            if isinstance(value, dict):
                merge(target[key], value, defaults[key], place, warnings)
            else:
                warnings.append(f"weapons.json {place}: should be {{ … }} – using the defaults")
        elif valid(key, value):
            target[key] = value
        else:
            warnings.append(f"weapons.json {place}: {json.dumps(value)} is not valid – using {defaults[key]}")


def valid(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return value > 0 if name in MUST_BE_POSITIVE else value >= 0
