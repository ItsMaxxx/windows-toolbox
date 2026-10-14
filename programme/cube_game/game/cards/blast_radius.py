"""
Blast radius card: The rocket's blast reaches further.
"""

from game.cards.card import Card
from game.rocket import Rocket


class BlastRadiusCard(Card):
    key = "blast_radius"
    name = "Blast radius"
    category = "Rocket"
    stat = "blast_radius"
    amount = 15
    card_amount = 50
    unit = " px"

    def targets(self, ship):
        return [ability for ability in ship.abilities if isinstance(ability, Rocket)]
