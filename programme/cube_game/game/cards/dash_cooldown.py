"""
Dash cooldown card: The dash is ready again sooner (not below 0.3 s).
"""

from game.cards.card import Card
from game.dash import Dash


class DashCooldownCard(Card):
    key = "dash_cooldown"
    name = "Dash cooldown"
    category = "Dash"
    stat = "cooldown_time"
    amount = -0.1
    card_amount = -0.3
    unit = " s"
    minimum = 0.3

    def targets(self, ship):
        return [ability for ability in ship.abilities if isinstance(ability, Dash)]
