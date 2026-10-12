"""
Seite von Discord Plus in der Toolbox-GUI (Bausteine aus toolbox/base.py).

Das Programm (discord_plus.py) läuft eigenständig ohne Adminrechte. Die Seite:
  - fragt über eine lokale Verbindung (IPC_PORT) den Status ab – samt dem, was Discord gerade meldet (zum Testen),
  - schreibt Einstellungen in daten\\discord_plus.json und sagt dem Programm dann "reload",
  - erklärt die einmalige Einrichtung (eigene Discord-App) und schickt „Verbinden“ ans Programm,
  - schaltet den Autostart über HKCU\\...\\Run (ohne UAC-Abfrage, siehe winutil.autostart_setzen).
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
# Startwerte, Port, Laden/Speichern und was angezeigt wird – gemeinsam mit discord_plus.py
import discord_plus_einstellungen as ds  # noqa: E402

# Von Setup.exe angelegt (wie beim Hardware-Monitor): im Task-Manager steht dann „Discord Plus“ statt „Python“
STARTER = FOLDER / ds.AUSWEIS["starter"]
SKRIPT = FOLDER / ds.AUSWEIS["skript"]

ANZEIGEN_BEI = {"Anrufe und Server": "beide", "Nur Anrufe": "privat", "Nur Server": "server"}
ARTEN = {text: art for art, text in ds.ARTEN.items()}
NEBEN_NAMEN = {"Name der App": 0, "Text": 2}
FARBEN = {"im_call": GOOD, "bereit": TEXT, "fehler": BAD}               # alles andere: WARN

EINRICHTUNG = (
    "Discord zeigt deinen Status nur an, wenn er von einer eigenen „App“ kommt. Die legst du einmal an "
    "(etwa 3 Minuten, kostenlos):\n\n"
    "1.  „Developer Portal öffnen“, mit deinem Discord-Konto anmelden, oben rechts „New Application“. "
    "Der Name, den du dort eingibst, steht später hinter „Spielt“ – z. B. „Telefonat“ oder „Voice-Chat“. "
    "Unter „General Information“ kannst du auch ein Bild hochladen (App Icon).\n"
    "2.  Links „OAuth2“: die „Client ID“ kopieren und unten einfügen. Das „Client Secret“ zeigt Discord nur "
    "einmal – bis dahin steht dort „Hidden for security“ und Kopieren ist gesperrt. Also „Reset Secret“ "
    "klicken (bestätigen, ggf. Code aus der Authenticator-App), dann erscheint es: sofort kopieren und unten "
    "einfügen. Es bleibt nur auf diesem PC (daten\\discord_plus.json).\n"
    "3.  Auf derselben Seite unter „Redirects“ → „Add Redirect“: http://localhost eintragen (Knopf „Kopieren“) "
    "und unten „Save Changes“.\n"
    "4.  Hier „Verbinden“ klicken. Discord fragt in der App einmal, ob deine App auf dein Konto zugreifen darf → "
    "„Autorisieren“. Danach fragt es nie wieder von selbst.\n"
    "5.  In Discord unter Einstellungen → Aktivitätsprivatsphäre (Activity Privacy) muss „Meine Aktivität teilen“ "
    "(Share my activity) an sein – sonst sieht niemand die Anzeige. Freunde sehen sie dann immer; darunter "
    "(Where I Share Activity) stellst du ein, auf welchen Servern sie auch andere sehen.\n\n"
    "Testen: Ruf jemanden an oder geh in einen Voice-Chat. Oben unter „Status“ steht dann, was Discord meldet."
)
HINWEISE = (
    "•  Funktioniert nur mit der Discord-App auf diesem PC (nicht im Browser) – sie muss laufen.\n"
    "•  Die Anzeige sehen alle, die auch sonst sehen, was du spielst: Freunde und Leute auf gemeinsamen Servern.\n"
    "•  Läuft gleichzeitig ein Spiel, zeigt Discord beide Aktivitäten; neben deinem Namen steht meist das Spiel.\n"
    "•  Die Dauer zählt ab dem Moment, in dem das Programm den Call bemerkt (spätestens nach 3 Sekunden)."
)
NAMEN_INFO = (
    "Zeigt, mit wem du im Call bist („Im Call mit Anna“), und bei Anrufen zu zweit ihr Profilbild.\n\n"
    "Das sehen alle deine Freunde – auch die, die die andere Person nicht kennen. Frag im Zweifel vorher."
)
NEBEN_NAMEN_INFO = (
    "Was in der Mitgliederliste und Freundesliste kurz neben deinem Namen steht:\n\n"
    "•  Name der App: z. B. „Spielt Telefonat“\n"
    "•  Text: deine erste Zeile, z. B. „Im Call“\n\n"
    "Im Profil steht immer alles."
)

# Beispiele für die Vorschau
BEISPIEL_ANRUF = {"art": "privat", "id": "1", "name": "", "andere": [{"name": "Anna", "avatar": "bild"}]}
BEISPIEL_SERVER = {"art": "server", "id": "2", "name": "Allgemein", "server": "Mein Server",
                   "andere": [{"name": "Anna", "avatar": None}, {"name": "Tom", "avatar": None},
                              {"name": "Lea", "avatar": None}]}


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
    app = app or "‹Name deiner App›"
    s = dict(s, call_status=True)
    bloecke = []
    for titel, kanal in (("Anruf mit Anna", BEISPIEL_ANRUF), ("Voice-Chat auf einem Server", BEISPIEL_SERVER)):
        act = ds.aktivitaet(kanal, s, time.time() - 754)
        if act is None:
            bloecke.append(f"{titel}:  wird nicht angezeigt")
            continue
        verb = ds.ARTEN[act["type"]]
        zeilen = [f"{titel}:", f"      {verb} {app}", f"      {act['details']}"]
        if act.get("state"):
            zeilen.append(f"      {act['state']}")
        if act.get("timestamps"):
            zeilen.append("      12:34 vergangen")
        if act.get("assets"):
            zeilen.append("      (mit Annas Profilbild)")
        neben = app if act["status_display_type"] == 0 else act["details"]
        zeilen.append(f"      neben deinem Namen: {verb} {neben}")
        bloecke.append("\n".join(zeilen))
    return "\n\n".join(bloecke)


def same_path(a, b):
    try:
        return Path(a).resolve() == Path(b).resolve()
    except (OSError, ValueError):
        return False


# ---------- Programm steuern (auch für „Toolbox und alle Programme“ in den Toolbox-Einstellungen) ----------
# Alle drei blockieren eine Weile – nur im Hintergrund aufrufen (app.run_async).
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


class DiscordPlusPage(ToolPage):
    settings_file = ds.SETTINGS_FILE
    defaults = ds.DEFAULT_SETTINGS
    visible = False
    poll_job = None
    app_name = None              # Name der Discord-App (meldet das Programm nach dem Verbinden)

    def layout(self):
        grey = {"width": 150, "style": "grau"}
        return [
            Section("Status",
                    Text("●  Prüfe …", name="status", size=14),
                    Text(name="erkannt", color=TEXT, hidden=True),     # was Discord gerade meldet (zum Testen)
                    Buttons(Button("Starten", self.start, name="start"),
                            Button("Beenden", self.stop, name="stop"),
                            Button("Neu starten", self.restart, name="restart"))),
            Section("Einrichtung (einmalig)",
                    Text(EINRICHTUNG, color=TEXT),
                    Buttons(Button("Developer Portal öffnen", lambda: webbrowser.open(ds.PORTAL_URL), width=190,
                                   ziel=ds.PORTAL_URL),
                            Button("http://localhost kopieren", self.redirect_kopieren, width=190, style="grau")),
                    Entry("Client ID", "client_id", width=280),
                    Entry("Client Secret", "client_secret", width=280, geheim=True),
                    Buttons(Button("Verbinden", self.verbinden, name="verbinden"),
                            Button("Abmelden", self.abmelden, name="abmelden", style="grau")),
                    Text(name="anmeldung")),
            Section("Call-Status",
                    Text("Zeigt in Discord „Im Call“ an, sobald du telefonierst oder in einem Voice-Chat bist – "
                         "auch für Freunde, die den Server oder Anruf nicht sehen können."),
                    Switch("Anzeigen, wenn ich im Call bin", key="call_status"),
                    Choice("Anzeigen bei", "anzeigen_bei", ANZEIGEN_BEI),
                    Entry("Text bei Anrufen", "text_privat"),
                    Entry("Text auf Servern", "text_server"),
                    Switch("Namen anzeigen („… mit Anna“)", key="namen"),
                    Text(NAMEN_INFO.split("\n\n")[1], color=WARN),
                    Switch("Server und Kanal bzw. Gruppenname anzeigen", key="ort"),
                    Switch("Personenzahl anzeigen (ab 3 Personen und auf Servern)", key="anzahl"),
                    Switch("Dauer anzeigen", key="dauer"),
                    Choice("Art", "art", ARTEN),
                    Choice("Neben deinem Namen", "neben_namen", NEBEN_NAMEN, info=NEBEN_NAMEN_INFO)),
            Section("Vorschau Call-Status",
                    Text(name="vorschau", color=TEXT),
                    Text("Ungefähr – wie es genau aussieht, entscheidet Discord.")),
            Section("Autostart",
                    Text("Startet Discord Plus beim Anmelden an Windows (ohne Adminrechte, ohne Nachfrage). "
                         "Es wartet dann im Hintergrund, bis Discord läuft."),
                    Switch("Beim Anmelden automatisch starten", command=self.toggle_autostart, name="autostart"),
                    Text(name="autostart_label")),
            Section("Gut zu wissen", Text(HINWEISE)),
            Section("Erweitert",
                    Buttons(Button("Log öffnen", lambda: self.open(ds.LOG_FILE), ziel=ds.LOG_FILE, **grey),
                            Button("Einstellungsdatei öffnen", lambda: self.open(self.settings_file), 
                                   ziel=self.settings_file, **grey),
                            Button("Ordner öffnen", lambda: self.open(FOLDER), ziel=FOLDER, **grey)),
                    Buttons(Button("Alles zurücksetzen", self.reset, width=150, style="gefahr"))),
        ]

    # ---------- Einstellungen ----------
    def load(self):
        return ds.load_settings()                # mit derselben Prüfung wie im Programm selbst

    def refresh(self, *keys):
        super().refresh(*keys)
        if "vorschau" in self.w:
            self.w["vorschau"].configure(text=vorschau(self.data, self.app_name))

    def on_saved(self):
        self.app.run_async(lambda: ipc("reload"))

    def reset(self):
        """Wie ToolPage.reset, aber die Zugangsdaten bleiben – sonst müsste man die ganze Einrichtung wiederholen."""
        zugang = {k: self.data.get(k, "") for k in ("client_id", "client_secret")}
        self.data = copy.deepcopy(self.defaults) | zugang
        self.refresh()
        self.save()

    def redirect_kopieren(self):
        self.clipboard_clear()
        self.clipboard_append(ds.REDIRECT_URI)
        self.app.toast(f"{ds.REDIRECT_URI} kopiert ✓")

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
        running = bool(status and status.get("ok"))
        if running:
            zustand = status.get("zustand")
            self.w["status"].configure(text=f"●  Läuft  ·  {status.get('meldung')}",
                                       text_color=FARBEN.get(zustand, WARN))
            erkannt = status.get("erkannt")
            self.w["erkannt"].configure(text=f"Discord meldet: {erkannt}" if erkannt else "")
            self.show("erkannt", bool(erkannt))
        else:
            self.w["status"].configure(text="●  Gestoppt – ohne das Programm zeigt Discord nichts an",
                                       text_color=MUTED)
            self.show("erkannt", False)
        self.enable("start", not running)
        self.enable("stop", running)
        self.enable("restart", running)

        nutzer = status.get("nutzer") if running else None
        if running and status.get("app") != self.app_name:
            self.app_name = status.get("app")
            self.w["vorschau"].configure(text=vorschau(self.data, self.app_name))
        if nutzer and status.get("zustand") not in ("einrichtung", "nicht_angemeldet"):
            text, farbe = f"✓  Verbunden als {nutzer}" + (f" – App „{self.app_name}“" if self.app_name else ""), GOOD
        elif not (self.data["client_id"] and self.data["client_secret"]):
            text, farbe = "Noch nicht eingerichtet – Client ID und Client Secret fehlen.", WARN
        elif running:
            text, farbe = "Noch nicht verbunden – „Verbinden“ klicken.", WARN
        else:
            text, farbe = "Zum Verbinden muss das Programm laufen – „Verbinden“ startet es.", MUTED
        self.w["anmeldung"].configure(text=text, text_color=farbe)
        self.enable("abmelden", bool(nutzer))

    def say(self, text):
        self.w["status"].configure(text=f"●  {text}", text_color=MUTED)

    def start(self):
        self.say("Wird gestartet …")
        self.enable("start", False)

        def done(ok):
            if not ok:
                self.app.toast("Start fehlgeschlagen – siehe Log", error=True)
            self.poll_status_soon()

        self.app.run_async(starten, done)

    def stop(self):
        self.say("Wird beendet …")
        self.app.run_async(lambda: ipc("quit"), lambda result: self.poll_status_soon())

    def restart(self):
        self.say("Wird neu gestartet …")

        def done(stopped):
            if stopped:
                self.start()
            else:
                self.app.toast("Programm reagiert nicht", error=True)

        self.app.run_async(beenden, done)

    # ---------- Verbinden ----------
    def verbinden(self):
        for element in self.elements:            # gerade eingetippt, aber noch nicht gespeichert (Feld nicht verlassen)
            if isinstance(element, Entry) and element.key:
                element.apply(self)
        if not (self.data["client_id"] and self.data["client_secret"]):
            self.app.toast("Erst Client ID und Client Secret eintragen (Schritt 2)", error=True)
            return
        self.enable("verbinden", False)
        self.w["anmeldung"].configure(text="Bitte in Discord „Autorisieren“ klicken …", text_color=WARN)

        def work():
            if not laeuft() and not starten():
                return False
            ipc("reload")                        # neue Client ID / neues Secret
            return ipc("verbinden") is not None

        def done(ok):
            self.enable("verbinden", True)
            if not ok:
                self.app.toast("Programm startet nicht – siehe Log", error=True)
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
            label.configure(text=f"⚠  {STARTER.name} fehlt – bitte Setup.exe ausführen.", text_color=WARN)
        elif info and not same_path(info["ziel"].strip('"'), STARTER):
            label.configure(text=f"⚠  Der Eintrag startet einen anderen Ort: {info['ziel']}\nAus- und wieder "
                                 f"einschalten stellt ihn auf diesen Ordner um.", text_color=WARN)
        elif info and not info["an"]:
            label.configure(text="Im Task-Manager unter „Autostart“ deaktiviert – Einschalten erlaubt ihn wieder.",
                            text_color=MUTED)
        else:
            label.configure(text="", text_color=MUTED)

    def toggle_autostart(self):
        an = bool(self.w["autostart"].get())
        if not winutil.autostart_setzen(ds.AUTOSTART, STARTER if an else None):
            self.app.toast("Ändern fehlgeschlagen", error=True)
        self.refresh_autostart()


SEITE = DiscordPlusPage
PROGRAMM = Programm(laeuft, beenden, starten)     # für „Toolbox und alle Programme“
