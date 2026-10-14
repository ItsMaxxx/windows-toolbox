"""
The "Levels" tab of the game menu: every level as a button – one row per series (A1 … A6, B1 … B6, then Survival) –
and below them the details of the level under the mouse (or the chosen one): its hints, its numbers (arena, walls,
spawning, cores – at the start and where they go), which enemies come when, and its events.

Every button already shows small indicators of what's coming: a square in each enemy type's colour (evolutions with
their dark frame) and one icon per kind of event (swarms, waves of one type, harder hits, more HP, harder walls).
Locked levels show them too, only dimmed – so you can see what's ahead. A tick marks cleared levels.

Everything comes from the level files (data/difficulties/*.json): the hints are written there, the rest follows from
the enemies, evolutions, swarms and phases. Rows: a new row starts whenever the tens of "order" change (1–6: A,
11–16: B, 20: Survival) – or after COLUMNS levels.

Only lays out and draws – the game menu handles the clicks (thing_at gives the level under the mouse).
"""

from dataclasses import dataclass

import pygame

from engine.ui import draw_text, font, wrap
from game import settings, skill_tree
from game.difficulty import DIFFICULTIES, evolution_chance
from game.enemies.roster import ENEMY_TYPES, EVOLUTIONS, apply
from game.game_over_scene import format_time
from game.icons import (CORE_COLOR, draw_check, draw_damage_icon, draw_hp_icon, draw_notice_icon, draw_swarm_icon,
                        draw_wall_icon, draw_wave_icon)
from game.skins.skin import draw_tier_frame

COLUMNS = 6
BUTTON_HEIGHT = 74
GAP = 8
DETAILS_GAP = 18                    # between the last row of buttons and the details
ENEMY_ICON = 11                     # the enemy squares on a button …
ENEMY_ICON_GAP = 3
EVENT_ICON = 13                     # … and the event icons
EVENT_ICON_GAP = 7
DETAIL_ICON = 15                    # icons in the details
LINE_HEIGHT = 22
TIME_WIDTH = 104                    # the events' times ("01:30, 03:00")
LABEL_WIDTH = 70                    # the numbers' labels ("Walls")
HINT_WIDTH = 250                    # the details' columns: hints, enemies, events (the rest)
ENEMY_WIDTH = 330
COLUMN_GAP = 20

FILL = (24, 24, 30)
HOVER_FILL = (34, 34, 42)
SELECTED_FILL = (255, 255, 255)
LOCKED = (70, 70, 80)
DIM = 0.35                          # locked levels: their indicators this bright
CLEARED = (110, 220, 110)
DAMAGE_COLOR = (255, 90, 70)
HP_COLOR = (110, 220, 110)
WALL_COLOR = (175, 175, 190)
NOTICE_COLOR = (255, 215, 60)
EVENT_ICONS = {"swarm": draw_swarm_icon, "wave": draw_wave_icon, "damage": draw_damage_icon, "hp": draw_hp_icon,
               "walls": draw_wall_icon, "notice": draw_notice_icon}
DAMAGE_STATS = {"contact_damage", "shot_damage", "blast_damage"}


@dataclass(frozen=True)
class Event:
    time: float                     # seconds into the run
    end: float | None               # None: from then on
    kind: str                       # key in EVENT_ICONS
    text: str
    color: tuple


def dimmed(color, factor):
    return tuple(round(channel * factor) for channel in color)


def percent(chance):
    return f"{chance * 100:.3g} %"


def plural(key):
    """ "Snipers", "Artilleries" – the type's name with an s (a y after a consonant becomes ies)."""
    name = ENEMY_TYPES[key].name
    if name.endswith("y") and name[-2:-1].lower() not in "aeiou":
        return name[:-1] + "ies"
    return name + "s"


def change_text(operation, number, unit=""):
    """A phase's change as a short text: "×0.8", "+2 px/s", "= 3 s"."""
    if operation == "multiply":
        return f"×{number:g}"
    if operation == "add":
        return f"{number:+g}{unit}"
    return f"= {number:g}{unit}"


def numbers(level, profile):
    """[(label, value)] – the level's numbers at the start and where they go over time. Arena size and cores with the
    player's skill tree ("Bigger arena", "Core luck"), as the run gets them."""
    arena, spawning = level.arena, level.spawning
    arena_size = skill_tree.start_arena_size(profile, level)
    walls = f"{arena.shrink_speed:g} px/s"
    if arena.shrink_growth and arena.max_shrink_speed > arena.shrink_speed:
        reached = (arena.max_shrink_speed - arena.shrink_speed) / arena.shrink_growth * 60
        walls = f"{arena.shrink_speed:g} to {arena.max_shrink_speed:g} px/s by {format_time(reached)}"
    gap = f"every {spawning.start_interval:g} s"
    if spawning.interval_drop and spawning.min_interval < spawning.start_interval:
        reached = (spawning.start_interval - spawning.min_interval) / spawning.interval_drop
        gap = f"{spawning.start_interval:g} to {spawning.min_interval:g} s by {format_time(reached)}"
    return [("Arena", f"{arena_size[0]:g} × {arena_size[1]:g} px"),
            ("Walls", walls),
            ("Spawns", gap),
            ("First", f"after {spawning.first_spawn:g} s"),
            ("Cores", f"{percent(skill_tree.core_chance(profile, level))} per kill")]


def enemy_rows(level):
    """[(type key, first second it can come, note)] for every type that can come on level – in order of appearance.
    Evolutions only if their tier 1 type comes; their note says how likely ("8–20 % of Basics")."""
    first = {}
    for entry in level.enemies:
        first[entry.type] = min(first.get(entry.type, entry.after), entry.after)
    for swarms in level.swarms:
        first[swarms.type] = min(first.get(swarms.type, swarms.after), swarms.after)
    rows = [(key, after, "") for key, after in first.items()]
    for entry in level.evolutions:
        if entry.type not in first:
            continue                # its tier 1 type never comes, so it never evolves
        start = max(entry.after, first[entry.type])
        low = evolution_chance(entry, start)
        high = entry.max_chance if entry.growth else low
        chance = percent(low) if high <= low else f"{low * 100:.3g}–{percent(high)}"
        rows.append((EVOLUTIONS[entry.type], start, f"{chance} of {plural(entry.type)}"))
    return sorted(rows, key=lambda row: row[1])


def events(level):
    """Everything that happens on level besides single enemies coming, as Events in order of time: harder walls and more
    HP from the start, swarms, and every phase (one Event per kind of change in it)."""
    found = []
    if level.arena.armor:
        found.append(Event(0, None, "walls", f"Armored walls ({level.arena.armor:g} px)", WALL_COLOR))
    start_hp = sum(number for target, stat, operation, number in level.enemy_stats
                   if target == "all" and stat == "base_hp" and operation == "add")
    if start_hp:
        found.append(Event(0, None, "hp", f"All enemies {start_hp:+g} HP", HP_COLOR))
    for swarms in level.swarms:
        found.append(Event(swarms.after, None, "swarm", f"{ENEMY_TYPES[swarms.type].name} swarms",
                           ENEMY_TYPES[swarms.type].skin.color))
    for phase in level.phases:
        changes = phase_changes(phase)
        if not changes and phase.announce:
            changes = [("notice", phase.announce, NOTICE_COLOR)]
        for index, (kind, text, color) in enumerate(changes):
            # the phase's own announcement describes it best – for its first change
            found.append(Event(phase.start, phase.end, kind, phase.announce if phase.announce and index == 0 else text,
                               color))
    return sorted(found, key=lambda event: event.time)


def phase_changes(phase):
    """[(kind, text, colour)] – what a phase changes, one entry per kind."""
    changes = []
    raised = [key for key, operation, number in phase.weights
              if operation == "set" or (operation == "multiply" and number > 1) or (operation == "add" and number > 0)]
    raised += [key for key, _ in phase.spawn if key not in raised]
    faster = phase.spawn_interval and apply(1.0, *phase.spawn_interval) < 1     # shorter gaps than now
    gap = change_text(*phase.spawn_interval, " s") if phase.spawn_interval else ""     # on the time between enemies
    if raised:
        changes.append(("wave", "More " + " and ".join(plural(key) for key in raised)
                        + (f", spawns {gap}" if gap else ""), ENEMY_TYPES[raised[0]].skin.color))
    elif gap:
        changes.append(("wave", f"{'Faster' if faster else 'Slower'} spawns ({gap})", NOTICE_COLOR))
    for name, operation, number in phase.arena:
        if name == "armor":
            changes.append(("walls", f"Walls harden ({change_text(operation, number, ' px')})", WALL_COLOR))
        else:
            changes.append(("walls", f"Walls close in {change_text(operation, number, ' px/s')}", WALL_COLOR))
    if any(stat in DAMAGE_STATS for _, stat, _, _ in phase.enemy_stats):
        changes.append(("damage", "Enemies hit harder", DAMAGE_COLOR))
    hp = sum(number for _, stat, operation, number in phase.enemy_stats if stat == "base_hp" and operation == "add")
    if hp:
        changes.append(("hp", f"New enemies {hp:+g} HP", HP_COLOR))
    return changes


def draw_enemy_icon(surface, key, center, size, factor=1.0):
    """An enemy type as a small square in its colour – an evolution with its dark frame."""
    rect = pygame.Rect(0, 0, size, size)
    rect.center = center
    color = dimmed(ENEMY_TYPES[key].skin.color, factor)
    pygame.draw.rect(surface, color, rect)
    if ENEMY_TYPES[key].tier == 2:
        draw_tier_frame(surface, rect, color)


class LevelPanel:
    def __init__(self, profile, rect):
        """rect: the tab's area in the game menu's window."""
        self.profile = profile
        self.rect = pygame.Rect(rect)

    # --- layout ---

    def button_rects(self):
        width = (self.rect.width - (COLUMNS - 1) * GAP) // COLUMNS
        rects, row, column, tens = {}, 0, 0, None
        for key, level in DIFFICULTIES.items():
            if tens is not None and (level.order // 10 != tens or column == COLUMNS):
                row, column = row + 1, 0
            tens = level.order // 10
            rects[key] = pygame.Rect(self.rect.left + column * (width + GAP),
                                     self.rect.top + row * (BUTTON_HEIGHT + GAP), width, BUTTON_HEIGHT)
            column += 1
        return rects

    def details_top(self):
        return max(rect.bottom for rect in self.button_rects().values()) + DETAILS_GAP

    def thing_at(self, position):
        """The key of the level under position – or None."""
        return next((key for key, rect in self.button_rects().items() if rect.collidepoint(position)), None)

    # --- drawing ---

    def draw(self, surface, hovered):
        """hovered: the key of the level under the mouse (its details are shown) – or None (the chosen one's)."""
        for key, rect in self.button_rects().items():
            self.draw_button(surface, key, rect, key == hovered)
        self.draw_details(surface, hovered or self.profile.difficulty)

    def draw_button(self, surface, key, rect, hovered):
        level = DIFFICULTIES[key]
        unlocked = self.profile.difficulty_unlocked(key)
        selected = key == self.profile.difficulty
        if selected:
            pygame.draw.rect(surface, SELECTED_FILL, rect, border_radius=6)
            text = settings.BACKGROUND
        else:
            pygame.draw.rect(surface, HOVER_FILL if hovered else FILL, rect, border_radius=6)
            text = settings.TEXT if unlocked else LOCKED
        border = CORE_COLOR if selected and hovered else settings.TEXT_MUTED if unlocked else LOCKED
        if not selected or hovered:
            pygame.draw.rect(surface, border, rect, width=3 if selected else 2, border_radius=6)
        name = draw_text(surface, level.name, 30 if len(level.name) <= 3 else 26, text, topleft=(rect.left + 10,
                                                                                               rect.top + 7))
        if self.profile.cleared(key):
            draw_check(surface, (rect.right - 16, name.centery), CLEARED if not selected else (40, 150, 40), 14)
        elif level.goal is not None:
            draw_text(surface, format_time(level.goal), 20, text, alpha=170, midright=(rect.right - 10, name.centery))
        elif not unlocked:
            draw_text(surface, "locked", 20, text, midright=(rect.right - 10, name.centery))
        factor = 1.0 if unlocked else DIM
        x = rect.left + 10 + ENEMY_ICON / 2
        for enemy, _, _ in enemy_rows(level):
            if x > rect.right - 10:
                break
            draw_enemy_icon(surface, enemy, (x, rect.top + 43), ENEMY_ICON, factor)
            x += ENEMY_ICON + ENEMY_ICON_GAP
        x = rect.left + 10 + EVENT_ICON / 2
        shown = []
        for event in events(level):
            if event.kind in shown or x > rect.right - 10:
                continue
            shown.append(event.kind)
            color = WALL_COLOR if event.kind == "swarm" and selected else event.color
            EVENT_ICONS[event.kind](surface, (x, rect.top + 60), dimmed(color, factor), EVENT_ICON)
            x += EVENT_ICON + EVENT_ICON_GAP

    def draw_details(self, surface, key):
        level = DIFFICULTIES[key]
        left, right, top = self.rect.left, self.rect.right, self.details_top()
        pygame.draw.line(surface, settings.TEXT_MUTED, (left, top - DETAILS_GAP / 2), (right, top - DETAILS_GAP / 2))
        name = draw_text(surface, level.name, 34, settings.TEXT, topleft=(left, top))
        draw_text(surface, level.description, 22, settings.TEXT_MUTED, midleft=(name.right + 14, name.centery + 2))
        draw_text(surface, self.status(key), 22, settings.TEXT, midright=(right, name.centery + 2))

        top = name.bottom + 14
        hints_left = left
        enemies_left = hints_left + HINT_WIDTH + COLUMN_GAP
        events_left = enemies_left + ENEMY_WIDTH + COLUMN_GAP
        bottom = self.rect.bottom
        below = self.draw_hints(surface, level, hints_left, top, HINT_WIDTH, bottom)
        self.draw_numbers(surface, level, hints_left, below + 12, bottom)
        self.draw_enemies(surface, level, enemies_left, top, bottom)
        self.draw_events(surface, level, events_left, top, right - events_left, bottom)

    def status(self, key):
        """Goal, best time, cleared or what unlocks it – the line right of the level's name."""
        level = DIFFICULTIES[key]
        best = self.profile.best_times.get(key)
        best_text = f"best {format_time(best)}" if best else "not played yet"
        if not self.profile.difficulty_unlocked(key):
            return f"locked – clear {DIFFICULTIES[level.requires].name} first"
        if level.goal is None:
            return f"endless  ·  {best_text}"
        if self.profile.cleared(key):
            return f"cleared  ·  {best_text}"
        return f"goal: survive {format_time(level.goal)}  ·  {best_text}"

    @staticmethod
    def heading(surface, text, left, top):
        draw_text(surface, text, 20, settings.TEXT_MUTED, topleft=(left, top))
        return top + 24

    def draw_hints(self, surface, level, left, top, width, bottom):
        """Returns where the next thing below can go."""
        y = self.heading(surface, "WHAT TO EXPECT", left, top)
        for hint in level.hints:
            for index, line in enumerate(wrap(hint, 21, width - 14)):
                if y + LINE_HEIGHT > bottom:
                    return y
                if index == 0:
                    pygame.draw.circle(surface, settings.TEXT, (left + 4, y + 8), 3)
                draw_text(surface, line, 21, settings.TEXT, topleft=(left + 14, y))
                y += LINE_HEIGHT - 2
            y += 4
        return y

    def draw_numbers(self, surface, level, left, top, bottom):
        """The level's numbers – walls: how fast each edge moves in; "by 04:10": when the last value is reached."""
        y = self.heading(surface, "NUMBERS", left, top)
        for label, value in numbers(level, self.profile):
            if y + LINE_HEIGHT > bottom:
                return
            draw_text(surface, label, 19, settings.TEXT_MUTED, topleft=(left, y + 1))
            draw_text(surface, value, 20, settings.TEXT, topleft=(left + LABEL_WIDTH, y))
            y += LINE_HEIGHT - 2

    def draw_enemies(self, surface, level, left, top, bottom):
        y = self.heading(surface, "ENEMIES", left, top)
        rows = enemy_rows(level)
        for index, (key, after, note) in enumerate(rows):
            if y + 2 * LINE_HEIGHT > bottom and index < len(rows) - 1:
                draw_text(surface, f"+{len(rows) - index} more", 20, settings.TEXT_MUTED, topleft=(left, y))
                return
            draw_enemy_icon(surface, key, (left + DETAIL_ICON / 2, y + 8), DETAIL_ICON)
            name = draw_text(surface, ENEMY_TYPES[key].name, 21, settings.TEXT, topleft=(left + DETAIL_ICON + 10, y))
            detail = f"from {format_time(after)}" + (f"  ·  {note}" if note else "")
            draw_text(surface, detail, 19, settings.TEXT_MUTED, midleft=(name.right + 10, name.centery + 1))
            y += LINE_HEIGHT

    def draw_events(self, surface, level, left, top, width, bottom):
        """One line per event – the same thing happening again later (no end, same text) shares a line: "01:30,
        03:00"."""
        y = self.heading(surface, "EVENTS", left, top)
        lines = []                  # [event, [its times]]
        for event in events(level):
            same = next((line for line in lines if event.end is None and line[0].end is None
                         and (line[0].kind, line[0].text) == (event.kind, event.text)), None)
            if same:
                same[1].append(event.time)
            else:
                lines.append([event, [event.time]])
        if not lines:
            draw_text(surface, "none – just enemies", 21, settings.TEXT_MUTED, topleft=(left, y))
        for index, (event, times) in enumerate(lines):
            if y + 2 * LINE_HEIGHT > bottom and index < len(lines) - 1:
                draw_text(surface, f"+{len(lines) - index} more", 20, settings.TEXT_MUTED, topleft=(left, y))
                return
            EVENT_ICONS[event.kind](surface, (left + DETAIL_ICON / 2, y + 8), event.color, DETAIL_ICON)
            if event.end is not None:
                when = f"{format_time(event.time)}–{format_time(event.end)}"
            else:
                when = ", ".join(format_time(time) for time in times[:2]) + (" …" if len(times) > 2 else "")
            draw_text(surface, when, 19, settings.TEXT_MUTED, topleft=(left + DETAIL_ICON + 10, y + 1))
            text_left = left + DETAIL_ICON + 10 + TIME_WIDTH
            text = event.text
            while len(text) > 4 and font(21).size(text)[0] > left + width - text_left:
                text = text[:-2] + "…"
            draw_text(surface, text, 21, settings.TEXT, topleft=(text_left, y))
            y += LINE_HEIGHT
