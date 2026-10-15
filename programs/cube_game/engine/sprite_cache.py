"""
Pictures that are made once and then reused, instead of drawing the same thing again in every frame.

Measured: an enemy's body drawn from scratch (square, frame, health pips) costs about 5–10 times as much as copying
a finished picture of it (blit), and a see-through effect that makes a new surface every frame costs about 4 times as
much as one that reuses its picture. What's slow there is mostly Python calling the drawing functions one by one – a
single blit is one call.

    PICTURES.get(key, make)   – the picture for key; make() draws it the first time. key must hold everything that
                                changes how it looks (size, colour, white for a hit, …)
    scratch(size)             – a cleared see-through surface to draw something on that changes every frame (it's
                                reused instead of made anew)
    load_picture(path)        – a picture file (PNG …) ready to draw, or None
"""

from collections import OrderedDict

import pygame


class SpriteCache:
    def __init__(self, limit):
        """limit: how many pictures it keeps – beyond that, the one unused the longest is dropped."""
        self.limit = limit
        self.pictures = OrderedDict()

    def get(self, key, make):
        if key in self.pictures:
            self.pictures.move_to_end(key)
            return self.pictures[key]
        picture = self.pictures[key] = make()       # may be None (e.g. no picture file) – that's kept, too
        if len(self.pictures) > self.limit:
            self.pictures.popitem(last=False)
        return picture

    def clear(self):
        self.pictures.clear()


PICTURES = SpriteCache(4000)    # small pictures (enemies, effects): even 4000 of them are only a few MB


def scratch(size):
    """A cleared see-through surface of size, to draw on and blit right away – always the same one for a size, so it's
    only valid until the next scratch() with that size."""
    surface = PICTURES.get(("scratch", tuple(size)), lambda: pygame.Surface(size, pygame.SRCALPHA))
    surface.fill((0, 0, 0, 0))
    surface.set_alpha(255)
    return surface


def load_picture(path):
    """A picture file (PNG, …) as a see-through surface in the format the game draws in (an opaque one gets alpha 255).
    None if the file doesn't exist or can't be read."""
    try:
        image = pygame.image.load(path)
    except (OSError, pygame.error):
        return None
    picture = pygame.Surface(image.get_size(), pygame.SRCALPHA)
    picture.blit(image, (0, 0))
    return picture
