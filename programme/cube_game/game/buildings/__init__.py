"""
Buildings: things the player puts into the world during a run. For now there's one, the watchtower (watchtower.py).

Their values come from data/buildings.json (explained in data/README.md) – reload() reads it again; the game menu
calls it every time it opens (via difficulty.reload()). What's missing or invalid there keeps the value in the code
(the stats dict of the building's class), and a warning goes to the game menu.
"""

import json
from pathlib import Path

from game.buildings.watchtower import Watchtower

BUILDING_TYPES = {"watchtower": Watchtower}
FILE = Path(__file__).resolve().parents[2] / "data" / "buildings.json"
MUST_BE_POSITIVE = {"max_hp", "size", "vision", "throw_time"}      # 0 would break things
STATS = {}                          # type key -> {stat: value}: data/buildings.json over the class fallbacks


def valid_value(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        return False
    return value > 0 or name not in MUST_BE_POSITIVE


def reload(warnings):
    """Reads data/buildings.json again into STATS. Problems are added to warnings (a list)."""
    try:
        data = json.loads(FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("should be { … }")
    except (OSError, ValueError) as error:
        warnings.append(f"buildings.json: can't be read ({error}) – using built-in values")
        data = {}
    STATS.clear()
    for key, building_type in BUILDING_TYPES.items():
        values = dict(building_type.stats)
        entry = data.get(key, {})
        if not isinstance(entry, dict):
            warnings.append(f"buildings.json {key}: should be {{ … }} – using built-in values")
            entry = {}
        for name, value in entry.items():
            if name not in values:
                warnings.append(f"buildings.json {key}: unknown value \"{name}\" – ignored")
            elif valid_value(name, value):
                values[name] = value
            else:
                warnings.append(f"buildings.json {key}.{name}: {json.dumps(value)} is not valid – using {values[name]}")
        STATS[key] = values
    for key in data.keys() - BUILDING_TYPES.keys():
        warnings.append(f"buildings.json: unknown building \"{key}\" – ignored")


reload([])                          # the game menu reloads (and shows the warnings); this is just the start value
