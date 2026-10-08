"""
Toolbox – eine Oberfläche für die selbst geschriebenen kleinen Windows-Tools.

Aufbau:
  oben     Tabs für die Arten von Programmen + Zahnrad für die Einstellungen der Toolbox selbst
  links    alle Programme des gewählten Tabs, alphabetisch
  rechts   die Einstellungen des gewählten Programms

Start:          Doppelklick auf Toolbox.pyw im Repo (oder: pythonw src\\gui\\toolbox.py)
Voraussetzung:  pip install customtkinter pystray pillow

Programme werden automatisch gefunden: jede Datei src/<programm>/<programm>_gui.py mit einem Eintrag TOOL.
Einstellungen der Toolbox: toolbox_settings.json, Fehler: toolbox.log (beides neben diesem Skript).
"""

import ctypes
import importlib.util
import json
import logging
import queue
import socket
import sys
import threading
from pathlib import Path

import customtkinter as ctk
from PIL import Image

sys.dont_write_bytecode = True             # keine __pycache__-Ordner im Projekt anlegen

APP_DIR = Path(__file__).resolve().parent
SRC_DIR = APP_DIR.parent                   # hier liegt je Programm ein Ordner (hardware_monitor\, …)
sys.path.insert(0, str(APP_DIR))           # damit base, winutil usw. gefunden werden – auch von den Programmseiten

from base import GOOD, MUTED, Choice, Section, Switch, Text, ToolInfo, ToolPage  # noqa: E402
from platzhalter import PlatzhalterPage  # noqa: E402

CATEGORIES = ["Allgemein", "Werkzeuge", "Medien", "Netzwerk"]     # Tabs oben, in dieser Reihenfolge
PLACEHOLDERS = [
    ToolInfo("xxx-werkzeuge", "XXX", "Werkzeuge", "Platzhalter", PlatzhalterPage),
    ToolInfo("xxx-medien", "XXX", "Medien", "Platzhalter", PlatzhalterPage),
    ToolInfo("xxx-netzwerk", "XXX", "Netzwerk", "Platzhalter", PlatzhalterPage),
]

VERSION = "1.0"
SETTINGS_FILE = APP_DIR / "toolbox_settings.json"
ICON_FILE = APP_DIR / "toolbox.ico"        # Werkzeugkoffer auf blauem Grund
GUI_PORT = 47816                 # damit ein zweiter Start nur das schon laufende Fenster nach vorne holt

APPEARANCE = {"Hell": "light", "Dunkel": "dark", "System": "system"}
DEFAULT_SETTINGS = {
    "appearance": "System",
    "close_to_tray": True,
    "tools": {},                               # eigene Einstellungen der einzelnen Programmseiten
}

logging.basicConfig(filename=APP_DIR / "toolbox.log", level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")


# ---------- Programme finden ----------
def find_tools():
    """Lädt jede src/<programm>/*_gui.py und sammelt deren TOOL-Eintrag.
    Eine fehlerhafte Seite wird nur protokolliert, damit die übrigen Programme trotzdem erscheinen."""
    tools = []
    for file in sorted(SRC_DIR.glob("*/*_gui.py")):
        try:
            spec = importlib.util.spec_from_file_location(file.stem, file)
            module = importlib.util.module_from_spec(spec)
            sys.modules[file.stem] = module
            spec.loader.exec_module(module)
            tools.append(module.TOOL)
        except Exception:
            logging.exception("Programmseite %s konnte nicht geladen werden", file)
    return tools


TOOLS = find_tools() + PLACEHOLDERS


# ---------- Einstellungen ----------
def load_settings():
    settings = json.loads(json.dumps(DEFAULT_SETTINGS))          # tiefe Kopie
    try:
        saved = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        if isinstance(saved, dict):
            if saved.get("appearance") in APPEARANCE:
                settings["appearance"] = saved["appearance"]
            if isinstance(saved.get("close_to_tray"), bool):
                settings["close_to_tray"] = saved["close_to_tray"]
            if isinstance(saved.get("tools"), dict):
                settings["tools"] = saved["tools"]
    except (OSError, ValueError):
        pass
    return settings


def save_settings(settings):
    try:
        SETTINGS_FILE.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")
        return True
    except OSError:
        logging.exception("Einstellungen der Toolbox konnten nicht gespeichert werden")
        return False


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
    """Einstellungen der Toolbox selbst – liegen in self.app.settings (toolbox_settings.json)."""

    def load(self):
        return self.app.settings

    def save(self):
        self.app.save()

    def layout(self):
        return [
            Section("Darstellung", Choice("Design", "appearance", list(APPEARANCE))),
            Section("Fenster",
                    Switch("Beim Schließen in den Infobereich minimieren", key="close_to_tray"),
                    Text("Die Toolbox läuft dann unten rechts als Symbol weiter. Doppelklick bzw. Klick öffnet sie "
                         "wieder, Rechtsklick → Beenden schließt sie ganz.")),
            Section("Info", Text(f"Toolbox {VERSION}\nEinstellungen: {SETTINGS_FILE}")),
        ]

    def on_change(self, key, value):
        if key == "appearance":
            ctk.set_appearance_mode(APPEARANCE[value])
        elif key == "close_to_tray" and not value:
            self.app.stop_tray()


# ---------- Hauptfenster ----------
class ToolboxApp(ctk.CTk):
    def __init__(self):
        self.settings = load_settings()
        ctk.set_appearance_mode(APPEARANCE[self.settings["appearance"]])
        ctk.set_default_color_theme("blue")
        super().__init__()

        self.title("Toolbox")
        self.geometry("1060x720")
        self.minsize(860, 540)
        self.set_window_icon()

        self.ui_queue = queue.Queue()           # Aufträge aus anderen Threads, die tkinter ausführen soll
        self.pages = {}                         # einmal gebaute Seiten bleiben erhalten
        self.current_page = None
        self.selected = {}                      # zuletzt gewähltes Programm je Tab
        self.sidebar_buttons = {}
        self.tray = None
        self.toast_job = None

        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)
        self.build_topbar()
        self.build_sidebar()
        self.main = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self.main.grid(row=1, column=1, sticky="nsew")
        self.main.columnconfigure(0, weight=1)
        self.main.rowconfigure(0, weight=1)

        self.show_category(CATEGORIES[0])
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        threading.Thread(target=self.instance_server, daemon=True).start()
        self.after(100, self.poll_queue)

    # --- Aufbau ---
    def set_window_icon(self):
        try:
            self.iconbitmap(str(ICON_FILE))      # nach iconbitmap() überschreibt CustomTkinter das Symbol nicht mehr
        except Exception:
            pass                                 # z. B. außerhalb von Windows

    def build_topbar(self):
        bar = ctk.CTkFrame(self, height=60, corner_radius=0, fg_color=("gray86", "gray14"))
        bar.grid(row=0, column=0, columnspan=2, sticky="ew")
        bar.columnconfigure(1, weight=1)

        ctk.CTkLabel(bar, text="  Toolbox", font=ctk.CTkFont(size=20, weight="bold"),
                     image=ctk.CTkImage(Image.open(ICON_FILE), size=(28, 28)), compound="left").grid(
            row=0, column=0, padx=(18, 24), pady=12)
        self.tabs = ctk.CTkSegmentedButton(bar, values=CATEGORIES, command=self.show_category,
                                           font=ctk.CTkFont(size=14), height=34)
        self.tabs.grid(row=0, column=1, sticky="w")
        self.toast_label = ctk.CTkLabel(bar, text="", text_color=GOOD, font=ctk.CTkFont(size=13))
        self.toast_label.grid(row=0, column=2, padx=12)
        self.gear = ctk.CTkButton(bar, text="⚙", width=40, height=36, font=ctk.CTkFont(size=22),
                                  fg_color="transparent", text_color=("gray20", "gray85"),
                                  hover_color=("gray78", "gray25"), command=self.show_settings)
        self.gear.grid(row=0, column=3, padx=(0, 16))

    def build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=230, corner_radius=0, fg_color=("gray88", "gray16"))
        self.sidebar.grid(row=1, column=0, sticky="nsw")
        self.sidebar.grid_propagate(False)       # feste Breite, auch bei kurzen Namen
        self.sidebar.columnconfigure(0, weight=1)

    # --- Navigation ---
    def show_category(self, category):
        self.tabs.set(category)
        for child in self.sidebar.winfo_children():
            child.destroy()
        self.sidebar_buttons = {}

        ctk.CTkLabel(self.sidebar, text=category.upper(), text_color=MUTED, anchor="w",
                     font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=0, sticky="ew", padx=12, pady=(14, 6))
        tools = sorted((t for t in TOOLS if t.category == category), key=lambda t: t.name.casefold())
        for row, tool in enumerate(tools, start=1):
            button = ctk.CTkButton(self.sidebar, text=tool.name, anchor="w", height=36, corner_radius=8,
                                   fg_color="transparent", text_color=("gray10", "gray90"),
                                   hover_color=("gray80", "gray24"), font=ctk.CTkFont(size=14),
                                   command=lambda t=tool: self.show_tool(t))
            button.grid(row=row, column=0, sticky="ew", padx=8, pady=2)
            self.sidebar_buttons[tool.id] = button
        if not tools:
            ctk.CTkLabel(self.sidebar, text="Noch keine Programme", text_color=MUTED).grid(
                row=1, column=0, sticky="w", padx=12)
            self.show_page(None)
            return
        remembered = self.selected.get(category)
        self.show_tool(next((t for t in tools if t.id == remembered), tools[0]))

    def show_tool(self, tool):
        self.selected[tool.category] = tool.id
        for tool_id, button in self.sidebar_buttons.items():
            button.configure(fg_color=("gray78", "gray26") if tool_id == tool.id else "transparent")
        if tool.id not in self.pages:
            self.pages[tool.id] = tool.page(self.main, self, tool)
        self.show_page(self.pages[tool.id])

    def show_settings(self):
        for button in self.sidebar_buttons.values():
            button.configure(fg_color="transparent")
        if "_settings" not in self.pages:
            info = ToolInfo("_settings", "Einstellungen", "", "Einstellungen der Toolbox selbst.", GuiSettingsPage)
            self.pages["_settings"] = GuiSettingsPage(self.main, self, info)
        self.show_page(self.pages["_settings"])

    def show_page(self, page):
        if self.current_page is page:
            return
        if self.current_page is not None:
            self.current_page.on_hide()
            self.current_page.grid_forget()
        self.current_page = page
        if page is not None:
            page.grid(row=0, column=0, sticky="nsew")
            page.on_show()

    # --- Hilfen für Programmseiten ---
    def tool_settings(self, tool_id):
        """Eigene Einstellungen einer Programmseite (werden mit den Toolbox-Einstellungen gespeichert)."""
        return self.settings["tools"].setdefault(tool_id, {})

    def save(self):
        if save_settings(self.settings):
            self.toast("Gespeichert ✓")
        else:
            self.toast("Speichern fehlgeschlagen", error=True)

    def toast(self, text, error=False):
        """Kurze Meldung oben rechts, verschwindet nach ein paar Sekunden."""
        self.toast_label.configure(text=text, text_color=("#c0392b", "#f87171") if error else GOOD)
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

    def instance_server(self):
        """Nimmt "show" von einem zweiten Toolbox-Start entgegen und holt dann dieses Fenster nach vorne."""
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if sys.platform != "win32":
                server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
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
                        if conn.recv(16).strip() == b"show":
                            self.ui_queue.put("show")
                            conn.sendall(b"ok\n")
                    except OSError:
                        pass


def main():
    if bring_existing_to_front():
        return
    try:
        # Eigene App-ID: sonst zeigt die Taskleiste das Python-Symbol statt des Toolbox-Symbols
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Toolbox.Tools")
    except Exception:
        pass
    try:
        ToolboxApp().mainloop()
    except Exception:
        logging.exception("Unerwarteter Fehler")
        raise


if __name__ == "__main__":
    main()
