"""
The scene where the game is played: the window keeps shrinking, the ship shoots its edges to push them back out,
enemies come in from the desktop. Getting hit squeezes the window. Once it's squeezed down to the ship, the run is
over (game over screen).

What the run starts with comes from the profile: the difficulty and the skill tree (shop, abilities, bonuses – see
skill_tree.py). Killed enemies drop stars (only with the shop unlocked) and, rarely, a core; cores are saved right
away, so they're kept even if the run is left through the pause menu. Surviving the level's goal clears it and unlocks
the next level – saved right then, with a notice on screen; the run goes on until the ship is crushed. Phases of the
level that announce themselves ("Snipers incoming!") get a notice, too.

Watchtowers (B, once unlocked): thrown out from the ship, each one gets its own window (Engine.open_view) that shows
the world around it – draw_view() draws it. They can't be hurt but stand only for a while, and enemies in a tower's
window take more damage (game/buildings/watchtower.py). The radar (once
unlocked, game/radar.py) opens a window of its own over enemies out of sight now and then.

The field (game/field.py): the arena plus the extra windows connected to it. Shots, blasts, the mouse, what counts
as seen, where enemies appear – all of it asks the field, so an extra window works like part of the arena (only the
ship stays in the arena). The extra windows lie on top of the main window, so it all looks like one field.

States: PLAYING, PAUSED (Esc: pause menu), INVENTORY (Tab) and SHOP (T). Outside PLAYING nothing moves, the mouse
is free and the window shows only the menu/inventory/shop: it takes on the panel's size, centred on the arena. On resume it snaps
back to the arena, which hasn't changed in the meantime. Leaving the window (Alt+Tab, clicking elsewhere) pauses the
game, too.
"""

import math
import random

import pygame

from engine import Scene
from engine.collision import close, nearby_pairs, push_apart
from engine.desktop import Desktop
from engine.key_overlay import KeyOverlay
from engine.sprite_cache import SpriteCache
from engine.ui import draw_text
from game import inventory, pause_menu, settings, shop_panel, skill_tree
from game.ability_bar import AbilityBar
from game.arena import Arena
from game.buildings.watchtower import Watchtower, values as watchtower_values
from game.core_pickup import CorePickup
from game.difficulty import DIFFICULTIES, next_difficulty
from game.field import Field
from game.enemies.roster import ENEMY_TYPES, EnemyRoster
from game.enemies.spawner import Spawner, distance_to_rect
from game.artillery_strike import ArtilleryStrike
from game.laser_beam import LaserBeam
from game.effects.artillery_blast import ArtilleryBlast
from game.effects.burning_ground import BurningGround
from game.effects.explosion import Explosion
from game.effects.slow_field import SlowField
from game.effects.spark import Spark
from game.hud import Hud
from game.icons import draw_swarm_icon
from game.inventory import Inventory
from game.pause_menu import PauseMenu
from game.points import Points
from game.shop import Shop
from game.shop_panel import ShopPanel
from game.star_pickup import StarPickup

PLAYING, PAUSED, INVENTORY, SHOP = "playing", "paused", "inventory", "shop"
PANEL_SIZES = {PAUSED: pause_menu.SIZE, INVENTORY: inventory.SIZE, SHOP: shop_panel.SIZE}
MARKER_INSET = 8                # off-screen markers: distance from the window's edge …
MARKER_RADIUS = 4               # … and size
SWARM_MARKER_INSET = 16         # a swarm's marker: distance from the window's edge …
SWARM_MARKER_SIZES = (12, 30)   # … size far away and right at the window …
SWARM_MARKER_FAR = 900          # … counts as far away from this many pixels beyond the window
NOTICE_TIME = 4.0               # seconds a notice ("… unlocked", a phase's announcement) stays on screen
NOTICE_COLOR = (255, 215, 60)
PHASE_COLOR = (255, 110, 80)
SHORT_NOTICE_TIME = 1.5         # seconds for small notices ("A watchtower costs 25 stars")
LOOKOUT_MARGIN = 14             # a Pusher's window: this much around its body …
LOOKOUT_BORDER = (150, 50, 50)  # … with a red frame, so it's clearly the enemy's
TOWER_BACKGROUND = (12, 12, 14) # a watchtower's window outside the arena: almost black, a hint of grey …
RADAR_BACKGROUND = (5, 11, 17)  # … the radar's: a hint of blue – just enough to tell them apart from the arena
SEPARATION_PASSES = (2, 8)      # how often per tick touching enemies are pushed apart (more: crowds overlap less) …
SEPARATION_BUDGET = 4000        # … as often as fits into this many pair checks – huge crowds get fewer passes
ENEMY_GAP = 3                   # pixels between touching enemies, so a crowd doesn't look like one big block
SEPARATION_REACH = 6            # pairs further apart than gap + this are skipped for the rest of the tick
FIRE_BUTTON = 0                 # the left mouse button fires the active weapon (index in get_pressed) …
SWITCH_BUTTON = 2               # … the right one switches weapons (settings.WEAPON_SWITCH_BUTTON, shown lit)

# W on top, A S D below – like on the keyboard
MOVEMENT_KEYS = [("W", pygame.K_w, 1, 0), ("A", pygame.K_a, 0, 1), ("S", pygame.K_s, 1, 1), ("D", pygame.K_d, 2, 1)]


def key_layout(ship):
    """The key display: W A S D, below them the keys of the abilities the ship has (SHIFT, SPACE, B)."""
    layout = list(MOVEMENT_KEYS)
    for slot, (keys, name, column) in enumerate(zip(settings.ABILITY_KEYS, settings.ABILITY_KEY_NAMES, (0, 2))):
        if ship.abilities[slot] is not None:
            layout.append((name, keys, column, 2, 2))
    if ship.watchtower is not None:
        layout.append((settings.BUILD_KEY_NAME, settings.BUILD_KEYS, 4, 2))
    return layout


class PlayScene(Scene):
    def __init__(self, profile):
        super().__init__()
        self.profile = profile
        self.difficulty = DIFFICULTIES[profile.difficulty]
        self.desktop = Desktop.current(profile.settings["all_monitors"])     # every monitor's usable area
        rules = self.difficulty.arena
        self.arena = Arena(self.desktop, skill_tree.start_arena_size(profile, self.difficulty), rules.shrink_speed,
                           rules.shrink_growth, rules.max_shrink_speed, rules.armor, rules.push_falloff)
        self.ship = skill_tree.start_ship(profile, self.arena.rect.center)
        self.arena.ship_size = self.ship.size
        self.shop_unlocked = profile.owns(skill_tree.SHOP)
        self.core_chance = skill_tree.core_chance(profile, self.difficulty)
        self.radar = skill_tree.start_radar(profile)            # None without the radar
        self.projectiles = []                   # the player's shots
        self.enemies = []
        self.enemy_projectiles = []
        self.strikes = []                       # artillery shells in the air (a circle filling where they land)
        self.beams = []                         # laser beams while they're on
        self.roster = EnemyRoster(self.difficulty)          # the enemies' values on this difficulty, buffs on all
        self.spawner = Spawner(self.desktop, self.difficulty, self.roster)
        self.explosions = []                    # effects: explosions, blasts (only drawn, they do nothing)
        self.burning = []                       # burning ground left by rockets – hurts the enemies in it
        self.slow_fields = []                   # left by mines – slows the enemies in it
        self.pickups = []                       # stars and cores dropped by killed enemies
        self.towers = []                        # watchtowers – in the air or standing
        self.points = Points(skill_tree.start_finds(profile))    # points of interest out there (game/points.py)
        self.ui_layer = None                    # this frame's HUD etc. for the extra windows: (main window, surface)
        self.ui_surface = None                  # the transparent surface it's drawn on (kept between frames)
        self.outlines = SpriteCache(16)         # the extra windows' borders (draw_outline) – big, so only a few
        self.elapsed = 0.0                      # seconds played (not counting pauses)
        self.kills = 0
        self.cores = 0                          # cores collected in this run (already added to the profile)
        upcoming = next_difficulty(profile.difficulty)
        # the level this run will unlock once it has lasted the goal – None if there's none (left)
        self.unlocks = upcoming if upcoming and not profile.difficulty_unlocked(upcoming) else None
        self.unlocked = None                    # set once it happened in this run
        self.cleared = False                    # the goal was reached in this run
        self.first_clear = not profile.cleared(profile.difficulty)    # … and never before – only then it's announced
        self.notices = []                       # on screen at the top: [text, colour, seconds left]
        self.ability_bar = AbilityBar()
        self.hud = Hud()
        self.shop = Shop(self.ship)
        self.shop_panel = ShopPanel(self.shop)
        self.key_overlay = KeyOverlay(key_layout(self.ship), settings.KEY_OVERLAY_INSET,
                                      profile.settings["key_display"], mouse_buttons=(FIRE_BUTTON, SWITCH_BUTTON) if all(self.ship.weapons) else (FIRE_BUTTON,))
        self.pause_menu = PauseMenu(resume=self.resume, game_menu=self.to_game_menu, quit_game=self.quit)
        self.inventory = Inventory()
        self.state = PLAYING

    def enter(self):
        self.set_state(PLAYING)

    def set_state(self, state):
        self.state = state
        if state == PAUSED:
            self.pause_menu.open()
        for view in self.extra_views():             # the extra windows only show while playing
            view.hidden = state != PLAYING
        self.engine.grab_mouse(state == PLAYING)
        self.engine.move_window(self.window_rect())

    def window_rect(self):
        """Playing: exactly the arena. Paused/inventory: just the panel, centred on the arena (and kept on the monitor
        the arena's centre is on)."""
        arena = self.arena.window_rect()
        if self.state == PLAYING:
            return arena
        panel = pygame.Rect((0, 0), PANEL_SIZES[self.state])
        panel.center = arena.center
        return panel.clamp(self.desktop.area_at(arena.center))

    # --- menu actions ---

    def resume(self):
        self.set_state(PLAYING)

    def to_game_menu(self):
        from game.game_menu_scene import GameMenuScene     # imported here: the game menu also imports this file
        self.engine.change_scene(GameMenuScene(self.profile))

    def game_over(self):
        """The ship is crushed: remember the time, then the game over screen – centred where the arena was."""
        from game.game_over_scene import GameOverScene, RunResult     # imported here: it also imports this file
        new_best = self.profile.record(self.elapsed)
        self.profile.save()
        result = RunResult(self.elapsed, self.kills, self.cores, self.profile.difficulty, new_best, self.unlocked,
                           self.cleared and self.first_clear)
        self.engine.change_scene(GameOverScene(self.profile, result, self.arena.rect.center))

    def quit(self):
        self.engine.stop()

    # --- events, logic, drawing ---

    def handle_event(self, event):
        self.key_overlay.handle_event(event)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.set_state(PAUSED if self.state == PLAYING else PLAYING)
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_TAB and self.state in (PLAYING, INVENTORY):
            self.set_state(INVENTORY if self.state == PLAYING else PLAYING)
        elif (event.type == pygame.KEYDOWN and event.key == pygame.K_t and self.state in (PLAYING, SHOP)
              and self.shop_unlocked):
            self.set_state(SHOP if self.state == PLAYING else PLAYING)
        elif event.type == pygame.WINDOWFOCUSLOST and self.state == PLAYING:
            self.set_state(PAUSED)
        elif self.state == PLAYING and (event.type == pygame.MOUSEWHEEL or event.type == pygame.MOUSEBUTTONDOWN
                                        and event.button == settings.WEAPON_SWITCH_BUTTON):
            self.ship.switch_weapon()                   # also while stunned – it's no action
        elif event.type == pygame.KEYDOWN and self.state == PLAYING and self.ship.stunned:
            pass                                        # stunned: no abilities, no towers
        elif event.type == pygame.KEYDOWN and self.state == PLAYING:
            if event.key in settings.BUILD_KEYS:
                self.throw_watchtower()
            for slot, keys in enumerate(settings.ABILITY_KEYS):
                if event.key in keys:
                    self.projectiles += self.ship.use_ability(slot, self.engine.mouse_position())
        elif self.state == PAUSED:
            self.pause_menu.handle_event(event)
        elif self.state == SHOP:
            self.shop_panel.handle_event(event)

    def update(self, dt):
        if self.state != PLAYING:
            return
        self.elapsed += dt
        for notice in self.notices:
            notice[2] -= dt
        self.notices = [notice for notice in self.notices if notice[2] > 0]
        if not self.cleared and self.difficulty.goal is not None and self.elapsed >= self.difficulty.goal:
            self.clear_level()
        phases = self.spawner.active_phases()
        self.arena.changes = [change for phase in phases for change in phase.arena]
        self.arena.breathe(phases)
        self.arena.update(dt)
        self.ship.update(dt, self.engine.mouse_position())
        self.arena.contain(self.ship)
        if self.arena.crushed(self.ship):
            self.game_over()
            return

        if pygame.mouse.get_pressed()[FIRE_BUTTON] and not self.ship.stunned:
            self.projectiles += self.ship.fire()

        self.roster.update(dt)
        field = self.field()
        self.engine.confine_mouse(field.rects)          # the mouse may go anywhere in the field
        new = self.spawner.update(dt, self.arena.rect, field.sight[1:])
        for enemy in new:
            enemy.arena, enemy.spawner = self.arena, self.spawner   # the Pusher shoves it, the Living Window spawns
        self.enemies += new
        self.lure_enemies()
        self.slow_enemies(dt)
        for text in self.spawner.announcements:
            self.notices.append([text, PHASE_COLOR, NOTICE_TIME])
        self.spawner.announcements.clear()
        for enemy in self.enemies[:]:                   # [:] – a copy, because spawned enemies are added
            for attack in enemy.update(dt, self.ship):
                if isinstance(attack, ArtilleryStrike):
                    self.strikes.append(attack)
                elif isinstance(attack, LaserBeam):
                    self.beams.append(attack)
                else:
                    self.enemy_projectiles.append(attack)
            if not enemy.seen and field.sees(enemy.rect):
                enemy.seen = True                       # the player has had it in view
            self.enemies += enemy.spawned
            enemy.spawned.clear()
        for enemy in self.enemies:
            if enemy.commands:
                enemy.command(self.enemies)             # a Commander's aura
        self.separate_enemies()
        self.update_towers(dt)
        self.expose_enemies()
        self.update_radar(dt)
        self.points.update(dt, self)

        # effects on shots in flight (slowing areas, deflecting enemies, …) go here – before projectile.update()
        self.update_player_shots(dt)
        self.update_enemy_shots(dt)
        self.update_strikes(dt)
        self.update_beams(dt)
        self.update_burning(dt)
        for enemy in self.enemies:
            if enemy.rect.colliderect(self.ship.rect) and enemy.stat("contact_damage"):
                if self.hit_ship(enemy.stat("contact_damage")):
                    enemy.on_hit_ship(self.ship)        # e.g. the shield's dash knocks it back

        for enemy in self.enemies:
            if not enemy.alive:
                self.kills += 1
                self.explosions.append(Explosion(enemy.center, enemy.size * 1.6, enemy.color))
                if enemy.drops_loot:
                    self.drop_loot(enemy.center)
        for enemy in self.enemies:
            if not enemy.alive and getattr(enemy, "view", None) is not None:
                self.engine.close_view(enemy.view)      # a Pusher's or Living Window's window
        self.enemies = [enemy for enemy in self.enemies if enemy.alive]
        self.update_lookouts()

        for pickup in self.pickups:
            pickup.update(dt, self.ship)
        collected = [pickup for pickup in self.pickups if pickup.rect.colliderect(self.ship.rect)]
        for pickup in collected:
            if pickup.currency == "cores":
                self.cores += 1
                self.profile.cores += 1
            else:
                self.ship.stars += 1
        if any(pickup.currency == "cores" for pickup in collected):
            self.profile.save()
        self.pickups = [pickup for pickup in self.pickups if pickup not in collected]

        for explosion in self.explosions:
            explosion.update(dt)
        self.explosions = [explosion for explosion in self.explosions if not explosion.done]

        self.engine.move_window(self.window_rect())

    def clear_level(self):
        """The goal is reached: the time counts right now (saved), so leaving the run afterwards keeps the unlock. The
        run goes on. "… CLEARED" only the first time the level is cleared, "… UNLOCKED" whenever something unlocks."""
        self.profile.record(self.elapsed)
        self.profile.save()
        self.cleared = True
        parts = [f"{self.difficulty.name.upper()} CLEARED"] if self.first_clear else []
        if self.unlocks:
            self.unlocked, self.unlocks = self.unlocks, None
            parts.append(f"{DIFFICULTIES[self.unlocked].name.upper()} UNLOCKED")
        if parts:
            self.notices.append(["  ·  ".join(parts), NOTICE_COLOR, NOTICE_TIME])

    def notify(self, text):
        """A small notice for a moment – the same text again only restarts it."""
        for notice in self.notices:
            if notice[0] == text:
                notice[2] = SHORT_NOTICE_TIME
                return
        self.notices.append([text, settings.TEXT_MUTED, SHORT_NOTICE_TIME])

    def throw_watchtower(self):
        """B: a watchtower flies from the ship towards the mouse, throw_range far (kept on a monitor) – if the ship
        has the kit, may have another tower standing and has the stars for it."""
        kit = self.ship.watchtower
        if kit is None:
            return
        if len(self.towers) >= kit.max_count:
            self.notify(f"All watchtowers are standing ({len(self.towers)}/{kit.max_count})")
            return
        if self.ship.stars < kit.price:
            self.notify(f"A watchtower costs {kit.price} stars")
            return
        self.ship.stars -= kit.price
        kit.bought += 1
        start = pygame.Vector2(self.ship.rect.center)
        direction = self.engine.mouse_position() - start
        direction = direction.normalize() if direction.length_squared() > 1 else pygame.Vector2(self.ship.aim)
        stats = watchtower_values()
        target = start + direction * stats["throw_range"]
        area = self.desktop.area_at(target)
        inner = area.inflate(-stats["size"], -stats["size"])           # the whole tower on the monitor
        target = (min(max(target.x, inner.left), inner.right), min(max(target.y, inner.top), inner.bottom))
        self.towers.append(Watchtower(kit, start, target))

    def update_towers(self, dt):
        """Watchtowers fly and land (their window opens, its rect is their area). Once their lifetime is over they
        vanish and their window closes."""
        for tower in self.towers:
            if tower.update(dt):
                tower.view = self.engine.open_view()
            if not tower.landed:
                continue
            tower.area = tower.vision_rect(self.desktop.area_at(tower.rect.center))
            if tower.view is not None:
                tower.view.rect = tower.area
        for tower in self.towers:
            if not tower.alive:
                self.explosions.append(Explosion(tower.center, tower.rect.width * 2.5, tower.color))
                if tower.view is not None:
                    self.engine.close_view(tower.view)
        self.towers = [tower for tower in self.towers if tower.alive]

    def update_lookouts(self):
        """Every Pusher and Living Window on a monitor gets a small window of its own that follows it – out there it's
        seen, but it's no part of the field (Field lookouts)."""
        for enemy in self.enemies:
            if not hasattr(enemy, "view"):
                continue
            rect = pygame.Rect(enemy.body.inflate(2 * LOOKOUT_MARGIN, 2 * LOOKOUT_MARGIN))
            if enemy.view is None and self.desktop.contains(rect.center):
                enemy.view = self.engine.open_view()
            if enemy.view is not None:
                enemy.view.rect = rect.clamp(self.desktop.area_at(rect.center))

    def lookouts(self):
        """The windows of the Pushers and Living Windows."""
        return [enemy.view for enemy in self.enemies if getattr(enemy, "view", None) is not None]

    def expose_enemies(self):
        """Enemies in a standing watchtower's area take its damage_bonus percent more damage this tick (Enemy.
        damage_factor) – the biggest bonus counts, towers don't stack."""
        areas = [(tower.area, tower.values["damage_bonus"]) for tower in self.towers if tower.area is not None]
        for enemy in self.enemies:
            bonus = max((bonus for area, bonus in areas if area.colliderect(enemy.rect)), default=0)
            enemy.damage_factor = 1 + bonus / 100

    def lure_enemies(self):
        """Melee enemies near a standing watchtower – within its lure_range and closer to it than to the ship – go for
        the tower instead of the ship."""
        standing = [tower for tower in self.towers if tower.landed]
        ship = pygame.Vector2(self.ship.rect.center)
        for enemy in self.enemies:
            if not enemy.melee:
                continue
            enemy.lure = None
            if not standing:
                continue
            center = enemy.center
            tower = min(standing, key=lambda tower: center.distance_squared_to(tower.center))
            distance = center.distance_to(tower.center)
            if distance <= tower.values["lure_range"] and distance < center.distance_to(ship):
                enemy.lure = tower

    def drop_loot(self, position):
        """A killed enemy's drop: a star if the shop is unlocked, and with core_chance a core next to it."""
        if self.shop_unlocked:
            self.pickups.append(StarPickup(position))
        if random.random() < self.core_chance:
            self.pickups.append(CorePickup(pygame.Vector2(position) + (14, 0) if self.shop_unlocked else position))

    def separate_enemies(self):
        """Enemies can't overlap: every touching pair is pushed apart (ENEMY_GAP between them), the heavier one moves
        less. That's also how they shove each other – a charging Charger rams the others out of its way."""
        solid = [enemy for enemy in self.enemies if enemy.solid]     # the Pusher walks through everything
        if not solid:
            return
        cell_size = max(enemy.size for enemy in solid) + ENEMY_GAP
        reach = ENEMY_GAP + SEPARATION_REACH        # filtered once, so the passes only go through pairs that can touch
        pairs = [(a.rect, b.rect, a.mass, b.mass, ENEMY_GAP) for a, b in nearby_pairs(solid, cell_size)
                 if close(a.rect, b.rect, reach)]
        for tower in self.towers:                   # standing towers are solid: enemies are pushed out, never them
            if tower.landed:
                pairs += [(tower.rect, enemy.rect, math.inf, enemy.mass, 0) for enemy in solid
                          if close(tower.rect, enemy.rect, reach)]
        fewest, most = SEPARATION_PASSES
        passes = min(most, max(fewest, SEPARATION_BUDGET // max(len(pairs), 1)))
        for _ in range(passes):                 # in a crowd, pushing one apart pushes it into the next
            for pair in pairs:
                push_apart(*pair)

    def update_radar(self, dt):
        """The radar opens its window over enemies out of sight (not in the arena or another extra window) and
        closes it again after its duration."""
        if self.radar is None:
            return
        hidden = [point.position for point in self.points.points if not point.revealed]
        change = self.radar.update(dt, self.enemies, self.field().sight, self.desktop, hidden)
        if change == "open":
            self.radar.view = self.engine.open_view()
            if self.radar.view is not None:
                self.radar.view.rect = pygame.Rect(self.radar.rect)
        elif change == "close" and self.radar.view is not None:
            self.engine.close_view(self.radar.view)
            self.radar.view = None

    def update_player_shots(self, dt):
        """Player shots end on an enemy (damage), on a shield (blocked: a spark, nothing else), at the field's wall
        (push the arena edge – see Field.wall_hit) or at their target. Shots with a blast radius explode at their end
        instead – also on a shield: blasts hurt from every side. A shot always either hits, is blocked or pushes.

        Piercing shots (the cannon) fly on through as many enemies as they may pierce, hurting each fully; if one
        reaches the wall after that, it pushes less (Projectile.wall_push). Hits count along the whole way a shot flew
        this tick, so fast shots (the laser) can't jump past small enemies."""
        field = self.field()
        shielded = [enemy for enemy in self.enemies if enemy.shielded and enemy.alive]
        alive = [enemy for enemy in self.enemies if enemy.alive]
        rects = [enemy.rect for enemy in alive]
        for projectile in self.projectiles[:]:          # [:] – a copy, because hits remove from the list
            projectile.update(dt)
            shield = next((e for e in shielded if e not in projectile.pierced and e.blocks(projectile)), None)
            enemy = shield or self.first_hit(projectile, alive, rects)
            while enemy and not shield and not projectile.stats.blast_radius and projectile.can_pierce:
                enemy.take_damage(projectile.stats.damage)
                projectile.pierced.append(enemy)        # through it – flies on, maybe into the next one right away
                enemy = self.first_hit(projectile, alive, rects)
            side = field.wall_hit(projectile)
            if not (enemy or side or projectile.arrived):
                continue
            self.projectiles.remove(projectile)
            if projectile.stats.blast_radius:
                self.explode(projectile)
            elif shield:
                self.explosions.append(Spark(projectile.rect.center, -projectile.direction))
            elif enemy:
                enemy.take_damage(projectile.stats.damage)
            elif side:
                self.arena.push(side, projectile.wall_push)

    @staticmethod
    def first_hit(projectile, enemies, rects):
        """The first enemy (still alive, not pierced yet) the shot touched on this tick's way – or None. rects: the
        enemies' rects, for a quick check of which ones are near the way at all."""
        near = [enemies[index] for index in projectile.sweep().collidelistall(rects)]
        touched = [enemy for enemy in near if enemy.alive and enemy not in projectile.pierced
                   and projectile.touches(enemy.rect)]
        return min(touched, key=lambda enemy: enemy.center.distance_squared_to(projectile.previous), default=None)

    def update_enemy_shots(self, dt):
        """Enemy shots fly through the window's edges (they often come from outside) and through watchtowers; they end
        on the ship or when they leave the desktop."""
        for projectile in self.enemy_projectiles[:]:
            projectile.update(dt)
            if projectile.rect.colliderect(self.ship.rect):
                self.hit_ship(projectile.stats.damage)
                self.enemy_projectiles.remove(projectile)
            elif not self.desktop.bounds.collidepoint(projectile.rect.center):
                self.enemy_projectiles.remove(projectile)

    def update_strikes(self, dt):
        """Artillery shells land when their circle is full: they hurt the ship if it's in the circle. A splitter
        shell hurts nothing itself – it bursts into fragments, strikes of their own."""
        fragments = []
        for strike in self.strikes:
            if strike.update(dt):
                if strike.damage:
                    if strike.hits(self.ship.rect):
                        self.hit_ship(strike.damage)
                    self.explosions.append(ArtilleryBlast(strike.center, strike.radius))
                else:
                    self.explosions.append(Explosion(strike.center, strike.radius, strike.color))
                fragments += strike.fragments()
        self.strikes = [strike for strike in self.strikes if not strike.landed] + fragments

    def update_beams(self, dt):
        """Laser beams hurt the ship once per beam and go out after their time (or when their Laser dies)."""
        for beam in self.beams:
            beam.update(dt)
            if beam.done:
                continue
            if self.ship not in beam.hurt and beam.hits(self.ship.rect) and self.hit_ship(beam.damage):
                beam.hurt.append(self.ship)
        self.beams = [beam for beam in self.beams if not beam.done]

    def hit_ship(self, damage):
        """The window is the ship's health: a hit squeezes the edges in by damage pixels (on average, less the ship's
        armor), mostly the ones away from the ship – unless the ship is still invulnerable. True if the hit counted."""
        if not self.ship.hit():
            return False
        self.arena.hit(self.ship.absorb(damage), self.ship.rect.center)
        return True

    def explode(self, projectile):
        """Blast at the end of the shot, inside the field: damage to every enemy within the radius, and the arena edges
        whose part of the field's wall it reaches are pushed out (Field.walls_within – in a window: the edge the shot
        crossed to get there, like a bullet)."""
        field = self.field()
        position = field.clamp(projectile.rect.center)
        stats = projectile.stats
        for enemy in self.enemies:
            if enemy.distance_to(position) <= stats.blast_radius + enemy.size / 2:
                enemy.take_damage(stats.damage)
        for side in field.walls_within(position, stats.blast_radius, projectile.beyond):
            self.arena.push(side, stats.wall_push)
        self.explosions.append(Explosion(position, stats.blast_radius, stats.color))
        if stats.burn_time:
            self.burning.append(BurningGround(position, stats.burn_radius, stats.burn_damage, stats.burn_time))
        if stats.slow_time:
            self.slow_fields.append(SlowField(position, stats.slow_radius, stats.slow, stats.slow_time))

    def slow_enemies(self, dt):
        """Slow fields slow every enemy in them for this tick (before the enemies move), then go out."""
        for field in self.slow_fields:
            field.update(dt)
            for enemy in self.enemies:
                if field.covers(enemy):
                    enemy.slow(field.factor)
        self.slow_fields = [field for field in self.slow_fields if not field.done]

    def update_burning(self, dt):
        """Burning ground hurts every enemy in it with each pulse, then goes out."""
        for ground in self.burning:
            ground.update(dt)
            for _ in range(ground.pulses):
                for enemy in self.enemies:
                    if enemy.alive and enemy.distance_to(ground.position) <= ground.radius + enemy.size / 2:
                        enemy.take_damage(ground.damage)
        self.burning = [ground for ground in self.burning if not ground.done]

    def draw(self, surface):
        self.ui_layer = None
        if self.state == PAUSED:
            self.pause_menu.draw(surface)
            return
        if self.state == INVENTORY:
            self.inventory.draw(surface, self.ship)
            return
        if self.state == SHOP:
            self.shop_panel.draw(surface, self.ship)
            return
        offset = self.engine.window_rect.topleft            # world -> window: subtract the window's position
        self.arena.draw(surface, offset)
        self.draw_world(surface, offset)
        self.draw_ui(surface, offset)
        window = pygame.Rect(offset, surface.get_size())
        if any(window.colliderect(rect) for rect in self.field().sight[1:]):
            self.ui_layer = (window, self.draw_ui_layer(surface.get_size(), offset))

    def draw_ui_layer(self, size, offset):
        """The main window's HUD, hints, markers … once more, on a transparent surface – the extra windows lying on
        top of the main window put their part of it over their picture, so nothing of it gets covered."""
        if self.ui_surface is None or self.ui_surface.get_size() != tuple(size):
            self.ui_surface = pygame.Surface(size, pygame.SRCALPHA)
        self.ui_surface.fill((0, 0, 0, 0))
        self.draw_ui(self.ui_surface, offset)
        return self.ui_surface

    def draw_ui(self, surface, offset):
        """Everything on top of the world in the main window: markers, keys, abilities, HUD, notices, hints."""
        if settings.OFFSCREEN_MARKERS:
            self.draw_offscreen_markers(surface, offset)
        self.key_overlay.draw(surface)
        self.ability_bar.draw(surface, self.ship)
        kit = self.ship.watchtower
        towers = (len(self.towers), kit.max_count, kit.price) if kit else None
        self.hud.draw(surface, self.elapsed, self.ship.stars if self.shop_unlocked else None, self.cores, towers,
                      None if self.cleared else self.difficulty.goal)
        top = 14
        for text, color, seconds in self.notices:
            top = draw_text(surface, text, 36, color, alpha=round(255 * min(1.0, seconds)),
                            midtop=(surface.get_width() / 2, top)).bottom + 4
        hint = draw_text(surface, "ESC to open menu", 22, settings.TEXT, alpha=settings.HINT_ALPHA, topleft=(10, 8))
        draw_text(surface, "TAB to open inventory", 22, settings.TEXT, alpha=settings.HINT_ALPHA,
                  topleft=(10, hint.bottom + 2))

    def draw_world(self, surface, offset):
        """Everything in the world, as seen from a window whose top left corner is at offset (screen pixels)."""
        area = pygame.Rect(offset, surface.get_size())
        for ground in self.burning + self.slow_fields:      # on the ground, under everything else
            ground.draw(surface, offset)
        self.points.draw(surface, offset, area)
        for strike in self.strikes:
            strike.draw(surface, offset)
        for beam in self.beams:
            beam.draw(surface, offset)
        for explosion in self.explosions:
            explosion.draw(surface, offset)
        for pickup in self.pickups:
            pickup.draw(surface, offset)
        for tower in self.towers:
            if tower.area is not None:
                tower.skin.draw_area(surface, tower.area.move(-offset[0], -offset[1]))
            tower.draw(surface, offset)
        for enemy in self.enemies:
            if enemy.rect.colliderect(area):
                enemy.draw(surface, offset)
        for projectile in self.enemy_projectiles + self.projectiles:
            projectile.draw(surface, offset)
        for strike in self.strikes:                     # artillery shells in the air, over everything on the ground
            strike.draw_air(surface, offset)
        self.ship.draw(surface, offset)

    def draw_view(self, surface, view):
        """An extra window (a watchtower's or the radar's): the world at view.rect. Its background is almost black, with
        a hint of grey (blue for the radar) – except where it lies over the arena: that part is black like the arena.
        The border is the outline of all windows together (draw_outline). Where it covers the main window, the main
        window's HUD etc. is drawn on top (draw_ui_layer)."""
        offset = view.rect.topleft
        radar = self.radar is not None and view is self.radar.view
        surface.fill(RADAR_BACKGROUND if radar else TOWER_BACKGROUND)
        surface.fill(settings.BACKGROUND, self.arena.window_rect().move(-offset[0], -offset[1]))
        self.draw_outline(surface, offset)
        self.draw_world(surface, offset)
        if view in self.lookouts():
            pygame.draw.rect(surface, LOOKOUT_BORDER, surface.get_rect(), settings.BORDER_WIDTH)
        if self.ui_layer is not None:                   # the main window's HUD etc. where this window covers it
            window, layer = self.ui_layer
            surface.blit(layer, (window.left - offset[0], window.top - offset[1]))

    def draw_outline(self, surface, offset):
        """The border around all windows together – the arena and every extra window – as far as it lies in this
        window: where windows overlap or touch, their edges merge into one line, as if the arena's border made a bend.
        A window on its own just gets its frame.

        How: a mask of everything covered by a window (a bit bigger than this window, so edges right at its side are
        found, too); the border is every covered pixel that has an uncovered one at most BORDER_WIDTH away. (The main
        window simply draws the arena's border: where it differs, an extra window lies on top of it.)

        That's slow (half a millisecond for a small window), so the finished border is kept (self.outlines) and only
        worked out anew once a window has moved or changed its size."""
        width = settings.BORDER_WIDTH
        size = (surface.get_width() + 2 * width, surface.get_height() + 2 * width)
        origin = pygame.Vector2(offset) - (width, width)
        covered_rects = []
        field = self.field()
        for rect in field.sight[:len(field.sight) - len(field.lookouts)]:      # a Pusher's window has its own frame
            local = rect.move(-origin.x, -origin.y).clip(pygame.Rect((0, 0), size))
            if local.width and local.height:
                covered_rects.append(tuple(local))

        def make():
            covered = pygame.Mask(size)
            for left, top, local_width, local_height in covered_rects:
                covered.draw(pygame.Mask((local_width, local_height), fill=True), (left, top))
            uncovered = covered.copy()
            uncovered.invert()
            reach = pygame.Mask((2 * width + 1, 2 * width + 1), fill=True)
            near_uncovered = uncovered.convolve(reach, pygame.Mask(size), (-width, -width))
            border = covered.overlap_mask(near_uncovered, (0, 0))
            return border.to_surface(setcolor=settings.BORDER, unsetcolor=(0, 0, 0, 0))

        surface.blit(self.outlines.get((size, tuple(covered_rects)), make), (-width, -width))

    def extra_views(self):
        """The open extra windows: the watchtowers' and the radar's."""
        views = [tower.view for tower in self.towers] + ([self.radar.view] if self.radar is not None else [])
        return [view for view in views if view is not None] + self.lookouts()

    def field(self):
        """The field right now: the arena and the extra windows (game/field.py)."""
        lookouts = self.lookouts()
        return Field(self.arena, [view.rect for view in self.extra_views() if view.rect is not None
                                  and view not in lookouts],
                     [view.rect for view in lookouts if view.rect is not None])

    def draw_offscreen_markers(self, surface, offset):
        """At the window's edge, where it would come in: a dot for every enemy the player can't see (in no window), in
        its colour – a swarm gets one swarm icon instead, the bigger the closer it is – and an arrow for every point of
        interest out of sight."""
        inside = surface.get_rect().inflate(-2 * MARKER_INSET, -2 * MARKER_INSET)
        field = self.field()
        swarms = {}                                     # swarm -> [its enemies out of sight]
        for enemy in self.enemies:
            if field.sees_point(enemy.center):
                continue
            if enemy.swarm is not None:
                swarms.setdefault(enemy.swarm, []).append(enemy)
                continue
            position = enemy.center - offset
            marker = (min(max(position.x, inside.left), inside.right), min(max(position.y, inside.top), inside.bottom))
            pygame.draw.circle(surface, enemy.color, marker, MARKER_RADIUS)
        swarm_inside = surface.get_rect().inflate(-2 * SWARM_MARKER_INSET, -2 * SWARM_MARKER_INSET)
        for swarm, members in swarms.items():
            middle = sum((enemy.center for enemy in members), pygame.Vector2()) / len(members)
            distance = distance_to_rect(middle, self.arena.rect)
            near = 1 - min(1.0, distance / SWARM_MARKER_FAR)                # 1 at the window, 0 far away
            size = SWARM_MARKER_SIZES[0] + (SWARM_MARKER_SIZES[1] - SWARM_MARKER_SIZES[0]) * near
            position = middle - offset
            marker = (min(max(position.x, swarm_inside.left), swarm_inside.right),
                      min(max(position.y, swarm_inside.top), swarm_inside.bottom))
            draw_swarm_icon(surface, marker, ENEMY_TYPES[swarm.kind].skin.color, round(size))
        self.points.draw_markers(surface, offset, field)
