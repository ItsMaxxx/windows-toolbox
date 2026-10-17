"""Pusher: a big dark-blue block with light stripes; while it holds on, a thick arm with a fist reaches into the arena."""

import pygame

from game.skins.skin import FLASH_COLOR, Skin

ARM_COLOR = (90, 120, 200)
STRIPE_COLOR = (140, 165, 230)


class PusherSkin(Skin):
    color = (45, 60, 130)

    def draw_below(self, surface, enemy, rect):
        """The arm – rect is the body in window coordinates, the arm is moved the same way."""
        if not enemy.holding:
            return
        shift = pygame.Vector2(rect.topleft) - enemy.body.topleft
        arm = enemy.rect.move(shift)
        color = FLASH_COLOR if enemy.flash else ARM_COLOR
        pygame.draw.rect(surface, color, arm)
        fist = pygame.FRect(0, 0, arm.width + 8, arm.height + 8)
        if enemy.side in ("left", "right"):
            fist.width = arm.height + 8
            fist.center = (arm.right - fist.width / 2 if enemy.side == "left" else arm.left + fist.width / 2,
                           arm.centery)
        else:
            fist.height = arm.width + 8
            fist.center = (arm.centerx,
                           arm.bottom - fist.height / 2 if enemy.side == "top" else arm.top + fist.height / 2)
        pygame.draw.rect(surface, color, fist, border_radius=4)

    def draw_above(self, surface, enemy, rect):
        """Two light stripes across the body, along the way it shoves."""
        horizontal = enemy.side in ("left", "right") or enemy.side is None
        for share in (0.33, 0.67):
            if horizontal:
                y = rect.top + rect.height * share
                pygame.draw.line(surface, STRIPE_COLOR, (rect.left + 5, y), (rect.right - 6, y), 3)
            else:
                x = rect.left + rect.width * share
                pygame.draw.line(surface, STRIPE_COLOR, (x, rect.top + 5), (x, rect.bottom - 6), 3)
