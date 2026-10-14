"""
Top right in the game: the time survived, the cores collected in this run, and – once the shop is unlocked – the
stars the player has and a small shop icon with its key (T). With the watchtower unlocked, one more line: the next
tower's price, how many stand of how many allowed, and its key (B).
"""

from engine.ui import draw_text
from game import settings
from game.icons import draw_core, draw_shop_icon, draw_star, draw_watchtower_icon

RIGHT_MARGIN = 12
READY_ALPHA = 200


class Hud:
    def draw(self, surface, elapsed, stars, cores, towers=None):
        """stars: None while the shop is locked (then stars and the shop icon aren't shown). towers: (standing,
        allowed, price of the next) – None without the watchtower."""
        right = surface.get_width() - RIGHT_MARGIN
        minutes, seconds = divmod(int(elapsed), 60)
        timer = draw_text(surface, f"{minutes:02}:{seconds:02}", 30, settings.TEXT, alpha=READY_ALPHA,
                          topright=(right, 8))

        count = draw_text(surface, str(cores), 26, settings.TEXT, alpha=READY_ALPHA, topright=(right, timer.bottom + 4))
        draw_core(surface, (count.left - 12, count.centery), 8)
        if stars is None:
            return
        count = draw_text(surface, str(stars), 26, settings.TEXT, alpha=READY_ALPHA, topright=(right, count.bottom + 4))
        draw_star(surface, (count.left - 12, count.centery), 8)

        key = draw_text(surface, "T", 22, settings.TEXT, alpha=settings.HINT_ALPHA * 2,
                        topright=(right, count.bottom + 8))
        faded = [round(channel * settings.HINT_ALPHA * 2 / 255) for channel in settings.TEXT]
        draw_shop_icon(surface, (key.left - 14, key.centery), faded)
        if towers is None:
            return
        standing, allowed, price = towers
        key = draw_text(surface, settings.BUILD_KEY_NAME, 22, settings.TEXT, alpha=settings.HINT_ALPHA * 2,
                        topright=(right, key.bottom + 8))
        draw_watchtower_icon(surface, (key.left - 14, key.centery), faded)
        count = draw_text(surface, f"{standing}/{allowed}", 22, settings.TEXT, alpha=READY_ALPHA,
                          midright=(key.left - 28, key.centery))
        if standing < allowed:
            cost = draw_text(surface, str(price), 22, settings.TEXT, alpha=READY_ALPHA,
                             midright=(count.left - 12, count.centery))
            draw_star(surface, (cost.left - 9, cost.centery), 6)
