"""
Energy regen card: The energy comes back faster.
"""

from game.cards.card import Card


class EnergyRegenCard(Card):
    key = "energy_regen"
    name = "Energy regen"
    category = "Ship"
    stat = "energy_regen"
    amount = 2
    card_amount = 6
    unit = "/s"
