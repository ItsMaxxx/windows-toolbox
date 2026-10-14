"""
Cards: every card raises one stat (card.py explains the two ways they're used). CARDS has every card type by its key –
a new card type goes into its own file here and into ALL_CARDS.

Their numbers (amount, card_amount, price, price_step) and the rules of the game menu's card shop (RULES) come from
data/upgrades.json – reload() reads it again; the game menu calls it every time it opens (via difficulty.reload()).
What's missing or invalid there keeps the value in the code, and a warning goes to the game menu.
"""

import json
from dataclasses import dataclass, fields, replace
from pathlib import Path

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
from game.cards.vision import VisionCard
from game.cards.max_energy import MaxEnergyCard
from game.cards.energy_regen import EnergyRegenCard

ALL_CARDS = [
    MoveSpeedCard,
    MaxEnergyCard,
    EnergyRegenCard,
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
    VisionCard,
]
CARDS = {card_type.key: card_type() for card_type in ALL_CARDS}      # key -> the card (cards have no state)
FILE = Path(__file__).resolve().parents[2] / "data" / "upgrades.json"
NUMBERS = ("amount", "card_amount", "price", "price_step")
DEFAULTS = {card_type: {name: getattr(card_type, name) for name in NUMBERS} for card_type in ALL_CARDS}


@dataclass(frozen=True)
class CardShopRules:
    offers: int = 3             # cards offered at once
    first_price: int = 2        # cores for a card while the collection is empty …
    price_step: int = 1         # … and this many more for each card already in it
    reroll_price: int = 1       # cores for new offers
    sell_refund: int = 1        # cores back for selling a card
    max_owned: int = 12
    max_active: int = 3


RULES = CardShopRules()


def valid_number(name, value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    return name in ("amount", "card_amount") or value >= 0     # amounts can go down (cooldowns)


def reload(warnings):
    """Reads data/upgrades.json again: the cards' numbers and RULES. Problems are added to warnings (a list)."""
    global RULES
    try:
        data = json.loads(FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("should be { … }")
    except (OSError, ValueError) as error:
        warnings.append(f"upgrades.json: can't be read ({error}) – using built-in values")
        data = {}
    for card_type, values in DEFAULTS.items():                 # start from the code's values every time
        for name, value in values.items():
            setattr(card_type, name, value)

    upgrades = data.get("upgrades", {})
    for key, entry in (upgrades.items() if isinstance(upgrades, dict) else ()):
        if key not in CARDS:
            warnings.append(f"upgrades.json upgrades: unknown card \"{key}\" – ignored")
            continue
        for name, value in (entry.items() if isinstance(entry, dict) else ()):
            card_type = type(CARDS[key])
            if name not in NUMBERS:
                warnings.append(f"upgrades.json {key}: unknown value \"{name}\" – ignored")
            elif not valid_number(name, value):
                warnings.append(f"upgrades.json {key}.{name}: {json.dumps(value)} is not valid – "
                                f"using {getattr(card_type, name)}")
            else:
                setattr(card_type, name, value)

    rules = data.get("card_shop", {})
    values = {}
    for key, value in (rules.items() if isinstance(rules, dict) else ()):
        if key not in {item.name for item in fields(CardShopRules)}:
            warnings.append(f"upgrades.json card_shop: unknown value \"{key}\" – ignored")
        elif not isinstance(value, int) or isinstance(value, bool) or value < 0 or (key == "offers" and value < 1):
            warnings.append(f"upgrades.json card_shop.{key}: {json.dumps(value)} is not valid (a whole number)")
        else:
            values[key] = value
    RULES = replace(CardShopRules(), **values)
