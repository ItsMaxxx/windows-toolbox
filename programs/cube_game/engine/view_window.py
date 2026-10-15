"""
An extra window next to the game's main window (Engine.open_view): borderless, without a taskbar button, and passive –
it never takes the focus (the game would pause), not even when it's clicked: it says "don't activate me" to the
click (WM_MOUSEACTIVATE → MA_NOACTIVATE, in its own window procedure in front of SDL's), on top of being a
WS_EX_NOACTIVATE window. Clicks on it don't fall through to the
desktop behind it: the mouse may be in it (it can be part of the field), and the game reads the mouse buttons no
matter which of its windows the mouse is over. It shows its picture the same way the main window does
(layered_window.py), just without touching the mouse lock.

It's owned by the main window (an "owned window" in Windows' terms): Windows always keeps it above the main window,
also when the game gets the focus back – where the two overlap, the extra window is on top.

Windows only: everything goes through ctypes (user32), no extra packages.
"""

import ctypes
from ctypes import wintypes

import pygame

from engine.layered_window import LayeredWindow

user32 = ctypes.windll.user32

GWL_EXSTYLE = -20
GWLP_HWNDPARENT = -8                # for a top-level window: its owner
WS_EX_LAYERED = 0x00080000
WS_EX_TOOLWINDOW = 0x00000080       # no taskbar button, not in Alt+Tab
WS_EX_NOACTIVATE = 0x08000000       # never becomes the active window
SW_SHOWNA = 8                       # show without activating
SW_HIDE = 0
GWLP_WNDPROC = -4
WM_MOUSEACTIVATE = 0x0021
MA_NOACTIVATE = 3
WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
OFF_SCREEN = (-32000, -32000)       # where it's created – it's moved into place with its first picture

user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.SetWindowLongPtrW.restype = ctypes.c_ssize_t
user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.CallWindowProcW.restype = ctypes.c_ssize_t
user32.CallWindowProcW.argtypes = [ctypes.c_void_p, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]


class ViewWindow:
    def __init__(self, owner=None):
        """owner: the main window's handle – this one stays above it. Raises OSError / pygame.error if it can't be
        made."""
        self.window = pygame.Window("view", (1, 1), OFF_SCREEN, hidden=True, borderless=True, utility=True)
        self.hwnd = self.window.handle
        if owner:
            user32.SetWindowLongPtrW(self.hwnd, GWLP_HWNDPARENT, owner)
        style = user32.GetWindowLongPtrW(self.hwnd, GWL_EXSTYLE)
        user32.SetWindowLongPtrW(self.hwnd, GWL_EXSTYLE,
                                 style | WS_EX_LAYERED | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE)
        # its own window procedure in front of SDL's: refuses to be activated by a click, passes everything else on
        self.sdl_procedure = user32.GetWindowLongPtrW(self.hwnd, GWLP_WNDPROC)
        self.procedure = WNDPROC(self.handle_message)       # kept here, so it isn't garbage collected while in use
        user32.SetWindowLongPtrW(self.hwnd, GWLP_WNDPROC, ctypes.cast(self.procedure, ctypes.c_void_p).value)
        try:
            self.layered = LayeredWindow(self.window, manage_mouse=False)
        except OSError:
            self.close_window()
            raise
        self.rect = None                # where it is on the screen = the part of the world it shows (set by the scene)
        self.hidden = False             # set by the scene: True – not on the screen for now (e.g. while paused)
        self.shown = False              # whether it's on the screen right now

    def canvas(self):
        """Where to draw the next picture (the size of rect)."""
        return self.layered.canvas(self.rect.size)

    def show(self):
        """Puts what was drawn on the canvas on the screen at rect. The first time, the window appears – without
        becoming active."""
        self.layered.show(self.rect.size, self.rect.topleft)
        if not self.shown:
            self.shown = True
            user32.ShowWindow(self.hwnd, SW_SHOWNA)

    def hide(self):
        """Takes it off the screen until the next show()."""
        if self.shown:
            self.shown = False
            user32.ShowWindow(self.hwnd, SW_HIDE)

    def handle_message(self, hwnd, message, wparam, lparam):
        if message == WM_MOUSEACTIVATE:
            return MA_NOACTIVATE                # the click still arrives, the window just doesn't become active
        return user32.CallWindowProcW(self.sdl_procedure, hwnd, message, wparam, lparam)

    def close(self):
        self.layered.close()
        self.close_window()

    def close_window(self):
        user32.SetWindowLongPtrW(self.hwnd, GWLP_WNDPROC, self.sdl_procedure)     # SDL's again before it goes
        self.window.destroy()
