"""
The levels (A1 … A6, B1 … B6, Survival), chosen in the game menu before a run. Each one is a JSON file in
data/difficulties/ – its goal (how long to survive to clear it), what unlocks it, arena, cores, how fast and which
enemies spawn (and how that changes over time), swarms, phases, evolutions (tier 2 enemies spawning instead of tier 1),
the enemies' own values on this level (enemy_stats) and the hints shown in the game menu (README.md there explains
every value). Change the numbers there, no code needed. In the code they're still called "difficulties".

Loading never crashes the game: a value that's missing or doesn't make sense falls back to the default below (the
field defaults of the classes), a broken file is skipped. Everything that went wrong ends up in WARNINGS, which the
game menu shows. The files are read again every time the game menu opens (data/enemies.json too, see roster.py), so
changes show up without a restart.
"""

import json
import re
from dataclasses import dataclass, field, fields, replace
from pathlib import Path

from game import ability_data, buildings, cards, radar, ship_data, shop_data, skill_tree
from game.enemies import roster
from game.enemies.roster import ENEMY_TYPES, EVOLUTIONS, EnemyRoster, stat_names
from game.weapons import data as weapon_data

FOLDER = Path(__file__).resolve().parents[1] / "data" / "difficulties"
MUST_BE_POSITIVE = {"start_interval", "min_interval", "growth_time", "shrink_speed"}   # 0 would break the game
CHANGE = re.compile(r"^\s*([+\-x*])\s*(\d+(?:\.\d+)?)\s*$")     # "+1", "-10", "x1.5" in enemy_stats


@dataclass(frozen=True)
class Unlock:
    requires: str | None = None     # file name (without .json) of the level to clear first (its goal) – None: open


@dataclass(frozen=True)
class Arena:
    start_size: tuple = (800, 560)  # width, height (the skill tree's "Bigger arena" adds to it)
    shrink_speed: float = 20        # pixels per second each edge moves in at the start …
    shrink_growth: float = 0        # … plus this much per minute played …
    max_shrink_speed: float = 60    # … up to this
    armor: float = 0                # pixels every push of an edge is shorter (phases can change it)
    push_falloff: float = 0         # pushes get weaker the further the arena is out already – 0: off (game/arena.py)


@dataclass(frozen=True)
class Spawning:
    first_spawn: float = 2.0        # seconds until the first enemy
    start_interval: float = 2.6     # seconds between enemies at the start …
    min_interval: float = 0.9       # … getting shorter down to this
    interval_drop: float = 0.012    # seconds less per second played


@dataclass(frozen=True)
class EnemyEntry:
    type: str = "basic"             # key in ENEMY_TYPES
    weight: float = 1               # how likely compared to the others …
    after: float = 0                # … from this many seconds played on …
    growth: float = 0               # … plus this much weight per minute since then


@dataclass(frozen=True)
class Swarms:
    type: str = "basic"
    after: float = 0                # no swarms before this many seconds
    start_chance: float = 0.02      # chance per second at the start …
    chance_growth: float = 0.0008   # … plus this much per second played …
    max_chance: float = 0.15        # … up to this
    start_size: int = 6             # enemies in a swarm at the start …
    growth_time: float = 10         # … one more every this many seconds …
    max_size: int = 40              # … up to this
    min_gap: float = 6              # seconds at least between two swarms (of this kind)


@dataclass(frozen=True)
class Evolution:
    """How likely a tier 1 type spawns as its evolution (tier 2, roster.EVOLUTIONS) instead."""
    type: str = "basic"             # the tier 1 type
    chance: float = 0.1             # chance per enemy of that type at the start …
    after: float = 0                # … from this many seconds played on …
    growth: float = 0               # … plus this much per minute since then …
    max_chance: float = 1           # … up to this


@dataclass(frozen=True)
class Phase:
    """A stretch of the run (from start to end seconds) with different spawn weights and/or buffs on the enemies."""
    start: float = 0                # "from" in the file
    end: float | None = None        # "to" in the file – None: until the run ends
    weights: tuple = ()             # (type, operation, number) – on the spawn weights while it lasts
    enemy_stats: tuple = ()         # (target, stat, operation, number) – buffs while it lasts: add or multiply only
    announce: str | None = None     # shown on screen when it starts
    arena: tuple = ()               # (value, operation, number) – the arena's ARENA_CHANGES while it lasts
    spawn: tuple = ()               # (type, count) – extra enemies once, when it starts
    spawn_interval: tuple = ()      # (operation, number) – on the seconds between enemies while it lasts (or empty)


@dataclass(frozen=True)
class Difficulty:
    key: str                        # the file name without .json – saved in the profile
    name: str = ""
    description: str = ""
    order: float = 0                # position in the game menu (smallest first)
    goal: float | None = None       # seconds to survive to clear it (unlocks the next) – None: endless (Survival)
    core_chance: float = 0.01       # chance that a killed enemy drops a core
    unlock: Unlock = field(default_factory=Unlock)
    arena: Arena = field(default_factory=Arena)
    spawning: Spawning = field(default_factory=Spawning)
    enemies: tuple = (EnemyEntry(),)
    swarms: tuple = (Swarms(),)     # every kind of swarm on this difficulty, each with its own chance
    phases: tuple = ()
    evolutions: tuple = ()          # Evolution entries – none: only tier 1 (unless "enemies" names tier 2 types)
    enemy_stats: tuple = ()         # (target, stat, operation, number) – target: "all" or a type; set/add/multiply
    hints: tuple = ()               # short texts for the game menu ("Many ranged units")

    @property
    def requires(self):
        return self.unlock.requires


SECTIONS = {"unlock": Unlock, "arena": Arena, "spawning": Spawning}
ARENA_CHANGES = ("shrink_speed", "armor", "push_falloff")       # arena values a phase can change
DIFFICULTIES = {}                   # key -> Difficulty, in menu order (filled by reload())
WARNINGS = []                       # what went wrong while loading, for the game menu


def default_key():
    """The first difficulty – where a new profile starts."""
    return next(iter(DIFFICULTIES))


def next_difficulty(key):
    """The level that clearing key unlocks – or None for the last."""
    return next((other for other, difficulty in DIFFICULTIES.items() if difficulty.requires == key), None)


def evolution_chance(entry, elapsed):
    """How likely entry's type spawns as its evolution elapsed seconds into the run (0 before entry.after)."""
    if elapsed < entry.after:
        return 0.0
    return min(entry.max_chance, entry.chance + entry.growth * (elapsed - entry.after) / 60)


# --- loading ---

def valid(name, value, default):
    """Does value fit where default is? Numbers ≥ 0 (> 0 for MUST_BE_POSITIVE), text, a pair of sizes, …"""
    if name == "goal":                                      # seconds, or null for endless
        return value is None or (isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0)
    if name == "hints":
        return isinstance(value, list) and all(isinstance(text, str) for text in value)
    if isinstance(default, (int, float)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            return False
        return value > 0 or name not in MUST_BE_POSITIVE
    if isinstance(default, str):
        return isinstance(value, str) and (name != "type" or value in ENEMY_TYPES)
    if isinstance(default, tuple):
        return (isinstance(value, list) and len(value) == len(default)
                and all(isinstance(number, (int, float)) and number > 0 for number in value))
    return value is None or isinstance(value, str)          # default None: an optional name


def read_values(cls, data, file, section="", skip=()):
    """The valid values for cls's fields from data (a dict from JSON) – what's missing or invalid is left out (so the
    field's default is used) and noted in WARNINGS. section: where in the file (for the warnings), skip: fields that
    aren't read here."""
    if not isinstance(data, dict):
        WARNINGS.append(f"{file} {section}: should be {{ … }} – using the defaults")
        return {}
    allowed = [item for item in fields(cls) if item.name not in skip]
    values = {}
    for item in allowed:
        if item.name not in data:
            continue
        value = data[item.name]
        if valid(item.name, value, item.default):
            values[item.name] = tuple(value) if isinstance(value, list) else value
        else:
            where = f"{section}.{item.name}" if section else item.name
            WARNINGS.append(f"{file} {where}: {json.dumps(value)} is not valid – using {json.dumps(item.default)}")
    for key in data.keys() - {item.name for item in allowed}:
        WARNINGS.append(f"{file} {section or 'top level'}: unknown key \"{key}\" – ignored")
    return values


def read(cls, data, file, section):
    return cls(**read_values(cls, data, file, section))


def load_file(path):
    file = path.name
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("should be { … }")
    sections = {name: read(cls, data.get(name, {}), file, name) for name, cls in SECTIONS.items()}
    enemies = []
    entries = data.get("enemies", [])
    if not isinstance(entries, list):
        WARNINGS.append(f"{file} enemies: should be a list [ … ]")
        entries = []
    for index, entry in enumerate(entries):
        if isinstance(entry, dict) and entry.get("type", "basic") not in ENEMY_TYPES:
            # a typo in the type would otherwise quietly turn into a basic enemy
            WARNINGS.append(f"{file} enemies[{index}]: unknown type {json.dumps(entry['type'])} – skipped")
            continue
        enemies.append(read(EnemyEntry, entry, file, f"enemies[{index}]"))
    if not enemies:
        WARNINGS.append(f"{file} enemies: none given – only basic enemies")
        enemies = [EnemyEntry()]
    special = {*SECTIONS, "enemies", "swarms", "phases", "enemy_stats", "evolutions"}
    plain = {key: value for key, value in data.items() if key not in special}
    top = read_values(Difficulty, plain, file, skip=("key", *special))
    top.setdefault("name", path.stem.capitalize())
    return Difficulty(key=path.stem, enemies=tuple(enemies), swarms=read_swarms(data, file),
                      phases=read_phases(data, file), evolutions=read_evolutions(data, file),
                      enemy_stats=read_enemy_stats(data.get("enemy_stats", {}), file), **top, **sections)


def read_evolutions(data, file):
    """ "evolutions": [{"type": "basic", "chance": 0.1, "after": 60, "growth": 0.05, "max_chance": 0.4}, …]"""
    section = data.get("evolutions", [])
    if not isinstance(section, list):
        WARNINGS.append(f"{file} evolutions: should be a list [ … ] – ignored")
        return ()
    evolutions = []
    for index, entry in enumerate(section):
        if not isinstance(entry, dict) or entry.get("type", "basic") not in EVOLUTIONS:
            kind = json.dumps(entry.get("type")) if isinstance(entry, dict) else "it"
            WARNINGS.append(f"{file} evolutions[{index}]: {kind} has no evolution (only {', '.join(EVOLUTIONS)}) – "
                            f"skipped")
            continue
        evolutions.append(read(Evolution, entry, file, f"evolutions[{index}]"))
    return tuple(evolutions)


def read_swarms(data, file):
    """ "swarms": one { … } or a list of them (one per kind of swarm, e.g. basic and charger), [] for none."""
    section = data.get("swarms", {})
    if isinstance(section, dict):
        return (read(Swarms, section, file, "swarms"),)
    if not isinstance(section, list):
        WARNINGS.append(f"{file} swarms: should be {{ … }} or a list [ … ] – using the defaults")
        return (Swarms(),)
    swarms = []
    for index, entry in enumerate(section):
        if isinstance(entry, dict) and entry.get("type", "basic") not in ENEMY_TYPES:
            WARNINGS.append(f"{file} swarms[{index}]: unknown type {json.dumps(entry['type'])} – skipped")
            continue
        swarms.append(read(Swarms, entry, file, f"swarms[{index}]"))
    return tuple(swarms)


def read_phases(data, file):
    """ "phases": [{"from": 180, "to": 220, "weights": {"sniper": "x3"}, "enemy_stats": {…}, "announce": "…"}, …]"""
    section = data.get("phases", [])
    if not isinstance(section, list):
        WARNINGS.append(f"{file} phases: should be a list [ … ] – ignored")
        return ()
    phases = []
    for index, entry in enumerate(section):
        where = f"phases[{index}]"
        if not isinstance(entry, dict):
            WARNINGS.append(f"{file} {where}: should be {{ … }} – skipped")
            continue
        for key in entry.keys() - {"from", "to", "weights", "enemy_stats", "announce", "arena", "spawn",
                                   "spawn_interval"}:
            WARNINGS.append(f"{file} {where}: unknown key \"{key}\" – ignored")
        start, end = entry.get("from", 0), entry.get("to")
        if not valid("from", start, 0.0):
            WARNINGS.append(f"{file} {where}.from: {json.dumps(start)} is not valid (seconds) – skipped")
            continue
        if end is not None and not (valid("to", end, 0.0) and end > start):
            WARNINGS.append(f"{file} {where}.to: {json.dumps(end)} is not valid (seconds after \"from\") – skipped")
            continue
        announce = entry.get("announce")
        if announce is not None and not isinstance(announce, str):
            WARNINGS.append(f"{file} {where}.announce: should be a text – ignored")
            announce = None
        stats = []
        for change in read_enemy_stats(entry.get("enemy_stats", {}), file, f"{where}.enemy_stats"):
            if change[2] == "set":
                WARNINGS.append(f"{file} {where}.enemy_stats.{change[0]}.{change[1]}: only \"+1\", \"-1\" or "
                                f"\"x1.5\" in a phase – ignored")
            else:
                stats.append(change)
        interval = ()
        if "spawn_interval" in entry:
            interval = parse_change(entry["spawn_interval"]) or ()
            if not interval or (interval[0] != "add" and interval[1] <= 0):
                WARNINGS.append(f"{file} {where}.spawn_interval: {json.dumps(entry['spawn_interval'])} is not valid "
                                f"– ignored (seconds, \"-1\", \"+1\" or \"x0.5\")")
                interval = ()
        phases.append(Phase(start, end, read_weights(entry.get("weights", {}), file, f"{where}.weights"),
                            tuple(stats), announce, read_arena_changes(entry.get("arena", {}), file, f"{where}.arena"),
                            read_spawn(entry.get("spawn", {}), file, f"{where}.spawn"), interval))
    return tuple(phases)


def read_spawn(section, file, where):
    """ {"shooter": 4, "basic": 2} as (type, count) – enemies that come once, when the phase starts."""
    if not isinstance(section, dict):
        WARNINGS.append(f"{file} {where}: should be {{ … }} – ignored")
        return ()
    spawn = []
    for key, count in section.items():
        if key not in ENEMY_TYPES:
            WARNINGS.append(f"{file} {where}: unknown enemy type \"{key}\" – ignored")
        elif isinstance(count, bool) or not isinstance(count, int) or count < 1:
            WARNINGS.append(f"{file} {where}.{key}: {json.dumps(count)} is not valid – ignored "
                            f"(a whole number, 1 or more)")
        else:
            spawn.append((key, count))
    return tuple(spawn)


def read_arena_changes(section, file, where):
    """ {"armor": "+3", "shrink_speed": "x1.5"} as (value, operation, number) – like enemy_stats' values."""
    if not isinstance(section, dict):
        WARNINGS.append(f"{file} {where}: should be {{ … }} – ignored")
        return ()
    changes = []
    for name, value in section.items():
        change = parse_change(value)
        if name not in ARENA_CHANGES:
            WARNINGS.append(f"{file} {where}: unknown value \"{name}\" – ignored (only {', '.join(ARENA_CHANGES)})")
        elif change is None:
            WARNINGS.append(f"{file} {where}.{name}: {json.dumps(value)} is not valid – ignored "
                            f"(a number, \"+3\", \"-3\" or \"x1.5\")")
        else:
            changes.append((name, *change))
    return tuple(changes)


def read_weights(section, file, where):
    """ {"sniper": "x3", "charger": "+20", "basic": 0} as (type, operation, number) – like enemy_stats' values."""
    if not isinstance(section, dict):
        WARNINGS.append(f"{file} {where}: should be {{ … }} – ignored")
        return ()
    changes = []
    for key, value in section.items():
        change = parse_change(value)
        if key not in ENEMY_TYPES:
            WARNINGS.append(f"{file} {where}: unknown enemy type \"{key}\" – ignored")
        elif change is None:
            WARNINGS.append(f"{file} {where}.{key}: {json.dumps(value)} is not valid – ignored "
                            f"(a number, \"+10\", \"-10\" or \"x3\")")
        else:
            changes.append((key, *change))
    return tuple(changes)


def read_enemy_stats(section, file, where="enemy_stats"):
    """ {"all": {"base_hp": "+1"}, "charger": {"speed": 100, "contact_damage": "x1.5"}} (a difficulty's or a phase's
    "enemy_stats") as a list of (target, stat, operation, number) – in file order, "all" first, so a type's own entry
    comes after it."""
    if not isinstance(section, dict):
        WARNINGS.append(f"{file} {where}: should be {{ … }} – ignored")
        return ()
    changes = []
    for target in sorted(section, key=lambda name: name != "all"):
        values = section[target]
        if target != "all" and target not in ENEMY_TYPES:
            WARNINGS.append(f"{file} {where}: unknown enemy type \"{target}\" – ignored")
            continue
        if not isinstance(values, dict):
            WARNINGS.append(f"{file} {where}.{target}: should be {{ … }} – ignored")
            continue
        known = {name for key in ENEMY_TYPES for name in stat_names(key)} if target == "all" else stat_names(target)
        for name, value in values.items():
            change = parse_change(value)
            if name not in known:
                WARNINGS.append(f"{file} {where}.{target}: unknown stat \"{name}\" – {roster.unknown_stat(name)}")
            elif change is None:
                WARNINGS.append(f"{file} {where}.{target}.{name}: {json.dumps(value)} is not valid – ignored "
                                f"(a number, \"+1\", \"-1\" or \"x1.5\")")
            else:
                changes.append((target, name, *change))
    return tuple(changes)


def parse_change(value):
    """3 -> ("set", 3), "+1" -> ("add", 1), "-2" -> ("add", -2), "x1.5" / "*1.5" -> ("multiply", 1.5); else None."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return ("set", value)
    match = CHANGE.match(value) if isinstance(value, str) else None
    if not match:
        return None
    sign, number = match.group(1), float(match.group(2))
    if sign in "x*":
        return ("multiply", number)
    return ("add", number if sign == "+" else -number)


def reload():
    """Reads data/enemies.json, data/upgrades.json, data/shop.json, data/weapons.json, data/abilities.json,
    data/buildings.json, data/radar.json, data/ships.json, data/skilltree.json and every file in FOLDER again
    (DIFFICULTIES and WARNINGS are changed in place)."""
    WARNINGS.clear()
    roster.reload(WARNINGS)
    cards.reload(WARNINGS)
    weapon_data.reload(WARNINGS)
    shop_data.reload(WARNINGS)              # after the weapons: their upgrade_factor is the fallback
    ability_data.reload(WARNINGS)
    buildings.reload(WARNINGS)
    radar.reload(WARNINGS)
    ship_data.reload(WARNINGS)
    skill_tree.reload(WARNINGS)
    loaded = []
    for path in sorted(FOLDER.glob("*.json")):
        try:
            loaded.append(load_file(path))
        except (OSError, ValueError) as error:
            WARNINGS.append(f"{path.name}: can't be read ({error}) – skipped")
    if not loaded:
        WARNINGS.append(f"no difficulty files in {FOLDER} – using built-in values")
        loaded = [Difficulty(key="normal", name="Normal")]
    loaded.sort(key=lambda difficulty: difficulty.order)
    keys = {difficulty.key for difficulty in loaded}
    goals = {difficulty.key: difficulty.goal for difficulty in loaded}
    for index, difficulty in enumerate(loaded):
        if difficulty.requires is not None and difficulty.requires not in keys:
            WARNINGS.append(f"{difficulty.key}.json unlock.requires: \"{difficulty.requires}\" doesn't exist – open")
            loaded[index] = replace(difficulty, unlock=Unlock())
        elif difficulty.requires is not None and goals[difficulty.requires] is None:
            WARNINGS.append(f"{difficulty.key}.json unlock.requires: \"{difficulty.requires}\" has no goal (can't be "
                            f"cleared) – open")
            loaded[index] = replace(difficulty, unlock=Unlock())
    DIFFICULTIES.clear()
    DIFFICULTIES.update((difficulty.key, difficulty) for difficulty in loaded)
    for difficulty in loaded:
        EnemyRoster(difficulty, WARNINGS)    # only to report enemy_stats that end up invalid (e.g. "-5" on 2 HP)


reload()
