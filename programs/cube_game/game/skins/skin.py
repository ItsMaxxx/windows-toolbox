"""
Base class for enemy skins. A skin draws one enemy in this order:
    draw_below()  – things under the body (barrel, laser, warning line, …)
    buff glow     – if the enemy has an active buff (game/effects/buff_glow.py)
    body          – the square in the skin's colour, white for a moment after a hit; evolutions (tier 2) with a dark
                    frame inside – or the enemy's picture file instead (see below)
    draw_above()  – things on top of the body (e.g. the Carrier's hangar)
    health pips   – once it's damaged
A skin for a new enemy is a subclass that sets color and overrides draw_below/draw_above if it needs to. It may read
the enemy's state (enemy.state, enemy.aim, …), but never change it.

The body, the glow and the pips look the same frame after frame, so they're drawn once into a picture and then only
copied (engine/sprite_cache.py) – one per size, white or not, tier. Only what moves (barrels, arms, lines) is drawn
anew every frame.

Picture files: if assets/images/<enemy key>.png exists (e.g. shooter.png), it's drawn as the body instead of the
square – scaled to the enemy's size, turned to where the enemy faces (drawn facing right), white for a hit. Evolutions
have their own key (fat.png, …), so they get no frame. Everything else (barrels, pips, glow) stays as it is. The files
are read once when the game starts drawing that enemy – a new or changed one shows from the next run of the game.
"""

import math
from pathlib import Path

import pygame

from engine.sprite_cache import PICTURES, load_picture
from game.effects.buff_glow import COLOR as GLOW_COLOR, GAP as GLOW_GAP
from game.effects.buff_glow import buff_glow

IMAGES = Path(__file__).resolve().parents[2] / "assets" / "images"
TURN_STEP = 5               # degrees: a picture file is prepared turned in steps this big (72 pictures for a full turn)
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


def picture_file(key):
    """The enemy's picture file (assets/images/<key>.png) – None if there is none. Read only once."""
    return PICTURES.get(("file", key), lambda: load_picture(IMAGES / f"{key}.png"))


def fit(picture, size):
    """picture scaled to fit into size, keeping its proportions."""
    scale = min(size[0] / picture.get_width(), size[1] / picture.get_height())
    return pygame.transform.smoothscale(picture, (max(1, round(picture.get_width() * scale)),
                                                  max(1, round(picture.get_height() * scale))))


def whitened(picture):
    """The same shape all white (see-through stays see-through) – for the moment after a hit."""
    white = picture.copy()
    white.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGBA_MAX)
    return white


class Skin:
    color = (255, 40, 40)

    def draw(self, surface, enemy, rect):
        """rect: the enemy's body in window coordinates."""
        self.draw_below(surface, enemy, rect)
        size = (int(rect.width), int(rect.height))
        buffs = enemy.active_buffs()
        if buffs:
            color = next((buff.color for buff in buffs if buff.color), GLOW_COLOR)    # a coloured buff shows first
            surface.blit(buff_glow(size, color), (rect.x - GLOW_GAP, rect.y - GLOW_GAP))
        file = picture_file(enemy.key)
        if file is None:
            body = PICTURES.get((type(self), size, enemy.tier, bool(enemy.flash)),
                                lambda: self.make_body(size, enemy.tier, bool(enemy.flash)))
            surface.blit(body, rect)
        else:
            body = self.turned_file(enemy.key, file, size, bool(enemy.flash), enemy.aim)
            surface.blit(body, body.get_rect(center=rect.center))
        self.draw_above(surface, enemy, rect)
        max_hp = max(1, round(enemy.stat("base_hp")))
        if enemy.hp < max_hp:
            self.draw_health(surface, enemy, rect, max_hp)

    def make_body(self, size, tier, flash):
        """The body as a picture: the square in the skin's colour (white for a hit), evolutions with their frame. A skin
        whose body isn't a plain square overrides this."""
        body = pygame.Surface(size, pygame.SRCALPHA)
        body.fill(FLASH_COLOR if flash else self.color)
        if tier == 2:
            draw_tier_frame(body, body.get_rect(), self.color)
        return body

    def turned_file(self, key, file, size, flash, aim):
        """The picture file as the body: scaled, white for a hit, turned towards aim (in TURN_STEP steps)."""
        def make_scaled():
            scaled = fit(file, size)
            return whitened(scaled) if flash else scaled

        angle = round(-aim.as_polar()[1] / TURN_STEP) * TURN_STEP % 360      # screen y points down: turn the other way
        scaled = PICTURES.get(("file", key, size, flash), make_scaled)
        return PICTURES.get(("file", key, size, flash, angle), lambda: pygame.transform.rotate(scaled, angle))

    def draw_below(self, surface, enemy, rect):
        pass

    def draw_above(self, surface, enemy, rect):
        pass

    def draw_health(self, surface, enemy, rect, max_hp):
        """One pip per hit point above the enemy – filled ones are left."""
        filled = math.ceil(enemy.hp)
        pips = PICTURES.get(("pips", self.color, max_hp, filled), lambda: self.make_pips(max_hp, filled))
        surface.blit(pips, (rect.centerx - pips.get_width() / 2, rect.top - PIP_SIZE[1] - 4))

    def make_pips(self, max_hp, filled):
        width, height = PIP_SIZE
        pips = pygame.Surface((max_hp * width + (max_hp - 1) * 2, height), pygame.SRCALPHA)
        for index in range(max_hp):
            pygame.draw.rect(pips, self.color if index < filled else PIP_EMPTY, (index * (width + 2), 0, width, height))
        return pips
