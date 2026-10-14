"""
The card shop in the game menu, between runs – paid with cores. It offers a few cards (RULES.offers); buy one and it
goes into the collection, or reroll all offers. Every card in the collection makes the next one more expensive.
The collection holds up to RULES.max_owned cards; up to RULES.max_active of them can be active – those apply to the
ship at the start of every run (skill_tree.start_ship). The same card can be owned and active more than once: they
stack. Selling a card gives a few cores back.

Collection and offers are kept in the profile (saved after every change), so the offers stay the same until you buy
or reroll – closing and opening the game menu doesn't give new ones.
"""

import random

from game import cards, skill_tree
from game.cards import CARDS


class CardShop:
    def __init__(self, profile):
        self.profile = profile
        rules = cards.RULES
        offers = profile.card_offers[:rules.offers]
        self.offers = offers + [None] * (rules.offers - len(offers))
        if not any(self.offers) and not profile.card_offers:
            self.roll()                         # the very first visit: free offers
            self.save()

    @property
    def rules(self):
        return cards.RULES

    # --- prices ---

    def price(self):
        """Cores for the next card: more for every card already in the collection."""
        return self.rules.first_price + self.rules.price_step * len(self.profile.cards)

    def full(self):
        return len(self.profile.cards) >= self.rules.max_owned

    # --- offers ---

    def candidates(self, exclude=()):
        """Card keys worth offering: ones that would change something on the next run's ship (no dash cards without
        the dash), without the keys in exclude."""
        ship = skill_tree.start_ship(self.profile, (0, 0))
        return [key for key, card in CARDS.items() if key not in exclude and card.available(ship)]

    def roll(self):
        """New random offers, all different (free – used for the first visit and by reroll())."""
        keys = self.candidates()
        picked = random.sample(keys, min(self.rules.offers, len(keys)))
        self.offers = picked + [None] * (self.rules.offers - len(picked))

    def reroll(self):
        """Pays reroll_price for new offers. "" if it worked, else why not."""
        if self.profile.cores < self.rules.reroll_price:
            return "Not enough cores"
        self.profile.cores -= self.rules.reroll_price
        self.roll()
        self.save()
        return ""

    def buy(self, index):
        """Buys offer number index into the collection. "" if it worked, else why not."""
        key = self.offers[index]
        if key is None:
            return "Sold out – reroll for new cards"
        if self.full():
            return "Collection full – right-click a card to sell it"
        if self.profile.cores < self.price():
            return "Not enough cores"
        self.profile.cores -= self.price()
        self.profile.cards.append({"key": key, "active": False})
        others = {offer for i, offer in enumerate(self.offers) if offer and i != index}
        keys = self.candidates(exclude=others)
        self.offers[index] = random.choice(keys) if keys else None
        self.save()
        return ""

    # --- collection ---

    def active_count(self):
        return sum(card["active"] for card in self.profile.cards)

    def toggle(self, index):
        """Makes card number index in the collection active or inactive. "" if it worked, else why not."""
        card = self.profile.cards[index]
        if not card["active"] and self.active_count() >= self.rules.max_active:
            return f"Only {self.rules.max_active} cards can be active – deactivate one first"
        card["active"] = not card["active"]
        self.save()
        return ""

    def sell(self, index):
        """Sells card number index for sell_refund cores."""
        self.profile.cards.pop(index)
        self.profile.cores += self.rules.sell_refund
        self.save()

    def save(self):
        self.profile.card_offers = list(self.offers)
        self.profile.save()
