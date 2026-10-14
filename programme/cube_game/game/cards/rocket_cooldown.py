"""
Rocket cooldown card: The rocket is ready again sooner (not below 1.5 s).
"""

from game.cards.card import Card
from game.rocket import Rocket


class RocketCooldownCard(Card):
    key = "rocket_cooldown"
    name = "Rocket cooldown"
    category = "Rocket"
    stat = "cooldown_time"
    amount = -0.3
    card_amount = -1
    unit = " s"
    minimum = 1.5

    def targets(self, ship):
        return [ability for ability in ship.abilities if isinstance(ability, Rocket)]
