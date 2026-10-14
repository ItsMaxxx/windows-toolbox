"""
The artillery's warning on the ground: a red circle where the shell will land. A disc grows from the middle until it
fills the circle – when it's full, it explodes. The last moment the outline blinks.
"""

import math

import pygame

COLOR = (255, 70, 50)
FILL_ALPHA = 70             # how see-through the growing disc is (0 = invisible, 255 = solid)
BLINK_FROM = 0.8            # progress after which the outline blinks
BLINK_SPEED = 30


def draw_target_marker(surface, center, radius, progress, age):
    """progress: 0 (just fired) to 1 (lands now). age: seconds since it was fired (for the blinking)."""
    size = math.ceil(radius) * 2 + 2
    disc = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(disc, (*COLOR, FILL_ALPHA), (size / 2, size / 2), radius * progress)
    surface.blit(disc, disc.get_rect(center=(round(center[0]), round(center[1]))))
    if progress < BLINK_FROM or math.sin(age * BLINK_SPEED) > 0:
        pygame.draw.circle(surface, COLOR, center, radius, 2)
    pygame.draw.circle(surface, COLOR, center, 3)           # the exact spot


def draw_landing_marker(surface, center, radius):
    """Where a splitter shell comes down: only a thin ring and the spot – it doesn't hurt there itself, its fragments'
    circles show where they will."""
    dim = [round(channel * 0.6) for channel in COLOR]
    pygame.draw.circle(surface, dim, center, radius, 1)
    pygame.draw.circle(surface, dim, center, 3)
