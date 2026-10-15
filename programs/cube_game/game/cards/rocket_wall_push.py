"""
Rocket wall push card: The rocket's blast pushes walls further out.
"""

from game.cards.card import Card
from game.rocket import Rocket


class RocketWallPushCard(Card):
    key = "rocket_wall_push"
    name = "Rocket wall push"
    category = "Rocket"
    stat = "wall_push"
    amount = 20
    card_amount = 60
    unit = " px"

    def targets(self, ship):
        return [ability for ability in ship.abilities if isinstance(ability, Rocket)]
