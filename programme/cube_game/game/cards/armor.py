"""
Armor card: Every hit squeezes the arena less (not above settings.MAX_SHIP_ARMOR).
"""

from game import settings
from game.cards.card import Card


class ArmorCard(Card):
    key = "armor"
    name = "Armor"
    category = "Ship"
    stat = "armor"
    amount = 3
    card_amount = 10
    unit = "%"
    maximum = settings.MAX_SHIP_ARMOR
