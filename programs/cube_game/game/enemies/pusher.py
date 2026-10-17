"""
Pusher: a big dark-blue block that comes from beyond the edge of the map. It walks straight to the nearest edge of the
arena – through every other enemy (solid = False: out there you couldn't see them bump into each other) – grabs it
from outside and shoves the whole window away from itself (Arena.shove): towards the edge of the screen, and once the
window is there, the arena gets narrower on that side.

Its body stays outside, where shots can't reach it (a shot that does reach it, through a watchtower's window, bounces
off). Only its arm, reaching into the arena, can be hit – that's its hitbox (rect) while it holds on. Out there you
still see it: the scene gives it a small window of its own that follows it (view – not part of the field, only to see
it).

body is where it is (screen pixels), rect what can be hit: the body while it walks (shots bounce off it), the arm
while it holds on.
"""

import pygame

from game.enemies.enemy import Enemy
from game.skins.pusher import PusherSkin

WALK, HOLD = "walk", "hold"
GAP = 2                         # pixels between its body and the arena's edge while it holds on
OPPOSITE = {"left": "right", "right": "left", "top": "bottom", "bottom": "top"}


class Pusher(Enemy):
    key = "pusher"
    name = "Pusher"
    skin = PusherSkin()
    solid = False
    spawns_outside = True       # the spawner puts it beyond the edge of the map
    stats = {                   # fallback – see data/enemies.json
        "base_hp": 10, "speed": 70, "size": 46, "contact_damage": 25,
        "push_speed": 30,       # pixels per second it shoves the window
        "arm_length": 44,       # how far its arm reaches into the arena …
        "arm_width": 18,        # … and how thick it is (the hitbox while it holds on)
    }

    def __init__(self, position, roster=None):
        super().__init__(position, roster)
        self.body = pygame.FRect(self.rect)
        self.state = WALK
        self.side = None            # the arena's edge it holds ("left", …)
        self.along = 0.0            # where along that edge (screen pixels: y for left/right, x for top/bottom)
        self.view = None            # its own window (set by the scene) – None while there's none

    @property
    def holding(self):
        return self.state == HOLD

    def blocks(self, projectile):
        """Its body is armored: only the arm can be hurt."""
        return not self.holding

    def act(self, dt, ship):
        if self.arena is None:
            return []
        if self.state == WALK:
            self.walk(dt)
        if self.state == HOLD:
            self.arena.shove(OPPOSITE[self.side], self.stat("push_speed") * self.speed_factor * dt)
            self.hold_on()
        return []

    def walk(self, dt):
        """Towards the nearest point just outside the arena's edge; there it grabs the edge."""
        arena = self.arena.rect
        center = pygame.Vector2(self.body.center)
        side = self.arena.side_hit(center) or self.nearest_side(center)
        spot = self.spot(side, center.y if side in ("left", "right") else center.x)
        offset = spot - center
        step = self.stat("speed") * self.speed_factor * dt
        if offset.length() <= step:
            self.state, self.side = HOLD, side
            self.along = spot.y if side in ("left", "right") else spot.x
            return
        self.body.center = center + offset.normalize() * step
        self.rect = pygame.FRect(self.body)
        if arena.colliderect(self.body):            # came at a corner: step straight out of the arena again
            self.body.center = self.spot(side, self.along_of(center, side))
            self.rect = pygame.FRect(self.body)

    def nearest_side(self, center):
        arena = self.arena.rect
        gaps = {"left": center.x - arena.left, "right": arena.right - center.x,
                "top": center.y - arena.top, "bottom": arena.bottom - center.y}
        return min(gaps, key=gaps.get)

    @staticmethod
    def along_of(center, side):
        return center.y if side in ("left", "right") else center.x

    def spot(self, side, along):
        """Where its centre is when it holds side at along (kept within the edge, so the arm fits)."""
        arena = self.arena.rect
        half = self.body.width / 2 + GAP
        reach = self.stat("arm_width") / 2
        if side in ("left", "right"):
            y = min(max(along, arena.top + reach), arena.bottom - reach) if arena.height > 2 * reach else arena.centery
            return pygame.Vector2(arena.left - half if side == "left" else arena.right + half, y)
        x = min(max(along, arena.left + reach), arena.right - reach) if arena.width > 2 * reach else arena.centerx
        return pygame.Vector2(x, arena.top - half if side == "top" else arena.bottom + half)

    def hold_on(self):
        """Its body stays glued to the edge it holds (the edge moves – shoved, pushed back, shrinking); the arm reaches
        into the arena from there."""
        arena = self.arena.rect
        self.body.center = self.spot(self.side, self.along)
        length, width = self.stat("arm_length"), self.stat("arm_width")
        if self.side in ("left", "right"):
            arm = pygame.FRect(0, 0, min(length, arena.width), width)
            arm.centery = self.body.centery
            if self.side == "left":
                arm.left = arena.left
            else:
                arm.right = arena.right
        else:
            arm = pygame.FRect(0, 0, width, min(length, arena.height))
            arm.centerx = self.body.centerx
            if self.side == "top":
                arm.top = arena.top
            else:
                arm.bottom = arena.bottom
        self.rect = arm

    def draw(self, surface, offset):
        self.skin.draw(surface, self, self.body.move(-offset[0], -offset[1]))
