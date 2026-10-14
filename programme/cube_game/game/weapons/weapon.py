"""
Base class for weapons. A weapon sits in one of the ship's weapon slots (chosen in the game menu's Loadout tab) and
decides everything about its shots: damage, attack speed, projectile speed and size, wall push, colour – and how much
of the ship's energy a shot uses. Each weapon has its own cooldown; the energy is shared (Ship.fire checks it).

Its values come from data/weapons.json (STATS[key], see data.py). They are changed two ways:
  - the skill tree: upgrade(name, amount) adds amount to a value, never below its minimum (how much: the node's
    "per_level" in data/skilltree.json × its level – skill_tree.build_weapon),
  - shop upgrades and cards: they set the attributes directly – a shop upgrade by its own amount in data/shop.json,
    a card by its card_amount × upgrade_factors, how strongly cards work on this weapon (game/cards/card.py).
Names are the ones in the data file ("attack_speed"); ATTRIBUTES says which attribute each one is ("fire_rate").

New weapon = subclass with its own key, name and colour (see gun.py); override fire() / make_projectile() for
different patterns (a spread, piercing shots, a beam).
"""

from game.projectile import Projectile
from game.shot_stats import ShotStats
from game.weapons import data

READY = 1e-9        # cooldowns at or below this count as 0 – 1/6 s minus 10 × 1/60 s leaves a tiny float remainder


class Weapon:
    key = "weapon"                  # its name in data/weapons.json, the profile and the skill tree
    name = "Weapon"
    color = (255, 255, 255)
    description = ""               # one short line for the loadout
    ATTRIBUTES = {"damage": "damage", "attack_speed": "fire_rate", "projectile_speed": "shot_speed",
                  "projectile_size": "shot_size", "wall_push": "wall_push", "energy_use": "energy_cost"}
    MINIMUMS = {"fire_rate": 0.1, "shot_speed": 50, "energy_cost": 0.0}       # never below these (else 0)

    def __init__(self):
        stats = data.STATS[self.key]
        for name, attribute in self.ATTRIBUTES.items():
            setattr(self, attribute, stats[name])
        self.upgrade_factors = dict(stats.get("upgrade_factor", {}))      # card key -> factor
        self.cooldown = 0.0                 # seconds until the next shot is possible

    # --- upgrades ---

    def upgrade(self, name, amount):
        attribute = self.ATTRIBUTES[name]
        value = round(getattr(self, attribute) + amount, 6)
        setattr(self, attribute, max(self.MINIMUMS.get(attribute, 0), value))

    # --- firing ---

    @property
    def ready(self):
        return self.cooldown <= READY

    def update(self, dt):
        # may go up to one tick below 0: the leftover time carries over to the next shot, so rates that don't fit
        # the 60 ticks evenly (e.g. 7/s) are still right on average
        self.cooldown = max(self.cooldown - dt, -dt)

    def shot_stats(self):
        """Snapshot of the current values – every shot gets its own copy when it's fired."""
        return ShotStats(damage=self.damage, speed=self.shot_speed, wall_push=self.wall_push, size=self.shot_size,
                         color=self.color)

    def fire(self, origin, direction):
        """New projectiles (a list, so weapons can fire several at once) – empty while cooling down. The ship has
        already checked (and taken) the energy."""
        if not self.ready:
            return []
        self.cooldown += 1 / self.fire_rate
        return [self.make_projectile(origin, direction)]

    def make_projectile(self, origin, direction):
        return Projectile(origin, direction, self.shot_stats())

    def stat_lines(self):
        """(name, value) rows for the inventory and the loadout."""
        return [
            ("Damage", f"{self.damage:g}"),
            ("Attack speed", f"{self.fire_rate:g}/s"),
            ("Wall push", f"{self.wall_push:g} px"),
            ("Projectile speed", f"{self.shot_speed:g} px/s"),
            ("Energy use", f"{self.energy_cost:g} per shot"),
        ]
