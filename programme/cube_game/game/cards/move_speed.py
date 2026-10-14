"""
Move speed card: Faster ship: more movement speed.
"""

from game.cards.card import Card


class MoveSpeedCard(Card):
    key = "move_speed"
    name = "Move speed"
    category = "Ship"
    stat = "speed"
    amount = 20
    card_amount = 60
    unit = " px/s"
