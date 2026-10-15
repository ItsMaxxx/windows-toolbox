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
    shop_name – its entry in data/shop.json, if that isn't its key ("rocket_blast_radius"; weapon cards make theirs)
and targets(ship): which objects have that stat (the ship, all weapons, the dash, …).

A target can scale a card from the card shop: a weapon's upgrade_factors (from data/weapons.json) say how strongly each
card works on it, by card type key – e.g. the laser gets only 0.02 × the damage, because it fires 30 tiny bolts a
second. The shop during a run doesn't scale: every card has its own entry in data/shop.json (shop_key – e.g.
"mg_damage"), and its amount is exactly what one upgrade adds.

Weapon cards (WeaponCard) belong to one weapon each: "Cannon: Damage" only changes the cannon – in the shop during a
run and as a card from the card shop (there it does nothing while the cannon isn't in a slot).

The numbers here are only the fallback – the real values are in data/shop.json (amount, price, price_step) and
data/upgrades.json (card_amount).
"""

from game.weapons import WEAPON_TYPES, data as weapon_data

SHOP_PREFIX = {"machine_gun": "mg"}        # weapon key -> its upgrades' prefix in data/shop.json (as in the skill tree)

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
    shop_name = None            # its name in data/shop.json if not its key
    price = 10                  # stars for the first upgrade in a run …
    price_step = 0              # … and this many more for every further one (none unless data/shop.json says so)

    @property
    def color(self):
        return CATEGORY_COLORS.get(self.category, (255, 255, 255))

    @property
    def shop_key(self):
        """Its name in data/shop.json (the type's key, unless shop_name says otherwise)."""
        return self.shop_name or self.key

    @property
    def kind(self):
        """The card type's key – its card_amount in data/upgrades.json and the weapons' upgrade_factor use it."""
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
        after = self.changed(now, *self.step(target, amount))
        return f"{now:.4g}{self.unit}", f"{after:.4g}{self.unit}"

    def step(self, target, amount=None):
        """(amount, factor) for target: a shop upgrade (amount None) adds its own amount exactly, a card from the card
        shop its amount × the target's upgrade_factor."""
        return (self.amount, 1) if amount is None else (amount, self.factor(target))

    def factor(self, target):
        """How strongly this card works on target (1 unless a weapon says otherwise)."""
        return getattr(target, "upgrade_factors", {}).get(self.kind, 1)

    def changed(self, value, amount, factor=1):
        """value with amount × factor added, never below the minimum or above the maximum."""
        value = round(value + amount * factor, 6)               # 1.2 - 0.15 would be 1.0499999…
        if self.minimum is not None:
            value = max(self.minimum, value)
        if self.maximum is not None:
            value = min(self.maximum, value)
        return value

    def apply(self, ship, amount=None):
        """Adds amount to the stat on every target (None: a shop upgrade's amount)."""
        for target in self.targets(ship):
            setattr(target, self.stat, self.changed(getattr(target, self.stat), *self.step(target, amount)))

    def apply_card(self, ship):
        """The card from the game menu: adds card_amount."""
        self.apply(ship, self.card_amount)


class WeaponCard(Card):
    """A card for one weapon: it only changes that weapon, and only while it's in a slot. Every weapon card type exists
    once per weapon (cards/__init__.py) – its key is the type's key and the weapon's, e.g. "damage:cannon"; the numbers
    card_amount is the type's, the same for every weapon (times its upgrade_factor); in the shop during a run each
    weapon has its own entry (shop_key: "gun_damage", "mg_damage", …) with its own amount and prices."""
    category = "Weapons"

    def __init__(self, weapon):
        self.weapon = weapon                    # the weapon's key (game/weapons)
        self.key = f"{type(self).key}:{weapon}"

    @property
    def shop_key(self):
        return f"{SHOP_PREFIX.get(self.weapon, self.weapon)}_{self.kind}"

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
