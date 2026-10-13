"""
Feste Daten der Hardware für den Tab „Hardwaredaten“: Hersteller, Modell, Hersteller- und Produkt-IDs,
Seriennummern, Treiber. Gelesen über WMI (Windows-Verwaltungsschnittstelle) per pythonnet – einmal beim Öffnen des
Fensters, nicht laufend. Braucht keine Adminrechte und kein LibreHardwareMonitor.

Bereiche und Felder stehen hier als ID (z. B. "grafikkarte", "hersteller_id"); ihre Namen und Erklärungen stehen in
i18n.json (hw.bereich.…, hw.feld.…, hw.erklaerung.…) und werden erst beim Anzeigen bzw. Kopieren eingesetzt.

Zum Ausprobieren:  python hardwaredaten.py   -> gibt alles aus, was der Tab zeigen würde
"""

import ctypes
import logging
import platform
import re
import uuid
from collections import Counter
from datetime import date

from hardware_monitor_einstellungen import t

# PCI-Herstellerkennungen (Auszug: die bei Desktop-PCs häufigsten)
PCI_HERSTELLER = {
    "10DE": "Nvidia", "1002": "AMD", "1022": "AMD", "8086": "Intel", "10EC": "Realtek", "144D": "Samsung",
    "1043": "Asus", "1462": "MSI", "1458": "Gigabyte", "1849": "ASRock", "15B7": "SanDisk / WD", "1B4B": "Marvell",
    "14E4": "Broadcom", "168C": "Qualcomm Atheros", "1969": "Qualcomm Atheros", "1E0F": "Kioxia", "1179": "Toshiba",
    "1987": "Phison", "126F": "Silicon Motion", "1CC1": "ADATA", "2646": "Kingston", "C0A9": "Crucial",
    "1344": "Micron", "3842": "EVGA", "1DA2": "Sapphire", "174B": "Sapphire", "196E": "PNY", "19DA": "Zotac",
    "1682": "XFX", "148C": "PowerColor", "1569": "Palit", "10B0": "Gainward", "1028": "Dell", "103C": "HP",
    "17AA": "Lenovo", "1025": "Acer", "1B21": "ASMedia", "1D6A": "Aquantia", "14F1": "Conexant / Senary",
    "152D": "Quanta", "1D72": "Xiaomi", "19E5": "Huawei",
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
RAM_TYPEN = {20: "DDR", 21: "DDR2", 24: "DDR3", 26: "DDR4", 29: "LPDDR3", 30: "LPDDR4", 34: "DDR5", 35: "LPDDR5"}
# Werte mit „hw.wert.…“ sind IDs aus i18n.json, der Rest Namen, die überall gleich heißen (siehe anzeige())
RAM_BAUFORMEN = {8: "hw.wert.dimm", 12: "hw.wert.sodimm"}     # Win32_PhysicalMemory.FormFactor
NETZ_ARTEN = {14: "hw.wert.lan", 9: "WLAN", 1: "WLAN", 8: "hw.wert.mobilfunk", 10: "Bluetooth"}   # NdisPhysicalMedium
BUS_TYPEN = {1: "SCSI", 3: "ATA", 7: "USB", 8: "RAID", 9: "iSCSI", 10: "SAS", 11: "SATA", 12: "hw.wert.sd_karte",
             17: "NVMe"}
MEDIEN_TYPEN = {3: "hw.wert.hdd", 4: "SSD"}
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


# ---------- DXCore (Windows-Grafikschnittstelle): integrierte oder eigene GPU? ----------
class GUID(ctypes.Structure):
    _fields_ = [("bytes", ctypes.c_ubyte * 16)]

    def __init__(self, text):
        super().__init__()
        ctypes.memmove(self.bytes, uuid.UUID(text).bytes_le, 16)


def com_methode(obj, nr, ergebnis, *argtypes):
    """Methode Nr. nr eines COM-Objekts, gezählt wie in dxcore_interface.h (0–2: QueryInterface, AddRef, Release)."""
    vtable = ctypes.cast(obj, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    return lambda *args: ctypes.WINFUNCTYPE(ergebnis, ctypes.c_void_p, *argtypes)(vtable[nr])(obj, *args)


def gpu_arten():
    """(Hersteller-ID, Produkt-ID, Subsystem) -> „Integriert (im Prozessor)“ / „Extern (eGPU)“ / „Dediziert“.
    Am Namen lässt sich das nicht erkennen („Intel Arc Graphics“ ist integriert, „Intel Arc A770“ eine Karte)."""
    from ctypes import POINTER, byref, c_bool, c_size_t, c_uint32, c_void_p
    HRESULT = ctypes.HRESULT
    factory, liste = c_void_p(), c_void_p()
    ctypes.WinDLL("dxcore").DXCoreCreateAdapterFactory(byref(GUID("78ee5945-c36e-4b13-a669-005dd11c0f06")),
                                                       byref(factory))
    com_methode(factory, 3, HRESULT, c_uint32, POINTER(GUID), POINTER(GUID), POINTER(c_void_p))(   # CreateAdapterList
        1, byref(GUID("248e2800-a793-4724-abaa-23a6de1be090")),         # alle GPUs, die rechnen können
        byref(GUID("526c7776-40e9-459b-b711-f32ad76dfc28")), byref(liste))
    arten = {}
    for i in range(com_methode(liste, 4, c_uint32)()):                # GetAdapterCount
        adapter = c_void_p()
        com_methode(liste, 3, HRESULT, c_uint32, POINTER(GUID), POINTER(c_void_p))(               # GetAdapter
            i, byref(GUID("f0db4c7f-fe5a-42a2-bd62-f2a6cf6fc83e")), byref(adapter))
        eigenschaft = com_methode(adapter, 6, HRESULT, c_uint32, c_size_t, c_void_p)               # GetProperty
        ids, integriert, extern = (c_uint32 * 4)(), c_bool(), c_bool()
        eigenschaft(3, ctypes.sizeof(ids), ids)                         # HardwareID: Hersteller, Produkt, Subsystem
        eigenschaft(12, 1, byref(integriert))                           # IsIntegrated
        eigenschaft(13, 1, byref(extern))                               # IsDetachable
        arten[(f"{ids[0]:04X}", f"{ids[1]:04X}", f"{ids[2]:08X}")] = (
            t("hw.wert.integriert") if integriert.value else t("hw.wert.extern") if extern.value
            else t("hw.wert.dediziert"))
        com_methode(adapter, 2, c_uint32)()                             # Release
    com_methode(liste, 2, c_uint32)()
    com_methode(factory, 2, c_uint32)()
    return arten


# ---------- Namen in der gewählten Sprache ----------
def bereichsname(bereich):
    """"grafikkarte" -> „Grafikkarte“ bzw. „Graphics card“."""
    return t(f"hw.bereich.{bereich}")


def feldname(feld):
    """"hersteller_id" -> „Hersteller-ID“ bzw. „Vendor ID“."""
    return t(f"hw.feld.{feld}")


def erklaerung(feld):
    """Was ein Feld bedeutet (Fußzeile des Fensters) – oder None, wenn es keine Erklärung gibt."""
    return t(f"hw.erklaerung.{feld}") if f"hw.erklaerung.{feld}" in t else None


def anzeige(eintrag):
    """Eintrag aus RAM_BAUFORMEN usw.: eine ID wird übersetzt, ein Name bleibt; None bleibt None."""
    return t(eintrag) if eintrag and eintrag in t else eintrag


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
    """Zahl mit deutschem Komma, z. B. num(2.54, 1) -> „2,5“ (auch für die Messwerte im Detailfenster)."""
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
    felder = [("hersteller_id", mit_namen(ven, PCI_HERSTELLER)), ("produkt_id", dev)]
    if subsys and subsys != "00000000":
        # PCI: SUBSYS_<Modell><Hersteller>, Audio-Codecs umgekehrt: SUBSYS_<Hersteller><Modell>
        codec = re.match(r"HDAUDIO\\|INTELAUDIO\\FUNC_", pnp, re.I)
        sub_dev, sub_ven = (subsys[4:], subsys[:4]) if codec else (subsys[:4], subsys[4:])
        felder += [("platinen_hersteller", mit_namen(sub_ven, PCI_HERSTELLER)), ("subsystem_id", sub_dev)]
    if rev:
        felder.append(("revision", rev))
    return felder + [("hardware_id", hardware_id(pnp))]


def usb_ids(pnp):
    m = re.search(r"VID_([0-9A-F]{4})&PID_([0-9A-F]{4})", pnp or "", re.I)
    return (m[1].upper(), m[2].upper()) if m else None


def ids_felder(pnp):
    """IDs aus einer PCI- oder USB-Kennung (Netzwerkadapter können beides sein)."""
    ids = usb_ids(pnp)
    if ids:
        return [("hersteller_id", mit_namen(ids[0], USB_HERSTELLER)), ("produkt_id", ids[1]),
                ("hardware_id", hardware_id(pnp))]
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
        geraete.append((wert(p["Name"]) or t("hw.name.prozessor"), felder_ohne_leere([
            ("hersteller", CPU_HERSTELLER.get(hersteller, hersteller)),
            ("kerne_threads", f"{p['NumberOfCores']} / {p['NumberOfLogicalProcessors']}"),
            ("grundtakt", f"{p['MaxClockSpeed']} MHz" if zahl(p["MaxClockSpeed"]) else None),
            ("l3_cache", f"{l3 // 1024} MB" if l3 else None),
            ("sockel", wert(p["SocketDesignation"])),
            ("prozessor_id", wert(p["ProcessorId"])),
        ])))
    return geraete


def grafikkarten():
    try:
        arten = gpu_arten()
    except Exception:                            # z. B. Windows 10 vor Version 2004 (ohne dxcore.dll): Feld fehlt
        logging.exception("DXCore: Art der Grafikkarten nicht lesbar")
        arten = {}
    geraete = []
    for g in abfrage("SELECT Name, PNPDeviceID, DriverVersion, DriverDate FROM Win32_VideoController"):
        pnp = (g["PNPDeviceID"] or "").upper()
        if not pnp.startswith("PCI\\"):
            continue                             # virtuelle Anzeigen (Fernwartung, Streaming) weglassen
        m = re.search(r"VEN_(\w{4})&DEV_(\w{4})(?:&SUBSYS_(\w{8}))?", pnp)
        art = m and (arten.get(m.groups()) or next((a for ids, a in arten.items() if ids[:2] == m.groups()[:2]), None))
        geraete.append((wert(g["Name"]) or t("hw.name.grafikkarte"), felder_ohne_leere(
            [("art", art)] + pci_felder(g["PNPDeviceID"])
            + [("treiberversion", wert(g["DriverVersion"])), ("treiberdatum", datum(g["DriverDate"]))])))
    return geraete


def mainboard():
    geraete = []
    for b in abfrage("SELECT Manufacturer, Product, Version, SerialNumber FROM Win32_BaseBoard"):
        hersteller, modell = wert(b["Manufacturer"]), wert(b["Product"])
        felder = [("hersteller", hersteller), ("modell", modell), ("version", wert(b["Version"])),
                  ("seriennummer", wert(b["SerialNumber"]))]
        for bios in abfrage("SELECT Manufacturer, SMBIOSBIOSVersion, ReleaseDate FROM Win32_BIOS"):
            felder += [("bios_hersteller", wert(bios["Manufacturer"])),
                       ("bios_version", wert(bios["SMBIOSBIOSVersion"])), ("bios_datum", datum(bios["ReleaseDate"]))]
        geraete.append((" ".join(filter(None, (hersteller, modell))) or t("hw.name.mainboard"),
                        felder_ohne_leere(felder)))
    return geraete


def arbeitsspeicher():
    geraete, verloetet = [], {}
    for r in abfrage("SELECT Manufacturer, PartNumber, SerialNumber, BankLabel, DeviceLocator, Capacity, Speed, "
                     "ConfiguredClockSpeed, SMBIOSMemoryType, FormFactor FROM Win32_PhysicalMemory"):
        teil = wert(r["PartNumber"])
        hersteller = herstellername = wert(r["Manufacturer"])
        if not hersteller and teil:
            herstellername = next((name for muster, name in RAM_TEILENUMMER if re.match(muster, teil)), None)
            hersteller = t("hw.wert.laut_teilenummer", hersteller=herstellername) if herstellername else None
        groesse = zahl(r["Capacity"]) or 0
        typ = RAM_TYPEN.get(zahl(r["SMBIOSMemoryType"]))
        eingestellt, maximal = zahl(r["ConfiguredClockSpeed"]), zahl(r["Speed"])
        name = " ".join(filter(None, (herstellername, teil)))
        if typ and typ.startswith("LP"):         # LPDDR ist immer verlötet und kommt je Speicherkanal -> zusammenfassen
            gruppe = verloetet.setdefault(name or t("hw.name.arbeitsspeicher"), {
                "hersteller": hersteller, "teilenummer": teil, "groesse": 0, "typ": typ,
                "takt": f"{eingestellt} MT/s" if eingestellt else None, "bauform": t("hw.wert.verloetet"),
                "kanaele": 0})
            gruppe["groesse"] += groesse
            gruppe["kanaele"] += 1
            continue
        geraete.append((name or t("hw.name.speicherriegel"), felder_ohne_leere([
            ("hersteller", hersteller),
            ("teilenummer", teil),
            ("groesse", f"{groesse // 1024 ** 3} GB" if groesse else None),
            ("typ", typ),
            ("bauform", anzeige(RAM_BAUFORMEN.get(zahl(r["FormFactor"])))),
            ("takt", f"{eingestellt} MT/s" if eingestellt else None),
            ("takt_laut_riegel", f"{maximal} MT/s" if maximal and maximal != eingestellt else None),
            ("steckplatz", " / ".join(filter(None, (wert(r["BankLabel"]), wert(r["DeviceLocator"]))))),
            ("seriennummer", wert(r["SerialNumber"])),
        ])))
    for name, gruppe in verloetet.items():
        gruppe["groesse"] = f"{gruppe['groesse'] // 1024 ** 3} GB" if gruppe["groesse"] else None
        gruppe["kanaele"] = str(gruppe["kanaele"])
        geraete.insert(0, (name, felder_ohne_leere(list(gruppe.items()))))
    return geraete


def laufwerke():
    geraete = []
    for d in sorted(abfrage("SELECT DeviceId, FriendlyName, SerialNumber, FirmwareVersion, Size, BusType, MediaType "
                            "FROM MSFT_PhysicalDisk", scope=r"root\Microsoft\Windows\Storage"),
                    key=lambda d: zahl(d["DeviceId"]) or 0):
        groesse = zahl(d["Size"])
        geraete.append((wert(d["FriendlyName"]) or t("hw.name.laufwerk"), felder_ohne_leere([
            ("art", anzeige(MEDIEN_TYPEN.get(zahl(d["MediaType"])))),
            ("anschluss", anzeige(BUS_TYPEN.get(zahl(d["BusType"])))),
            ("groesse", None if not groesse else f"{num(groesse / 1e12, 1)} TB" if groesse >= 1e12
             else f"{groesse / 1e9:.0f} GB"),
            ("seriennummer", (wert(d["SerialNumber"]) or "").rstrip(".") or None),
            ("firmware", wert(d["FirmwareVersion"])),
            ("datentraeger_nr", d["DeviceId"]),
        ])))
    return geraete


def netzwerk():
    # Art (LAN, WLAN, …) steht nur in der neueren Klasse MSFT_NetAdapter – Win32_NetworkAdapter meldet auch WLAN
    # als „Ethernet“. Zugeordnet wird über die Gerätekennung.
    arten = {(a["PnPDeviceID"] or "").upper(): anzeige(NETZ_ARTEN.get(zahl(a["NdisPhysicalMedium"])))
             for a in abfrage("SELECT PnPDeviceID, NdisPhysicalMedium FROM MSFT_NetAdapter",
                              scope=r"root\StandardCimv2")}
    geraete = []
    for n in abfrage("SELECT Name, PNPDeviceID, MACAddress FROM Win32_NetworkAdapter WHERE PhysicalAdapter = TRUE"):
        pnp = n["PNPDeviceID"] or ""
        if not re.match(r"(PCI|USB)\\", pnp, re.I):
            continue                             # virtuelle Adapter (VPN, Hyper-V, …) weglassen
        geraete.append((wert(n["Name"]) or t("hw.name.netzwerkadapter"), felder_ohne_leere(
            [("art", arten.get(pnp.upper()))] + ids_felder(pnp) + [("mac_adresse", wert(n["MACAddress"]))])))
    return geraete


def audio():
    geraete = []
    for s in abfrage("SELECT Name, PNPDeviceID FROM Win32_SoundDevice"):
        pnp = s["PNPDeviceID"] or ""
        # INTELAUDIO\FUNC_: Codec hinter Intel Smart Sound (Laptops) – die übrigen INTELAUDIO-Einträge sind nur
        # Anschlüsse dieses Controllers (Mikrofon, Bluetooth, USB)
        if not re.match(r"(PCI|HDAUDIO|INTELAUDIO\\FUNC_)", pnp, re.I):
            continue                             # USB-Audio steht bei den USB-Geräten, virtuelle fehlen ganz
        name = wert(s["Name"]) or t("hw.name.audiogeraet")
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
        name = (namen[0] if namen else f"{t('hw.name.usb_geraet')} ({hersteller})" if hersteller
                else t("hw.name.usb_geraet"))
        geraete.append((name, felder_ohne_leere([
            ("hersteller_id", mit_namen(vid, USB_HERSTELLER) if vid in USB_HERSTELLER
             else f"{vid} ({hersteller})" if hersteller else vid),
            ("produkt_id", pid),
            ("seriennummer", seriennr),
            ("hardware_id", f"USB\\VID_{vid}&PID_{pid}"),
        ])))
    return sorted(geraete, key=lambda g: g[0].lower())


# Bereich-ID (Name: hw.bereich.<ID> in i18n.json) -> Funktion, die ihn liest
BEREICHE = (("prozessor", prozessoren), ("grafikkarte", grafikkarten), ("mainboard", mainboard),
            ("arbeitsspeicher", arbeitsspeicher), ("laufwerke", laufwerke), ("netzwerk", netzwerk),
            ("audio", audio), ("usb_geraete", usb_geraete))


def lesen():
    """Alle Bereiche: [(Bereich-ID, [(Gerätename, [(Feld-ID, Wert), …]), …]), …] – leere Bereiche fehlen."""
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
    bloecke = ["\n".join([name] + [f"  {feldname(feld)}: {w}" for feld, w in felder]) for name, felder in geraete]
    return f"=== {bereichsname(bereich)} ===\n" + "\n\n".join(bloecke)


def alles_als_text(daten):
    """Alle Bereiche, mit Computername und Datum oben drüber."""
    kopf = t("hw.text.kopf", pc=platform.node(), datum=f"{date.today():%d.%m.%Y}")
    return kopf + "\n\n" + "\n\n\n".join(als_text(b, g) for b, g in daten) + "\n"


def modellnamen(geraete):
    """Die Gerätenamen eines Bereichs – gleiche Geräte zusammengefasst („2× G.Skill …“)."""
    namen = Counter(name for name, _ in geraete)
    return [f"{n}× {name}" if n > 1 else name for name, n in namen.items()]


def modellnamen_als_text(daten):
    """Nur die Modellnamen: der Bereich, darunter je Gerät eine Zeile mit Tab davor."""
    zeilen = []
    for bereich, geraete in daten:
        zeilen += [bereichsname(bereich)] + [f"\t{name}" for name in modellnamen(geraete)]
    return "\n".join(zeilen) + "\n"


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    for bereich, geraete in lesen():
        print(f"\n=== {bereichsname(bereich)} ===")
        for name, felder in geraete:
            print(f"  {name}")
            for feld, w in felder:
                print(f"      {feldname(feld):20} {w}")
