"""
Information about the Windows desktop: the usable area (without the taskbar) of the main monitor, or of all monitors.

With several monitors the game world can be all of them together (Desktop). They don't have to form a rectangle –
e.g. two monitors of different height, or a taskbar on only one of them – so covers() checks whether a rectangle lies
completely on monitors (nothing of it in the gaps, where it would be invisible).

Needs DPI awareness (see cube_game.py), otherwise Windows reports scaled values.
"""

import ctypes
from ctypes import wintypes

import pygame

SPI_GETWORKAREA = 0x0030
EPSILON = 1e-6              # leftovers thinner than this (rounding) count as covered


class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT), ("rcWork", wintypes.RECT),
                ("dwFlags", wintypes.DWORD)]


MONITOR_ENUM_PROC = ctypes.WINFUNCTYPE(ctypes.c_int, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(wintypes.RECT),
                                       wintypes.LPARAM)


def work_area():
    """The usable area of the main monitor (without the taskbar) in screen pixels, as a pygame.Rect."""
    rect = wintypes.RECT()
    if ctypes.windll.user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rect), 0):
        return pygame.Rect(rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top)
    pygame.display.init()
    return pygame.Rect((0, 0), pygame.display.get_desktop_sizes()[0])


def work_areas():
    """The usable area of every monitor (main monitor first). Falls back to just the main monitor."""
    areas = []

    def found(monitor, dc, rect, data):
        info = MONITORINFO()
        info.cbSize = ctypes.sizeof(info)
        if ctypes.windll.user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
            work = info.rcWork
            areas.append(pygame.Rect(work.left, work.top, work.right - work.left, work.bottom - work.top))
        return 1                                    # go on with the next monitor

    try:
        ctypes.windll.user32.EnumDisplayMonitors(None, None, MONITOR_ENUM_PROC(found), 0)
    except (AttributeError, OSError):
        areas = []
    main = work_area()
    return [main] + [area for area in areas if area != main]


class Desktop:
    def __init__(self, areas):
        """areas: the monitors' usable areas – the first one is the main monitor."""
        self.areas = [pygame.Rect(area) for area in areas]
        self.main = self.areas[0]
        self.bounds = self.main.unionall(self.areas[1:])    # the smallest rectangle around all of them

    @classmethod
    def current(cls, all_monitors=True):
        return cls(work_areas() if all_monitors else [work_area()])

    def contains(self, point):
        return any(area.collidepoint(point) for area in self.areas)

    def area_at(self, point):
        """The monitor area point is on – or the nearest one."""
        return min(self.areas, key=lambda area: pygame.Vector2(clamp_point(point, area)).distance_squared_to(point))

    def clamp_point(self, point):
        """The point itself if it's on a monitor, else the nearest point that is."""
        return pygame.Vector2(clamp_point(point, self.area_at(point)))

    def covers(self, rect):
        """True if rect lies completely on monitors. Works by cutting every monitor out of rect: whatever is left at
        the end is in a gap."""
        pieces = [(rect.left, rect.top, rect.right, rect.bottom)]
        for area in self.areas:
            rest = []
            for left, top, right, bottom in pieces:
                if right <= area.left or left >= area.right or bottom <= area.top or top >= area.bottom:
                    rest.append((left, top, right, bottom))         # doesn't touch this monitor
                    continue
                if left < area.left:
                    rest.append((left, top, area.left, bottom))
                if right > area.right:
                    rest.append((area.right, top, right, bottom))
                inner_left, inner_right = max(left, area.left), min(right, area.right)
                if top < area.top:
                    rest.append((inner_left, top, inner_right, area.top))
                if bottom > area.bottom:
                    rest.append((inner_left, area.bottom, inner_right, bottom))
            pieces = [piece for piece in rest if piece[2] - piece[0] > EPSILON and piece[3] - piece[1] > EPSILON]
            if not pieces:
                return True
        return False


def clamp_point(point, area):
    return (min(max(point[0], area.left), area.right - 1), min(max(point[1], area.top), area.bottom - 1))
