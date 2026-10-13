"""
Rocket wall push card: The rocket's blast pushes walls further out.
"""

from game.cards.card import Card
from game.rocket import Rocket


class RocketWallPushCard(Card):
    name = "Rocket wall push"
    category = "Rocket"
    stat = "wall_push"
    amount = 30
    unit = " px"

    def targets(self, ship):
        return [ability for ability in ship.abilities if isinstance(ability, Rocket)]
