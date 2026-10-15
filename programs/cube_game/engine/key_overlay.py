"""
Key display like in esports streams: keycaps that light up while the game sees the key as held – and, if wanted, a
mouse whose buttons light up while they're held.

Shows what pygame actually receives – handy to spot keyboard ghosting (the keyboard not reporting some key
combinations). Toggled with toggle_key (F3 by default).
"""

import pygame

KEY_SIZE = 40               # pixels per keycap (a wide key is several of these, plus the gaps between them)
GAP = 6                     # pixels between keycaps
MOUSE_SIZE = (54, 86)       # width, height of the mouse
IDLE_FILL = (255, 255, 255, 30)
IDLE_BORDER = (255, 255, 255, 110)
IDLE_TEXT = (255, 255, 255, 160)
HELD_FILL = (255, 255, 255, 230)
HELD_TEXT = (0, 0, 0, 255)


class KeyOverlay:
    def __init__(self, layout, inset=12, visible=True, toggle_key=pygame.K_F3, mouse_buttons=()):
        """layout: list of (label, keys, column, row) or (label, keys, column, row, width) – keys: one pygame key or
        several (e.g. both shift keys), width: in keycaps. E.g. ("W", pygame.K_w, 1, 0).
        mouse_buttons: which mouse buttons to show on a mouse right of the keys (indexes into
        pygame.mouse.get_pressed(): 0 left, 2 right) – empty: no mouse.
        inset: gap to the bottom right corner of the window, in pixels (the window can change size)."""
        self.layout = [(label, keys if isinstance(keys, (tuple, list)) else (keys,), column, row, *rest)
                       for label, keys, column, row, *rest in layout]
        self.visible = visible
        self.toggle_key = toggle_key
        self.mouse_buttons = tuple(mouse_buttons)
        columns = max(column + (rest[0] if rest else 1) for _, _, column, _, *rest in self.layout)
        rows = max(row for _, _, _, row, *_ in self.layout) + 1
        keys_width = columns * KEY_SIZE + (columns - 1) * GAP
        height = rows * KEY_SIZE + (rows - 1) * GAP
        self.mouse_rect = None
        width = keys_width
        if self.mouse_buttons:
            height = max(height, MOUSE_SIZE[1])
            self.mouse_rect = pygame.Rect(keys_width + 2 * GAP, height - MOUSE_SIZE[1], *MOUSE_SIZE)
            width = self.mouse_rect.right
        self.surface = pygame.Surface((width, height), pygame.SRCALPHA)
        self.key_top = height - (rows * KEY_SIZE + (rows - 1) * GAP)      # keys sit at the bottom, like the mouse
        self.inset = inset
        pygame.font.init()
        self.font = pygame.font.Font(None, 26)
        self.small_font = pygame.font.Font(None, 20)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == self.toggle_key:
            self.visible = not self.visible

    def draw(self, surface):
        if not self.visible:
            return
        held = pygame.key.get_pressed()
        self.surface.fill((0, 0, 0, 0))
        for label, keys, column, row, *rest in self.layout:
            width = rest[0] if rest else 1
            cap = pygame.Rect(column * (KEY_SIZE + GAP), self.key_top + row * (KEY_SIZE + GAP),
                              width * KEY_SIZE + (width - 1) * GAP, KEY_SIZE)
            font = self.font if self.font.size(label)[0] <= cap.width - 8 else self.small_font
            self.draw_cap(cap, label, any(held[key] for key in keys), font)
        if self.mouse_rect is not None:
            self.draw_mouse()
        corner = surface.get_rect().inflate(-2 * self.inset, -2 * self.inset).bottomright
        surface.blit(self.surface, self.surface.get_rect(bottomright=corner))

    def draw_cap(self, cap, label, held, font, radius=6, **corners):
        if held:
            pygame.draw.rect(self.surface, HELD_FILL, cap, border_radius=radius, **corners)
            text_color = HELD_TEXT
        else:
            pygame.draw.rect(self.surface, IDLE_FILL, cap, border_radius=radius, **corners)
            pygame.draw.rect(self.surface, IDLE_BORDER, cap, width=2, border_radius=radius, **corners)
            text_color = IDLE_TEXT
        if label:
            text = font.render(label, True, text_color)
            self.surface.blit(text, text.get_rect(center=cap.center))

    def draw_mouse(self):
        """A mouse from above: two buttons on top (lit while held), the body below."""
        mouse = self.mouse_rect
        pressed = pygame.mouse.get_pressed()
        button_height = round(mouse.height * 0.42)
        half = (mouse.width - 2) // 2
        left = pygame.Rect(mouse.left, mouse.top, half, button_height)
        right = pygame.Rect(mouse.right - half, mouse.top, half, button_height)
        body = pygame.Rect(mouse.left, mouse.top + button_height + 2, mouse.width, mouse.height - button_height - 2)
        radius = mouse.width // 2
        self.draw_cap(left, "", 0 in self.mouse_buttons and pressed[0], self.small_font, radius=0,
                      border_top_left_radius=radius)
        self.draw_cap(right, "", 2 in self.mouse_buttons and pressed[2], self.small_font, radius=0,
                      border_top_right_radius=radius)
        self.draw_cap(body, "", False, self.small_font, radius=0, border_bottom_left_radius=radius,
                      border_bottom_right_radius=radius)
