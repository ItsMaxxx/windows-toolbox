"""
Cluster: the Artillery's evolution (tier 2). Darker and tougher; sets up and throws with its catapult just like an
Artillery, but its shell is a splitter: it does no harm where it comes down (only a thin ring marks the spot) – it
bursts there into split_count fragments that hop far apart (split_min_spread … split_spread pixels, evenly round the
spot), each with its own small red circle (split_radius) that fills while it's in the air (split_time). Running from
the big circle doesn't work any more: watch where the fragments go.
"""

from game.artillery_strike import ArtilleryStrike, Split
from game.enemies.artillery import Artillery
from game.skins.cluster import SHELL_COLOR, ClusterSkin


class ClusterArtillery(Artillery):
    key = "cluster"
    name = "Cluster"
    tier = 2
    skin = ClusterSkin()
    stats = {                       # fallback – see data/enemies.json
        "base_hp": 5, "speed": 50, "size": 36, "contact_damage": 25,
        "fire_range": 950, "min_range": 240, "setup_time": 1.2, "pack_time": 0.9, "reload_time": 4.0,
        "turn_speed": 50, "fire_cone": 16, "fill_time": 1.4, "aim_spread": 40,
        "swing_time": 0.35, "arc_height": 80, "arc_steepness": 0.18, "arc_peak": 0.5, "shell_size": 18,
        "split_count": 3,           # fragments the shell bursts into …
        "split_spread": 170,        # … landing at most this far from where it came down …
        "split_min_spread": 100,    # … and at least this far
        "split_radius": 40,         # a fragment's circle
        "split_damage": 35,
        "split_time": 0.8,          # seconds a fragment is in the air (its circle fills meanwhile)
        "split_arc_height": 60,
    }

    def launch(self, spot):
        split = Split(self.stat("split_count"), self.stat("split_spread"), self.stat("split_min_spread"),
                      self.stat("split_radius"), self.stat("split_damage"), self.stat("split_time"),
                      self.stat("split_arc_height"))
        return ArtilleryStrike(self.center, spot, self.stat("split_radius"), self.stat("fill_time"), 0,
                               self.arc(spot), split=split, size=self.stat("shell_size"), color=SHELL_COLOR)
