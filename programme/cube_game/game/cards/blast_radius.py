"""
Blast radius card: The rocket's blast reaches further.
"""

from game.cards.card import Card
from game.rocket import Rocket


class BlastRadiusCard(Card):
    name = "Blast radius"
    category = "Rocket"
    stat = "blast_radius"
    amount = 25
    unit = " px"

    def targets(self, ship):
        return [ability for ability in ship.abilities if isinstance(ability, Rocket)]
