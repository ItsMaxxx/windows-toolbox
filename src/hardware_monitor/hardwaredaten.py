"""
Feste Daten der Hardware für den Tab „Hardwaredaten“: Hersteller, Modell, Hersteller- und Produkt-IDs,
Seriennummern, Treiber. Gelesen über WMI (Windows-Verwaltungsschnittstelle) per pythonnet – einmal beim Öffnen des
Fensters, nicht laufend. Braucht keine Adminrechte und kein LibreHardwareMonitor.

Zum Ausprobieren:  python hardwaredaten.py   -> gibt alles aus, was der Tab zeigen würde
"""

import logging
import platform
import re
from collections import Counter
from datetime import date

# Was ein Feld bedeutet – erscheint beim Drüberfahren in der Fußzeile des Fensters
ERKLAERUNGEN = {
    "Hersteller-ID": "Kennung des Chip-Herstellers (Vendor ID), z. B. 10DE = Nvidia. Weltweit eindeutig vergeben.",
    "Produkt-ID": "Kennung des Chips beim Hersteller (Device ID bzw. bei USB Product ID).",
    "Platinen-Hersteller": "Wer die Karte gebaut hat (Subsystem Vendor ID) – bei Grafikkarten z. B. Asus oder MSI, "
                           "auch wenn der Chip von Nvidia ist.",
    "Subsystem-ID": "Kennung des genauen Kartenmodells beim Platinen-Hersteller.",
    "Revision": "Überarbeitungsstand des Chips.",
    "Hardware-ID": "Vollständige Kennung, unter der Windows das Gerät führt – gut für die Treibersuche.",
    "Prozessor-ID": "CPUID-Kennung: Merkmale, Familie, Modell und Stepping des Prozessors (keine Seriennummer).",
    "MAC-Adresse": "Die feste Hardware-Adresse des Netzwerkanschlusses.",
    "Seriennummer": "Seriennummer laut Gerät; fehlt, wenn der Hersteller keine hinterlegt hat.",
    "Teilenummer": "Bestellnummer des Herstellers – damit findet man genau diesen Riegel wieder.",
    "Takt": "Eingestellter Speichertakt in Megatransfers pro Sekunde.",
    "Takt laut Riegel": "Höchster Takt, den der Riegel ohne XMP/EXPO meldet.",
}

# PCI-Herstellerkennungen (Auszug: die bei Desktop-PCs häufigsten)
PCI_HERSTELLER = {
    "10DE": "Nvidia", "1002": "AMD", "1022": "AMD", "8086": "Intel", "10EC": "Realtek", "144D": "Samsung",
    "1043": "Asus", "1462": "MSI", "1458": "Gigabyte", "1849": "ASRock", "15B7": "SanDisk / WD", "1B4B": "Marvell",
    "14E4": "Broadcom", "168C": "Qualcomm Atheros", "1969": "Qualcomm Atheros", "1E0F": "Kioxia", "1179": "Toshiba",
    "1987": "Phison", "126F": "Silicon Motion", "1CC1": "ADATA", "2646": "Kingston", "C0A9": "Crucial",
    "1344": "Micron", "3842": "EVGA", "1DA2": "Sapphire", "174B": "Sapphire", "196E": "PNY", "19DA": "Zotac",
    "1682": "XFX", "148C": "PowerColor", "1569": "Palit", "10B0": "Gainward", "1028": "Dell", "103C": "HP",
    "17AA": "Lenovo", "1025": "Acer", "1B21": "ASMedia", "1D6A": "Aquantia",
}
# USB-Herstellerkennungen (Auszug)
USB_HERSTELLER = {
    "046D": "Logitech", "1532": "Razer", "1235": "Focusrite", "056A": "Wacom", "0DB0": "MSI", "1462": "MSI",
    "2E1A": "Insta360", "045E": "Microsoft", "1B1C": "Corsair", "1038": "SteelSeries", "0951": "Kingston",
    "03F0": "HP", "04F2": "Chicony", "05AC": "Apple", "054C": "Sony", "0781": "SanDisk", "0BDA": "Realtek",
    "8087": "Intel", "046A": "Cherry", "0B05": "Asus", "26CE": "ASRock", "048D": "ITE", "1B21": "ASMedia",
    "2109": "VIA Labs", "05E3": "Genesys Logic", "0A12": "Cambridge Silicon Radio", "1050": "Yubico",
    "0B95": "ASIX", "18D1": "Google", "04E8": "Samsung", "2717": "Xiaomi",
}
# RAM-Hersteller aus dem Anfang der Teilenummer – Windows meldet beim Hersteller oft nur „Unknown“
RAM_TEILENUMMER = (
    (r"F[345]-", "G.Skill"), (r"CM", "Corsair"), (r"KF|KHX|KVR|KCP", "Kingston"), (r"BL|CT", "Crucial"),
    (r"M[34]\d\d", "Samsung"), (r"HM", "SK Hynix"), (r"MTA", "Micron"), (r"A[XD][45]", "ADATA"),
)
RAM_TYPEN = {20: "DDR", 21: "DDR2", 24: "DDR3", 26: "DDR4", 30: "LPDDR4", 34: "DDR5", 35: "LPDDR5"}
BUS_TYPEN = {1: "SCSI", 3: "ATA", 7: "USB", 8: "RAID", 9: "iSCSI", 10: "SAS", 11: "SATA", 12: "SD-Karte",
             17: "NVMe"}
MEDIEN_TYPEN = {3: "Festplatte (HDD)", 4: "SSD"}
CPU_HERSTELLER = {"AuthenticAMD": "AMD", "GenuineIntel": "Intel"}
PLATZHALTER = {"", "unknown", "default string", "to be filled by o.e.m.", "none", "not available", "00000000"}


# ---------- WMI ----------
def abfrage(wql, scope=r"root\cimv2"):
    """Führt eine WMI-Abfrage aus. Ergebnis: Liste von dicts (Werte als Text oder None); bei Fehlern leer."""
    try:
        import clr  # pythonnet – im Hardware-Monitor ohnehin geladen
        clr.AddReference("System.Management")
        from System.Management import ManagementObjectSearcher
        with ManagementObjectSearcher(scope, wql) as searcher:
            return [{p.Name: None if p.Value is None else str(p.Value) for p in obj.Properties}
                    for obj in searcher.Get()]
    except Exception:
        logging.exception("WMI-Abfrage fehlgeschlagen: %s", wql)
        return []


# ---------- Helfer ----------
def wert(text):
    """Bereinigter Text – oder None für leere Werte und Platzhalter wie „To Be Filled By O.E.M.“."""
    text = (text or "").strip()
    return None if text.lower() in PLATZHALTER else text


def mit_namen(kennung, tabelle):
    """„10DE“ -> „10DE (Nvidia)“, unbekannte Kennungen bleiben, wie sie sind."""
    return f"{kennung} ({tabelle[kennung]})" if kennung in tabelle else kennung


def zahl(text):
    try:
        return int(text)
    except (TypeError, ValueError):
        return None


def num(value, decimals):
    return f"{value:.{decimals}f}".replace(".", ",")


def datum(text):
    """WMI-Datum „20210303000000.000000+000“ -> „03.03.2021“."""
    m = re.match(r"(\d{4})(\d\d)(\d\d)", text or "")
    return f"{m[3]}.{m[2]}.{m[1]}" if m else None


def hardware_id(pnp):
    """„PCI\\VEN_10DE&DEV_2805&…\\4&1FC9…“ -> „PCI\\VEN_10DE&DEV_2805&…“ (ohne den Teil, der nur den Steckplatz angibt)."""
    return pnp.rsplit("\\", 1)[0] if pnp and pnp.count("\\") >= 2 else pnp


def pci_felder(pnp):
    """Hersteller-, Produkt- und Subsystem-ID aus einer PCI- oder HD-Audio-Kennung."""
    m = re.search(r"VEN_([0-9A-F]{4})&DEV_([0-9A-F]{4})(?:&SUBSYS_([0-9A-F]{8}))?(?:&REV_([0-9A-F]+))?",
                  pnp or "", re.I)
    if not m:
        return []
    ven, dev, subsys, rev = (g.upper() if g else None for g in m.groups())
    felder = [("Hersteller-ID", mit_namen(ven, PCI_HERSTELLER)), ("Produkt-ID", dev)]
    if subsys and subsys != "00000000":
        # PCI: SUBSYS_<Modell><Hersteller>, HD-Audio umgekehrt: SUBSYS_<Hersteller><Modell>
        sub_dev, sub_ven = (subsys[4:], subsys[:4]) if pnp.upper().startswith("HDAUDIO") else (subsys[:4], subsys[4:])
        felder += [("Platinen-Hersteller", mit_namen(sub_ven, PCI_HERSTELLER)), ("Subsystem-ID", sub_dev)]
    if rev:
        felder.append(("Revision", rev))
    return felder + [("Hardware-ID", hardware_id(pnp))]


def usb_ids(pnp):
    m = re.search(r"VID_([0-9A-F]{4})&PID_([0-9A-F]{4})", pnp or "", re.I)
    return (m[1].upper(), m[2].upper()) if m else None


def ids_felder(pnp):
    """IDs aus einer PCI- oder USB-Kennung (Netzwerkadapter können beides sein)."""
    ids = usb_ids(pnp)
    if ids:
        return [("Hersteller-ID", mit_namen(ids[0], USB_HERSTELLER)), ("Produkt-ID", ids[1]),
                ("Hardware-ID", hardware_id(pnp))]
    return pci_felder(pnp)


def felder_ohne_leere(felder):
    return [(name, w) for name, w in felder if w]


# ---------- Die einzelnen Bereiche ----------
def prozessoren():
    geraete = []
    for p in abfrage("SELECT Name, Manufacturer, ProcessorId, NumberOfCores, NumberOfLogicalProcessors, "
                     "MaxClockSpeed, SocketDesignation, L2CacheSize, L3CacheSize FROM Win32_Processor"):
        hersteller = wert(p["Manufacturer"])
        l3 = zahl(p["L3CacheSize"])
        geraete.append((wert(p["Name"]) or "Prozessor", felder_ohne_leere([
            ("Hersteller", CPU_HERSTELLER.get(hersteller, hersteller)),
            ("Kerne / Threads", f"{p['NumberOfCores']} / {p['NumberOfLogicalProcessors']}"),
            ("Grundtakt", f"{p['MaxClockSpeed']} MHz" if zahl(p["MaxClockSpeed"]) else None),
            ("L3-Cache", f"{l3 // 1024} MB" if l3 else None),
            ("Sockel", wert(p["SocketDesignation"])),
            ("Prozessor-ID", wert(p["ProcessorId"])),
        ])))
    return geraete


def grafikkarten():
    geraete = []
    for g in abfrage("SELECT Name, PNPDeviceID, DriverVersion, DriverDate FROM Win32_VideoController"):
        if not (g["PNPDeviceID"] or "").upper().startswith("PCI\\"):
            continue                             # virtuelle Anzeigen (Fernwartung, Streaming) weglassen
        geraete.append((wert(g["Name"]) or "Grafikkarte", felder_ohne_leere(
            pci_felder(g["PNPDeviceID"])
            + [("Treiberversion", wert(g["DriverVersion"])), ("Treiberdatum", datum(g["DriverDate"]))])))
    return geraete


def mainboard():
    geraete = []
    for b in abfrage("SELECT Manufacturer, Product, Version, SerialNumber FROM Win32_BaseBoard"):
        hersteller, modell = wert(b["Manufacturer"]), wert(b["Product"])
        felder = [("Hersteller", hersteller), ("Modell", modell), ("Version", wert(b["Version"])),
                  ("Seriennummer", wert(b["SerialNumber"]))]
        for bios in abfrage("SELECT Manufacturer, SMBIOSBIOSVersion, ReleaseDate FROM Win32_BIOS"):
            felder += [("BIOS-Hersteller", wert(bios["Manufacturer"])),
                       ("BIOS-Version", wert(bios["SMBIOSBIOSVersion"])), ("BIOS-Datum", datum(bios["ReleaseDate"]))]
        geraete.append((" ".join(filter(None, (hersteller, modell))) or "Mainboard", felder_ohne_leere(felder)))
    return geraete


def arbeitsspeicher():
    geraete = []
    for r in abfrage("SELECT Manufacturer, PartNumber, SerialNumber, BankLabel, DeviceLocator, Capacity, Speed, "
                     "ConfiguredClockSpeed, SMBIOSMemoryType FROM Win32_PhysicalMemory"):
        teil = wert(r["PartNumber"])
        hersteller = wert(r["Manufacturer"])
        if not hersteller and teil:
            geraten = next((name for muster, name in RAM_TEILENUMMER if re.match(muster, teil)), None)
            hersteller = f"{geraten} (laut Teilenummer)" if geraten else None
        groesse = zahl(r["Capacity"])
        eingestellt, maximal = zahl(r["ConfiguredClockSpeed"]), zahl(r["Speed"])
        name = " ".join(filter(None, (hersteller.split(" (")[0] if hersteller else None, teil)))
        geraete.append((name or "Speicherriegel", felder_ohne_leere([
            ("Hersteller", hersteller),
            ("Teilenummer", teil),
            ("Größe", f"{groesse // 1024 ** 3} GB" if groesse else None),
            ("Typ", RAM_TYPEN.get(zahl(r["SMBIOSMemoryType"]))),
            ("Takt", f"{eingestellt} MT/s" if eingestellt else None),
            ("Takt laut Riegel", f"{maximal} MT/s" if maximal and maximal != eingestellt else None),
            ("Steckplatz", " / ".join(filter(None, (wert(r["BankLabel"]), wert(r["DeviceLocator"]))))),
            ("Seriennummer", wert(r["SerialNumber"])),
        ])))
    return geraete


def laufwerke():
    geraete = []
    for d in sorted(abfrage("SELECT DeviceId, FriendlyName, SerialNumber, FirmwareVersion, Size, BusType, MediaType "
                            "FROM MSFT_PhysicalDisk", scope=r"root\Microsoft\Windows\Storage"),
                    key=lambda d: zahl(d["DeviceId"]) or 0):
        groesse = zahl(d["Size"])
        geraete.append((wert(d["FriendlyName"]) or "Laufwerk", felder_ohne_leere([
            ("Art", MEDIEN_TYPEN.get(zahl(d["MediaType"]))),
            ("Anschluss", BUS_TYPEN.get(zahl(d["BusType"]))),
            ("Größe", None if not groesse else f"{num(groesse / 1e12, 1)} TB" if groesse >= 1e12
             else f"{groesse / 1e9:.0f} GB"),
            ("Seriennummer", (wert(d["SerialNumber"]) or "").rstrip(".") or None),
            ("Firmware", wert(d["FirmwareVersion"])),
            ("Datenträger-Nr.", d["DeviceId"]),
        ])))
    return geraete


def netzwerk():
    geraete = []
    for n in abfrage("SELECT Name, PNPDeviceID, MACAddress FROM Win32_NetworkAdapter WHERE PhysicalAdapter = TRUE"):
        if not re.match(r"(PCI|USB)\\", n["PNPDeviceID"] or "", re.I):
            continue                             # virtuelle Adapter (VPN, Hyper-V, …) weglassen
        geraete.append((wert(n["Name"]) or "Netzwerkadapter",
                        felder_ohne_leere(ids_felder(n["PNPDeviceID"]) + [("MAC-Adresse", wert(n["MACAddress"]))])))
    return geraete


def audio():
    geraete = []
    for s in abfrage("SELECT Name, PNPDeviceID FROM Win32_SoundDevice"):
        pnp = s["PNPDeviceID"] or ""
        if not re.match(r"(PCI|HDAUDIO)\\", pnp, re.I):
            continue                             # USB-Audio steht bei den USB-Geräten, virtuelle fehlen ganz
        name = wert(s["Name"]) or "Audiogerät"
        m = re.search(r"VEN_10EC&DEV_0([0-9A-F]{3})", pnp, re.I)
        if m and name.startswith("High Definition Audio"):
            name = f"Realtek ALC{m[1]}"           # Realtek-Codecs heißen wie ihre Produkt-ID, z. B. 0892 -> ALC892
        geraete.append((name, felder_ohne_leere(pci_felder(pnp))))
    return geraete


GENERISCH = re.compile(r"^(USB|HID)\b|Verbundgerät|Composite|Eingabegerät|Input Device|Audiogerät", re.I)


def usb_geraete():
    """Angeschlossene USB-Geräte, eins pro Hersteller-/Produkt-ID (ein Gerät meldet sich oft mehrfach an)."""
    gruppen = {}
    for e in abfrage("SELECT Name, Manufacturer, PNPDeviceID FROM Win32_PnPEntity WHERE PNPDeviceID LIKE 'USB%'"):
        ids = usb_ids(e["PNPDeviceID"])
        if ids:
            gruppen.setdefault(ids, []).append(e)
    geraete = []
    for (vid, pid), eintraege in gruppen.items():
        namen = [n for n in (wert(e["Name"]) for e in eintraege) if n and not GENERISCH.search(n)]
        hersteller = USB_HERSTELLER.get(vid) or next(
            (h for h in (wert(e["Manufacturer"]) for e in eintraege)
             if h and not h.startswith("(") and not h.startswith("Microsoft")), None)
        # Seriennummer: steht bei vielen Geräten als letzter Teil der Kennung (ohne „&“, das wäre eine Windows-Nummer)
        seriennr = next((e["PNPDeviceID"].rsplit("\\", 1)[1] for e in eintraege
                         if "&MI_" not in e["PNPDeviceID"].upper() and "&" not in e["PNPDeviceID"].rsplit("\\", 1)[1]),
                        None)
        name = namen[0] if namen else f"USB-Gerät ({hersteller})" if hersteller else "USB-Gerät"
        geraete.append((name, felder_ohne_leere([
            ("Hersteller-ID", mit_namen(vid, USB_HERSTELLER) if vid in USB_HERSTELLER
             else f"{vid} ({hersteller})" if hersteller else vid),
            ("Produkt-ID", pid),
            ("Seriennummer", seriennr),
            ("Hardware-ID", f"USB\\VID_{vid}&PID_{pid}"),
        ])))
    return sorted(geraete, key=lambda g: g[0].lower())


BEREICHE = (("Prozessor", prozessoren), ("Grafikkarte", grafikkarten), ("Mainboard", mainboard),
            ("Arbeitsspeicher", arbeitsspeicher), ("Laufwerke", laufwerke), ("Netzwerk", netzwerk),
            ("Audio", audio), ("USB-Geräte", usb_geraete))


def lesen():
    """Alle Bereiche: [(Bereich, [(Gerätename, [(Feld, Wert), …]), …]), …] – leere Bereiche fehlen."""
    daten = []
    for bereich, funktion in BEREICHE:
        try:
            geraete = funktion()
        except Exception:                        # ein kaputter Bereich soll die anderen nicht verhindern
            logging.exception("Hardwaredaten: Bereich %s konnte nicht gelesen werden", bereich)
            continue
        if geraete:
            daten.append((bereich, geraete))
    return daten


# ---------- Als Text (Kopieren im Tab Hardwaredaten) ----------
def als_text(bereich, geraete):
    """Ein Bereich mit allen Geräten und Feldern – zum Einfügen in Forum, Chat, Notizen."""
    bloecke = ["\n".join([name] + [f"  {feld}: {w}" for feld, w in felder]) for name, felder in geraete]
    return f"=== {bereich} ===\n" + "\n\n".join(bloecke)


def alles_als_text(daten):
    """Alle Bereiche, mit Computername und Datum oben drüber."""
    kopf = f"Hardwaredaten von {platform.node()} – Stand {date.today():%d.%m.%Y}"
    return kopf + "\n\n" + "\n\n\n".join(als_text(b, g) for b, g in daten) + "\n"


def modellnamen_als_text(daten):
    """Nur die Modellnamen: der Bereich, darunter je Gerät eine Zeile mit Tab davor – gleiche Geräte zusammengefasst
    („2× G.Skill …“)."""
    zeilen = []
    for bereich, geraete in daten:
        namen = Counter(name for name, _ in geraete)
        zeilen += [bereich] + [f"\t{n}× {name}" if n > 1 else f"\t{name}" for name, n in namen.items()]
    return "\n".join(zeilen) + "\n"


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    for bereich, geraete in lesen():
        print(f"\n=== {bereich} ===")
        for name, felder in geraete:
            print(f"  {name}")
            for feld, w in felder:
                print(f"      {feld:20} {w}")
