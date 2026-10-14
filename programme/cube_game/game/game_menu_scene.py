"""
The game menu between runs (Play in the main menu leads here). Left: the ship as it will start the next run. Right:
the chosen level and four tabs: the levels (level_panel.py – every level with indicators of what's coming), the
loadout (which weapon in which slot, loadout_panel.py), and where cores are spent (only here): the skill tree
(skill_tree_panel.py) and the card shop with the card collection (card_panel.py) – that tab only appears once "Card
shop" is bought in the skill tree. Start begins a run, Back returns to the main menu.

Mouse: click a level, a tab, an upgrade (buys its next level), a card or a button – right click a card in the
collection for a small menu (sell). In the loadout, drag weapons onto the slots.
Keyboard: A/D or arrow keys change the level (only between unlocked ones), Tab goes to the next tab, Enter starts,
Esc goes back. A locked level shows what unlocks it.

Every time it opens, the difficulty files are read again (so changes to them show up right away); if something in
them is wrong, the problems are listed in red above the buttons.
"""

import pygame

from engine import Scene
from engine.context_menu import ContextMenu
from engine.desktop import work_area
from engine.ui import draw_panel, draw_text
from game import difficulty as difficulty_files
from game import settings, skill_tree
from game.card_panel import CardPanel
from game.card_shop import CardShop
from game.skill_tree_panel import SkillTreePanel
from game.difficulty import DIFFICULTIES, WARNINGS
from game.level_panel import LevelPanel
from game.loadout_panel import LoadoutPanel
from game.game_over_scene import format_time
from game.icons import CORE_COLOR, draw_core
from game.profile import Profile
from game.ship_shape import draw_ship

MARGIN = 24
LEFT_WIDTH = 260                    # ship column
RIGHT_LEFT = 320                    # level and tabs
PREVIEW_HEIGHT = 170
LEVEL_TOP = 94                      # the chosen level, above the tabs
TABS = (("levels", "Levels"), ("loadout", "Loadout"), ("tree", "Skill tree"), ("cards", "Cards"))
TAB_TOP = 168
TAB_SIZE = (150, 32)
TAB_GAP = 10
TREE_TOP = 214                      # the tabs' content starts here …
TREE_BOTTOM = 770                   # … and ends here (the skill tree is centred in between)
INFO_TOP = TREE_BOTTOM              # messages, hints and warnings: below the tabs' content
WARNING_LINES = 2                   # problems in the difficulty files shown at most (and how many more there are) …
WARNING_LENGTH = 80                 # … each cut to this many characters, so it fits
BACK_SIZE = (140, 44)
START_SIZE = (240, 52)
MESSAGE_TIME = 1500                 # milliseconds a message ("Not enough cores") stays visible

FILL = (24, 24, 30)
HOVER_FILL = (34, 34, 42)
LOCKED = (70, 70, 80)
TOO_EXPENSIVE = (200, 70, 70)
SUCCESS = CORE_COLOR
SELECTED_FILL = (255, 255, 255)
LINE = (50, 50, 58)
DIFFICULTY_LEFT_KEYS = (pygame.K_a, pygame.K_LEFT)
DIFFICULTY_RIGHT_KEYS = (pygame.K_d, pygame.K_RIGHT)
START_KEYS = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)


class GameMenuScene(Scene):
    def __init__(self, profile=None):
        super().__init__()
        difficulty_files.reload()
        self.profile = profile or Profile.load()
        if self.profile.difficulty not in DIFFICULTIES or not self.profile.difficulty_unlocked(self.profile.difficulty):
            self.profile.difficulty = difficulty_files.default_key()      # its file was removed or changed
        self.rect = pygame.Rect((0, 0), settings.GAME_MENU_WINDOW_SIZE)
        self.rect.center = work_area().center
        self.tab = "levels"
        self.card_panel = CardPanel(CardShop(self.profile), RIGHT_LEFT, TREE_TOP,
                                    self.rect.width - MARGIN - RIGHT_LEFT, self.show_message)
        area = (RIGHT_LEFT, TREE_TOP, self.rect.width - MARGIN - RIGHT_LEFT, TREE_BOTTOM - TREE_TOP)
        self.tree_panel = SkillTreePanel(self.profile, area)
        self.loadout_panel = LoadoutPanel(self.profile, area, self.show_message)
        self.level_panel = LevelPanel(self.profile, area)
        # what the mouse is on: ("difficulty", key) – a level –, ("tab", key), ("node", key), ("cards", what – see
        # CardPanel), ("loadout", what – see LoadoutPanel), "start", "back" or None
        self.hovered = None
        self.menu = None                        # the open context menu (right click on a card)
        self.message = ""
        self.message_color = settings.TEXT
        self.message_until = 0

    def enter(self):
        self.engine.grab_mouse(False)
        self.engine.move_window(self.rect)

    # --- layout (window coordinates) ---

    def tabs(self):
        """The tabs to show: (key, label) – the cards only once the card shop is bought."""
        return [(key, label) for key, label in TABS if key != "cards" or self.profile.owns(skill_tree.CARD_SHOP)]

    def tab_rects(self):
        width, height = TAB_SIZE
        return {key: pygame.Rect(RIGHT_LEFT + index * (width + TAB_GAP), TAB_TOP, width, height)
                for index, (key, _) in enumerate(self.tabs())}

    def back_rect(self):
        return pygame.Rect((MARGIN, self.rect.height - MARGIN - BACK_SIZE[1]), BACK_SIZE)

    def start_rect(self):
        rect = pygame.Rect((0, 0), START_SIZE)
        rect.bottomright = (self.rect.width - MARGIN, self.rect.height - MARGIN + 4)
        return rect

    def thing_at(self, position):
        for key, rect in self.tab_rects().items():
            if rect.collidepoint(position):
                return ("tab", key)
        if self.tab == "levels":
            key = self.level_panel.thing_at(position)
            if key is not None:
                return ("difficulty", key)
        elif self.tab == "tree":
            key = self.tree_panel.thing_at(position)
            if key is not None:
                return ("node", key)
        elif self.tab == "loadout":
            thing = self.loadout_panel.thing_at(position)
            if thing is not None:
                return ("loadout", thing)
        elif self.tab == "cards":
            thing = self.card_panel.thing_at(position)
            if thing is not None:
                return ("cards", thing)
        if self.start_rect().collidepoint(position):
            return "start"
        if self.back_rect().collidepoint(position):
            return "back"
        return None

    # --- actions ---

    def start(self):
        from game.play_scene import PlayScene      # imported here: PlayScene also imports this file
        self.engine.change_scene(PlayScene(self.profile))

    def back(self):
        from game.main_menu_scene import MainMenuScene
        self.engine.change_scene(MainMenuScene())

    def choose_difficulty(self, key):
        if not self.profile.difficulty_unlocked(key):
            self.show_message(self.unlock_hint(key), TOO_EXPENSIVE)
        elif key != self.profile.difficulty:
            self.profile.difficulty = key
            self.profile.save()

    def step_difficulty(self, step):
        keys = [key for key in DIFFICULTIES if self.profile.difficulty_unlocked(key)]
        self.choose_difficulty(keys[(keys.index(self.profile.difficulty) + step) % len(keys)])

    @staticmethod
    def unlock_hint(key):
        """E.g. "Survive 02:30 on A3 to unlock A4"."""
        requires = DIFFICULTIES[DIFFICULTIES[key].requires]
        return f"Survive {format_time(requires.goal)} on {requires.name} to unlock {DIFFICULTIES[key].name}"

    def buy(self, key):
        node = skill_tree.NODES_BY_KEY[key]
        profile = self.profile
        if profile.maxed(node):
            self.show_message("Already at its maximum", settings.TEXT_MUTED)
        elif not profile.unlocked(node):
            missing = [skill_tree.NODES_BY_KEY[key].name for key in node.requires if not profile.owns(key)]
            self.show_message(f"Unlock {' and '.join(missing)} first", TOO_EXPENSIVE)
        elif not profile.buy(node):
            self.show_message("Not enough cores", TOO_EXPENSIVE)
        elif node.max_level > 1:
            self.show_message(f"{node.name}: level {profile.level(key)}", SUCCESS)
        else:
            self.show_message(f"{node.name} unlocked!", SUCCESS)

    def show_message(self, text, color):
        self.message, self.message_color = text, color
        self.message_until = pygame.time.get_ticks() + MESSAGE_TIME

    # --- events ---

    def open_menu(self, thing, position):
        """Right click on a card: its context menu, if it has one."""
        found = self.card_panel.menu_items(thing)
        if found:
            title, items = found
            self.menu = ContextMenu(position, items, pygame.Rect((0, 0), self.rect.size), title)

    def handle_event(self, event):
        if self.menu is not None:
            used = self.menu.handle_event(event)
            if not self.menu.open:
                self.menu = None
                if event.type == pygame.MOUSEBUTTONUP:
                    self.hovered = self.thing_at(event.pos)     # the card under the mouse may be gone (sold)
            if used:
                return
        if self.tab == "loadout" and self.loadout_panel.handle_event(event):
            return
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.thing_at(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button in (1, 3):     # 3: right click (a card's menu)
            thing = self.thing_at(event.pos)
            if thing and thing[0] == "cards":
                if event.button == 1:
                    self.card_panel.click(thing[1])
                    self.hovered = self.thing_at(event.pos)     # the card under the mouse may have changed
                else:
                    self.open_menu(thing[1], event.pos)
            elif event.button != 1:
                pass
            elif thing == "start":
                self.start()
            elif thing == "back":
                self.back()
            elif thing and thing[0] == "difficulty":
                self.choose_difficulty(thing[1])
            elif thing and thing[0] == "tab":
                self.tab = thing[1]
            elif thing and thing[0] == "node":
                self.buy(thing[1])
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.back()
            elif event.key in START_KEYS:
                self.start()
            elif event.key == pygame.K_TAB:
                keys = [key for key, _ in self.tabs()]
                self.tab = keys[(keys.index(self.tab) + 1) % len(keys)] if self.tab in keys else keys[0]
                self.hovered = self.menu = None
            elif event.key in DIFFICULTY_LEFT_KEYS:
                self.step_difficulty(-1)
            elif event.key in DIFFICULTY_RIGHT_KEYS:
                self.step_difficulty(1)

    # --- drawing ---

    def draw(self, surface):
        panel = surface.get_rect()
        draw_panel(surface, panel, radius=0)
        draw_text(surface, "GAME MENU", 36, settings.TEXT, topleft=(MARGIN, 20))
        count = draw_text(surface, str(self.profile.cores), 34, settings.TEXT, topright=(panel.right - MARGIN, 22))
        draw_core(surface, (count.left - 16, count.centery - 1), 11)

        self.draw_ship_column(surface)
        self.draw_difficulty(surface)
        self.draw_tabs(surface)
        if self.tab == "levels":
            self.level_panel.draw(surface, self.hovered[1] if self.hovered and self.hovered[0] == "difficulty" else None)
        elif self.tab == "tree":
            self.tree_panel.draw(surface, self.hovered[1] if self.hovered and self.hovered[0] == "node" else None)
        elif self.tab == "loadout":
            self.loadout_panel.draw(surface, self.hovered[1] if self.hovered and self.hovered[0] == "loadout" else None)
        elif self.tab == "cards":
            self.card_panel.draw(surface, self.hovered[1] if self.hovered and self.hovered[0] == "cards" else None)
        self.draw_info(surface)
        self.draw_warnings(surface)
        self.draw_button(surface, self.back_rect(), "Back", 28, self.hovered == "back")
        self.draw_button(surface, self.start_rect(), "Start", 34, True, hovered=self.hovered == "start")
        draw_text(surface, "ENTER start  ·  ESC back  ·  A / D level  ·  TAB switch tab", 20, settings.TEXT,
                  alpha=settings.HINT_ALPHA * 2, midbottom=(panel.centerx, panel.bottom - 20))
        if self.menu is not None:
            self.menu.draw(surface)

    def draw_ship_column(self, surface):
        """The ship as the next run starts it – read from the same functions the run uses."""
        profile = self.profile
        ship = skill_tree.start_ship(profile, (0, 0))
        draw_text(surface, "YOUR SHIP", 22, settings.TEXT_MUTED, topleft=(MARGIN, 70))
        preview = pygame.Rect(MARGIN, 94, LEFT_WIDTH, PREVIEW_HEIGHT)
        pygame.draw.rect(surface, settings.BACKGROUND, preview, border_radius=6)
        pygame.draw.rect(surface, settings.TEXT_MUTED, preview, width=1, border_radius=6)
        aim = pygame.Vector2(pygame.mouse.get_pos()) - preview.center
        draw_ship(surface, preview.center, aim.normalize() if aim.length_squared() > 1 else (0, -1), 80, ship.color)

        dash, rocket = ship.abilities
        radar = skill_tree.start_radar(profile)
        difficulty = DIFFICULTIES[profile.difficulty]
        width, height = skill_tree.start_arena_size(profile, difficulty)
        best = profile.best_times.get(profile.difficulty)
        rows = [
            ("LMB", ship.weapons[0].name if ship.weapons[0] else "empty"),
            ("RMB", ship.weapons[1].name if ship.weapons[1] else "empty"),
            ("Energy", f"{ship.max_energy:g}  ·  +{ship.energy_regen:g}/s"),
            ("Armor", f"{ship.armor:g} px  ·  {ship.invulnerable_time:g} s"),
            (settings.ABILITY_KEY_NAMES[0], (dash.name + (f" ×{dash.max_charges}" if dash.max_charges > 1 else ""))
             if dash else None),
            (settings.ABILITY_KEY_NAMES[1], rocket.name if rocket else None),
            (settings.BUILD_KEY_NAME, f"Watchtower ×{ship.watchtower.max_count}" if ship.watchtower else None),
            ("Radar", f"every {radar.cooldown:g} s" if radar else None),
            ("Shop", "T" if profile.owns(skill_tree.SHOP) else None),
            ("Arena", f"{width} × {height}"),
            ("Start stars", str(ship.stars)),
            ("Active cards", f"{len(profile.active_cards())}/{profile.max_active_cards()}"
             if profile.owns(skill_tree.CARD_SHOP) else None),
            (f"Best ({difficulty.name})", format_time(best) if best else "–"),
        ]
        y = preview.bottom + 16
        for name, value in rows:
            draw_text(surface, name, 22, settings.TEXT_MUTED, topleft=(MARGIN, y))
            if value is None:
                draw_text(surface, "locked", 22, LOCKED, topright=(MARGIN + LEFT_WIDTH, y))
            else:
                draw_text(surface, value, 22, settings.TEXT, topright=(MARGIN + LEFT_WIDTH, y))
            pygame.draw.line(surface, LINE, (MARGIN, y + 20), (MARGIN + LEFT_WIDTH, y + 20))
            y += 27

    def draw_difficulty(self, surface):
        """The chosen level above the tabs: its name, description, goal and core chance (choose it in the Levels
        tab or with A / D)."""
        draw_text(surface, "LEVEL", 22, settings.TEXT_MUTED, topleft=(RIGHT_LEFT, 70))
        level = DIFFICULTIES[self.profile.difficulty]
        name = draw_text(surface, level.name, 44, settings.TEXT, topleft=(RIGHT_LEFT, LEVEL_TOP))
        draw_text(surface, level.description, 24, settings.TEXT_MUTED, midleft=(name.right + 16, name.centery + 2))
        chance = skill_tree.core_chance(self.profile, level)
        goal = "endless" if level.goal is None else f"goal {format_time(level.goal)}"
        if self.profile.cleared(level.key):
            goal = "cleared"
        draw_text(surface, f"{goal}  ·  core chance {chance * 100:.3g} %", 22, settings.TEXT,
                  midright=(self.rect.width - MARGIN, name.centery + 2))

    def draw_tabs(self, surface):
        for key, label in self.tabs():
            self.draw_button(surface, self.tab_rects()[key], label, 24, key == self.tab,
                             hovered=self.hovered == ("tab", key))

    def draw_info(self, surface):
        """The description of the upgrade under the mouse, or the last message."""
        center = (RIGHT_LEFT + self.rect.width - MARGIN) // 2
        if pygame.time.get_ticks() < self.message_until:
            draw_text(surface, self.message, 24, self.message_color, midtop=(center, INFO_TOP + 12))
        elif self.hovered and self.hovered[0] == "cards" and self.card_panel.info(self.hovered[1]):
            draw_text(surface, self.card_panel.info(self.hovered[1]), 22, settings.TEXT, midtop=(center, INFO_TOP + 12))
        elif self.tab == "levels":
            hovered = self.hovered[1] if self.hovered and self.hovered[0] == "difficulty" else None
            if hovered and not self.profile.difficulty_unlocked(hovered):
                draw_text(surface, self.unlock_hint(hovered), 22, settings.TEXT, midtop=(center, INFO_TOP + 12))
            else:
                draw_text(surface, "click a level to choose it  ·  survive its goal to unlock the next  ·  the run "
                                   "goes on after the goal", 20, settings.TEXT, alpha=settings.HINT_ALPHA * 2,
                          midtop=(center, INFO_TOP + 12))
        elif self.tab == "loadout":
            draw_text(surface, "drag a weapon onto a slot  ·  drag it off its slot to empty it  ·  both weapons share "
                               "the energy", 20, settings.TEXT, alpha=settings.HINT_ALPHA * 2,
                      midtop=(center, INFO_TOP + 12))
        elif self.tab == "cards":
            limit = self.profile.max_active_cards()
            apply = "card applies" if limit == 1 else "cards apply"
            draw_text(surface, f"buy cards with cores  ·  up to {limit} active {apply} at the start of every run", 20,
                      settings.TEXT, alpha=settings.HINT_ALPHA * 2, midtop=(center, INFO_TOP + 12))
        else:
            draw_text(surface, "click an upgrade to buy it  ·  point at one for details  ·  cores drop rarely from "
                               "killed enemies", 20,
                      settings.TEXT, alpha=settings.HINT_ALPHA * 2, midtop=(center, INFO_TOP + 12))

    def draw_warnings(self, surface):
        """Problems found in the difficulty files, in red, so a typo there doesn't go unnoticed."""
        if not WARNINGS:
            return
        lines = [line if len(line) <= WARNING_LENGTH else line[:WARNING_LENGTH - 1] + "…"
                 for line in WARNINGS[:WARNING_LINES]]
        if len(WARNINGS) > WARNING_LINES:
            lines[-1] += f"   (+{len(WARNINGS) - WARNING_LINES} more)"
        center = (RIGHT_LEFT + self.rect.width - MARGIN) // 2
        for index, line in enumerate(lines):
            draw_text(surface, line, 18, TOO_EXPENSIVE, midtop=(center, INFO_TOP + 40 + index * 18))

    @staticmethod
    def draw_button(surface, rect, label, size, selected, hovered=None):
        """Like the menu buttons: white when selected, an outline otherwise (brighter fill under the mouse)."""
        if selected:
            pygame.draw.rect(surface, SELECTED_FILL, rect, border_radius=6)
            draw_text(surface, label, size, settings.BACKGROUND, center=rect.center)
            if hovered:
                pygame.draw.rect(surface, CORE_COLOR, rect, width=3, border_radius=6)
            return
        if hovered:
            pygame.draw.rect(surface, HOVER_FILL, rect, border_radius=6)
        pygame.draw.rect(surface, settings.TEXT_MUTED, rect, width=2, border_radius=6)
        draw_text(surface, label, size, settings.TEXT, center=rect.center)
