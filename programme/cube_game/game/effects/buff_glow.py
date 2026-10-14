"""
The outline around an enemy with an active buff (see game/enemies/buff.py) – so the player sees who got stronger.
"""

import pygame

COLOR = (255, 70, 150)
GAP = 4                     # pixels between the enemy and the outline


def draw_buff_glow(surface, rect):
    """rect: the enemy's body in window coordinates."""
    pygame.draw.rect(surface, COLOR, rect.inflate(2 * GAP, 2 * GAP), 2, border_radius=3)
