"""
Commander: gold, keeps its distance behind the others. Every enemy within its aura (aura_radius – a thin gold ring
around it shows how far) gets faster and hits harder, and keeps that for aura_time seconds after leaving it: its outline
turns gold (Buff.color). The buff from several commanders doesn't stack – it's renewed. Commanders don't buff each
other. Kill it, and its buff runs out soon after.

It often comes with a swarm (a level's swarms can have a "leader"): then it spawns right in the swarm's middle.
"""

from game.enemies.buff import Buff
from game.enemies.enemy import Enemy
from game.skins.commander import AURA_COLOR, CommanderSkin

DAMAGE_STATS = ("contact_damage", "projectile_damage", "blast_damage")


class Commander(Enemy):
    key = "commander"
    name = "Commander"
    skin = CommanderSkin()
    commands = True
    stats = {                       # fallback – see data/enemies.json
        "base_hp": 5, "speed": 85, "size": 30, "contact_damage": 25,
        "preferred_distance": 220,  # keeps this far from the ship …
        "back_off": 80,
        "close_in": 40,
        "aura_radius": 170,         # enemies this close (centre to centre) get the buff …
        "aura_time": 3,             # … and keep it this many seconds after leaving the aura
        "aura_speed": 1.2,          # their speed × this …
        "aura_damage": 1.25,        # … and the damage they do × this
    }

    def act(self, dt, ship):
        self.keep_distance(ship.rect.center, self.stat("preferred_distance"), self.stat("back_off"),
                           self.stat("close_in"), dt)
        return []

    def command(self, enemies):
        radius, time = self.stat("aura_radius"), self.stat("aura_time")
        speed, damage = self.stat("aura_speed"), self.stat("aura_damage")
        center = self.center
        for enemy in enemies:
            if enemy.commands or not enemy.alive or center.distance_to(enemy.center) > radius:
                continue
            enemy.renew_buffs([Buff("speed", factor=speed, duration=time, source=self.key, color=AURA_COLOR)]
                              + [Buff(stat, factor=damage, duration=time, source=self.key) for stat in DAMAGE_STATS])
