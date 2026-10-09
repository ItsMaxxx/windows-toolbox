"""
Baukasten für Programmseiten in der Toolbox. Eine Seite wird – ähnlich wie HTML – nur beschrieben:

    class MeineSeite(ToolPage):
        settings_file = Path(__file__).with_name("mein_programm_settings.json")
        defaults = {"rate": 2, "farbe": "blau"}

        def layout(self):
            return [
                Section("Aktualisierung",
                        Text("Wie oft gemessen wird."),
                        Choice("Rate", "rate", {"1 s": 1, "2 s": 2, "5 s": 5})),
                Section("Erweitert",
                        Buttons(Button("Ordner öffnen", lambda: self.open(Path(__file__).parent)))),
            ]

    TOOL = ToolInfo("mein_programm", "Mein Programm", "Werkzeuge", "Kurze Beschreibung", MeineSeite)

Bausteine mit key zeigen den Wert self.data[key] an und speichern Änderungen sofort in settings_file.
Bausteine mit name sind danach als self.w[name] erreichbar, z. B. um eine Statuszeile zu ändern.
Die Toolbox findet jede Datei src/<programm>/<programm>_gui.py mit einem Eintrag TOOL automatisch.
"""

import json
import os
import tkinter.font as tkfont
from dataclasses import dataclass

import customtkinter as ctk

# Farben jeweils als (hell, dunkel) – CustomTkinter nimmt automatisch die passende.
# Dunkel = Stil der PROOFM-Website (Navy-Hintergrund, grüner Akzent), hell = dieselben Töne auf hellem Grund.
BG = ("#eef2f6", "#0a1d2c")             # Fensterhintergrund
BAR = ("#f8fafc", "#071822")            # Kopf- und Seitenleiste
CARD = ("#ffffff", "#152736")
BORDER = ("#d8e1ea", "#213443")
FIELD = ("#f4f7fa", "#101d29")          # Eingabefelder, Auswahlknöpfe
TEXT = ("#0f2333", "#e2e8f0")
MUTED = ("#5b6f84", "#8fa3b8")
ACCENT = ("#3ddc97", "#3ddc97")         # Hauptknöpfe
ACCENT_HOVER = ("#5ce8aa", "#5ce8aa")
ACCENT_DEEP = ("#1f9e6a", "#3ddc97")    # Schalter, Regler, Häkchen (auf hellem Grund etwas dunkler)
ON_ACCENT = ("#062016", "#062016")      # Text auf grünen Knöpfen
SELECTED = ("#c6eedb", "#1d4f47")       # gewählter Tab, Eintrag oder Auswahlknopf
HOVER = ("#e6edf3", "#13242d")          # Maus über Tab oder Eintrag
BUTTON = ("#e6edf3", "#233443")         # graue Knöpfe
BUTTON_HOVER = ("#d8e1ea", "#31414f")
BUTTON_OFF = ("#e6edf3", "#1b2c3a")     # Farbe für gerade nicht nutzbare Knöpfe
TRACK = ("#c5d1dc", "#2a3b4a")          # Bahn von Schaltern und Reglern
GOOD = ("#1f9e6a", "#3ddc97")
BAD = ("#d64545", "#ff6464")
WARN = ("#b7791f", "#f5c451")
FONTS = ("Inter", "Segoe UI")           # erste installierte Schrift wird genommen


def apply_theme():
    """Farben und Formen aller CustomTkinter-Bausteine – vor dem ersten Fenster aufrufen."""
    ctk.set_default_color_theme("blue")                     # Grundlage, die Farben kommen von hier
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
    """Schrift der Website (Inter), falls installiert – sonst Segoe UI. Braucht ein schon erstelltes Fenster."""
    families = set(tkfont.families(root))
    ctk.ThemeManager.theme["CTkFont"]["family"] = next((f for f in FONTS if f in families), FONTS[-1])


@dataclass
class ToolInfo:
    id: str               # eindeutiger Kurzname, z. B. "hardware_monitor"
    name: str             # Anzeige in der Seitenleiste
    category: str         # Tab, in dem das Programm erscheint
    description: str      # Untertitel auf der Programmseite
    page: type            # Klasse der Programmseite (Unterklasse von ToolPage)


# ---------- Bausteine ----------
class Section:
    """Ein Bereich (Karte) mit Überschrift; darin die Bausteine untereinander."""

    def __init__(self, title, *elements):
        self.title, self.elements = title, elements


class Element:
    """Grundform: Beschriftung links (falls label), Bedienelement rechts – ohne label über die ganze Breite."""
    sticky = "w"

    def __init__(self, label=None, key=None, name=None):
        self.label, self.key, self.name = label, key, name

    def place(self, page, card, row):
        """Baut den Baustein ab Zeile row ein und gibt die Zahl der belegten Zeilen zurück."""
        self.widget = self.create(page, card)
        if self.label:
            ctk.CTkLabel(card, text=self.label, anchor="w").grid(row=row, column=0, sticky="w", padx=(18, 12), pady=4)
            self.widget.grid(row=row, column=1, sticky=self.sticky, padx=(0, 18), pady=4)
        else:
            self.widget.grid(row=row, column=0, columnspan=2, sticky=self.sticky, padx=18, pady=4)
        return 1

    def create(self, page, card):
        raise NotImplementedError

    def refresh(self, page):
        """Den Wert aus page.data anzeigen (nur bei Bausteinen mit key)."""


class Text(Element):
    """Text über die ganze Breite. hidden=True blendet ihn anfangs aus (später page.show(name))."""
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
    """Ein Knopf in Buttons(...). style: "normal" (grün), "grau", "rahmen" oder "gefahr" (roter Text)."""
    STYLES = {
        "normal": {},
        "grau": {"fg_color": BUTTON, "hover_color": BUTTON_HOVER, "border_width": 1, "text_color": TEXT},
        "rahmen": {"fg_color": "transparent", "hover_color": BUTTON, "border_width": 1, "text_color": TEXT},
        "gefahr": {"fg_color": "transparent", "hover_color": BUTTON, "border_width": 1, "text_color": BAD},
    }

    def __init__(self, text, command, name=None, width=110, style="normal"):
        self.text, self.command, self.name, self.width, self.style = text, command, name, width, style


class Buttons(Element):
    """Eine Reihe Knöpfe nebeneinander."""

    def __init__(self, *buttons):
        super().__init__()
        self.buttons = buttons

    def create(self, page, card):
        row = ctk.CTkFrame(card, fg_color="transparent")
        for b in self.buttons:
            button = ctk.CTkButton(row, text=b.text, width=b.width, command=b.command, **Button.STYLES[b.style])
            button.pack(side="left", padx=(0, 8))
            if b.name:
                page.w[b.name] = button
        return row


class Choice(Element):
    """Auswahlknöpfe nebeneinander. options: {"Anzeige": Wert} oder eine Liste, wenn Anzeige = Wert."""

    def __init__(self, label, key, options, name=None):
        super().__init__(label, key, name)
        self.options = options if isinstance(options, dict) else {o: o for o in options}

    def create(self, page, card):
        return ctk.CTkSegmentedButton(card, values=list(self.options),
                                      command=lambda text: page.set(self.key, self.options[text]))

    def refresh(self, page):
        value = page.data.get(self.key)
        self.widget.set(next((text for text, v in self.options.items() if v == value), ""))


class Combo(Element):
    """Aufklappliste, in die man auch selbst etwas eintippen kann.
    names übersetzt gespeicherte Werte in Anzeigetexte, z. B. {"auto": "Automatisch"}."""

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
        value = value or page.defaults.get(self.key, "")           # leer = Startwert
        if value != page.data.get(self.key):
            page.set(self.key, value)

    def refresh(self, page):
        value = page.data.get(self.key, "")
        self.widget.set(self.names.get(value, value))


class Entry(Element):
    """Eingabefeld. Mit key wird der Wert gespeichert, sonst bekommt command(text) ihn beim Verlassen/Enter."""

    def __init__(self, label, key=None, value="", command=None, name=None, width=240):
        super().__init__(label, key, name)
        self.value, self.command, self.width = value, command, width

    def create(self, page, card):
        entry = ctk.CTkEntry(card, width=self.width)
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
    """Schalter. Mit key wird der Zustand gespeichert, sonst wird command() aufgerufen."""

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
    """Schieberegler für ganze Zahlen. text steht links, {} darin wird durch den Wert ersetzt."""

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


class Check(Element):
    """Häkchen, das alle Einträge aus items in die Liste page.data[key] aufnimmt bzw. daraus entfernt.
    hint steht klein darunter."""

    def __init__(self, text, key, items, hint=None, name=None):
        super().__init__(key=key, name=name)
        self.text, self.items, self.hint = text, list(items), hint

    def place(self, page, card, row):
        self.widget = ctk.CTkCheckBox(card, text=self.text, command=lambda: self.apply(page))
        self.widget.grid(row=row, column=0, columnspan=2, sticky="w", padx=18, pady=(6, 0))
        if self.hint:
            ctk.CTkLabel(card, text=self.hint, text_color=MUTED, anchor="w", font=ctk.CTkFont(size=12)).grid(
                row=row + 1, column=0, columnspan=2, sticky="w", padx=(50, 18))
        return 2 if self.hint else 1

    def apply(self, page):
        others = [item for item in page.data[self.key] if item not in self.items]
        page.set(self.key, (self.items if self.widget.get() else []) + others)

    def refresh(self, page):
        self.widget.select() if set(self.items) <= set(page.data[self.key]) else self.widget.deselect()


class TextList(Element):
    """Textfeld für die Liste page.data[key], ein Eintrag pro Zeile, mit Knopf zum Übernehmen.
    Einträge aus exclude (z. B. die von Check-Häkchen) erscheinen nicht im Feld und bleiben erhalten."""

    def __init__(self, text, key, exclude=(), button="Übernehmen", name=None):
        super().__init__(key=key, name=name)
        self.text, self.exclude, self.button = text, set(exclude), button

    def place(self, page, card, row):
        ctk.CTkLabel(card, text=self.text, anchor="w", font=ctk.CTkFont(size=12)).grid(
            row=row, column=0, columnspan=2, sticky="w", padx=18, pady=(14, 4))
        self.widget = ctk.CTkTextbox(card, height=90)
        self.widget.grid(row=row + 1, column=0, columnspan=2, sticky="ew", padx=18)
        ctk.CTkButton(card, text=self.button, width=160, command=lambda: self.apply(page)).grid(
            row=row + 2, column=0, columnspan=2, sticky="w", padx=18, pady=(8, 4))
        return 3

    def apply(self, page):
        kept = [item for item in page.data[self.key] if item in self.exclude]
        for line in self.widget.get("1.0", "end").splitlines():
            if line.strip() and line.strip() not in kept:
                kept.append(line.strip())
        page.set(self.key, kept)

    def refresh(self, page):
        self.widget.delete("1.0", "end")
        self.widget.insert("1.0", "\n".join(item for item in page.data[self.key] if item not in self.exclude))


# ---------- Seite ----------
class ToolPage(ctk.CTkScrollableFrame):
    """Eine scrollbare Seite im Hauptbereich: Titel, Untertitel und die Bereiche aus layout()."""
    settings_file = None      # Path der JSON-Datei mit den Einstellungen des Programms (oder None)
    defaults = {}             # Startwerte für alles, was die Bausteine per key anzeigen

    def __init__(self, master, app, info):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.info = info
        self.w = {}                              # Bausteine mit name
        self.elements = []                       # alle Bausteine (zum Auffrischen)
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
        card.grid_rowconfigure(row, minsize=12)  # etwas Abstand zum unteren Rand

    # --- Werte ---
    def load(self):
        """Startwerte, überschrieben mit dem, was in settings_file steht (unbekannte Schlüssel bleiben erhalten)."""
        data = json.loads(json.dumps(self.defaults))          # tiefe Kopie
        try:
            saved = json.loads(self.settings_file.read_text(encoding="utf-8"))
            if isinstance(saved, dict):
                data.update(saved)
        except (AttributeError, OSError, ValueError):
            pass
        return data

    def save(self):
        try:
            self.settings_file.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError as error:
            self.app.toast(f"Speichern fehlgeschlagen: {error.strerror or error}", error=True)
            return
        self.app.toast("Gespeichert ✓")
        self.on_saved()

    def set(self, key, value, later=False):
        """Wert ändern, anzeigen und speichern – bei later (Schieberegler) erst kurz nach dem Loslassen."""
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
        """Bausteine neu anzeigen – alle oder nur die zu den genannten keys."""
        for element in self.elements:
            if element.key and (not keys or element.key in keys):
                element.refresh(self)

    def reset(self):
        self.data = json.loads(json.dumps(self.defaults))
        self.refresh()
        self.save()

    # --- Hilfen ---
    def show(self, name, visible=True):
        self.w[name].grid() if visible else self.w[name].grid_remove()

    def enable(self, name, enabled=True):
        """Knopf an/aus – ausgeschaltete Knöpfe werden grau, damit man den Unterschied sofort sieht."""
        self.w[name].configure(state="normal" if enabled else "disabled",
                               fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"] if enabled else BUTTON_OFF)

    def open(self, path):
        """Datei oder Ordner mit dem passenden Programm öffnen."""
        try:
            os.startfile(path)
        except (OSError, AttributeError):
            self.app.toast(f"Nicht gefunden: {path.name}", error=True)

    # --- Wird von der Toolbox bzw. von set() aufgerufen; Unterklassen können das überschreiben ---
    def layout(self):
        """Liste der Bereiche (Section) dieser Seite."""
        return []

    def on_change(self, key, value):
        """Ein Wert wurde geändert, kurz bevor er gespeichert wird."""

    def on_saved(self):
        """Nach dem Speichern, z. B. dem Programm sagen, dass es die Einstellungen neu laden soll."""

    def on_show(self):
        """Seite wird sichtbar: Einstellungen neu einlesen (das Programm kann sie selbst geändert haben)."""
        self.data = self.load()
        self.refresh()

    def on_hide(self):
        """Seite wird verlassen oder das Fenster versteckt (z. B. Abfragen stoppen)."""
