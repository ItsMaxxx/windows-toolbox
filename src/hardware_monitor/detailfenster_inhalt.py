"""
Was im Detailfenster des Hardware-Monitors steht – Tab für Tab, eine Zeile pro Wert.

  Wert hinzufügen:  eine Zeile Wert("Name") in die passende Gruppe schreiben
  Wert weglassen:   die Zeile löschen
  Reihenfolge:      so wie hier aufgeschrieben

Die genauen Sensornamen stehen in der Ausgabe von `python hardware_monitor.py --list`
(dort in eckigen Klammern auch das Gerät für Gruppe(...): cpu, gpu, ram, mainboard, laufwerk, netzwerk).

  Gruppe("laufwerk", ...)          gilt für jedes Laufwerk einzeln
  Wert("Fan #*")                   * steht für beliebigen Text – hier: alle Lüfter
  Wert("GPU Core", typ="Takt")     typ nur nötig, wenn es den Namen mehrfach gibt
  Wert("Package", text="CPU gesamt")   eigene Beschriftung
  Hardwaredaten()                  statt Gruppen: feste Daten wie Hersteller- und Produkt-IDs

Gespeichert? Fenster schließen und wieder öffnen – die Änderungen sind sofort da.
"""

from detailfenster import AlleSensoren, Gruppe, Hardwaredaten, Tab, Wert  # noqa: F401 (AlleSensoren siehe unten)

FENSTER = [
    Tab("Temperaturen",
        Gruppe("cpu",
               Wert("Core (Tctl/Tdie)"),
               Wert("CCD* (Tdie)")),
        Gruppe("gpu",
               Wert("GPU Core", typ="Temperatur"),
               Wert("GPU Hot Spot"),
               Wert("GPU Memory Junction"))),

    Tab("CPU",
        Gruppe("cpu",
               Wert("CPU Total"),
               Wert("CPU Core Max"),
               Wert("Package", typ="Leistung"),
               Wert("Cores (Average)"),
               Wert("Cores (Average Effective)"),
               Wert("Core (Tctl/Tdie)"),
               Wert("CCD* (Tdie)"),
               Wert("Core (SVI2 TFN)"),
               Wert("SoC (SVI2 TFN)"),
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
               Wert("GPU Fan *", typ="Lüfter"),
               Wert("GPU Fan *", typ="Lüftersteuerung"),
               Wert("GPU PCIe Rx"),
               Wert("GPU PCIe Tx"))),

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
               Wert("Fan #*", typ="Lüfter"),
               Wert("Fan #*", typ="Lüftersteuerung"),
               Wert("Vcore"),
               Wert("+12V"),
               Wert("+5V"),
               Wert("+3.3V"),
               Wert("+3V Standby"),
               Wert("+1.8V"),
               Wert("Chipset 1.05V"))),

    Tab("Laufwerke",
        Gruppe("laufwerk",                              # jedes Laufwerk einzeln
               Wert("Composite Temperature"),
               Wert("Temperature"),
               Wert("Temperature #*"),
               Wert("Used Space"),
               Wert("Free Space"),
               Wert("Total Space"),
               Wert("Read Rate"),
               Wert("Write Rate"),
               Wert("Total Activity"),
               Wert("Life"),
               Wert("Percentage Used"),
               Wert("Available Spare"),
               Wert("Data Read"),
               Wert("Data Written"),
               Wert("Power On Hours"))),

    Tab("Netzwerk",
        Gruppe("netzwerk",
               Wert("Download Speed"),
               Wert("Upload Speed"),
               Wert("Network Utilization"),
               Wert("Data Downloaded"),
               Wert("Data Uploaded"))),

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
    ("Temperature", r"Distance to TjMax", "Abstand bis zu der Temperatur, ab der sich die CPU drosselt – hier ist ein "
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
    ("Temperature", r"Temperature #(\d+)", "Unbenannter Temperaturfühler Nr. {0} am Mainboard; was er misst, hängt "
                                           "vom Board ab."),
    ("Temperature", r"Temperature( \d+)?", "Temperatur des Laufwerks (Controller oder Speicherchips)."),
    ("Temperature", r"Composite Temperature", "Zusammengefasste Temperatur der SSD, nach der sie sich ggf. drosselt."),
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
    ("Clock", r"Core #(\d+)", "Aktueller Takt von CPU-Kern Nr. {0}."),
    ("Clock", r"Bus Speed", "Grundtakt, aus dem sich per Multiplikator der CPU-Takt ergibt (meist rund 100 MHz)."),
    ("Clock", r"Cores \(Average.*\)", "Durchschnittlicher Takt aller CPU-Kerne."),
    ("Clock", r"GPU Core", "Aktueller Takt des Grafikchips."),
    ("Clock", r"GPU Memory", "Aktueller Takt des Grafikspeichers."),
    ("Clock", r"GPU Shader", "Takt der Shader-Einheiten der Grafikkarte."),
    # --- Leistung ---
    ("Power", r"(CPU )?Package", "Gesamter Stromverbrauch des Prozessors."),
    ("Power", r"Core #(\d+) \(SMU\)", "Stromverbrauch von Kern Nr. {0}, gemeldet vom Prozessor selbst."),
    ("Power", r"Cores", "Stromverbrauch aller Kerne zusammen."),
    ("Power", r"SoC", "Stromverbrauch des I/O-Teils der CPU."),
    ("Power", r"GPU (Package|Power)", "Gesamter Stromverbrauch der Grafikkarte."),
    # --- Spannung ---
    ("Voltage", r"Core \(SVI\d? ?TFN\)", "Kernspannung der CPU, gemeldet vom Spannungsregler."),
    ("Voltage", r"SoC \(SVI\d? ?TFN\)", "Spannung des I/O-Teils der CPU."),
    ("Voltage", r"Vcore|CPU Core|CPU VCore", "Kernspannung der CPU, gemessen vom Mainboard."),
    ("Voltage", r"\+?(12|5|3[.,]3)V", "Spannung der {0}-Volt-Leitung vom Netzteil; sollte nahe am Sollwert liegen "
                                      "(etwa ±5 %)."),
    ("Voltage", r"VBat|Vbat|CMOS Battery|Battery", "Spannung der Knopfzelle auf dem Mainboard; liegt sie unter etwa "
                                                   "2,8 V, sollte sie bald getauscht werden."),
    ("Voltage", r"GPU Core", "Spannung des Grafikchips."),
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
                                             "wenn der Grafikspeicher knapp wird."),
    # --- Durchsatz ---
    ("Throughput", r"Read Rate", "Aktuelle Lesegeschwindigkeit des Laufwerks."),
    ("Throughput", r"Write Rate", "Aktuelle Schreibgeschwindigkeit des Laufwerks."),
    ("Throughput", r"Upload Speed", "Aktuelle Upload-Geschwindigkeit."),
    ("Throughput", r"Download Speed", "Aktuelle Download-Geschwindigkeit."),
    ("Throughput", r"GPU PCIe Rx", "Daten, die die Grafikkarte gerade über PCIe empfängt."),
    ("Throughput", r"GPU PCIe Tx", "Daten, die die Grafikkarte gerade über PCIe sendet."),
    # --- Zustand ---
    ("Level", r"Available Spare", "Reserve-Speicherzellen der SSD für defekte Zellen; sinkt im Laufe der Zeit."),
    ("Level", r"Remaining Life", "Geschätzte verbleibende Lebensdauer der SSD."),
    ("Level", r"Percentage Used", "Verbrauchter Anteil der vom Hersteller angegebenen Lebensdauer der SSD."),
    ("Level", r"Charge Level", "Ladestand des Akkus."),
    ("Level", r"Degradation Level", "Wie stark der Akku gegenüber neu an Kapazität verloren hat."),
]

TYP_ERKLAERUNGEN = {   # Rückfall, wenn kein genauerer Eintrag oben passt
    "Temperature": "Ein Temperaturfühler dieser Komponente.",
    "Load": "Auslastung in Prozent.",
    "Clock": "Taktfrequenz in Megahertz (Millionen Takte pro Sekunde).",
    "Power": "Aktuelle Leistungsaufnahme in Watt.",
    "Voltage": "Gemessene Spannung in Volt.",
    "Current": "Gemessene Stromstärke in Ampere.",
    "Fan": "Lüfterdrehzahl in Umdrehungen pro Minute.",
    "Control": "Ansteuerung eines Lüfters oder einer Pumpe in Prozent.",
    "Data": "Eine Datenmenge.",
    "SmallData": "Eine Speichermenge.",
    "Throughput": "Aktuelle Übertragungsgeschwindigkeit.",
    "Level": "Füllstand bzw. Zustand in Prozent.",
}
