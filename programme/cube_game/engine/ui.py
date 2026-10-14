"""
Small drawing helpers for menus and panels: fonts, text, panels.
"""

import functools

import pygame

PANEL_FILL = (16, 16, 20)
PANEL_BORDER = (255, 255, 255)


@functools.lru_cache(maxsize=None)
def font(size):
    """pygame's built-in font in the given size (created once, then reused)."""
    return pygame.font.Font(None, size)


def draw_text(surface, text, size, color, alpha=255, **anchor):
    """Draws text and returns its rect. anchor positions it, e.g. center=(100, 50) or topleft=(10, 8).
    alpha < 255 makes it transparent (faded)."""
    image = font(size).render(text, True, color)
    if alpha < 255:
        image.set_alpha(alpha)
    rect = image.get_rect(**anchor)
    surface.blit(image, rect)
    return rect


def wrap(text, size, width):
    """text split into lines (at spaces) that are at most width pixels wide – a single long word stays whole."""
    lines = []
    for word in text.split():
        if lines and font(size).size(f"{lines[-1]} {word}")[0] <= width:
            lines[-1] += f" {word}"
        else:
            lines.append(word)
    return lines


def draw_panel(surface, rect, radius=8):
    """A dark box with a white outline – the background of menus and windows inside the game.
    radius=0 for square corners, e.g. when the panel fills the whole window."""
    pygame.draw.rect(surface, PANEL_FILL, rect, border_radius=radius)
    pygame.draw.rect(surface, PANEL_BORDER, rect, width=2, border_radius=radius)
