"""
The shop screen (T): 3 cards to buy, a reroll button and the ship's stats below. Like the inventory, the game is
paused and the window shows only this panel (SIZE is the window size then).

Mouse: hover and click a card to buy it, click "Reroll". Keyboard: 1 2 3 buy, R rerolls.
"""

import pygame

from engine.ui import draw_panel, draw_text, font
from game import settings
from game.icons import STAR_COLOR, draw_arrow, draw_star
from game.shop import REROLL_PRICE

SIZE = (720, 580)
CARD_SIZE = (210, 236)
CARD_GAP = 21
CARD_TOP = 70
CARD_FILL = (24, 24, 30)
CARD_HOVER_FILL = (34, 34, 42)
TOO_EXPENSIVE = (200, 70, 70)
CATEGORY_COLORS = {"Ship": settings.SHIP_COLOR, "Weapons": (235, 235, 235), "Dash": (80, 200, 255),
                   "Rocket": (255, 70, 50)}
REROLL_SIZE = (220, 40)
BUY_KEYS = (pygame.K_1, pygame.K_2, pygame.K_3)
MESSAGE_TIME = 1200         # milliseconds a message ("Not enough stars") stays visible
LINE = (50, 50, 58)


class ShopPanel:
    def __init__(self, shop):
        self.shop = shop
        self.hovered = None                     # index of the card under the mouse, "reroll" or None
        self.message = ""
        self.message_until = 0

    # --- layout (window coordinates; the panel fills the window) ---

    def card_rects(self):
        total = 3 * CARD_SIZE[0] + 2 * CARD_GAP
        left = (SIZE[0] - total) // 2
        return [pygame.Rect(left + index * (CARD_SIZE[0] + CARD_GAP), CARD_TOP, *CARD_SIZE) for index in range(3)]

    def reroll_rect(self):
        rect = pygame.Rect((0, 0), REROLL_SIZE)
        rect.midtop = (SIZE[0] // 2, CARD_TOP + CARD_SIZE[1] + 18)
        return rect

    # --- input ---

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.thing_at(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            thing = self.thing_at(event.pos)
            if thing == "reroll":
                self.reroll()
            elif thing is not None:
                self.buy(thing)
        elif event.type == pygame.KEYDOWN:
            if event.key in BUY_KEYS:
                self.buy(BUY_KEYS.index(event.key))
            elif event.key == pygame.K_r:
                self.reroll()

    def thing_at(self, position):
        for index, rect in enumerate(self.card_rects()):
            if rect.collidepoint(position):
                return index
        return "reroll" if self.reroll_rect().collidepoint(position) else None

    def buy(self, index):
        offer = self.shop.offers[index]
        if offer is not None and not self.shop.buy(index):
            self.show_message("Not enough stars")

    def reroll(self):
        if not self.shop.reroll():
            self.show_message("Not enough stars")

    def show_message(self, text):
        self.message = text
        self.message_until = pygame.time.get_ticks() + MESSAGE_TIME

    # --- drawing ---

    def draw(self, surface, ship):
        panel = surface.get_rect()
        draw_panel(surface, panel, radius=0)
        draw_text(surface, "SHOP", 36, settings.TEXT, topleft=(24, 20))
        self.draw_price(surface, ship.stars, (panel.right - 24, 34), size=32, align="right", color=settings.TEXT)

        for index, (rect, offer) in enumerate(zip(self.card_rects(), self.shop.offers)):
            self.draw_card(surface, rect, offer, ship, index)

        reroll = self.reroll_rect()
        affordable = self.shop.can_afford(REROLL_PRICE)
        if self.hovered == "reroll":
            pygame.draw.rect(surface, CARD_HOVER_FILL, reroll, border_radius=6)
        pygame.draw.rect(surface, settings.TEXT_MUTED, reroll, width=2, border_radius=6)
        draw_text(surface, "Reroll", 26, settings.TEXT, midleft=(reroll.left + 50, reroll.centery))
        self.draw_price(surface, REROLL_PRICE, (reroll.right - 50, reroll.centery), size=26, align="right",
                        color=settings.TEXT if affordable else TOO_EXPENSIVE)
        hint_y = reroll.bottom + 8
        if pygame.time.get_ticks() < self.message_until:
            draw_text(surface, self.message, 22, TOO_EXPENSIVE, midtop=(panel.centerx, hint_y))
        else:
            draw_text(surface, "click or 1 2 3 to buy  ·  R to reroll", 20, settings.TEXT,
                      alpha=settings.HINT_ALPHA * 2, midtop=(panel.centerx, hint_y))

        self.draw_stats(surface, ship, top=hint_y + 34)
        draw_text(surface, "T or ESC to close", 22, settings.TEXT, alpha=settings.HINT_ALPHA * 2,
                  bottomright=(panel.right - 20, panel.bottom - 14))

    def draw_card(self, surface, rect, offer, ship, index):
        hovered = self.hovered == index and offer is not None
        pygame.draw.rect(surface, CARD_HOVER_FILL if hovered else CARD_FILL, rect, border_radius=8)
        if offer is None:
            pygame.draw.rect(surface, LINE, rect, width=1, border_radius=8)
            draw_text(surface, "sold out", 24, settings.TEXT, alpha=settings.HINT_ALPHA, center=rect.center)
            return
        color = CATEGORY_COLORS.get(offer.category, settings.TEXT)
        pygame.draw.rect(surface, color, rect, width=3 if hovered else 1, border_radius=8)
        band = pygame.Rect(rect.left, rect.top, rect.width, 28)
        pygame.draw.rect(surface, color, band, border_top_left_radius=8, border_top_right_radius=8)
        draw_text(surface, offer.category.upper(), 20, settings.BACKGROUND, center=band.center)
        draw_text(surface, str(index + 1), 18, settings.BACKGROUND, midright=(band.right - 10, band.centery))

        draw_text(surface, offer.name, 26, settings.TEXT, midtop=(rect.centerx, rect.top + 44))
        draw_text(surface, offer.effect(), 48, color, midtop=(rect.centerx, rect.top + 80))
        now, after = offer.values(ship)
        y = rect.top + 146
        left = draw_text(surface, now, 22, settings.TEXT_MUTED, midright=(rect.centerx - 18, y))
        draw_arrow(surface, (rect.centerx - 10, y), (rect.centerx + 10, y), settings.TEXT_MUTED)
        draw_text(surface, after, 22, settings.TEXT, midleft=(rect.centerx + 18, left.centery))

        affordable = self.shop.can_afford(offer.price)
        self.draw_price(surface, offer.price, (rect.centerx, rect.bottom - 30), size=30, align="center",
                        color=settings.TEXT if affordable else TOO_EXPENSIVE)

    def draw_price(self, surface, amount, anchor, size, align, color):
        """A star icon followed by a number. align: where anchor is – "left", "center" or "right" of the whole."""
        width = size * 0.6 + 6 + font(size).size(str(amount))[0]
        x, y = anchor
        left = {"left": x, "center": x - width / 2, "right": x - width}[align]
        draw_star(surface, (left + size * 0.3, y), size * 0.32, STAR_COLOR)
        draw_text(surface, str(amount), size, color, midleft=(left + size * 0.6 + 6, y))

    def draw_stats(self, surface, ship, top):
        """The ship's stats in columns – one column per part (ship, weapons, abilities)."""
        groups = ship.stat_groups()
        left, right = 24, SIZE[0] - 24
        draw_text(surface, "YOUR STATS", 22, settings.TEXT_MUTED, topleft=(left, top))
        width = (right - left - (len(groups) - 1) * 16) / len(groups)
        for column, (title, rows) in enumerate(groups):
            x = left + column * (width + 16)
            y = top + 26
            draw_text(surface, title, 22, settings.TEXT, topleft=(x, y))
            for name, value in rows:
                y += 22
                draw_text(surface, name, 19, settings.TEXT_MUTED, topleft=(x, y))
                draw_text(surface, value, 19, settings.TEXT, topright=(x + width, y))
