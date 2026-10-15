"""
discord_plus.py – Discord Plus: Erweiterungen für Discord, die im Hintergrund laufen.

Bisher eine Funktion, der Call-Status: zeigt in Discord „Im Call“ an, sobald du in einem Anruf oder Voice-Chat
bist. Discord zeigt Server-Voice-Chats nur Leuten mit Zugriff auf den Server, private Anrufe niemandem. Dieses Programm
setzt deshalb eine eigene Aktivität (Rich Presence, „Spielt …“) – die sehen alle, die auch sonst sehen, was du spielst.

Dateien:
  discord_plus.py                 dieses Programm: läuft unsichtbar, Symbol im Infobereich, Fernsteuerung durch die Toolbox
  discord_ipc.py                  spricht mit der Discord-App (Named Pipe) und mit discord.com (Anmeldung)
  discord_plus_settings.py   Startwerte, Laden/Speichern und was angezeigt wird (aktivitaet) – gemeinsam mit der Seite
  discord_plus_gui.py             seine Seite in der Toolbox, mit der Anleitung zur einmaligen Einrichtung

Ablauf (Call-Status): Alle paar Sekunden fragt das Programm die Discord-App, in welchem Sprachkanal du bist
(GET_SELECTED_VOICE_CHANNEL) – das schließt private Anrufe und Gruppenanrufe ein. Ändert sich etwas, setzt es die
Aktivität neu (SET_ACTIVITY) oder löscht sie. Dafür muss es einmal angemeldet sein: „Verbinden“ auf der Toolbox-Seite
schickt den Befehl "verbinden", dann fragt Discord in der App nach. Von selbst fragt das Programm nie – so poppt
mitten im Spiel nichts auf.

Aufruf:  pythonw discord_plus.py   (oder DiscordPlus.exe, legt Setup.exe an)
Alle Texte (Symbol, Meldungen an die Toolbox) stehen in i18n.json; die Sprache liest es beim Start und bei "reload".
Fehler landen in daten/logs/discord_plus.log (pythonw hat keine Konsole).
"""

import ctypes
import json
import logging
import os
import queue
import socket
import sys
import threading
import time
from pathlib import Path

sys.dont_write_bytecode = True                              # keine __pycache__-Ordner anlegen (wie bei der Toolbox)
sys.path.insert(0, str(Path(__file__).resolve().parent))    # Nachbardateien finden – auch beim Start mit python -m
from discord_ipc import DiscordFehler, Verbindung, token_holen  # noqa: E402
from discord_plus_settings import (ANMELDUNG_FILE, AUSWEIS, IPC_PORT, LOG_FILE, REDIRECT_URI,  # noqa: E402
                                          aktivitaet, load_settings, save_settings, t)

import storage  # noqa: E402  (liegt in toolbox\, den Pfad setzt discord_plus_settings)
import i18n  # noqa: E402
import winutil  # noqa: E402

logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

ABFRAGE = 3              # Sekunden zwischen zwei Abfragen, solange Discord läuft
WARTEN = 15              # Sekunden bis zum nächsten Versuch, wenn Discord nicht läuft oder etwas fehlt
ICON_DATEI = Path(__file__).resolve().with_name(AUSWEIS["icon"])    # Discord-Kreis mit Gesicht (build_logo.py)
ART = {1: "privat", 3: "gruppe"}                                                   # Discord-Kanaltypen; sonst Server


def kanal_lesen(daten_kanal, ich):
    """Antwort von GET_SELECTED_VOICE_CHANNEL -> das, was aktivitaet() braucht (siehe dort). ich: deine Nutzer-ID."""
    andere = []
    for v in daten_kanal.get("voice_states") or []:
        nutzer = v.get("user") or {}
        if nutzer.get("id") == ich:
            continue
        # nick = Spitzname (Server oder Freundesliste), sonst Anzeigename, sonst Benutzername
        name = v.get("nick") or nutzer.get("global_name") or nutzer.get("username") or "?"
        avatar = (f"https://cdn.discordapp.com/avatars/{nutzer['id']}/{nutzer['avatar']}.png?size=256"
                  if nutzer.get("avatar") and nutzer.get("id") else None)
        andere.append({"name": name, "avatar": avatar})
    return {"art": ART.get(daten_kanal.get("type"), "server"), "id": daten_kanal.get("id"),
            "name": daten_kanal.get("name") or "", "guild_id": daten_kanal.get("guild_id"), "andere": andere}


def kanal_text(kanal):
    """Für die Toolbox: was Discord gerade meldet, z. B. „Privater Anruf mit Anna“."""
    if kanal is None:
        return t("kanal.keiner")
    namen = ", ".join(a["name"] for a in kanal["andere"]) or t("kanal.niemand")
    if kanal["art"] == "server":
        ort = " · ".join(teil for teil in (kanal.get("server"), kanal["name"]) if teil)
        return t("kanal.server", ort=ort, namen=namen)
    return t("kanal.privat" if kanal["art"] == "privat" else "kanal.gruppe", namen=namen)


class DiscordPlus:
    """Der Wächter-Thread hält die Verbindung zu Discord; Befehle von der Toolbox und vom Symbol kommen über
    self.befehle bei ihm an – so spricht immer nur ein Thread mit Discord."""

    def __init__(self):
        self.settings = load_settings()
        self.anmeldung = storage.load(ANMELDUNG_FILE, {})
        self.befehle = queue.Queue()
        self.stop = threading.Event()
        self.verbindung = None
        self.angemeldet = False          # AUTHENTICATE auf dieser Verbindung geklappt
        self.ich = None                  # deine Nutzer-ID (aus AUTHENTICATE) – dich selbst nicht als „mit …“ zeigen
        self.verbinden_fehler = None     # warum das letzte „Verbinden“ nicht geklappt hat (bleibt bis zum nächsten)
        self.server_namen = {}           # guild_id -> Name (fragt Discord nur einmal je Server)
        self.call = None                 # (Kanal-ID, Startzeit) des aktuellen Calls
        self.gesetzt = None              # zuletzt an Discord geschickte Aktivität (nur bei Änderung neu senden)
        # Für die Statusabfrage der Toolbox und den Tooltip des Symbols
        self.zustand = "start"           # einrichtung, discord_fehlt, nicht_angemeldet, warte, bereit, im_call, fehler
        self.meldung = t("meldung.startet")
        self.kanal = None
        self.lock = threading.Lock()
        self.icon = None

    # ---------- Zustand ----------
    def melden(self, zustand, meldung, kanal=None):
        with self.lock:
            geaendert = (zustand, meldung) != (self.zustand, self.meldung)
            self.zustand, self.meldung, self.kanal = zustand, meldung, kanal
        if geaendert:
            if zustand == "fehler":
                logging.warning("%s", meldung)
            if self.icon:
                self.icon.title = f"Discord Plus: {meldung}"[:127]      # Windows erlaubt höchstens 127 Zeichen
                self.icon.update_menu()

    def status(self):
        with self.lock:
            return {"ok": True, "pid": os.getpid(), "zustand": self.zustand, "meldung": self.meldung,
                    "erkannt": kanal_text(self.kanal) if self.angemeldet else None,
                    "nutzer": self.anmeldung.get("nutzer"), "app": self.anmeldung.get("app"),
                    "anzeige": self.gesetzt}

    # ---------- Anmeldung ----------
    def anmeldung_speichern(self, token, **mehr):
        self.anmeldung.update({
            "client_id": self.settings["client_id"],
            "access_token": token["access_token"],
            "refresh_token": token.get("refresh_token", self.anmeldung.get("refresh_token")),
            "ablauf": time.time() + int(token.get("expires_in", 0)),
        }, **mehr)
        try:
            storage.save(ANMELDUNG_FILE, self.anmeldung)
        except OSError:
            logging.exception("Anmeldung konnte nicht gespeichert werden")

    def anmelden(self):
        """Mit dem gespeicherten Token anmelden – läuft es bald ab oder ist es ungültig, vorher erneuern.
        True, wenn es geklappt hat; False, wenn es neu „Verbinden“ braucht."""
        s, a = self.settings, self.anmeldung
        if a.get("client_id") != s["client_id"] or not a.get("access_token"):
            return False
        if a.get("ablauf", 0) - time.time() < 24 * 3600 and not self.erneuern():
            return False
        try:
            self.angemeldet_mit(self.verbindung.anmelden(a["access_token"]))
            return True
        except DiscordFehler as fehler:
            logging.info("Token abgelehnt (%s) – wird erneuert", fehler)
        if not self.erneuern():
            return False
        self.angemeldet_mit(self.verbindung.anmelden(self.anmeldung["access_token"]))
        return True

    def erneuern(self):
        """Neues Token mit dem refresh_token holen (ohne Nachfrage in Discord)."""
        if not self.anmeldung.get("refresh_token"):
            return False
        try:
            token = token_holen(self.settings["client_id"], self.settings["client_secret"],
                                grant_type="refresh_token", refresh_token=self.anmeldung["refresh_token"])
        except DiscordFehler as fehler:
            logging.warning("Token erneuern: %s", fehler)
            self.anmeldung.pop("access_token", None)      # abgelaufen oder widerrufen -> neu verbinden
            return False
        self.anmeldung_speichern(token)
        return True

    def angemeldet_mit(self, antwort):
        self.angemeldet = True
        self.verbinden_fehler = None
        nutzer = (antwort or {}).get("user") or {}
        app = ((antwort or {}).get("application") or {}).get("name")
        self.ich = nutzer.get("id")
        neu = {"nutzer": nutzer.get("global_name") or nutzer.get("username"), "app": app}
        if any(self.anmeldung.get(k) != v for k, v in neu.items()):
            self.anmeldung.update(neu)
            try:
                storage.save(ANMELDUNG_FILE, self.anmeldung)
            except OSError:
                logging.exception("Anmeldung konnte nicht gespeichert werden")

    def verbinden(self):
        """„Verbinden“ in der Toolbox: Discord fragt in der App nach – wartet, bis du dort klickst."""
        s = self.settings
        if not (s["client_id"] and s["client_secret"]):
            self.melden("einrichtung", t("meldung.zugang_fehlt"))
            return
        try:
            self.verbunden()
        except OSError:
            self.melden("discord_fehlt", t("meldung.discord_starten"))
            return
        except DiscordFehler as fehler:
            self.melden("fehler", t("meldung.client_id_abgelehnt", fehler=fehler))
            return
        self.melden("warte", t("meldung.autorisieren"))
        try:
            code = self.verbindung.autorisieren()
            token = token_holen(s["client_id"], s["client_secret"], grant_type="authorization_code", code=code,
                                redirect_uri=REDIRECT_URI)
            self.anmeldung_speichern(token)
            self.angemeldet_mit(self.verbindung.anmelden(token["access_token"]))
            logging.info("Mit Discord verbunden als %s", self.anmeldung.get("nutzer"))
        except DiscordFehler as fehler:
            self.verbinden_fehler = str(fehler)
        except OSError as fehler:
            self.trennen()
            self.verbinden_fehler = str(fehler)
        if self.verbinden_fehler:
            logging.warning("Verbinden fehlgeschlagen: %s", self.verbinden_fehler)

    def abmelden(self):
        for key in ("access_token", "refresh_token", "ablauf", "nutzer", "app"):
            self.anmeldung.pop(key, None)
        try:
            storage.save(ANMELDUNG_FILE, self.anmeldung)
        except OSError:
            logging.exception("Anmeldung konnte nicht gespeichert werden")
        self.trennen()                   # löscht auch die Aktivität

    # ---------- Verbindung ----------
    def verbunden(self):
        """Verbindung zu Discord herstellen, falls es noch keine (für diese Client-ID) gibt. Wirft OSError."""
        if self.verbindung and self.verbindung.client_id != self.settings["client_id"]:
            self.trennen()
        if self.verbindung is None:
            self.verbindung = Verbindung(self.settings["client_id"])
            self.angemeldet = False
            self.gesetzt = None

    def trennen(self):
        if self.verbindung:
            self.verbindung.schliessen()
        self.verbindung = None
        self.angemeldet = False
        self.gesetzt = None
        self.call = None

    def schritt(self):
        """Eine Abfrage: Wo bist du gerade, und passt die Anzeige in Discord dazu? Gibt die Wartezeit zurück."""
        s = self.settings
        if not (s["client_id"] and s["client_secret"]):
            self.trennen()
            self.melden("einrichtung", t("meldung.einrichtung"))
            return WARTEN
        try:
            self.verbunden()
            if not self.angemeldet and not self.anmelden():
                if self.verbinden_fehler:
                    self.melden("fehler", t("meldung.verbinden_fehlgeschlagen", fehler=self.verbinden_fehler))
                else:
                    self.melden("nicht_angemeldet", t("meldung.nicht_verbunden"))
                return WARTEN
            antwort = self.verbindung.sprachkanal()
            kanal = kanal_lesen(antwort, self.ich) if antwort else None
            if kanal and kanal["art"] == "server" and kanal["guild_id"]:
                kanal["server"] = self.server_name(kanal["guild_id"])
            self.anzeigen(kanal)
            return ABFRAGE
        except DiscordFehler as fehler:
            self.trennen()
            self.melden("fehler", t("meldung.discord_fehler", fehler=fehler, code=fehler.code))
            return WARTEN
        except (OSError, ValueError):
            self.trennen()
            self.melden("discord_fehlt", t("meldung.discord_fehlt"))
            return WARTEN

    def server_name(self, guild_id):
        if guild_id not in self.server_namen:
            try:
                self.server_namen[guild_id] = (self.verbindung.server(guild_id) or {}).get("name") or ""
            except DiscordFehler:
                self.server_namen[guild_id] = ""
        return self.server_namen[guild_id]

    def anzeigen(self, kanal):
        """Aktivität passend zum Kanal setzen oder löschen – nur, wenn sie sich ändert (Discord erlaubt höchstens
        5 Änderungen in 20 Sekunden)."""
        if kanal is None:
            self.call = None
        elif self.call is None or self.call[0] != kanal["id"]:
            self.call = (kanal["id"], time.time())                      # neuer Call: Dauer zählt ab jetzt
        neu = aktivitaet(kanal, self.settings, self.call[1] if self.call else 0)
        if neu != self.gesetzt:
            self.verbindung.aktivitaet_setzen(os.getpid(), neu)
            self.gesetzt = neu
        if not self.settings["call_status"]:
            self.melden("bereit", t("meldung.pausiert"), kanal)
        elif neu:
            text = neu["details"] + (f" · {neu['state']}" if neu.get("state") else "")
            self.melden("im_call", t("meldung.zeigt_an", text=text), kanal)
        elif kanal:
            self.melden("bereit", t("meldung.nicht_angezeigt"), kanal)
        else:
            self.melden("bereit", t("meldung.kein_call"), kanal)

    # ---------- Wächter-Thread ----------
    def waechter(self):
        warten = 0
        while not self.stop.is_set():
            try:
                befehl = self.befehle.get(timeout=warten)
            except queue.Empty:
                befehl = None
            if befehl == "quit":
                break
            if befehl == "reload":
                if i18n.reload() and self.icon:   # Sprache in der Toolbox umgestellt: Menü sofort neu beschriften
                    self.icon.update_menu()
                self.settings.update(load_settings())       # Standardtexte in Discord dann auch in der neuen Sprache
            elif befehl == "verbinden":
                self.verbinden()
            elif befehl == "abmelden":
                self.abmelden()
            try:
                warten = self.schritt()
            except Exception:
                logging.exception("Unerwarteter Fehler bei der Abfrage")
                self.trennen()
                warten = WARTEN
        self.trennen()

    # ---------- Fernsteuerung durch die Toolbox ----------
    def ipc_server(self):
        """Befehle der Toolbox, einer pro Verbindung: status, reload, verbinden, abmelden, quit."""
        server = None
        while server is None and not self.stop.is_set():
            try:
                server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                server.bind(("127.0.0.1", IPC_PORT))         # nur von diesem PC aus erreichbar
                server.listen()
            except OSError:
                server.close()
                server = None
                self.stop.wait(2)                            # Port noch belegt (z. B. direkt nach Neustart)
        if server is None:
            return
        with server:
            while not self.stop.is_set():
                try:
                    conn, _ = server.accept()
                except OSError:
                    break
                with conn:
                    try:
                        conn.settimeout(1)
                        befehl = conn.recv(64).decode("utf-8", "replace").strip()
                        if befehl == "status":
                            antwort = self.status()
                        elif befehl in ("reload", "verbinden", "abmelden"):
                            self.befehle.put(befehl)
                            antwort = {"ok": True}
                        elif befehl == "quit":
                            self.beenden()
                            antwort = {"ok": True}
                        else:
                            antwort = {"ok": False, "error": f"Unbekannter Befehl: {befehl}"}
                        conn.sendall((json.dumps(antwort) + "\n").encode("utf-8"))
                    except OSError:
                        pass

    # ---------- Symbol im Infobereich ----------
    def symbol(self):
        import pystray
        from PIL import Image

        def pausieren(icon, item):
            self.settings["call_status"] = not self.settings["call_status"]
            try:
                save_settings(self.settings)
            except OSError:
                logging.exception("Einstellungen konnten nicht gespeichert werden")
            self.befehle.put("reload")

        menue = pystray.Menu(
            pystray.MenuItem(lambda item: self.meldung, None, enabled=False),
            pystray.Menu.SEPARATOR,
            # Texte als Funktionen: pystray fragt sie bei jedem update_menu() neu (Sprachwechsel)
            pystray.MenuItem(lambda item: t("menue.einstellungen"), lambda icon, item: threading.Thread(
                target=winutil.open_toolbox, args=(AUSWEIS["id"],), daemon=True).start(), default=True),
            pystray.MenuItem(lambda item: t("menue.call_status"), pausieren,
                             checked=lambda item: self.settings["call_status"]),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(lambda item: f"✕  {t('menue.beenden')}", lambda icon, item: self.beenden()),
        )
        bild = Image.open(ICON_DATEI).convert("RGBA").resize((64, 64), Image.LANCZOS)
        self.icon = pystray.Icon("discord_plus", bild, f"Discord Plus: {self.meldung}", menue)
        return self.icon

    def beenden(self):
        self.stop.set()
        self.befehle.put("quit")
        if self.icon:
            self.icon.stop()

    def run(self):
        waechter = threading.Thread(target=self.waechter, daemon=True)
        waechter.start()
        threading.Thread(target=self.ipc_server, daemon=True).start()
        self.symbol().run()              # läuft, bis beenden() das Symbol stoppt
        waechter.join(timeout=5)         # Aktivität in Discord noch löschen (trennen)


_mutex = None                    # muss bis zum Programmende leben – sonst gibt Windows den Mutex wieder frei


def already_running():
    """True, wenn das Programm schon läuft (z. B. Autostart und Toolbox starten es gleichzeitig)."""
    global _mutex
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _mutex = kernel32.CreateMutexW(None, False, "Local\\DiscordPlus_SingleInstance")
    return ctypes.get_last_error() == 183               # ERROR_ALREADY_EXISTS


def main():
    if already_running():
        logging.info("Läuft bereits – zweiter Start wird beendet.")
        return
    try:
        DiscordPlus().run()
    except Exception:
        logging.exception("Unerwarteter Fehler")
        raise


if __name__ == "__main__":
    main()
