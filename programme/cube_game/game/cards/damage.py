"""
Damage card: More damage per shot, for every weapon (in the shop during a run: for one).
"""

from game.cards.card import WeaponCard


class DamageCard(WeaponCard):
    key = "damage"
    name = "Damage"
    stat = "damage"
    amount = 0.5
    card_amount = 2
    unit = ""
