"""
What stays between runs and after closing the game: cores, bought skill tree nodes, the loadout (which weapon is in
which slot), the card collection and the card shop's offers, the chosen level ("difficulty") and the best time on each
level (which also decides which levels are cleared and so which are unlocked).

Saved as daten\\cube_game.json in the toolbox's main folder, like every toolbox program (see toolbox\\daten.py). A
missing or broken file simply means a fresh start; values that don't make sense are ignored.

The same file holds the settings from the toolbox's Cube Game page under "settings" – the toolbox writes only those,
the game only reads them (settings): save() reads the file fresh first and leaves "settings" (and anything else it
doesn't know) as it is, so neither overwrites the other.
"""

import json
from pathlib import Path

from game import cards, skill_tree
from game.difficulty import DIFFICULTIES, default_key
from game.skill_tree import NODES_BY_KEY
from game.weapons import STARTER, WEAPON_TYPES

FILE = Path(__file__).resolve().parents[3] / "daten" / "cube_game.json"
SETTINGS = {"key_display": True}     # the toolbox page's settings and their defaults (see cube_game_gui.py)
RENAMED_NODES = {"mg_shot_speed": "mg_projectile_speed", "cannon_shot_speed": "cannon_projectile_speed"}   # old -> now


class Profile:
    def __init__(self, file=FILE):
        self.file = Path(file)
        self.cores = 0
        self.levels = {}                # node key -> level bought
        self.loadout = [STARTER, None]  # weapon key in each weapon slot (left / right mouse button), None: empty
        self.difficulty = default_key()
        self.best_times = {}            # difficulty key -> seconds survived
        self.cards = []                 # the card collection: [{"key": "damage:gun", "active": True}, …]
        self.card_offers = []           # the card shop's offers: card keys, None for a sold slot
        self.settings = dict(SETTINGS)  # from the toolbox page – read only

    @classmethod
    def load(cls, file=FILE):
        profile = cls(file)
        try:
            data = json.loads(profile.file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return profile
        if not isinstance(data, dict):
            return profile
        if isinstance(data.get("cores"), int) and data["cores"] >= 0:
            profile.cores = data["cores"]
        for key, level in dict(data.get("levels") or {}).items():
            key = RENAMED_NODES.get(key, key)
            if key in NODES_BY_KEY and isinstance(level, int) and level > 0:
                profile.levels[key] = level     # more than the node has now: level() caps it
        loadout = data.get("loadout")
        if (isinstance(loadout, list) and len(loadout) == 2 and any(loadout)
                and all(key is None or key in WEAPON_TYPES for key in loadout) and loadout[0] != loadout[1]):
            profile.loadout = list(loadout)
        if data.get("difficulty") in DIFFICULTIES:      # a difficulty whose file is gone: back to the first
            profile.difficulty = data["difficulty"]
        for key, seconds in dict(data.get("best_times") or {}).items():
            if key in DIFFICULTIES and isinstance(seconds, (int, float)) and seconds > 0:
                profile.best_times[key] = round(float(seconds), 2)
        if not profile.difficulty_unlocked(profile.difficulty):
            profile.difficulty = default_key()
        rules = cards.RULES
        saved_cards = data.get("cards") if isinstance(data.get("cards"), list) else []
        weapon = profile.loadout[0] or STARTER          # old weapon cards (for every weapon) become this weapon's
        valid = [(cards.saved_key(card.get("key"), weapon), card) for card in saved_cards if isinstance(card, dict)]
        valid = [(key, card) for key, card in valid if key]
        active = 0
        for key, card in valid[:rules.max_owned]:   # never more than allowed (a limit was lowered): the first count
            is_active = card.get("active") is True and active < profile.max_active_cards()
            active += is_active
            profile.cards.append({"key": key, "active": is_active})
        offers = data.get("card_offers")
        if isinstance(offers, list):
            profile.card_offers = [cards.saved_key(key, weapon) for key in offers]
        settings = data.get("settings") if isinstance(data.get("settings"), dict) else {}
        for key, default in SETTINGS.items():
            if isinstance(settings.get(key), type(default)):
                profile.settings[key] = settings[key]
        return profile

    def save(self):
        """Writes the file. False if that didn't work (the game goes on, the progress just isn't kept). What's in the
        file and not the game's (the toolbox's "settings") stays as it is there right now."""
        try:
            data = json.loads(self.file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        if not isinstance(data, dict):
            data = {}
        data.update({"cores": self.cores, "levels": self.levels, "loadout": self.loadout,
                     "difficulty": self.difficulty, "best_times": self.best_times, "cards": self.cards,
                     "card_offers": self.card_offers})
        try:
            self.file.parent.mkdir(parents=True, exist_ok=True)
            self.file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError:
            return False
        return True

    # --- skill tree ---

    def level(self, key):
        """The bought level of node key – at most its levels now (data/skilltree.json may have fewer since)."""
        node = NODES_BY_KEY.get(key)
        return min(self.levels.get(key, 0), node.max_level) if node else self.levels.get(key, 0)

    def owns(self, key):
        return self.level(key) > 0

    def unlocked(self, node):
        """True if every node it requires has been bought – maxed, if it says so (so this one can be bought)."""
        return not self.missing(node)

    def missing(self, node):
        """The keys of the nodes it requires that aren't bought yet (or not maxed yet, for node.requires_max)."""
        if node.requires_max:
            return [key for key in node.requires if not self.maxed(NODES_BY_KEY[key])]
        return [key for key in node.requires if not self.owns(key)]

    def maxed(self, node):
        return self.level(node.key) >= node.max_level

    def next_cost(self, node):
        """Cores for the next level – None if it's already at its maximum."""
        return None if self.maxed(node) else node.costs[self.level(node.key)]

    def can_buy(self, node):
        return self.unlocked(node) and not self.maxed(node) and self.cores >= self.next_cost(node)

    def buy(self, node):
        """Buys the next level and saves. False if that's not possible (locked, maxed, not enough cores)."""
        if not self.can_buy(node):
            return False
        self.cores -= self.next_cost(node)
        self.levels[node.key] = self.level(node.key) + 1
        self.save()
        return True

    def max_active_cards(self):
        """How many cards can be active at once: max_active in data/upgrades.json plus the skill tree's Card slots."""
        return cards.RULES.max_active + round(skill_tree.amount(self, skill_tree.CARD_SLOTS))

    def active_cards(self):
        """The keys of the active cards (a key twice if that card is active twice) – never more than
        max_active_cards(), e.g. after data/skilltree.json lost a level of Card slots."""
        return [card["key"] for card in self.cards if card["active"]][:self.max_active_cards()]

    # --- difficulties and runs ---

    def difficulty_unlocked(self, key):
        requires = DIFFICULTIES[key].unlock.requires
        return requires is None or self.cleared(requires)

    def cleared(self, key):
        """True once a run on level key lasted its goal (never for an endless level)."""
        goal = DIFFICULTIES[key].goal
        return goal is not None and self.best_times.get(key, 0) >= goal

    def record(self, seconds):
        """A run on the current difficulty ended after seconds. True if that's a new best time. Saved to 1/100 s
        (the run's clock adds up 1/60 s steps, so it ends in 240.00000000008 and the like)."""
        seconds = round(seconds, 2)
        if seconds <= self.best_times.get(self.difficulty, 0):
            return False
        self.best_times[self.difficulty] = seconds
        return True
