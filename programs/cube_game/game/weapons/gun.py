"""
The gun: the weapon every ship starts with, in weapon slot 1. Single white shots in a straight line – the middle
ground between the machine gun and the cannon. As the starter it has only three skill tree upgrades (damage, attack
speed, energy use).
"""

from game.weapons.weapon import Weapon


class Gun(Weapon):
    key = "gun"
    name = "Gun"
    color = (255, 255, 255)
    description = "The all-rounder: steady shots, fair on energy."
