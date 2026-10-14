"""
Magnet card: Stars and cores get pulled in from further away.
"""

from game.cards.card import Card


class MagnetCard(Card):
    key = "magnet"
    name = "Magnet"
    category = "Ship"
    stat = "magnet_radius"
    amount = 25
    card_amount = 70
    unit = " px"
