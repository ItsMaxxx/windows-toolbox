"""
Where saved data lives: in the folder data\\ in the main folder – separate from the code and from runtime\\.

    data\\toolbox.json              settings of the Toolbox itself
    data\\<program>.json            one file per program, e.g. hardware_monitor.json
    data\\logs\\<program>.log        errors and notes (pythonw has no console)

To back up or take along, data\\ is all you need. Program pages get their file automatically (ToolPage.settings_file),
standalone programs get it with storage.settings_file("<program>"). Reading and writing is done everywhere with
load() and save().
"""

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
LOG_DIR = DATA_DIR / "logs"

# Until October 2026 the folder was called daten\ and some files and values had German names
OLD_DATA_DIR = ROOT / "daten"
OLD_FILE_NAMES = {"installiert.json": "installed.json"}
OLD_KEYS = {"installed.json": {"programme": "programs"}, "toolbox.json": {"sprache": "language"}}
OLD_VALUES = {"toolbox.json": {"appearance": {"Hell": "Light", "Dunkel": "Dark"}}}


def migrate_old_data():
    """Moves everything from daten\\ to data\\ once, with the new file names, keys and values. If a file is already
    in data\\ (e.g. written by Setup.exe in the meantime), its values win – the old ones only fill in what's missing.
    daten\\ is deleted afterwards; if something goes wrong, it stays and the next start tries again."""
    if not OLD_DATA_DIR.is_dir():
        return
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        for old in OLD_DATA_DIR.glob("*.json"):
            name = OLD_FILE_NAMES.get(old.name, old.name)
            try:
                data = json.loads(old.read_text(encoding="utf-8-sig"))
            except ValueError:
                data = None                     # broken – the program falls back to its defaults anyway
            if isinstance(data, dict):
                renamed = OLD_KEYS.get(name, {})
                data = {renamed.get(key, key): value for key, value in data.items()}
                for key, values in OLD_VALUES.get(name, {}).items():
                    if data.get(key) in values:
                        data[key] = values[data[key]]
                data.update(load(DATA_DIR / name, {}))
                save(DATA_DIR / name, data)
            old.unlink()
        for old in (OLD_DATA_DIR / "logs").glob("*.log"):
            new = LOG_DIR / old.name
            text = old.read_text(encoding="utf-8", errors="replace")
            if new.exists():
                text += new.read_text(encoding="utf-8", errors="replace")     # old lines first
            new.write_text(text, encoding="utf-8")
            old.unlink()
        for folder in (OLD_DATA_DIR / "logs", OLD_DATA_DIR):
            if folder.is_dir():
                folder.rmdir()                  # only if empty – anything unknown stays there
    except OSError:
        pass


def settings_file(program):
    """data\\<program>.json – e.g. settings_file("toolbox") or settings_file("hardware_monitor")."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR / f"{program}.json"


def log_file(program):
    """data\\logs\\<program>.log"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    return LOG_DIR / f"{program}.log"


def load(file, defaults):
    """Defaults, overwritten with what is in file. Unknown keys are kept; whether the values are valid is up to the
    caller to check. If the file is missing or broken, you simply get the defaults."""
    data = copy.deepcopy(defaults)
    try:
        saved = json.loads(file.read_text(encoding="utf-8"))
        if isinstance(saved, dict):
            data.update(saved)
    except (OSError, ValueError):
        pass
    return data


def save(file, data):
    """Saves data as readable JSON. Raises OSError if it doesn't work."""
    file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


migrate_old_data()
