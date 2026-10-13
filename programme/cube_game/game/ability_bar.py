"""
Bottom left in the game: the ability slots with their key, e.g. "SHIFT  Dash". Bright when ready, faded with the
seconds left while cooling down.
"""

from engine.ui import draw_text
from game import settings

LINE_HEIGHT = 22
READY_ALPHA = 200


class AbilityBar:
    def draw(self, surface, ship):
        bottom = surface.get_height() - 10
        slots = [(key, ability) for key, ability in zip(settings.ABILITY_KEY_NAMES, ship.abilities) if ability]
        for index, (key, ability) in enumerate(slots):
            y = bottom - (len(slots) - index) * LINE_HEIGHT
            if ability.ready:
                draw_text(surface, f"{key}  {ability.name}", 22, settings.TEXT, alpha=READY_ALPHA, topleft=(10, y))
            else:
                draw_text(surface, f"{key}  {ability.name}  {ability.cooldown:.1f}s", 22, settings.TEXT,
                          alpha=settings.HINT_ALPHA, topleft=(10, y))
