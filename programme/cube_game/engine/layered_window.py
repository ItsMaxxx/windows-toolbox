"""
Shows the game's pictures through Windows' "layered window" function UpdateLayeredWindow: position, size and picture
of the window change in ONE step. With SDL's own functions that takes three (move, resize, show the new picture),
and if Windows redraws the screen in between, the window visibly jumps – e.g. first to the left, then growing back to
the right when a shot pushes the left wall.

The game draws straight into the bitmap that's shown (canvas()): no copying, and the memory is only made anew when the
window gets bigger than ever before – important when the window spans several monitors.

SDL keeps handling keyboard and mouse; it just never shows anything itself (no flip()). Two things SDL doesn't
notice when the window is moved this way, so they're done here, too:
  - SDL's idea of the window size is kept up to date (the mouse coordinates rely on it),
  - locking the mouse into the window (ClipCursor) – SDL would keep it locked to the old spot. The lock can also be a
    set of rectangles (mouse_area, e.g. the arena and the extra windows connected to it): Windows can only lock the
    cursor into one rectangle, so it's locked into the box around them, and put back onto the nearest rectangle
    whenever it gets into a gap between them.

Windows only: everything goes through ctypes (user32/gdi32), no extra packages.
"""

import ctypes
from ctypes import wintypes

import pygame

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
ULW_OPAQUE = 0x00000004
DIB_RGB_COLORS = 0


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wintypes.DWORD), ("biWidth", ctypes.c_long), ("biHeight", ctypes.c_long),
                ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", ctypes.c_long), ("biYPelsPerMeter", ctypes.c_long),
                ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD)]


class SIZE(ctypes.Structure):
    _fields_ = [("cx", ctypes.c_long), ("cy", ctypes.c_long)]


user32.GetDC.restype = wintypes.HDC
user32.GetDC.argtypes = [wintypes.HWND]
user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.SetWindowLongPtrW.restype = ctypes.c_ssize_t
user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
user32.UpdateLayeredWindow.argtypes = [wintypes.HWND, wintypes.HDC, ctypes.POINTER(wintypes.POINT), ctypes.POINTER(SIZE),
                                       wintypes.HDC, ctypes.POINTER(wintypes.POINT), wintypes.DWORD, ctypes.c_void_p,
                                       wintypes.DWORD]
user32.ClipCursor.argtypes = [ctypes.POINTER(wintypes.RECT)]
user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
gdi32.CreateCompatibleDC.restype = wintypes.HDC
gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
gdi32.DeleteDC.argtypes = [wintypes.HDC]
gdi32.CreateDIBSection.restype = wintypes.HBITMAP
gdi32.CreateDIBSection.argtypes = [wintypes.HDC, ctypes.c_void_p, ctypes.c_uint, ctypes.POINTER(ctypes.c_void_p),
                                   wintypes.HANDLE, wintypes.DWORD]
gdi32.SelectObject.restype = wintypes.HGDIOBJ
gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]


def cursor_position():
    """Where the mouse cursor is on the screen (screen pixels) – no matter over which window."""
    point = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(point))
    return point.x, point.y


class LayeredWindow:
    def __init__(self, window, manage_mouse=True):
        """window: the pygame.Window. Raises OSError if Windows doesn't play along – the engine then falls back to
        SDL's own (flickering) way. manage_mouse: False for extra windows (view_window.py) – only the game's main
        window locks the mouse, and an extra one must never let it go."""
        self.window = window
        self.manage_mouse = manage_mouse
        self.hwnd = window.handle
        style = user32.GetWindowLongPtrW(self.hwnd, GWL_EXSTYLE)
        user32.SetWindowLongPtrW(self.hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED)
        self.screen_dc = user32.GetDC(None)
        self.memory_dc = gdi32.CreateCompatibleDC(self.screen_dc)
        if not self.screen_dc or not self.memory_dc:
            raise OSError("no device context")
        self.bitmap = None
        self.bits = ctypes.c_void_p()           # where the bitmap's pixels are in memory
        self.pixels = None                      # the same memory for Python …
        self.surface = None                     # … and as a pygame surface the size of the whole bitmap
        self.size = (0, 0)                      # the bitmap's size: as big as the biggest window so far
        self.mouse_locked = False
        self.mouse_area = None                  # rectangles the locked mouse may move in – None: just the window
        self.rect = None                        # where the window is now (screen pixels)

    def canvas(self, size):
        """Where to draw the next picture: a surface of size that lies directly in the bitmap show() puts on the
        screen. Only valid until the next canvas() call."""
        width, height = size
        if width > self.size[0] or height > self.size[1]:
            self._make_bitmap((max(width, self.size[0]), max(height, self.size[1])))
        return self.surface.subsurface((0, 0, width, height))

    def show(self, size, topleft):
        """Puts what was drawn on the canvas (size) on the screen as the window's content, with the window's top left
        corner at topleft."""
        width, height = size
        ok = user32.UpdateLayeredWindow(self.hwnd, self.screen_dc, ctypes.byref(wintypes.POINT(*topleft)),
                                        ctypes.byref(SIZE(width, height)), self.memory_dc,
                                        ctypes.byref(wintypes.POINT(0, 0)), 0, None, ULW_OPAQUE)
        if not ok:
            raise OSError(ctypes.GetLastError(), "UpdateLayeredWindow failed")
        if tuple(self.window.size) != size:
            self.window.size = size             # only tells SDL – the window already has this size
        self.rect = (topleft[0], topleft[1], topleft[0] + width, topleft[1] + height)
        self._apply_mouse_lock()

    def lock_mouse(self, locked):
        """Keeps the cursor inside the window (True) or lets it go (False)."""
        self.mouse_locked = locked
        self._apply_mouse_lock()

    def _apply_mouse_lock(self):
        if not self.manage_mouse:
            return
        if not (self.mouse_locked and self.rect):
            user32.ClipCursor(None)
            return
        left, top, right, bottom = self.rect
        area = self.mouse_area or [pygame.Rect(left, top, right - left, bottom - top)]
        box = area[0].unionall(area[1:])
        user32.ClipCursor(ctypes.byref(wintypes.RECT(box.left, box.top, box.right, box.bottom)))
        x, y = cursor_position()
        if len(area) > 1 and not any(rect.collidepoint(x, y) for rect in area):
            # in a gap between the rectangles: onto the nearest one
            nearest = [(min(max(x, rect.left), rect.right - 1), min(max(y, rect.top), rect.bottom - 1))
                       for rect in area]
            user32.SetCursorPos(*min(nearest, key=lambda point: (point[0] - x) ** 2 + (point[1] - y) ** 2))

    def _make_bitmap(self, size):
        width, height = size
        header = BITMAPINFOHEADER(ctypes.sizeof(BITMAPINFOHEADER), width, -height, 1, 32, 0, 0, 0, 0, 0, 0)  # top-down
        bitmap = gdi32.CreateDIBSection(self.memory_dc, ctypes.byref(header), DIB_RGB_COLORS, ctypes.byref(self.bits),
                                        None, 0)
        if not bitmap:
            raise OSError("CreateDIBSection failed")
        gdi32.SelectObject(self.memory_dc, bitmap)
        self.surface = None                     # the old surface pointed into the old bitmap's memory
        if self.bitmap:
            gdi32.DeleteObject(self.bitmap)
        self.bitmap = bitmap
        self.size = size
        # the pixels in memory are blue, green, red, (unused) – row after row, top row first
        self.pixels = (ctypes.c_char * (width * height * 4)).from_address(self.bits.value)
        self.surface = pygame.image.frombuffer(self.pixels, size, "BGRA")

    def close(self):
        if self.manage_mouse:
            user32.ClipCursor(None)
        if self.bitmap:
            gdi32.DeleteObject(self.bitmap)
        gdi32.DeleteDC(self.memory_dc)
        user32.ReleaseDC(None, self.screen_dc)
