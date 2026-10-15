"""
Was discord_plus.py und seine Seite in der Toolbox (discord_plus_gui.py) gemeinsam brauchen: Startwerte, Laden und
Speichern, Port, Name des Autostart-Eintrags – und aktivitaet(), die aus dem Sprachkanal die Anzeige in Discord baut
(auch für die Vorschau auf der Toolbox-Seite).

Zwei Dateien in daten\\:
  discord_plus.json             Einstellungen – schreibt die Toolbox-Seite (Client-ID und -Secret stehen auch hier)
  discord_plus_anmeldung.json   Anmeldung bei Discord (Token) – schreibt nur das Programm selbst
Getrennt, damit sich Toolbox und Programm nie gegenseitig etwas überschreiben.

Alle Texte stehen in i18n.json (t("id"), siehe toolbox\\i18n.py) – auch das, was Freunde in Discord sehen.
"""

import json
import sys
from pathlib import Path

ORDNER = Path(__file__).resolve().parent
sys.path.append(str(ORDNER.parents[1] / "toolbox"))     # storage.py (gemeinsam mit der Toolbox)
import storage  # noqa: E402
import i18n  # noqa: E402

t = i18n.Texts(ORDNER / "i18n.json")   # alle Texte von Discord Plus: t("id") in der gewählten Sprache

AUSWEIS = json.loads((ORDNER / "program.json").read_text(encoding="utf-8"))
IPC_PORT = AUSWEIS["port"]             # lokale Fernsteuerung durch die Toolbox (nur von diesem PC aus erreichbar)
AUTOSTART = AUSWEIS["autostart"]       # Name des Eintrags unter HKCU\...\Run (setup.ps1 räumt ihn beim Entfernen weg)
SETTINGS_FILE = storage.settings_file(AUSWEIS["id"])
ANMELDUNG_FILE = storage.settings_file(AUSWEIS["id"] + "_anmeldung")
LOG_FILE = storage.log_file(AUSWEIS["id"])

PORTAL_URL = "https://discord.com/developers/applications"
REDIRECT_URI = "http://localhost"      # muss in der Discord-App unter OAuth2 → Redirects eingetragen sein

ANZEIGEN_BEI = ("beide", "privat", "server")
# Art der Aktivität – mehr erlaubt Discord über diese Schnittstelle nicht (Doku: SET_ACTIVITY).
# Angezeigt wird t("art.<Nummer>"), z. B. „Spielt“ bzw. „Playing“.
ARTEN = (0, 2, 3, 5)
NEBEN_NAMEN = (0, 2)                   # status_display_type: 0 = Name der App, 2 = Text (details)

DEFAULT_SETTINGS = {
    "client_id": "",                   # aus dem Developer Portal (OAuth2 → Client ID)
    "client_secret": "",               # dito (OAuth2 → Reset Secret) – bleibt nur auf diesem PC
    "call_status": True,                     # aus = nichts anzeigen (das Programm läuft weiter)
    "anzeigen_bei": "beide",           # "privat" = nur Anrufe (DM, Gruppe), "server" = nur Server-Voice-Chats
    "text_privat": "",                 # leer = Standardtext der gewählten Sprache (t("standard.text_privat"))
    "text_server": "",                 # dito – „Im Voice-Chat“ bzw. „In a voice chat“
    "namen": False,                    # „… mit Anna, Tom“ und das Profilbild – sehen dann alle deine Freunde
    "ort": False,                      # Server und Kanal bzw. Name der Gruppe
    "anzahl": True,                    # „3 Personen“ (nicht bei Anrufen zu zweit)
    "dauer": True,                     # „seit 12:34“ – zählt ab dem Moment, in dem das Programm den Call bemerkt
    "art": 0,                          # Schlüssel aus ARTEN
    "neben_namen": 2,                  # was in der Mitgliederliste neben deinem Namen steht (NEBEN_NAMEN)
}


def load_settings():
    """Liest die Einstellungen; alles Fehlende oder Ungültige bekommt den Startwert."""
    return pruefen(storage.load(SETTINGS_FILE, DEFAULT_SETTINGS))


def pruefen(s):
    """Alles Ungültige in den Einstellungen s bekommt den Startwert (ändert s und gibt es zurück)."""
    start = DEFAULT_SETTINGS
    for key in ("client_id", "client_secret"):
        s[key] = s[key].strip() if isinstance(s[key], str) else ""
    for key in ("text_privat", "text_server"):
        text = s[key].strip() if isinstance(s[key], str) else ""
        # Zu kurz (Discord verlangt mindestens 2 Zeichen) oder ein unveränderter Standardtext – egal in welcher
        # Sprache: dann der Standardtext der gewählten Sprache. Eigene Texte bleiben, wie sie sind.
        if len(text) < 2 or text in t.all(f"standard.{key}"):
            s[key] = t(f"standard.{key}")
    for key in ("call_status", "namen", "ort", "anzahl", "dauer"):
        if not isinstance(s[key], bool):
            s[key] = start[key]
    if s["anzeigen_bei"] not in ANZEIGEN_BEI:
        s["anzeigen_bei"] = start["anzeigen_bei"]
    if s["art"] not in ARTEN:
        s["art"] = start["art"]
    if s["neben_namen"] not in NEBEN_NAMEN:
        s["neben_namen"] = start["neben_namen"]
    return s


def save_settings(settings):
    """Speichert die Einstellungen. Wirft OSError, wenn es nicht klappt."""
    storage.save(SETTINGS_FILE, settings)


# ---------- Was in Discord angezeigt wird ----------
def kuerzen(text, laenge=128):
    """Discord nimmt höchstens 128 Zeichen je Zeile."""
    return text if len(text) <= laenge else text[:laenge - 1] + "…"


def namen_liste(namen, hoechstens=3):
    """["Anna", "Tom", "Lea", "Ben"] -> "Anna, Tom, Lea und 1 weitere" (bzw. "… and 1 more")."""
    if len(namen) <= hoechstens:
        return t("anzeige.und", vorne=", ".join(namen[:-1]), letzter=namen[-1]) if len(namen) > 1 else "".join(namen)
    return t("anzeige.weitere", namen=", ".join(namen[:hoechstens]), n=len(namen) - hoechstens)


def aktivitaet(kanal, s, start):
    """Die Aktivität für SET_ACTIVITY – oder None, wenn nichts angezeigt werden soll.

    kanal: was das Programm aus GET_SELECTED_VOICE_CHANNEL macht (None = in keinem Call):
           {"art": "privat"/"gruppe"/"server", "name": Kanal- bzw. Gruppenname, "server": Servername,
            "andere": [{"name", "avatar"}, …] – alle außer dir}
    s:     die Einstellungen
    start: Unix-Zeit in Sekunden, seit der du in diesem Call bist
    """
    if kanal is None or not s["call_status"]:
        return None
    privat = kanal["art"] in ("privat", "gruppe")
    if (s["anzeigen_bei"] == "privat" and not privat) or (s["anzeigen_bei"] == "server" and privat):
        return None
    andere = kanal["andere"]
    text = s["text_privat"] if privat else s["text_server"]
    if s["namen"] and andere:
        text = t("anzeige.mit", text=text, namen=namen_liste([a["name"] for a in andere]))

    zeile2 = []
    if s["ort"]:
        if kanal["art"] == "server":
            zeile2.append(" · ".join(t for t in (kanal.get("server"), kanal.get("name")) if t))
        elif kanal["art"] == "gruppe" and kanal.get("name"):
            zeile2.append(kanal["name"])
    personen = len(andere) + 1
    if s["anzahl"] and (personen > 2 or not privat):
        zeile2.append(t("anzeige.allein") if personen == 1 else t("anzeige.personen", n=personen))

    act = {"type": s["art"], "status_display_type": s["neben_namen"], "details": kuerzen(text)}
    zeile2 = " · ".join(t for t in zeile2 if t)
    if len(zeile2) >= 2:
        act["state"] = kuerzen(zeile2)
    if s["dauer"]:
        act["timestamps"] = {"start": int(start)}
    if s["namen"] and len(andere) == 1 and andere[0].get("avatar"):
        act["assets"] = {"large_image": andere[0]["avatar"], "large_text": kuerzen(andere[0]["name"])}
    return act
