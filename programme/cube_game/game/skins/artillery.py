"""Artillery: an olive square with a short, thick mortar barrel towards the ship. The barrel kicks back when it fires
and slides out again while it reloads; a muzzle flash for a moment after the shot. While it sets up, four small square
feet slide out from under its corners (enemy.deploy: 0 … 1) – and back in while it packs up."""

import pygame

from game.skins.skin import Skin

BARREL_COLOR = (200, 210, 150)
FLASH_COLOR = (255, 210, 120)
KICK = 0.45                 # how far the barrel goes back on a shot (part of its length)
FOOT_COLOR = (90, 100, 45)
FOOT_SIZE = 0.35            # side of a foot, as part of the artillery's size …
FOOT_OUT = 0.12             # … and how far it sticks out past the corner (both ways)


class ArtillerySkin(Skin):
    color = (125, 140, 60)

    def draw_below(self, surface, enemy, rect):
        if enemy.deploy > 0:
            side = enemy.size * FOOT_SIZE
            out = enemy.size * FOOT_OUT * enemy.deploy          # at 0 just inside the corner: hidden under the body
            for x, y in ((-1, -1), (1, -1), (-1, 1), (1, 1)):       # the four corners
                foot = pygame.Rect(0, 0, side, side)
                foot.center = (rect.centerx + x * (rect.width / 2 + out - side / 2),
                               rect.centery + y * (rect.height / 2 + out - side / 2))
                pygame.draw.rect(surface, FOOT_COLOR, foot)
        start = pygame.Vector2(rect.center)
        length = enemy.size * (1.0 - KICK * enemy.recoil)
        end = start + enemy.aim * length
        pygame.draw.line(surface, BARREL_COLOR, start, end, 10)
        if enemy.recoil > 0.7:                      # right after the shot
            pygame.draw.circle(surface, FLASH_COLOR, end + enemy.aim * 6, 7)
