"""
The arena is the game window itself: a rectangle on the screen that keeps shrinking towards its centre. A shot that
hits one of its edges pushes exactly that edge back out – but only as far as there's screen behind it: with several
monitors it can spread over all of them, but never into a gap between them or under a taskbar (Desktop.covers()).
Once it's as narrow or as low as the ship, the ship is crushed (crushed()) and the run is over.

The edges move in faster the longer the run lasts: shrink_growth more pixels per second every minute, up to
max_shrink_speed (all three from the difficulty).

Armor: every push of an edge is armor pixels shorter – flat, so many small pushes (machine gun, laser) lose far more
than a few big ones (cannon); at least settings.MIN_PUSH_SHARE of a push is always left (game/armor.py). The difficulty
sets where it starts; its phases can change it – and the shrink speed and push falloff – for a while or for good
(changes, set by the scene from the active phases).

Push falloff: the further the arena is out already, the less a push does – per axis, so a wide arena is hard to widen
but still easy to make taller. A push is multiplied by (start size ÷ size now) ^ push_falloff on the edge's axis: with
falloff 1 it does half at twice the start width, and double while the arena is half as wide as at the start. 0 = off.

Breathing: a phase with "breathe" pulls every edge in by that many pixels over its time, on top of the shrinking –
and when it ends, they spring back out by as much (smoothly, like a push, but armor and falloff don't count). Push
the walls while it lasts, and the arena is bigger afterwards (breathe()).

Shoving: a Pusher moves the whole window (shove()). Where the screen ends, the window can't go on – that edge stays,
and the opposite one moves in instead: the arena gets narrower, down to the ship's size.

Getting hit squeezes the arena (hit()) – mostly from the side away from the ship, so it can't be dragged along by
just moving one way.
"""

import pygame

from engine.collision import keep_inside
from game import armor, settings, ship_data
from game.enemies.roster import apply

SIDES = ("left", "right", "top", "bottom")
ROOM_STEPS = 20             # how exactly the free room in front of an edge is found (halving the step this often)


class Arena:
    def __init__(self, desktop, size, shrink_speed, shrink_growth=0.0, max_shrink_speed=None, armor=0.0,
                 push_falloff=0.0):
        """desktop: where the window may be (engine/desktop.py). It starts in the middle of the main monitor. size: at
        the start. shrink_speed: pixels per second each edge moves in at the start, plus shrink_growth per minute, up
        to max_shrink_speed (None: no limit). armor and push_falloff: at the start (see above)."""
        self.desktop = desktop
        self.start_shrink_speed = shrink_speed
        self.shrink_growth = shrink_growth
        self.max_shrink_speed = max_shrink_speed
        self.base_armor = armor
        self.base_push_falloff = push_falloff
        self.changes = []                   # (value, operation, number) from the active phases – set by the scene
        self.breathing = {}                 # id(phase) -> phase: the active phases that breathe – breathe()
        self.storm_speed = 0.0              # pixels per second more while it reaches into a storm (game/points.py)
        self.fixed_speed = False
        self.ship_size = ship_data.current()["size"]   # the edges stop there – set by the scene from its ship
        self.elapsed = 0.0                  # seconds this arena has been shrinking
        self.rect = pygame.FRect((0, 0), size)
        self.rect.center = desktop.main.center
        if not desktop.covers(self.rect):
            self.rect = self.rect.clip(desktop.main)       # bigger than the main monitor
        self.start_size = self.rect.size                    # pushes are measured against it (push falloff)
        self.pending = dict.fromkeys(SIDES, 0.0)     # how far each edge still has to move out after hits

    def window_rect(self):
        """The arena as a whole-pixel rectangle for the window. Every edge is rounded on its own, so the opposite edge
        doesn't wobble when one edge moves."""
        left, top = round(self.rect.left), round(self.rect.top)
        return pygame.Rect(left, top, round(self.rect.right) - left, round(self.rect.bottom) - top)

    def changed(self, name, value):
        """value with the active phases' changes to name applied, in their order."""
        for changed_name, operation, number in self.changes:
            if changed_name == name:
                value = apply(value, operation, number)
        return value

    @property
    def shrink_speed(self):
        """Pixels per second each edge moves in right now."""
        speed = self.start_shrink_speed + self.shrink_growth * self.elapsed / 60
        if self.max_shrink_speed is not None:
            speed = min(self.max_shrink_speed, speed)
        return speed if self.fixed_speed else max(0.0, self.changed("shrink_speed", speed))

    @shrink_speed.setter
    def shrink_speed(self, speed):
        """A fixed speed from now on (e.g. 0 to stop the walls) – phases don't change it any more either."""
        self.start_shrink_speed, self.shrink_growth, self.max_shrink_speed = speed, 0.0, None
        self.fixed_speed = True

    @property
    def armor(self):
        """Pixels every push of an edge is shorter right now."""
        return max(0.0, self.changed("armor", self.base_armor))

    @property
    def push_falloff(self):
        """How much harder pushes get the further the arena is out already (see above)."""
        return max(0.0, self.changed("push_falloff", self.base_push_falloff))

    def push_factor(self, side):
        """What a push on side is multiplied by: (start size ÷ size now) ^ push_falloff on that side's axis – below 1
        while the arena is bigger than at the start, above 1 while it's smaller."""
        axis = 0 if side in ("left", "right") else 1
        return (self.start_size[axis] / max(1.0, self.rect.size[axis])) ** self.push_falloff

    def update(self, dt):
        self.elapsed += dt
        breath = sum(phase.breathe / (phase.end - phase.start) for phase in self.breathing.values())
        self.squeeze((self.shrink_speed + breath + self.storm_speed) * dt)
        self._expand(dt)

    def breathe(self, phases):
        """phases: the active phases (set by the scene every tick). Those with breathe pull the edges in while they
        last; one that has ended gives its pixels back – every edge springs out again."""
        now = {id(phase): phase for phase in phases if phase.breathe}
        for key, phase in self.breathing.items():
            if key not in now:
                for side in SIDES:
                    self.pending[side] += phase.breathe
        self.breathing = now

    def squeeze(self, distance):
        """Moves every edge inwards by distance – each tick a little. It stops at the ship's size: then the ship is
        crushed."""
        smallest = self.ship_size
        step_x = min(distance, max(0.0, (self.rect.width - smallest) / 2))
        step_y = min(distance, max(0.0, (self.rect.height - smallest) / 2))
        self.rect.inflate_ip(-2 * step_x, -2 * step_y)       # inflate keeps the centre in place

    def hit(self, distance, ship):
        """The ship was hit: the arena gets 2 × distance narrower and lower – the edges away from ship (a point) move
        in more than the near ones (settings.HIT_SIDE_BIAS). Stops at the ship's size, like squeeze()."""
        smallest = self.ship_size
        rect = self.rect
        for low, high, size, position in (("left", "right", rect.width, ship[0] - rect.left),
                                          ("top", "bottom", rect.height, ship[1] - rect.top)):
            total = min(2 * distance, max(0.0, size - smallest))
            share = min(1.0, max(0.0, position / size)) if size else 0.5      # 0 at the low edge … 1 at the high one
            near_low = 0.5 + settings.HIT_SIDE_BIAS * (share - 0.5)          # the low edge's part of total
            if low == "left":
                rect.update(rect.left + total * near_low, rect.top, rect.width - total, rect.height)
            else:
                rect.update(rect.left, rect.top + total * near_low, rect.width, rect.height - total)

    def _expand(self, dt):
        for side, distance in self.pending.items():
            step = min(distance, settings.PUSH_SPEED * dt)
            if step <= 0:
                continue
            self.pending[side] -= step
            if not self.desktop.covers(self.widened(side, step)):
                step = self.room(side, step)            # only up to the end of the screen
            self.rect = self.widened(side, step)

    def shove(self, side, distance):
        """Moves the whole window distance pixels towards side ("right": to the right). As far as the screen goes –
        the rest squeezes: the edge at the end of the screen stays, the opposite one moves in (not below the ship)."""
        direction = {"left": (-1, 0), "right": (1, 0), "top": (0, -1), "bottom": (0, 1)}[side]

        def moved(step):
            return self.rect.move(direction[0] * step, direction[1] * step)

        step = distance
        if not self.desktop.covers(moved(step)):
            fits, too_far = 0.0, step                   # how far it can go – found by halving, like room()
            for _ in range(ROOM_STEPS):
                middle = (fits + too_far) / 2
                if self.desktop.covers(moved(middle)):
                    fits = middle
                else:
                    too_far = middle
            step = fits
        self.rect = moved(step)
        rest = distance - step
        if rest <= 0:
            return
        horizontal = side in ("left", "right")
        rest = min(rest, max(0.0, (self.rect.width if horizontal else self.rect.height) - self.ship_size))
        rect = self.rect
        if side == "right":
            rect.update(rect.left + rest, rect.top, rect.width - rest, rect.height)
        elif side == "left":
            rect.width -= rest
        elif side == "bottom":
            rect.update(rect.left, rect.top + rest, rect.width, rect.height - rest)
        else:
            rect.height -= rest

    def widened(self, side, step):
        """The arena with one edge moved out by step."""
        rect = self.rect.copy()
        if side == "left":
            rect.update(rect.left - step, rect.top, rect.width + step, rect.height)
        elif side == "right":
            rect.width += step
        elif side == "top":
            rect.update(rect.left, rect.top - step, rect.width, rect.height + step)
        else:
            rect.height += step
        return rect

    def room(self, side, step):
        """How far (at most step) the edge can move out and still be completely on screen – found by halving."""
        fits, too_far = 0.0, step
        for _ in range(ROOM_STEPS):
            middle = (fits + too_far) / 2
            if self.desktop.covers(self.widened(side, middle)):
                fits = middle
            else:
                too_far = middle
        return fits

    def push(self, side, distance):
        """Hit on an edge: it moves out by distance times the push factor, minus the armor (smoothly, over the next
        ticks)."""
        if distance > 0:
            distance *= self.push_factor(side)
            self.pending[side] += armor.reduce(distance, self.armor, settings.MIN_PUSH_SHARE)

    def side_hit(self, point):
        """Which edge point has crossed ("left", "right", "top", "bottom") – or None while it's inside.
        Past a corner, the edge it is further beyond wins."""
        overshoot = {
            "left": self.rect.left - point[0],
            "right": point[0] - self.rect.right,
            "top": self.rect.top - point[1],
            "bottom": point[1] - self.rect.bottom,
        }
        side = max(overshoot, key=overshoot.get)
        return side if overshoot[side] > 0 else None

    def crushed(self, entity):
        """True if two opposite edges touch entity at once – the arena is no wider or no higher than it."""
        return self.rect.width <= entity.rect.width + 0.01 or self.rect.height <= entity.rect.height + 0.01

    def contain(self, entity):
        """Keeps entity inside the arena (shrinking edges push it along). True if it touched an edge."""
        return keep_inside(entity.rect, self.rect)

    def draw(self, surface, offset):
        """Background and an outline along the edges (the arena fills the whole window)."""
        surface.fill(settings.BACKGROUND)
        rect = self.window_rect().move(-offset[0], -offset[1])
        pygame.draw.rect(surface, settings.BORDER, rect, settings.BORDER_WIDTH)
