"""
The enemy roster of a run: every enemy type's values for this run, the buffs on all enemies, and create() to make an
enemy with them (the spawner and the Carrier use it).

Where an enemy's values come from – each layer overrides the one before:
  1. the stats dict in the enemy's class – only a fallback, if data/enemies.json lacks a value or is broken
  2. data/enemies.json – the real standard values (explained in data/README.md)
  3. "enemy_stats" in the difficulty file – the difficulty's own values, like a map in the StarCraft 2 editor:
     a number replaces the value, "+1" / "-1" adds, "x1.5" multiplies; "all" applies to every type that has the stat
Buffs (buff.py) come on top during the run.

Evolutions: some tier 1 types have a stronger tier 2 version (EVOLUTIONS). A level's "evolutions" say how likely one
of them spawns in its place – the spawner asks for that (see spawner.py); create() always makes exactly the type asked.
"""

import json
from pathlib import Path

from game.enemies.artillery import Artillery
from game.enemies.basic import BasicEnemy
from game.enemies.cannoneer import Cannoneer
from game.enemies.carrier import Carrier
from game.enemies.charger import Charger
from game.enemies.critter import Critter
from game.enemies.fat import FatGuy
from game.enemies.laser import Laser
from game.enemies.shield import ShieldBearer
from game.enemies.shooter import Shooter
from game.enemies.sniper import Sniper

# the names the data files use for the enemy types
ENEMY_TYPES = {"basic": BasicEnemy, "charger": Charger, "shooter": Shooter, "sniper": Sniper, "carrier": Carrier,
               "critter": Critter, "artillery": Artillery, "fat": FatGuy, "cannoneer": Cannoneer, "shield": ShieldBearer,
               "laser": Laser}
# tier 1 type -> its evolution (tier 2)
EVOLUTIONS = {"basic": "fat", "shooter": "cannoneer", "charger": "shield", "sniper": "laser"}
FILE = Path(__file__).resolve().parents[2] / "data" / "enemies.json"
# 0 would break things (division by 0, invisible enemies, …)
MUST_BE_POSITIVE = {"base_hp", "size", "fire_interval", "reload_time", "aim_time", "spawn_interval", "blast_radius",
                    "setup_time", "pack_time", "beam_time"}
BASE_STATS = {}                     # type key -> {stat: value}: data/enemies.json over the class fallbacks


def stat_names(key):
    return ENEMY_TYPES[key].stats.keys()


def valid_value(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        return False
    return value > 0 or name not in MUST_BE_POSITIVE


def reload(warnings):
    """Reads data/enemies.json again into BASE_STATS. Problems are added to warnings (a list)."""
    try:
        data = json.loads(FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("should be { … }")
    except (OSError, ValueError) as error:
        warnings.append(f"enemies.json: can't be read ({error}) – using built-in values")
        data = {}
    BASE_STATS.clear()
    for key, enemy_type in ENEMY_TYPES.items():
        values = dict(enemy_type.stats)
        entry = data.get(key, {})
        if not isinstance(entry, dict):
            warnings.append(f"enemies.json {key}: should be {{ … }} – using built-in values")
            entry = {}
        for name, value in entry.items():
            if name not in values:
                warnings.append(f"enemies.json {key}: unknown stat \"{name}\" – ignored")
            elif valid_value(name, value):
                values[name] = value
            else:
                warnings.append(f"enemies.json {key}.{name}: {json.dumps(value)} is not valid – using {values[name]}")
        BASE_STATS[key] = values
    for key in data.keys() - ENEMY_TYPES.keys():
        warnings.append(f"enemies.json: unknown enemy type \"{key}\" – ignored")


def apply(value, operation, number):
    if operation == "set":
        return number
    if operation == "add":
        return value + number
    return value * number                   # "multiply"


class EnemyRoster:
    def __init__(self, difficulty=None, warnings=None):
        """difficulty: whose enemy_stats apply (None: just the standard values). warnings: a list to report
        overrides that end up invalid (e.g. "-5" on 2 HP) – such a value keeps its standard."""
        self.stats = {key: dict(values) for key, values in BASE_STATS.items()}
        self.buffs = []                     # on all enemies of the run (Buff.target: one type, or None for all)
        for target, name, operation, number in (difficulty.enemy_stats if difficulty else ()):
            for key in ENEMY_TYPES if target == "all" else (target,):
                if name not in self.stats[key]:
                    continue                # "all": only the types that have this stat
                value = apply(self.stats[key][name], operation, number)
                if valid_value(name, value):
                    self.stats[key][name] = value
                elif warnings is not None:
                    warnings.append(f"{difficulty.key}.json enemy_stats: {key}.{name} would be {value:g} – "
                                    f"keeping {self.stats[key][name]:g}")

    def create(self, key, position):
        return ENEMY_TYPES[key](position, self)

    def buffs_for(self, enemy):
        return [buff for buff in self.buffs if buff.target in (None, enemy.key)]

    def update(self, dt):
        for buff in self.buffs:
            buff.update(dt)
        self.buffs = [buff for buff in self.buffs if not buff.expired]
