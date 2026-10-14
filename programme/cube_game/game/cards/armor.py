"""
Armor card: Every hit squeezes the arena a few pixels less (flat – strong against many small hits).
"""

from game.cards.card import Card


class ArmorCard(Card):
    key = "armor"
    name = "Armor"
    category = "Ship"
    stat = "armor"
    amount = 2
    card_amount = 6
    unit = " px"
