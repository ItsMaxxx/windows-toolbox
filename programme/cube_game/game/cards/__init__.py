"""
Shop cards: every card raises one stat. ALL_CARDS is what the shop picks from – a new card type goes into its
own file here and into this list.
"""

from game.cards.move_speed import MoveSpeedCard
from game.cards.damage import DamageCard
from game.cards.attack_speed import AttackSpeedCard
from game.cards.wall_push import WallPushCard
from game.cards.shot_speed import ShotSpeedCard
from game.cards.dash_distance import DashDistanceCard
from game.cards.dash_cooldown import DashCooldownCard
from game.cards.rocket_damage import RocketDamageCard
from game.cards.blast_radius import BlastRadiusCard
from game.cards.rocket_wall_push import RocketWallPushCard
from game.cards.rocket_cooldown import RocketCooldownCard

ALL_CARDS = [
    MoveSpeedCard,
    DamageCard,
    AttackSpeedCard,
    WallPushCard,
    ShotSpeedCard,
    DashDistanceCard,
    DashCooldownCard,
    RocketDamageCard,
    BlastRadiusCard,
    RocketWallPushCard,
    RocketCooldownCard,
]
