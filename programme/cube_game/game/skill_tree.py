"""
The core skill tree: permanent upgrades, bought with cores in the game menu between runs. A node can have several
levels (costs: one price per level) and needs other nodes first (requires: all of them).

The tree is a graph: Shop sits in the middle, the branches (BRANCHES – ship, energy, each weapon, abilities,
scouting) grow outwards from it in every direction, also diagonally. Each node has its own place (position, in grid
units from the middle – skill_tree_panel.py says how big a unit is); the lines between nodes come from requires.

The ship starts with nothing but its gun: the shop, the card shop, the other weapons, both abilities and all bonuses
come from here.

What each node costs and does is in data/skilltree.json (explained in data/README.md): its costs and its values –
mostly "per_level", how much one level adds. reload() reads it again – the game menu calls it every time it opens (via
difficulty.reload()). The costs in DEFAULT_NODES and the values in DEFAULT_VALUES below are only the fallback if the
file lacks them or they're invalid.
Upgrades of a weapon, the rocket or the energy are listed in EFFECTS (which value of which part they raise). What the
bought nodes (and the active cards from the card shop) do to a new run is in the functions at the bottom – the game
menu uses them, too, to show the next run's ship.
"""

import json
from dataclasses import dataclass, field, replace
from pathlib import Path

from game.buildings.watchtower import WatchtowerKit
from game.cards import CARDS
from game.dash import Dash
from game.radar import Radar
from game.rocket import Rocket
from game.ship import Ship
from game.weapons import STARTER, WEAPON_TYPES, data, unlocked as weapon_unlocked

FILE = Path(__file__).resolve().parents[1] / "data" / "skilltree.json"

SHOP, DASH, ROCKET, HEAD_START, BIGGER_ARENA, CORE_LUCK, WATCHTOWER = (
    "shop", "dash", "rocket", "head_start", "bigger_arena", "core_luck", "watchtower")
RADAR, RADAR_SIZE, RADAR_COOLDOWN, RADAR_DURATION = "radar", "radar_size", "radar_cooldown", "radar_duration"
BURNING_GROUND = "burning_ground"
ARMOR, RECOVERY = "armor", "recovery"        # the ship's hull
CARD_SHOP = "card_shop"         # the Cards tab of the game menu – without it, no cards (and active ones don't apply)


@dataclass(frozen=True)
class Branch:
    name: str
    color: tuple
    label_at: tuple | None = None       # where its name is written (grid units) – None: its first node names it


BRANCHES = {
    "ship": Branch("Ship", (40, 110, 255), (0, 1.75)),
    "energy": Branch("Energy", (255, 225, 90), (0, -1.1)),
    "gun": Branch("Gun", (235, 235, 235), (-2.3, 0)),
    "machine_gun": Branch("Machine gun", (255, 170, 60)),
    "cannon": Branch("Cannon", (200, 140, 255)),
    "laser": Branch("Laser", (90, 255, 160)),
    "rocket": Branch("Rocket", (255, 70, 50)),
    "dash": Branch("Dash", (80, 200, 255)),
    "scouting": Branch("Scouting", (120, 180, 255)),
}


@dataclass(frozen=True)
class Node:
    key: str                    # saved in the profile – don't rename
    name: str
    description: str
    costs: tuple                # cores for each level – the number of levels is len(costs)
    requires: tuple             # keys of the nodes that have to be bought first (all of them)
    branch: str                 # key in BRANCHES: its colour
    position: tuple             # (x, y) in grid units from the middle of the tree – y grows downwards
    values: dict = field(default_factory=dict, compare=False)   # what it does (DEFAULT_VALUES, data/skilltree.json)

    @property
    def max_level(self):
        return len(self.costs)


# the tree as built in – reload() makes NODES from it with the costs and values of data/skilltree.json. Descriptions
# in DESCRIBED get the node's values filled in ({…}).
DEFAULT_NODES = [
    Node(SHOP, "Shop", "T during a run: buy upgrades with stars. Killed enemies drop stars.", (1,), (), "ship",
         (0, 0)),

    # ship – downwards
    Node(HEAD_START, "Head start", "Every run starts with {per_level:g} more stars.", (2, 3, 5), (SHOP,),
         "ship", (-0.9, 1.1)),
    Node(BIGGER_ARENA, "Bigger arena", "The window starts {width:g} × {height:g} px bigger.",
         (2, 4, 6), (HEAD_START,), "ship", (-0.9, 2.4)),
    Node(CORE_LUCK, "Core luck", "Cores drop more often: +{per_level:.1%} per level.", (3, 6, 9), (SHOP,),
         "ship", (0.9, 1.1)),
    Node(CARD_SHOP, "Card shop", "Unlocks the Cards tab: buy cards with cores – active cards apply at the start of "
         "every run.", (4,), (CORE_LUCK,), "ship", (0.9, 2.4)),
    Node(ARMOR, "Armor", "Every hit squeezes the window less.", (3, 6, 10), (BIGGER_ARENA,), "ship", (-0.9, 3.3)),
    Node(RECOVERY, "Recovery", "After a hit you stay invulnerable for longer.", (2, 4, 6), (ARMOR,), "ship",
         (0, 3.3)),

    # energy and the laser behind it – upwards
    Node("max_energy", "Max energy", "More energy for your weapons.", (2, 4, 6), (SHOP,), "energy", (-0.9, -1.1)),
    Node("energy_regen", "Energy regen", "Energy refills faster.", (2, 4, 6), (SHOP,), "energy", (0.9, -1.1)),
    Node("laser", "Laser", "A weapon: a beam that barely hurts enemies, but pushes the walls hard.", (6,),
         ("max_energy", "energy_regen"), "laser", (0, -2.15)),
    Node("laser_damage", "Damage", "More damage.", (2, 4, 6), ("laser",), "laser", (-1.0, -3.05)),
    Node("laser_energy", "Energy use", "Uses less energy.", (2, 4, 6), ("laser",), "laser", (0, -3.3)),
    Node("laser_wall_push", "Wall push", "Pushes the walls further.", (2, 4, 6), ("laser",), "laser",
         (1.0, -3.05)),

    # the gun (the weapon every ship starts with) – to the left, the machine gun and the cannon behind it
    Node("gun_energy", "Energy use", "Uses less energy.", (2, 3, 5), (SHOP,), "gun", (-1.35, 0)),
    Node("gun_attack_speed", "Attack speed", "Shoots faster.", (2, 3, 5), ("gun_energy",), "gun",
         (-2.3, -0.75)),
    Node("gun_damage", "Damage", "More damage.", (2, 3, 5), ("gun_energy",), "gun", (-2.3, 0.75)),

    Node("machine_gun", "Machine gun", "A weapon: very fast, but its shots spread a lot.", (5,),
         ("gun_attack_speed",), "machine_gun", (-3.4, -1.45)),
    Node("mg_attack_speed", "Attack speed", "Shoots faster – and spreads more.", (2, 4, 6),
         ("machine_gun",), "machine_gun", (-3.0, -2.55)),
    Node("mg_damage", "Damage", "More damage – and spreads more.", (2, 4, 6), ("machine_gun",),
         "machine_gun", (-4.35, -2.05)),
    Node("mg_energy", "Energy use", "Uses less energy.", (2, 4, 6), ("machine_gun",), "machine_gun",
         (-4.6, -0.95)),
    Node("mg_precision", "Precision", "Its shots spread less.", (3, 5, 8), ("mg_attack_speed",),
         "machine_gun", (-3.6, -3.4)),
    Node("mg_wall_push", "Wall push", "Pushes the walls further.", (2, 4, 6), ("mg_damage",),
         "machine_gun", (-5.45, -2.65)),
    Node("mg_shot_speed", "Projectile speed", "Faster projectiles.", (2, 4, 6), ("mg_energy",),
         "machine_gun", (-5.6, -1.3)),

    Node("cannon", "Cannon", "A weapon: slow, heavy shots that pierce an enemy.", (5,), ("gun_damage",), "cannon",
         (-3.4, 1.45)),
    Node("cannon_damage", "Damage", "More damage.", (2, 4, 6), ("cannon",), "cannon", (-3.0, 2.55)),
    Node("cannon_attack_speed", "Attack speed", "Shoots faster.", (2, 4, 6), ("cannon",), "cannon",
         (-4.35, 2.05)),
    Node("cannon_energy", "Energy use", "Uses less energy.", (2, 4, 6), ("cannon",), "cannon",
         (-4.6, 0.95)),
    Node("cannon_piercing", "Piercing", "Each shot pierces one more enemy.", (6, 10), ("cannon_damage",),
         "cannon", (-3.6, 3.4)),
    Node("cannon_shot_speed", "Projectile speed", "Faster projectiles.", (2, 4, 6),
         ("cannon_attack_speed",), "cannon", (-5.45, 2.65)),
    Node("cannon_wall_push", "Wall push", "Pushes the walls further.", (2, 4, 6), ("cannon_energy",),
         "cannon", (-5.6, 1.3)),

    # abilities – to the right: the dash in the middle, the rocket below
    Node(DASH, "Dash", "SHIFT: a quick burst in the direction you're moving.", (3,), (SHOP,), "dash", (1.6, 0)),

    Node(ROCKET, "Rocket", "SPACE: a rocket that explodes at the mouse and pushes the walls out.", (4,), (SHOP,),
         "rocket", (2.6, 1.25)),
    Node("rocket_cooldown", "Cooldown", "Ready again sooner.", (2, 4, 6), (ROCKET,), "rocket",
         (3.95, 0.6)),
    Node("rocket_radius", "Blast radius", "The blast reaches further.", (2, 4, 6), (ROCKET,), "rocket",
         (4.1, 1.65)),
    Node("rocket_damage", "Damage", "More damage.", (2, 4, 6), (ROCKET,), "rocket", (3.3, 2.7)),
    Node("rocket_wall_push", "Wall push", "Pushes the walls further.", (2, 4, 6), (ROCKET,), "rocket",
         (2.0, 2.7)),
    Node(BURNING_GROUND, "Burning ground", "The blast leaves burning ground behind that hurts enemies.",
         (15,), ("rocket_cooldown", "rocket_radius", "rocket_damage"), "rocket", (5.35, 2.35)),

    # watchtower and radar – up and to the right
    Node(WATCHTOWER, "Watchtower",
         "B: throw a tower (stars) – its own window keeps watching there. +{per_level:g} tower per level.", (3, 5, 8),
         (SHOP,), "scouting", (2.6, -1.25)),
    Node(RADAR, "Radar", "Every now and then a light blue window shows the biggest enemy group out of sight.", (4,),
         (WATCHTOWER,), "scouting", (3.8, -1.95)),
    Node(RADAR_SIZE, "Scan size", "The radar's window gets bigger.", (2, 4, 6), (RADAR,), "scouting", (3.4, -3.15)),
    Node(RADAR_COOLDOWN, "Scan rate", "The radar scans more often.", (2, 4, 6), (RADAR,), "scouting", (4.75, -2.95)),
    Node(RADAR_DURATION, "Scan time", "The radar's window stays open longer.", (2, 4, 6), (RADAR,), "scouting",
         (5.25, -1.75)),
]
# what each node does – the fallback for data/skilltree.json. "per_level": how much one level adds (to the value in
# EFFECTS, or as below); nodes that only unlock something have none.
DEFAULT_VALUES = {
    HEAD_START: {"per_level": 10},                  # stars at the start of a run
    BIGGER_ARENA: {"per_level": (60, 40)},          # pixels wider, higher
    CORE_LUCK: {"per_level": 0.005},                # drop chance (on top of the level's)
    ARMOR: {"per_level": 5},                        # percent off every hit
    RECOVERY: {"per_level": 0.15},                  # seconds invulnerable after a hit
    "max_energy": {"per_level": 20},
    "energy_regen": {"per_level": 4},
    "gun_energy": {"per_level": -1},
    "gun_attack_speed": {"per_level": 0.3},
    "gun_damage": {"per_level": 0.4},
    "mg_attack_speed": {"per_level": 1, "spread_per_level": 3},
    "mg_damage": {"per_level": 0.1, "spread_per_level": 3},
    "mg_energy": {"per_level": -0.4},
    "mg_precision": {"per_level": -6},
    "mg_wall_push": {"per_level": 1.5},
    "mg_shot_speed": {"per_level": 100},
    "cannon_damage": {"per_level": 1},
    "cannon_attack_speed": {"per_level": 0.1},
    "cannon_energy": {"per_level": -2},
    "cannon_piercing": {"per_level": 1},
    "cannon_shot_speed": {"per_level": 80},
    "cannon_wall_push": {"per_level": 6},
    "laser_damage": {"per_level": 0.01},
    "laser_energy": {"per_level": -0.12},
    "laser_wall_push": {"per_level": 0.4},
    "rocket_cooldown": {"per_level": -0.6},
    "rocket_radius": {"per_level": 15},
    "rocket_damage": {"per_level": 1},
    "rocket_wall_push": {"per_level": 20},
    BURNING_GROUND: {"duration": 3, "damage_per_second": 1.5, "radius": 0.8},   # radius: share of the blast radius
    WATCHTOWER: {"per_level": 1},                   # towers standing at once
    RADAR_SIZE: {"per_level": 30},                  # pixels
    RADAR_COOLDOWN: {"per_level": -0.75},           # seconds (negative: sooner)
    RADAR_DURATION: {"per_level": 1},               # seconds
}
MUST_NOT_BE_NEGATIVE = {HEAD_START, BIGGER_ARENA, CORE_LUCK, WATCHTOWER, BURNING_GROUND, ARMOR, RECOVERY}
DESCRIBED = {HEAD_START, BIGGER_ARENA, CORE_LUCK, WATCHTOWER}      # descriptions with their values in them
NODES = []                      # the tree as it is now (filled by reload(), changed in place)
NODES_BY_KEY = {}


def reload(warnings):
    """Reads data/skilltree.json again into NODES and NODES_BY_KEY. Problems are added to warnings (a list)."""
    try:
        data = json.loads(FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("should be { … }")
    except (OSError, ValueError) as error:
        warnings.append(f"skilltree.json: can't be read ({error}) – using built-in values")
        data = {}
    for key in data.keys() - {node.key for node in DEFAULT_NODES}:
        warnings.append(f"skilltree.json: unknown node \"{key}\" – ignored")
    NODES.clear()
    for node in DEFAULT_NODES:
        entry = data.get(node.key, {})
        if not isinstance(entry, dict):
            warnings.append(f"skilltree.json {node.key}: should be {{ … }} – using built-in values")
            entry = {}
        costs, values = read_node(node, entry, warnings)
        description = node.description
        if node.key in DESCRIBED:
            per_level = values["per_level"]
            texts = dict(width=per_level[0], height=per_level[1]) if isinstance(per_level, tuple) else values
            description = description.format(**texts)
        NODES.append(replace(node, costs=costs, values=values, description=description))
    NODES_BY_KEY.clear()
    NODES_BY_KEY.update((node.key, node) for node in NODES)


def read_node(node, entry, warnings):
    """(costs, values) of node: the valid ones from its entry in the file, else the built-in ones."""
    costs, values = node.costs, dict(DEFAULT_VALUES.get(node.key, {}))
    for name, value in entry.items():
        where = f"skilltree.json {node.key}.{name}"
        if name == "costs":
            if (isinstance(value, list) and value
                    and all(isinstance(cost, int) and not isinstance(cost, bool) and cost >= 0 for cost in value)):
                costs = tuple(value)
            else:
                warnings.append(f"{where}: {json.dumps(value)} is not valid (whole numbers, one per level) – using "
                                f"{json.dumps(list(costs))}")
        elif name not in values:
            known = ", ".join(["costs", *values]) or "costs"
            warnings.append(f"skilltree.json {node.key}: unknown value \"{name}\" – ignored (only {known})")
        elif isinstance(values[name], tuple):           # a pair: Bigger arena's [wider, higher]
            if isinstance(value, list) and len(value) == 2 and all(number(part, False) for part in value):
                values[name] = tuple(value)
            else:
                warnings.append(f"{where}: {json.dumps(value)} is not valid ([wider, higher]) – using "
                                f"{json.dumps(values[name])}")
        elif number(value, node.key not in MUST_NOT_BE_NEGATIVE):
            values[name] = value
        else:
            warnings.append(f"{where}: {json.dumps(value)} is not valid – using {json.dumps(values[name])}")
    return costs, values


def number(value, negative_allowed):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return negative_allowed or value >= 0


def amount(profile, key, name="per_level"):
    """What the bought levels of node key add: its value name × its level (0 if not bought)."""
    return NODES_BY_KEY[key].values[name] * profile.level(key)


reload([])                      # until the game menu reads it again (with its warnings)

# upgrade nodes: node key -> (part, value) – the part is a weapon's key, "rocket", "energy" (the ship's) or "ship"
# (its hull), the value what one level raises by the node's "per_level"
EFFECTS = {
    "max_energy": ("energy", "max"),
    "energy_regen": ("energy", "regen"),
    ARMOR: ("ship", "armor"),
    RECOVERY: ("ship", "invulnerable_time"),
    "gun_energy": ("gun", "energy_use"),
    "gun_attack_speed": ("gun", "attack_speed"),
    "gun_damage": ("gun", "damage"),
    "mg_attack_speed": ("machine_gun", "attack_speed"),
    "mg_damage": ("machine_gun", "damage"),
    "mg_energy": ("machine_gun", "energy_use"),
    "mg_precision": ("machine_gun", "spread"),
    "mg_wall_push": ("machine_gun", "wall_push"),
    "mg_shot_speed": ("machine_gun", "projectile_speed"),
    "cannon_damage": ("cannon", "damage"),
    "cannon_attack_speed": ("cannon", "attack_speed"),
    "cannon_energy": ("cannon", "energy_use"),
    "cannon_piercing": ("cannon", "piercing"),
    "cannon_shot_speed": ("cannon", "projectile_speed"),
    "cannon_wall_push": ("cannon", "wall_push"),
    "laser_damage": ("laser", "damage"),
    "laser_energy": ("laser", "energy_use"),
    "laser_wall_push": ("laser", "wall_push"),
    "rocket_cooldown": ("rocket", "cooldown"),
    "rocket_radius": ("rocket", "blast_radius"),
    "rocket_damage": ("rocket", "damage"),
    "rocket_wall_push": ("rocket", "wall_push"),
}
EFFECT_UNITS = {"damage": " damage", "attack_speed": " shots/s", "energy_use": " energy per shot",
                "wall_push": " px wall push", "projectile_speed": " px/s projectile speed", "spread": "° spread",
                "piercing": " enemy pierced", "max": " max energy", "regen": " energy/s", "cooldown": " s cooldown",
                "blast_radius": " px blast radius", "armor": "% less damage from hits",
                "invulnerable_time": " s invulnerable after a hit"}
PER_SECOND = {"damage": " damage/s", "energy_use": " energy/s", "wall_push": " px/s wall push"}    # the laser's


def effect_text(node):
    """What one level of an upgrade node does, e.g. "+0.4 damage per level" – None for nodes without a number."""
    if node.key not in EFFECTS:
        return None
    part, value = EFFECTS[node.key]
    per_level = node.values["per_level"]
    if part == "laser" and value in PER_SECOND:         # its values are per bolt – per second says more
        text = f"{per_level * data.STATS[part]['attack_speed']:+.3g}{PER_SECOND[value]}"
    else:
        text = f"{per_level:+g}{EFFECT_UNITS[value]}"
    if "spread_per_level" in node.values:
        text += f", {node.values['spread_per_level']:+g}° spread"
    return text + " per level"


# --- what the bought nodes do to a new run ---

def start_ship(profile, center):
    """The ship a run starts with: the weapons of the loadout (at least the gun), its energy and hull, the unlocked
    abilities, the watchtower kit, the head start stars and the active cards (once the card shop is unlocked) – with
    every bought upgrade."""
    ship = Ship(center)
    ship.weapons = [build_weapon(profile, key) if key and weapon_unlocked(profile, key) else None
                    for key in profile.loadout]
    if not any(ship.weapons):
        ship.weapons[0] = build_weapon(profile, STARTER)
    for node_key, (part, value) in EFFECTS.items():
        if part in ("energy", "ship") and profile.owns(node_key):
            ship.upgrade(value, amount(profile, node_key))
    ship.abilities = [Dash() if profile.owns(DASH) else None, build_rocket(profile) if profile.owns(ROCKET) else None]
    ship.stars = round(amount(profile, HEAD_START))
    if profile.owns(WATCHTOWER):
        ship.watchtower = WatchtowerKit(max_count=round(amount(profile, WATCHTOWER)))
    for key in profile.active_cards() if profile.owns(CARD_SHOP) else ():
        CARDS[key].apply_card(ship)                  # a dash card without the dash simply changes nothing
    return ship


def build_weapon(profile, key):
    """The weapon key with its bought skill tree upgrades."""
    weapon = WEAPON_TYPES[key]()
    for node_key, (part, value) in EFFECTS.items():
        if part == key and profile.owns(node_key):
            weapon.upgrade(value, amount(profile, node_key))
            if "spread_per_level" in NODES_BY_KEY[node_key].values:      # the machine gun spreads more
                weapon.upgrade("spread", amount(profile, node_key, "spread_per_level"))
    return weapon


def build_rocket(profile):
    """The rocket with its bought skill tree upgrades."""
    rocket = Rocket()
    for node_key, (part, value) in EFFECTS.items():
        if part == "rocket" and profile.owns(node_key):
            rocket.upgrade(value, amount(profile, node_key))
    rocket.burning = dict(NODES_BY_KEY[BURNING_GROUND].values) if profile.owns(BURNING_GROUND) else None
    return rocket


def start_radar(profile):
    """The run's radar with the bought upgrades – None if it isn't unlocked."""
    if not profile.owns(RADAR):
        return None
    return Radar(amount(profile, RADAR_SIZE), amount(profile, RADAR_COOLDOWN), amount(profile, RADAR_DURATION))


def start_arena_size(profile, difficulty):
    width, height = difficulty.arena.start_size
    level = profile.level(BIGGER_ARENA)
    wider, higher = NODES_BY_KEY[BIGGER_ARENA].values["per_level"]
    return round(width + wider * level), round(height + higher * level)


def core_chance(profile, difficulty):
    """Chance that a killed enemy drops a core: the difficulty's plus "Core luck"."""
    return difficulty.core_chance + amount(profile, CORE_LUCK)
