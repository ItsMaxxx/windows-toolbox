"""
Armor is flat everywhere – the walls' (the level's arena armor), the ship's and the enemies': every push or hit loses
that many pixels or points. So many small pushes or shots (machine gun, laser) lose much more of their effect than a
few big ones (cannon). It never takes everything, though: a share is always left (settings.MIN_PUSH_SHARE,
MIN_HIT_SHARE, MIN_DAMAGE_SHARE).
"""


def reduce(amount, armor, min_share):
    """amount minus armor – but at least min_share of amount."""
    return max(amount - max(0.0, armor), amount * min_share)
