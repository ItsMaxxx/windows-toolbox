"""
Projectile speed card: Faster projectiles, for every weapon.
"""

from game.cards.card import Card


class ShotSpeedCard(Card):
    key = "shot_speed"
    name = "Projectile speed"
    category = "Weapons"
    stat = "shot_speed"
    amount = 100
    card_amount = 150
    unit = " px/s"

    def targets(self, ship):
        return [weapon for weapon in ship.weapons if weapon]
