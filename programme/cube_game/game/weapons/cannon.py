"""
The cannon: slow, big, heavy shots. Each one pierces `piercing` enemies – it hurts them fully and flies on – and only
stops at the next one. If it reaches the wall after piercing, it has lost some of its force: its wall push is
multiplied by pierced_push once for every enemy it went through (0.5: half after one, a quarter after two).
The machine gun's opposite: armor (flat, game/armor.py) hardly touches its big hits, but against enemies with few hit
points most of its damage is wasted.
"""

from dataclasses import replace

from game.weapons import data
from game.weapons.weapon import Weapon


class Cannon(Weapon):
    key = "cannon"
    name = "Cannon"
    color = (200, 140, 255)
    description = "Slow, heavy shots that pierce: breaks armor and pushes walls hard, wasted on weak enemies."
    ATTRIBUTES = dict(Weapon.ATTRIBUTES, piercing="pierce")

    def shot_stats(self):
        return replace(super().shot_stats(), pierce=round(self.pierce),
                       pierce_push=data.STATS[self.key]["pierced_push"])

    def stat_lines(self):
        enemies = "enemy" if round(self.pierce) == 1 else "enemies"
        return super().stat_lines() + [("Piercing", f"{round(self.pierce)} {enemies}")]
