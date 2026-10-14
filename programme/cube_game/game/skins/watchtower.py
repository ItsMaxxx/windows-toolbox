"""
How the watchtower looks: a light blue square base (the player's side is blue) with a dark lens in the middle and a
radar line sweeping round it – it's watching. In the air it's drawn bigger the higher it is, with its shadow on the
ground below. Health pips once it's damaged, like on enemies.
"""

import math

import pygame

COLOR = (120, 180, 255)
LENS = (12, 24, 48)
SWEEP_SPEED = 2.5           # how fast the radar line turns (radians per second)
FLASH_COLOR = (255, 255, 255)
SHADOW = (30, 30, 36)
PIP_SIZE = (6, 4)
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
            max_hp = max(1, round(tower.values["max_hp"]))
            if tower.hp < max_hp:
                self.draw_health(surface, tower, body, max_hp)

    def draw_health(self, surface, tower, rect, max_hp):
        width, height = PIP_SIZE
        total = max_hp * width + (max_hp - 1) * 2
        left = rect.centerx - total / 2
        for index in range(max_hp):
            color = self.color if index < math.ceil(tower.hp) else PIP_EMPTY
            pygame.draw.rect(surface, color, (left + index * (width + 2), rect.top - height - 4, width, height))
