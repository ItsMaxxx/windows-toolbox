"""
The shop screen (T): every stat as a row – what it is now, what it becomes, and the price in stars. Click a row to
upgrade it; each upgrade of a stat costs more than the last. Like the inventory, the game is paused and the window
shows only this panel (SIZE is the window size then).

Three columns: the ship and the watchtower on the left, the weapon in slot 1 and the dash in the middle, the weapon in
slot 2 and the rocket on the right (COLUMNS). Only what the ship has in this run is shown – an empty slot or a part
that isn't unlocked yet leaves its place free, and what's below moves up.
"""

import pygame

from engine.ui import draw_panel, draw_text, font
from game import settings
from game.icons import STAR_COLOR, draw_arrow, draw_star

SIZE = (1000, 640)
COLUMNS = (("ship", "watchtower"), ("weapon1", "dash"), ("weapon2", "rocket"))     # Shop section keys
MARGIN = 24
COLUMN_GAP = 16
TOP = 70
HEADER_HEIGHT = 24
ROW_HEIGHT = 50
ROW_GAP = 4
ROW_FILL = (24, 24, 30)
ROW_HOVER_FILL = (34, 34, 42)
TOO_EXPENSIVE = (200, 70, 70)
MESSAGE_TIME = 1200         # milliseconds a message ("Not enough stars") stays visible


class ShopPanel:
    def __init__(self, shop):
        self.shop = shop
        self.hovered = None                     # the card under the mouse
        self.message = ""
        self.message_until = 0

    # --- layout (window coordinates; the panel fills the window) ---

    def layout(self):
        """[(section, header position, [(card, row rect), …]), …] – where everything goes."""
        width = (SIZE[0] - 2 * MARGIN - (len(COLUMNS) - 1) * COLUMN_GAP) // len(COLUMNS)
        sections = {section.key: section for section in self.shop.sections}
        placed = []
        for column, keys in enumerate(COLUMNS):
            x, y = MARGIN + column * (width + COLUMN_GAP), TOP
            for section in (sections[key] for key in keys if key in sections):
                rows = []
                header = (x, y)
                y += HEADER_HEIGHT
                for card in section.cards:
                    rows.append((card, pygame.Rect(x, y, width, ROW_HEIGHT)))
                    y += ROW_HEIGHT + ROW_GAP
                placed.append((section, header, rows))
                y += 10
        return placed

    def card_at(self, position):
        for _, _, rows in self.layout():
            for card, rect in rows:
                if rect.collidepoint(position):
                    return card
        return None

    # --- input ---

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.card_at(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            card = self.card_at(event.pos)
            if card is not None:
                self.buy(card)

    def buy(self, card):
        if self.shop.maxed(card):
            self.show_message(f"{card.name} can't go any further")
        elif not self.shop.buy(card):
            self.show_message("Not enough stars")

    def show_message(self, text):
        self.message = text
        self.message_until = pygame.time.get_ticks() + MESSAGE_TIME

    # --- drawing ---

    def draw(self, surface, ship):
        panel = surface.get_rect()
        draw_panel(surface, panel, radius=0)
        draw_text(surface, "SHOP", 36, settings.TEXT, topleft=(MARGIN, 20))
        self.draw_price(surface, ship.stars, (panel.right - MARGIN, 34), size=32, align="right", color=settings.TEXT)

        for section, (x, y), rows in self.layout():
            draw_text(surface, section.title.upper(), 20, section.color, topleft=(x, y + 4))
            for card, rect in rows:
                self.draw_row(surface, card, rect, section.color)

        bottom = panel.bottom - 14
        if pygame.time.get_ticks() < self.message_until:
            draw_text(surface, self.message, 24, TOO_EXPENSIVE, midbottom=(panel.centerx, bottom - 26))
        else:
            draw_text(surface, "click a stat to upgrade it  ·  every upgrade of a stat costs more than the last", 20,
                      settings.TEXT, alpha=settings.HINT_ALPHA * 2, midbottom=(panel.centerx, bottom - 26))
        draw_text(surface, "T or ESC to close", 22, settings.TEXT, alpha=settings.HINT_ALPHA * 2,
                  bottomright=(panel.right - 20, bottom))

    def draw_row(self, surface, card, rect, color):
        """One stat: color is its section's (a weapon's own colour for its upgrades)."""
        hovered = self.hovered is card
        pygame.draw.rect(surface, ROW_HOVER_FILL if hovered else ROW_FILL, rect, border_radius=6)
        if hovered:
            pygame.draw.rect(surface, color, rect, width=2, border_radius=6)
        pygame.draw.rect(surface, color, (rect.left, rect.top, 4, rect.height),
                         border_top_left_radius=6, border_bottom_left_radius=6)
        name = draw_text(surface, card.name, 22, settings.TEXT, topleft=(rect.left + 14, rect.top + 7))
        level = self.shop.level(card)
        if level:
            draw_text(surface, f"×{level}", 18, settings.TEXT_MUTED, midleft=(name.right + 8, name.centery))
        now, after = card.values(self.shop.ship)
        if self.shop.maxed(card):
            draw_text(surface, now, 19, settings.TEXT_MUTED, topleft=(rect.left + 14, rect.top + 28))
            draw_text(surface, "MAX", 24, settings.TEXT_MUTED, midright=(rect.right - 14, rect.centery))
            return
        left = draw_text(surface, now, 19, settings.TEXT_MUTED, topleft=(rect.left + 14, rect.top + 28))
        draw_arrow(surface, (left.right + 6, left.centery), (left.right + 22, left.centery), settings.TEXT_MUTED)
        draw_text(surface, after, 19, settings.TEXT, midleft=(left.right + 28, left.centery))
        affordable = self.shop.can_afford(card)
        self.draw_price(surface, self.shop.price(card), (rect.right - 14, rect.centery), size=26, align="right",
                        color=settings.TEXT if affordable else TOO_EXPENSIVE)

    @staticmethod
    def draw_price(surface, amount, anchor, size, align, color):
        """A star icon followed by a number. align: where anchor is – "left", "center" or "right" of the whole."""
        width = size * 0.6 + 6 + font(size).size(str(amount))[0]
        x, y = anchor
        left = {"left": x, "center": x - width / 2, "right": x - width}[align]
        draw_star(surface, (left + size * 0.3, y), size * 0.32, STAR_COLOR)
        draw_text(surface, str(amount), size, color, midleft=(left + size * 0.6 + 6, y))
