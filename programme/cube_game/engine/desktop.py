"""
Information about the Windows desktop.
"""

import ctypes
from ctypes import wintypes

import pygame

SPI_GETWORKAREA = 0x0030


def work_area():
    """The usable area of the main monitor (without the taskbar) in screen pixels, as a pygame.Rect.
    Needs DPI awareness (see cube_game.py), otherwise Windows reports scaled values."""
    rect = wintypes.RECT()
    if ctypes.windll.user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rect), 0):
        return pygame.Rect(rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top)
    pygame.display.init()
    return pygame.Rect((0, 0), pygame.display.get_desktop_sizes()[0])
