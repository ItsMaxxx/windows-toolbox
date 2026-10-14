"""
Wall push card: Shots push the wall they hit further out, for every weapon (in the shop during a run: for one).
"""

from game.cards.card import WeaponCard


class WallPushCard(WeaponCard):
    key = "wall_push"
    name = "Wall push"
    stat = "wall_push"
    amount = 3
    card_amount = 10
    unit = " px"
