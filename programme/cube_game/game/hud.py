"""
Top right in the game: the time survived, the stars the player has, and a small shop icon with its key (T).
"""

from engine.ui import draw_text
from game import settings
from game.icons import draw_shop_icon, draw_star

RIGHT_MARGIN = 12
READY_ALPHA = 200


class Hud:
    def draw(self, surface, elapsed, stars):
        right = surface.get_width() - RIGHT_MARGIN
        minutes, seconds = divmod(int(elapsed), 60)
        timer = draw_text(surface, f"{minutes:02}:{seconds:02}", 30, settings.TEXT, alpha=READY_ALPHA,
                          topright=(right, 8))

        count = draw_text(surface, str(stars), 26, settings.TEXT, alpha=READY_ALPHA, topright=(right, timer.bottom + 4))
        draw_star(surface, (count.left - 12, count.centery), 8)

        key = draw_text(surface, "T", 22, settings.TEXT, alpha=settings.HINT_ALPHA * 2,
                        topright=(right, count.bottom + 8))
        faded = [round(channel * settings.HINT_ALPHA * 2 / 255) for channel in settings.TEXT]
        draw_shop_icon(surface, (key.left - 14, key.centery), faded)
