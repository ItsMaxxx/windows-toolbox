"""
The "Skill tree" tab of the game menu: the whole tree as a graph (see skill_tree.py) – Shop in the middle, the branches
around it, each in its colour. The nodes are small circles with their level inside and a short name below; everything
else (description, price, what it needs) is in a tooltip next to the node under the mouse.

How a node looks tells its state:
  - bought to the maximum: filled with its branch's colour,
  - partly bought: its branch's colour as the ring,
  - can be bought now: a white ring (grey if there aren't enough cores),
  - needs other nodes first: dark grey.
A line to a node is in the branch's colour once the node it comes from is bought.

Only lays out and draws – buying is done by the game menu (it asks thing_at()).
"""

import pygame

from engine.ui import draw_text, wrap
from game import settings
from game.icons import CORE_COLOR, draw_core
from game.skill_tree import BRANCHES, NODES, NODES_BY_KEY, effect_text

UNIT = (78, 72)                     # pixels per grid unit (x, y) – node positions are in grid units
RADIUS = 18                         # a node's circle …
BIG_RADIUS = 24                     # … and of the first node of a branch (an unlock: a weapon, an ability, …)
HIT_REACH = 6                       # the mouse counts as on a node this many pixels outside its circle, too
LABEL_SIZE = 18
TOOLTIP_WIDTH = 280
TOOLTIP_PADDING = 12
TOOLTIP_GAP = 14                    # between the node and its tooltip

FILL = (24, 24, 30)
HOVER_FILL = (40, 40, 50)
TOOLTIP_FILL = (12, 12, 16)
LOCKED = (70, 70, 80)
LINE = (45, 45, 52)
TOO_EXPENSIVE = (200, 70, 70)


def dimmed(color, factor):
    return [round(channel * factor) for channel in color]


def full_name(node):
    """E.g. "Gun: Damage" – the name alone is the same in many branches."""
    return node.name if is_big(node) or node.branch == "ship" else f"{BRANCHES[node.branch].name}: {node.name}"


def is_big(node):
    """Drawn bigger and named in its branch's colour: the middle (Shop) and the first node of a branch that has no
    label of its own – it unlocks something (a weapon, an ability, …) and names the branch."""
    if not node.requires:
        return True
    return BRANCHES[node.branch].label_at is None and all(NODES_BY_KEY[key].branch != node.branch
                                                          for key in node.requires)


class SkillTreePanel:
    def __init__(self, profile, rect):
        """rect: the tab's area in the game menu's window – the tree is centred in it."""
        self.profile = profile
        self.rect = pygame.Rect(rect)

    # --- layout ---

    def center(self, node_or_position):
        """A node's (or a grid position's) middle in window pixels."""
        x, y = getattr(node_or_position, "position", node_or_position)
        return pygame.Vector2(self.rect.centerx + x * UNIT[0], self.rect.centery + y * UNIT[1])

    @staticmethod
    def radius(node):
        return BIG_RADIUS if is_big(node) else RADIUS

    def thing_at(self, position):
        """The key of the node under position, or None."""
        for node in NODES:
            if self.center(node).distance_to(position) <= self.radius(node) + HIT_REACH:
                return node.key
        return None

    # --- drawing ---

    def draw(self, surface, hovered):
        """hovered: the key of the node under the mouse (or None) – it gets a tooltip."""
        for node in NODES:                          # lines first, so the circles cover their ends
            for key in node.requires:
                self.draw_line(surface, NODES_BY_KEY[key], node)
        for branch in BRANCHES.values():
            if branch.label_at is not None:
                draw_text(surface, branch.name.upper(), 18, dimmed(branch.color, 0.8),
                          center=self.center(branch.label_at))
        for node in NODES:
            self.draw_node(surface, node, node.key == hovered)
        if hovered is not None:
            self.draw_tooltip(surface, NODES_BY_KEY[hovered])

    def draw_line(self, surface, parent, node):
        start, end = self.center(parent), self.center(node)
        if self.profile.owns(parent.key):
            color = dimmed(BRANCHES[node.branch].color, 0.9 if self.profile.owns(node.key) else 0.45)
        else:
            color = LINE
        pygame.draw.line(surface, color, start, end, 2)

    def draw_node(self, surface, node, hovered):
        profile = self.profile
        color = BRANCHES[node.branch].color
        center, radius = self.center(node), self.radius(node)
        level = profile.level(node.key)
        if profile.maxed(node):
            fill, ring, text = dimmed(color, 0.55), color, settings.TEXT
        elif not profile.unlocked(node):
            fill, ring, text = FILL, LOCKED, LOCKED
        elif level:
            fill, ring, text = FILL, color, settings.TEXT
        else:
            fill, ring = FILL, settings.TEXT if profile.can_buy(node) else settings.TEXT_MUTED
            text = settings.TEXT
        pygame.draw.circle(surface, HOVER_FILL if hovered and fill == FILL else fill, center, radius)
        pygame.draw.circle(surface, ring, center, radius, width=3 if hovered else 2)
        if node.max_level > 1:
            draw_text(surface, f"{level}/{node.max_level}", 18, text, center=center)
        elif level:
            pygame.draw.circle(surface, settings.TEXT, center, 4)        # bought: a dot in the middle

        label_size = 22 if is_big(node) else LABEL_SIZE
        label_color = color if is_big(node) and profile.unlocked(node) else text if text == LOCKED else \
            settings.TEXT_MUTED
        draw_text(surface, node.name, label_size, label_color, midtop=(center.x, center.y + radius + 3))

    def draw_tooltip(self, surface, node):
        """Name, branch and level, the description and what one level adds, then what it costs (or needs)."""
        profile = self.profile
        branch = BRANCHES[node.branch]
        width = TOOLTIP_WIDTH - 2 * TOOLTIP_PADDING
        lines = wrap(node.description, 20, width)
        effect = wrap(effect_text(node) or "", 20, width)
        level = profile.level(node.key)
        cost = profile.next_cost(node)
        missing = [full_name(NODES_BY_KEY[key]) for key in node.requires if not profile.owns(key)]
        height = TOOLTIP_PADDING * 2 + 26 + 22 + (len(lines) + len(effect)) * 19 + 8 + 22

        center, radius = self.center(node), self.radius(node)
        box = pygame.Rect(0, 0, TOOLTIP_WIDTH, height)
        box.midleft = (center.x + radius + TOOLTIP_GAP, center.y)
        if box.right > surface.get_width() - 8:                         # no room on the right: to the left
            box.midright = (center.x - radius - TOOLTIP_GAP, center.y)
        box.clamp_ip(surface.get_rect().inflate(-16, -16))
        pygame.draw.rect(surface, TOOLTIP_FILL, box, border_radius=8)
        pygame.draw.rect(surface, branch.color, box, width=2, border_radius=8)

        left, y = box.left + TOOLTIP_PADDING, box.top + TOOLTIP_PADDING
        draw_text(surface, node.name, 26, settings.TEXT, topleft=(left, y))
        if node.max_level > 1:
            draw_text(surface, f"{level}/{node.max_level}", 22, settings.TEXT, topright=(box.right - TOOLTIP_PADDING,
                                                                                         y + 2))
        y += 26
        draw_text(surface, branch.name, 18, branch.color, topleft=(left, y))
        y += 22
        for line in lines:
            draw_text(surface, line, 20, settings.TEXT_MUTED, topleft=(left, y))
            y += 19
        for line in effect:
            draw_text(surface, line, 20, settings.TEXT, topleft=(left, y))
            y += 19
        y += 8
        if cost is None:
            draw_text(surface, "OWNED" if node.max_level == 1 else "MAX", 20, CORE_COLOR, topleft=(left, y))
        elif missing:
            draw_text(surface, "needs " + ", ".join(missing), 20, TOO_EXPENSIVE, topleft=(left, y))
        else:
            draw_core(surface, (left + 7, y + 8), 8)
            color = settings.TEXT if profile.cores >= cost else TOO_EXPENSIVE
            label = "click to buy" if profile.cores >= cost else "not enough cores"
            price = draw_text(surface, str(cost), 24, color, topleft=(left + 20, y - 1))
            draw_text(surface, label, 18, settings.TEXT_MUTED, topleft=(price.right + 10, y + 2))
