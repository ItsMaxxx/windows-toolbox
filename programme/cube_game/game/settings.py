"""
All numbers and colours of the game in one place, so they can be tweaked quickly.
Distances in screen pixels, speeds in pixels per second.
"""

import pygame

TITLE = "Cube Game"
MENU_WINDOW_SIZE = (640, 460)   # window of the main menu

# The window is the arena: it keeps shrinking, shots against its edges push them back out
WINDOW_START_SIZE = (800, 560)
WINDOW_MIN_SIZE = (160, 160)    # smaller than this it doesn't shrink (later: game over)
SHRINK_SPEED = 20               # each edge moves inwards this fast
PUSH_SPEED = 600                # a hit pushes its edge out smoothly at this speed, instead of jumping

# The ship itself – its weapons have their own values (game/basic_gun.py, …)
SHIP_SIZE = 30                  # hitbox (square) and size of the ship
SHIP_SPEED = 320

# Getting hit: the window is your health – every point of damage squeezes each edge in by HIT_SHRINK at once,
# then the ship can't be hit for a moment (it blinks)
HIT_SHRINK = 25
INVULNERABLE_TIME = 1.0
OFFSCREEN_MARKERS = True        # dots at the window's edge showing where enemies outside the window are

# Keys for the ability slots (slot 1: dash, slot 2: rocket) and how they're shown on screen
ABILITY_KEYS = ((pygame.K_LSHIFT, pygame.K_RSHIFT), (pygame.K_SPACE,))
ABILITY_KEY_NAMES = ("SHIFT", "SPACE")

KEY_OVERLAY_VISIBLE = True      # key display in the bottom right corner; F3 shows/hides it while playing
KEY_OVERLAY_INSET = 12          # gap between the key display and the window's corner
HINT_ALPHA = 70                 # how visible the hints top left ("ESC to open menu", …) are (0 = invisible, 255 = solid)

BACKGROUND = (0, 0, 0)          # inside the arena
BORDER = (255, 255, 255)        # outline of the arena, so you can see the walls
BORDER_WIDTH = 2
TEXT = (255, 255, 255)
TEXT_MUTED = (150, 150, 160)
SHIP_COLOR = (40, 110, 255)
