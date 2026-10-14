"""
Bottom left in the game: the ability slots with their key, e.g. "SHIFT  Dash". Bright when ready, faded with the
seconds left while cooling down. An ability with several charges shows how many it has, e.g. "SHIFT  Dash  1/2  0.8s"
(bright while at least one is there, the seconds until the next one while one is missing). Above them the energy bar (shared by both weapons) – it turns red while there isn't
enough energy for a shot of any weapon.
"""

import pygame

from engine.ui import draw_text
from game import settings

LINE_HEIGHT = 22
READY_ALPHA = 200
ENERGY_BAR = (150, 8)           # width, height
ENERGY_COLOR = (255, 225, 90)
EMPTY_COLOR = (210, 80, 60)     # not enough for any shot
BAR_BACKGROUND = (45, 45, 52)


class AbilityBar:
    def draw(self, surface, ship):
        bottom = surface.get_height() - 10
        slots = [(key, ability) for key, ability in zip(settings.ABILITY_KEY_NAMES, ship.abilities) if ability]
        for index, (key, ability) in enumerate(slots):
            y = bottom - (len(slots) - index) * LINE_HEIGHT
            text = f"{key}  {ability.name}"
            if ability.max_charges > 1:
                text += f"  {ability.charges}/{ability.max_charges}"
            if ability.charges < ability.max_charges:
                text += f"  {ability.cooldown:.1f}s"
            draw_text(surface, text, 22, settings.TEXT, alpha=READY_ALPHA if ability.ready else settings.HINT_ALPHA,
                      topleft=(10, y))
        self.draw_energy(surface, ship, bottom - len(slots) * LINE_HEIGHT - 8)

    @staticmethod
    def draw_energy(surface, ship, bottom):
        width, height = ENERGY_BAR
        bar = pygame.Rect(10, bottom - height, width, height)
        costs = [weapon.energy_cost for weapon in ship.weapons if weapon]
        color = EMPTY_COLOR if costs and ship.energy < min(costs) else ENERGY_COLOR
        pygame.draw.rect(surface, BAR_BACKGROUND, bar, border_radius=3)
        filled = bar.copy()
        filled.width = round(width * ship.energy / ship.max_energy) if ship.max_energy else 0
        if filled.width:
            pygame.draw.rect(surface, color, filled, border_radius=3)
        draw_text(surface, f"ENERGY  {ship.energy:.0f}", 20, settings.TEXT, alpha=READY_ALPHA,
                  bottomleft=(bar.left, bar.top - 3))
