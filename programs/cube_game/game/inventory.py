"""
The inventory (Tab): a small window in the middle. Left: the ship and its own stats. Right: its 2 weapon slots and
2 ability slots with what's in them – everything is read from the ship, so new weapons and upgrades show up by
themselves. The game is paused while it's open, and the window shows only the inventory (SIZE is the window size
then).
"""

import pygame

from engine.ui import draw_panel, draw_text
from game import settings
from game.ship_shape import draw_ship

SIZE = (680, 560)
PREVIEW_SIZE = 190                  # square on the left with the ship in it
SHOWCASE_AIM = pygame.Vector2(1, -1).normalize()        # ship pointing up and to the right
SLOT_GAP = 14
SLOT_HEIGHT = 200                   # weapon slots …
ABILITY_SLOT_HEIGHT = 170           # … and ability slots
WEAPON_KEYS = ("LMB", "RMB")        # which mouse button fires which weapon slot
SLOT_BORDER = (70, 70, 80)
LINE = (50, 50, 58)


class Inventory:
    def draw(self, surface, ship):
        panel = surface.get_rect()
        draw_panel(surface, panel, radius=0)
        draw_text(surface, "INVENTORY", 36, settings.TEXT, topleft=(panel.left + 24, panel.top + 20))

        # left: the ship and its own stats
        preview = pygame.Rect(panel.left + 24, panel.top + 64, PREVIEW_SIZE, PREVIEW_SIZE)
        pygame.draw.rect(surface, settings.BACKGROUND, preview, border_radius=6)
        pygame.draw.rect(surface, settings.TEXT_MUTED, preview, width=1, border_radius=6)
        draw_ship(surface, preview.center, SHOWCASE_AIM, PREVIEW_SIZE * 0.55, ship.color)
        self.draw_rows(surface, [("Move speed", f"{ship.speed:g} px/s"),
                                 ("Energy", f"{ship.energy:.0f}/{ship.max_energy:g}"),
                                 ("Energy regen", f"{ship.energy_regen:g}/s"),
                                 ("Armor", f"{ship.armor:g} px"),
                                 ("Recovery", f"{ship.invulnerable_time:g} s"),
                                 ("Magnet", f"{ship.magnet_radius:g} px")],
                       preview.left, preview.right, preview.bottom + 16)

        # right: 2 weapon slots, 2 ability slots
        left = preview.right + 28
        width = (panel.right - 24 - left - SLOT_GAP) // 2
        y = preview.top
        draw_text(surface, "WEAPONS", 22, settings.TEXT_MUTED, topleft=(left, y))
        for index, weapon in enumerate(ship.weapons):
            box = pygame.Rect(left + index * (width + SLOT_GAP), y + 22, width, SLOT_HEIGHT)
            self.draw_slot(surface, box, weapon, WEAPON_KEYS[index])
        y += 22 + SLOT_HEIGHT + 16
        draw_text(surface, "ABILITIES", 22, settings.TEXT_MUTED, topleft=(left, y))
        for index, ability in enumerate(ship.abilities):
            box = pygame.Rect(left + index * (width + SLOT_GAP), y + 22, width, ABILITY_SLOT_HEIGHT)
            self.draw_slot(surface, box, ability, settings.ABILITY_KEY_NAMES[index])

        draw_text(surface, "TAB or ESC to close", 22, settings.TEXT, alpha=settings.HINT_ALPHA * 2,
                  bottomright=(panel.right - 20, panel.bottom - 14))

    def draw_slot(self, surface, box, item, key=""):
        """One slot: a frame, the name of what's in it and its values – or "empty"."""
        pygame.draw.rect(surface, SLOT_BORDER, box, width=1, border_radius=6)
        if key:
            draw_text(surface, key, 18, settings.TEXT, alpha=settings.HINT_ALPHA * 2,
                      topright=(box.right - 10, box.top + 10))
        if item is None:
            draw_text(surface, "empty", 24, settings.TEXT, alpha=settings.HINT_ALPHA, center=box.center)
            return
        draw_text(surface, item.name, 26, settings.TEXT, topleft=(box.left + 12, box.top + 10))
        self.draw_rows(surface, item.stat_lines(), box.left + 12, box.right - 12, box.top + 40, size=20, step=25)

    def draw_rows(self, surface, rows, left, right, top, size=24, step=30):
        """(name, value) rows: name faded on the left, value on the right, a thin line below each."""
        for name, value in rows:
            draw_text(surface, name, size, settings.TEXT_MUTED, topleft=(left, top))
            draw_text(surface, value, size, settings.TEXT, topright=(right, top))
            pygame.draw.line(surface, LINE, (left, top + size - 2), (right, top + size - 2))
            top += step
