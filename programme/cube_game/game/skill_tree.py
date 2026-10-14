"""
The core skill tree: permanent upgrades, bought with cores in the game menu between runs. A node can have several
levels (costs: one price per level) and needs another node first (requires).

The ship starts with nothing but its gun: the shop, both abilities and all bonuses come from here. What the bought
nodes (and the active cards from the card shop) do to a new run is in the functions at the bottom – the game menu uses
them, too, to show the next run's ship.
"""

from dataclasses import dataclass

from game.buildings.watchtower import WatchtowerKit
from game.cards import CARDS
from game.dash import Dash
from game.radar import Radar
from game.rocket import Rocket
from game.ship import Ship

HEAD_START_STARS = 10           # stars per level of "Head start"
ARENA_BONUS = (60, 40)          # pixels wider/higher per level of "Bigger arena"
CORE_LUCK_BONUS = 0.005         # drop chance per level of "Core luck" (on top of the difficulty's)

SHOP, DASH, ROCKET, HEAD_START, BIGGER_ARENA, CORE_LUCK, WATCHTOWER = (
    "shop", "dash", "rocket", "head_start", "bigger_arena", "core_luck", "watchtower")
RADAR, RADAR_SIZE, RADAR_COOLDOWN, RADAR_DURATION = "radar", "radar_size", "radar_cooldown", "radar_duration"


@dataclass(frozen=True)
class Node:
    key: str                    # saved in the profile – don't rename
    name: str
    description: str
    costs: tuple                # cores for each level – the number of levels is len(costs)
    requires: str | None        # key of the node that has to be bought first
    column: int                 # place in the drawing of the tree
    row: int

    @property
    def max_level(self):
        return len(self.costs)


NODES = [
    Node(SHOP, "Shop", "T during a run: buy upgrades with stars. Killed enemies drop stars.", (1,), None, 1, 0),
    Node(DASH, "Dash", "SHIFT: a quick burst in the direction you're moving.", (3,), SHOP, 0, 1),
    Node(HEAD_START, "Head start", f"Every run starts with {HEAD_START_STARS} more stars.", (2, 3, 5), SHOP, 1, 1),
    Node(ROCKET, "Rocket", "SPACE: a rocket that explodes at the mouse and pushes the walls out.", (4,), SHOP, 2, 1),
    Node(BIGGER_ARENA, "Bigger arena", f"The window starts {ARENA_BONUS[0]} × {ARENA_BONUS[1]} px bigger.",
         (2, 4, 6), DASH, 0, 2),
    Node(CORE_LUCK, "Core luck", f"Cores drop more often: +{CORE_LUCK_BONUS:.1%} per level.", (3, 6, 9), ROCKET, 2, 2),
    Node(WATCHTOWER, "Watchtower",
         "B: throw a tower (stars) – its own window keeps watching there. +1 tower per level.", (3, 5, 8), SHOP, 1, 2),
    Node(RADAR, "Radar", "Every now and then a light blue window shows the biggest enemy group out of sight.", (4,),
         WATCHTOWER, 1, 3),
    Node(RADAR_SIZE, "Scan size", "The radar's window gets bigger.", (2, 4, 6), RADAR, 0, 4),
    Node(RADAR_COOLDOWN, "Scan rate", "The radar scans more often.", (2, 4, 6), RADAR, 1, 4),
    Node(RADAR_DURATION, "Scan time", "The radar's window stays open longer.", (2, 4, 6), RADAR, 2, 4),
]
NODES_BY_KEY = {node.key: node for node in NODES}


# --- what the bought nodes do to a new run ---

def start_ship(profile, center):
    """The ship a run starts with: the gun, the unlocked abilities, the watchtower kit, the head start stars and the
    active cards."""
    ship = Ship(center)
    ship.abilities = [Dash() if profile.owns(DASH) else None, Rocket() if profile.owns(ROCKET) else None]
    ship.stars = HEAD_START_STARS * profile.level(HEAD_START)
    if profile.owns(WATCHTOWER):
        ship.watchtower = WatchtowerKit(max_count=profile.level(WATCHTOWER))
    for key in profile.active_cards():
        CARDS[key].apply_card(ship)                  # a dash card without the dash simply changes nothing
    return ship


def start_radar(profile):
    """The run's radar with the bought upgrades – None if it isn't unlocked."""
    if not profile.owns(RADAR):
        return None
    return Radar(profile.level(RADAR_SIZE), profile.level(RADAR_COOLDOWN), profile.level(RADAR_DURATION))


def start_arena_size(profile, difficulty):
    width, height = difficulty.arena.start_size
    level = profile.level(BIGGER_ARENA)
    return round(width + ARENA_BONUS[0] * level), round(height + ARENA_BONUS[1] * level)


def core_chance(profile, difficulty):
    """Chance that a killed enemy drops a core: the difficulty's plus "Core luck"."""
    return difficulty.core_chance + CORE_LUCK_BONUS * profile.level(CORE_LUCK)
