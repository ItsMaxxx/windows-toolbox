"""
The abilities' base values (dash, rocket): data/abilities.json (every value explained in data/README.md). reload()
reads it again into STATS – the game menu calls it every time it opens (via difficulty.reload()). What's missing or
invalid in the file keeps the value in DEFAULTS, and a warning goes to the game menu.

What the skill tree adds is in data/skilltree.json, what shop upgrades add in data/shop.json, what cards add in
data/upgrades.json.
"""

import copy
import json
from pathlib import Path

FILE = Path(__file__).resolve().parents[1] / "data" / "abilities.json"
DEFAULTS = {
    "dash": {
        "cooldown": 1.2,            # seconds until it's ready again …
        "min_cooldown": 0.3,        # … never shorter than this, whatever upgrades and cards take off
        "distance": 220,            # pixels
        "duration": 0.12,           # seconds the dash takes
        "charges": 1,               # dashes stored at once (the skill tree's Charges add more)
    },
    "rocket": {
        "cooldown": 7,
        "min_cooldown": 1.5,
        "damage": 3,
        "blast_radius": 110,
        "wall_push": 120,
        "speed": 120,               # pixels per second at launch …
        "acceleration": 2200,       # … getting faster by this much every second
        "size": 12,                 # diameter of the rocket (pixels)
    },
}
MUST_BE_POSITIVE = {"cooldown", "duration", "speed", "size", "charges"}
STATS = copy.deepcopy(DEFAULTS)


def reload(warnings):
    """Reads data/abilities.json again into STATS. Problems are added to warnings (a list)."""
    try:
        data = json.loads(FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("should be { … }")
    except (OSError, ValueError) as error:
        warnings.append(f"abilities.json: can't be read ({error}) – using built-in values")
        data = {}
    STATS.clear()
    STATS.update(copy.deepcopy(DEFAULTS))
    for key in data.keys() - DEFAULTS.keys():
        warnings.append(f"abilities.json: unknown ability \"{key}\" – ignored")
    for key, values in STATS.items():
        entry = data.get(key, {})
        if not isinstance(entry, dict):
            warnings.append(f"abilities.json {key}: should be {{ … }} – using built-in values")
            continue
        for name, value in entry.items():
            if name not in values:
                warnings.append(f"abilities.json {key}: unknown value \"{name}\" – ignored")
            elif (isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0
                  or (value == 0 and name in MUST_BE_POSITIVE)):
                warnings.append(f"abilities.json {key}.{name}: {json.dumps(value)} is not valid – using {values[name]}")
            else:
                values[name] = value
