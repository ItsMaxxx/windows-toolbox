"""
Attack speed card: More shots per second, for every weapon.
"""

from game.cards.card import Card


class AttackSpeedCard(Card):
    name = "Attack speed"
    category = "Weapons"
    stat = "fire_rate"
    amount = 1
    unit = "/s"

    def targets(self, ship):
        return [weapon for weapon in ship.weapons if weapon]
