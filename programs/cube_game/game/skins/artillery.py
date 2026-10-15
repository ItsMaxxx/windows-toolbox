"""Artillery: an olive square with a catapult on top. Its arm lies back with a shell in the bucket; when it fires, the arm
swings forward over the top (seen from above: the bucket comes over the body and rises up the screen – the same way a
shell in the air is drawn, see artillery_strike.py) and hits the crossbar in front; then it cranks back during the
reload (enemy.arm in degrees, enemy.loaded). While it sets up, four small square feet slide out from under its
corners (enemy.deploy: 0 … 1) – and back in while it packs up."""

import math

import pygame

from game.artillery_strike import SHELL_COLOR, SHELL_RING
from game.skins.skin import Skin

ARM_LENGTH = 0.9            # the arm's length, as part of the size (the enemy throws its shells from that high)
ARM_COLOR = (200, 210, 150)
FRAME_COLOR = (75, 85, 35)
FOOT_COLOR = (90, 100, 45)
FOOT_SIZE = 0.35            # side of a foot, as part of the artillery's size …
FOOT_OUT = 0.12             # … and how far it sticks out past the corner (both ways)
CROSSBAR_AT = 0.3           # the crossbar the arm stops at: this far in front of the middle (part of the size) …
CROSSBAR_WIDTH = 0.9        # … and this long
BUCKET_SIZE = 0.17          # the bucket's radius, as part of the size (a bit bigger the higher it is)


class ArtillerySkin(Skin):
    color = (125, 140, 60)
    shell_color = SHELL_COLOR

    def draw_below(self, surface, enemy, rect):
        if enemy.deploy > 0:
            side = enemy.size * FOOT_SIZE
            out = enemy.size * FOOT_OUT * enemy.deploy          # at 0 just inside the corner: hidden under the body
            for x, y in ((-1, -1), (1, -1), (-1, 1), (1, 1)):       # the four corners
                foot = pygame.Rect(0, 0, side, side)
                foot.center = (rect.centerx + x * (rect.width / 2 + out - side / 2),
                               rect.centery + y * (rect.height / 2 + out - side / 2))
                pygame.draw.rect(surface, FOOT_COLOR, foot)

    def draw_above(self, surface, enemy, rect):
        center, aim = pygame.Vector2(rect.center), enemy.aim
        across = aim.rotate(90) * enemy.size * CROSSBAR_WIDTH / 2
        bar = center + aim * enemy.size * CROSSBAR_AT
        pygame.draw.line(surface, FRAME_COLOR, bar - across, bar + across, 4)
        # the arm turns about the middle, in the upright plane through aim: -cos along the ground, sin upwards
        length = enemy.size * ARM_LENGTH
        angle = math.radians(enemy.arm)
        up = math.sin(angle)
        bucket = center + aim * length * -math.cos(angle) - (0, length * up)
        pygame.draw.line(surface, ARM_COLOR, center, bucket, 5)
        pygame.draw.circle(surface, FRAME_COLOR, center, 4)                     # the axle
        radius = enemy.size * BUCKET_SIZE * (1 + 0.3 * up)
        pygame.draw.circle(surface, ARM_COLOR, bucket, radius)
        if enemy.loaded:
            shell = radius * 0.75
            pygame.draw.circle(surface, self.shell_color, bucket, shell)
            pygame.draw.circle(surface, SHELL_RING, bucket, shell, 1)
