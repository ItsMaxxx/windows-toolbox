"""
Wall push card: Shots push the wall they hit further out, for every weapon.
"""

from game.cards.card import Card


class WallPushCard(Card):
    name = "Wall push"
    category = "Weapons"
    stat = "wall_push"
    amount = 5
    unit = " px"

    def targets(self, ship):
        return [weapon for weapon in ship.weapons if weapon]
