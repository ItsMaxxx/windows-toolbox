"""
The scene where the game is played: the window keeps shrinking, the ship shoots its edges to push them back out,
enemies come in from the desktop. Getting hit squeezes the window.

States: PLAYING, PAUSED (Esc: pause menu), INVENTORY (Tab) and SHOP (T). Outside PLAYING nothing moves, the mouse
is free and the window shows only the menu/inventory/shop: it takes on the panel's size, centred on the arena. On resume it snaps
back to the arena, which hasn't changed in the meantime. Leaving the window (Alt+Tab, clicking elsewhere) pauses the
game, too.
"""

import pygame

from engine import Scene
from engine.desktop import work_area
from engine.key_overlay import KeyOverlay
from engine.ui import draw_text
from game import inventory, pause_menu, settings, shop_panel
from game.ability_bar import AbilityBar
from game.arena import Arena
from game.enemies.spawner import Spawner
from game.explosion import Explosion
from game.hud import Hud
from game.inventory import Inventory
from game.pause_menu import PauseMenu
from game.ship import Ship
from game.shop import Shop
from game.shop_panel import ShopPanel
from game.star_pickup import StarPickup

PLAYING, PAUSED, INVENTORY, SHOP = "playing", "paused", "inventory", "shop"
PANEL_SIZES = {PAUSED: pause_menu.SIZE, INVENTORY: inventory.SIZE, SHOP: shop_panel.SIZE}
MARKER_INSET = 8                # off-screen markers: distance from the window's edge …
MARKER_RADIUS = 4               # … and size
WEAPON_BUTTONS = (0, 2)         # weapon slot 1: left mouse button, slot 2: right mouse button (index in get_pressed)

# W on top, A S D below – like on the keyboard
MOVEMENT_KEYS = [("W", pygame.K_w, 1, 0), ("A", pygame.K_a, 0, 1), ("S", pygame.K_s, 1, 1), ("D", pygame.K_d, 2, 1)]


class PlayScene(Scene):
    def __init__(self):
        super().__init__()
        self.desktop = work_area()
        self.arena = Arena(self.desktop)
        self.ship = Ship(self.arena.rect.center)
        self.projectiles = []                   # the player's shots
        self.enemies = []
        self.enemy_projectiles = []
        self.spawner = Spawner(self.desktop)
        self.explosions = []
        self.pickups = []                       # stars dropped by killed enemies
        self.elapsed = 0.0                      # seconds played (not counting pauses)
        self.ability_bar = AbilityBar()
        self.hud = Hud()
        self.shop = Shop(self.ship)
        self.shop_panel = ShopPanel(self.shop)
        self.key_overlay = KeyOverlay(MOVEMENT_KEYS, settings.KEY_OVERLAY_INSET, settings.KEY_OVERLAY_VISIBLE)
        self.pause_menu = PauseMenu(resume=self.resume, main_menu=self.to_main_menu, quit_game=self.quit)
        self.inventory = Inventory()
        self.state = PLAYING

    def enter(self):
        self.set_state(PLAYING)

    def set_state(self, state):
        self.state = state
        if state == PAUSED:
            self.pause_menu.open()
        self.engine.grab_mouse(state == PLAYING)
        self.engine.move_window(self.window_rect())

    def window_rect(self):
        """Playing: exactly the arena. Paused/inventory: just the panel, centred on the arena (and on the desktop)."""
        arena = self.arena.window_rect()
        if self.state == PLAYING:
            return arena
        panel = pygame.Rect((0, 0), PANEL_SIZES[self.state])
        panel.center = arena.center
        return panel.clamp(self.desktop)

    # --- menu actions ---

    def resume(self):
        self.set_state(PLAYING)

    def to_main_menu(self):
        from game.main_menu_scene import MainMenuScene     # imported here: the main menu also imports this file
        self.engine.change_scene(MainMenuScene())

    def quit(self):
        self.engine.stop()

    # --- events, logic, drawing ---

    def handle_event(self, event):
        self.key_overlay.handle_event(event)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.set_state(PAUSED if self.state == PLAYING else PLAYING)
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_TAB and self.state in (PLAYING, INVENTORY):
            self.set_state(INVENTORY if self.state == PLAYING else PLAYING)
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_t and self.state in (PLAYING, SHOP):
            self.set_state(SHOP if self.state == PLAYING else PLAYING)
        elif event.type == pygame.WINDOWFOCUSLOST and self.state == PLAYING:
            self.set_state(PAUSED)
        elif event.type == pygame.KEYDOWN and self.state == PLAYING:
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
        self.arena.update(dt)
        self.ship.update(dt, self.engine.mouse_position())
        self.arena.contain(self.ship)

        buttons = pygame.mouse.get_pressed()
        for slot, button in enumerate(WEAPON_BUTTONS):
            if buttons[button]:
                self.projectiles += self.ship.fire(slot)

        self.enemies += self.spawner.update(dt, self.arena.rect, len(self.enemies))
        for enemy in self.enemies:
            self.enemy_projectiles += enemy.update(dt, self.ship)

        # effects on shots in flight (slowing areas, deflecting enemies, …) go here – before projectile.update()
        self.update_player_shots(dt)
        self.update_enemy_shots(dt)
        for enemy in self.enemies:
            if enemy.contact_damage and enemy.rect.colliderect(self.ship.rect):
                self.hit_ship(enemy.contact_damage)

        for enemy in self.enemies:
            if not enemy.alive:
                self.explosions.append(Explosion(enemy.center, enemy.size * 1.6, enemy.color))
                self.pickups.append(StarPickup(enemy.center))
        self.enemies = [enemy for enemy in self.enemies if enemy.alive]

        for pickup in self.pickups:
            pickup.update(dt, self.ship)
        collected = [pickup for pickup in self.pickups if pickup.rect.colliderect(self.ship.rect)]
        self.ship.stars += len(collected)
        self.pickups = [pickup for pickup in self.pickups if pickup not in collected]

        for explosion in self.explosions:
            explosion.update(dt)
        self.explosions = [explosion for explosion in self.explosions if not explosion.done]

        self.engine.move_window(self.window_rect())

    def update_player_shots(self, dt):
        """Player shots end on an enemy (damage), at an edge (push it out) or at their target. Shots with a blast
        radius explode at their end instead."""
        for projectile in self.projectiles[:]:          # [:] – a copy, because hits remove from the list
            projectile.update(dt)
            enemy = next((e for e in self.enemies if e.alive and e.rect.colliderect(projectile.rect)), None)
            side = self.arena.side_hit(projectile.rect.center)
            if not (enemy or side or projectile.arrived):
                continue
            self.projectiles.remove(projectile)
            if projectile.stats.blast_radius:
                self.explode(projectile)
            elif enemy:
                enemy.take_damage(projectile.stats.damage)
            elif side:
                self.arena.push(side, projectile.stats.wall_push)

    def update_enemy_shots(self, dt):
        """Enemy shots fly through the window's edges (they often come from outside); they end on the ship or when
        they leave the desktop."""
        for projectile in self.enemy_projectiles[:]:
            projectile.update(dt)
            if projectile.rect.colliderect(self.ship.rect):
                self.hit_ship(projectile.stats.damage)
                self.enemy_projectiles.remove(projectile)
            elif not self.desktop.collidepoint(projectile.rect.center):
                self.enemy_projectiles.remove(projectile)

    def hit_ship(self, damage):
        """The window is the ship's health: a hit squeezes every edge in – unless the ship is still invulnerable."""
        if self.ship.hit():
            self.arena.squeeze(settings.HIT_SHRINK * damage)

    def explode(self, projectile):
        """Blast at the end of the shot (inside the arena): damage to every enemy within the radius, and every edge
        within it is pushed out."""
        position = pygame.Vector2(projectile.rect.center)
        position.x = min(max(position.x, self.arena.rect.left), self.arena.rect.right)
        position.y = min(max(position.y, self.arena.rect.top), self.arena.rect.bottom)
        stats = projectile.stats
        for enemy in self.enemies:
            if enemy.distance_to(position) <= stats.blast_radius + enemy.size / 2:
                enemy.take_damage(stats.damage)
        for side in self.arena.sides_within(position, stats.blast_radius):
            self.arena.push(side, stats.wall_push)
        self.explosions.append(Explosion(position, stats.blast_radius, stats.color))

    def draw(self, surface):
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
        for explosion in self.explosions:
            explosion.draw(surface, offset)
        for pickup in self.pickups:
            pickup.draw(surface, offset)
        for enemy in self.enemies:
            enemy.draw(surface, offset)
        for projectile in self.enemy_projectiles + self.projectiles:
            projectile.draw(surface, offset)
        self.ship.draw(surface, offset)
        if settings.OFFSCREEN_MARKERS:
            self.draw_offscreen_markers(surface, offset)
        self.key_overlay.draw(surface)
        self.ability_bar.draw(surface, self.ship)
        self.hud.draw(surface, self.elapsed, self.ship.stars)
        hint = draw_text(surface, "ESC to open menu", 22, settings.TEXT, alpha=settings.HINT_ALPHA, topleft=(10, 8))
        draw_text(surface, "TAB to open inventory", 22, settings.TEXT, alpha=settings.HINT_ALPHA,
                  topleft=(10, hint.bottom + 2))

    def draw_offscreen_markers(self, surface, offset):
        """A dot at the window's edge for every enemy outside it, in its colour, where it would come in."""
        inside = surface.get_rect().inflate(-2 * MARKER_INSET, -2 * MARKER_INSET)
        for enemy in self.enemies:
            position = enemy.center - offset
            if surface.get_rect().collidepoint(position):
                continue
            marker = (min(max(position.x, inside.left), inside.right), min(max(position.y, inside.top), inside.bottom))
            pygame.draw.circle(surface, enemy.color, marker, MARKER_RADIUS)
