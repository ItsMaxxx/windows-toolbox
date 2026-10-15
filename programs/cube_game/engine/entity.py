"""
Base class for everything in the game world: a rectangle with a colour that can update and draw itself.

Positions are in world coordinates (screen pixels). When drawing, offset is subtracted – the top left corner of the
window – so the entity lands in the right spot inside the window.
"""

import pygame


class Entity:
    def __init__(self, x, y, width, height, color):
        self.rect = pygame.FRect(x, y, width, height)          # FRect: float position, so slow movement isn't lost
        self.color = color

    def update(self, dt):
        """One logic tick. dt in seconds."""

    def draw(self, surface, offset):
        pygame.draw.rect(surface, self.color, self.rect.move(-offset[0], -offset[1]))
