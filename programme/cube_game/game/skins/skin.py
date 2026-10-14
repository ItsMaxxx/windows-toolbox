"""
Base class for enemy skins. A skin draws one enemy in this order:
    draw_below()  – things under the body (barrel, laser, warning line, …)
    buff glow     – if the enemy has an active buff (game/effects/buff_glow.py)
    body          – the square in the skin's colour, white for a moment after a hit
    tier frame    – evolutions (tier 2) only: a dark frame inside the body
    draw_above()  – things on top of the body (e.g. the Carrier's hangar)
    health pips   – once it's damaged
A skin for a new enemy is a subclass that sets color and overrides draw_below/draw_above if it needs to. It may read
the enemy's state (enemy.state, enemy.aim, …), but never change it.
"""

import math

import pygame

from game.effects.buff_glow import draw_buff_glow

FLASH_COLOR = (255, 255, 255)
PIP_SIZE = (6, 4)           # health pips above a damaged enemy
PIP_EMPTY = (70, 70, 70)
TIER_FRAME_SHADE = 0.45     # the tier 2 frame: the body's colour this dark …
TIER_FRAME_INSET = 0.18     # … this far inside the edge (part of the size) …
TIER_FRAME_WIDTH = 0.1      # … and this thick (at least 2 px)


def draw_tier_frame(surface, rect, color):
    """The mark of an evolution: a dark frame inside the body (also used for the icons in the game menu)."""
    inset = round(rect.width * TIER_FRAME_INSET)
    frame = pygame.Rect(rect).inflate(-2 * inset, -2 * inset)
    width = max(2, round(rect.width * TIER_FRAME_WIDTH))
    pygame.draw.rect(surface, [round(channel * TIER_FRAME_SHADE) for channel in color], frame, width)


class Skin:
    color = (255, 40, 40)

    def draw(self, surface, enemy, rect):
        """rect: the enemy's body in window coordinates."""
        self.draw_below(surface, enemy, rect)
        if enemy.active_buffs():
            draw_buff_glow(surface, rect)
        pygame.draw.rect(surface, FLASH_COLOR if enemy.flash else self.color, rect)
        if enemy.tier == 2:
            draw_tier_frame(surface, rect, self.color)
        self.draw_above(surface, enemy, rect)
        max_hp = max(1, round(enemy.stat("base_hp")))
        if enemy.hp < max_hp:
            self.draw_health(surface, enemy, rect, max_hp)

    def draw_below(self, surface, enemy, rect):
        pass

    def draw_above(self, surface, enemy, rect):
        pass

    def draw_health(self, surface, enemy, rect, max_hp):
        """One pip per hit point above the enemy – filled ones are left."""
        width, height = PIP_SIZE
        total = max_hp * width + (max_hp - 1) * 2
        left = rect.centerx - total / 2
        for index in range(max_hp):
            color = self.color if index < math.ceil(enemy.hp) else PIP_EMPTY
            pygame.draw.rect(surface, color, (left + index * (width + 2), rect.top - height - 4, width, height))
