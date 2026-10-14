"""
How the watchtower looks: a light blue square base (the player's side is blue) with a dark lens in the middle and a
radar line sweeping round it – it's watching. In the air it's drawn bigger the higher it is, with its shadow on the
ground below. A health bar once it's damaged.
"""

import math

import pygame

COLOR = (120, 180, 255)
LENS = (12, 24, 48)
SWEEP_SPEED = 2.5           # how fast the radar line turns (radians per second)
FLASH_COLOR = (255, 255, 255)
SHADOW = (30, 30, 36)
BAR_SIZE = (30, 4)         # the health bar once it is damaged
PIP_EMPTY = (70, 70, 70)


class WatchtowerSkin:
    color = COLOR

    def draw(self, surface, tower, rect):
        """rect: the tower in window coordinates (on the ground – in flight it's drawn higher and bigger)."""
        if not tower.landed:
            pygame.draw.ellipse(surface, SHADOW, pygame.Rect(rect).inflate(-rect.width * 0.2, -rect.height * 0.4))
            scale = 1 + 0.6 * tower.height
            body = pygame.Rect(0, 0, rect.width * scale, rect.height * scale)
            body.center = (rect.centerx, rect.centery - 30 * tower.height)
        else:
            body = pygame.Rect(rect)
        pygame.draw.rect(surface, FLASH_COLOR if tower.flash else self.color, body, border_radius=4)
        radius = body.width * 0.3
        pygame.draw.circle(surface, LENS, body.center, radius)
        if tower.landed:
            angle = tower.age * SWEEP_SPEED
            end = (body.centerx + math.cos(angle) * radius, body.centery + math.sin(angle) * radius)
            pygame.draw.line(surface, self.color, body.center, end, 2)
            max_hp = max(1, round(tower.values["base_hp"]))
            if tower.hp < max_hp:
                self.draw_health(surface, tower, body, max_hp)

    def draw_health(self, surface, tower, rect, max_hp):
        """A bar above it: the part still filled is the HP left."""
        width, height = BAR_SIZE
        bar = pygame.Rect(0, 0, width, height)
        bar.midbottom = (rect.centerx, rect.top - 4)
        pygame.draw.rect(surface, PIP_EMPTY, bar)
        pygame.draw.rect(surface, self.color, (bar.left, bar.top, round(width * max(0.0, tower.hp) / max_hp), height))
