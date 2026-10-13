"""
Move speed card: Faster ship: more movement speed.
"""

from game.cards.card import Card


class MoveSpeedCard(Card):
    name = "Move speed"
    category = "Ship"
    stat = "speed"
    amount = 30
    unit = " px/s"
