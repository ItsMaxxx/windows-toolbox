"""
Legt eine Kopie von pythonw.exe mit eigenem Namen und Symbol an, z. B. runtime\\HardwareMonitor.exe.
Aufgerufen von setup.ps1 (Schritt 3) mit dem Python aus runtime\\:

    python exe_anlegen.py <Ziel.exe> <Beschreibung> <Symbol.ico>

Wozu: Der Task-Manager zeigt als Programmname die Dateibeschreibung der .exe und daneben ihr Symbol. Eine reine Kopie
von pythonw.exe hieße dort „Python“ mit Python-Logo. In der Kopie werden deshalb zwei Ressourcen ersetzt:
  - die Versionsinfo (Dateibeschreibung = <Beschreibung>, z. B. „Hardware-Monitor“)
  - das Symbol (aus <Symbol.ico>)
Die digitale Signatur von pythonw.exe wird dabei entfernt – nach der Änderung wäre sie ohnehin ungültig, und eine
ungültige Signatur sieht für Virenscanner verdächtiger aus als gar keine.

Geändert wird über die Windows-Funktionen BeginUpdateResource/UpdateResource/EndUpdateResource (kernel32) –
kein zusätzliches Werkzeug nötig.

Exitcode: 0 = angelegt oder schon aktuell, 1 = Fehler, 2 = Ziel gerade in Benutzung (Programm läuft).
"""

import ctypes
import os
import struct
import sys
from ctypes import wintypes
from pathlib import Path

RT_ICON, RT_GROUP_ICON, RT_VERSION = 3, 14, 16
SPRACHE = 1033                                   # Sprache der Ressourcen in pythonw.exe (Englisch, USA)
PRODUKT = "Toolbox"

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.BeginUpdateResourceW.restype = wintypes.HANDLE
k32.BeginUpdateResourceW.argtypes = [wintypes.LPCWSTR, wintypes.BOOL]
k32.UpdateResourceW.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, wintypes.WORD, ctypes.c_void_p,
                                wintypes.DWORD]
k32.EndUpdateResourceW.argtypes = [wintypes.HANDLE, wintypes.BOOL]
k32.LoadLibraryExW.restype = wintypes.HMODULE
k32.LoadLibraryExW.argtypes = [wintypes.LPCWSTR, wintypes.HANDLE, wintypes.DWORD]
k32.FreeLibrary.argtypes = [wintypes.HMODULE]
k32.EnumResourceNamesW.argtypes = [wintypes.HMODULE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
ENUM_NAMEN = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HMODULE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)


def fehler(text):
    raise OSError(f"{text} (Windows-Fehler {ctypes.get_last_error()})")


# ---------- Signatur entfernen ----------
def ohne_signatur(daten):
    """pythonw.exe ohne die Signatur: Eintrag im Datenverzeichnis „Security“ leeren, die Daten am Dateiende abschneiden."""
    daten = bytearray(daten)
    pe = struct.unpack_from("<I", daten, 0x3C)[0]                       # Beginn des PE-Kopfs
    magic = struct.unpack_from("<H", daten, pe + 24)[0]                 # 0x20B = 64 Bit, 0x10B = 32 Bit
    eintrag = pe + 24 + (112 if magic == 0x20B else 96) + 4 * 8         # Datenverzeichnis Nr. 4 = Security
    offset, groesse = struct.unpack_from("<II", daten, eintrag)
    if offset and offset + groesse == len(daten):                       # Signatur steht immer am Ende
        del daten[offset:]
        struct.pack_into("<II", daten, eintrag, 0, 0)
    return bytes(daten)


# ---------- Versionsinfo ----------
def knoten(name, wert=b"", kinder=(), text=False):
    """Ein Block der Versionsinfo (VS_VERSIONINFO, StringFileInfo, …): Länge, Wertlänge, Typ, Name, Wert, Unterblöcke.
    Alles ist auf 4 Byte ausgerichtet."""
    def auffuellen(b):
        return b + b"\0" * (-len(b) % 4)

    kopf_rest = auffuellen(b"\0" * 6 + (name + "\0").encode("utf-16-le"))[6:]
    rumpf = kopf_rest + wert
    if kinder:
        rumpf = auffuellen(b"\0" * 6 + rumpf)[6:] + b"".join(auffuellen(k) for k in kinder[:-1]) + kinder[-1]
    wertlaenge = len(wert) // 2 if text else len(wert)                  # bei Text in Zeichen, sonst in Byte
    return struct.pack("<HHH", 6 + len(rumpf), wertlaenge, 1 if text else 0) + rumpf


def versionsinfo(beschreibung, dateiname):
    v = sys.version_info
    ms, ls = (v.major << 16) | v.minor, v.micro << 16
    fest = struct.pack("<13I", 0xFEEF04BD, 0x00010000, ms, ls, ms, ls, 0x3F, 0, 0x40004, 1, 0, 0, 0)
    version = f"{v.major}.{v.minor}.{v.micro}"
    texte = {
        "FileDescription": beschreibung,
        "ProductName": PRODUKT,
        "FileVersion": version,
        "ProductVersion": version,
        "InternalName": Path(dateiname).stem,
        "OriginalFilename": dateiname,
        "Comments": f"pythonw.exe (Python {version}) mit eigenem Namen und Symbol – angelegt von Einrichten.cmd",
        "LegalCopyright": "Python: Copyright © Python Software Foundation",
    }
    eintraege = [knoten(k, (w + "\0").encode("utf-16-le"), text=True) for k, w in texte.items()]
    tabelle = knoten(f"{SPRACHE:04X}04B0", kinder=eintraege, text=True)  # 04B0 = Unicode
    return knoten("VS_VERSION_INFO", fest, kinder=[
        knoten("StringFileInfo", kinder=[tabelle], text=True),
        knoten("VarFileInfo", kinder=[knoten("Translation", struct.pack("<HH", SPRACHE, 1200))], text=True),
    ])


# ---------- Symbol ----------
def symbol_teile(ico):
    """.ico -> (Bilder für RT_ICON, Verzeichnis für RT_GROUP_ICON). Das Verzeichnis verweist per Nummer auf die Bilder."""
    _, typ, anzahl = struct.unpack_from("<HHH", ico, 0)
    if typ != 1:
        raise ValueError("keine .ico-Datei")
    bilder, verzeichnis = [], struct.pack("<HHH", 0, 1, anzahl)
    for i in range(anzahl):
        b, h, farben, _, ebenen, bits, groesse, offset = struct.unpack_from("<BBBBHHII", ico, 6 + 16 * i)
        bilder.append(ico[offset:offset + groesse])
        verzeichnis += struct.pack("<BBBBHHIH", b, h, farben, 0, ebenen, bits, groesse, i + 1)
    return bilder, verzeichnis


def vorhandene(pfad, typ):
    """Nummern der Ressourcen eines Typs in einer .exe (z. B. die 12 Python-Symbolbilder)."""
    modul = k32.LoadLibraryExW(str(pfad), None, 0x2)                    # LOAD_LIBRARY_AS_DATAFILE
    if not modul:
        fehler(f"{pfad} lässt sich nicht lesen")
    nummern = []
    rueckruf = ENUM_NAMEN(lambda m, t, name, _: nummern.append(name) or True)
    k32.EnumResourceNamesW(modul, typ, rueckruf, None)                  # False, wenn es keine gibt – auch gut
    k32.FreeLibrary(modul)
    return [n for n in nummern if n < 0x10000]                         # nur Nummern, keine Namen


def ressource(handle, typ, nummer, daten):
    """Ressource setzen bzw. mit daten=None löschen."""
    puffer = ctypes.create_string_buffer(daten, len(daten)) if daten is not None else None
    if not k32.UpdateResourceW(handle, typ, nummer, SPRACHE, puffer, len(daten) if daten else 0):
        fehler(f"Ressource {typ}/{nummer} lässt sich nicht ändern")


def namen_vergessen(ziel):
    """Windows merkt sich Programmnamen im „MuiCache“ – dort stünde für eine frühere reine Kopie noch „Python“, und der
    Task-Manager zeigte weiter den alten Namen. Den Eintrag löschen, dann liest Windows den Namen neu aus der Datei."""
    import winreg
    schluessel = r"Software\Classes\Local Settings\Software\Microsoft\Windows\Shell\MuiCache"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, schluessel, 0, winreg.KEY_SET_VALUE) as k:
            for endung in (".FriendlyAppName", ".ApplicationCompany"):
                try:
                    winreg.DeleteValue(k, str(ziel.resolve()) + endung)
                except FileNotFoundError:
                    pass
    except OSError:
        pass                                     # kein MuiCache – nichts zu vergessen


# ---------- Ablauf ----------
def anlegen(ziel, beschreibung, ico_pfad):
    quelle = Path(sys.executable).with_name("pythonw.exe")
    neu = ziel.with_name(ziel.name + ".neu")
    neu.write_bytes(ohne_signatur(quelle.read_bytes()))
    try:
        bilder, verzeichnis = symbol_teile(ico_pfad.read_bytes())
        alte_bilder = vorhandene(neu, RT_ICON)
        handle = k32.BeginUpdateResourceW(str(neu), False)
        if not handle:
            fehler("BeginUpdateResource fehlgeschlagen")
        for nummer in vorhandene(neu, RT_GROUP_ICON):
            ressource(handle, RT_GROUP_ICON, nummer, None)              # Python-Symbol raus …
        for nummer in alte_bilder:
            if nummer > len(bilder):
                ressource(handle, RT_ICON, nummer, None)
        for nummer, bild in enumerate(bilder, start=1):                 # … eigenes rein
            ressource(handle, RT_ICON, nummer, bild)
        ressource(handle, RT_GROUP_ICON, 1, verzeichnis)
        ressource(handle, RT_VERSION, 1, versionsinfo(beschreibung, ziel.name))
        if not k32.EndUpdateResourceW(handle, False):
            fehler("EndUpdateResource fehlgeschlagen")

        namen_vergessen(ziel)
        if ziel.exists() and ziel.read_bytes() == neu.read_bytes():
            print(f"{ziel.name} ist schon aktuell")
            return 0
        try:
            os.replace(neu, ziel)
        except PermissionError:
            print(f"{ziel.name} ist gerade in Benutzung – nach dem Beenden des Programms erneut einrichten")
            return 2
        print(f"{ziel.name} angelegt")
        return 0
    finally:
        neu.unlink(missing_ok=True)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    try:
        sys.exit(anlegen(Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])))
    except (OSError, ValueError) as e:
        print(f"Fehler: {e}")
        sys.exit(1)
