"""
A vertical list of buttons, usable with the mouse (hover + click) and the keyboard (W/S or arrow keys, Enter/Space).

Positions are window coordinates (mouse events from pygame are relative to the window, too). The menu is laid out
on every draw, so it stays centred even if the window changes size.
"""

import pygame

UP_KEYS = (pygame.K_w, pygame.K_UP)
DOWN_KEYS = (pygame.K_s, pygame.K_DOWN)
CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)


class Menu:
    def __init__(self, buttons, width=260, height=46, spacing=12, font_size=30):
        self.buttons = buttons
        self.selected = 0
        self.width = width
        self.height = height
        self.spacing = spacing
        self.font_size = font_size

    @property
    def total_height(self):
        return len(self.buttons) * self.height + (len(self.buttons) - 1) * self.spacing

    def layout(self, midtop):
        """Places the buttons below each other, the first one's top centre at midtop."""
        x, y = midtop
        for button in self.buttons:
            button.rect = pygame.Rect(0, 0, self.width, self.height)
            button.rect.midtop = (x, y)
            y += self.height + self.spacing

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in UP_KEYS:
                self.selected = (self.selected - 1) % len(self.buttons)
            elif event.key in DOWN_KEYS:
                self.selected = (self.selected + 1) % len(self.buttons)
            elif event.key in CONFIRM_KEYS:
                self.buttons[self.selected].action()
        elif event.type == pygame.MOUSEMOTION:
            for index, button in enumerate(self.buttons):
                if button.rect.collidepoint(event.pos):
                    self.selected = index
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            # on release, not on press – otherwise the still-held button would fire a shot right after "Play"
            for button in self.buttons:
                if button.rect.collidepoint(event.pos):
                    button.action()
                    break

    def draw(self, surface, midtop):
        self.layout(midtop)
        for index, button in enumerate(self.buttons):
            button.draw(surface, index == self.selected, self.font_size)
