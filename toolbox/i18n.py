"""
Sprachen: Texte stehen nicht im Code, sondern in einer Tabelle i18n.json neben dem Programm – je ID ein Block, darin
jede Sprache in einer eigenen Zeile (neue Sprache = in jedem Block eine Zeile mehr):

    {
      "status.laeuft": {
        "de": "Läuft",
        "en": "Running"
      },
      "aufgabe.fehlt": {
        "de": "Aufgabe „{task}“ gibt es noch nicht.",
        "en": "Task \\"{task}\\" does not exist yet."
      }
    }

Im Code steht dann nur die ID:

    t = i18n.Texte(ORDNER / "i18n.json")
    t("status.laeuft")                   -> „Läuft“ bzw. „Running“
    t("aufgabe.fehlt", task="X")         -> {task} wird ersetzt

Fehlt eine Übersetzung, kommt der englische Text; fehlt auch der, die ID selbst (einmal je ID im Log) – es stürzt
also nichts ab, wenn eine Zelle leer ist.

Welche Sprachen es gibt, steht in sprachen.json hier daneben – Code und Name, z. B. "fr": "Français". Daraus bauen
die Toolbox ihre Knöpfe (DE | EN | FR) und Setup.exe seine Optionsfelder, beide in dieser Reihenfolge. Neue Sprache:
dort eine Zeile ergänzen und in den i18n.json der Programme je ID eine Zeile – sonst nichts.

Welche Sprache gilt, steht in daten\\toolbox.json ("sprache": ein Code aus SPRACHEN) – gewählt im Setup oder in den
Einstellungen der Toolbox, gilt für die Toolbox und alle Programme. Fehlt der Eintrag: die Anzeigesprache von Windows,
wenn es sie gibt, sonst RUECKFALL. Eigenständige Programme lesen sie mit laden() – beim Start und wenn die Toolbox
„reload“ schickt; die Toolbox selbst setzt sie mit setzen().
"""

import ctypes
import json
import locale
import logging
from pathlib import Path

import daten

# sprachen.json liest auch setup\setup.ps1 (Sprachen) – deshalb JSON und nicht Python
SPRACHEN_DATEI = Path(__file__).with_name("sprachen.json")
try:
    _liste = json.loads(SPRACHEN_DATEI.read_text(encoding="utf-8"))
    NAMEN = dict(_liste["sprachen"])            # Code -> Name in der Sprache selbst, z. B. {"de": "Deutsch", …}
    RUECKFALL = _liste["rueckfall"]             # fehlt eine Übersetzung, gilt diese Sprache
except (OSError, ValueError, KeyError, TypeError):
    logging.exception("%s konnte nicht gelesen werden – nur Englisch", SPRACHEN_DATEI)
    NAMEN, RUECKFALL = {"en": "English"}, "en"
SPRACHEN = tuple(NAMEN)                         # alle Codes, die man wählen kann, z. B. ("de", "en")

TOOLBOX_DATEI = daten.einstellungen("toolbox")


def systemsprache():
    """Anzeigesprache von Windows, wenn sie in SPRACHEN steht (z. B. "de") – sonst RUECKFALL."""
    try:
        kennung = ctypes.windll.kernel32.GetUserDefaultUILanguage()      # z. B. 0x0407 = Deutsch (Deutschland)
    except (AttributeError, OSError):
        return RUECKFALL
    sprache = (locale.windows_locale.get(kennung) or "")[:2]            # "de_DE" -> "de"
    return sprache if sprache in SPRACHEN else RUECKFALL


def gewaehlte():
    """Die Sprache aus daten\\toolbox.json – oder die Systemsprache, wenn dort (noch) keine gültige steht."""
    sprache = daten.lesen(TOOLBOX_DATEI, {}).get("sprache")
    return sprache if sprache in SPRACHEN else systemsprache()


SPRACHE = gewaehlte()           # gilt für alle Texte dieses Prozesses


def setzen(sprache):
    """Sprache für diesen Prozess umstellen. True, wenn sie sich geändert hat."""
    global SPRACHE
    if sprache not in SPRACHEN or sprache == SPRACHE:
        return False
    SPRACHE = sprache
    return True


def laden():
    """Sprache neu aus daten\\toolbox.json lesen (z. B. nach „reload“ von der Toolbox). True, wenn sie sich geändert hat."""
    return setzen(gewaehlte())


class Texte:
    """Die Texte eines Programms aus seiner i18n.json. Aufruf: t("id") oder t("id", name=wert) für {name}."""

    def __init__(self, datei):
        self.datei = datei
        self.fehlend = set()                     # schon im Log gemeldete IDs
        try:
            self.tabelle = json.loads(datei.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            logging.exception("Texte aus %s konnten nicht geladen werden", datei)
            self.tabelle = {}

    def __call__(self, id, **werte):
        zeile = self.tabelle.get(id) or {}
        text = zeile.get(SPRACHE) or zeile.get(RUECKFALL)
        if not text:
            if id not in self.fehlend:
                self.fehlend.add(id)
                logging.warning("Text fehlt in %s: %s (%s)", self.datei.name, id, SPRACHE)
            return id
        return text.format(**werte) if werte else text

    def __contains__(self, id):
        return id in self.tabelle

    def alle(self, id):
        """Der Text in allen Sprachen, z. B. {"Im Call", "In a call"} – um Standardtexte wiederzuerkennen."""
        return set((self.tabelle.get(id) or {}).values())
