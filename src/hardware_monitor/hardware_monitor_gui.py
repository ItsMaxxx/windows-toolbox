"""
Seite des Hardware-Monitors in der Toolbox-GUI (Bausteine aus src/gui/base.py).

Die Toolbox läuft ohne Adminrechte, hardware_monitor mit. Deshalb:
  - Status, Beenden und "Einstellungen neu laden" gehen über eine lokale Verbindung (IPC_PORT),
  - Starten geht über die geplante Aufgabe (keine UAC-Abfrage) oder notfalls direkt mit UAC-Abfrage,
  - Einstellungen schreibt die Toolbox in hardware_monitor_settings.json und sagt hardware_monitor dann "reload".
"""

import json
import socket
import time
from pathlib import Path

import winutil
from base import (BAD, GOOD, MUTED, WARN, Button, Buttons, Choice, Combo, Entry, Section, Slider, Switch, Text,
                  ToolInfo, ToolPage)

FOLDER = Path(__file__).resolve().parent
SCRIPT = FOLDER / "hardware_monitor.py"
# Von Einrichten.cmd angelegt: Kopie von pythonw.exe im Projekt-Python – so heißt der Prozess im Task-Manager
MONITOR_EXE = FOLDER.parents[1] / "runtime" / "HardwareMonitor.exe"
IPC_PORT = 47815                 # muss zu IPC_PORT in hardware_monitor.py passen
DEFAULT_TASK = "HardwareMonitor"

ICON_RATES = {"1 s": 1, "2 s": 2, "5 s": 5, "10 s": 10}
POPUP_RATES = {"0,5 s": 0.5, "1 s": 1, "2 s": 2, "5 s": 5}
ORDERS = {"CPU zuerst": ["cpu", "gpu"], "GPU zuerst": ["gpu", "cpu"]}
AUTO = {"auto": "Automatisch"}
CPU_CHOICES = ["Automatisch", "Core (Tctl/Tdie)", "CPU Package", "Core Max", "Core Average", "CCD1 (Tdie)", "CCD2 (Tdie)"]
GPU_CHOICES = ["Automatisch", "GPU Core", "GPU Hot Spot", "GPU Memory Junction"]


def ipc(command, timeout=0.6):
    """Schickt einen Befehl an hardware_monitor. Antwort als dict – oder None, wenn es nicht läuft."""
    try:
        with socket.create_connection(("127.0.0.1", IPC_PORT), timeout=timeout) as conn:
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


def monitor_exe():
    """Womit hardware_monitor.py läuft: runtime\\HardwareMonitor.exe, sonst pythonw.exe des laufenden Pythons."""
    return str(MONITOR_EXE) if MONITOR_EXE.exists() else winutil.pythonw_exe()


def same_path(a, b):
    try:
        return Path(a).resolve() == Path(b).resolve()
    except (OSError, ValueError):
        return False


class HardwareMonitorPage(ToolPage):
    settings_file = FOLDER / "hardware_monitor_settings.json"
    defaults = {                 # muss zu DEFAULT_SETTINGS in hardware_monitor.py passen
        "icon_interval": 2, "popup_interval": 1, "icon_order": ["cpu", "gpu"],
        "cpu_sensor": "auto", "gpu_sensor": "auto", "warn_temp": 60, "hot_temp": 80,
    }
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
                    Text(f"⚠  {SCRIPT} nicht gefunden.", name="missing", color=WARN, hidden=True)),
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
                    Choice("Detailfenster", "popup_interval", POPUP_RATES)),
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
                    Entry("Name der Aufgabe", value=self.task_name, command=self.on_task_name),
                    Buttons(Button("Ordner öffnen", lambda: self.open(FOLDER), **grey),
                            Button("Log öffnen", lambda: self.open(FOLDER / "hardware_monitor.log"), **grey),
                            Button("Einstellungsdatei öffnen", lambda: self.open(self.settings_file), **grey),
                            Button("Alles zurücksetzen", self.reset, width=150, style="gefahr"))),
        ]

    # ---------- Einstellungen ----------
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

    @property
    def task_name(self):
        return self.app.tool_settings("hardware_monitor").get("task_name", DEFAULT_TASK)

    def on_task_name(self, name):
        name = name or DEFAULT_TASK
        if name != self.task_name:
            self.app.tool_settings("hardware_monitor")["task_name"] = name
            self.app.save()
            self.refresh_task()

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
        self.w["status"].configure(
            text=f"●  Läuft  ·  CPU {fmt_temp(status.get('cpu'))}  ·  GPU {fmt_temp(status.get('gpu'))}"
            if running else "●  Gestoppt", text_color=GOOD if running else MUTED)
        self.enable("start", not running)
        self.enable("stop", running)
        self.enable("restart", running)
        self.show("missing", not SCRIPT.exists())
        self.update_order_hint()

    def say(self, text):
        self.w["status"].configure(text=f"●  {text}", text_color=MUTED)

    def start(self):
        if not SCRIPT.exists():
            self.app.toast("hardware_monitor.py nicht gefunden", error=True)
            return
        self.say("Wird gestartet …")
        self.enable("start", False)
        task = self.task_name

        def work():
            info = winutil.task_info(task)
            if info and info.get("state") != "Disabled" and self.task_points_here(info) and winutil.run_task(task):
                return True
            # Keine passende aktive Aufgabe -> direkt mit Adminrechten starten; Windows fragt per UAC nach
            return winutil.run_elevated(monitor_exe(), f'"{SCRIPT}"', cwd=str(FOLDER))

        def done(ok):
            if not ok:
                self.app.toast("Start abgebrochen oder fehlgeschlagen", error=True)
            self.poll_status_soon()

        self.app.run_async(work, done)

    def stop(self):
        self.say("Wird beendet …")
        self.app.run_async(lambda: ipc("quit"), lambda result: self.poll_status_soon())

    def restart(self):
        self.say("Wird neu gestartet …")

        def work():
            ipc("quit")
            for _ in range(50):                  # bis zu 5 Sekunden warten, bis es wirklich beendet ist
                if ipc("status", timeout=0.2) is None:
                    return True
                time.sleep(0.1)
            return False

        def done(stopped):
            if stopped:
                self.start()
            else:
                self.app.toast("Programm reagiert nicht", error=True)

        self.app.run_async(work, done)

    # ---------- Autostart ----------
    def refresh_task(self):
        task = self.task_name
        self.w["autostart"].configure(state="disabled")
        self.w["task_label"].configure(text=f"Prüfe Aufgabe „{task}“ …", text_color=MUTED)
        self.app.run_async(lambda: winutil.task_info(task), self.show_task)

    def task_points_here(self, info):
        """Startet die Aufgabe wirklich dieses hardware_monitor.py mit dem richtigen Programm – und nicht z. B. eine
        alte Kopie unter C:\\Tools oder den Ort, an dem der Ordner vor dem Verschieben lag?"""
        arguments = (info.get("arguments") or "").strip().strip('"')
        return bool(arguments) and same_path(arguments, SCRIPT) and same_path(info.get("execute") or "", monitor_exe())

    def show_task(self, info):
        task, switch, label, button = self.task_name, self.w["autostart"], self.w["task_label"], self.w["task_button"]
        if info is None:
            switch.deselect()
            button.configure(text="Aufgabe einrichten")
            label.configure(text=f"Aufgabe „{task}“ gibt es noch nicht. „Aufgabe einrichten“ legt sie an "
                                 f"(Windows fragt einmal nach Adminrechten).", text_color=WARN)
            return
        enabled = info.get("state") != "Disabled"
        switch.configure(state="normal")
        switch.select() if enabled else switch.deselect()
        if self.task_points_here(info):
            button.configure(text="Neu einrichten")
            label.configure(text=f"Aufgabe „{task}“ in der Aufgabenplanung ({'aktiv' if enabled else 'deaktiviert'})",
                            text_color=MUTED)
        else:
            button.configure(text="Aufgabe aktualisieren")
            label.configure(text=f"⚠  Aufgabe „{task}“ startet einen anderen Ort: {info.get('execute')} "
                                 f"{info.get('arguments')}\n„Aufgabe aktualisieren“ stellt sie auf diesen Ordner um "
                                 f"(oder Einrichten.cmd erneut ausführen).", text_color=WARN)

    def setup_task(self):
        if not SCRIPT.exists():
            self.app.toast("hardware_monitor.py nicht gefunden", error=True)
            return
        task = self.task_name
        self.w["task_button"].configure(state="disabled")
        self.w["task_label"].configure(text="Richte Aufgabe ein … (bitte die Windows-Abfrage bestätigen)",
                                       text_color=MUTED)

        def done(ok):
            self.w["task_button"].configure(state="normal")
            self.app.toast("Aufgabe eingerichtet ✓" if ok else "Einrichten fehlgeschlagen oder abgebrochen",
                           error=not ok)
            self.refresh_task()

        self.app.run_async(lambda: winutil.register_task(task, SCRIPT, monitor_exe()), done)

    def toggle_autostart(self):
        enabled, task = bool(self.w["autostart"].get()), self.task_name
        self.w["autostart"].configure(state="disabled")

        def done(ok):
            if not ok:
                self.app.toast("Ändern fehlgeschlagen oder abgebrochen", error=True)
            self.refresh_task()

        self.app.run_async(lambda: winutil.set_task_enabled(task, enabled), done)


TOOL = ToolInfo("hardware_monitor", "Hardware-Monitor", "Allgemein",
                "CPU- und GPU-Temperatur in der Taskleiste; ein Klick aufs Icon zeigt fast alle Hardware-Werte "
                "(hardware_monitor).",
                HardwareMonitorPage)
