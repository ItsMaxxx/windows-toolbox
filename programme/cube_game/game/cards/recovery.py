"""
Recovery card: After a hit the ship stays invulnerable for longer (not above settings.MAX_INVULNERABLE_TIME).
"""

from game import settings
from game.cards.card import Card


class RecoveryCard(Card):
    key = "recovery"
    name = "Recovery"
    category = "Ship"
    stat = "invulnerable_time"
    amount = 0.1
    card_amount = 0.3
    unit = " s"
    maximum = settings.MAX_INVULNERABLE_TIME
