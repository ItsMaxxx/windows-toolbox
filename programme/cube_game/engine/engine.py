"""
The engine: opens the window and runs the game loop with a fixed timestep.

Game logic runs at exactly TICK_RATE ticks per second, no matter how fast the PC draws. Each frame, the time that has
passed is added to an accumulator; for every full tick in it, the scene gets one update(). That way movement is equally
fast on every PC ("Fix Your Timestep", see README.md).

The window is borderless and can be moved and resized by the game (move_window). Positions in the game world are
screen pixels; the window is just the part of the screen you can see – like a camera.

Moving without flicker: each frame, the scene first draws into a buffer that already has the window's new size. Then
LayeredWindow puts position, size and picture on the screen in one step (see layered_window.py). Before that, the
engine waits for DwmFlush(): Windows' compositor has just refreshed the screen – that syncs the frames to the
monitor. If the layered window isn't available, SDL moves, resizes and shows the picture one after the other right
after DwmFlush(); that still flickers now and then (measured: 4 % of the frames in which the window moves, instead
of 56 % without the wait).
"""

import ctypes

import pygame

from engine.layered_window import LayeredWindow

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

    def mouse_position(self):
        """The mouse position in screen pixels (world coordinates), not relative to the window."""
        return pygame.Vector2(pygame.mouse.get_pos()) + self.shown_topleft

    def change_scene(self, scene):
        self.scene = scene
        scene.engine = self
        scene.enter()

    def stop(self):
        self.running = False

    def present(self):
        """Draws the scene and shows it – moving/resizing the window at the same moment (see the top of this file)."""
        if self.buffer is None or self.buffer.get_size() != self.target_rect.size:
            self.buffer = pygame.Surface(self.target_rect.size, 0, 32)
        self.scene.draw(self.buffer)
        if self.dwm_flush and self.dwm_flush() != 0:
            self.dwm_flush = None               # compositor not available after all
        if self.layered:
            try:
                self.layered.show(self.buffer, self.target_rect.topleft)
                self.shown_topleft = self.target_rect.topleft
                return
            except OSError:
                self.layered.close()
                self.layered = None             # from now on SDL's way
                self.window.grab_mouse = self.mouse_locked
        if tuple(self.window.position) != self.target_rect.topleft:
            self.window.position = self.target_rect.topleft
        if tuple(self.window.size) != self.target_rect.size:
            self.window.size = self.target_rect.size
        self.window.get_surface().blit(self.buffer, (0, 0))
        self.window.flip()
        self.shown_topleft = self.target_rect.topleft

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
            if self.layered:
                self.layered.close()            # also lets the mouse go, even after a crash
            self.window.destroy()
            pygame.quit()
