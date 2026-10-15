"""
Toolbox – one interface for the self-written small Windows tools.

Layout:
  top      tabs for the kinds of programs + gear for the settings of the Toolbox itself
  left     all programs of the selected tab, alphabetically
  right    the settings of the selected program

Start:          double-click Toolbox.exe in the main folder (or: pythonw toolbox\\toolbox.py)
Requirement:    run Setup.exe once (creates runtime\\ and the starter .exe files)

Programs are found automatically: every folder programs\\<program>\\ with a program.json (name, tab,
description, version …); its "page" is the file with the program page (PAGE, optionally PROGRAM).
Only the installed ones appear on the left (data\\installed.json, written by Setup.exe); they can be installed and
removed in the settings under "Programs".
Toolbox settings: data\\toolbox.json, errors: data\\logs\\toolbox.log (see storage.py).
All texts are in toolbox\\i18n.json – only their ID is here: t("…") (see i18n.py). Name and description of a
program come from its i18n.json (program.name, program.description), otherwise from its program.json.
"""

import ctypes
import importlib.util
import json
import logging
import os
import queue
import shutil
import socket
import subprocess
import sys
import threading
import time
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk
from PIL import Image

sys.dont_write_bytecode = True             # don't create __pycache__ folders in the project

APP_DIR = Path(__file__).resolve().parent
ROOT = APP_DIR.parent                      # main folder (Toolbox.exe, runtime\, programs\, data\)
PROGRAMS_DIR = ROOT / "programs"           # one folder per program lives here (hardware_monitor\, …)
sys.path.insert(0, str(APP_DIR))           # so that base, winutil etc. are found – also by the program pages

import i18n  # noqa: E402
import storage  # noqa: E402
import winutil  # noqa: E402
from base import (BAD, BAR, BORDER, CARD, GOOD, HOVER, MUTED, SELECTED, TEXT, Button, Buttons, Choice,  # noqa: E402
                  Section, Switch, Text, ToolInfo, ToolPage, Tooltip, apply_font, apply_theme, show_target, t)

# Tabs at the top, in this order – like "category" in program.json; shown is t("category.<lower>")
CATEGORIES = ["General", "Games"]

MANIFEST = json.loads((APP_DIR / "program.json").read_text(encoding="utf-8"))    # like for every program
VERSION = MANIFEST["version"]
SETTINGS_FILE = storage.settings_file("toolbox")
ICON_FILE = APP_DIR / "toolbox.ico"        # blue toolbox – the programs have program.ico (⚒ on green)
GITHUB_URL = "https://github.com/ItsMaxxx/windows-toolbox"     # button "Windows Toolbox" at the top left
# Created by Setup.exe: pythonw.exe with the name "Toolbox" and its own icon (for the Task Manager). The starter
# Toolbox.exe in the main folder starts this one too; for the restart it goes directly, without the detour.
TOOLBOX_EXE = ROOT / "runtime" / "Toolbox.exe"
SETUP_EXE = ROOT / "Setup.exe"
UNINSTALL_EXE = ROOT / "Uninstall.exe"
# Which programs are installed – written by setup.ps1 (Save-Installed), the Toolbox only reads it
INSTALLED_FILE = storage.settings_file("installed")
GUI_PORT = MANIFEST["port"]      # a second start only brings the running window to the front; setup.ps1 says "quit"

# Saved value -> CustomTkinter mode; shown is t("settings.theme.<lower>")
APPEARANCE = {"Light": "light", "Dark": "dark", "System": "system"}
ZOOM_STEPS = [0.5, 0.67, 0.75, 0.8, 0.9, 1.0, 1.1, 1.25, 1.5, 1.75, 2.0]     # Ctrl + mouse wheel, steps like a browser
# Buttons DE | EN | … in the settings, automatically from toolbox\languages.json; applies to Toolbox and all programs
LANGUAGE_BUTTONS = {language.upper(): language for language in i18n.LANGUAGES}
DEFAULT_SETTINGS = {
    "appearance": "Dark",
    "close_to_tray": True,
    "zoom": 1.0,
    "language": i18n.LANGUAGE,           # set by Setup.exe; if missing: the Windows display language (see i18n.py)
}

logging.basicConfig(filename=storage.log_file("toolbox"), level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")


# ---------- Find programs ----------
def find_manifests():
    """All programs\\<program>\\program.json – installed or not. "folder" adds the program folder.
    A broken manifest is only logged so the others still appear."""
    manifests = []
    for manifest_file in sorted(PROGRAMS_DIR.glob("*/program.json")):
        try:
            manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
            manifest["folder"] = manifest_file.parent
            texts = manifest_file.with_name("i18n.json")
            manifest["texts"] = i18n.Texts(texts) if texts.exists() else None     # name and description per language
            manifests.append(manifest)
        except (OSError, ValueError):
            logging.exception("Manifest %s could not be read", manifest_file)
    return manifests


def display_text(manifest, field):
    """Name ("name") or description ("description") of a program in the chosen language – from its
    i18n.json (program.name, program.description), otherwise as it is in program.json."""
    texts, id = manifest.get("texts"), f"program.{field}"
    return texts(id) if texts and id in texts else manifest.get(field, "")


def installed_ids(manifests):
    """IDs of the installed programs according to data\\installed.json. If the file is missing (or broken): all –
    that's how it was before programs could be installed individually. setup.ps1 has the same rule (Installed)."""
    ids = storage.load(INSTALLED_FILE, {"programs": None})["programs"]
    return {m["id"] for m in manifests if not isinstance(ids, list) or m["id"] in ids}


def find_tools(manifests):
    """Loads the page named in each manifest and builds the ToolInfo from it.
    A faulty program is only logged so the others still appear."""
    tools = []
    for manifest in manifests:
        try:
            file = manifest["folder"] / manifest["page"]
            spec = importlib.util.spec_from_file_location(file.stem, file)
            module = importlib.util.module_from_spec(spec)
            sys.modules[file.stem] = module
            spec.loader.exec_module(module)
            tools.append(ToolInfo(manifest["id"], display_text(manifest, "name"), manifest["category"],
                                  display_text(manifest, "description"), module.PAGE, getattr(module, "PROGRAM", None)))
        except Exception:
            logging.exception("Program %s could not be loaded", manifest["folder"])
    return tools


MANIFESTS = find_manifests()
INSTALLED = installed_ids(MANIFESTS)                 # only changes via setup.ps1 – which restarts the Toolbox
TOOLS = find_tools([m for m in MANIFESTS if m["id"] in INSTALLED])


def update_names():
    """Name and description of all programs in the currently chosen language (after a language change)."""
    manifest_of = {m["id"]: m for m in MANIFESTS}
    for tool in TOOLS:
        tool.name = display_text(manifest_of[tool.id], "name")
        tool.description = display_text(manifest_of[tool.id], "description")


# ---------- Settings ----------
def load_settings():
    """Saved settings – anything invalid gets the default."""
    settings = storage.load(SETTINGS_FILE, DEFAULT_SETTINGS)
    if settings["appearance"] not in APPEARANCE:
        settings["appearance"] = DEFAULT_SETTINGS["appearance"]
    if not isinstance(settings["close_to_tray"], bool):
        settings["close_to_tray"] = DEFAULT_SETTINGS["close_to_tray"]
    if settings["zoom"] not in ZOOM_STEPS:
        settings["zoom"] = DEFAULT_SETTINGS["zoom"]
    if settings["language"] not in i18n.LANGUAGES:
        settings["language"] = DEFAULT_SETTINGS["language"]
    return settings


def save_settings(settings):
    try:
        storage.save(SETTINGS_FILE, settings)
        return True
    except OSError:
        logging.exception("Toolbox settings could not be saved")
        return False


# ---------- Update (git pull, then Setup.exe) ----------
# All three block for a while – only call them in the background (app.run_async).
def git(*args, timeout=30):
    """Run git in the main folder (without a console window). Result – or None if git is missing or hangs."""
    exe = shutil.which("git")
    return winutil.run_hidden([exe, "-C", str(ROOT), *args], timeout) if exe else None


def git_version():
    """Version of the folder for display: (commit, date), e.g. ("6c3fccf", "10.10.2026") – or None without git or
    without a repo."""
    if not (ROOT / ".git").exists():
        return None
    result = git("log", "-1", "--format=%h %cd", "--date=format:%d.%m.%Y")
    if result is None or result.returncode != 0 or " " not in result.stdout.strip():
        return None
    return tuple(result.stdout.strip().split(" ", 1))


def git_fetch():
    """Gets new commits from GitHub – only as a fast-forward, your own changes are never overwritten.
    Returns (new commits, error message or None); 0 new commits = already up to date."""
    def error(result, text):
        lines = result.stderr.strip().splitlines() if result is not None else []
        return 0, f"{text}: {lines[-1]}" if lines else text

    result = git("fetch", "--quiet", timeout=120)
    if result is None or result.returncode != 0:
        return error(result, t("git.fetch"))
    result = git("rev-list", "--count", "HEAD..@{upstream}")
    if result is None or result.returncode != 0:
        return error(result, t("git.no_branch"))
    new = int(result.stdout.strip() or 0)
    if new:
        result = git("pull", "--ff-only", "--quiet", timeout=120)
        if result is None or result.returncode != 0:
            return error(result, t("git.pull"))
    return new, None


# ---------- Only one Toolbox at a time ----------
def bring_existing_to_front():
    """Is the Toolbox already running? Then have it show its window and return True."""
    try:
        with socket.create_connection(("127.0.0.1", GUI_PORT), timeout=0.5) as conn:
            conn.sendall(b"show\n")
            return conn.recv(16).startswith(b"ok")
    except OSError:
        return False


# ---------- Settings page (gear) ----------
class GuiSettingsPage(ToolPage):
    """Settings of the Toolbox itself – live in self.app.settings (data\\toolbox.json)."""

    def load(self):
        return self.app.settings

    def save(self):
        self.app.save()

    def layout(self):
        return [
            Section(t("settings.appearance"),
                    Choice(t("settings.language"), "language", LANGUAGE_BUTTONS),
                    Choice(t("settings.theme"), "appearance",
                           {t(f"settings.theme.{value.lower()}"): value for value in APPEARANCE}),
                    Text(t("settings.appearance.text"))),
            Section(t("settings.window"),
                    Switch(t("settings.window.tray"), key="close_to_tray"),
                    Text(t("settings.window.text"))),
            Section(t("settings.programs"),
                    Text(t("settings.programs.text")),
                    *[self.program_row(m) for m in MANIFESTS]),
            Section(t("settings.quit"),
                    Text(f"●  {t('settings.programs.checking')}", name="programs"),
                    Buttons(Button(t("button.restart"), self.app.restart, name="only_restart"),
                            Button(t("button.quit"), self.app.quit_app, name="only_quit", style="gray"),
                            label=t("settings.toolbox_only"), info=t("info.toolbox_only")),
                    Buttons(Button(t("button.restart"), lambda: self.all_programs(restart=True), name="all_restart"),
                            Button(t("button.quit"), lambda: self.all_programs(restart=False), name="all_quit",
                                   style="gray"),
                            label=t("settings.all"), info=t("info.all"))),
            Section(t("settings.update"),
                    Text(f"●  {t('settings.version.checking')}", name="version"),
                    Buttons(Button(t("button.update"), self.run_update, name="update"),
                            label=t("settings.update.label"), info=t("info.update")),
                    Buttons(Button(t("button.repair"), self.repair, name="setup", style="gray",
                                   target=f"{SETUP_EXE} -Restart"),
                            label=t("settings.repair.label"), info=t("info.repair"))),
            Section(t("settings.uninstall"),
                    Buttons(Button(t("button.uninstall"), self.uninstall, name="uninstall",
                                   style="danger", target=UNINSTALL_EXE),
                            label=t("settings.all"), info=t("info.uninstall"))),
            Section(t("settings.info"),
                    Text(t("settings.info.text", version=VERSION, folder=storage.DATA_DIR))),
        ]

    def on_change(self, key, value):
        if key == "appearance":
            ctk.set_appearance_mode(APPEARANCE[value])
        elif key == "close_to_tray" and not value:
            self.app.stop_tray()
        elif key == "language":
            self.app.change_language(value)

    # --- Programs ---
    def program_row(self, manifest):
        """One row per program: name and version, the description in the "i", next to it Install or Remove."""
        button_name = f"program_{manifest['id']}"
        if manifest["id"] in INSTALLED:
            button = Button(t("button.remove"), lambda: self.install(manifest, False), name=button_name,
                            style="danger", target=f"{UNINSTALL_EXE} -Programs {manifest['id']}")
        else:
            button = Button(t("button.install"), lambda: self.install(manifest, True), name=button_name,
                            target=f"{SETUP_EXE} -Programs {manifest['id']}")
        return Buttons(button, label=f"{display_text(manifest, 'name')} {manifest.get('version', '')}".strip(),
                       info=display_text(manifest, "description") or None)

    def install(self, manifest, on):
        """Setup.exe or Uninstall.exe -Programs <id> in a separate window. Both quit the Toolbox and
        restart it at the end – then with the changed list on the left."""
        if not on and not messagebox.askyesno(t("remove.title"),
                                              t("remove.question", name=display_text(manifest, "name")),
                                              icon="warning", parent=self):
            return
        exe = SETUP_EXE if on else UNINSTALL_EXE
        try:
            os.startfile(str(exe), arguments=f"-Programs {manifest['id']}", cwd=str(ROOT))
        except OSError:
            logging.exception("%s could not be started", exe.name)
            self.app.toast(t("toast.did_not_start", name=exe.name), error=True)
            return
        self.enable(f"program_{manifest['id']}", False)

    # --- Quit and restart ---
    def on_show(self):
        super().on_show()
        self.check_programs()
        self.check_version()

    def check_programs(self):
        """Shows which programs are running right now (the query runs in the background)."""
        tools = [tool for tool in TOOLS if tool.program]
        if not tools:
            self.w["programs"].configure(text=t("programs.none"), text_color=MUTED)
            return

        def show(states):
            if not self.winfo_exists():
                return                           # page rebuilt in the meantime (language change)
            lines = [f"●  {t('programs.running' if on else 'programs.stopped', name=tool.name)}"
                     for tool, on in zip(tools, states or [])]
            self.w["programs"].configure(text="\n".join(lines), text_color=MUTED)

        self.app.run_async(lambda: [tool.program.is_running() for tool in tools], show)

    def all_programs(self, restart):
        """First stop every running program (and start it again with restart), then the Toolbox itself.
        If something goes wrong with a program, the Toolbox stays open and shows the error."""
        tools = [tool for tool in TOOLS if tool.program]
        buttons = ("only_restart", "only_quit", "all_restart", "all_quit")
        for name in buttons:
            self.enable(name, False)
        self.w["programs"].configure(text=f"●  {t('programs.restarting' if restart else 'programs.quitting')}")

        def work():
            failed = []
            for tool in tools:
                p = tool.program
                if not p.is_running():
                    continue                     # stopped programs stay stopped – also on restart
                if not p.stop() or (restart and not p.start()):
                    failed.append(tool.name)
            return failed

        def done(failed):
            if failed is None or failed:
                for name in buttons:
                    self.enable(name, True)
                self.app.toast(t("toast.failed", names=", ".join(failed or [t("error.unknown")])),
                               error=True)
                self.check_programs()
            elif restart:
                self.app.restart()
            else:
                self.app.quit_app()

        self.app.run_async(work, done)

    # --- Update ---
    def check_version(self):
        def show(version):
            if not self.winfo_exists():
                return                           # page rebuilt in the meantime (language change)
            text = f"●  {t('version.text', hash=version[0], date=version[1]) if version else t('version.no_git')}"
            self.w["version"].configure(text=text, text_color=MUTED)
            self.enable("update", bool(version))

        self.app.run_async(git_version, show)

    def run_update(self):
        """git pull; if there was something new, then Setup.exe (start_setup)."""
        self.enable("update", False)
        self.w["version"].configure(text=f"●  {t('version.searching')}", text_color=MUTED)

        def done(result):
            new, error = result or (0, t("error.unknown"))
            if error:
                self.w["version"].configure(text=f"●  {error}", text_color=BAD)
                self.enable("update", True)
            elif not new:
                self.app.toast(t("toast.up_to_date"))
                self.check_version()
            else:
                self.start_setup(f"●  {t('version.fetched', n=new)}")

        self.app.run_async(git_fetch, done)

    def repair(self):
        """Like after an update, just without git pull (see info.repair)."""
        self.start_setup(f"●  {t('version.setup_running')}")

    def uninstall(self):
        """Uninstall.exe in a separate window – the same as double-clicking it. It quits the Toolbox
        itself."""
        if not messagebox.askyesno(t("uninstall.title"), t("uninstall.question", folder=ROOT),
                                   icon="warning", parent=self):
            return
        try:
            os.startfile(str(UNINSTALL_EXE), cwd=str(ROOT))
        except OSError:
            logging.exception("Uninstall.exe could not be started")
            self.app.toast(t("toast.did_not_start", name=UNINSTALL_EXE.name), error=True)
            return
        self.enable("uninstall", False)

    def start_setup(self, text):
        """Setup.exe -Restart in a separate window. It quits the Toolbox, brings runtime\\ up to date with
        requirements.txt, restores everything as before (autostart, settings) and restarts what was running."""
        self.w["version"].configure(text=text, text_color=GOOD)
        try:
            os.startfile(str(SETUP_EXE), arguments="-Restart", cwd=str(SETUP_EXE.parent))
        except OSError:
            logging.exception("Setup.exe could not be started")
            self.w["version"].configure(text=f"●  {t('version.setup_error')}", text_color=BAD)


# ---------- Scroll the page with the mouse (in addition to the mouse wheel) ----------
class Scrolling:
    """Two ways to scroll the visible page with the mouse:

    Middle-click like in a browser: an icon marks the spot; the further the mouse is above or below it,
    the faster the page scrolls.
      short click                 keeps scrolling until the next click (or Esc or mouse wheel)
      hold + drag                 scrolls only until the button is released
    While it runs, all mouse clicks go to the icon (grab) – so the click that ends it doesn't trigger anything.

    Left-click + drag like on a phone: the page follows the mouse; released with momentum it glides on a bit.
    Only on empty areas and texts – buttons, switches, sliders, input fields etc. work as usual."""
    DEAD_ZONE = 12          # px around the start point where nothing scrolls or a click isn't a drag yet
    SPEED = 0.12            # middle-click: px per step per px of distance outside the dead zone
    TICK = 16               # ms per step (~60 per second)
    GRACE = 0.3             # s – focus may still be missing this long after the click (window is becoming active)
    FRICTION = 0.94         # momentum: this much speed remains per step
    MIN_MOMENTUM = 300      # px/s – released slower, the page simply stays put
    TRANSPARENT = "#010203"     # background of the icon, becomes invisible – so only the circle remains
    # Left-click + drag doesn't start on these – they need the mouse themselves
    CONTROLS = (ctk.CTkButton, ctk.CTkSegmentedButton, ctk.CTkSwitch, ctk.CTkSlider, ctk.CTkEntry,
                ctk.CTkComboBox, ctk.CTkOptionMenu, ctk.CTkCheckBox, ctk.CTkRadioButton, ctk.CTkTextbox,
                tk.Entry, tk.Text, tk.Button, tk.Scale)

    def __init__(self, app):
        self.app = app
        self.icon = None                         # icon of the middle-click while it runs
        self.job = None                          # next step (middle-click or momentum)
        self.grabbed = False                     # left-click on the page, button still down
        self.dragging = False                    # … and already dragged further than the dead zone
        app.bind_all("<ButtonPress-2>", self.middle_press, add="+")
        app.bind_all("<ButtonRelease-2>", self.middle_release, add="+")
        app.bind_all("<ButtonPress-1>", self.left_press, add="+")
        app.bind_all("<B1-Motion>", self.left_drag, add="+")
        app.bind_all("<ButtonRelease-1>", self.left_release, add="+")
        app.bind_all("<ButtonPress>", lambda e: self.stop(), add="+")         # e.g. right-click ends it
        app.bind_all("<MouseWheel>", lambda e: self.stop(), add="+")
        app.bind_all("<Escape>", lambda e: self.stop(), add="+")

    # --- shared ---
    def canvas_under(self, widget):
        """Canvas of the visible page if widget is on it and there is something to scroll – otherwise None.
        In it CTkScrollableFrame moves the content of the page."""
        page = self.app.current_page
        if not isinstance(page, ToolPage) or isinstance(widget, str):      # str: Tk-internal window
            return None
        canvas = page._parent_canvas
        w = widget
        while w is not None and w is not canvas:
            w = w.master
        if w is None or canvas.yview() == (0.0, 1.0):     # not on the page or fits entirely into the window
            return None
        return canvas

    def begin(self, canvas, event):
        self.canvas = canvas
        self.scaling = ctk.ScalingTracker.get_widget_scaling(self.app)
        self.start_x, self.start_y = event.x_root, event.y_root
        self.start_time = time.monotonic()
        self.position = canvas.yview()[0]        # carried as a float – otherwise slow scrolling gets stuck

    def move(self, px):
        """Scroll the page px further down (negative: up). False if it hits the end in the process."""
        top, bottom = self.canvas.yview()
        visible = bottom - top                   # share of the page in the window – from it: px → share
        self.position += px * visible / max(self.canvas.winfo_height(), 1)
        target = min(max(self.position, 0.0), 1.0 - visible)
        free = target == self.position
        self.position = target
        self.canvas.yview_moveto(target)
        return free

    def stop(self):
        """End middle-click scrolling or momentum."""
        if self.job:
            self.app.after_cancel(self.job)
            self.job = None
        if self.icon:
            self.icon.grab_release()
            self.icon.destroy()
            self.icon = None
            self.app.configure(cursor="")

    # --- Middle-click ---
    def middle_press(self, event):
        if self.icon:
            self.stop()
            return
        self.stop()
        canvas = self.canvas_under(event.widget)
        if canvas is None:
            return
        self.begin(canvas, event)
        self.moved = False
        self.show_icon()
        self.job = self.app.after(self.TICK, self.step)

    def middle_release(self, event):
        if self.icon and self.moved:             # held and dragged – releasing ends it
            self.stop()

    def show_icon(self):
        """Circle with arrows up/down at the start point – plain tk like the tooltip."""
        dark = ctk.get_appearance_mode() == "Dark"
        color = lambda pair: pair[1] if dark else pair[0]           # noqa: E731
        g = round(30 * self.scaling)
        self.icon = icon = tk.Toplevel(self.app)
        icon.withdraw()
        icon.overrideredirect(True)
        icon.attributes("-topmost", True)
        icon.attributes("-transparentcolor", self.TRANSPARENT)
        image = tk.Canvas(icon, width=g, height=g, bg=self.TRANSPARENT, highlightthickness=0,
                          cursor="sb_v_double_arrow")
        image.pack()
        image.create_oval(1, 1, g - 2, g - 2, fill=color(CARD), outline=color(MUTED),
                          width=max(1, round(self.scaling)))
        m, b = g / 2, g * 0.16                   # center, half arrow width
        image.create_polygon(m, g * 0.14, m - b, g * 0.36, m + b, g * 0.36, fill=color(TEXT))
        image.create_polygon(m, g * 0.86, m - b, g * 0.64, m + b, g * 0.64, fill=color(TEXT))
        icon.geometry(f"+{self.start_x - g // 2}+{self.start_y - g // 2}")
        icon.deiconify()
        self.app.configure(cursor="sb_v_double_arrow")
        self.hold()

    def hold(self):
        """All mouse clicks to the icon – only works once Windows has shown it, otherwise try again shortly."""
        if not self.icon:
            return
        try:
            self.icon.grab_set()
        except tk.TclError:
            self.icon.after(20, self.hold)

    def step(self):
        if not self.app.tk.call("focus") and time.monotonic() - self.start_time > self.GRACE:
            self.job = None
            self.stop()                          # another program in the foreground (e.g. Alt+Tab into a game)
            return
        x, y = self.app.winfo_pointerxy()
        dead_zone = self.DEAD_ZONE * self.scaling
        if abs(x - self.start_x) > dead_zone or abs(y - self.start_y) > dead_zone:
            self.moved = True
        distance = y - self.start_y
        speed = max(abs(distance) - dead_zone, 0) * self.SPEED
        if speed:
            self.move(speed if distance > 0 else -speed)
        self.job = self.app.after(self.TICK, self.step)

    # --- Left-click + drag ---
    def left_press(self, event):
        if self.icon:                            # middle-click scrolling is running – this click only ends it
            self.stop()
            return
        self.stop()                              # if the page is still gliding, a click stops it
        canvas = self.canvas_under(event.widget)
        if canvas is None or self.is_control(event.widget, canvas):
            return
        self.begin(canvas, event)
        self.grabbed, self.dragging = True, False
        self.last_y = event.y_root
        self.history = [(self.start_time, event.y_root)]     # last mouse positions – the speed on release from them

    def is_control(self, widget, canvas):
        while widget is not None and widget is not canvas:
            if isinstance(widget, self.CONTROLS):
                return True
            widget = widget.master
        return False

    def left_drag(self, event):
        if not self.grabbed:
            return
        if not self.dragging:
            if abs(event.y_root - self.start_y) <= self.DEAD_ZONE * self.scaling:
                return                           # still a click, not a drag
            self.dragging = True
            self.app.configure(cursor="fleur")
        self.move(self.last_y - event.y_root)    # mouse down = content down = scroll up
        self.last_y = event.y_root
        now = time.monotonic()
        self.history = [(t, y) for t, y in self.history if now - t < 0.1] + [(now, event.y_root)]

    def left_release(self, event):
        if not self.grabbed:
            return
        self.grabbed = False
        if not self.dragging:
            return
        self.dragging = False
        self.app.configure(cursor="")
        # Momentum: speed of the last 0.1 s – but only if the mouse was still moving when released
        now = time.monotonic()
        history = [(t, y) for t, y in self.history if now - t < 0.1]
        if len(history) >= 2 and now - history[-1][0] < 0.05:
            (t0, y0), (t1, y1) = history[0], history[-1]
            self.momentum = (y0 - y1) / max(t1 - t0, 0.001)          # px/s, positive = scroll down
            if abs(self.momentum) >= self.MIN_MOMENTUM:
                self.job = self.app.after(self.TICK, self.glide)

    def glide(self):
        self.momentum *= self.FRICTION
        if abs(self.momentum) < 50 or not self.move(self.momentum * self.TICK / 1000):
            self.job = None                      # rolled out or hit the end
            return
        self.job = self.app.after(self.TICK, self.glide)


# ---------- Main window ----------
class ToolboxApp(ctk.CTk):
    def __init__(self):
        self.settings = load_settings()
        ctk.set_appearance_mode(APPEARANCE[self.settings["appearance"]])
        ctk.set_widget_scaling(self.settings["zoom"])
        apply_theme()
        super().__init__()
        apply_font(self)

        # Title = path of the program, like in Explorer: in the Task Manager it shows under "Toolbox" which copy
        # is running right now (e.g. after moving the folder). The name is already in the logo anyway.
        self.title(str(Path(__file__).resolve()))
        self.geometry("1060x720")
        self.minsize(860, 540)
        self.set_window_icon()

        self.ui_queue = queue.Queue()           # jobs from other threads that tkinter should run
        self.pages = {}                         # pages built once are kept
        self.current_page = None
        self.selected = {}                      # last selected program per tab
        self.category = CATEGORIES[0]           # tab whose programs are on the left
        self.sidebar_buttons = {}
        self.tab_buttons = {}
        self.tray = None
        self.toast_job = None
        self.zoom_job = None
        self.zoom_rest = 0                      # started notches (touchpads deliver fractions of them)
        self.scrolling = Scrolling(self)

        self.columnconfigure(2, weight=1)
        self.rowconfigure(2, weight=1)
        self.build_topbar()
        self.build_sidebar()
        self.main = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self.main.grid(row=2, column=2, sticky="nsew")
        self.main.columnconfigure(0, weight=1)
        self.main.rowconfigure(0, weight=1)
        self.build_link_bar()

        self.show_category(CATEGORIES[0])
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        # Ctrl + mouse wheel is more specific than the pages' <MouseWheel> – so they don't scroll along
        self.bind_all("<Control-MouseWheel>", self.zoom_wheel)
        threading.Thread(target=self.instance_server, daemon=True).start()
        self.after(100, self.poll_queue)

    # --- Layout ---
    def set_window_icon(self):
        try:
            self.iconbitmap(str(ICON_FILE))      # after iconbitmap() CustomTkinter no longer overwrites the icon
        except Exception:
            pass                                 # toolbox.ico is missing – then with the default icon

    def build_topbar(self):
        """Header like on the website: name (button to the GitHub repo), tabs as plain links, line below."""
        bar = ctk.CTkFrame(self, height=60, corner_radius=0, fg_color=BAR)
        bar.grid(row=0, column=0, columnspan=3, sticky="ew")
        bar.columnconfigure(2, weight=1)
        ctk.CTkFrame(self, height=1, corner_radius=0, fg_color=BORDER).grid(row=1, column=0, columnspan=3, sticky="ew")

        name = ctk.CTkButton(bar, text="Windows Toolbox", width=0, height=36, corner_radius=8, fg_color="transparent",
                             hover_color=HOVER, text_color=TEXT, font=ctk.CTkFont(size=17, weight="bold"),
                             cursor="hand2", command=lambda: webbrowser.open(GITHUB_URL))
        name.grid(row=0, column=0, padx=(12, 20), pady=12)
        self.github_tooltip = Tooltip(name, t("header.github"))
        show_target(name, self, GITHUB_URL)

        tabs = ctk.CTkFrame(bar, fg_color="transparent")
        tabs.grid(row=0, column=1, sticky="w")
        for category in CATEGORIES:
            button = ctk.CTkButton(tabs, text=t(f"category.{category.lower()}"), width=0, height=34, corner_radius=8,
                                   fg_color="transparent", hover_color=HOVER, text_color=MUTED,
                                   font=ctk.CTkFont(size=14, weight="bold"),
                                   command=lambda c=category: self.show_category(c))
            button.pack(side="left", padx=2)
            self.tab_buttons[category] = button
        self.toast_label = ctk.CTkLabel(bar, text="", text_color=GOOD, font=ctk.CTkFont(size=13))
        self.toast_label.grid(row=0, column=3, padx=12)
        self.gear = ctk.CTkButton(bar, text="⚙", width=40, height=36, corner_radius=8, font=ctk.CTkFont(size=22),
                                  fg_color="transparent", text_color=MUTED, hover_color=HOVER,
                                  command=self.show_settings)
        self.gear.grid(row=0, column=4, padx=(0, 16))

    def build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=230, corner_radius=0, fg_color=BAR)
        self.sidebar.grid(row=2, column=0, sticky="nsw")
        self.sidebar.grid_propagate(False)       # fixed width, even with short names
        self.sidebar.columnconfigure(0, weight=1)
        ctk.CTkFrame(self, width=1, corner_radius=0, fg_color=BORDER).grid(row=2, column=1, sticky="ns")

    def build_link_bar(self):
        """Box at the bottom left like in a browser: shows what a button opens while the mouse is over it (see
        base.show_target). It lies over sidebar and page and is only visible then."""
        self.link_bar = ctk.CTkFrame(self, corner_radius=0, fg_color=BAR, border_width=1, border_color=BORDER)
        self.link_label = ctk.CTkLabel(self.link_bar, text="", text_color=MUTED, height=22,
                                       font=ctk.CTkFont(size=12))
        self.link_label.pack(padx=(9, 10), pady=2)

    def show_link(self, text):
        self.link_label.configure(text=text)
        self.link_bar.place(relx=0, rely=1, anchor="sw")
        self.link_bar.lift()

    def hide_link(self):
        self.link_bar.place_forget()

    def mark(self, button, active):
        """Highlight the selected tab/entry like the active links of the website (green tint, bright text)."""
        button.configure(fg_color=SELECTED if active else "transparent", text_color=TEXT if active else MUTED)

    # --- Navigation ---
    def show_category(self, category):
        for name, button in self.tab_buttons.items():
            self.mark(button, name == category)
        self.mark(self.gear, False)
        tools = self.fill_sidebar(category)
        if not tools:
            self.show_page(None)
            return
        remembered = self.selected.get(category)
        self.show_tool(next((tool for tool in tools if tool.id == remembered), tools[0]))

    def fill_sidebar(self, category):
        """Fill the sidebar with the programs of the tab (alphabetically) – returns them."""
        self.category = category
        for child in self.sidebar.winfo_children():
            child.destroy()
        self.sidebar_buttons = {}

        ctk.CTkLabel(self.sidebar, text=t(f"category.{category.lower()}").upper(), text_color=MUTED, anchor="w",
                     font=ctk.CTkFont(size=11, weight="bold")).grid(row=0, column=0, sticky="ew", padx=14, pady=(16, 6))
        tools = sorted((tool for tool in TOOLS if tool.category == category), key=lambda tool: tool.name.casefold())
        for row, tool in enumerate(tools, start=1):
            button = ctk.CTkButton(self.sidebar, text=tool.name, anchor="w", height=36, corner_radius=8,
                                   fg_color="transparent", text_color=MUTED, hover_color=HOVER,
                                   font=ctk.CTkFont(size=14, weight="bold"),
                                   command=lambda t=tool: self.show_tool(t))
            button.grid(row=row, column=0, sticky="ew", padx=8, pady=2)
            self.sidebar_buttons[tool.id] = button
        if not tools:
            # Only point to "Install" if there is something to install for this tab
            missing = any(m.get("category") == category and m["id"] not in INSTALLED for m in MANIFESTS)
            ctk.CTkLabel(self.sidebar, text=t("sidebar.empty_install" if missing else "sidebar.empty"),
                         text_color=MUTED, justify="left").grid(row=1, column=0, sticky="w", padx=12)
        return tools

    def show_tool(self, tool):
        self.category = tool.category
        self.selected[tool.category] = tool.id
        for name, button in self.tab_buttons.items():       # green again in case the gear was selected before
            self.mark(button, name == tool.category)
        self.mark(self.gear, False)
        for tool_id, button in self.sidebar_buttons.items():
            self.mark(button, tool_id == tool.id)
        if tool.id not in self.pages:
            self.pages[tool.id] = tool.page(self.main, self, tool)
        self.show_page(self.pages[tool.id])

    def show_program(self, tool_id):
        """Show this program's page (including the tab) – e.g. from the gear in the Hardware Monitor. Unknown or not
        installed: stays as it is."""
        tool = next((tool for tool in TOOLS if tool.id == tool_id), None)
        if tool:
            self.show_category(tool.category)
            self.show_tool(tool)

    def show_settings(self):
        for button in (*self.tab_buttons.values(), *self.sidebar_buttons.values()):
            self.mark(button, False)
        self.mark(self.gear, True)
        if "_settings" not in self.pages:
            info = ToolInfo("_settings", t("settings.title"), "", t("settings.subtitle"),
                            GuiSettingsPage)
            self.pages["_settings"] = GuiSettingsPage(self.main, self, info)
        self.show_page(self.pages["_settings"])

    def show_page(self, page):
        if self.current_page is page:
            return
        self.scrolling.stop()
        self.hide_link()                         # the button under it is gone in a moment – its <Leave> won't come
        if self.current_page is not None:
            self.current_page.on_hide()
            self.current_page.grid_forget()
        self.current_page = page
        if page is not None:
            page.grid(row=0, column=0, sticky="nsew")
            page.on_show()

    # --- Zoom ---
    def zoom_wheel(self, event):
        """Ctrl + mouse wheel: everything bigger or smaller like in a browser, is remembered. The display at the top
        right comes immediately, the rescaling only shortly after the last notch – rescaling everything takes a moment."""
        self.zoom_rest += event.delta
        notches = int(self.zoom_rest / 120)       # 120 = one notch
        if notches:
            self.zoom_rest -= notches * 120
            step = min(max(ZOOM_STEPS.index(self.settings["zoom"]) + notches, 0), len(ZOOM_STEPS) - 1)
            self.settings["zoom"] = ZOOM_STEPS[step]
            self.toast(t("toast.zoom", percent=round(ZOOM_STEPS[step] * 100)))
            if self.zoom_job:
                self.after_cancel(self.zoom_job)
            self.zoom_job = self.after(150, self.apply_zoom)
        return "break"

    def apply_zoom(self):
        self.zoom_job = None
        ctk.set_widget_scaling(self.settings["zoom"])
        if not save_settings(self.settings):
            self.toast(t("toast.zoom_error"), error=True)

    def change_language(self, language):
        """Immediately in the new language: the Toolbox relabels itself (relabel), running programs read it
        again (Program.reload)."""
        i18n.set_language(language)
        # Both only once the click is done: set() saves right after on_change (otherwise the programs would still read
        # the old language) and afterwards still works with the settings page that relabel replaces
        self.after_idle(self.relabel)
        for tool in TOOLS:
            if tool.program and tool.program.reload:
                self.after_idle(lambda p=tool.program: self.run_async(p.reload))

    def relabel(self):
        """After a language change: relabel header and sidebar, rebuild all pages (program pages the next time they
        are shown) – and show the settings again, where the switch happened."""
        update_names()
        for category, button in self.tab_buttons.items():
            button.configure(text=t(f"category.{category.lower()}"))
        self.github_tooltip.text = t("header.github")
        if self.tray is not None:
            self.tray.update_menu()
        self.show_page(None)
        for page in self.pages.values():
            page.destroy()
        self.pages = {}
        self.fill_sidebar(self.category)
        self.show_settings()

    # --- Helpers for program pages ---
    def save(self):
        if save_settings(self.settings):
            self.toast(t("toast.saved"))
        else:
            self.toast(t("toast.save_failed"), error=True)

    def toast(self, text, error=False):
        """Short message at the top right, disappears after a few seconds."""
        self.toast_label.configure(text=text, text_color=BAD if error else GOOD)
        if self.toast_job:
            self.after_cancel(self.toast_job)
        self.toast_job = self.after(2500, lambda: self.toast_label.configure(text=""))

    def run_async(self, func, on_done=None):
        """Run func in the background (so the window doesn't freeze), on_done(result) afterwards in the GUI thread."""
        def worker():
            try:
                result = func()
            except Exception:
                logging.exception("Error in background task")
                result = None
            if on_done:
                self.ui_queue.put(lambda: on_done(result))
        threading.Thread(target=worker, daemon=True).start()

    def poll_queue(self):
        try:
            while True:
                task = self.ui_queue.get_nowait()
                if task == "show":
                    self.show_window()
                elif isinstance(task, tuple) and task[0] == "show":         # ("show", program id)
                    self.show_program(task[1])
                    self.show_window()
                elif task == "quit":
                    self.quit_app()
                    return
                else:
                    try:
                        task()
                    except Exception:            # an error must not stop the queue
                        logging.exception("Error after a background task")
        except queue.Empty:
            pass
        self.after(100, self.poll_queue)

    # --- Close, notification area ---
    def on_close(self):
        if self.settings["close_to_tray"]:
            self.hide_to_tray()
        else:
            self.quit_app()

    def hide_to_tray(self):
        self.scrolling.stop()
        self.hide_link()
        if self.current_page is not None:
            self.current_page.on_hide()          # e.g. no status queries while the window is gone
        self.withdraw()
        if self.tray is None:
            try:
                import pystray
                menu = pystray.Menu(
                    pystray.MenuItem(lambda item: t("tray.open"), lambda icon, item: self.ui_queue.put("show"),
                                     default=True),
                    pystray.MenuItem(lambda item: t("tray.quit"), lambda icon, item: self.ui_queue.put("quit")),
                )
                self.tray = pystray.Icon("toolbox", Image.open(ICON_FILE), "Toolbox", menu)
                self.tray.run_detached()
            except Exception:
                logging.exception("Tray icon could not be created – quitting the Toolbox instead")
                self.quit_app()

    def show_window(self):
        self.deiconify()
        self.lift()
        self.focus_force()
        if self.current_page is not None:
            self.current_page.on_show()

    def stop_tray(self):
        if self.tray is not None:
            self.tray.stop()
            self.tray = None

    def quit_app(self):
        if self.current_page is not None:
            self.current_page.on_hide()
        self.stop_tray()
        self.destroy()

    def restart(self):
        """Starts a new Toolbox and quits this one. The new one waits with --after <pid> until this one is really
        closed – otherwise it would find the old one still running and only bring its window to the front."""
        exe = str(TOOLBOX_EXE) if TOOLBOX_EXE.exists() else winutil.pythonw_exe()
        try:
            subprocess.Popen([exe, str(Path(__file__).resolve()), "--after", str(os.getpid())],
                             cwd=str(ROOT), creationflags=winutil.CREATE_NO_WINDOW)
        except OSError:
            logging.exception("New Toolbox could not be started")
            self.toast(t("toast.restart_error"), error=True)
            return
        self.quit_app()

    def instance_server(self):
        """Commands over a local connection, one per connection, answer "ok":
          show    a second Toolbox start brings this window to the front with it
          show <program id>   the same, right on this program's page (gear in the Hardware Monitor)
          status  is the Toolbox running? (setup.ps1 asks before setting up)
          quit    quit (setup.ps1, so it can renew or delete runtime\\)"""
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.bind(("127.0.0.1", GUI_PORT))
            server.listen()
        except OSError:
            logging.warning("Port %s in use – a second start can't bring this window to the front", GUI_PORT)
            return
        with server:
            while True:
                try:
                    conn, _ = server.accept()
                except OSError:
                    break
                with conn:
                    try:
                        conn.settimeout(1)
                        command = conn.recv(64).strip()
                        if command.startswith(b"show "):
                            self.ui_queue.put(("show", command[5:].decode(errors="replace").strip()))
                            conn.sendall(b"ok\n")
                        elif command in (b"show", b"quit"):
                            self.ui_queue.put(command.decode())
                        if command in (b"show", b"status", b"quit"):
                            conn.sendall(b"ok\n")
                    except OSError:
                        pass


def main():
    if "--after" in sys.argv:                    # restart (restart()): first wait until the old Toolbox is closed
        try:
            winutil.wait_for_exit(int(sys.argv[sys.argv.index("--after") + 1]), timeout=10)
        except (IndexError, ValueError):
            pass
    if bring_existing_to_front():
        return
    # Own app ID: otherwise the taskbar shows the Python icon instead of the Toolbox icon
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Toolbox.Tools")
    try:
        ToolboxApp().mainloop()
    except Exception:
        logging.exception("Unexpected error")
        raise


if __name__ == "__main__":
    main()
