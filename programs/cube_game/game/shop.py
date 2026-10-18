"""
The shop during a run (T): every stat can be upgraded directly, as often as you like, for stars. Each upgrade of a
stat costs more than the last one of that stat: price + price_step × (times bought in this run) – the numbers are in
data/shop.json. A stat that can't go further (a cooldown at its minimum) is maxed.

Upgrades are cards (game/cards), in sections – only for what the ship has in this run:
  - the ship itself,
  - each weapon in a slot, with its own weapon cards (an upgrade of the gun's damage doesn't touch the cannon, and each
    has its own price),
  - each ability and the watchtower, once unlocked.
"""

from dataclasses import dataclass

from game import settings
from game.cards import CARDS
from game.cards.card import CATEGORY_COLORS, WeaponCard

WEAPON_KEYS = ("Slot 1", "Slot 2")  # one fires at a time (LMB), RMB switches
PART_KEYS = {"Dash": settings.ABILITY_KEY_NAMES[0], "Rocket": settings.ABILITY_KEY_NAMES[1],
             "Watchtower": settings.BUILD_KEY_NAME}


@dataclass(frozen=True)
class Section:
    key: str                    # "ship", "weapon1", "weapon2", "dash", "rocket", "watchtower" – where the panel puts it
    title: str
    color: tuple
    cards: tuple


class Shop:
    def __init__(self, ship):
        self.ship = ship
        self.bought = {}            # card key -> how often it was bought in this run
        self.sections = self.build_sections()      # the loadout doesn't change during a run

    def build_sections(self):
        cards = list(CARDS.values())
        sections = [Section("ship", "Ship", CATEGORY_COLORS["Ship"],
                            tuple(card for card in cards if card.category == "Ship"))]
        for slot, weapon in enumerate(self.ship.weapons):
            if weapon:
                own = tuple(card for card in cards if isinstance(card, WeaponCard) and card.weapon == weapon.key)
                sections.append(Section(f"weapon{slot + 1}", f"{weapon.name} ({WEAPON_KEYS[slot]})", weapon.color,
                                        own))
        for category in ("Dash", "Rocket", "Watchtower"):
            owned = tuple(card for card in cards if card.category == category and self.has_part(card))
            if owned:
                sections.append(Section(category.lower(), f"{category} ({PART_KEYS[category]})",
                                        CATEGORY_COLORS[category], owned))
        return sections

    def has_part(self, card):
        return bool(card.targets(self.ship))

    def level(self, card):
        return self.bought.get(card.key, 0)

    def price(self, card):
        return round(card.price + card.price_step * self.level(card))

    def maxed(self, card):
        return self.has_part(card) and not card.available(self.ship)

    def can_afford(self, card):
        return self.ship.stars >= self.price(card)

    def buy(self, card):
        """One upgrade of card's stat. False if the ship doesn't have the part, it's maxed or too expensive."""
        if not card.available(self.ship) or not self.can_afford(card):
            return False
        self.ship.stars -= self.price(card)
        card.apply(self.ship)
        self.bought[card.key] = self.level(card) + 1
        return True
