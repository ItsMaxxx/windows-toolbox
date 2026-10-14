"""
Base class for cards. A card raises one stat of the ship, its weapons or its abilities by a fixed amount. Cards are
used two ways:
  - in the shop during a run (T): every card is a stat you can upgrade again and again, for stars – each time it
    costs price_step more, and each time it adds amount (game/shop.py),
  - in the game menu: cards bought with cores go into the player's collection; the active ones apply to the ship at
    the start of every run, each adding card_amount – usually more than a shop upgrade (game/card_shop.py).

A card type is a subclass that only sets class attributes:
    key       – its name in the data files and the save file, e.g. "damage" – don't rename
    name      – the stat as shown on the card, e.g. "Damage"
    category  – which part it upgrades: "Ship", "Weapons", "Dash", "Rocket", "Watchtower" (also its colour)
    stat      – the attribute that changes, e.g. "damage"
    amount    – how much one shop upgrade adds, e.g. 1 or -0.5 (cooldowns go down)
    card_amount – how much the card from the game menu adds
    unit      – shown after the numbers, e.g. " px" or " s"
    minimum   – the stat never goes below this (for cooldowns)
and targets(ship): which objects have that stat (the ship, all weapons, the dash, …).

The numbers here are only the fallback – the real values are in data/upgrades.json.
"""

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
    price = 10                  # stars for the first upgrade in a run …
    price_step = 5              # … and this many more for every further one

    @property
    def color(self):
        return CATEGORY_COLORS.get(self.category, (255, 255, 255))

    def targets(self, ship):
        """The objects this card changes. Empty = the ship doesn't have that part (e.g. no dash yet)."""
        return [ship]

    def available(self, ship):
        """True if buying it would change something: the ship has the part, and the stat isn't at its minimum."""
        targets = self.targets(ship)
        if not targets:
            return False
        if self.minimum is not None and self.amount < 0:       # e.g. a cooldown that's already as low as it goes
            return getattr(targets[0], self.stat) > self.minimum
        return True

    def effect(self):
        """The big text on the card (its card_amount), e.g. "+2" or "-0.5 s"."""
        return f"{self.card_amount:+g}{self.unit}"

    def values(self, ship, amount=None):
        """(now, after buying) as text, e.g. ("6/s", "7/s") – read from the first target. amount: what's added (None:
        a shop upgrade's amount)."""
        now = getattr(self.targets(ship)[0], self.stat)
        return f"{now:g}{self.unit}", f"{self.changed(now, amount):g}{self.unit}"

    def changed(self, value, amount=None):
        """value with amount added (None: a shop upgrade's amount), never below the minimum."""
        amount = self.amount if amount is None else amount
        value = round(value + amount, 6)                        # 1.2 - 0.15 would be 1.0499999…
        return max(self.minimum, value) if self.minimum is not None else value

    def apply(self, ship, amount=None):
        """Adds amount to the stat on every target (None: a shop upgrade's amount)."""
        for target in self.targets(ship):
            setattr(target, self.stat, self.changed(getattr(target, self.stat), amount))

    def apply_card(self, ship):
        """The card from the game menu: adds card_amount."""
        self.apply(ship, self.card_amount)
