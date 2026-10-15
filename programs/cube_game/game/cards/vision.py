"""
Vision card: Bigger watchtower windows – also for towers that are already standing.
"""

from game.cards.card import Card


class VisionCard(Card):
    key = "vision"
    shop_name = "watchtower_vision"
    name = "Vision"
    category = "Watchtower"
    stat = "vision"
    amount = 40
    card_amount = 80
    unit = " px"

    def targets(self, ship):
        return [ship.watchtower] if ship.watchtower else []
