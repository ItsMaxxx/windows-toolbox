"""
A tiny menu that opens at the mouse, e.g. on a right click: an optional title and a short list of items. Click an
item to do it; a click anywhere else or Esc closes the menu without doing anything.

While it's open, the scene passes every event to handle_event() first – it returns True for the events it used (the
scene then ignores them), so a click that closes the menu doesn't also click whatever is under it.

    menu = ContextMenu(event.pos, [("Sell", sell)], bounds=window_rect, title="Damage +1")
"""

import pygame

from engine.ui import PANEL_FILL, draw_text, font

ITEM_HEIGHT = 30
TITLE_HEIGHT = 26
PADDING = 6
MIN_WIDTH = 120
FONT_SIZE = 24
TITLE_SIZE = 19
BORDER = (110, 110, 125)
HOVER_FILL = (44, 44, 56)
TEXT = (255, 255, 255)
TITLE = (150, 150, 160)


class ContextMenu:
    def __init__(self, position, items, bounds, title=None):
        """position: where the mouse is (the menu's top left corner, moved in to stay inside bounds). items:
        [(label, action), …] – action is called without arguments."""
        self.items = items
        self.title = title
        self.open = True
        self.hovered = None                 # index of the item under the mouse
        texts = [(label, FONT_SIZE) for label, _ in items] + ([(title, TITLE_SIZE)] if title else [])
        width = max([MIN_WIDTH] + [font(size).size(text)[0] + 4 * PADDING for text, size in texts])
        height = 2 * PADDING + len(items) * ITEM_HEIGHT + (TITLE_HEIGHT if title else 0)
        self.rect = pygame.Rect(position, (width, height)).clamp(bounds)

    def item_rect(self, index):
        top = self.rect.top + PADDING + (TITLE_HEIGHT if self.title else 0) + index * ITEM_HEIGHT
        return pygame.Rect(self.rect.left + PADDING, top, self.rect.width - 2 * PADDING, ITEM_HEIGHT)

    def item_at(self, position):
        for index in range(len(self.items)):
            if self.item_rect(index).collidepoint(position):
                return index
        return None

    def handle_event(self, event):
        """True if the event was used by the menu (the scene should ignore it then)."""
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.item_at(event.pos)
            return True                     # what's under the menu doesn't light up meanwhile
        if event.type == pygame.MOUSEBUTTONDOWN:
            return True
        if event.type == pygame.MOUSEBUTTONUP:
            index = self.item_at(event.pos)
            self.open = False
            if index is not None and event.button == 1:
                self.items[index][1]()
            return True
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.open = False
            return True
        return False

    def draw(self, surface):
        pygame.draw.rect(surface, PANEL_FILL, self.rect, border_radius=6)
        pygame.draw.rect(surface, BORDER, self.rect, width=1, border_radius=6)
        if self.title:
            draw_text(surface, self.title, TITLE_SIZE, TITLE,
                      midleft=(self.rect.left + 2 * PADDING, self.rect.top + PADDING + TITLE_HEIGHT // 2))
        for index, (label, _) in enumerate(self.items):
            rect = self.item_rect(index)
            if index == self.hovered:
                pygame.draw.rect(surface, HOVER_FILL, rect, border_radius=4)
            draw_text(surface, label, FONT_SIZE, TEXT, midleft=(rect.left + PADDING, rect.centery))
