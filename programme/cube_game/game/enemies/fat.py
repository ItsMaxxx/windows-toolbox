"""
Fat Guy: the Basic's evolution (tier 2). A bigger, dark red cube with many more hit points – otherwise a Basic: runs
straight at the ship, touching it hurts. Being big, it shoves smaller enemies out of its way.
"""

from game.enemies.basic import BasicEnemy
from game.skins.fat import FatSkin


class FatGuy(BasicEnemy):
    key = "fat"
    name = "Fat Guy"
    tier = 2
    skin = FatSkin()
    stats = {"base_hp": 8, "speed": 90, "size": 38, "contact_damage": 25}    # fallback – see data/enemies.json
