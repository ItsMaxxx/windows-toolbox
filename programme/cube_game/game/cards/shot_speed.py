"""
Shot speed card: Faster shots, for every weapon.
"""

from game.cards.card import Card


class ShotSpeedCard(Card):
    name = "Shot speed"
    category = "Weapons"
    stat = "shot_speed"
    amount = 150
    unit = " px/s"

    def targets(self, ship):
        return [weapon for weapon in ship.weapons if weapon]
