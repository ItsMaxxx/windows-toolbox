"""
The "Loadout" tab of the game menu: which weapon goes into which weapon slot (left / right mouse button).

Left: every weapon as a card – locked ones (not bought in the skill tree yet) greyed out. Right: the two slots with
the full values of what's in them (with the skill tree's upgrades) and what firing both at once costs in energy.

Drag a weapon card onto a slot to put it there (if it's already in the other slot, the two swap). Drag a weapon from
one slot onto the other to swap them, or off the slots to empty its slot. A plain click on a card puts it into the
first empty slot. At least one slot always keeps a weapon. Every change is saved right away (profile.loadout).

Only lays out, draws and turns mouse input into loadout changes – the game menu passes the mouse events on
(handle_event) while this tab is open.
"""

import pygame

from engine.ui import draw_text
from game import settings, skill_tree
from game.weapons import WEAPON_TYPES, unlocked

CARD_SIZE = (210, 112)
CARD_GAP = 16
CARD_COLUMNS = 2
SLOTS_LEFT = 480                    # the slots start this far right of the tab's left edge
SLOT_SIZE = (228, 230)
SLOT_GAP = 16
SLOT_KEYS = ("LMB", "RMB")
DRAG_START = 5                      # pixels the mouse has to move before a press becomes a drag

FILL = (24, 24, 30)
HOVER_FILL = (34, 34, 42)
LOCKED = (70, 70, 80)
LINE = (50, 50, 58)
DROP_HIGHLIGHT = (90, 225, 255)
TOO_EXPENSIVE = (200, 70, 70)
SUCCESS = (90, 225, 255)


class LoadoutPanel:
    def __init__(self, profile, rect, show_message):
        """rect: the tab's area in the game menu's window. show_message(text, color): for results."""
        self.profile = profile
        self.rect = pygame.Rect(rect)
        self.show_message = show_message
        self.drag = None            # while the mouse is held on a weapon: {"key", "source" (slot or None), "start"}
        self.dragging = False       # the mouse has moved far enough: it's a real drag (the card follows the mouse)
        self.mouse = (0, 0)

    # --- layout ---

    def card_rects(self):
        width, height = CARD_SIZE
        top = self.rect.top + 28
        return {key: pygame.Rect(self.rect.left + (index % CARD_COLUMNS) * (width + CARD_GAP),
                                 top + (index // CARD_COLUMNS) * (height + CARD_GAP), width, height)
                for index, key in enumerate(WEAPON_TYPES)}

    def slot_rects(self):
        width, height = SLOT_SIZE
        return [pygame.Rect(self.rect.left + SLOTS_LEFT + index * (width + SLOT_GAP), self.rect.top + 28, width,
                            height) for index in range(len(SLOT_KEYS))]

    def thing_at(self, position):
        """("weapon", key), ("slot", index) or None."""
        for key, rect in self.card_rects().items():
            if rect.collidepoint(position):
                return ("weapon", key)
        for index, rect in enumerate(self.slot_rects()):
            if rect.collidepoint(position):
                return ("slot", index)
        return None

    # --- input ---

    def handle_event(self, event):
        """Mouse input for the loadout. True if it was used (the game menu then ignores it)."""
        if event.type == pygame.MOUSEMOTION:
            self.mouse = event.pos
            if self.drag and not self.dragging:
                start = pygame.Vector2(self.drag["start"])
                self.dragging = start.distance_to(event.pos) >= DRAG_START
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            thing = self.thing_at(event.pos)
            if thing and thing[0] == "weapon":
                if not unlocked(self.profile, thing[1]):
                    self.show_message(f"Unlock the {WEAPON_TYPES[thing[1]].name} in the skill tree first",
                                      TOO_EXPENSIVE)
                    return True
                self.drag = {"key": thing[1], "source": None, "start": event.pos}
            elif thing and thing[0] == "slot" and self.profile.loadout[thing[1]]:
                self.drag = {"key": self.profile.loadout[thing[1]], "source": thing[1], "start": event.pos}
            else:
                return False
            self.dragging = False
            return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.drag:
            drag, dragging = self.drag, self.dragging
            self.drag, self.dragging = None, False
            if dragging:
                self.drop(drag, self.thing_at(event.pos))
            elif drag["source"] is None:
                self.put_in_free_slot(drag["key"])
            return True
        return False

    def drop(self, drag, target):
        """A dragged weapon was let go over target (from thing_at)."""
        loadout = list(self.profile.loadout)
        key, source = drag["key"], drag["source"]
        if target and target[0] == "slot":
            slot = target[1]
            if source is None and key in loadout:       # already in a slot: the two slots swap
                source = loadout.index(key)
            if source is not None:
                loadout[source], loadout[slot] = loadout[slot], loadout[source]
            else:
                loadout[slot] = key
        elif source is not None:                        # dragged off its slot: empty it
            loadout[source] = None
        else:
            return
        self.set_loadout(loadout)

    def put_in_free_slot(self, key):
        loadout = list(self.profile.loadout)
        if key in loadout:
            self.show_message("Drag it onto the other slot to swap", settings.TEXT_MUTED)
        elif None not in loadout:
            self.show_message("Both slots are full – drag it onto one to replace it", settings.TEXT_MUTED)
        else:
            loadout[loadout.index(None)] = key
            self.set_loadout(loadout)

    def set_loadout(self, loadout):
        if not any(loadout):
            self.show_message("Keep at least one weapon", TOO_EXPENSIVE)
            return
        if loadout != self.profile.loadout:
            self.profile.loadout = loadout
            self.profile.save()

    # --- drawing ---

    def draw(self, surface, hovered):
        """hovered: what thing_at() says is under the mouse (or None)."""
        left, top = self.rect.topleft
        draw_text(surface, "WEAPONS", 22, settings.TEXT_MUTED, topleft=(left, top))
        for key, rect in self.card_rects().items():
            self.draw_card(surface, key, rect, hovered == ("weapon", key))

        ship = skill_tree.start_ship(self.profile, (0, 0))             # the next run's energy (cards included)
        draw_text(surface, "SLOTS", 22, settings.TEXT_MUTED, topleft=(left + SLOTS_LEFT, top))
        target = self.thing_at(self.mouse) if self.dragging else None
        for index, rect in enumerate(self.slot_rects()):
            self.draw_slot(surface, index, rect, target == ("slot", index), hovered == ("slot", index))
        self.draw_energy(surface, ship, self.slot_rects()[0].bottom + 18)

        details = self.drag["key"] if self.drag else hovered[1] if hovered and hovered[0] == "weapon" else None
        if details:
            self.draw_details(surface, details)
        if self.dragging:
            rect = pygame.Rect((0, 0), CARD_SIZE)
            rect.center = self.mouse
            self.draw_card(surface, self.drag["key"], rect, True, floating=True)

    def draw_card(self, surface, key, rect, hovered, floating=False):
        weapon_type = WEAPON_TYPES[key]
        available = unlocked(self.profile, key)
        color = weapon_type.color if available else LOCKED
        pygame.draw.rect(surface, HOVER_FILL if hovered else FILL, rect, border_radius=8)
        pygame.draw.rect(surface, color, rect, width=3 if hovered else 1, border_radius=8)
        pygame.draw.rect(surface, color, (rect.left, rect.top, 5, rect.height), border_top_left_radius=8,
                         border_bottom_left_radius=8)
        draw_text(surface, weapon_type.name, 26, settings.TEXT if available else LOCKED,
                  topleft=(rect.left + 16, rect.top + 12))
        if not available:
            draw_text(surface, "locked – skill tree", 20, LOCKED, topleft=(rect.left + 16, rect.top + 42))
            return
        if key in self.profile.loadout and not floating:
            slot = SLOT_KEYS[self.profile.loadout.index(key)]
            draw_text(surface, slot, 18, settings.TEXT, topright=(rect.right - 12, rect.top + 14))
        words = weapon_type.description.split()
        half = (len(words) + 1) // 2
        for line, text in enumerate((" ".join(words[:half]), " ".join(words[half:]))):
            draw_text(surface, text, 19, settings.TEXT_MUTED, topleft=(rect.left + 16, rect.top + 42 + line * 19))
        weapon = skill_tree.build_weapon(self.profile, key)
        draw_text(surface, f"{weapon.energy_cost * weapon.fire_rate:.3g} energy/s while firing", 18, color,
                  bottomleft=(rect.left + 16, rect.bottom - 10))

    def draw_slot(self, surface, index, rect, drop_target, hovered):
        key = self.profile.loadout[index]
        pygame.draw.rect(surface, HOVER_FILL if hovered or drop_target else FILL, rect, border_radius=8)
        border = DROP_HIGHLIGHT if drop_target else WEAPON_TYPES[key].color if key else LOCKED
        pygame.draw.rect(surface, border, rect, width=3 if drop_target else 2, border_radius=8)
        draw_text(surface, SLOT_KEYS[index], 20, settings.TEXT, alpha=settings.HINT_ALPHA * 2,
                  topright=(rect.right - 12, rect.top + 12))
        if key is None:
            draw_text(surface, "empty", 26, settings.TEXT, alpha=settings.HINT_ALPHA, center=rect.center)
            return
        weapon = skill_tree.build_weapon(self.profile, key)
        draw_text(surface, weapon.name, 28, weapon.color, topleft=(rect.left + 14, rect.top + 12))
        if not unlocked(self.profile, key):
            draw_text(surface, "locked – not used", 20, TOO_EXPENSIVE, topleft=(rect.left + 14, rect.top + 44))
        self.draw_rows(surface, weapon.stat_lines(), rect.left + 14, rect.right - 14, rect.top + 50)

    def draw_energy(self, surface, ship, top):
        """The ship's energy, and what firing everything in the slots at once costs per second."""
        left = self.rect.left + SLOTS_LEFT
        right = self.slot_rects()[-1].right
        weapons = [weapon for weapon in ship.weapons if weapon]
        use = sum(weapon.energy_cost * weapon.fire_rate for weapon in weapons)
        rows = [("Energy", f"{ship.max_energy:g}"), ("Energy regen", f"{ship.energy_regen:g}/s"),
                ("Firing " + ("both" if len(weapons) > 1 else "it"), f"{use:.3g} energy/s")]
        self.draw_rows(surface, rows, left, right, top, size=22, step=27)
        if use > ship.energy_regen:
            seconds = ship.max_energy / (use - ship.energy_regen)
            text = f"full energy lasts {seconds:.0f} s of non-stop fire, then it fires slower"
        else:
            text = "the energy keeps up with non-stop fire"
        draw_text(surface, text, 19, settings.TEXT_MUTED, topleft=(left, top + 3 * 27 + 4))

    def draw_details(self, surface, key):
        """The values of the weapon under the mouse (or being dragged), below the cards."""
        top = max(rect.bottom for rect in self.card_rects().values()) + 24
        weapon = skill_tree.build_weapon(self.profile, key)
        draw_text(surface, weapon.name.upper(), 22, weapon.color if unlocked(self.profile, key) else LOCKED,
                  topleft=(self.rect.left, top))
        width = CARD_COLUMNS * CARD_SIZE[0] + (CARD_COLUMNS - 1) * CARD_GAP
        self.draw_rows(surface, weapon.stat_lines(), self.rect.left, self.rect.left + width, top + 28, size=22,
                       step=27)

    @staticmethod
    def draw_rows(surface, rows, left, right, top, size=20, step=24):
        """(name, value) rows: name faded on the left, value on the right, a thin line below each."""
        for name, value in rows:
            draw_text(surface, name, size, settings.TEXT_MUTED, topleft=(left, top))
            draw_text(surface, value, size, settings.TEXT, topright=(right, top))
            pygame.draw.line(surface, LINE, (left, top + size - 2), (right, top + size - 2))
            top += step
