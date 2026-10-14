"""
Critter: tiny, fast and pale green, dies to one hit. Never spawned on its own – a Carrier keeps releasing them. Runs
straight at the ship like the basic enemy. Drops nothing, otherwise a Carrier would be a star and core farm.
"""

from game.enemies.enemy import Enemy
from game.skins.critter import CritterSkin


class Critter(Enemy):
    key = "critter"
    name = "Critter"
    melee = True
    skin = CritterSkin()
    drops_loot = False
    stats = {"max_hp": 1, "speed": 175, "size": 12, "contact_damage": 1}    # fallback – see data/enemies.json
