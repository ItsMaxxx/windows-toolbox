"""
Dash cooldown card: The dash is ready again sooner (not below its min_cooldown in data/abilities.json).
"""

from game import ability_data
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

    @property
    def minimum(self):
        return ability_data.STATS["dash"]["min_cooldown"]

    def targets(self, ship):
        return [ability for ability in ship.abilities if isinstance(ability, Dash)]
