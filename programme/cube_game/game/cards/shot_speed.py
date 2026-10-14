"""
Projectile speed card: Faster projectiles, for every weapon (in the shop during a run: for one).
"""

from game.cards.card import WeaponCard


class ShotSpeedCard(WeaponCard):
    key = "shot_speed"
    name = "Projectile speed"
    stat = "shot_speed"
    amount = 100
    card_amount = 150
    unit = " px/s"
