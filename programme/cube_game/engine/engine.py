"""
The engine: opens the window and runs the game loop with a fixed timestep.

Game logic runs at exactly TICK_RATE ticks per second, no matter how fast the PC draws. Each frame, the time that has
passed is added to an accumulator; for every full tick in it, the scene gets one update(). That way movement is equally
fast on every PC ("Fix Your Timestep", see README.md).

The window is borderless and can be moved and resized by the game (move_window). Positions in the game world are
screen pixels; the window is just the part of the screen you can see – like a camera.

Moving without flicker: each frame, the scene first draws into a picture that already has the window's new size –
straight into the memory LayeredWindow shows from, so nothing is copied (the window can be as wide as several
monitors). Then LayeredWindow puts position, size and picture on the screen in one step (see layered_window.py).
Before that, the engine waits for DwmFlush(): Windows' compositor has just refreshed the screen – that syncs the
frames to the monitor. If the layered window isn't available, SDL moves, resizes and shows the picture one after the
other right after DwmFlush(); that still flickers now and then (measured: 4 % of the frames in which the window moves, instead
of 56 % without the wait).

Extra windows (open_view): small passive windows next to the main one that show another part of the world – e.g. a
watchtower's view. They lie on top of the main window but never take the focus or the mouse (view_window.py); the
scene draws them in draw_view() and can hide them for a while (view.hidden). They all close when the scene changes.
Their events are ignored, so they can't e.g. pause the game – and if the main window loses the focus to one of them
anyway (a click on it), it takes the focus right back and the scene never hears of it (internal_focus_loss).
"""

import ctypes
from ctypes import wintypes

import pygame

from engine.layered_window import LayeredWindow, cursor_position
from engine.view_window import ViewWindow

TICK_RATE = 60                  # logic updates per second
MAX_FRAME_TIME = 0.25           # seconds; after a freeze (e.g. dragging the window) don't try to catch up endlessly
MAX_FPS = 144                   # with vsync: don't draw more often than this, even on faster monitors


class Engine:
    def __init__(self, title, rect, tick_rate=TICK_RATE):
        """rect: position and size of the window on the screen (pygame.Rect)."""
        pygame.init()
        self.window = pygame.Window(title, rect.size, rect.topleft, borderless=True)
        self.window.focus()
        self.clock = pygame.time.Clock()
        self.tick_rate = tick_rate
        self.tick_time = 1 / tick_rate
        self.scene = None
        self.running = False
        self.target_rect = pygame.Rect(rect)    # where the window goes at the next present()
        self.shown_topleft = rect.topleft       # where the window is on the screen right now
        self.buffer = None                      # the next picture, drawn before the window moves
        self.mouse_locked = False
        try:
            self.dwm_flush = ctypes.windll.dwmapi.DwmFlush
        except (AttributeError, OSError):
            self.dwm_flush = None               # no compositor: no vsync, the clock limits the frame rate
        try:
            self.layered = LayeredWindow(self.window)
        except OSError:
            self.layered = None
        self.views = []                         # the open extra windows (open_view)

    @property
    def window_rect(self):
        """Where the window is on the screen – or will be after this frame, if the scene has moved it."""
        return pygame.Rect(self.target_rect)

    def move_window(self, rect):
        """Moves/resizes the window to rect (screen pixels). Happens when the next picture is shown."""
        self.target_rect = pygame.Rect(rect)

    def grab_mouse(self, grab):
        """True: keep the cursor inside the window, so a click can't land on the desktop behind it."""
        self.mouse_locked = grab
        if self.layered:
            self.layered.lock_mouse(grab and self.window.focused)
        else:
            self.window.grab_mouse = grab

    def confine_mouse(self, rects):
        """While the mouse is locked (grab_mouse): keep it inside these screen rectangles instead of just the window –
        e.g. the arena and the extra windows connected to it. None: just the window."""
        if self.layered:
            self.layered.mouse_area = [pygame.Rect(rect) for rect in rects] if rects else None

    def mouse_position(self):
        """The mouse position in screen pixels (world coordinates), not relative to the window – also while it's over
        an extra window."""
        if self.layered:
            return pygame.Vector2(cursor_position())
        return pygame.Vector2(pygame.mouse.get_pos()) + self.shown_topleft

    def open_view(self):
        """A new extra window (see the top of this file) – None if there can't be one (no layered windows). The scene
        sets its rect (where it is on the screen = the part of the world it shows) and draws it in draw_view()."""
        if not self.layered:
            return None
        try:
            view = ViewWindow(self.layered.hwnd)
        except (OSError, pygame.error):
            return None
        self.views.append(view)
        return view

    def close_view(self, view):
        if view in self.views:
            self.views.remove(view)
            view.close()

    def close_views(self):
        for view in self.views[:]:
            self.close_view(view)

    def present_views(self):
        """Every extra window: the scene draws the part of the world it shows, then it's put on the screen."""
        for view in self.views[:]:
            if view.hidden:
                view.hide()
                continue
            if view.rect is None or view.rect.width <= 0 or view.rect.height <= 0:
                continue
            try:
                picture = view.canvas()
                self.scene.draw_view(picture, view)
                view.show()
            except OSError:
                self.close_view(view)

    def is_own_event(self, event):
        """False for events of an extra window (they have their own window attribute)."""
        window = getattr(event, "window", None)
        return window is None or window.id == self.window.id

    def change_scene(self, scene):
        self.close_views()
        self.confine_mouse(None)
        self.scene = scene
        scene.engine = self
        scene.enter()

    def stop(self):
        self.running = False

    def present(self):
        """Draws the scene and shows it – moving/resizing the window at the same moment (see the top of this file)."""
        size, topleft = self.target_rect.size, self.target_rect.topleft
        picture = None
        if self.layered:
            try:
                picture = self.layered.canvas(size)
            except OSError:
                self.drop_layered()
        if picture is None:
            if self.buffer is None or self.buffer.get_size() != size:
                self.buffer = pygame.Surface(size, 0, 32)
            picture = self.buffer
        self.scene.draw(picture)
        if self.dwm_flush and self.dwm_flush() != 0:
            self.dwm_flush = None               # compositor not available after all
        if self.layered:
            try:
                self.layered.show(size, topleft)
                self.shown_topleft = topleft
                self.present_views()
                return
            except OSError:
                picture = picture.copy()        # its memory goes away with the layered window
                self.drop_layered()
        if tuple(self.window.position) != topleft:
            self.window.position = topleft
        if tuple(self.window.size) != size:
            self.window.size = size
        self.window.get_surface().blit(picture, (0, 0))
        self.window.flip()
        self.shown_topleft = topleft

    def drop_layered(self):
        """The layered window doesn't work (any more): from now on SDL's way."""
        self.layered.close()
        self.layered = None
        self.window.grab_mouse = self.mouse_locked

    def internal_focus_loss(self, event):
        """True if event is the main window losing the focus while the active window is still one of the game's own
        (an extra window got clicked) – then it's not a real "the player left the game"."""
        if event.type != pygame.WINDOWFOCUSLOST or not self.views:
            return False
        try:
            user32 = ctypes.windll.user32
            user32.GetForegroundWindow.restype = wintypes.HWND
            active = user32.GetForegroundWindow()
        except (AttributeError, OSError):
            return False
        return active in {self.window.handle} | {view.hwnd for view in self.views}

    def handle_focus(self, event):
        """Lets the mouse go while another window is active (Alt+Tab) – otherwise it would stay locked in."""
        if self.layered and event.type in (pygame.WINDOWFOCUSLOST, pygame.WINDOWFOCUSGAINED):
            self.layered.lock_mouse(self.mouse_locked and event.type == pygame.WINDOWFOCUSGAINED)

    def run(self, scene):
        self.change_scene(scene)
        self.running = True
        accumulator = 0.0
        try:
            while self.running:
                frame_time = self.clock.tick(MAX_FPS if self.dwm_flush else self.tick_rate) / 1000
                accumulator += min(frame_time, MAX_FRAME_TIME)

                for event in pygame.event.get():
                    if not self.is_own_event(event):
                        continue
                    if self.internal_focus_loss(event):
                        self.window.focus()             # back to the main window, the game goes on
                        continue
                    if event.type in (pygame.QUIT, pygame.WINDOWCLOSE):           # e.g. Alt+F4
                        self.stop()
                    else:
                        self.handle_focus(event)
                        self.scene.handle_event(event)

                while accumulator >= self.tick_time:
                    self.scene.update(self.tick_time)
                    accumulator -= self.tick_time

                self.present()
        finally:
            self.close_views()
            if self.layered:
                self.layered.close()            # also lets the mouse go, even after a crash
            self.window.destroy()
            pygame.quit()
