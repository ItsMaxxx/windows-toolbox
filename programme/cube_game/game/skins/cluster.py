"""Cluster: like the Artillery, but darker and browner (with the tier 2 frame), and its shells are rust red."""

from game.skins.artillery import ArtillerySkin

SHELL_COLOR = (150, 60, 30)


class ClusterSkin(ArtillerySkin):
    color = (110, 100, 45)
    shell_color = SHELL_COLOR
