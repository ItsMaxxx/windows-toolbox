"""
Rocket damage card: The rocket's blast does more damage.
"""

from game.cards.card import Card
from game.rocket import Rocket


class RocketDamageCard(Card):
    key = "rocket_damage"
    name = "Rocket damage"
    category = "Rocket"
    stat = "damage"
    amount = 2
    card_amount = 6
    unit = ""

    def targets(self, ship):
        return [ability for ability in ship.abilities if isinstance(ability, Rocket)]
