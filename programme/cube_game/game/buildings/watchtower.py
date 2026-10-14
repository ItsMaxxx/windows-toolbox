"""
The watchtower: thrown from the ship (B) in the mouse's direction, throw_range far – out of the arena, too. Where it
lands it opens its own small window (vision × vision pixels, see engine/view_window.py) that keeps showing that spot
for the rest of the run: you see snipers, artillery and swarms coming before they reach the arena.

Enemies can destroy it: touching enemies (their contact damage), enemy shots and artillery strikes hurt it – after a
hit it can't be hurt again for hit_cooldown seconds. Melee enemies (basic, charger, critter) that get within
lure_range of it and are closer to it than to the ship go for the tower instead. Destroyed, its window closes.

Two classes: WatchtowerKit is what the ship carries (skill tree "Watchtower": how many towers at once; the shop and
cards upgrade its vision), Watchtower is one tower in the world. The values are in data/buildings.json.
"""

import math

import pygame

from engine import Entity
from game.skins.watchtower import WatchtowerSkin

KEY = "watchtower"


def values():
    """This building's values from data/buildings.json (imported here: game.buildings imports this file)."""
    from game import buildings
    return buildings.STATS[KEY]


class WatchtowerKit:
    """On the ship (ship.watchtower): how many towers it may have standing at once, how far they see, what the next
    one costs."""
    name = "Watchtower"

    def __init__(self, max_count):
        self.max_count = max_count
        self.vision = values()["vision"]        # side length of a tower's window – upgradeable (card "vision")
        self.bought = 0                         # towers thrown in this run: each one costs price_step more

    @property
    def price(self):
        stats = values()
        return round(stats["price"] + stats["price_step"] * self.bought)


class Watchtower(Entity):
    stats = {                   # fallback only – the real values are in data/buildings.json
        "max_hp": 6,
        "size": 24,             # pixels (square)
        "vision": 320,          # side length of its window
        "throw_range": 420,     # how far it's thrown from the ship
        "throw_time": 0.5,      # seconds in the air
        "price": 15,            # stars for the first tower of a run …
        "price_step": 10,       # … and this many more for every further one
        "hit_cooldown": 0.4,    # seconds after a hit in which it can't be hurt again
        "lure_range": 220,      # melee enemies this close (and closer to it than to the ship) attack it
    }
    skin = WatchtowerSkin()

    def __init__(self, kit, start, target):
        """kit: the ship's WatchtowerKit (its vision is read live, so upgrades widen standing towers' windows, too).
        Flies from start to target, then stands there."""
        self.values = dict(values())
        size = self.values["size"]
        super().__init__(0, 0, size, size, self.skin.color)
        self.kit = kit
        self.start = pygame.Vector2(start)
        self.target = pygame.Vector2(target)
        self.rect.center = self.start
        self.flight = 0.0                       # seconds in the air so far
        self.hp = self.values["max_hp"]
        self.hit_timer = 0.0
        self.flash = 0.0
        self.age = 0.0                          # seconds since it was thrown (for the skin's animation)
        self.view = None                        # its window (Engine.open_view) – None until it lands / if none

    @property
    def landed(self):
        return self.flight >= self.values["throw_time"]

    @property
    def progress(self):
        """0 when thrown … 1 when it lands."""
        return min(1.0, self.flight / self.values["throw_time"])

    @property
    def height(self):
        """How high up it is in its flight (0 on the ground, 1 at the top) – the skin draws it bigger then."""
        return math.sin(math.pi * self.progress)

    @property
    def alive(self):
        return self.hp > 0

    @property
    def center(self):
        return pygame.Vector2(self.rect.center)

    def update(self, dt):
        """True once, in the tick it lands."""
        self.age += dt
        self.hit_timer = max(0.0, self.hit_timer - dt)
        self.flash = max(0.0, self.flash - dt)
        if self.landed:
            return False
        self.flight += dt
        progress = self.progress
        eased = 1 - (1 - progress) ** 2         # fast out of the hand, slowing down before it lands
        self.rect.center = self.start.lerp(self.target, eased)
        return self.landed

    def vision_rect(self, area):
        """Its window on the screen: vision × vision around it, kept on area (the monitor it stands on)."""
        rect = pygame.Rect(0, 0, round(self.kit.vision), round(self.kit.vision))
        rect.center = (round(self.rect.centerx), round(self.rect.centery))
        return rect.clamp(area).clip(area)

    def take_damage(self, amount):
        """Only once it has landed, and not again within hit_cooldown."""
        if not self.landed or self.hit_timer > 0 or amount <= 0:
            return
        self.hp -= amount
        self.hit_timer = self.values["hit_cooldown"]
        self.flash = 0.1

    def draw(self, surface, offset):
        self.skin.draw(surface, self, self.rect.move(-offset[0], -offset[1]))
