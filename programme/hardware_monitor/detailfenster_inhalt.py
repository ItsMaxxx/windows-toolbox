"""
Was im Detailfenster des Hardware-Monitors steht – Tab für Tab, eine Zeile pro Wert.

  Wert hinzufügen:  eine Zeile Wert("Name") in die passende Gruppe schreiben
  Wert weglassen:   die Zeile löschen
  Reihenfolge:      so wie hier aufgeschrieben

Die genauen Sensornamen stehen in der Ausgabe von `python hardware_monitor.py --list`
(dort in eckigen Klammern auch das Gerät für Gruppe(...): cpu, gpu, ram, mainboard, laufwerk, netzwerk, akku).

  Gruppe("laufwerk", ...)          gilt für jedes Laufwerk einzeln
  Gruppe("gpu", ..., name="Intel*")    nur Geräte, deren Name passt
  Wert("Fan #*")                   * steht für beliebigen Text – hier: alle Lüfter
  Wert("GPU Core", typ="Takt")     typ nur nötig, wenn es den Namen mehrfach gibt
  Wert("Package", text="CPU gesamt")   eigene Beschriftung (in jeder Sprache gleich – oder eine ID aus i18n.json)
  Wert("CPU Core #*", ohne="*Distance*")   Platzhalter, aber ohne die Namen, die hierzu passen
  Abschnitt("Lüfter", Wert(...), Wert(...))   einklappbarer Unterpunkt in einer Gruppe
  Abschnitt(..., eine_zeile=True)  gleichnamige Werte in einer Zeile (Fan #1: Drehzahl, dahinter % als Balken)
  Hardwaredaten()                  statt Gruppen: feste Daten wie Hersteller- und Produkt-IDs

Die Namen unterscheiden sich je nach Hardware (AMD: „Core (Tctl/Tdie)“, Intel: „CPU Package“). Was es auf einem PC
nicht gibt, wird einfach nicht angezeigt – daher stehen hier die Namen für beide nebeneinander. Tabs, deren Geräte
der PC gar nicht hat (z. B. Mainboard-Sensoren am Laptop, Akku am Desktop), werden ausgeblendet.

Beschriftungen – Tab-Titel, Abschnitt, titel=, text= – und die Erklärungen unten sind IDs aus i18n.json (z. B.
"tab.gpu"); ihr Text steht dort für jede Sprache. Ein eigener Text ohne ID geht auch, er steht dann in jeder Sprache
gleich da.

Gespeichert? Fenster schließen und wieder öffnen – die Änderungen sind sofort da.
"""

from detailfenster import Abschnitt, AlleSensoren, Gruppe, Hardwaredaten, Tab, Wert  # noqa: F401 (AlleSensoren siehe unten)

# Die Lüfter – eine Zeile je Lüfter: Drehzahl, dahinter die Ansteuerung als Balken. Stehen jeweils in zwei Tabs.
# Mainboards benennen ihre Anschlüsse unterschiedlich („Fan #1“, „CPU Fan“, „Chassis Fan #2“, „Pump“ …).
LUEFTER = Abschnitt("abschnitt.luefter",
                    Wert("*Fan*", typ="Lüfter"),
                    Wert("*Pump*", typ="Lüfter"),
                    Wert("*Fan*", typ="Lüftersteuerung"),
                    Wert("*Pump*", typ="Lüftersteuerung"),
                    eine_zeile=True)
GPU_LUEFTER = Abschnitt("abschnitt.luefter",
                        Wert("GPU Fan*", typ="Lüfter"),
                        Wert("GPU Fan*", typ="Lüftersteuerung"),
                        eine_zeile=True)

FENSTER = [
    Tab("tab.temperaturen",
        Gruppe("cpu",
               Wert("Core (Tctl/Tdie)"),                # AMD
               Wert("CCD* (Tdie)"),
               Wert("CPU Package", typ="Temperatur"),   # Intel
               Wert("Core Max", typ="Temperatur")),
        Gruppe("gpu",
               Wert("GPU Core", typ="Temperatur"),
               Wert("GPU Hot Spot"),
               Wert("GPU Memory Junction"),
               GPU_LUEFTER),
        Gruppe("mainboard",
               LUEFTER)),

    Tab("tab.cpu",
        Gruppe("cpu",
               Wert("CPU Total"),
               Wert("CPU Core Max"),
               Wert("Package", typ="Leistung"),         # AMD
               Wert("CPU Package", typ="Leistung"),     # Intel
               Wert("CPU Cores", typ="Leistung"),
               Wert("Cores (Average)"),
               Wert("Cores (Average Effective)"),
               Wert("CPU Core #*", typ="Takt"),         # Intel: Takt je Kern (ohne Durchschnitt)
               Wert("Core (Tctl/Tdie)"),
               Wert("CCD* (Tdie)"),
               Wert("CPU Package", typ="Temperatur"),
               Wert("Core Max", typ="Temperatur"),
               Wert("CPU Core #*", typ="Temperatur", ohne="*Distance to TjMax"),
               Wert("Core (SVI2 TFN)"),
               Wert("SoC (SVI2 TFN)"),
               Wert("CPU Core", typ="Spannung"),
               Wert("Bus Speed"))),

    Tab("tab.gpu",
        Gruppe("gpu",
               Wert("GPU Core", typ="Temperatur"),
               Wert("GPU Hot Spot"),
               Wert("GPU Core", typ="Auslastung", text="wert.gpu_core_auslastung"),
               Wert("GPU Memory Controller"),
               Wert("GPU Video Engine"),
               Wert("GPU Bus"),
               Wert("GPU Power", typ="Auslastung"),
               Wert("GPU Board Power"),
               Wert("GPU Package"),
               Wert("GPU Core", typ="Takt", text="wert.gpu_core_takt"),
               Wert("GPU Memory", typ="Takt", text="wert.gpu_memory_takt"),
               Wert("GPU Core Voltage"),
               Wert("GPU Memory Used"),
               Wert("GPU Memory Free"),
               Wert("GPU Memory Total"),
               Wert("GPU PCIe Rx"),
               Wert("GPU PCIe Tx"),
               GPU_LUEFTER),
        Gruppe("gpu",                                   # Intel-Grafik: liefert nur Leistung und Windows-Werte
               Wert("GPU Power", typ="Leistung"),
               Wert("D3D 3D"),
               Wert("D3D Dedicated Memory Used"),
               Wert("D3D Shared Memory Used"),
               Wert("D3D Shared Memory Free"),
               Wert("D3D Shared Memory Total"),
               name="Intel*")),

    Tab("tab.ram",
        Gruppe("ram",
               Wert("Memory", typ="Auslastung", text="wert.auslastung"),
               Wert("Memory Used"),
               Wert("Memory Available"),
               name="Total Memory", titel="titel.arbeitsspeicher"),
        Gruppe("ram",
               Wert("Memory", typ="Auslastung", text="wert.auslastung"),
               Wert("Memory Used"),
               Wert("Memory Available"),
               name="Virtual Memory", titel="titel.mit_auslagerung"),
        Gruppe("ram",                                   # jeder Riegel einzeln
               Wert("DIMM #*"),
               Wert("Capacity"))),

    Tab("tab.mainboard",
        Gruppe("mainboard",
               Wert("CPU", typ="Temperatur"),
               Wert("Motherboard"),
               Wert("VRM"),
               Wert("Auxiliary*"),
               Wert("Vcore"),
               Wert("+12V"),
               Wert("+5V"),
               Wert("+3.3V"),
               Wert("+3V Standby"),
               Wert("+1.8V"),
               Wert("Chipset 1.05V"),
               LUEFTER)),

    Tab("tab.laufwerke",
        Gruppe("laufwerk",                              # jedes Laufwerk einzeln
               Wert("Composite Temperature"),
               Wert("Temperature"),
               Wert("Temperature #*"),
               Wert("Warning Temperature"),
               Wert("Critical Temperature"),
               Wert("Used Space"),
               Wert("Free Space"),
               Wert("Total Space"),
               Wert("Read Rate"),
               Wert("Write Rate"),
               Wert("Total Activity"),
               Wert("Life"),
               Wert("Percentage Used"),
               Wert("Available Spare"),
               Wert("Available Spare Threshold"),
               Wert("Data Read"),
               Wert("Data Written"),
               Wert("Power On Count"),
               Wert("Power On Hours"))),

    Tab("tab.netzwerk",
        Gruppe("netzwerk",
               Wert("Download Speed"),
               Wert("Upload Speed"),
               Wert("Network Utilization"),
               Wert("Data Downloaded"),
               Wert("Data Uploaded"))),

    Tab("tab.akku",
        Gruppe("akku",
               Wert("Charge Level"),
               Wert("Remaining Capacity"),
               Wert("Remaining Time*"),
               Wert("*Rate", typ="Leistung"),              # Discharge Rate bzw. Charge Rate
               Wert("*Current"),
               Wert("Voltage"),
               Wert("Fully-Charged Capacity"),
               Wert("Designed Capacity"),
               Wert("Degradation Level"),
               Wert("Cycle Count"))),

    # Feste Daten statt Messwerte: Hersteller, Modell, IDs, Seriennummern (siehe hardwaredaten.py)
    Tab("tab.hardwaredaten", Hardwaredaten()),

    # Alles, was LibreHardwareMonitor findet, zum Nachschlagen von Sensornamen – bei Bedarf wieder einkommentieren:
    # Tab("tab.alles", AlleSensoren()),
]


# ---------- Erklärungen in der Fußzeile ----------
# (Sensortyp, Muster, Text-ID) – das Muster muss auf den ganzen Sensornamen passen (regulärer Ausdruck).
# Die Texte stehen in i18n.json unter der ID ("erklaerung.…") – dort für jede Sprache.
# {0} im Text wird durch die erste Klammergruppe im Muster ersetzt (z. B. die Nummer bei "CCD1").
# Wichtig ist der Sensortyp: "GPU Core" ist z. B. sowohl eine Temperatur als auch eine Auslastung und ein Takt.
ERKLAERUNGEN = [
    # --- Temperaturen: CPU ---
    ("Temperature", r"Core \(Tctl/Tdie\)", "erklaerung.temp.tctl_tdie"),
    ("Temperature", r"Core \(Tctl\)", "erklaerung.temp.tctl"),
    ("Temperature", r"Core \(Tdie\)", "erklaerung.temp.tdie"),
    ("Temperature", r"CCD(\d+) \(Tdie\)", "erklaerung.temp.ccd"),
    ("Temperature", r"CCDs Max \(Tdie\)", "erklaerung.temp.ccds_max"),
    ("Temperature", r"CCDs Average \(Tdie\)", "erklaerung.temp.ccds_average"),
    ("Temperature", r"SoC", "erklaerung.temp.soc"),
    ("Temperature", r"CPU Package", "erklaerung.temp.cpu_package"),
    ("Temperature", r"Core Max", "erklaerung.temp.core_max"),
    ("Temperature", r"Core Average", "erklaerung.temp.core_average"),
    ("Temperature", r"CPU Core #(\d+)", "erklaerung.temp.cpu_core"),
    ("Temperature", r"(?:.* )?Distance to TjMax", "erklaerung.temp.distance_tjmax"),
    # --- Temperaturen: GPU ---
    ("Temperature", r"GPU Core", "erklaerung.temp.gpu_core"),
    ("Temperature", r"GPU Hot Spot", "erklaerung.temp.gpu_hot_spot"),
    ("Temperature", r"GPU Memory Junction", "erklaerung.temp.gpu_memory_junction"),
    ("Temperature", r"GPU Memory", "erklaerung.temp.gpu_memory"),
    ("Temperature", r"GPU VR .+", "erklaerung.temp.gpu_vr"),
    ("Temperature", r"GPU Liquid", "erklaerung.temp.gpu_liquid"),
    # --- Temperaturen: Mainboard / Laufwerke ---
    ("Temperature", r"CPU", "erklaerung.temp.mainboard_cpu"),
    ("Temperature", r"System|Motherboard", "erklaerung.temp.system"),
    ("Temperature", r"PCH|Chipset", "erklaerung.temp.chipsatz"),
    ("Temperature", r"VRM.*", "erklaerung.temp.vrm"),
    ("Temperature", r"Temperature #(\d+)", "erklaerung.temp.unbenannt"),
    ("Temperature", r"Temperature( \d+)?", "erklaerung.temp.laufwerk"),
    ("Temperature", r"Composite Temperature", "erklaerung.temp.composite"),
    ("Temperature", r"Warning Temperature", "erklaerung.temp.warning"),
    ("Temperature", r"Critical Temperature", "erklaerung.temp.critical"),
    # --- Auslastung ---
    ("Load", r"CPU Total", "erklaerung.last.cpu_total"),
    ("Load", r"CPU Core Max", "erklaerung.last.cpu_core_max"),
    ("Load", r"CPU Core #(\d+)(?: Thread #(\d+))?", "erklaerung.last.cpu_core"),
    ("Load", r"GPU Core", "erklaerung.last.gpu_core"),
    ("Load", r"GPU Memory Controller", "erklaerung.last.gpu_memory_controller"),
    ("Load", r"GPU Video Engine", "erklaerung.last.gpu_video_engine"),
    ("Load", r"GPU Bus", "erklaerung.last.gpu_bus"),
    ("Load", r"GPU Memory", "erklaerung.last.gpu_memory"),
    ("Load", r"D3D .+", "erklaerung.last.d3d"),
    ("Load", r"Memory", "erklaerung.last.memory"),
    ("Load", r"Virtual Memory", "erklaerung.last.virtual_memory"),
    ("Load", r"Used Space", "erklaerung.last.used_space"),
    ("Load", r"(Total|Read|Write) Activity", "erklaerung.last.activity"),
    ("Load", r"Network Utilization", "erklaerung.last.network"),
    # --- Takt ---
    ("Clock", r"(?:CPU )?Core #(\d+)", "erklaerung.takt.cpu_core"),
    ("Clock", r"Bus Speed", "erklaerung.takt.bus"),
    ("Clock", r"Cores \(Average.*\)", "erklaerung.takt.cores_average"),
    ("Clock", r"GPU Core", "erklaerung.takt.gpu_core"),
    ("Clock", r"GPU Memory", "erklaerung.takt.gpu_memory"),
    ("Clock", r"GPU Shader", "erklaerung.takt.gpu_shader"),
    # --- Leistung ---
    ("Power", r"(CPU )?Package", "erklaerung.leistung.package"),
    ("Power", r"Core #(\d+) \(SMU\)", "erklaerung.leistung.core_smu"),
    ("Power", r"(?:CPU )?Cores", "erklaerung.leistung.cores"),
    ("Power", r"SoC", "erklaerung.leistung.soc"),
    ("Power", r"CPU Memory", "erklaerung.leistung.cpu_memory"),
    ("Power", r"CPU Platform", "erklaerung.leistung.platform"),
    ("Power", r"GPU (Package|Power)", "erklaerung.leistung.gpu"),
    ("Power", r"Discharge Rate", "erklaerung.leistung.entladen"),
    ("Power", r"Charge Rate", "erklaerung.leistung.laden"),
    # --- Spannung ---
    ("Voltage", r"Core \(SVI\d? ?TFN\)", "erklaerung.spannung.core_svi"),
    ("Voltage", r"SoC \(SVI\d? ?TFN\)", "erklaerung.spannung.soc_svi"),
    ("Voltage", r"Vcore|CPU VCore", "erklaerung.spannung.vcore"),
    ("Voltage", r"CPU Core", "erklaerung.spannung.cpu_core"),
    ("Voltage", r"CPU Core #(\d+)", "erklaerung.spannung.cpu_core_nr"),
    ("Voltage", r"\+?(12|5|3[.,]3)V", "erklaerung.spannung.netzteil"),
    ("Voltage", r"VBat|Vbat|CMOS Battery|Battery", "erklaerung.spannung.cmos"),
    ("Voltage", r"GPU Core", "erklaerung.spannung.gpu_core"),
    ("Voltage", r"Voltage", "erklaerung.spannung.akku"),
    # --- Akku ---
    ("Current", r"Discharge Current", "erklaerung.akku.entladestrom"),
    ("Current", r"Charge Current", "erklaerung.akku.ladestrom"),
    ("Energy", r"Remaining Capacity", "erklaerung.akku.rest"),
    ("Energy", r"Fully-Charged Capacity", "erklaerung.akku.voll"),
    ("Energy", r"Designed Capacity", "erklaerung.akku.neu"),
    ("TimeSpan", r"Remaining Time.*", "erklaerung.akku.restzeit"),
    # --- Lüfter ---
    ("Fan", r"GPU Fan( \d+)?", "erklaerung.luefter.gpu"),
    ("Fan", r"Fan #(\d+)", "erklaerung.luefter.mainboard"),
    ("Fan", r"Pump.*", "erklaerung.luefter.pumpe"),
    ("Control", r"GPU Fan( \d+)?", "erklaerung.luefter.gpu_steuerung"),
    ("Control", r"Fan( Control)? #(\d+)", "erklaerung.luefter.mainboard_steuerung"),
    # --- Speicher / Daten ---
    ("Data", r"Memory Used", "erklaerung.daten.memory_used"),
    ("Data", r"Memory Available", "erklaerung.daten.memory_available"),
    ("Data", r"Virtual Memory Used", "erklaerung.daten.virtual_used"),
    ("Data", r"Virtual Memory Available", "erklaerung.daten.virtual_available"),
    ("Data", r"Data Read", "erklaerung.daten.gelesen"),
    ("Data", r"Data Written", "erklaerung.daten.geschrieben"),
    ("Data", r"Data Uploaded", "erklaerung.daten.hochgeladen"),
    ("Data", r"Data Downloaded", "erklaerung.daten.heruntergeladen"),
    ("SmallData", r"GPU Memory Used", "erklaerung.daten.gpu_used"),
    ("SmallData", r"GPU Memory Free", "erklaerung.daten.gpu_free"),
    ("SmallData", r"GPU Memory Total", "erklaerung.daten.gpu_total"),
    ("SmallData", r"D3D Dedicated Memory Used", "erklaerung.daten.d3d_dedicated"),
    ("SmallData", r"D3D Shared Memory Used", "erklaerung.daten.d3d_shared_used"),
    ("SmallData", r"D3D Shared Memory Free", "erklaerung.daten.d3d_shared_free"),
    ("SmallData", r"D3D Shared Memory Total", "erklaerung.daten.d3d_shared_total"),
    # --- Durchsatz ---
    ("Throughput", r"Read Rate", "erklaerung.durchsatz.lesen"),
    ("Throughput", r"Write Rate", "erklaerung.durchsatz.schreiben"),
    ("Throughput", r"Upload Speed", "erklaerung.durchsatz.upload"),
    ("Throughput", r"Download Speed", "erklaerung.durchsatz.download"),
    ("Throughput", r"GPU PCIe Rx", "erklaerung.durchsatz.pcie_rx"),
    ("Throughput", r"GPU PCIe Tx", "erklaerung.durchsatz.pcie_tx"),
    # --- Zustand ---
    ("Level", r"Available Spare", "erklaerung.zustand.spare"),
    ("Level", r"Available Spare Threshold", "erklaerung.zustand.spare_grenze"),
    ("Level", r"Life", "erklaerung.zustand.life"),
    ("Level", r"Percentage Used", "erklaerung.zustand.used"),
    ("Level", r"Charge Level", "erklaerung.zustand.ladestand"),
    ("Level", r"Degradation Level", "erklaerung.zustand.verschleiss"),
    # --- Zähler ---
    ("Factor", r"Power On Count", "erklaerung.zaehler.einschaltungen"),
    ("Factor", r"Power On Hours", "erklaerung.zaehler.stunden"),
]

TYP_ERKLAERUNGEN = {   # Rückfall, wenn kein genauerer Eintrag oben passt
    "Temperature": "erklaerung.typ.Temperature",
    "Load": "erklaerung.typ.Load",
    "Clock": "erklaerung.typ.Clock",
    "Power": "erklaerung.typ.Power",
    "Voltage": "erklaerung.typ.Voltage",
    "Current": "erklaerung.typ.Current",
    "Energy": "erklaerung.typ.Energy",
    "TimeSpan": "erklaerung.typ.TimeSpan",
    "Fan": "erklaerung.typ.Fan",
    "Control": "erklaerung.typ.Control",
    "Data": "erklaerung.typ.Data",
    "SmallData": "erklaerung.typ.SmallData",
    "Throughput": "erklaerung.typ.Throughput",
    "Level": "erklaerung.typ.Level",
}
