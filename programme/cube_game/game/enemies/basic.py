"""
Basic: the red cube. Runs straight at the ship; touching it hurts. Uses the default behaviour of Enemy.
"""

from game.enemies.enemy import Enemy


class BasicEnemy(Enemy):
    name = "Basic"
    max_hp = 2
    speed = 110
    size = 26
    color = (230, 40, 40)
    contact_damage = 1
