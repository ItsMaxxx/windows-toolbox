"""
Rocket cooldown card: The rocket is ready again sooner (not below its min_cooldown in data/abilities.json).
"""

from game import ability_data
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

    @property
    def minimum(self):
        return ability_data.STATS["rocket"]["min_cooldown"]

    def targets(self, ship):
        return [ability for ability in ship.abilities if isinstance(ability, Rocket)]
