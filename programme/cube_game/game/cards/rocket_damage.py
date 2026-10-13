"""
Rocket damage card: The rocket's blast does more damage.
"""

from game.cards.card import Card
from game.rocket import Rocket


class RocketDamageCard(Card):
    name = "Rocket damage"
    category = "Rocket"
    stat = "damage"
    amount = 3
    unit = ""

    def targets(self, ship):
        return [ability for ability in ship.abilities if isinstance(ability, Rocket)]
