"""
Damage card: More damage per shot, for every weapon.
"""

from game.cards.card import Card


class DamageCard(Card):
    key = "damage"
    name = "Damage"
    category = "Weapons"
    stat = "damage"
    amount = 0.5
    card_amount = 2
    unit = ""

    def targets(self, ship):
        return [weapon for weapon in ship.weapons if weapon]
