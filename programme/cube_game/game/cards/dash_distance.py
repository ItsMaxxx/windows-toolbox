"""
Dash distance card: The dash goes further.
"""

from game.cards.card import Card
from game.dash import Dash


class DashDistanceCard(Card):
    key = "dash_distance"
    name = "Dash distance"
    category = "Dash"
    stat = "distance"
    amount = 25
    card_amount = 80
    unit = " px"

    def targets(self, ship):
        return [ability for ability in ship.abilities if isinstance(ability, Dash)]
