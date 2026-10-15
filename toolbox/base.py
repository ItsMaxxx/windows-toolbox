"""
Building blocks for program pages in the Toolbox. A page is – similar to HTML – only described:

    FOLDER = Path(__file__).parent

    class MyPage(ToolPage):
        defaults = {"rate": 2, "color": "blue"}

        def layout(self):
            return [
                Section("Refresh",
                        Text("How often to measure."),
                        Choice("Rate", "rate", {"1 s": 1, "2 s": 2, "5 s": 5})),
                Section("Advanced",
                        Buttons(Button("Open folder", lambda: self.open(FOLDER), target=FOLDER))),
            ]

    PAGE = MyPage

Name, tab and description are not here but in program.json next to it – the Toolbox builds the ToolInfo from it.
If a tool keeps running as its own program (like the Hardware Monitor), PROGRAM = Program(is_running, stop, start)
tells the Toolbox how to query, stop and start it. Then "Toolbox and all programs – quit or restart" in the Toolbox
settings automatically applies to it as well.

Building blocks with key show the value self.data[key] and save changes immediately to settings_file – by default
that is data\\<program>.json (one file per program, see storage.py).
Building blocks with name are then reachable as self.w[name], e.g. to change a status line.
Buttons that open something outside the Toolbox (website, file, folder, program) get target=… – it then shows at the
bottom left of the window while hovering, like in a browser.
The Toolbox finds each program via programs/<program>/program.json; its "page" is the file with PAGE.
"""

import copy
import os
import tkinter as tk
import tkinter.font as tkfont
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import customtkinter as ctk

import i18n
import storage

t = i18n.Texts(Path(__file__).with_name("i18n.json"))     # texts of the Toolbox itself: t("id") in the chosen language

# Colors each as (light, dark) – CustomTkinter picks the matching one automatically.
# Dark = style of the PROOFM website (navy background, green accent), light = the same tones on a light background.
BG = ("#eef2f6", "#0a1d2c")             # window background
BAR = ("#f8fafc", "#071822")            # header and sidebar
CARD = ("#ffffff", "#152736")
BORDER = ("#d8e1ea", "#213443")
FIELD = ("#f4f7fa", "#101d29")          # input fields, segmented buttons
TEXT = ("#0f2333", "#e2e8f0")
MUTED = ("#5b6f84", "#8fa3b8")
ACCENT = ("#3ddc97", "#3ddc97")         # main buttons
ACCENT_HOVER = ("#5ce8aa", "#5ce8aa")
ACCENT_DEEP = ("#1f9e6a", "#3ddc97")    # switches, sliders, checkmarks (a bit darker on a light background)
ON_ACCENT = ("#062016", "#062016")      # text on green buttons
SELECTED = ("#c6eedb", "#1d4f47")       # selected tab, entry or segmented button
HOVER = ("#e6edf3", "#13242d")          # mouse over tab or entry
BUTTON = ("#e6edf3", "#233443")         # gray buttons
BUTTON_HOVER = ("#d8e1ea", "#31414f")
BUTTON_OFF = ("#e6edf3", "#1b2c3a")     # color for buttons that can't be used right now
TRACK = ("#c5d1dc", "#2a3b4a")          # track of switches and sliders
GOOD = ("#1f9e6a", "#3ddc97")
BAD = ("#d64545", "#ff6464")
WARN = ("#b7791f", "#f5c451")
FONTS = ("Inter", "Segoe UI")           # the first installed font is used


def apply_theme():
    """Colors and shapes of all CustomTkinter widgets – call before the first window."""
    ctk.set_default_color_theme("blue")                     # base, the colors come from here
    t = ctk.ThemeManager.theme
    t["CTk"]["fg_color"] = t["CTkToplevel"]["fg_color"] = BG
    t["CTkFrame"].update(fg_color=CARD, top_fg_color=CARD, border_color=BORDER)
    t["CTkButton"].update(corner_radius=8, fg_color=ACCENT, hover_color=ACCENT_HOVER, border_color=BORDER,
                          text_color=ON_ACCENT, text_color_disabled=MUTED)
    t["CTkLabel"]["text_color"] = TEXT
    field = {"corner_radius": 8, "border_width": 1, "fg_color": FIELD, "border_color": BORDER, "text_color": TEXT}
    t["CTkEntry"].update(field, placeholder_text_color=MUTED)
    t["CTkComboBox"].update(field, button_color=BORDER, button_hover_color=BUTTON_HOVER, text_color_disabled=MUTED)
    t["CTkTextbox"].update(field, scrollbar_button_color=BUTTON, scrollbar_button_hover_color=BUTTON_HOVER)
    t["CTkCheckBox"].update(corner_radius=5, border_width=2, fg_color=ACCENT_DEEP, hover_color=ACCENT_HOVER,
                            border_color=MUTED, checkmark_color=ON_ACCENT, text_color=TEXT,
                            text_color_disabled=MUTED)
    t["CTkSwitch"].update(fg_color=TRACK, progress_color=ACCENT_DEEP, button_color=("#5b6f84", "#e2e8f0"),
                          button_hover_color=("#0f2333", "#ffffff"), text_color=TEXT, text_color_disabled=MUTED)
    t["CTkSlider"].update(fg_color=TRACK, progress_color=ACCENT_DEEP, button_color=ACCENT_DEEP,
                          button_hover_color=ACCENT_HOVER)
    t["CTkSegmentedButton"].update(corner_radius=8, fg_color=FIELD, selected_color=SELECTED,
                                   selected_hover_color=SELECTED, unselected_color=FIELD,
                                   unselected_hover_color=BUTTON, text_color=TEXT, text_color_disabled=MUTED)
    t["CTkScrollbar"].update(button_color=BUTTON, button_hover_color=BUTTON_HOVER)
    t["DropdownMenu"].update(fg_color=CARD, hover_color=SELECTED, text_color=TEXT)


def apply_font(root):
    """Font of the website (Inter) if installed – otherwise Segoe UI. Needs an already created window."""
    families = set(tkfont.families(root))
    ctk.ThemeManager.theme["CTkFont"]["family"] = next((f for f in FONTS if f in families), FONTS[-1])


@dataclass
class Program:
    """A standalone program of a tool that keeps running even without the Toolbox (e.g. the Hardware Monitor).
    Through it the Toolbox can stop and restart it along with itself in its settings ("Toolbox and all programs").

    All three run in the background (not in the GUI thread) and may take a while:
      is_running() -> True if it is running right now
      stop()       -> True if it is really stopped afterwards (wait for the process to end!)
      start()      -> True if the start worked
    Optional:
      reload()     -> have it read its settings and language again – the Toolbox calls this after a language change
    """
    is_running: Callable
    stop: Callable
    start: Callable
    reload: Callable | None = None


@dataclass
class ToolInfo:
    id: str               # unique short name, e.g. "hardware_monitor"
    name: str             # shown in the sidebar
    category: str         # tab in which the program appears
    description: str      # subtitle on the program page
    page: type            # class of the program page (subclass of ToolPage)
    program: Program | None = None      # only for tools with a standalone running program (see Program)


# ---------- Building blocks ----------
class Section:
    """An area (card) with a heading; inside it the building blocks one below the other."""

    def __init__(self, title, *elements):
        self.title, self.elements = title, elements


class Tooltip:
    """Small hint window while the mouse is over widget. text may have several lines (e.g. "•" bullets)."""

    def __init__(self, widget, text):
        self.widget, self.text, self.window = widget, text, None
        widget.bind("<Enter>", self.show, add="+")
        widget.bind("<Leave>", self.hide, add="+")

    def show(self, event=None):
        if self.window:
            return
        dark = ctk.get_appearance_mode() == "Dark"                  # colors matching light/dark
        color = lambda pair: pair[1] if dark else pair[0]           # noqa: E731
        # Plain tk instead of CustomTkinter: CTkToplevel sets icon and title bar with a delay, and CustomTkinter's DPI
        # tracking can't handle CTk widgets in a tk.Toplevel – both unnecessary for a hint window
        self.window = window = tk.Toplevel(self.widget)
        window.withdraw()
        window.overrideredirect(True)                               # without title bar
        window.attributes("-topmost", True)
        window.configure(bg=color(BORDER))                          # 1 px border
        # Multiply sizes by the Windows scaling like the CTk widgets do (negative font size = pixels)
        s = ctk.ScalingTracker.get_widget_scaling(self.widget)
        font = (ctk.ThemeManager.theme["CTkFont"]["family"], -round(12 * s))
        tk.Label(window, text=self.text, justify="left", anchor="w", wraplength=round(400 * s), bg=color(CARD),
                 fg=color(TEXT), font=font, padx=round(10 * s), pady=round(8 * s)).pack(padx=1, pady=1)
        window.update_idletasks()
        x, y = self.widget.winfo_rootx(), self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        x = min(x, self.widget.winfo_screenwidth() - window.winfo_reqwidth() - 8)    # not past the screen edge
        window.geometry(f"+{x}+{y}")
        window.deiconify()

    def hide(self, event=None):
        if self.window:
            self.window.destroy()
            self.window = None


def info_icon(master, text):
    """Round "i" that shows text as a tooltip while hovering."""
    icon = ctk.CTkLabel(master, text="i", width=18, height=18, corner_radius=9, fg_color=BUTTON, text_color=MUTED,
                        font=ctk.CTkFont(size=11, weight="bold"), cursor="question_arrow")
    Tooltip(icon, text)
    return icon


class Element:
    """Basic form: label on the left (if label), control on the right – without label across the full width.
    info: explanation that appears while hovering over an "i" after the label."""
    sticky = "w"

    def __init__(self, label=None, key=None, name=None, info=None):
        self.label, self.key, self.name, self.info = label, key, name, info

    def place(self, page, card, row):
        """Places the building block starting at row and returns the number of rows used."""
        self.widget = self.create(page, card)
        if self.label:
            caption = ctk.CTkFrame(card, fg_color="transparent")
            ctk.CTkLabel(caption, text=self.label, anchor="w").pack(side="left")
            if self.info:
                info_icon(caption, self.info).pack(side="left", padx=(6, 0))
            caption.grid(row=row, column=0, sticky="w", padx=(18, 12), pady=4)
            self.widget.grid(row=row, column=1, sticky=self.sticky, padx=(0, 18), pady=4)
        else:
            self.widget.grid(row=row, column=0, columnspan=2, sticky=self.sticky, padx=18, pady=4)
        return 1

    def create(self, page, card):
        raise NotImplementedError

    def refresh(self, page):
        """Show the value from page.data (only for building blocks with key)."""


class Text(Element):
    """Text across the full width. hidden=True hides it at first (later page.show(name))."""
    sticky = "ew"

    def __init__(self, text="", name=None, color=MUTED, size=12, hidden=False):
        super().__init__(name=name)
        self.text, self.color, self.size, self.hidden = text, color, size, hidden

    def place(self, page, card, row):
        rows = super().place(page, card, row)
        if self.hidden:
            self.widget.grid_remove()
        return rows

    def create(self, page, card):
        return ctk.CTkLabel(card, text=self.text, text_color=self.color, anchor="w", justify="left",
                            wraplength=620, font=ctk.CTkFont(size=self.size))


class Button:
    """A button in Buttons(...). style: "normal" (green), "gray", "outline" or "danger" (red text)."""
    STYLES = {
        "normal": {},
        "gray": {"fg_color": BUTTON, "hover_color": BUTTON_HOVER, "border_width": 1, "text_color": TEXT},
        "outline": {"fg_color": "transparent", "hover_color": BUTTON, "border_width": 1, "text_color": TEXT},
        "danger": {"fg_color": "transparent", "hover_color": BUTTON, "border_width": 1, "text_color": BAD},
    }

    def __init__(self, text, command, name=None, width=110, style="normal", target=None):
        self.text, self.command, self.name, self.width, self.style = text, command, name, width, style
        self.target = target    # what the button opens (website, file, folder, program) – see show_target()


def show_target(widget, app, target):
    """Like in a browser: while the mouse is over widget, the bottom left of the window shows what it opens. target is
    an address, a path or a function that returns one of them (only asked when hovering)."""
    widget.bind("<Enter>", lambda e: app.show_link(str(target() if callable(target) else target)), add="+")
    widget.bind("<Leave>", lambda e: app.hide_link(), add="+")


class Buttons(Element):
    """A row of buttons side by side – with label like the other building blocks with a caption on the left."""

    def __init__(self, *buttons, label=None, info=None):
        super().__init__(label=label, info=info)
        self.buttons = buttons

    def create(self, page, card):
        row = ctk.CTkFrame(card, fg_color="transparent")
        for b in self.buttons:
            button = ctk.CTkButton(row, text=b.text, width=b.width, command=b.command, **Button.STYLES[b.style])
            button.base_color = Button.STYLES[b.style].get("fg_color")      # for page.enable(): this color again
            button.pack(side="left", padx=(0, 8))
            if b.target:
                show_target(button, page.app, b.target)
            if b.name:
                page.w[b.name] = button
        return row


class Choice(Element):
    """Segmented buttons side by side. options: {"Display": value} or a list if display = value."""

    def __init__(self, label, key, options, name=None, info=None):
        super().__init__(label, key, name, info)
        self.options = options if isinstance(options, dict) else {o: o for o in options}

    def create(self, page, card):
        return ctk.CTkSegmentedButton(card, values=list(self.options),
                                      command=lambda text: page.set(self.key, self.options[text]))

    def refresh(self, page):
        value = page.data.get(self.key)
        self.widget.set(next((text for text, v in self.options.items() if v == value), ""))


class Combo(Element):
    """Drop-down list you can also type into yourself.
    names translates saved values into display texts, e.g. {"auto": "Automatic"}."""

    def __init__(self, label, key, values, names=None, name=None, width=240):
        super().__init__(label, key, name)
        self.values, self.names, self.width = values, names or {}, width

    def create(self, page, card):
        box = ctk.CTkComboBox(card, values=self.values, width=self.width, command=lambda text: self.apply(page))
        box.bind("<Return>", lambda e: self.apply(page))
        box.bind("<FocusOut>", lambda e: self.apply(page))
        return box

    def apply(self, page):
        text = self.widget.get().strip()
        value = next((v for v, shown in self.names.items() if shown == text), text)
        value = value or page.defaults.get(self.key, "")           # empty = default
        if value != page.data.get(self.key):
            page.set(self.key, value)

    def refresh(self, page):
        value = page.data.get(self.key, "")
        self.widget.set(self.names.get(value, value))


class Entry(Element):
    """Input field. With key the value is saved, otherwise command(text) gets it on leaving/Enter.
    secret=True shows dots instead of the text (e.g. for a password or client secret)."""

    def __init__(self, label, key=None, value="", command=None, name=None, width=240, secret=False, info=None):
        super().__init__(label, key, name, info)
        self.value, self.command, self.width, self.secret = value, command, width, secret

    def create(self, page, card):
        entry = ctk.CTkEntry(card, width=self.width, show="•" if self.secret else "")
        entry.insert(0, self.value)
        entry.bind("<Return>", lambda e: self.apply(page))
        entry.bind("<FocusOut>", lambda e: self.apply(page))
        return entry

    def apply(self, page):
        text = self.widget.get().strip()
        if not self.key:
            self.command(text)
        elif text != page.data.get(self.key):
            page.set(self.key, text)

    def refresh(self, page):
        if self.key:
            self.widget.delete(0, "end")
            self.widget.insert(0, page.data.get(self.key, ""))


class Switch(Element):
    """Switch. With key the state is saved, otherwise command() is called."""

    def __init__(self, text, key=None, command=None, name=None):
        super().__init__(key=key, name=name)
        self.text, self.command = text, command

    def create(self, page, card):
        return ctk.CTkSwitch(card, text=self.text,
                             command=lambda: page.set(self.key, bool(self.widget.get())) if self.key
                             else self.command())

    def refresh(self, page):
        if self.key:
            self.widget.select() if page.data.get(self.key) else self.widget.deselect()


class Slider(Element):
    """Slider for whole numbers. text is on the left, {} in it is replaced by the value."""

    def __init__(self, text, key, start, end, color=None, name=None):
        super().__init__(key=key, name=name)
        self.text, self.start, self.end, self.color = text, start, end, color

    def place(self, page, card, row):
        self.text_label = ctk.CTkLabel(card, anchor="w", text_color=self.color)
        self.text_label.grid(row=row, column=0, sticky="w", padx=(18, 12), pady=4)
        self.widget = ctk.CTkSlider(card, from_=self.start, to=self.end, number_of_steps=self.end - self.start,
                                    width=260, command=lambda v: page.set(self.key, int(round(v)), later=True))
        self.widget.grid(row=row, column=1, sticky="w", pady=4)
        return 1

    def refresh(self, page):
        value = page.data[self.key]
        self.widget.set(value)
        self.text_label.configure(text=self.text.format(value))


# ---------- Page ----------
class ToolPage(ctk.CTkScrollableFrame):
    """A scrollable page in the main area: title, subtitle and the sections from layout()."""
    settings_file = None      # JSON file with the settings (Path) – by default data\<program>.json
    defaults = {}             # defaults for everything the building blocks show via key

    def __init__(self, master, app, info):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.info = info
        if self.settings_file is None:
            self.settings_file = storage.settings_file(info.id)
        self.w = {}                              # building blocks with name
        self.elements = []                       # all building blocks (for refreshing)
        self.save_job = None
        self.data = self.load()
        self.columnconfigure(0, weight=1)

        ctk.CTkLabel(self, text=info.name, font=ctk.CTkFont(size=24, weight="bold"),
                     anchor="w").grid(row=0, column=0, sticky="ew", padx=24, pady=(22, 0))
        if info.description:
            ctk.CTkLabel(self, text=info.description, text_color=MUTED, anchor="w", justify="left",
                         wraplength=640).grid(row=1, column=0, sticky="ew", padx=24, pady=(2, 8))
        for number, section in enumerate(self.layout(), start=2):
            self.add_section(number, section)
        self.refresh()

    def add_section(self, number, section):
        card = ctk.CTkFrame(self, fg_color=CARD, corner_radius=12, border_width=1, border_color=BORDER)
        card.grid(row=number, column=0, sticky="ew", padx=24, pady=(10, 4))
        card.columnconfigure(1, weight=1)
        ctk.CTkLabel(card, text=section.title, font=ctk.CTkFont(size=16, weight="bold"), anchor="w").grid(
            row=0, column=0, columnspan=2, sticky="ew", padx=18, pady=(14, 4))
        row = 1
        for element in section.elements:
            row += element.place(self, card, row)
            if element.name:
                self.w[element.name] = element.widget
            self.elements.append(element)
        card.grid_rowconfigure(row, minsize=12)  # a bit of space to the bottom edge

    # --- Values ---
    def load(self):
        """Defaults, overwritten with what is in settings_file (unknown keys are kept)."""
        return storage.load(self.settings_file, self.defaults)

    def save(self):
        try:
            storage.save(self.settings_file, self.data)
        except OSError as error:
            self.app.toast(t("toast.save_error", error=error.strerror or error), error=True)
            return
        self.app.toast(t("toast.saved"))
        self.on_saved()

    def set(self, key, value, later=False):
        """Change, show and save a value – with later (slider) only shortly after releasing."""
        self.data[key] = value
        self.on_change(key, value)
        self.refresh(key)
        if self.save_job:
            self.after_cancel(self.save_job)
            self.save_job = None
        if later:
            self.save_job = self.after(500, self.save)
        else:
            self.save()

    def refresh(self, *keys):
        """Show building blocks again – all or only those for the given keys."""
        for element in self.elements:
            if element.key and (not keys or element.key in keys):
                element.refresh(self)

    def reset(self):
        self.data = copy.deepcopy(self.defaults)
        self.refresh()
        self.save()

    # --- Helpers ---
    def show(self, name, visible=True):
        self.w[name].grid() if visible else self.w[name].grid_remove()

    def enable(self, name, enabled=True):
        """Button on/off – disabled buttons turn gray so you see the difference right away.
        When enabled it gets its color back (green or that of its style, e.g. "gray")."""
        button = self.w[name]
        color = getattr(button, "base_color", None) or ctk.ThemeManager.theme["CTkButton"]["fg_color"]
        button.configure(state="normal" if enabled else "disabled", fg_color=color if enabled else BUTTON_OFF)

    def open(self, path):
        """Open a file or folder with the matching program."""
        try:
            os.startfile(path)
        except OSError:
            self.app.toast(t("toast.not_found", name=path.name), error=True)

    # --- Called by the Toolbox or by set(); subclasses can override this ---
    def layout(self):
        """List of the sections (Section) of this page."""
        return []

    def on_change(self, key, value):
        """A value was changed, shortly before it is saved."""

    def on_saved(self):
        """After saving, e.g. tell the program to reload its settings."""

    def on_show(self):
        """Page becomes visible: read the settings again (the program may have changed them itself)."""
        self.data = self.load()
        self.refresh()

    def on_hide(self):
        """Page is left or the window is hidden (e.g. stop polling)."""
