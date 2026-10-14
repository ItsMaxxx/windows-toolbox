"""
Base class for cards. A card raises one stat of the ship, its weapons or its abilities by a fixed amount. Cards are
used two ways:
  - in the shop during a run (T): every card is a stat you can upgrade again and again, for stars – each time it
    costs price_step more, and each time it adds amount (game/shop.py),
  - in the game menu: cards bought with cores go into the player's collection; the active ones apply to the ship at
    the start of every run, each adding card_amount – usually more than a shop upgrade (game/card_shop.py).

A card type is a subclass that only sets class attributes:
    key       – its name in the data files and the save file, e.g. "damage" – don't rename (a weapon card's key
                in CARDS and the save file adds the weapon: "damage:cannon")
    name      – the stat as shown on the card, e.g. "Damage"
    category  – which part it upgrades: "Ship", "Weapons", "Dash", "Rocket", "Watchtower" (also its colour)
    stat      – the attribute that changes, e.g. "damage"
    amount    – how much one shop upgrade adds, e.g. 1 or -0.5 (cooldowns go down)
    card_amount – how much the card from the game menu adds
    unit      – shown after the numbers, e.g. " px" or " s"
    minimum   – the stat never goes below this (for cooldowns)
    maximum   – the stat never goes above this (for the ship's armor, …)
and targets(ship): which objects have that stat (the ship, all weapons, the dash, …).

A target can scale the card: a weapon's upgrade_factors (from data/weapons.json) say how strongly each card works on
it, by card type key – e.g. the laser gets only 0.02 × the damage, because it fires 30 tiny bolts a second.

Weapon cards (WeaponCard) belong to one weapon each: "Cannon: Damage" only changes the cannon – in the shop during a
run and as a card from the card shop (there it does nothing while the cannon isn't in a slot).

The numbers here are only the fallback – the real values are in data/upgrades.json.
"""

from game.weapons import WEAPON_TYPES, data as weapon_data

CATEGORY_COLORS = {"Ship": (40, 110, 255), "Weapons": (235, 235, 235), "Dash": (80, 200, 255), "Rocket": (255, 70, 50),
                   "Watchtower": (120, 180, 255)}


class Card:
    key = "card"
    name = "Card"
    category = "Ship"
    stat = ""
    amount = 0
    card_amount = 0
    unit = ""
    minimum = None
    maximum = None
    price = 10                  # stars for the first upgrade in a run …
    price_step = 5              # … and this many more for every further one

    @property
    def color(self):
        return CATEGORY_COLORS.get(self.category, (255, 255, 255))

    @property
    def kind(self):
        """The card type's key – its numbers in data/upgrades.json and the weapons' upgrade_factor use it."""
        return type(self).key

    @property
    def label(self):
        """The band on top of the card: what it belongs to."""
        return self.category

    @property
    def full_name(self):
        """Its name where it stands alone, e.g. "Cannon: Damage" (a weapon card)."""
        return self.name

    def targets(self, ship):
        """The objects this card changes. Empty = the ship doesn't have that part (e.g. no dash yet)."""
        return [ship]

    def available(self, ship):
        """True if buying it would change something: the ship has the part, and the stat isn't at its minimum (or
        maximum)."""
        targets = self.targets(ship)
        if not targets:
            return False
        if self.minimum is not None and self.amount < 0:       # e.g. a cooldown that's already as low as it goes
            return getattr(targets[0], self.stat) > self.minimum
        if self.maximum is not None and self.amount > 0:       # e.g. armor that's already as high as it goes
            return getattr(targets[0], self.stat) < self.maximum
        return True

    def effect(self):
        """The big text on the card (its card_amount), e.g. "+2" or "-0.5 s"."""
        return f"{self.card_amount:+g}{self.unit}"

    def values(self, ship, amount=None):
        """(now, after buying) as text, e.g. ("6/s", "7/s") – read from the first target. amount: what's added (None:
        a shop upgrade's amount)."""
        target = self.targets(ship)[0]
        now = getattr(target, self.stat)
        after = self.changed(now, amount, self.factor(target))
        return f"{now:.4g}{self.unit}", f"{after:.4g}{self.unit}"

    def factor(self, target):
        """How strongly this card works on target (1 unless a weapon says otherwise)."""
        return getattr(target, "upgrade_factors", {}).get(self.kind, 1)

    def changed(self, value, amount=None, factor=1):
        """value with amount × factor added (amount None: a shop upgrade's amount), never below the minimum or above
        the maximum."""
        amount = self.amount if amount is None else amount
        value = round(value + amount * factor, 6)               # 1.2 - 0.15 would be 1.0499999…
        if self.minimum is not None:
            value = max(self.minimum, value)
        if self.maximum is not None:
            value = min(self.maximum, value)
        return value

    def apply(self, ship, amount=None):
        """Adds amount to the stat on every target (None: a shop upgrade's amount)."""
        for target in self.targets(ship):
            setattr(target, self.stat, self.changed(getattr(target, self.stat), amount, self.factor(target)))

    def apply_card(self, ship):
        """The card from the game menu: adds card_amount."""
        self.apply(ship, self.card_amount)


class WeaponCard(Card):
    """A card for one weapon: it only changes that weapon, and only while it's in a slot. Every weapon card type exists
    once per weapon (cards/__init__.py) – its key is the type's key and the weapon's, e.g. "damage:cannon"; the numbers
    (amount, …) are the type's, the same for every weapon."""
    category = "Weapons"

    def __init__(self, weapon):
        self.weapon = weapon                    # the weapon's key (game/weapons)
        self.key = f"{type(self).key}:{weapon}"

    @property
    def weapon_type(self):
        return WEAPON_TYPES[self.weapon]

    @property
    def label(self):
        return self.weapon_type.name

    @property
    def full_name(self):
        return f"{self.weapon_type.name}: {self.name}"

    @property
    def color(self):
        return self.weapon_type.color

    def effect(self):
        """What it really adds to its weapon – the card_amount times the weapon's upgrade_factor."""
        factor = weapon_data.STATS[self.weapon].get("upgrade_factor", {}).get(self.kind, 1)
        return f"{round(self.card_amount * factor, 6):+g}{self.unit}"

    def targets(self, ship):
        return [weapon for weapon in ship.weapons if weapon and weapon.key == self.weapon]
