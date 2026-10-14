"""
All numbers and colours of the game in one place, so they can be tweaked quickly – except what depends on the
difficulty (arena size and shrinking, cores, enemies): that's in data/difficulties/*.json.
Distances in screen pixels, speeds in pixels per second.
"""

import pygame

TITLE = "Cube Game"
MENU_WINDOW_SIZE = (640, 460)   # window of the main menu
GAME_MENU_WINDOW_SIZE = (1300, 900)      # window of the game menu (ship, difficulty, skill tree) between runs

# The window is the arena: it keeps shrinking, shots against its edges push them back out. Once it's as narrow (or as
# low) as the ship, the ship is crushed: game over. Start size and shrinking speed: per difficulty.
PUSH_SPEED = 600                # a hit pushes its edge out smoothly at this speed, instead of jumping

# The ship itself – its weapons and energy have their own values (data/weapons.json)
SHIP_SIZE = 30                  # hitbox (square) and size of the ship
SHIP_SPEED = 280

# Getting hit: the window is your health – an enemy's damage is in pixels: the edges move in that far at once (on
# average – width and height each get 2 × damage smaller), then the ship can't be hit for a moment (it blinks) …
# … but not evenly: the edges far from the ship move in more, the near ones less. 0 = every edge the same, 1 = with the
# ship right at the left edge, the left edge doesn't move at all and the right one twice as far (the total stays)
HIT_SIDE_BIAS = 1.0
MAX_ARMOR = 90                  # percent: the arena's armor never takes more than this off a push
INVULNERABLE_TIME = 1.0
ALL_MONITORS = False             # with several monitors the arena can spread over all of them (False: main monitor only)
OFFSCREEN_MARKERS = True        # dots at the window's edge showing where enemies outside the window are

# Keys for the ability slots (slot 1: dash, slot 2: rocket) and how they're shown on screen
ABILITY_KEYS = ((pygame.K_LSHIFT, pygame.K_RSHIFT), (pygame.K_SPACE,))
ABILITY_KEY_NAMES = ("SHIFT", "SPACE")
BUILD_KEYS = (pygame.K_b,)      # throws a watchtower (once unlocked in the skill tree)
BUILD_KEY_NAME = "B"

# key display in the bottom right corner – shown at the start or not: a setting on the toolbox's Cube Game page
# (profile.SETTINGS); F3 shows/hides it while playing
KEY_OVERLAY_INSET = 12          # gap between the key display and the window's corner
HINT_ALPHA = 70                 # how visible the hints top left ("ESC to open menu", …) are (0 = invisible, 255 = solid)

BACKGROUND = (0, 0, 0)          # inside the arena
BORDER = (255, 255, 255)        # outline of the arena, so you can see the walls
BORDER_WIDTH = 2
TEXT = (255, 255, 255)
TEXT_MUTED = (150, 150, 160)
SHIP_COLOR = (40, 110, 255)
