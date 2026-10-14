"""
What you buy with stars during a run: data/shop.json (explained in data/README.md) – the upgrades in the shop (T: what
one adds and what it costs, game/shop.py), one entry per row of the shop – each weapon's own ("gun_damage",
"mg_damage", …, card.shop_key) –, and the watchtowers (B). reload() reads it again; the game menu calls it every
time it opens (via difficulty.reload()). What's missing or invalid keeps the value in the code, and a warning goes to
the game menu.
"""

import json
from pathlib import Path

from game import cards
from game.cards.card import WeaponCard
from game.weapons import data as weapon_data

FILE = Path(__file__).resolve().parents[1] / "data" / "shop.json"
TOWER_DEFAULTS = {"price": 15, "price_step": 0}     # stars for the first watchtower of a run, and more for each further
TOWER = dict(TOWER_DEFAULTS)


def reload(warnings):
    """Reads data/shop.json again: every card's amount, price and price_step, and TOWER. Problems are added to
    warnings."""
    try:
        data = json.loads(FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("should be { … }")
    except (OSError, ValueError) as error:
        warnings.append(f"shop.json: can't be read ({error}) – using built-in values")
        data = {}
    for key in data.keys() - {"upgrades", "watchtower"}:
        warnings.append(f"shop.json: unknown key \"{key}\" – ignored")
    read_upgrades(data.get("upgrades", {}), warnings)

    TOWER.clear()
    TOWER.update(TOWER_DEFAULTS)
    tower = data.get("watchtower", {})
    for name, value in (tower.items() if isinstance(tower, dict) else ()):
        if name not in TOWER_DEFAULTS:
            warnings.append(f"shop.json watchtower: unknown value \"{name}\" – ignored")
        elif isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            warnings.append(f"shop.json watchtower.{name}: {json.dumps(value)} is not valid – using {TOWER[name]}")
        else:
            TOWER[name] = value


def defaults(card):
    """A card's shop numbers while data/shop.json has no entry for it: its type's – for a weapon card the amount times
    the weapon's upgrade_factor, as it worked before every weapon had its own entry."""
    values = {name: cards.DEFAULTS[type(card)][name] for name in cards.SHOP_NUMBERS}
    if isinstance(card, WeaponCard):
        factor = weapon_data.STATS[card.weapon].get("upgrade_factor", {}).get(card.kind, 1)
        values["amount"] = round(values["amount"] * factor, 6)
    return values


def read_upgrades(upgrades, warnings):
    """Sets amount, price and price_step on every card (cards.CARDS) from its entry in upgrades (by card.shop_key)."""
    by_key = {}
    for card in cards.CARDS.values():
        for name, value in defaults(card).items():
            setattr(card, name, value)
        by_key[card.shop_key] = card
    renamed = {card.kind: card.shop_key for card in cards.CARDS.values() if card.shop_key != card.kind}
    for key, entry in (upgrades.items() if isinstance(upgrades, dict) else ()):
        if key not in by_key:
            if key in renamed:
                own = [card.shop_key for card in cards.CARDS.values() if card.kind == key]
                hint = (f"every weapon has its own now ({', '.join(own)})"
                        if issubclass(cards.CARD_TYPES[key], WeaponCard) else f"it's \"{renamed[key]}\" now")
                warnings.append(f"shop.json upgrades: \"{key}\" – {hint} – ignored")
            else:
                warnings.append(f"shop.json upgrades: unknown upgrade \"{key}\" – ignored")
            continue
        card = by_key[key]
        for name, value in (entry.items() if isinstance(entry, dict) else ()):
            if name not in cards.SHOP_NUMBERS:
                warnings.append(f"shop.json {key}: unknown value \"{name}\" – ignored")
            elif not cards.valid_number(name, value):
                warnings.append(f"shop.json {key}.{name}: {json.dumps(value)} is not valid – "
                                f"using {getattr(card, name)}")
            else:
                setattr(card, name, value)
