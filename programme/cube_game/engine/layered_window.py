"""
Shows the game's pictures through Windows' "layered window" function UpdateLayeredWindow: position, size and picture
of the window change in ONE step. With SDL's own functions that takes three (move, resize, show the new picture),
and if Windows redraws the screen in between, the window visibly jumps – e.g. first to the left, then growing back to
the right when a shot pushes the left wall.

SDL keeps handling keyboard and mouse; it just never shows anything itself (no flip()). Two things SDL doesn't
notice when the window is moved this way, so they're done here, too:
  - SDL's idea of the window size is kept up to date (the mouse coordinates rely on it),
  - locking the mouse into the window (ClipCursor) – SDL would keep it locked to the old spot.

Windows only: everything goes through ctypes (user32/gdi32), no extra packages.
"""

import ctypes
from ctypes import wintypes

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
gdi32.CreateCompatibleDC.restype = wintypes.HDC
gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
gdi32.DeleteDC.argtypes = [wintypes.HDC]
gdi32.CreateDIBSection.restype = wintypes.HBITMAP
gdi32.CreateDIBSection.argtypes = [wintypes.HDC, ctypes.c_void_p, ctypes.c_uint, ctypes.POINTER(ctypes.c_void_p),
                                   wintypes.HANDLE, wintypes.DWORD]
gdi32.SelectObject.restype = wintypes.HGDIOBJ
gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]


class LayeredWindow:
    def __init__(self, window):
        """window: the pygame.Window. Raises OSError if Windows doesn't play along – the engine then falls back to
        SDL's own (flickering) way."""
        self.window = window
        self.hwnd = window.handle
        style = user32.GetWindowLongPtrW(self.hwnd, GWL_EXSTYLE)
        user32.SetWindowLongPtrW(self.hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED)
        self.screen_dc = user32.GetDC(None)
        self.memory_dc = gdi32.CreateCompatibleDC(self.screen_dc)
        if not self.screen_dc or not self.memory_dc:
            raise OSError("no device context")
        self.bitmap = None
        self.bits = ctypes.c_void_p()           # where the bitmap's pixels are in memory
        self.size = None
        self.mouse_locked = False
        self.rect = None                        # where the window is now (screen pixels)

    def show(self, surface, topleft):
        """Puts surface on the screen as the window's content, with the window's top left corner at topleft.
        surface must be 32 bits per pixel (see Engine.present)."""
        size = surface.get_size()
        if size != self.size:
            self._make_bitmap(size)
        width, height = size
        if surface.get_pitch() == width * 4:
            ctypes.memmove(self.bits, surface._pixels_address, width * height * 4)
        else:                                   # rows with padding: copy one by one
            pitch = surface.get_pitch()
            for row in range(height):
                ctypes.memmove(self.bits.value + row * width * 4, surface._pixels_address + row * pitch, width * 4)
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
        if self.mouse_locked and self.rect:
            user32.ClipCursor(ctypes.byref(wintypes.RECT(*self.rect)))
        else:
            user32.ClipCursor(None)

    def _make_bitmap(self, size):
        width, height = size
        header = BITMAPINFOHEADER(ctypes.sizeof(BITMAPINFOHEADER), width, -height, 1, 32, 0, 0, 0, 0, 0, 0)  # top-down
        bitmap = gdi32.CreateDIBSection(self.memory_dc, ctypes.byref(header), DIB_RGB_COLORS, ctypes.byref(self.bits),
                                        None, 0)
        if not bitmap:
            raise OSError("CreateDIBSection failed")
        gdi32.SelectObject(self.memory_dc, bitmap)
        if self.bitmap:
            gdi32.DeleteObject(self.bitmap)
        self.bitmap = bitmap
        self.size = size

    def close(self):
        user32.ClipCursor(None)
        if self.bitmap:
            gdi32.DeleteObject(self.bitmap)
        gdi32.DeleteDC(self.memory_dc)
        user32.ReleaseDC(None, self.screen_dc)
