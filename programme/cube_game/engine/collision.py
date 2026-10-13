"""
Collision helpers for axis-aligned rectangles (AABB).
"""


def keep_inside(rect, bounds):
    """Pushes rect back inside bounds if it sticks out. Returns True if it had to be pushed (it hit a wall)."""
    if bounds.contains(rect):
        return False
    rect.clamp_ip(bounds)
    return True


def overlaps(a, b):
    """True if the two rectangles overlap."""
    return a.colliderect(b)
