"""
A button in a menu: a label and what happens when it's activated. Menu positions and draws it.
"""

import pygame

from engine.ui import draw_text

IDLE_BORDER = (150, 150, 150)
IDLE_TEXT = (210, 210, 210)
SELECTED_FILL = (255, 255, 255)
SELECTED_TEXT = (0, 0, 0)


class Button:
    def __init__(self, label, action):
        self.label = label
        self.action = action                    # function without arguments
        self.rect = pygame.Rect(0, 0, 0, 0)     # set by Menu before drawing

    def draw(self, surface, selected, font_size):
        if selected:
            pygame.draw.rect(surface, SELECTED_FILL, self.rect, border_radius=6)
            text_color = SELECTED_TEXT
        else:
            pygame.draw.rect(surface, IDLE_BORDER, self.rect, width=2, border_radius=6)
            text_color = IDLE_TEXT
        draw_text(surface, self.label, font_size, text_color, center=self.rect.center)
