"""
Damage card: More damage per shot, for every weapon.
"""

from game.cards.card import Card


class DamageCard(Card):
    name = "Damage"
    category = "Weapons"
    stat = "damage"
    amount = 1
    unit = ""

    def targets(self, ship):
        return [weapon for weapon in ship.weapons if weapon]
