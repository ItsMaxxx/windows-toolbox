"""
Toolbox – eine Oberfläche für die selbst geschriebenen kleinen Windows-Tools.

Aufbau:
  oben     Tabs für die Arten von Programmen + Zahnrad für die Einstellungen der Toolbox selbst
  links    alle Programme des gewählten Tabs, alphabetisch
  rechts   die Einstellungen des gewählten Programms

Start:          Doppelklick auf Toolbox.exe im Hauptordner (oder: pythonw toolbox\\toolbox.py)
Voraussetzung:  einmal Setup.exe (legt runtime\\ und die Starter-.exe an)

Programme werden automatisch gefunden: jeder Ordner programme\\<programm>\\ mit einer programm.json (Name, Tab,
Beschreibung, Version …); deren "seite" ist die Datei mit der Programmseite (SEITE, optional PROGRAMM).
Links erscheinen nur die eingerichteten (daten\\installiert.json, schreibt Setup.exe); einrichten und entfernen lassen
sie sich in den Einstellungen unter „Programme“.
Einstellungen der Toolbox: daten\\toolbox.json, Fehler: daten\\logs\\toolbox.log (siehe daten.py).
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

sys.dont_write_bytecode = True             # keine __pycache__-Ordner im Projekt anlegen

APP_DIR = Path(__file__).resolve().parent
ROOT = APP_DIR.parent                      # Hauptordner (Toolbox.exe, runtime\, programme\, daten\)
PROGRAMME_DIR = ROOT / "programme"         # hier liegt je Programm ein Ordner (hardware_monitor\, …)
sys.path.insert(0, str(APP_DIR))           # damit base, winutil usw. gefunden werden – auch von den Programmseiten

import daten  # noqa: E402
import winutil  # noqa: E402
from base import (BAD, BAR, BORDER, CARD, GOOD, HOVER, MUTED, SELECTED, TEXT, Button, Buttons, Choice,  # noqa: E402
                  Section, Switch, Text, ToolInfo, ToolPage, Tooltip, apply_font, apply_theme)

CATEGORIES = ["Allgemein", "Games"]     # Tabs oben, in dieser Reihenfolge

AUSWEIS = json.loads((APP_DIR / "programm.json").read_text(encoding="utf-8"))    # wie bei jedem Programm
VERSION = AUSWEIS["version"]
SETTINGS_FILE = daten.einstellungen("toolbox")
ICON_FILE = APP_DIR / "toolbox.ico"        # blauer Werkzeugkoffer – die Programme haben programm.ico (⚒ auf Grün)
GITHUB_URL = "https://github.com/ItsMaxxx/windows-toolbox"     # Knopf „Windows Toolbox“ oben links
# Von Setup.exe angelegt: pythonw.exe mit Namen „Toolbox“ und eigenem Symbol (für den Task-Manager). Diese
# startet auch der Starter Toolbox.exe im Hauptordner; für den Neustart geht es direkt, ohne den Umweg.
TOOLBOX_EXE = ROOT / "runtime" / "Toolbox.exe"
SETUP_EXE = ROOT / "Setup.exe"
UNINSTALL_EXE = ROOT / "Uninstall.exe"
# Welche Programme eingerichtet sind – schreibt setup.ps1 (Installierte-Speichern), die Toolbox liest nur
INSTALLIERT_FILE = daten.einstellungen("installiert")
GUI_PORT = AUSWEIS["port"]       # ein zweiter Start holt nur das laufende Fenster nach vorne; setup.ps1 sagt "quit"

APPEARANCE = {"Hell": "light", "Dunkel": "dark", "System": "system"}
ZOOM_STUFEN = [0.5, 0.67, 0.75, 0.8, 0.9, 1.0, 1.1, 1.25, 1.5, 1.75, 2.0]    # Strg + Mausrad, Stufen wie im Browser
DEFAULT_SETTINGS = {
    "appearance": "Dunkel",
    "close_to_tray": True,
    "zoom": 1.0,
}

logging.basicConfig(filename=daten.log("toolbox"), level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")


# ---------- Programme finden ----------
def find_ausweise():
    """Alle programme\\<programm>\\programm.json – eingerichtet oder nicht. "ordner" ergänzt den Programmordner.
    Ein kaputter Ausweis wird nur protokolliert, damit die übrigen trotzdem erscheinen."""
    ausweise = []
    for ausweis_datei in sorted(PROGRAMME_DIR.glob("*/programm.json")):
        try:
            ausweis = json.loads(ausweis_datei.read_text(encoding="utf-8"))
            ausweis["ordner"] = ausweis_datei.parent
            ausweise.append(ausweis)
        except (OSError, ValueError):
            logging.exception("Ausweis %s konnte nicht gelesen werden", ausweis_datei)
    return ausweise


def installierte_ids(ausweise):
    """IDs der eingerichteten Programme laut daten\\installiert.json. Fehlt die Datei (oder ist sie kaputt): alle –
    so war es, bevor man Programme einzeln einrichten konnte. Dieselbe Regel hat setup.ps1 (Installierte)."""
    ids = daten.lesen(INSTALLIERT_FILE, {"programme": None})["programme"]
    return {a["id"] for a in ausweise if not isinstance(ids, list) or a["id"] in ids}


def find_tools(ausweise):
    """Lädt zu jedem Ausweis die darin genannte Seite und baut daraus das ToolInfo.
    Ein fehlerhaftes Programm wird nur protokolliert, damit die übrigen trotzdem erscheinen."""
    tools = []
    for ausweis in ausweise:
        try:
            file = ausweis["ordner"] / ausweis["seite"]
            spec = importlib.util.spec_from_file_location(file.stem, file)
            module = importlib.util.module_from_spec(spec)
            sys.modules[file.stem] = module
            spec.loader.exec_module(module)
            tools.append(ToolInfo(ausweis["id"], ausweis["name"], ausweis["kategorie"], ausweis.get("beschreibung", ""),
                                  module.SEITE, getattr(module, "PROGRAMM", None)))
        except Exception:
            logging.exception("Programm %s konnte nicht geladen werden", ausweis["ordner"])
    return tools


AUSWEISE = find_ausweise()
INSTALLIERT = installierte_ids(AUSWEISE)                 # ändert sich nur über setup.ps1 – das startet die Toolbox neu
TOOLS = find_tools([a for a in AUSWEISE if a["id"] in INSTALLIERT])


# ---------- Einstellungen ----------
def load_settings():
    """Gespeicherte Einstellungen – Ungültiges bekommt den Startwert."""
    settings = daten.lesen(SETTINGS_FILE, DEFAULT_SETTINGS)
    if settings["appearance"] not in APPEARANCE:
        settings["appearance"] = DEFAULT_SETTINGS["appearance"]
    if not isinstance(settings["close_to_tray"], bool):
        settings["close_to_tray"] = DEFAULT_SETTINGS["close_to_tray"]
    if settings["zoom"] not in ZOOM_STUFEN:
        settings["zoom"] = DEFAULT_SETTINGS["zoom"]
    return settings


def save_settings(settings):
    try:
        daten.schreiben(SETTINGS_FILE, settings)
        return True
    except OSError:
        logging.exception("Einstellungen der Toolbox konnten nicht gespeichert werden")
        return False


# ---------- Aktualisieren (git pull, danach Setup.exe) ----------
# Alle drei blockieren eine Weile – nur im Hintergrund aufrufen (app.run_async).
def git(*args, timeout=30):
    """git im Hauptordner ausführen (ohne Konsolenfenster). Ergebnis – oder None, wenn git fehlt oder hängt."""
    exe = shutil.which("git")
    return winutil.run_hidden([exe, "-C", str(ROOT), *args], timeout) if exe else None


def git_stand():
    """Stand des Ordners für die Anzeige, z. B. „6c3fccf vom 10.10.2026“ – oder None ohne git bzw. ohne Repo."""
    if not (ROOT / ".git").exists():
        return None
    result = git("log", "-1", "--format=%h vom %cd", "--date=format:%d.%m.%Y")
    return result.stdout.strip() if result is not None and result.returncode == 0 else None


def git_holen():
    """Holt neue Commits von GitHub – nur als Fast-Forward, eigene Änderungen werden nie überschrieben.
    Rückgabe (neue Commits, Fehlermeldung oder None); 0 neue Commits = schon aktuell."""
    def fehler(result, text):
        zeilen = result.stderr.strip().splitlines() if result is not None else []
        return 0, f"{text}: {zeilen[-1]}" if zeilen else text

    result = git("fetch", "--quiet", timeout=120)
    if result is None or result.returncode != 0:
        return fehler(result, "Abrufen fehlgeschlagen")
    result = git("rev-list", "--count", "HEAD..@{upstream}")
    if result is None or result.returncode != 0:
        return fehler(result, "Kein Zweig auf GitHub zugeordnet")
    neu = int(result.stdout.strip() or 0)
    if neu:
        result = git("pull", "--ff-only", "--quiet", timeout=120)
        if result is None or result.returncode != 0:
            return fehler(result, "git pull fehlgeschlagen")
    return neu, None


# ---------- Nur eine Toolbox gleichzeitig ----------
def bring_existing_to_front():
    """Läuft die Toolbox schon? Dann deren Fenster zeigen lassen und True zurückgeben."""
    try:
        with socket.create_connection(("127.0.0.1", GUI_PORT), timeout=0.5) as conn:
            conn.sendall(b"show\n")
            return conn.recv(16).startswith(b"ok")
    except OSError:
        return False


# ---------- Einstellungsseite (Zahnrad) ----------
class GuiSettingsPage(ToolPage):
    """Einstellungen der Toolbox selbst – liegen in self.app.settings (daten\\toolbox.json)."""

    def load(self):
        return self.app.settings

    def save(self):
        self.app.save()

    def layout(self):
        return [
            Section("Darstellung",
                    Choice("Design", "appearance", list(APPEARANCE)),
                    Text("Größer oder kleiner: Strg + Mausrad. Mausrad-Klick scrollt wie im Browser – Maus hoch oder "
                         "runter bewegen, nochmal klicken beendet. Oder die Seite mit der linken Maustaste "
                         "anfassen und ziehen.")),
            Section("Fenster",
                    Switch("Beim Schließen in den Infobereich minimieren", key="close_to_tray"),
                    Text("Die Toolbox läuft dann unten rechts als Symbol weiter. Doppelklick bzw. Klick öffnet sie "
                         "wieder, Rechtsklick → Beenden schließt sie ganz.")),
            Section("Programme",
                    Text("Eingerichtete Programme erscheinen links. Installieren und Entfernen laufen in einem eigenen "
                         "Fenster; die Toolbox schließt sich dabei kurz und startet danach von selbst neu."),
                    *[self.programm_zeile(a) for a in AUSWEISE]),
            Section("Beenden und Neustart",
                    Text("●  Prüfe Programme …", name="programme"),
                    Buttons(Button("Neu starten", self.app.neu_starten, name="nur_neu"),
                            Button("Beenden", self.app.quit_app, name="nur_ende", style="grau"),
                            label="Nur Toolbox", info=NUR_TOOLBOX_INFO),
                    Buttons(Button("Neu starten", lambda: self.alle(neu=True), name="alle_neu"),
                            Button("Beenden", lambda: self.alle(neu=False), name="alle_ende", style="grau"),
                            label="Toolbox und alle Programme", info=ALLE_INFO)),
            Section("Aktualisieren",
                    Text("●  Prüfe Stand …", name="stand"),
                    Buttons(Button("Aktualisieren", self.aktualisieren, name="update"),
                            label="Neuester Stand von GitHub", info=UPDATE_INFO),
                    Buttons(Button("Neu einrichten", self.neu_einrichten, name="setup", style="grau"),
                            label="Ohne Update, z. B. zum Reparieren", info=NEU_EINRICHTEN_INFO)),
            Section("Info", Text(f"Toolbox {VERSION}\nEinstellungen und Logs: {daten.DATEN_DIR}")),
        ]

    def on_change(self, key, value):
        if key == "appearance":
            ctk.set_appearance_mode(APPEARANCE[value])
        elif key == "close_to_tray" and not value:
            self.app.stop_tray()

    # --- Programme ---
    def programm_zeile(self, ausweis):
        """Eine Zeile je Programm: Name und Version, die Beschreibung im „i“, daneben Installieren bzw. Entfernen."""
        knopf = f"programm_{ausweis['id']}"
        if ausweis["id"] in INSTALLIERT:
            button = Button("Entfernen", lambda: self.einrichten(ausweis, False), name=knopf, style="gefahr")
        else:
            button = Button("Installieren", lambda: self.einrichten(ausweis, True), name=knopf)
        return Buttons(button, label=f"{ausweis['name']} {ausweis.get('version', '')}".strip(),
                       info=ausweis.get("beschreibung") or None)

    def einrichten(self, ausweis, an):
        """Setup.exe bzw. Uninstall.exe -Programme <id> in einem eigenen Fenster. Beide beenden die Toolbox und
        starten sie am Ende neu – dann mit der geänderten Liste links."""
        if not an and not messagebox.askyesno(
                "Programm entfernen",
                f"{ausweis['name']} entfernen?\n\nEs wird beendet, Autostart und heruntergeladene Dateien werden "
                "gelöscht. Deine Einstellungen bleiben – über „Installieren“ ist es jederzeit wieder da.",
                icon="warning", parent=self):
            return
        exe = SETUP_EXE if an else UNINSTALL_EXE
        try:
            os.startfile(str(exe), arguments=f"-Programme {ausweis['id']}", cwd=str(ROOT))
        except OSError:
            logging.exception("%s konnte nicht gestartet werden", exe.name)
            self.app.toast(f"{exe.name} startete nicht", error=True)
            return
        self.enable(f"programm_{ausweis['id']}", False)

    # --- Beenden und Neustart ---
    def on_show(self):
        super().on_show()
        self.programme_pruefen()
        self.stand_pruefen()

    def programme_pruefen(self):
        """Zeigt, welche Programme gerade laufen (die Abfrage läuft im Hintergrund)."""
        tools = [t for t in TOOLS if t.programm]
        if not tools:
            self.w["programme"].configure(text="Keine Programme, die eigenständig laufen.", text_color=MUTED)
            return

        def zeigen(zustaende):
            zeilen = [f"●  {t.name}: {'läuft' if an else 'gestoppt'}" for t, an in zip(tools, zustaende or [])]
            self.w["programme"].configure(text="\n".join(zeilen), text_color=MUTED)

        self.app.run_async(lambda: [t.programm.laeuft() for t in tools], zeigen)

    def alle(self, neu):
        """Erst jedes laufende Programm beenden (und bei neu wieder starten), dann die Toolbox selbst.
        Klappt bei einem Programm etwas nicht, bleibt die Toolbox offen und zeigt den Fehler."""
        tools = [t for t in TOOLS if t.programm]
        knoepfe = ("nur_neu", "nur_ende", "alle_neu", "alle_ende")
        for name in knoepfe:
            self.enable(name, False)
        self.w["programme"].configure(text="●  Programme werden " + ("neu gestartet …" if neu else "beendet …"))

        def work():
            fehler = []
            for tool in tools:
                p = tool.programm
                if not p.laeuft():
                    continue                     # gestoppte Programme bleiben gestoppt – auch beim Neustart
                if not p.beenden() or (neu and not p.starten()):
                    fehler.append(tool.name)
            return fehler

        def done(fehler):
            if fehler is None or fehler:
                for name in knoepfe:
                    self.enable(name, True)
                self.app.toast(f"Nicht geklappt: {', '.join(fehler or ['unbekannter Fehler'])}", error=True)
                self.programme_pruefen()
            elif neu:
                self.app.neu_starten()
            else:
                self.app.quit_app()

        self.app.run_async(work, done)

    # --- Aktualisieren ---
    def stand_pruefen(self):
        def zeigen(stand):
            text = f"●  Stand: {stand}" if stand else "●  Kein Git-Ordner oder git fehlt – Aktualisieren nicht möglich."
            self.w["stand"].configure(text=text, text_color=MUTED)
            self.enable("update", bool(stand))

        self.app.run_async(git_stand, zeigen)

    def aktualisieren(self):
        """git pull; gab es Neues, danach Setup.exe (setup_starten)."""
        self.enable("update", False)
        self.w["stand"].configure(text="●  Suche nach Updates …", text_color=MUTED)

        def done(ergebnis):
            neu, fehler = ergebnis or (0, "unbekannter Fehler")
            if fehler:
                self.w["stand"].configure(text=f"●  {fehler}", text_color=BAD)
                self.enable("update", True)
            elif not neu:
                self.app.toast("Schon auf dem neuesten Stand ✓")
                self.stand_pruefen()
            else:
                self.setup_starten(f"●  {neu} neue Änderung(en) geholt – Setup.exe läuft …")

        self.app.run_async(git_holen, done)

    def neu_einrichten(self):
        """Wie nach einem Update, nur ohne git pull (siehe NEU_EINRICHTEN_INFO)."""
        self.setup_starten("●  Setup.exe läuft …")

    def setup_starten(self, text):
        """Setup.exe -Neustart in einem eigenen Fenster. Das beendet die Toolbox, bringt runtime\\ auf den Stand von
        requirements.txt, stellt alles wie vorher (Autostart, Einstellungen) und startet neu, was lief."""
        self.w["stand"].configure(text=text, text_color=GOOD)
        try:
            os.startfile(str(SETUP_EXE), arguments="-Neustart", cwd=str(SETUP_EXE.parent))
        except OSError:
            logging.exception("Setup.exe konnte nicht gestartet werden")
            self.w["stand"].configure(text="●  Setup.exe startete nicht – bitte Setup.exe im Hauptordner "
                                           "doppelklicken.", text_color=BAD)


UPDATE_INFO = (
    "Holt den neuesten Stand von GitHub (git pull) und führt danach Setup.exe aus:\n\n"
    "•  Die Toolbox schließt sich kurz, Pakete in runtime\\ werden auf die Versionen aus requirements.txt gebracht.\n"
    "•  Danach starten die Toolbox und die Programme, die liefen (z. B. der Hardware-Monitor), mit dem neuen "
    "Code. Neue Programme richtest du selbst ein: unter „Programme“ → Installieren.\n\n"
    "Alles, was du eingestellt hast, ist danach wie vorher: Einstellungen in daten\\, Autostart an oder aus, "
    "gestoppte Programme bleiben gestoppt. Eigene Änderungen am Code bleiben unangetastet: Passen sie nicht zum "
    "neuen Stand, bricht das Update mit einer Meldung ab."
)
NEU_EINRICHTEN_INFO = (
    "Führt Setup.exe aus wie nach einem Update, nur ohne etwas von GitHub zu holen – z. B. wenn etwas nicht mehr "
    "startet oder nach dem Verschieben des Ordners.\n\n"
    "Die Toolbox schließt sich kurz und kommt von selbst wieder. Alles, was du eingestellt hast, ist danach wie "
    "vorher: Einstellungen, Autostart an oder aus, laufende Programme laufen wieder, gestoppte bleiben gestoppt."
)
NUR_TOOLBOX_INFO = (
    "•  Neu starten: schließt die Toolbox und öffnet sie gleich wieder – z. B. nach einem Update.\n"
    "•  Beenden: schließt die Toolbox ganz (auch das Symbol im Infobereich).\n\n"
    "Programme wie der Hardware-Monitor laufen dabei weiter."
)
ALLE_INFO = (
    "Wie „Nur Toolbox“, aber zusätzlich für jedes Programm, das gerade läuft (z. B. den Hardware-Monitor):\n\n"
    "•  Neu starten: erst die Programme neu, dann die Toolbox. Gestoppte Programme bleiben gestoppt.\n"
    "•  Beenden: erst die Programme, dann die Toolbox."
)


# ---------- Seite mit der Maus scrollen (zusätzlich zum Mausrad) ----------
class Scrollen:
    """Zwei Arten, die sichtbare Seite mit der Maus zu scrollen:

    Mausrad-Klick wie im Browser: Ein Symbol markiert die Stelle; je weiter die Maus darüber bzw. darunter steht,
    desto schneller scrollt die Seite.
      kurz klicken                scrollt weiter bis zum nächsten Klick (oder Esc bzw. Mausrad)
      gedrückt halten + ziehen    scrollt nur, bis die Taste losgelassen wird
    Solange es läuft, gehen alle Mausklicks an das Symbol (grab) – der Klick zum Beenden löst also nichts aus.

    Linksklick + ziehen wie am Handy: Die Seite folgt der Maus; mit Schwung losgelassen gleitet sie noch etwas weiter.
    Nur auf freien Flächen und Texten – Knöpfe, Schalter, Regler, Eingabefelder usw. funktionieren wie gewohnt."""
    TOTZONE = 12            # px um die Startstelle, in denen nichts scrollt bzw. ein Klick noch kein Ziehen ist
    TEMPO = 0.12            # Mausrad-Klick: px pro Schritt je px Abstand außerhalb der Totzone
    TAKT = 16               # ms je Schritt (~60 pro Sekunde)
    ANLAUF = 0.3            # s – so lange darf der Fokus nach dem Klick noch fehlen (Fenster wird gerade aktiv)
    REIBUNG = 0.94          # Schwung: so viel Tempo bleibt pro Schritt übrig
    MIN_SCHWUNG = 300       # px/s – langsamer losgelassen bleibt die Seite einfach stehen
    DURCHSICHTIG = "#010203"    # Hintergrund des Symbols, wird unsichtbar – so bleibt nur der Kreis
    # Darauf startet Linksklick + ziehen nicht – die brauchen die Maus selbst
    BEDIENELEMENTE = (ctk.CTkButton, ctk.CTkSegmentedButton, ctk.CTkSwitch, ctk.CTkSlider, ctk.CTkEntry,
                      ctk.CTkComboBox, ctk.CTkOptionMenu, ctk.CTkCheckBox, ctk.CTkRadioButton, ctk.CTkTextbox,
                      tk.Entry, tk.Text, tk.Button, tk.Scale)

    def __init__(self, app):
        self.app = app
        self.symbol = None                       # Symbol des Mausrad-Klicks, solange der läuft
        self.job = None                          # nächster Schritt (Mausrad-Klick oder Schwung)
        self.gefasst = False                     # Linksklick auf der Seite, Taste noch unten
        self.zieht = False                       # … und schon weiter als die Totzone gezogen
        app.bind_all("<ButtonPress-2>", self.mitte_druecken, add="+")
        app.bind_all("<ButtonRelease-2>", self.mitte_loslassen, add="+")
        app.bind_all("<ButtonPress-1>", self.links_druecken, add="+")
        app.bind_all("<B1-Motion>", self.links_ziehen, add="+")
        app.bind_all("<ButtonRelease-1>", self.links_loslassen, add="+")
        app.bind_all("<ButtonPress>", lambda e: self.stop(), add="+")         # z. B. Rechtsklick beendet
        app.bind_all("<MouseWheel>", lambda e: self.stop(), add="+")
        app.bind_all("<Escape>", lambda e: self.stop(), add="+")

    # --- gemeinsam ---
    def canvas_unter(self, widget):
        """Canvas der sichtbaren Seite, wenn widget darauf liegt und es etwas zu scrollen gibt – sonst None.
        Darin verschiebt CTkScrollableFrame den Inhalt der Seite."""
        seite = self.app.current_page
        if not isinstance(seite, ToolPage) or isinstance(widget, str):      # str: Tk-internes Fenster
            return None
        canvas = seite._parent_canvas
        w = widget
        while w is not None and w is not canvas:
            w = w.master
        if w is None or canvas.yview() == (0.0, 1.0):     # nicht auf der Seite bzw. passt ganz ins Fenster
            return None
        return canvas

    def beginnen(self, canvas, event):
        self.canvas = canvas
        self.skalierung = ctk.ScalingTracker.get_widget_scaling(self.app)
        self.start_x, self.start_y = event.x_root, event.y_root
        self.start_zeit = time.monotonic()
        self.position = canvas.yview()[0]        # als Kommazahl mitführen – sonst bleibt langsames Scrollen hängen

    def verschieben(self, px):
        """Seite um px weiter nach unten scrollen (negativ: nach oben). False, wenn sie dabei am Ende anstößt."""
        oben, unten = self.canvas.yview()
        sichtbar = unten - oben                  # Anteil der Seite im Fenster – daraus: px → Anteil
        self.position += px * sichtbar / max(self.canvas.winfo_height(), 1)
        ziel = min(max(self.position, 0.0), 1.0 - sichtbar)
        frei = ziel == self.position
        self.position = ziel
        self.canvas.yview_moveto(ziel)
        return frei

    def stop(self):
        """Mausrad-Klick-Scrollen bzw. Schwung beenden."""
        if self.job:
            self.app.after_cancel(self.job)
            self.job = None
        if self.symbol:
            self.symbol.grab_release()
            self.symbol.destroy()
            self.symbol = None
            self.app.configure(cursor="")

    # --- Mausrad-Klick ---
    def mitte_druecken(self, event):
        if self.symbol:
            self.stop()
            return
        self.stop()
        canvas = self.canvas_unter(event.widget)
        if canvas is None:
            return
        self.beginnen(canvas, event)
        self.bewegt = False
        self.symbol_zeigen()
        self.job = self.app.after(self.TAKT, self.schritt)

    def mitte_loslassen(self, event):
        if self.symbol and self.bewegt:          # gedrückt gehalten und gezogen – beim Loslassen ist Schluss
            self.stop()

    def symbol_zeigen(self):
        """Kreis mit Pfeilen hoch/runter an der Startstelle – schlichtes tk wie beim Tooltip."""
        dunkel = ctk.get_appearance_mode() == "Dark"
        farbe = lambda paar: paar[1] if dunkel else paar[0]         # noqa: E731
        g = round(30 * self.skalierung)
        self.symbol = symbol = tk.Toplevel(self.app)
        symbol.withdraw()
        symbol.overrideredirect(True)
        symbol.attributes("-topmost", True)
        symbol.attributes("-transparentcolor", self.DURCHSICHTIG)
        bild = tk.Canvas(symbol, width=g, height=g, bg=self.DURCHSICHTIG, highlightthickness=0,
                         cursor="sb_v_double_arrow")
        bild.pack()
        bild.create_oval(1, 1, g - 2, g - 2, fill=farbe(CARD), outline=farbe(MUTED),
                         width=max(1, round(self.skalierung)))
        m, b = g / 2, g * 0.16                   # Mitte, halbe Pfeilbreite
        bild.create_polygon(m, g * 0.14, m - b, g * 0.36, m + b, g * 0.36, fill=farbe(TEXT))
        bild.create_polygon(m, g * 0.86, m - b, g * 0.64, m + b, g * 0.64, fill=farbe(TEXT))
        symbol.geometry(f"+{self.start_x - g // 2}+{self.start_y - g // 2}")
        symbol.deiconify()
        self.app.configure(cursor="sb_v_double_arrow")
        self.festhalten()

    def festhalten(self):
        """Alle Mausklicks ans Symbol – klappt erst, wenn Windows es angezeigt hat, sonst gleich noch mal."""
        if not self.symbol:
            return
        try:
            self.symbol.grab_set()
        except tk.TclError:
            self.symbol.after(20, self.festhalten)

    def schritt(self):
        if not self.app.tk.call("focus") and time.monotonic() - self.start_zeit > self.ANLAUF:
            self.job = None
            self.stop()                          # anderes Programm im Vordergrund (z. B. Alt+Tab ins Spiel)
            return
        x, y = self.app.winfo_pointerxy()
        totzone = self.TOTZONE * self.skalierung
        if abs(x - self.start_x) > totzone or abs(y - self.start_y) > totzone:
            self.bewegt = True
        abstand = y - self.start_y
        tempo = max(abs(abstand) - totzone, 0) * self.TEMPO
        if tempo:
            self.verschieben(tempo if abstand > 0 else -tempo)
        self.job = self.app.after(self.TAKT, self.schritt)

    # --- Linksklick + ziehen ---
    def links_druecken(self, event):
        if self.symbol:                          # Mausrad-Klick-Scrollen läuft – dieser Klick beendet es nur
            self.stop()
            return
        self.stop()                              # gleitet die Seite noch, hält ein Klick sie an
        canvas = self.canvas_unter(event.widget)
        if canvas is None or self.ist_bedienelement(event.widget, canvas):
            return
        self.beginnen(canvas, event)
        self.gefasst, self.zieht = True, False
        self.letztes_y = event.y_root
        self.verlauf = [(self.start_zeit, event.y_root)]     # letzte Mauspositionen – daraus das Tempo beim Loslassen

    def ist_bedienelement(self, widget, canvas):
        while widget is not None and widget is not canvas:
            if isinstance(widget, self.BEDIENELEMENTE):
                return True
            widget = widget.master
        return False

    def links_ziehen(self, event):
        if not self.gefasst:
            return
        if not self.zieht:
            if abs(event.y_root - self.start_y) <= self.TOTZONE * self.skalierung:
                return                           # noch ein Klick, kein Ziehen
            self.zieht = True
            self.app.configure(cursor="fleur")
        self.verschieben(self.letztes_y - event.y_root)      # Maus runter = Inhalt runter = nach oben scrollen
        self.letztes_y = event.y_root
        jetzt = time.monotonic()
        self.verlauf = [(t, y) for t, y in self.verlauf if jetzt - t < 0.1] + [(jetzt, event.y_root)]

    def links_loslassen(self, event):
        if not self.gefasst:
            return
        self.gefasst = False
        if not self.zieht:
            return
        self.zieht = False
        self.app.configure(cursor="")
        # Schwung: Tempo der letzten 0,1 s – aber nur, wenn die Maus beim Loslassen noch in Bewegung war
        jetzt = time.monotonic()
        verlauf = [(t, y) for t, y in self.verlauf if jetzt - t < 0.1]
        if len(verlauf) >= 2 and jetzt - verlauf[-1][0] < 0.05:
            (t0, y0), (t1, y1) = verlauf[0], verlauf[-1]
            self.schwung = (y0 - y1) / max(t1 - t0, 0.001)           # px/s, positiv = nach unten scrollen
            if abs(self.schwung) >= self.MIN_SCHWUNG:
                self.job = self.app.after(self.TAKT, self.gleiten)

    def gleiten(self):
        self.schwung *= self.REIBUNG
        if abs(self.schwung) < 50 or not self.verschieben(self.schwung * self.TAKT / 1000):
            self.job = None                      # ausgerollt bzw. am Ende angestoßen
            return
        self.job = self.app.after(self.TAKT, self.gleiten)


# ---------- Hauptfenster ----------
class ToolboxApp(ctk.CTk):
    def __init__(self):
        self.settings = load_settings()
        ctk.set_appearance_mode(APPEARANCE[self.settings["appearance"]])
        ctk.set_widget_scaling(self.settings["zoom"])
        apply_theme()
        super().__init__()
        apply_font(self)

        # Titel = Pfad des Programms, wie beim Explorer: Im Task-Manager steht er unter „Toolbox“ und zeigt, welche
        # Kopie gerade läuft (z. B. nach dem Verschieben des Ordners). Der Name steht ja schon im Logo.
        self.title(str(Path(__file__).resolve()))
        self.geometry("1060x720")
        self.minsize(860, 540)
        self.set_window_icon()

        self.ui_queue = queue.Queue()           # Aufträge aus anderen Threads, die tkinter ausführen soll
        self.pages = {}                         # einmal gebaute Seiten bleiben erhalten
        self.current_page = None
        self.selected = {}                      # zuletzt gewähltes Programm je Tab
        self.sidebar_buttons = {}
        self.tab_buttons = {}
        self.tray = None
        self.toast_job = None
        self.zoom_job = None
        self.zoom_rest = 0                      # angefangene Rasten (Touchpads liefern Bruchteile davon)
        self.scrollen = Scrollen(self)

        self.columnconfigure(2, weight=1)
        self.rowconfigure(2, weight=1)
        self.build_topbar()
        self.build_sidebar()
        self.main = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self.main.grid(row=2, column=2, sticky="nsew")
        self.main.columnconfigure(0, weight=1)
        self.main.rowconfigure(0, weight=1)

        self.show_category(CATEGORIES[0])
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        # Strg + Mausrad ist genauer als das <MouseWheel> der Seiten – die scrollen dabei also nicht mit
        self.bind_all("<Control-MouseWheel>", self.zoom_mausrad)
        threading.Thread(target=self.instance_server, daemon=True).start()
        self.after(100, self.poll_queue)

    # --- Aufbau ---
    def set_window_icon(self):
        try:
            self.iconbitmap(str(ICON_FILE))      # nach iconbitmap() überschreibt CustomTkinter das Symbol nicht mehr
        except Exception:
            pass                                 # toolbox.ico fehlt – dann eben mit dem Standardsymbol

    def build_topbar(self):
        """Kopfleiste wie auf der Website: Name (Knopf zum GitHub-Repo), Tabs als schlichte Links, Linie darunter."""
        bar = ctk.CTkFrame(self, height=60, corner_radius=0, fg_color=BAR)
        bar.grid(row=0, column=0, columnspan=3, sticky="ew")
        bar.columnconfigure(2, weight=1)
        ctk.CTkFrame(self, height=1, corner_radius=0, fg_color=BORDER).grid(row=1, column=0, columnspan=3, sticky="ew")

        name = ctk.CTkButton(bar, text="Windows Toolbox", width=0, height=36, corner_radius=8, fg_color="transparent",
                             hover_color=HOVER, text_color=TEXT, font=ctk.CTkFont(size=17, weight="bold"),
                             cursor="hand2", command=lambda: webbrowser.open(GITHUB_URL))
        name.grid(row=0, column=0, padx=(12, 20), pady=12)
        Tooltip(name, f"Auf GitHub öffnen\n{GITHUB_URL}")

        tabs = ctk.CTkFrame(bar, fg_color="transparent")
        tabs.grid(row=0, column=1, sticky="w")
        for category in CATEGORIES:
            button = ctk.CTkButton(tabs, text=category, width=0, height=34, corner_radius=8, fg_color="transparent",
                                   hover_color=HOVER, text_color=MUTED, font=ctk.CTkFont(size=14, weight="bold"),
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
        self.sidebar.grid_propagate(False)       # feste Breite, auch bei kurzen Namen
        self.sidebar.columnconfigure(0, weight=1)
        ctk.CTkFrame(self, width=1, corner_radius=0, fg_color=BORDER).grid(row=2, column=1, sticky="ns")

    def mark(self, button, active):
        """Gewählten Tab/Eintrag hervorheben wie die aktiven Links der Website (grün getönt, heller Text)."""
        button.configure(fg_color=SELECTED if active else "transparent", text_color=TEXT if active else MUTED)

    # --- Navigation ---
    def show_category(self, category):
        for name, button in self.tab_buttons.items():
            self.mark(button, name == category)
        self.mark(self.gear, False)
        for child in self.sidebar.winfo_children():
            child.destroy()
        self.sidebar_buttons = {}

        ctk.CTkLabel(self.sidebar, text=category.upper(), text_color=MUTED, anchor="w",
                     font=ctk.CTkFont(size=11, weight="bold")).grid(row=0, column=0, sticky="ew", padx=14, pady=(16, 6))
        tools = sorted((t for t in TOOLS if t.category == category), key=lambda t: t.name.casefold())
        for row, tool in enumerate(tools, start=1):
            button = ctk.CTkButton(self.sidebar, text=tool.name, anchor="w", height=36, corner_radius=8,
                                   fg_color="transparent", text_color=MUTED, hover_color=HOVER,
                                   font=ctk.CTkFont(size=14, weight="bold"),
                                   command=lambda t=tool: self.show_tool(t))
            button.grid(row=row, column=0, sticky="ew", padx=8, pady=2)
            self.sidebar_buttons[tool.id] = button
        if not tools:
            # Nur auf „Installieren“ verweisen, wenn es für diesen Tab auch etwas zu installieren gibt
            fehlt = any(a.get("kategorie") == category and a["id"] not in INSTALLIERT for a in AUSWEISE)
            text = "Noch keine Programme –\ninstallieren unter ⚙ → Programme" if fehlt else "Noch keine Programme"
            ctk.CTkLabel(self.sidebar, text=text, text_color=MUTED, justify="left").grid(
                row=1, column=0, sticky="w", padx=12)
            self.show_page(None)
            return
        remembered = self.selected.get(category)
        self.show_tool(next((t for t in tools if t.id == remembered), tools[0]))

    def show_tool(self, tool):
        self.selected[tool.category] = tool.id
        for name, button in self.tab_buttons.items():       # wieder grün, falls vorher das Zahnrad gewählt war
            self.mark(button, name == tool.category)
        self.mark(self.gear, False)
        for tool_id, button in self.sidebar_buttons.items():
            self.mark(button, tool_id == tool.id)
        if tool.id not in self.pages:
            self.pages[tool.id] = tool.page(self.main, self, tool)
        self.show_page(self.pages[tool.id])

    def show_settings(self):
        for button in (*self.tab_buttons.values(), *self.sidebar_buttons.values()):
            self.mark(button, False)
        self.mark(self.gear, True)
        if "_settings" not in self.pages:
            info = ToolInfo("_settings", "Einstellungen", "", "Einstellungen der Toolbox selbst.", GuiSettingsPage)
            self.pages["_settings"] = GuiSettingsPage(self.main, self, info)
        self.show_page(self.pages["_settings"])

    def show_page(self, page):
        if self.current_page is page:
            return
        self.scrollen.stop()
        if self.current_page is not None:
            self.current_page.on_hide()
            self.current_page.grid_forget()
        self.current_page = page
        if page is not None:
            page.grid(row=0, column=0, sticky="nsew")
            page.on_show()

    # --- Zoom ---
    def zoom_mausrad(self, event):
        """Strg + Mausrad: alles größer bzw. kleiner wie im Browser, wird gemerkt. Die Anzeige oben rechts kommt
        sofort, das Umrechnen erst kurz nach der letzten Raste – alles neu zu skalieren dauert einen Moment."""
        self.zoom_rest += event.delta
        rasten = int(self.zoom_rest / 120)        # 120 = eine Raste
        if rasten:
            self.zoom_rest -= rasten * 120
            stufe = min(max(ZOOM_STUFEN.index(self.settings["zoom"]) + rasten, 0), len(ZOOM_STUFEN) - 1)
            self.settings["zoom"] = ZOOM_STUFEN[stufe]
            self.toast(f"Zoom {round(ZOOM_STUFEN[stufe] * 100)} %")
            if self.zoom_job:
                self.after_cancel(self.zoom_job)
            self.zoom_job = self.after(150, self.zoom_anwenden)
        return "break"

    def zoom_anwenden(self):
        self.zoom_job = None
        ctk.set_widget_scaling(self.settings["zoom"])
        if not save_settings(self.settings):
            self.toast("Zoom konnte nicht gespeichert werden", error=True)

    # --- Hilfen für Programmseiten ---
    def save(self):
        if save_settings(self.settings):
            self.toast("Gespeichert ✓")
        else:
            self.toast("Speichern fehlgeschlagen", error=True)

    def toast(self, text, error=False):
        """Kurze Meldung oben rechts, verschwindet nach ein paar Sekunden."""
        self.toast_label.configure(text=text, text_color=BAD if error else GOOD)
        if self.toast_job:
            self.after_cancel(self.toast_job)
        self.toast_job = self.after(2500, lambda: self.toast_label.configure(text=""))

    def run_async(self, func, on_done=None):
        """func im Hintergrund ausführen (damit das Fenster nicht einfriert), on_done(ergebnis) danach im GUI-Thread."""
        def worker():
            try:
                result = func()
            except Exception:
                logging.exception("Fehler in Hintergrundaufgabe")
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
                elif task == "quit":
                    self.quit_app()
                    return
                else:
                    task()
        except queue.Empty:
            pass
        self.after(100, self.poll_queue)

    # --- Schließen, Infobereich ---
    def on_close(self):
        if self.settings["close_to_tray"]:
            self.hide_to_tray()
        else:
            self.quit_app()

    def hide_to_tray(self):
        self.scrollen.stop()
        if self.current_page is not None:
            self.current_page.on_hide()          # z. B. keine Status-Abfragen, solange das Fenster weg ist
        self.withdraw()
        if self.tray is None:
            try:
                import pystray
                menu = pystray.Menu(
                    pystray.MenuItem("Toolbox öffnen", lambda icon, item: self.ui_queue.put("show"), default=True),
                    pystray.MenuItem("Beenden", lambda icon, item: self.ui_queue.put("quit")),
                )
                self.tray = pystray.Icon("toolbox", Image.open(ICON_FILE), "Toolbox", menu)
                self.tray.run_detached()
            except Exception:
                logging.exception("Tray-Symbol konnte nicht angelegt werden – Toolbox wird stattdessen beendet")
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

    def neu_starten(self):
        """Startet eine neue Toolbox und beendet diese. Die neue wartet mit --nach <pid>, bis diese wirklich zu ist –
        sonst fände sie die alte noch laufend und holte nur deren Fenster nach vorne."""
        exe = str(TOOLBOX_EXE) if TOOLBOX_EXE.exists() else winutil.pythonw_exe()
        try:
            subprocess.Popen([exe, str(Path(__file__).resolve()), "--nach", str(os.getpid())],
                             cwd=str(ROOT), creationflags=winutil.CREATE_NO_WINDOW)
        except OSError:
            logging.exception("Neue Toolbox konnte nicht gestartet werden")
            self.toast("Neustart fehlgeschlagen", error=True)
            return
        self.quit_app()

    def instance_server(self):
        """Befehle über eine lokale Verbindung, je einer pro Verbindung, Antwort "ok":
          show    ein zweiter Toolbox-Start holt damit dieses Fenster nach vorne
          status  läuft die Toolbox? (setup.ps1 fragt vor dem Einrichten)
          quit    beenden (setup.ps1, damit es runtime\\ erneuern bzw. löschen kann)"""
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.bind(("127.0.0.1", GUI_PORT))
            server.listen()
        except OSError:
            logging.warning("Port %s belegt – zweiter Start kann dieses Fenster nicht nach vorne holen", GUI_PORT)
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
                        command = conn.recv(16).strip()
                        if command in (b"show", b"quit"):
                            self.ui_queue.put(command.decode())
                        if command in (b"show", b"status", b"quit"):
                            conn.sendall(b"ok\n")
                    except OSError:
                        pass


def main():
    if "--nach" in sys.argv:                     # Neustart (neu_starten): erst warten, bis die alte Toolbox zu ist
        try:
            winutil.wait_for_exit(int(sys.argv[sys.argv.index("--nach") + 1]), timeout=10)
        except (IndexError, ValueError):
            pass
    if bring_existing_to_front():
        return
    # Eigene App-ID: sonst zeigt die Taskleiste das Python-Symbol statt des Toolbox-Symbols
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Toolbox.Tools")
    try:
        ToolboxApp().mainloop()
    except Exception:
        logging.exception("Unerwarteter Fehler")
        raise


if __name__ == "__main__":
    main()
