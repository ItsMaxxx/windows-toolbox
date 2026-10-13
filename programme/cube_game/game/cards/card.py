"""
Base class for shop cards. A card raises one stat of the ship, its weapons or its abilities by a fixed amount.

A card type is a subclass that only sets class attributes:
    name      – the stat as shown on the card, e.g. "Damage"
    category  – which part it upgrades: "Ship", "Weapons", "Dash", "Rocket" (also decides the card's colour)
    stat      – the attribute that changes, e.g. "damage"
    amount    – how much, e.g. 1 or -0.5 (cooldowns go down)
    unit      – shown after the numbers, e.g. " px" or " s"
    minimum   – the stat never goes below this (for cooldowns)
and targets(ship): which objects have that stat (the ship, all weapons, the dash, …).

What the shop needs from anything it sells: name, price, available(ship), apply(ship). Weapons or abilities that can
be bought later only need the same four things.
"""

PRICE = 10                  # stars


class Card:
    name = "Card"
    category = "Ship"
    stat = ""
    amount = 0
    unit = ""
    minimum = None
    price = PRICE

    def targets(self, ship):
        """The objects this card changes. Empty = the ship doesn't have that part, the card isn't offered."""
        return [ship]

    def available(self, ship):
        targets = self.targets(ship)
        if not targets:
            return False
        if self.minimum is not None and self.amount < 0:       # e.g. a cooldown that's already as low as it goes
            return getattr(targets[0], self.stat) > self.minimum
        return True

    def effect(self):
        """The big text on the card, e.g. "+1" or "-0.5 s"."""
        return f"{self.amount:+g}{self.unit}"

    def values(self, ship):
        """(now, after buying) as text, e.g. ("6/s", "7/s") – read from the first target."""
        now = getattr(self.targets(ship)[0], self.stat)
        return f"{now:g}{self.unit}", f"{self.changed(now):g}{self.unit}"

    def changed(self, value):
        value = round(value + self.amount, 6)                   # 1.2 - 0.15 would be 1.0499999…
        return max(self.minimum, value) if self.minimum is not None else value

    def apply(self, ship):
        for target in self.targets(ship):
            setattr(target, self.stat, self.changed(getattr(target, self.stat)))
