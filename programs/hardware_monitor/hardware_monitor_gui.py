"""
Seite des Hardware-Monitors in der Toolbox-GUI (Bausteine aus toolbox/base.py).

Die Toolbox läuft ohne Adminrechte, hardware_monitor mit. Deshalb:
  - Status, Beenden und "Einstellungen neu laden" gehen über eine lokale Verbindung (IPC_PORT),
  - Starten geht über die geplante Aufgabe (keine UAC-Abfrage) oder notfalls direkt mit UAC-Abfrage,
  - Einstellungen schreibt die Toolbox in data\\hardware_monitor.json und sagt hardware_monitor dann "reload".
Alle Texte stehen in i18n.json – hier steht nur ihre ID: t("seite.…") (siehe toolbox\\i18n.py).
"""

import json
import socket
import sys
import time
from pathlib import Path

import winutil
from base import BAD, GOOD, MUTED, WARN, Button, Buttons, Choice, Combo, Program, Section, Slider, Switch, Text, ToolPage

FOLDER = Path(__file__).resolve().parent
sys.path.append(str(FOLDER))
# Startwerte, Raten, Port, Aufgabe, Laden/Speichern, Texte – gemeinsam mit hardware_monitor.py
import hardware_monitor_settings as hm  # noqa: E402
from hardware_monitor_settings import t  # noqa: E402

# Von Setup.exe angelegt: der Starter HardwareMonitor.exe (findet runtime\ relativ zu sich, deshalb ohne
# Argumente) und dahinter pythonw.exe mit eigenem Namen und Symbol – so heißt der Prozess im Task-Manager
# „Hardware-Monitor“ statt „Python“ (setup\make_exe.py)
STARTER = FOLDER / hm.AUSWEIS["starter"]


def sekunden(werte):
    """(0.5, 1, 2) -> {"0,5 s": 0.5, "1 s": 1, "2 s": 2} für die Auswahlknöpfe."""
    return {f"{w:g} s".replace(".", ","): w for w in werte}


ICON_RATES = sekunden(hm.ICON_RATES)
POPUP_RATES = sekunden(hm.POPUP_RATES)
# Sensornamen von LibreHardwareMonitor – die bleiben englisch; davor steht in der Liste noch „Automatisch“
CPU_CHOICES = ["Core (Tctl/Tdie)", "CPU Package", "Core Max", "Core Average", "CCD1 (Tdie)", "CCD2 (Tdie)"]
GPU_CHOICES = ["GPU Core", "GPU Hot Spot", "GPU Memory Junction"]


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
    Ordner vor dem Verschieben lag? (Dasselbe prüft setup.ps1 in Schritt 6.)"""
    return same_path(info.get("execute") or "", STARTER) and not (info.get("arguments") or "").strip()


# ---------- Programm steuern (auch für „Toolbox und alle Programme“ in den Toolbox-Einstellungen) ----------
# Alle blockieren eine Weile – nur im Hintergrund aufrufen (app.run_async).
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


def neu_laden():
    """Einstellungen und Sprache neu einlesen lassen (z. B. nach einem Sprachwechsel in der Toolbox)."""
    ipc("reload")


class HardwareMonitorPage(ToolPage):
    settings_file = hm.SETTINGS_FILE
    defaults = hm.DEFAULT_SETTINGS
    visible = False
    poll_job = None
    running_order = None         # Icon-Reihenfolge, mit der das laufende Programm gestartet wurde

    def layout(self):
        grey = {"width": 150, "style": "gray"}
        auto = {"auto": t("seite.automatisch")}
        return [
            Section(t("seite.status"),
                    Text(f"●  {t('seite.status.pruefe')}", name="status", size=14),
                    Buttons(Button(t("seite.starten"), self.start, name="start"),
                            Button(t("seite.beenden"), self.stop, name="stop"),
                            Button(t("seite.neu_starten"), self.restart, name="restart")),
                    Text(f"⚠  {t('seite.starter_fehlt', starter=STARTER)}", name="missing", color=WARN,
                         hidden=True)),
            Section(t("seite.autostart"),
                    Text(t("seite.autostart.text")),
                    Switch(t("seite.autostart.schalter"), command=self.toggle_autostart, name="autostart"),
                    Text(name="task_label"),
                    Buttons(Button(t("seite.aufgabe.einrichten"), self.setup_task, name="task_button", width=170))),
            Section(t("seite.aktualisierung"),
                    Text(t("seite.aktualisierung.text")),
                    Choice(t("seite.aktualisierung.icons"), "icon_interval", ICON_RATES),
                    Choice(t("seite.aktualisierung.fenster"), "popup_interval", POPUP_RATES),
                    Choice(t("seite.effizienz"), "effizienzmodus",
                           dict(zip((t("seite.automatisch"), t("seite.effizienz.an"), t("seite.effizienz.aus")),
                                    hm.EFFIZIENZ)),
                           info=t("seite.effizienz.info"))),
            Section(t("seite.anzeige"),
                    Choice(t("seite.reihenfolge"), "icon_order",
                           {t("seite.reihenfolge.cpu"): ["cpu", "gpu"], t("seite.reihenfolge.gpu"): ["gpu", "cpu"]}),
                    Text(t("seite.reihenfolge.hinweis"), name="order_hint", color=WARN, hidden=True),
                    Combo(t("seite.sensor_cpu"), "cpu_sensor", [auto["auto"], *CPU_CHOICES], names=auto),
                    Combo(t("seite.sensor_gpu"), "gpu_sensor", [auto["auto"], *GPU_CHOICES], names=auto),
                    Text(t("seite.sensor.text")),
                    Text(t("seite.farben.text")),
                    Slider(t("seite.cpu_gelb"), "cpu_warn_temp", 40, 100, color=WARN),
                    Slider(t("seite.cpu_rot"), "cpu_hot_temp", 41, 110, color=BAD),
                    Slider(t("seite.gpu_gelb"), "gpu_warn_temp", 40, 100, color=WARN),
                    Slider(t("seite.gpu_rot"), "gpu_hot_temp", 41, 110, color=BAD)),
            Section(t("seite.detailfenster"),
                    Text(t("seite.detailfenster.text")),
                    Buttons(Button(t("seite.ordner_oeffnen"), lambda: self.open(FOLDER), width=150, style="gray",
                                   target=FOLDER))),
            Section(t("seite.erweitert"),
                    Buttons(Button(t("seite.log_oeffnen"), lambda: self.open(hm.LOG_FILE), target=hm.LOG_FILE, **grey),
                            Button(t("seite.einstellungsdatei_oeffnen"), lambda: self.open(self.settings_file),
                                   target=self.settings_file, **grey),
                            Button(t("seite.zuruecksetzen"), self.reset, width=150, style="danger"))),
        ]

    # ---------- Einstellungen ----------
    def load(self):
        return hm.load_settings()                # mit derselben Prüfung wie im Monitor selbst

    def on_change(self, key, value):
        # gelb muss immer unter rot liegen – den anderen Regler notfalls mitziehen
        kind, _, art = key.partition("_")                # z. B. "cpu", "warn_temp"
        warn, hot = f"{kind}_warn_temp", f"{kind}_hot_temp"
        if art == "warn_temp" and value >= self.data[hot]:
            self.data[hot] = value + 1
            self.refresh(hot)
        elif art == "hot_temp" and value <= self.data[warn]:
            self.data[warn] = value - 1
            self.refresh(warn)
        elif key == "icon_order":
            self.update_order_hint()

    def on_saved(self):
        self.app.run_async(neu_laden)

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
        if not self.winfo_exists():
            return                               # Seite wurde inzwischen neu gebaut (Sprachwechsel)
        running = bool(status and status.get("ok"))
        self.running_order = status.get("order") if running else None
        if running:                              # nur die Icons, die es gibt (ohne GPU-Temperatur kein GPU-Icon)
            werte = [f"{kind.upper()} {fmt_temp(status.get(kind))}" for kind in status.get("icons", ["cpu", "gpu"])]
            text = "  ·  ".join([f"●  {t('seite.status.laeuft')}"] + werte)
        else:
            text = f"●  {t('seite.status.gestoppt')}"
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
            self.app.toast(t("seite.toast.starter_fehlt", starter=STARTER.name), error=True)
            return
        self.say(t("seite.status.startet"))
        self.enable("start", False)

        def done(ok):
            if not ok:
                self.app.toast(t("seite.toast.start_fehlgeschlagen"), error=True)
            self.poll_status_soon()

        self.app.run_async(starten, done)

    def stop(self):
        self.say(t("seite.status.beendet"))
        self.app.run_async(lambda: ipc("quit"), lambda result: self.poll_status_soon())

    def restart(self):
        self.say(t("seite.status.neustart"))

        def done(stopped):
            if stopped:
                self.start()
            else:
                self.app.toast(t("seite.toast.reagiert_nicht"), error=True)

        self.app.run_async(beenden, done)

    # ---------- Autostart ----------
    def refresh_task(self):
        task = hm.AUFGABE
        self.w["autostart"].configure(state="disabled")
        self.w["task_label"].configure(text=t("seite.aufgabe.pruefe", task=task), text_color=MUTED)
        self.app.run_async(lambda: winutil.task_info(task), self.show_task)

    def show_task(self, info):
        if not self.winfo_exists():
            return                               # Seite wurde inzwischen neu gebaut (Sprachwechsel)
        task, switch, label, button = hm.AUFGABE, self.w["autostart"], self.w["task_label"], self.w["task_button"]
        if info is None:
            switch.deselect()
            button.configure(text=t("seite.aufgabe.einrichten"))
            label.configure(text=t("seite.aufgabe.fehlt", task=task), text_color=WARN)
            return
        enabled = info.get("state") != "Disabled"
        switch.configure(state="normal")
        switch.select() if enabled else switch.deselect()
        if task_points_here(info):
            button.configure(text=t("seite.aufgabe.neu_einrichten"))
            label.configure(text=t("seite.aufgabe.aktiv" if enabled else "seite.aufgabe.deaktiviert", task=task),
                            text_color=MUTED)
        else:
            button.configure(text=t("seite.aufgabe.aktualisieren"))
            text = t("seite.aufgabe.anderer_ort", task=task, ziel=info.get("execute"), argumente=info.get("arguments"))
            label.configure(text=f"⚠  {text}", text_color=WARN)

    def setup_task(self):
        if not STARTER.exists():
            self.app.toast(t("seite.toast.starter_fehlt", starter=STARTER.name), error=True)
            return
        self.w["task_button"].configure(state="disabled")
        self.w["task_label"].configure(text=t("seite.aufgabe.richte_ein"), text_color=MUTED)

        def done(ok):
            if not self.winfo_exists():
                return
            self.w["task_button"].configure(state="normal")
            self.app.toast(t("seite.toast.aufgabe_eingerichtet") if ok else t("seite.toast.einrichten_fehlgeschlagen"),
                           error=not ok)
            self.refresh_task()

        self.app.run_async(lambda: winutil.register_task(hm.AUFGABE, STARTER, cwd=FOLDER), done)

    def toggle_autostart(self):
        enabled = bool(self.w["autostart"].get())
        self.w["autostart"].configure(state="disabled")

        def done(ok):
            if not ok:
                self.app.toast(t("seite.toast.aendern_fehlgeschlagen"), error=True)
            if self.winfo_exists():
                self.refresh_task()

        self.app.run_async(lambda: winutil.set_task_enabled(hm.AUFGABE, enabled), done)


PAGE = HardwareMonitorPage
PROGRAM = Program(laeuft, beenden, starten, neu_laden)     # für „Toolbox und alle Programme“ und den Sprachwechsel
