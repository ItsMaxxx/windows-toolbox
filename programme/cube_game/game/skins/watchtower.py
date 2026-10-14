"""
How the watchtower looks: a light blue square base (the player's side is blue) with a dark lens in the middle and a
radar line sweeping round it – it's watching. In the air it's drawn bigger the higher it is, with its shadow on the
ground below. A bar above it shows the time it has left; in the last seconds it blinks.
"""

import math

import pygame

COLOR = (120, 180, 255)
LENS = (12, 24, 48)
SWEEP_SPEED = 2.5           # how fast the radar line turns (radians per second)
SHADOW = (30, 30, 36)
BAR_SIZE = (30, 4)         # the time bar
PIP_EMPTY = (70, 70, 70)
BLINK_FROM = 2.0           # seconds left from which it blinks …
BLINK_RATE = 6             # … this often per second
AREA_ALPHA = 110           # the outline of its area


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
        blink = tower.landed and tower.time_left < BLINK_FROM and int(tower.time_left * BLINK_RATE) % 2
        pygame.draw.rect(surface, PIP_EMPTY if blink else self.color, body, border_radius=4)
        radius = body.width * 0.3
        pygame.draw.circle(surface, LENS, body.center, radius)
        if tower.landed:
            angle = tower.age * SWEEP_SPEED
            end = (body.centerx + math.cos(angle) * radius, body.centery + math.sin(angle) * radius)
            pygame.draw.line(surface, self.color, body.center, end, 2)
            self.draw_time(surface, tower, body)

    def draw_time(self, surface, tower, rect):
        """A bar above it: the part still filled is the time left."""
        width, height = BAR_SIZE
        bar = pygame.Rect(0, 0, width, height)
        bar.midbottom = (rect.centerx, rect.top - 4)
        share = tower.time_left / tower.values["lifetime"]
        pygame.draw.rect(surface, PIP_EMPTY, bar)
        pygame.draw.rect(surface, self.color, (bar.left, bar.top, round(width * share), height))

    def draw_area(self, surface, rect):
        """Its area (rect, in window coordinates): a thin outline – enemies in it take more damage."""
        layer = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(layer, (*self.color, AREA_ALPHA), layer.get_rect(), 1)
        surface.blit(layer, rect.topleft)
