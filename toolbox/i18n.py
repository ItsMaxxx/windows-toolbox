"""
Languages: texts are not in the code but in a table i18n.json next to the program – one block per ID, inside it
each language on its own line (new language = one more line in every block):

    {
      "status.running": {
        "de": "Läuft",
        "en": "Running"
      },
      "task.missing": {
        "de": "Aufgabe „{task}“ gibt es noch nicht.",
        "en": "Task \\"{task}\\" does not exist yet."
      }
    }

The code then only contains the ID:

    t = i18n.Texts(FOLDER / "i18n.json")
    t("status.running")                  -> "Läuft" or "Running"
    t("task.missing", task="X")          -> {task} gets replaced

If a translation is missing, you get the English text; if that is missing too, the ID itself (once per ID in the
log) – so nothing crashes when a cell is empty.

Which languages exist is in languages.json right next to this file – code and name, e.g. "fr": "Français". From it
the Toolbox builds its buttons (DE | EN | FR) and Setup.exe its radio buttons, both in this order. New language:
add one line there and one line per ID in the programs' i18n.json files – nothing else.

Which language applies is in data\\toolbox.json ("language": a code from LANGUAGES) – chosen in the setup or in the
Toolbox settings, applies to the Toolbox and all programs. If the entry is missing: the Windows display language,
if it exists, otherwise FALLBACK. Standalone programs read it with reload() – at startup and when the Toolbox sends
"reload"; the Toolbox itself sets it with set_language().
"""

import ctypes
import json
import locale
import logging
from pathlib import Path

import storage

# languages.json is also read by setup\setup.ps1 (Languages) – that's why it's JSON and not Python
LANGUAGES_FILE = Path(__file__).with_name("languages.json")
try:
    _list = json.loads(LANGUAGES_FILE.read_text(encoding="utf-8"))
    NAMES = dict(_list["languages"])            # code -> name in the language itself, e.g. {"de": "Deutsch", …}
    FALLBACK = _list["fallback"]                # if a translation is missing, this language applies
except (OSError, ValueError, KeyError, TypeError):
    logging.exception("%s could not be read – English only", LANGUAGES_FILE)
    NAMES, FALLBACK = {"en": "English"}, "en"
LANGUAGES = tuple(NAMES)                        # all codes you can choose, e.g. ("de", "en")

TOOLBOX_FILE = storage.settings_file("toolbox")


def system_language():
    """Windows display language if it is in LANGUAGES (e.g. "de") – otherwise FALLBACK."""
    try:
        lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()      # e.g. 0x0407 = German (Germany)
    except (AttributeError, OSError):
        return FALLBACK
    language = (locale.windows_locale.get(lang_id) or "")[:2]           # "de_DE" -> "de"
    return language if language in LANGUAGES else FALLBACK


def chosen():
    """The language from data\\toolbox.json – or the system language if there is no valid one there (yet)."""
    language = storage.load(TOOLBOX_FILE, {}).get("language")
    return language if language in LANGUAGES else system_language()


LANGUAGE = chosen()             # applies to all texts of this process


def set_language(language):
    """Switch the language for this process. True if it changed."""
    global LANGUAGE
    if language not in LANGUAGES or language == LANGUAGE:
        return False
    LANGUAGE = language
    return True


def reload():
    """Read the language again from data\\toolbox.json (e.g. after "reload" from the Toolbox). True if it changed."""
    return set_language(chosen())


class Texts:
    """The texts of a program from its i18n.json. Call: t("id") or t("id", name=value) for {name}."""

    def __init__(self, file):
        self.file = file
        self.missing = set()                     # IDs already reported in the log
        try:
            self.table = json.loads(file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            logging.exception("Texts from %s could not be loaded", file)
            self.table = {}

    def __call__(self, id, **values):
        row = self.table.get(id) or {}
        text = row.get(LANGUAGE) or row.get(FALLBACK)
        if not text:
            if id not in self.missing:
                self.missing.add(id)
                logging.warning("Text missing in %s: %s (%s)", self.file.name, id, LANGUAGE)
            return id
        return text.format(**values) if values else text

    def __contains__(self, id):
        return id in self.table

    def all(self, id):
        """The text in all languages, e.g. {"Im Call", "In a call"} – to recognize default texts."""
        return set((self.table.get(id) or {}).values())
