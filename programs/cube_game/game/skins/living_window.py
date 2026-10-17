"""Living Window: a thick frame around a tinted area – turquoise while small, red once it's about to burst – with an
eye that watches the ship. Docked, the eye sits in the part reaching into the arena, so you see it from in there."""

import pygame

from game.skins.skin import FLASH_COLOR, Skin

YOUNG = (60, 220, 200)              # the frame's colour at min_size …
RIPE = (240, 60, 60)                # … and right before it bursts
EYE = (235, 245, 240)
PUPIL = (20, 30, 30)
TINT = 0.12                         # the area inside: the frame's colour this bright, added to what's there


def mix(low, high, share):
    return tuple(round(a + (b - a) * share) for a, b in zip(low, high))


class LivingWindowSkin(Skin):
    color = YOUNG

    def draw_window(self, surface, enemy, rect):
        low, high = enemy.stat("min_size"), enemy.stat("max_size")
        ripe = min(1.0, max(0.0, (rect.width - low) / max(1.0, high - low)))
        color = FLASH_COLOR if enemy.flash else mix(YOUNG, RIPE, ripe)
        surface.fill([round(channel * TINT) for channel in color], rect, special_flags=pygame.BLEND_RGB_ADD)
        pygame.draw.rect(surface, color, rect, 4)
        inner = pygame.FRect(rect).inflate(-12, -12)
        if inner.width > 4:
            pygame.draw.rect(surface, [round(channel * 0.4) for channel in color], inner, 1)
        radius = max(5.0, rect.width * 0.11)
        center = pygame.Vector2(rect.center)
        if enemy.side is not None:                      # docked: into the part that reaches into the arena
            overlap = enemy.stat("overlap")
            radius = min(radius, overlap * 0.32)
            inward = {"left": (1, 0), "right": (-1, 0), "top": (0, 1), "bottom": (0, -1)}[enemy.side]
            center += pygame.Vector2(inward) * (rect.width / 2 - overlap / 2)
        pygame.draw.ellipse(surface, EYE, pygame.FRect(center.x - radius * 1.4, center.y - radius, radius * 2.8,
                                                       radius * 2))
        pygame.draw.circle(surface, PUPIL, center + enemy.aim * radius * 0.6, radius * 0.5)
