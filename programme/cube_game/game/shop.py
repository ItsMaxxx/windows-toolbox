"""
The shop's logic: 3 random offers, buying (10 stars, the bought card is replaced by a new random one) and rerolling
all offers (3 stars). The offers stay the same between visits – they only change by buying or rerolling.

Offers are anything with name, price, available(ship) and apply(ship) – for now only cards (game/cards), later also
weapons or abilities.
"""

import random

from game.cards import ALL_CARDS

OFFER_COUNT = 3
REROLL_PRICE = 3            # stars


class Shop:
    def __init__(self, ship):
        self.ship = ship
        self.offers = [None] * OFFER_COUNT
        self.roll()

    def candidates(self, exclude=()):
        """New offers that make sense for this ship right now, without the types in exclude."""
        return [card_type() for card_type in ALL_CARDS
                if card_type not in exclude and card_type().available(self.ship)]

    def roll(self):
        """New random offers, all of different types (free – used at the start and by reroll())."""
        cards = self.candidates()
        picked = random.sample(cards, min(OFFER_COUNT, len(cards)))
        self.offers = picked + [None] * (OFFER_COUNT - len(picked))

    def can_afford(self, price):
        return self.ship.stars >= price

    def reroll(self):
        """Pays REROLL_PRICE for new offers. False if there aren't enough stars."""
        if not self.can_afford(REROLL_PRICE):
            return False
        self.ship.stars -= REROLL_PRICE
        self.roll()
        return True

    def buy(self, index):
        """Buys offer number index (0–2). False if it's empty or too expensive."""
        offer = self.offers[index]
        if offer is None or not self.can_afford(offer.price):
            return False
        self.ship.stars -= offer.price
        offer.apply(self.ship)
        self.offers[index] = None
        for i, card in enumerate(self.offers):
            # the bought slot gets a new card; so does a slot whose card has reached its limit (e.g. a cooldown that
            # can't go lower any more)
            if card is None or not card.available(self.ship):
                self.offers[i] = self.replacement(i)
        return True

    def replacement(self, index):
        """A random new offer for slot index, of a type that isn't in the other slots – or None if there's none."""
        others = {type(card) for i, card in enumerate(self.offers) if card and i != index}
        cards = self.candidates(exclude=others)
        return random.choice(cards) if cards else None
