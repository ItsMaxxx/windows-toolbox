"""
Basic: the red cube. Runs straight at the ship; touching it hurts. Uses the default behaviour of Enemy.
"""

from game.enemies.enemy import Enemy
from game.skins.basic import BasicSkin


class BasicEnemy(Enemy):
    key = "basic"
    name = "Basic"
    melee = True
    skin = BasicSkin()
    stats = {"max_hp": 2, "speed": 110, "size": 26, "contact_damage": 1}    # fallback – see data/enemies.json
