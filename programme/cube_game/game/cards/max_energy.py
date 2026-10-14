"""
Max energy card: More energy for both weapons together.
"""

from game.cards.card import Card


class MaxEnergyCard(Card):
    key = "max_energy"
    name = "Max energy"
    category = "Ship"
    stat = "max_energy"
    amount = 10
    card_amount = 30
    unit = ""

    def apply(self, ship, amount=None):
        before = ship.max_energy
        super().apply(ship, amount)
        ship.energy += ship.max_energy - before         # the new part comes filled up
