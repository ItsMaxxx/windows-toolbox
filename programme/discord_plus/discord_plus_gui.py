"""
Seite von Discord Plus in der Toolbox-GUI (Bausteine aus toolbox/base.py).

Das Programm (discord_plus.py) läuft eigenständig ohne Adminrechte. Die Seite:
  - fragt über eine lokale Verbindung (IPC_PORT) den Status ab – samt dem, was Discord gerade meldet (zum Testen),
  - schreibt Einstellungen in daten\\discord_plus.json und sagt dem Programm dann "reload",
  - erklärt die einmalige Einrichtung (eigene Discord-App) und schickt „Verbinden“ ans Programm,
  - schaltet den Autostart über HKCU\\...\\Run (ohne UAC-Abfrage, siehe winutil.autostart_setzen).
Alle Texte stehen in i18n.json – hier steht nur ihre ID: t("seite.…") (siehe toolbox\\i18n.py).
"""

import copy
import json
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

import winutil
from base import (BAD, GOOD, MUTED, TEXT, WARN, Button, Buttons, Choice, Entry, Programm, Section, Switch, Text,
                  ToolPage)

FOLDER = Path(__file__).resolve().parent
sys.path.append(str(FOLDER))
# Startwerte, Port, Laden/Speichern, Texte und was angezeigt wird – gemeinsam mit discord_plus.py
import discord_plus_einstellungen as ds  # noqa: E402
from discord_plus_einstellungen import t  # noqa: E402

# Von Setup.exe angelegt (wie beim Hardware-Monitor): im Task-Manager steht dann „Discord Plus“ statt „Python“
STARTER = FOLDER / ds.AUSWEIS["starter"]
SKRIPT = FOLDER / ds.AUSWEIS["skript"]

FARBEN = {"im_call": GOOD, "bereit": TEXT, "fehler": BAD}               # alles andere: WARN


def beispiele():
    """Beispiele für die Vorschau: ein Anruf mit Anna und ein Voice-Chat auf einem Server."""
    anruf = {"art": "privat", "id": "1", "name": "", "andere": [{"name": "Anna", "avatar": "bild"}]}
    server = {"art": "server", "id": "2", "name": t("vorschau.kanal"), "server": t("vorschau.server_name"),
              "andere": [{"name": "Anna", "avatar": None}, {"name": "Tom", "avatar": None},
                         {"name": "Lea", "avatar": None}]}
    return ((t("vorschau.anruf"), anruf), (t("vorschau.server"), server))


def ipc(command, timeout=0.6):
    """Schickt einen Befehl an discord_plus. Antwort als dict – oder None, wenn es nicht läuft."""
    try:
        with socket.create_connection(("127.0.0.1", ds.IPC_PORT), timeout=timeout) as conn:
            conn.sendall(command.encode("utf-8") + b"\n")
            data = b""
            while not data.endswith(b"\n"):
                chunk = conn.recv(4096)
                if not chunk:
                    break
                data += chunk
        return json.loads(data) if data else None
    except (OSError, ValueError):
        return None


def vorschau(s, app):
    """So ungefähr sieht es in deinem Profil aus – für einen Anruf mit Anna und einen Server-Voice-Chat."""
    app = app or t("vorschau.app")
    s = dict(s, call_status=True)
    bloecke = []
    for titel, kanal in beispiele():
        act = ds.aktivitaet(kanal, s, time.time() - 754)
        if act is None:
            bloecke.append(t("vorschau.nicht_angezeigt", titel=titel))
            continue
        verb = t(f"art.{act['type']}")
        zeilen = [f"{titel}:", f"      {verb} {app}", f"      {act['details']}"]
        if act.get("state"):
            zeilen.append(f"      {act['state']}")
        if act.get("timestamps"):
            zeilen.append(f"      {t('vorschau.vergangen')}")
        if act.get("assets"):
            zeilen.append(f"      {t('vorschau.profilbild')}")
        neben = app if act["status_display_type"] == 0 else act["details"]
        zeilen.append(f"      {t('vorschau.neben', verb=verb, neben=neben)}")
        bloecke.append("\n".join(zeilen))
    return "\n\n".join(bloecke)


def same_path(a, b):
    try:
        return Path(a).resolve() == Path(b).resolve()
    except (OSError, ValueError):
        return False


# ---------- Programm steuern (auch für „Toolbox und alle Programme“ in den Toolbox-Einstellungen) ----------
# Alle blockieren eine Weile – nur im Hintergrund aufrufen (app.run_async).
def laeuft():
    return ipc("status") is not None


def beenden():
    """Bittet das Programm, sich zu beenden, und wartet aufs Prozessende (es löscht dabei die Anzeige in Discord)."""
    status = ipc("status")
    if status is None:
        return True
    ipc("quit")
    if winutil.wait_for_exit(status.get("pid"), timeout=10):
        return True
    for _ in range(50):                          # Rückfall: warten, bis es nicht mehr antwortet (bis zu 5 s)
        if ipc("status", timeout=0.2) is None:
            return True
        time.sleep(0.1)
    return False


def starten():
    """Startet das Programm (ohne Adminrechte) und wartet, bis es antwortet. Fehlt der Starter noch, direkt das
    Skript mit dem Python der Toolbox."""
    befehl = [str(STARTER)] if STARTER.exists() else [winutil.pythonw_exe(), str(SKRIPT)]
    try:
        subprocess.Popen(befehl, cwd=str(FOLDER), creationflags=winutil.CREATE_NO_WINDOW)
    except OSError:
        return False
    for _ in range(50):
        if ipc("status", timeout=0.2):
            return True
        time.sleep(0.2)
    return False


def neu_laden():
    """Einstellungen und Sprache neu einlesen lassen (z. B. nach einem Sprachwechsel in der Toolbox)."""
    ipc("reload")


class DiscordPlusPage(ToolPage):
    settings_file = ds.SETTINGS_FILE
    defaults = ds.DEFAULT_SETTINGS
    visible = False
    poll_job = None
    app_name = None              # Name der Discord-App (meldet das Programm nach dem Verbinden)

    def layout(self):
        grey = {"width": 150, "style": "grau"}
        return [
            Section(t("seite.status"),
                    Text(f"●  {t('seite.status.pruefe')}", name="status", size=14),
                    Text(name="erkannt", color=TEXT, hidden=True),     # was Discord gerade meldet (zum Testen)
                    Buttons(Button(t("seite.starten"), self.start, name="start"),
                            Button(t("seite.beenden"), self.stop, name="stop"),
                            Button(t("seite.neu_starten"), self.restart, name="restart"))),
            Section(t("seite.einrichtung"),
                    Text(t("seite.einrichtung.text"), color=TEXT),
                    Buttons(Button(t("seite.portal"), lambda: webbrowser.open(ds.PORTAL_URL), width=190,
                                   ziel=ds.PORTAL_URL),
                            Button(t("seite.localhost_kopieren"), self.redirect_kopieren, width=190, style="grau")),
                    Entry(t("seite.client_id"), "client_id", width=280),
                    Entry(t("seite.client_secret"), "client_secret", width=280, geheim=True),
                    Buttons(Button(t("seite.verbinden"), self.verbinden, name="verbinden"),
                            Button(t("seite.abmelden"), self.abmelden, name="abmelden", style="grau")),
                    Text(name="anmeldung")),
            Section(t("seite.call_status"),
                    Text(t("seite.call_status.text")),
                    Switch(t("seite.anzeigen"), key="call_status"),
                    Choice(t("seite.anzeigen_bei"), "anzeigen_bei",
                           {t(f"seite.anzeigen_bei.{wert}"): wert for wert in ds.ANZEIGEN_BEI}),
                    Entry(t("seite.text_privat"), "text_privat"),
                    Entry(t("seite.text_server"), "text_server"),
                    Switch(t("seite.namen"), key="namen"),
                    Text(t("seite.namen.warnung"), color=WARN),
                    Switch(t("seite.ort"), key="ort"),
                    Switch(t("seite.anzahl"), key="anzahl"),
                    Switch(t("seite.dauer"), key="dauer"),
                    Choice(t("seite.art"), "art", {t(f"art.{art}"): art for art in ds.ARTEN}),
                    Choice(t("seite.neben_namen"), "neben_namen",
                           {t("seite.neben_namen.app"): 0, t("seite.neben_namen.text"): 2},
                           info=t("seite.neben_namen.info"))),
            Section(t("seite.vorschau"),
                    Text(name="vorschau", color=TEXT),
                    Text(t("seite.vorschau.text"))),
            Section(t("seite.autostart"),
                    Text(t("seite.autostart.text")),
                    Switch(t("seite.autostart.schalter"), command=self.toggle_autostart, name="autostart"),
                    Text(name="autostart_label")),
            Section(t("seite.gut_zu_wissen"), Text(t("seite.hinweise"))),
            Section(t("seite.erweitert"),
                    Buttons(Button(t("seite.log_oeffnen"), lambda: self.open(ds.LOG_FILE), ziel=ds.LOG_FILE, **grey),
                            Button(t("seite.einstellungsdatei_oeffnen"), lambda: self.open(self.settings_file),
                                   ziel=self.settings_file, **grey),
                            Button(t("seite.ordner_oeffnen"), lambda: self.open(FOLDER), ziel=FOLDER, **grey)),
                    Buttons(Button(t("seite.zuruecksetzen"), self.reset, width=150, style="gefahr"))),
        ]

    # ---------- Einstellungen ----------
    def load(self):
        return ds.load_settings()                # mit derselben Prüfung wie im Programm selbst

    def refresh(self, *keys):
        super().refresh(*keys)
        if "vorschau" in self.w:
            self.w["vorschau"].configure(text=vorschau(self.data, self.app_name))

    def on_saved(self):
        self.app.run_async(neu_laden)

    def reset(self):
        """Wie ToolPage.reset, aber die Zugangsdaten bleiben – sonst müsste man die ganze Einrichtung wiederholen.
        pruefen() setzt die Standardtexte der gewählten Sprache ein."""
        zugang = {k: self.data.get(k, "") for k in ("client_id", "client_secret")}
        self.data = ds.pruefen(copy.deepcopy(self.defaults) | zugang)
        self.refresh()
        self.save()

    def redirect_kopieren(self):
        self.clipboard_clear()
        self.clipboard_append(ds.REDIRECT_URI)
        self.app.toast(t("seite.toast.kopiert", text=ds.REDIRECT_URI))

    # ---------- Status und Steuerung ----------
    def on_show(self):
        if self.visible:
            return
        self.visible = True
        super().on_show()                        # z. B. übers Symbol pausiert
        self.poll_status()
        self.refresh_autostart()

    def on_hide(self):
        self.visible = False
        if self.poll_job:
            self.after_cancel(self.poll_job)
            self.poll_job = None

    def poll_status(self):
        if not self.visible:
            return
        self.app.run_async(lambda: ipc("status"), self.show_status)
        self.poll_job = self.after(2000, self.poll_status)

    def poll_status_soon(self):
        """Nach Start/Stopp ein paar Mal schnell nachsehen, statt 2 Sekunden zu warten."""
        for delay in (400, 1200, 2500):
            self.after(delay, lambda: self.app.run_async(lambda: ipc("status"), self.show_status))

    def show_status(self, status):
        if not self.winfo_exists():
            return                               # Seite wurde inzwischen neu gebaut (Sprachwechsel)
        running = bool(status and status.get("ok"))
        if running:
            zustand = status.get("zustand")
            self.w["status"].configure(text=f"●  {t('seite.status.laeuft', meldung=status.get('meldung'))}",
                                       text_color=FARBEN.get(zustand, WARN))
            erkannt = status.get("erkannt")
            self.w["erkannt"].configure(text=t("seite.erkannt", text=erkannt) if erkannt else "")
            self.show("erkannt", bool(erkannt))
        else:
            self.w["status"].configure(text=f"●  {t('seite.status.gestoppt')}", text_color=MUTED)
            self.show("erkannt", False)
        self.enable("start", not running)
        self.enable("stop", running)
        self.enable("restart", running)

        nutzer = status.get("nutzer") if running else None
        if running and status.get("app") != self.app_name:
            self.app_name = status.get("app")
            self.w["vorschau"].configure(text=vorschau(self.data, self.app_name))
        if nutzer and status.get("zustand") not in ("einrichtung", "nicht_angemeldet"):
            text = (t("seite.verbunden_app", nutzer=nutzer, app=self.app_name) if self.app_name
                    else t("seite.verbunden", nutzer=nutzer))
            text, farbe = f"✓  {text}", GOOD
        elif not (self.data["client_id"] and self.data["client_secret"]):
            text, farbe = t("seite.nicht_eingerichtet"), WARN
        elif running:
            text, farbe = t("seite.nicht_verbunden"), WARN
        else:
            text, farbe = t("seite.muss_laufen"), MUTED
        self.w["anmeldung"].configure(text=text, text_color=farbe)
        self.enable("abmelden", bool(nutzer))

    def say(self, text):
        self.w["status"].configure(text=f"●  {text}", text_color=MUTED)

    def start(self):
        self.say(t("seite.status.startet"))
        self.enable("start", False)

        def done(ok):
            if not ok:
                self.app.toast(t("seite.toast.start_fehlgeschlagen"), error=True)
            self.poll_status_soon()

        self.app.run_async(starten, done)

    def stop(self):
        self.say(t("seite.status.beendet"))
        self.app.run_async(lambda: ipc("quit"), lambda result: self.poll_status_soon())

    def restart(self):
        self.say(t("seite.status.neustart"))

        def done(stopped):
            if stopped:
                self.start()
            else:
                self.app.toast(t("seite.toast.reagiert_nicht"), error=True)

        self.app.run_async(beenden, done)

    # ---------- Verbinden ----------
    def verbinden(self):
        for element in self.elements:            # gerade eingetippt, aber noch nicht gespeichert (Feld nicht verlassen)
            if isinstance(element, Entry) and element.key:
                element.apply(self)
        if not (self.data["client_id"] and self.data["client_secret"]):
            self.app.toast(t("seite.toast.zugang_fehlt"), error=True)
            return
        self.enable("verbinden", False)
        self.w["anmeldung"].configure(text=t("seite.autorisieren"), text_color=WARN)

        def work():
            if not laeuft() and not starten():
                return False
            ipc("reload")                        # neue Client ID / neues Secret
            return ipc("verbinden") is not None

        def done(ok):
            if not self.winfo_exists():
                return
            self.enable("verbinden", True)
            if not ok:
                self.app.toast(t("seite.toast.startet_nicht"), error=True)
            self.poll_status_soon()

        self.app.run_async(work, done)

    def abmelden(self):
        self.app.run_async(lambda: ipc("abmelden"), lambda result: self.poll_status_soon())

    # ---------- Autostart ----------
    def refresh_autostart(self):
        info = winutil.autostart_info(ds.AUTOSTART)
        switch, label = self.w["autostart"], self.w["autostart_label"]
        switch.select() if info and info["an"] else switch.deselect()
        if not STARTER.exists():
            switch.configure(state="disabled")
            label.configure(text=f"⚠  {t('seite.starter_fehlt', starter=STARTER.name)}", text_color=WARN)
        elif info and not same_path(info["ziel"].strip('"'), STARTER):
            label.configure(text=f"⚠  {t('seite.autostart.anderer_ort', ziel=info['ziel'])}", text_color=WARN)
        elif info and not info["an"]:
            label.configure(text=t("seite.autostart.deaktiviert"), text_color=MUTED)
        else:
            label.configure(text="", text_color=MUTED)

    def toggle_autostart(self):
        an = bool(self.w["autostart"].get())
        if not winutil.autostart_setzen(ds.AUTOSTART, STARTER if an else None):
            self.app.toast(t("seite.toast.aendern_fehlgeschlagen"), error=True)
        self.refresh_autostart()


SEITE = DiscordPlusPage
PROGRAMM = Programm(laeuft, beenden, starten, neu_laden)     # für „Toolbox und alle Programme“ und den Sprachwechsel
