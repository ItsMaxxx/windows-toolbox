"""
Base class for scenes (menu, game, game over, editor, …). The engine always runs exactly one scene.
"""


class Scene:
    def __init__(self):
        self.engine = None          # set by Engine.change_scene()

    def enter(self):
        """Called when the scene becomes active – e.g. to move the window into place."""

    def handle_event(self, event):
        """One pygame event (key pressed, mouse click, …). Closing the window is handled by the engine."""

    def update(self, dt):
        """One logic tick. dt is always the same (1 / tick rate) in seconds."""

    def draw(self, surface):
        """Draw the whole scene onto surface (the window's content)."""
