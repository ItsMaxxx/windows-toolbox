"""
The outline around an enemy with an active buff (see game/enemies/buff.py) – so the player sees who got stronger.
Drawn once per size and then reused (engine/sprite_cache.py).
"""

import pygame

from engine.sprite_cache import PICTURES

COLOR = (255, 70, 150)
GAP = 4                     # pixels between the enemy and the outline


def buff_glow(size):
    """The outline for an enemy of size, as a picture – put its top left corner GAP pixels up and left of the enemy's."""
    def make():
        glow = pygame.Surface((size[0] + 2 * GAP, size[1] + 2 * GAP), pygame.SRCALPHA)
        pygame.draw.rect(glow, COLOR, glow.get_rect(), 2, border_radius=3)
        return glow

    return PICTURES.get(("buff glow", tuple(size)), make)
