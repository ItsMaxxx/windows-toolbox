"""
The shop during a run (T): every stat can be upgraded directly, as often as you like, for stars. Each upgrade of a
stat costs more than the last one of that stat: price + price_step × (times bought in this run) – the numbers are in
data/upgrades.json. A stat that can't go further (a cooldown at its minimum) is maxed.

Upgrades are cards (game/cards): the shop offers every card whose part the ship has (no dash yet: no dash upgrades).
"""

from game.cards import CARDS

CATEGORIES = ("Ship", "Weapons", "Dash", "Rocket", "Watchtower")


class Shop:
    def __init__(self, ship):
        self.ship = ship
        self.bought = {}            # card key -> how often it was bought in this run

    def upgrades(self, category):
        """The cards of one category, in their order – also those the ship has no part for (the panel shows them
        as locked)."""
        return [card for card in CARDS.values() if card.category == category]

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
