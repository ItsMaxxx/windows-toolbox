"""
Seite des Hardware-Monitors in der Toolbox-GUI (Bausteine aus toolbox/base.py).

Die Toolbox läuft ohne Adminrechte, hardware_monitor mit. Deshalb:
  - Status, Beenden und "Einstellungen neu laden" gehen über eine lokale Verbindung (IPC_PORT),
  - Starten geht über die geplante Aufgabe (keine UAC-Abfrage) oder notfalls direkt mit UAC-Abfrage,
  - Einstellungen schreibt die Toolbox in daten\\hardware_monitor.json und sagt hardware_monitor dann "reload".
"""

import json
import socket
import sys
import time
from pathlib import Path

import winutil
from base import BAD, GOOD, MUTED, WARN, Button, Buttons, Choice, Combo, Programm, Section, Slider, Switch, Text, ToolPage

FOLDER = Path(__file__).resolve().parent
sys.path.append(str(FOLDER))
# Startwerte, Raten, Port, Aufgabe, Laden/Speichern – gemeinsam mit hardware_monitor.py
import hardware_monitor_einstellungen as hm  # noqa: E402

# Von Setup.exe angelegt: der Starter HardwareMonitor.exe (findet runtime\ relativ zu sich, deshalb ohne
# Argumente) und dahinter pythonw.exe mit eigenem Namen und Symbol – so heißt der Prozess im Task-Manager
# „Hardware-Monitor“ statt „Python“ (setup\exe_anlegen.py)
STARTER = FOLDER / hm.AUSWEIS["starter"]


def sekunden(werte):
    """(0.5, 1, 2) -> {"0,5 s": 0.5, "1 s": 1, "2 s": 2} für die Auswahlknöpfe."""
    return {f"{w:g} s".replace(".", ","): w for w in werte}


ICON_RATES = sekunden(hm.ICON_RATES)
POPUP_RATES = sekunden(hm.POPUP_RATES)
ORDERS = {"CPU zuerst": ["cpu", "gpu"], "GPU zuerst": ["gpu", "cpu"]}
AUTO = {"auto": "Automatisch"}
CPU_CHOICES = ["Automatisch", "Core (Tctl/Tdie)", "CPU Package", "Core Max", "Core Average", "CCD1 (Tdie)", "CCD2 (Tdie)"]
GPU_CHOICES = ["Automatisch", "GPU Core", "GPU Hot Spot", "GPU Memory Junction"]
EFFIZIENZ = dict(zip(("Automatisch", "Immer an", "Aus"), hm.EFFIZIENZ))
EFFIZIENZ_INFO = (                # Tooltip am „i“ neben der Auswahl
    "Effizienzmodus von Windows 11 (grünes Blatt im Task-Manager):\n\n"
    "•  Automatisch: an, solange das Detailfenster zu ist – beim Öffnen aus, damit es flüssig bleibt.\n"
    "•  Immer an: auch bei offenem Fenster. Am sparsamsten, das Fenster reagiert evtl. träger.\n"
    "•  Aus: läuft immer mit normaler Priorität."
)


def ipc(command, timeout=0.6):
    """Schickt einen Befehl an hardware_monitor. Antwort als dict – oder None, wenn es nicht läuft."""
    try:
        with socket.create_connection(("127.0.0.1", hm.IPC_PORT), timeout=timeout) as conn:
            conn.sendall(command.encode("utf-8") + b"\n")
            data = b""
            while not data.endswith(b"\n"):
                chunk = conn.recv(4096)
                if not chunk:
                    break
                data += chunk
        return json.loads(data) if data else None
    except (OSError, ValueError):
        return None


def fmt_temp(value):
    return "–" if value is None else f"{value:.0f} °C"


def same_path(a, b):
    try:
        return Path(a).resolve() == Path(b).resolve()
    except (OSError, ValueError):
        return False


def task_points_here(info):
    """Startet die Aufgabe wirklich diesen Monitor – den Starter ohne Argumente – und nicht z. B. den Ort, an dem der
    Ordner vor dem Verschieben lag? (Dasselbe prüft setup.ps1 in Schritt 5.)"""
    return same_path(info.get("execute") or "", STARTER) and not (info.get("arguments") or "").strip()


# ---------- Programm steuern (auch für „Toolbox und alle Programme“ in den Toolbox-Einstellungen) ----------
# Alle drei blockieren eine Weile – nur im Hintergrund aufrufen (app.run_async).
def laeuft():
    return ipc("status") is not None


def beenden():
    """Bittet das Programm, sich zu beenden, und wartet aufs Prozessende (sonst scheitert ein direkter Neustart)."""
    status = ipc("status")
    if status is None:
        return True
    ipc("quit")
    if winutil.wait_for_exit(status.get("pid"), timeout=10):
        return True
    for _ in range(50):                          # Rückfall: warten, bis es nicht mehr antwortet (bis zu 5 s)
        if ipc("status", timeout=0.2) is None:
            return True
        time.sleep(0.1)
    return False


def starten():
    """Über die geplante Aufgabe (ohne Nachfrage) – oder, wenn es keine passende gibt, direkt mit UAC-Abfrage."""
    info = winutil.task_info(hm.AUFGABE)
    if info and info.get("state") != "Disabled" and task_points_here(info) and winutil.run_task(hm.AUFGABE):
        return True
    return winutil.run_elevated(str(STARTER), cwd=str(FOLDER))


class HardwareMonitorPage(ToolPage):
    settings_file = hm.SETTINGS_FILE
    defaults = hm.DEFAULT_SETTINGS
    visible = False
    poll_job = None
    running_order = None         # Icon-Reihenfolge, mit der das laufende Programm gestartet wurde

    def layout(self):
        grey = {"width": 150, "style": "grau"}
        return [
            Section("Status",
                    Text("●  Prüfe …", name="status", size=14),
                    Buttons(Button("Starten", self.start, name="start"),
                            Button("Beenden", self.stop, name="stop"),
                            Button("Neu starten", self.restart, name="restart")),
                    Text(f"⚠  {STARTER} fehlt – bitte Setup.exe ausführen.", name="missing", color=WARN,
                         hidden=True)),
            Section("Autostart",
                    Text("Startet den Hardware-Monitor beim Anmelden über die Aufgabenplanung "
                         "(mit Adminrechten, ohne Nachfrage)."),
                    Switch("Beim Anmelden automatisch starten", command=self.toggle_autostart, name="autostart"),
                    Text(name="task_label"),
                    Buttons(Button("Aufgabe einrichten", self.setup_task, name="task_button", width=170))),
            Section("Aktualisierung",
                    Text("Wie oft gemessen wird. Seltener = sparsamer. "
                         "Die Icons lesen nur CPU und GPU, das geöffnete Fenster die Geräte des gewählten Tabs."),
                    Choice("Taskleisten-Icons", "icon_interval", ICON_RATES),
                    Choice("Detailfenster", "popup_interval", POPUP_RATES),
                    Choice("Effizienzmodus", "effizienzmodus", EFFIZIENZ, info=EFFIZIENZ_INFO)),
            Section("Anzeige",
                    Choice("Reihenfolge der Icons", "icon_order", ORDERS),
                    Text("Wird nach „Neu starten“ übernommen", name="order_hint", color=WARN, hidden=True),
                    Combo("Sensor im CPU-Icon", "cpu_sensor", CPU_CHOICES, names=AUTO),
                    Combo("Sensor im GPU-Icon", "gpu_sensor", GPU_CHOICES, names=AUTO),
                    Text("Eigene Namen kannst du eintippen (siehe hardware_monitor.py --list). "
                         "Gibt es den Sensor nicht, wird automatisch gewählt."),
                    Slider("Gelb ab {} °C", "warn_temp", 40, 100, color=WARN),
                    Slider("Rot ab {} °C", "hot_temp", 41, 110, color=BAD)),
            Section("Detailfenster",
                    Text("Welche Werte im Detailfenster stehen, legst du in detailfenster_inhalt.py fest – "
                         "eine Zeile pro Wert. Änderungen erscheinen beim nächsten Öffnen des Fensters, "
                         "alle Sensornamen zeigt „hardware_monitor.py --list“."),
                    Buttons(Button("Ordner öffnen", lambda: self.open(FOLDER), width=150, style="grau"))),
            Section("Erweitert",
                    Buttons(Button("Log öffnen", lambda: self.open(hm.LOG_FILE), **grey),
                            Button("Einstellungsdatei öffnen", lambda: self.open(self.settings_file), **grey),
                            Button("Alles zurücksetzen", self.reset, width=150, style="gefahr"))),
        ]

    # ---------- Einstellungen ----------
    def load(self):
        return hm.load_settings()                # mit derselben Prüfung wie im Monitor selbst

    def on_change(self, key, value):
        # gelb muss immer unter rot liegen – den anderen Regler notfalls mitziehen
        if key == "warn_temp" and value >= self.data["hot_temp"]:
            self.data["hot_temp"] = value + 1
            self.refresh("hot_temp")
        elif key == "hot_temp" and value <= self.data["warn_temp"]:
            self.data["warn_temp"] = value - 1
            self.refresh("warn_temp")
        elif key == "icon_order":
            self.update_order_hint()

    def on_saved(self):
        self.app.run_async(lambda: ipc("reload"))

    def update_order_hint(self):
        self.show("order_hint", self.running_order is not None and self.running_order != self.data["icon_order"])

    # ---------- Status und Steuerung ----------
    def on_show(self):
        if self.visible:
            return
        self.visible = True
        super().on_show()                        # z. B. per Rechtsklick-Menü geänderte Raten übernehmen
        self.poll_status()
        self.refresh_task()

    def on_hide(self):
        self.visible = False
        if self.poll_job:
            self.after_cancel(self.poll_job)
            self.poll_job = None

    def poll_status(self):
        if not self.visible:
            return
        self.app.run_async(lambda: ipc("status"), self.show_status)
        self.poll_job = self.after(2000, self.poll_status)

    def poll_status_soon(self):
        """Nach Start/Stopp ein paar Mal schnell nachsehen, statt 2 Sekunden zu warten."""
        for delay in (400, 1200, 2500):
            self.after(delay, lambda: self.app.run_async(lambda: ipc("status"), self.show_status))

    def show_status(self, status):
        running = bool(status and status.get("ok"))
        self.running_order = status.get("order") if running else None
        if running:                              # nur die Icons, die es gibt (ohne GPU-Temperatur kein GPU-Icon)
            werte = [f"{kind.upper()} {fmt_temp(status.get(kind))}" for kind in status.get("icons", ["cpu", "gpu"])]
            text = "  ·  ".join(["●  Läuft"] + werte)
        else:
            text = "●  Gestoppt"
        self.w["status"].configure(text=text, text_color=GOOD if running else MUTED)
        self.enable("start", not running)
        self.enable("stop", running)
        self.enable("restart", running)
        self.show("missing", not STARTER.exists())
        self.update_order_hint()

    def say(self, text):
        self.w["status"].configure(text=f"●  {text}", text_color=MUTED)

    def start(self):
        if not STARTER.exists():
            self.app.toast(f"{STARTER.name} fehlt – bitte Setup.exe ausführen", error=True)
            return
        self.say("Wird gestartet …")
        self.enable("start", False)

        def done(ok):
            if not ok:
                self.app.toast("Start abgebrochen oder fehlgeschlagen", error=True)
            self.poll_status_soon()

        self.app.run_async(starten, done)

    def stop(self):
        self.say("Wird beendet …")
        self.app.run_async(lambda: ipc("quit"), lambda result: self.poll_status_soon())

    def restart(self):
        self.say("Wird neu gestartet …")

        def done(stopped):
            if stopped:
                self.start()
            else:
                self.app.toast("Programm reagiert nicht", error=True)

        self.app.run_async(beenden, done)

    # ---------- Autostart ----------
    def refresh_task(self):
        task = hm.AUFGABE
        self.w["autostart"].configure(state="disabled")
        self.w["task_label"].configure(text=f"Prüfe Aufgabe „{task}“ …", text_color=MUTED)
        self.app.run_async(lambda: winutil.task_info(task), self.show_task)

    def show_task(self, info):
        task, switch, label, button = hm.AUFGABE, self.w["autostart"], self.w["task_label"], self.w["task_button"]
        if info is None:
            switch.deselect()
            button.configure(text="Aufgabe einrichten")
            label.configure(text=f"Aufgabe „{task}“ gibt es noch nicht. „Aufgabe einrichten“ legt sie an "
                                 f"(Windows fragt einmal nach Adminrechten).", text_color=WARN)
            return
        enabled = info.get("state") != "Disabled"
        switch.configure(state="normal")
        switch.select() if enabled else switch.deselect()
        if task_points_here(info):
            button.configure(text="Neu einrichten")
            label.configure(text=f"Aufgabe „{task}“ in der Aufgabenplanung ({'aktiv' if enabled else 'deaktiviert'})",
                            text_color=MUTED)
        else:
            button.configure(text="Aufgabe aktualisieren")
            label.configure(text=f"⚠  Aufgabe „{task}“ startet einen anderen Ort: {info.get('execute')} "
                                 f"{info.get('arguments')}\n„Aufgabe aktualisieren“ stellt sie auf diesen Ordner um "
                                 f"(oder Setup.exe erneut ausführen).", text_color=WARN)

    def setup_task(self):
        if not STARTER.exists():
            self.app.toast(f"{STARTER.name} fehlt – bitte Setup.exe ausführen", error=True)
            return
        self.w["task_button"].configure(state="disabled")
        self.w["task_label"].configure(text="Richte Aufgabe ein … (bitte die Windows-Abfrage bestätigen)",
                                       text_color=MUTED)

        def done(ok):
            self.w["task_button"].configure(state="normal")
            self.app.toast("Aufgabe eingerichtet ✓" if ok else "Einrichten fehlgeschlagen oder abgebrochen",
                           error=not ok)
            self.refresh_task()

        self.app.run_async(lambda: winutil.register_task(hm.AUFGABE, STARTER, cwd=FOLDER), done)

    def toggle_autostart(self):
        enabled = bool(self.w["autostart"].get())
        self.w["autostart"].configure(state="disabled")

        def done(ok):
            if not ok:
                self.app.toast("Ändern fehlgeschlagen oder abgebrochen", error=True)
            self.refresh_task()

        self.app.run_async(lambda: winutil.set_task_enabled(hm.AUFGABE, enabled), done)


SEITE = HardwareMonitorPage
PROGRAMM = Programm(laeuft, beenden, starten)     # für „Toolbox und alle Programme“
