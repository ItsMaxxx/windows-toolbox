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
  Wert("Package", text="CPU gesamt")   eigene Beschriftung
  Wert("CPU Core #*", ohne="*Distance*")   Platzhalter, aber ohne die Namen, die hierzu passen
  Abschnitt("Lüfter", Wert(...), Wert(...))   einklappbarer Unterpunkt in einer Gruppe
  Abschnitt(..., eine_zeile=True)  gleichnamige Werte in einer Zeile (Fan #1: Drehzahl, dahinter % als Balken)
  Hardwaredaten()                  statt Gruppen: feste Daten wie Hersteller- und Produkt-IDs

Die Namen unterscheiden sich je nach Hardware (AMD: „Core (Tctl/Tdie)“, Intel: „CPU Package“). Was es auf einem PC
nicht gibt, wird einfach nicht angezeigt – daher stehen hier die Namen für beide nebeneinander. Tabs, deren Geräte
der PC gar nicht hat (z. B. Mainboard-Sensoren am Laptop, Akku am Desktop), werden ausgeblendet.

Gespeichert? Fenster schließen und wieder öffnen – die Änderungen sind sofort da.
"""

from detailfenster import Abschnitt, AlleSensoren, Gruppe, Hardwaredaten, Tab, Wert  # noqa: F401 (AlleSensoren siehe unten)

# Die Lüfter – eine Zeile je Lüfter: Drehzahl, dahinter die Ansteuerung als Balken. Stehen jeweils in zwei Tabs.
# Mainboards benennen ihre Anschlüsse unterschiedlich („Fan #1“, „CPU Fan“, „Chassis Fan #2“, „Pump“ …).
LUEFTER = Abschnitt("Lüfter",
                    Wert("*Fan*", typ="Lüfter"),
                    Wert("*Pump*", typ="Lüfter"),
                    Wert("*Fan*", typ="Lüftersteuerung"),
                    Wert("*Pump*", typ="Lüftersteuerung"),
                    eine_zeile=True)
GPU_LUEFTER = Abschnitt("Lüfter",
                        Wert("GPU Fan*", typ="Lüfter"),
                        Wert("GPU Fan*", typ="Lüftersteuerung"),
                        eine_zeile=True)

FENSTER = [
    Tab("Temperaturen",
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

    Tab("CPU",
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

    Tab("GPU",
        Gruppe("gpu",
               Wert("GPU Core", typ="Temperatur"),
               Wert("GPU Hot Spot"),
               Wert("GPU Core", typ="Auslastung", text="GPU Core Auslastung"),
               Wert("GPU Memory Controller"),
               Wert("GPU Video Engine"),
               Wert("GPU Bus"),
               Wert("GPU Power", typ="Auslastung"),
               Wert("GPU Board Power"),
               Wert("GPU Package"),
               Wert("GPU Core", typ="Takt", text="GPU Core Takt"),
               Wert("GPU Memory", typ="Takt", text="GPU Memory Takt"),
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

    Tab("RAM",
        Gruppe("ram",
               Wert("Memory", typ="Auslastung", text="Auslastung"),
               Wert("Memory Used"),
               Wert("Memory Available"),
               name="Total Memory", titel="Arbeitsspeicher"),
        Gruppe("ram",
               Wert("Memory", typ="Auslastung", text="Auslastung"),
               Wert("Memory Used"),
               Wert("Memory Available"),
               name="Virtual Memory", titel="Inklusive Auslagerungsdatei"),
        Gruppe("ram",                                   # jeder Riegel einzeln
               Wert("DIMM #*"),
               Wert("Capacity"))),

    Tab("Mainboard",
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

    Tab("Laufwerke",
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

    Tab("Netzwerk",
        Gruppe("netzwerk",
               Wert("Download Speed"),
               Wert("Upload Speed"),
               Wert("Network Utilization"),
               Wert("Data Downloaded"),
               Wert("Data Uploaded"))),

    Tab("Akku",
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
    Tab("Hardwaredaten", Hardwaredaten()),

    # Alles, was LibreHardwareMonitor findet, zum Nachschlagen von Sensornamen – bei Bedarf wieder einkommentieren:
    # Tab("Alles", AlleSensoren()),
]


# ---------- Erklärungen in der Fußzeile ----------
# (Sensortyp, Muster, Text) – das Muster muss auf den ganzen Sensornamen passen (regulärer Ausdruck).
# {0} wird durch die erste Klammergruppe im Muster ersetzt (z. B. die Nummer bei "CCD1").
# Wichtig ist der Sensortyp: "GPU Core" ist z. B. sowohl eine Temperatur als auch eine Auslastung und ein Takt.
ERKLAERUNGEN = [
    # --- Temperaturen: CPU ---
    ("Temperature", r"Core \(Tctl/Tdie\)", "Die Steuertemperatur des Prozessors, nach der Mainboard und Lüfter "
                                           "regeln – der wichtigste CPU-Wert."),
    ("Temperature", r"Core \(Tctl\)", "Steuertemperatur für die Lüfterregelung; bei einigen Ryzen-Modellen absichtlich "
                                      "um einen festen Wert höher als die echte Temperatur."),
    ("Temperature", r"Core \(Tdie\)", "Die tatsächliche Temperatur des Prozessor-Chips, ohne den Lüfter-Aufschlag von Tctl."),
    ("Temperature", r"CCD(\d+) \(Tdie\)", "Temperatur von Kern-Chip Nr. {0} (Core Complex Die) – hier sitzen die "
                                          "eigentlichen CPU-Kerne."),
    ("Temperature", r"CCDs Max \(Tdie\)", "Der höchste Wert aller Kern-Chips (CCDs)."),
    ("Temperature", r"CCDs Average \(Tdie\)", "Der Durchschnitt aller Kern-Chips (CCDs)."),
    ("Temperature", r"SoC", "Temperatur des I/O-Teils der CPU mit Speicher-Controller und PCIe-Anbindung."),
    ("Temperature", r"CPU Package", "Gesamttemperatur des Prozessors, meist so hoch wie der heißeste Kern – der "
                                    "wichtigste Wert bei Intel."),
    ("Temperature", r"Core Max", "Die Temperatur des aktuell heißesten CPU-Kerns."),
    ("Temperature", r"Core Average", "Der Durchschnitt über alle CPU-Kerne."),
    ("Temperature", r"CPU Core #(\d+)", "Temperatur von CPU-Kern Nr. {0}."),
    ("Temperature", r"(?:.* )?Distance to TjMax", "Abstand bis zu der Temperatur, ab der sich die CPU drosselt – hier ist ein "
                                          "höherer Wert besser."),
    # --- Temperaturen: GPU ---
    ("Temperature", r"GPU Core", "Die durchschnittliche Temperatur des Grafikchips – der klassische GPU-Wert."),
    ("Temperature", r"GPU Hot Spot", "Die heißeste Stelle auf dem Grafikchip; liegt normalerweise 10–20 °C über "
                                     "GPU Core, deutlich mehr kann auf schlechten Kühlerkontakt hindeuten."),
    ("Temperature", r"GPU Memory Junction", "Die heißeste Stelle im Grafikspeicher (VRAM); unter Last sind hier Werte "
                                            "bis knapp 100 °C noch normal."),
    ("Temperature", r"GPU Memory", "Temperatur des Grafikspeichers (VRAM)."),
    ("Temperature", r"GPU VR .+", "Temperatur eines Spannungswandlers, der Grafikchip oder Speicher mit Strom versorgt."),
    ("Temperature", r"GPU Liquid", "Temperatur der Kühlflüssigkeit bei wassergekühlten Grafikkarten."),
    # --- Temperaturen: Mainboard / Laufwerke ---
    ("Temperature", r"CPU", "CPU-Temperatur, gemessen vom Sensor auf dem Mainboard – meist weniger genau als Tctl/Tdie."),
    ("Temperature", r"System|Motherboard", "Temperatur auf dem Mainboard, ungefähr die Lufttemperatur im Gehäuse."),
    ("Temperature", r"PCH|Chipset", "Temperatur des Chipsatzes auf dem Mainboard."),
    ("Temperature", r"VRM.*", "Temperatur der Spannungswandler, die die CPU mit Strom versorgen."),
    ("Temperature", r"Temperature #(\d+)", "Unbenannter Temperaturfühler Nr. {0}; was er misst, hängt vom Gerät ab "
                                           "(bei SSDs meist Controller bzw. Speicherchips)."),
    ("Temperature", r"Temperature( \d+)?", "Temperatur des Laufwerks (Controller oder Speicherchips)."),
    ("Temperature", r"Composite Temperature", "Zusammengefasste Temperatur der SSD, nach der sie sich ggf. drosselt."),
    ("Temperature", r"Warning Temperature", "Grenzwert der SSD: Ab dieser Temperatur warnt sie und beginnt sich zu "
                                            "drosseln – kein Messwert."),
    ("Temperature", r"Critical Temperature", "Grenzwert der SSD: Ab dieser Temperatur drosselt sie sich stark, um "
                                             "Schäden zu vermeiden – kein Messwert."),
    # --- Auslastung ---
    ("Load", r"CPU Total", "Gesamtauslastung aller CPU-Kerne."),
    ("Load", r"CPU Core Max", "Auslastung des gerade am stärksten belasteten Kerns."),
    ("Load", r"CPU Core #(\d+)(?: Thread #(\d+))?", "Auslastung von CPU-Kern Nr. {0}."),
    ("Load", r"GPU Core", "Wie stark die Recheneinheiten der Grafikkarte gerade arbeiten."),
    ("Load", r"GPU Memory Controller", "Auslastung der Anbindung zwischen Grafikchip und Grafikspeicher."),
    ("Load", r"GPU Video Engine", "Auslastung der Videoeinheit (Abspielen und Aufnehmen von Videos)."),
    ("Load", r"GPU Bus", "Auslastung der PCIe-Verbindung zwischen Grafikkarte und Mainboard."),
    ("Load", r"GPU Memory", "Anteil des belegten Grafikspeichers (VRAM)."),
    ("Load", r"D3D .+", "Auslastung laut Windows für diesen Teil der Grafikkarte (z. B. 3D, Kopieren, Video)."),
    ("Load", r"Memory", "Anteil des belegten Arbeitsspeichers."),
    ("Load", r"Virtual Memory", "Anteil des belegten Arbeitsspeichers inklusive Auslagerungsdatei."),
    ("Load", r"Used Space", "Wie voll das Laufwerk ist."),
    ("Load", r"(Total|Read|Write) Activity", "Wie viel Prozent der Zeit das Laufwerk gerade beschäftigt ist."),
    ("Load", r"Network Utilization", "Auslastung der Netzwerkverbindung im Verhältnis zu ihrer Maximalgeschwindigkeit."),
    # --- Takt ---
    ("Clock", r"(?:CPU )?Core #(\d+)", "Aktueller Takt von CPU-Kern Nr. {0}."),
    ("Clock", r"Bus Speed", "Grundtakt, aus dem sich per Multiplikator der CPU-Takt ergibt (meist rund 100 MHz)."),
    ("Clock", r"Cores \(Average.*\)", "Durchschnittlicher Takt aller CPU-Kerne."),
    ("Clock", r"GPU Core", "Aktueller Takt des Grafikchips."),
    ("Clock", r"GPU Memory", "Aktueller Takt des Grafikspeichers."),
    ("Clock", r"GPU Shader", "Takt der Shader-Einheiten der Grafikkarte."),
    # --- Leistung ---
    ("Power", r"(CPU )?Package", "Gesamter Stromverbrauch des Prozessors."),
    ("Power", r"Core #(\d+) \(SMU\)", "Stromverbrauch von Kern Nr. {0}, gemeldet vom Prozessor selbst."),
    ("Power", r"(?:CPU )?Cores", "Stromverbrauch aller Kerne zusammen."),
    ("Power", r"SoC", "Stromverbrauch des I/O-Teils der CPU."),
    ("Power", r"CPU Memory", "Stromverbrauch des Speicher-Controllers in der CPU."),
    ("Power", r"CPU Platform", "Stromverbrauch des ganzen Geräts laut Prozessor (CPU, Chipsatz, Speicher …) – "
                               "nicht bei jedem Gerät verlässlich."),
    ("Power", r"GPU (Package|Power)", "Gesamter Stromverbrauch der Grafikkarte."),
    ("Power", r"Discharge Rate", "Leistung, die gerade aus dem Akku entnommen wird."),
    ("Power", r"Charge Rate", "Leistung, mit der der Akku gerade geladen wird."),
    # --- Spannung ---
    ("Voltage", r"Core \(SVI\d? ?TFN\)", "Kernspannung der CPU, gemeldet vom Spannungsregler."),
    ("Voltage", r"SoC \(SVI\d? ?TFN\)", "Spannung des I/O-Teils der CPU."),
    ("Voltage", r"Vcore|CPU VCore", "Kernspannung der CPU, gemessen vom Mainboard."),
    ("Voltage", r"CPU Core", "Kernspannung der CPU."),
    ("Voltage", r"CPU Core #(\d+)", "Spannung von CPU-Kern Nr. {0}."),
    ("Voltage", r"\+?(12|5|3[.,]3)V", "Spannung der {0}-Volt-Leitung vom Netzteil; sollte nahe am Sollwert liegen "
                                      "(etwa ±5 %)."),
    ("Voltage", r"VBat|Vbat|CMOS Battery|Battery", "Spannung der Knopfzelle auf dem Mainboard; liegt sie unter etwa "
                                                   "2,8 V, sollte sie bald getauscht werden."),
    ("Voltage", r"GPU Core", "Spannung des Grafikchips."),
    ("Voltage", r"Voltage", "Aktuelle Spannung des Akkus."),
    # --- Akku ---
    ("Current", r"Discharge Current", "Strom, der gerade aus dem Akku fließt."),
    ("Current", r"Charge Current", "Strom, mit dem der Akku gerade geladen wird."),
    ("Energy", r"Remaining Capacity", "Energie, die gerade noch im Akku steckt."),
    ("Energy", r"Fully-Charged Capacity", "Energie, die der Akku heute voll geladen speichert – sinkt mit dem Alter."),
    ("Energy", r"Designed Capacity", "Energie, die der Akku laut Hersteller im Neuzustand speichert."),
    ("TimeSpan", r"Remaining Time.*", "Geschätzte Restlaufzeit bei der aktuellen Leistungsaufnahme."),
    # --- Lüfter ---
    ("Fan", r"GPU Fan( \d+)?", "Drehzahl des Grafikkarten-Lüfters; 0 RPM im Leerlauf ist normal, viele Karten "
                               "stoppen ihre Lüfter dann."),
    ("Fan", r"Fan #(\d+)", "Drehzahl des Lüfteranschlusses Nr. {0} auf dem Mainboard."),
    ("Fan", r"Pump.*", "Drehzahl der Pumpe einer Wasserkühlung."),
    ("Control", r"GPU Fan( \d+)?", "Wie stark der Grafikkarten-Lüfter angesteuert wird (Prozent der Maximaldrehzahl)."),
    ("Control", r"Fan( Control)? #(\d+)", "Wie stark der Lüfteranschluss auf dem Mainboard angesteuert wird."),
    # --- Speicher / Daten ---
    ("Data", r"Memory Used", "Belegter Arbeitsspeicher."),
    ("Data", r"Memory Available", "Noch freier Arbeitsspeicher."),
    ("Data", r"Virtual Memory Used", "Belegter Arbeitsspeicher inklusive Auslagerungsdatei auf der SSD."),
    ("Data", r"Virtual Memory Available", "Noch freier Speicher inklusive Auslagerungsdatei."),
    ("Data", r"Data Read", "Insgesamt von diesem Laufwerk gelesene Datenmenge über seine ganze Lebensdauer."),
    ("Data", r"Data Written", "Insgesamt auf dieses Laufwerk geschriebene Datenmenge über seine ganze Lebensdauer."),
    ("Data", r"Data Uploaded", "Hochgeladene Datenmenge seit dem Verbinden des Adapters."),
    ("Data", r"Data Downloaded", "Heruntergeladene Datenmenge seit dem Verbinden des Adapters."),
    ("SmallData", r"GPU Memory Used", "Belegter Grafikspeicher (VRAM)."),
    ("SmallData", r"GPU Memory Free", "Noch freier Grafikspeicher (VRAM)."),
    ("SmallData", r"GPU Memory Total", "Gesamtgröße des Grafikspeichers (VRAM)."),
    ("SmallData", r"D3D Dedicated Memory Used", "Grafikspeicher, den Windows-Programme gerade belegen."),
    ("SmallData", r"D3D Shared Memory Used", "Arbeitsspeicher, den die Grafikkarte zusätzlich mitbenutzt – steigt, "
                                             "wenn der Grafikspeicher knapp wird. Bei Onboard-Grafik ohne eigenen "
                                             "Grafikspeicher ist das ihr ganzer Speicher."),
    ("SmallData", r"D3D Shared Memory Free", "Arbeitsspeicher, den die Grafik noch zusätzlich belegen dürfte."),
    ("SmallData", r"D3D Shared Memory Total", "Wie viel Arbeitsspeicher Windows der Grafik höchstens überlässt "
                                              "(meist die Hälfte)."),
    # --- Durchsatz ---
    ("Throughput", r"Read Rate", "Aktuelle Lesegeschwindigkeit des Laufwerks."),
    ("Throughput", r"Write Rate", "Aktuelle Schreibgeschwindigkeit des Laufwerks."),
    ("Throughput", r"Upload Speed", "Aktuelle Upload-Geschwindigkeit."),
    ("Throughput", r"Download Speed", "Aktuelle Download-Geschwindigkeit."),
    ("Throughput", r"GPU PCIe Rx", "Daten, die die Grafikkarte gerade über PCIe empfängt."),
    ("Throughput", r"GPU PCIe Tx", "Daten, die die Grafikkarte gerade über PCIe sendet."),
    # --- Zustand ---
    ("Level", r"Available Spare", "Reserve-Speicherzellen der SSD für defekte Zellen; sinkt im Laufe der Zeit."),
    ("Level", r"Available Spare Threshold", "Grenzwert: Fällt die Reserve (Available Spare) darunter, meldet die SSD "
                                            "einen kritischen Zustand – kein Messwert."),
    ("Level", r"Life", "Geschätzte verbleibende Lebensdauer der SSD."),
    ("Level", r"Percentage Used", "Verbrauchter Anteil der vom Hersteller angegebenen Lebensdauer der SSD."),
    ("Level", r"Charge Level", "Ladestand des Akkus."),
    ("Level", r"Degradation Level", "Wie stark der Akku gegenüber neu an Kapazität verloren hat."),
    # --- Zähler ---
    ("Factor", r"Power On Count", "Wie oft das Laufwerk insgesamt eingeschaltet wurde."),
    ("Factor", r"Power On Hours", "Betriebsstunden des Laufwerks über seine ganze Lebensdauer."),
]

TYP_ERKLAERUNGEN = {   # Rückfall, wenn kein genauerer Eintrag oben passt
    "Temperature": "Ein Temperaturfühler dieser Komponente.",
    "Load": "Auslastung in Prozent.",
    "Clock": "Taktfrequenz in Megahertz (Millionen Takte pro Sekunde).",
    "Power": "Aktuelle Leistungsaufnahme in Watt.",
    "Voltage": "Gemessene Spannung in Volt.",
    "Current": "Gemessene Stromstärke in Ampere.",
    "Energy": "Eine Energiemenge in Wattstunden.",
    "TimeSpan": "Eine Zeitdauer in Stunden und Minuten.",
    "Fan": "Lüfterdrehzahl in Umdrehungen pro Minute.",
    "Control": "Ansteuerung eines Lüfters oder einer Pumpe in Prozent.",
    "Data": "Eine Datenmenge.",
    "SmallData": "Eine Speichermenge.",
    "Throughput": "Aktuelle Übertragungsgeschwindigkeit.",
    "Level": "Füllstand bzw. Zustand in Prozent.",
}
