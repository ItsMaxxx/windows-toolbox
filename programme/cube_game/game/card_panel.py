"""
The "Cards" tab of the game menu: the card shop's offers with a reroll button on top, the collection below (up to
12 cards, the active ones highlighted). Left click an offer: buy it. Left click a card in the collection: make it
active or inactive. Right click a card in the collection: a small menu (menu_items – the game menu opens it) with
"Sell". The logic is in card_shop.py – this file only lays out, draws and turns clicks into calls.
"""

import pygame

from engine.ui import draw_text, font
from game import settings
from game.cards import CARDS
from game.icons import CORE_COLOR, draw_core

OFFER_SIZE = (150, 118)
OFFER_GAP = 16
GRID_COLUMNS = 6
SLOT_SIZE = (94, 56)
SLOT_GAP = 10
COLLECTION_GAP = 28                 # between the offers and the collection's title

FILL = (24, 24, 30)
HOVER_FILL = (34, 34, 42)
EMPTY = (50, 50, 58)
TOO_EXPENSIVE = (200, 70, 70)
SUCCESS = CORE_COLOR


def fit(text, size, width):
    """text, cut with "…" so it's at most width pixels wide."""
    if font(size).size(text)[0] <= width:
        return text
    while text and font(size).size(text + "…")[0] > width:
        text = text[:-1]
    return text + "…"


def shrink_to_fit(text, size, width, smallest):
    """(text, size): the biggest font size down to smallest at which text fits into width – cut with "…" if it
    doesn't even fit at smallest."""
    while size > smallest and font(size).size(text)[0] > width:
        size -= 1
    return fit(text, size, width), size


def dimmed(color, factor):
    return [round(channel * factor) for channel in color]


class CardPanel:
    def __init__(self, card_shop, left, top, width, show_message):
        """left, top, width: the area in the game menu's window. show_message(text, color): for results."""
        self.shop = card_shop
        self.left, self.top, self.width = left, top, width
        self.show_message = show_message

    # --- layout ---

    def offer_rects(self):
        width, height = OFFER_SIZE
        return [pygame.Rect(self.left + index * (width + OFFER_GAP), self.top, width, height)
                for index in range(len(self.shop.offers))]

    def reroll_rect(self):
        left = self.left + len(self.shop.offers) * (OFFER_SIZE[0] + OFFER_GAP)
        return pygame.Rect(left, self.top, self.left + self.width - left, OFFER_SIZE[1])

    def collection_top(self):
        return self.top + OFFER_SIZE[1] + COLLECTION_GAP

    def slot_rects(self):
        width, height = SLOT_SIZE
        top = self.collection_top() + 24
        return [pygame.Rect(self.left + (index % GRID_COLUMNS) * (width + SLOT_GAP),
                            top + (index // GRID_COLUMNS) * (height + SLOT_GAP), width, height)
                for index in range(self.shop.rules.max_owned)]

    def thing_at(self, position):
        """("offer", i), "reroll", ("owned", i) or None."""
        for index, rect in enumerate(self.offer_rects()):
            if rect.collidepoint(position):
                return ("offer", index)
        if self.reroll_rect().collidepoint(position):
            return "reroll"
        for index, rect in enumerate(self.slot_rects()[:len(self.shop.profile.cards)]):
            if rect.collidepoint(position):
                return ("owned", index)
        return None

    # --- input ---

    def click(self, thing):
        """A left click on thing."""
        if thing == "reroll":
            self.report(self.shop.reroll(), "New offers")
        elif thing and thing[0] == "offer":
            key = self.shop.offers[thing[1]]
            name = f"{CARDS[key].name} {CARDS[key].effect()}" if key else ""
            self.report(self.shop.buy(thing[1]), f"{name} added to your cards")
        elif thing and thing[0] == "owned":
            card = self.shop.profile.cards[thing[1]]
            self.report(self.shop.toggle(thing[1]), "Active" if not card["active"] else "Inactive")

    def menu_items(self, thing):
        """For a right click on thing: (title, [(label, action), …]) for the context menu – None if it has none."""
        if not (thing and thing[0] == "owned"):
            return None
        index = thing[1]
        card = CARDS[self.shop.profile.cards[index]["key"]]
        refund = self.shop.rules.sell_refund
        return (f"{card.name} {card.effect()}",
                [(f"Sell (+{refund} core{'' if refund == 1 else 's'})", lambda: self.sell(index))])

    def sell(self, index):
        card = CARDS[self.shop.profile.cards[index]["key"]]
        self.shop.sell(index)
        self.show_message(f"Sold {card.name} (+{self.shop.rules.sell_refund} cores)", SUCCESS)

    def report(self, problem, success):
        if problem:
            self.show_message(problem, TOO_EXPENSIVE)
        else:
            self.show_message(success, SUCCESS)

    def info(self, thing):
        """The line under the cards for what the mouse is on."""
        rules = self.shop.rules
        if thing == "reroll":
            return f"New offers for {rules.reroll_price} cores"
        if thing and thing[0] == "offer" and self.shop.offers[thing[1]]:
            card = CARDS[self.shop.offers[thing[1]]]
            return f"{card.name} {card.effect()}  ·  active cards apply at the start of every run"
        if thing and thing[0] == "owned":
            owned = self.shop.profile.cards[thing[1]]
            card = CARDS[owned["key"]]
            toggle = "deactivate" if owned["active"] else "activate"
            return f"{card.name} {card.effect()}  ·  left click: {toggle}  ·  right click: more (sell)"
        return None

    # --- drawing ---

    def draw(self, surface, hovered):
        for index, (rect, key) in enumerate(zip(self.offer_rects(), self.shop.offers)):
            self.draw_offer(surface, rect, key, hovered == ("offer", index))
        self.draw_reroll(surface, self.reroll_rect(), hovered == "reroll")

        rules, owned = self.shop.rules, self.shop.profile.cards
        title = draw_text(surface, f"YOUR CARDS  {len(owned)}/{rules.max_owned}", 22, settings.TEXT_MUTED,
                          topleft=(self.left, self.collection_top()))
        draw_text(surface, f"active {self.shop.active_count()}/{rules.max_active}", 22, CORE_COLOR,
                  midleft=(title.right + 18, title.centery))
        for index, rect in enumerate(self.slot_rects()):
            if index < len(owned):
                self.draw_owned(surface, rect, owned[index], hovered == ("owned", index))
            else:
                pygame.draw.rect(surface, EMPTY, rect, width=1, border_radius=6)

    def draw_offer(self, surface, rect, key, hovered):
        pygame.draw.rect(surface, HOVER_FILL if hovered and key else FILL, rect, border_radius=8)
        if key is None:
            pygame.draw.rect(surface, EMPTY, rect, width=1, border_radius=8)
            draw_text(surface, "sold out", 22, settings.TEXT, alpha=settings.HINT_ALPHA, center=rect.center)
            return
        card = CARDS[key]
        pygame.draw.rect(surface, card.color, rect, width=3 if hovered else 1, border_radius=8)
        band = pygame.Rect(rect.left, rect.top, rect.width, 22)
        pygame.draw.rect(surface, card.color, band, border_top_left_radius=8, border_top_right_radius=8)
        draw_text(surface, card.category.upper(), 18, settings.BACKGROUND, center=band.center)
        draw_text(surface, fit(card.name, 22, rect.width - 12), 22, settings.TEXT,
                  midtop=(rect.centerx, rect.top + 30))
        draw_text(surface, card.effect(), 34, card.color, midtop=(rect.centerx, rect.top + 52))
        price = self.shop.price()
        affordable = self.shop.profile.cores >= price and not self.shop.full()
        self.draw_cores(surface, price, (rect.centerx, rect.bottom - 16),
                        settings.TEXT if affordable else TOO_EXPENSIVE)

    def draw_reroll(self, surface, rect, hovered):
        if hovered:
            pygame.draw.rect(surface, HOVER_FILL, rect, border_radius=8)
        pygame.draw.rect(surface, settings.TEXT_MUTED, rect, width=2, border_radius=8)
        draw_text(surface, "Reroll", 26, settings.TEXT, center=(rect.centerx, rect.centery - 14))
        price = self.shop.rules.reroll_price
        color = settings.TEXT if self.shop.profile.cores >= price else TOO_EXPENSIVE
        self.draw_cores(surface, price, (rect.centerx, rect.centery + 18), color)

    def draw_owned(self, surface, rect, owned, hovered):
        card = CARDS[owned["key"]]
        active = owned["active"]
        fill = dimmed(card.color, 0.28) if active else (HOVER_FILL if hovered else FILL)
        pygame.draw.rect(surface, fill, rect, border_radius=6)
        border = card.color if active or hovered else dimmed(card.color, 0.55)
        pygame.draw.rect(surface, border, rect, width=3 if active else 1, border_radius=6)
        name, size = shrink_to_fit(card.name, 17, rect.width - 22, smallest=13)     # long names a bit smaller
        draw_text(surface, name, size, settings.TEXT, midleft=(rect.left + 6, rect.top + 11))
        draw_text(surface, card.effect(), 24, card.color if not active else settings.TEXT,
                  midbottom=(rect.centerx, rect.bottom - 5))
        if active:
            pygame.draw.circle(surface, CORE_COLOR, (rect.right - 9, rect.top + 10), 4)

    @staticmethod
    def draw_cores(surface, amount, center, color):
        """A core icon and a number, centred on center."""
        text = str(amount)
        width = 20 + font(26).size(text)[0]
        left = center[0] - width / 2
        draw_core(surface, (left + 7, center[1] - 1), 8)
        draw_text(surface, text, 26, color, midleft=(left + 20, center[1]))
