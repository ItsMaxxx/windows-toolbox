"""
Key display like in esports streams: keycaps that light up while the game sees the key as held.

Shows what pygame actually receives – handy to spot keyboard ghosting (the keyboard not reporting some key
combinations). Toggled with toggle_key (F3 by default).
"""

import pygame

KEY_SIZE = 40               # pixels per keycap
GAP = 6                     # pixels between keycaps
IDLE_FILL = (255, 255, 255, 30)
IDLE_BORDER = (255, 255, 255, 110)
IDLE_TEXT = (255, 255, 255, 160)
HELD_FILL = (255, 255, 255, 230)
HELD_TEXT = (0, 0, 0, 255)


class KeyOverlay:
    def __init__(self, layout, inset=12, visible=True, toggle_key=pygame.K_F3):
        """layout: list of (label, pygame key, column, row), e.g. ("W", pygame.K_w, 1, 0).
        inset: gap to the bottom right corner of the window, in pixels (the window can change size)."""
        self.layout = layout
        self.visible = visible
        self.toggle_key = toggle_key
        columns = max(column for _, _, column, _ in layout) + 1
        rows = max(row for _, _, _, row in layout) + 1
        self.surface = pygame.Surface((columns * KEY_SIZE + (columns - 1) * GAP,
                                       rows * KEY_SIZE + (rows - 1) * GAP), pygame.SRCALPHA)
        self.inset = inset
        pygame.font.init()
        self.font = pygame.font.Font(None, 26)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == self.toggle_key:
            self.visible = not self.visible

    def draw(self, surface):
        if not self.visible:
            return
        held = pygame.key.get_pressed()
        self.surface.fill((0, 0, 0, 0))
        for label, key, column, row in self.layout:
            cap = pygame.Rect(column * (KEY_SIZE + GAP), row * (KEY_SIZE + GAP), KEY_SIZE, KEY_SIZE)
            if held[key]:
                pygame.draw.rect(self.surface, HELD_FILL, cap, border_radius=6)
                text_color = HELD_TEXT
            else:
                pygame.draw.rect(self.surface, IDLE_FILL, cap, border_radius=6)
                pygame.draw.rect(self.surface, IDLE_BORDER, cap, width=2, border_radius=6)
                text_color = IDLE_TEXT
            text = self.font.render(label, True, text_color)
            self.surface.blit(text, text.get_rect(center=cap.center))
        corner = surface.get_rect().inflate(-2 * self.inset, -2 * self.inset).bottomright
        surface.blit(self.surface, self.surface.get_rect(bottomright=corner))
