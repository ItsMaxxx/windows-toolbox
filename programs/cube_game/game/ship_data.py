"""
The ships' base values: data/ships.json (every value explained in data/README.md). reload() reads it again into SHIPS –
the game menu calls it every time it opens (via difficulty.reload()). What's missing or invalid in a ship's entry keeps
the value in DEFAULTS, and a warning goes to the game menu.

Every entry under "ships" is one ship; "ship" in the file says which one is flown (there's no choice in the game menu
yet). A new ship is just a new entry – values it leaves out are those in DEFAULTS.
"""

import json
from pathlib import Path

FILE = Path(__file__).resolve().parents[1] / "data" / "ships.json"
DEFAULT_KEY = "standard"
DEFAULTS = {
    "name": "Standard",             # shown in the game
    "size": 30,                     # hitbox (square) and size of the ship
    "speed": 280,                   # pixels per second
    "max_energy": 100,              # energy for the weapons (full at the start) …
    "energy_regen": 20,             # … and how much comes back per second
    "invulnerable_time": 0.5,       # seconds after a hit in which it can't be hit again (it blinks)
    "armor": 0,                     # pixels every hit squeezes the arena less (flat, game/armor.py)
    "magnet_radius": 130,           # stars and cores this close get pulled in
    "color": (40, 110, 255),
}
MUST_BE_POSITIVE = {"size", "speed", "max_energy"}
SHIPS = {DEFAULT_KEY: dict(DEFAULTS)}       # ship key -> its values
selected = DEFAULT_KEY                      # the key of the ship that's flown


def current():
    """The values of the ship that's flown."""
    return SHIPS[selected]


def reload(warnings):
    """Reads data/ships.json again into SHIPS and selected. Problems are added to warnings (a list)."""
    global selected
    try:
        data = json.loads(FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("should be { … }")
    except (OSError, ValueError) as error:
        warnings.append(f"ships.json: can't be read ({error}) – using built-in values")
        data = {}
    for key in data.keys() - {"ship", "ships"}:
        warnings.append(f"ships.json: unknown key \"{key}\" – ignored")
    entries = data.get("ships", {DEFAULT_KEY: {}})
    if not isinstance(entries, dict) or not entries:
        warnings.append("ships.json ships: should be { \"name\": { … }, … } with at least one ship – using built-in "
                        "values")
        entries = {DEFAULT_KEY: {}}
    SHIPS.clear()
    for key, entry in entries.items():
        if not isinstance(entry, dict):
            warnings.append(f"ships.json {key}: should be {{ … }} – using built-in values")
            entry = {}
        SHIPS[key] = read_ship(key, entry, warnings)
    selected = data.get("ship", next(iter(SHIPS)))
    if selected not in SHIPS:
        fallback = next(iter(SHIPS))
        warnings.append(f"ships.json ship: {json.dumps(selected)} isn't one of the ships – flying \"{fallback}\"")
        selected = fallback


def read_ship(key, entry, warnings):
    values = dict(DEFAULTS)
    for name, value in entry.items():
        if name not in DEFAULTS:
            warnings.append(f"ships.json {key}: unknown value \"{name}\" – ignored")
        elif valid(name, value):
            values[name] = tuple(value) if name == "color" else value
        else:
            warnings.append(f"ships.json {key}.{name}: {json.dumps(value)} is not valid – using "
                            f"{json.dumps(DEFAULTS[name])}")
    return values


def valid(name, value):
    if name == "name":
        return isinstance(value, str) and value.strip() != ""
    if name == "color":         # [red, green, blue], each 0 … 255
        return (isinstance(value, list) and len(value) == 3
                and all(isinstance(part, int) and not isinstance(part, bool) and 0 <= part <= 255 for part in value))
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return value > 0 if name in MUST_BE_POSITIVE else value >= 0
