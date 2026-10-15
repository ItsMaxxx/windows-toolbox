"""
Attack speed card: More shots per second, for every weapon (in the shop during a run: for one).
"""

from game.cards.card import WeaponCard


class AttackSpeedCard(WeaponCard):
    key = "attack_speed"
    name = "Attack speed"
    stat = "fire_rate"
    amount = 0.5
    card_amount = 1.5
    unit = "/s"
