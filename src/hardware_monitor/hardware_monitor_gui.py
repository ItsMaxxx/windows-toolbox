"""
Programmseite für den Hardware-Monitor (hardware_monitor).

Die Toolbox läuft ohne Adminrechte, hardware_monitor mit. Deshalb:
  - Status, Beenden und "Einstellungen neu laden" gehen über eine lokale Verbindung (IPC_PORT),
  - Starten geht über die geplante Aufgabe (keine UAC-Abfrage) oder notfalls direkt mit UAC-Abfrage,
  - Einstellungen schreibt die Toolbox in hardware_monitor_settings.json und sagt hardware_monitor dann "reload".
"""

import json
import os
import socket
import time
from pathlib import Path

import customtkinter as ctk

from .base import BAD, BUTTON_OFF, GOOD, MUTED, WARN, ToolPage
from . import winutil

IPC_PORT = 47815                 # muss zu IPC_PORT in hardware_monitor.py passen
DEFAULT_TASK = "HardwareMonitor"

# Muss zu DEFAULT_SETTINGS in hardware_monitor.py passen
DEFAULTS = {
    "icon_interval": 2, "popup_interval": 1, "icon_order": ["cpu", "gpu"],
    "cpu_sensor": "auto", "gpu_sensor": "auto", "warn_temp": 60, "hot_temp": 80, "hidden": [],
}
ICON_RATES = {"1 s": 1, "2 s": 2, "5 s": 5, "10 s": 10}
POPUP_RATES = {"0,5 s": 0.5, "1 s": 1, "2 s": 2, "5 s": 5}
ORDERS = {"CPU zuerst": ["cpu", "gpu"], "GPU zuerst": ["gpu", "cpu"]}
AUTO = "Automatisch"
CPU_CHOICES = [AUTO, "Core (Tctl/Tdie)", "CPU Package", "Core Max", "Core Average", "CCD1 (Tdie)", "CCD2 (Tdie)"]
GPU_CHOICES = [AUTO, "GPU Core", "GPU Hot Spot", "GPU Memory Junction"]

# Fertige Gruppen zum Ausblenden: (Titel, Erklärung, Muster)
PRESETS = [
    ("D3D-Werte der Grafikkarte", "Auslastung und Speicher laut Windows (D3D 3D, D3D Copy, …) – meist fast alle 0 %.",
     ["D3D *"]),
    ("Einzelwerte pro CPU-Kern", "Last, Takt und Leistung jedes einzelnen Kerns; die Gesamtwerte bleiben sichtbar.",
     ["CPU Core #*", "Core #*"]),
    ("PCIe-Datenrate der Grafikkarte", "GPU PCIe Rx/Tx.", ["GPU PCIe *"]),
    ("Virtueller Arbeitsspeicher", "Werte inklusive Auslagerungsdatei.", ["Virtual Memory*"]),
    ("Lebenszeit-Datenmengen der Laufwerke", "Insgesamt gelesene und geschriebene Daten.", ["Data Read", "Data Written"]),
]
PRESET_PATTERNS = {p for _, _, patterns in PRESETS for p in patterns}


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


def set_enabled(button, enabled):
    """Knopf an/aus – ausgeschaltete Knöpfe werden grau, damit man den Unterschied sofort sieht."""
    button.configure(state="normal" if enabled else "disabled",
                     fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"] if enabled else BUTTON_OFF)


class HardwareMonitorPage(ToolPage):
    # ---------- Pfade ----------
    @property
    def folder(self):
        return self.app.tools_dir / "hardware_monitor"

    @property
    def script(self):
        return self.folder / "hardware_monitor.py"

    @property
    def settings_file(self):
        return self.folder / "hardware_monitor_settings.json"

    @property
    def task_name(self):
        return self.app.tool_settings("hardware_monitor").get("task_name", DEFAULT_TASK)

    # ---------- Aufbau ----------
    def build(self):
        self.visible = False
        self.poll_job = None
        self.save_job = None
        self.running_order = None
        self.data = self.load()
        small = ctk.CTkFont(size=12)

        # --- Status ---
        card = self.section("Status")
        line = ctk.CTkFrame(card, fg_color="transparent")
        line.grid(row=2, column=0, columnspan=3, sticky="ew", padx=18, pady=(0, 4))
        self.dot = ctk.CTkLabel(line, text="●", font=ctk.CTkFont(size=18), text_color=MUTED)
        self.dot.pack(side="left")
        self.status_label = ctk.CTkLabel(line, text="Prüfe …", font=ctk.CTkFont(size=14))
        self.status_label.pack(side="left", padx=(8, 0))
        buttons = ctk.CTkFrame(card, fg_color="transparent")
        buttons.grid(row=3, column=0, columnspan=3, sticky="w", padx=18, pady=(6, 16))
        self.start_button = ctk.CTkButton(buttons, text="Starten", width=110, command=self.start)
        self.start_button.pack(side="left", padx=(0, 8))
        self.stop_button = ctk.CTkButton(buttons, text="Beenden", width=110, command=self.stop)
        self.stop_button.pack(side="left", padx=(0, 8))
        self.restart_button = ctk.CTkButton(buttons, text="Neu starten", width=110, command=self.restart)
        self.restart_button.pack(side="left")
        self.status_hint = ctk.CTkLabel(card, text="", anchor="w", justify="left", wraplength=620, font=small,
                                        text_color=WARN)       # wird nur bei Bedarf eingeblendet

        # --- Autostart ---
        card = self.section("Autostart", "Startet den Hardware-Monitor beim Anmelden über die Aufgabenplanung "
                                         "(mit Adminrechten, ohne Nachfrage).")
        self.autostart = ctk.CTkSwitch(card, text="Beim Anmelden automatisch starten", command=self.toggle_autostart)
        self.autostart.grid(row=2, column=0, columnspan=2, sticky="w", padx=18, pady=4)
        self.task_button = ctk.CTkButton(card, text="Aufgabe einrichten", width=170, command=self.setup_task)
        self.task_button.grid(row=2, column=2, sticky="e", padx=18, pady=4)
        self.task_label = ctk.CTkLabel(card, text="", anchor="w", justify="left", wraplength=620, font=small,
                                       text_color=MUTED)
        self.task_label.grid(row=3, column=0, columnspan=3, sticky="ew", padx=18, pady=(0, 14))

        # --- Aktualisierung ---
        card = self.section("Aktualisierung", "Wie oft gemessen wird. Seltener = sparsamer. "
                                              "Die Icons lesen nur CPU und GPU, das geöffnete Fenster alles.")
        self.row_label(card, 2, "Taskleisten-Icons")
        self.icon_rate = ctk.CTkSegmentedButton(card, values=list(ICON_RATES), command=self.on_icon_rate)
        self.icon_rate.grid(row=2, column=1, sticky="w", pady=6)
        self.row_label(card, 3, "Detailfenster", pady=(6, 16))
        self.popup_rate = ctk.CTkSegmentedButton(card, values=list(POPUP_RATES), command=self.on_popup_rate)
        self.popup_rate.grid(row=3, column=1, sticky="w", pady=(6, 16))

        # --- Anzeige ---
        card = self.section("Anzeige")
        self.row_label(card, 2, "Reihenfolge der Icons")
        self.order = ctk.CTkSegmentedButton(card, values=list(ORDERS), command=self.on_order)
        self.order.grid(row=2, column=1, sticky="w", pady=6)
        self.order_hint = ctk.CTkLabel(card, text="", font=small, text_color=WARN, anchor="w")
        self.order_hint.grid(row=3, column=1, sticky="w")

        self.row_label(card, 4, "Sensor im CPU-Icon")
        self.cpu_sensor = ctk.CTkComboBox(card, values=CPU_CHOICES, width=240,
                                          command=lambda v: self.on_sensor("cpu_sensor", v))
        self.cpu_sensor.grid(row=4, column=1, sticky="w", pady=6)
        self.row_label(card, 5, "Sensor im GPU-Icon")
        self.gpu_sensor = ctk.CTkComboBox(card, values=GPU_CHOICES, width=240,
                                          command=lambda v: self.on_sensor("gpu_sensor", v))
        self.gpu_sensor.grid(row=5, column=1, sticky="w", pady=6)
        for box, key in ((self.cpu_sensor, "cpu_sensor"), (self.gpu_sensor, "gpu_sensor")):
            box.bind("<Return>", lambda e, b=box, k=key: self.on_sensor(k, b.get()))
            box.bind("<FocusOut>", lambda e, b=box, k=key: self.on_sensor(k, b.get()))
        ctk.CTkLabel(card, text="Eigene Namen kannst du eintippen (siehe hardware_monitor.py --list). "
                                "Gibt es den Sensor nicht, wird automatisch gewählt.",
                     font=small, text_color=MUTED, anchor="w", justify="left", wraplength=420).grid(
            row=6, column=1, sticky="w", pady=(0, 6))

        self.row_label(card, 7, "Farben")
        colors = ctk.CTkFrame(card, fg_color="transparent")
        colors.grid(row=7, column=1, columnspan=2, sticky="ew", pady=6)
        self.warn_label = ctk.CTkLabel(colors, text="", width=110, anchor="w", text_color=WARN)
        self.warn_label.grid(row=0, column=0, sticky="w")
        self.warn_slider = ctk.CTkSlider(colors, from_=40, to=100, number_of_steps=60, width=260,
                                         command=lambda v: self.on_threshold("warn_temp", v))
        self.warn_slider.grid(row=0, column=1, padx=8)
        self.hot_label = ctk.CTkLabel(colors, text="", width=110, anchor="w", text_color=BAD)
        self.hot_label.grid(row=1, column=0, sticky="w", pady=(6, 14))
        self.hot_slider = ctk.CTkSlider(colors, from_=41, to=110, number_of_steps=69, width=260,
                                        command=lambda v: self.on_threshold("hot_temp", v))
        self.hot_slider.grid(row=1, column=1, padx=8, pady=(6, 14))

        # --- Ausblenden ---
        card = self.section("Ausgeblendete Werte", "Diese Werte erscheinen im Detailfenster nicht mehr. "
                                                   "Die Taskleisten-Icons sind davon nicht betroffen.")
        self.preset_boxes = []
        row = 2
        for title, explanation, patterns in PRESETS:
            box = ctk.CTkCheckBox(card, text=title, command=self.on_hidden_changed)
            box.grid(row=row, column=0, columnspan=3, sticky="w", padx=18, pady=(6, 0))
            ctk.CTkLabel(card, text=explanation, font=small, text_color=MUTED, anchor="w").grid(
                row=row + 1, column=0, columnspan=3, sticky="w", padx=(50, 18))
            self.preset_boxes.append((box, patterns))
            row += 2
        ctk.CTkLabel(card, text="Eigene Muster – eins pro Zeile, * steht für beliebigen Text "
                                "(z. B.  GPU Video Engine  oder  Fan #*):", anchor="w", font=small).grid(
            row=row, column=0, columnspan=3, sticky="w", padx=18, pady=(14, 4))
        self.custom = ctk.CTkTextbox(card, height=90)
        self.custom.grid(row=row + 1, column=0, columnspan=3, sticky="ew", padx=18)
        ctk.CTkButton(card, text="Muster übernehmen", width=160, command=self.on_hidden_changed).grid(
            row=row + 2, column=0, columnspan=3, sticky="w", padx=18, pady=(8, 16))

        # --- Erweitert ---
        card = self.section("Erweitert")
        self.row_label(card, 2, "Name der Aufgabe")
        self.task_entry = ctk.CTkEntry(card, width=240)
        self.task_entry.insert(0, self.task_name)
        self.task_entry.grid(row=2, column=1, sticky="w", pady=6)
        self.task_entry.bind("<Return>", lambda e: self.on_task_name())
        self.task_entry.bind("<FocusOut>", lambda e: self.on_task_name())
        links = ctk.CTkFrame(card, fg_color="transparent")
        links.grid(row=3, column=0, columnspan=3, sticky="w", padx=18, pady=(8, 16))
        for text, path in (("Ordner öffnen", lambda: self.folder),
                           ("Log öffnen", lambda: self.folder / "hardware_monitor.log"),
                           ("Einstellungsdatei öffnen", lambda: self.settings_file)):
            ctk.CTkButton(links, text=text, width=150, fg_color=("gray70", "gray30"),
                          hover_color=("gray60", "gray35"),
                          command=lambda p=path: self.open_path(p())).pack(side="left", padx=(0, 8))
        ctk.CTkButton(links, text="Alles zurücksetzen", width=150, fg_color="transparent", border_width=1,
                      text_color=("gray20", "gray85"), command=self.reset).pack(side="left")

        self.fill_widgets()

    # ---------- Einstellungen lesen / schreiben ----------
    def load(self):
        data = json.loads(json.dumps(DEFAULTS))
        try:
            saved = json.loads(self.settings_file.read_text(encoding="utf-8"))
            if isinstance(saved, dict):
                data.update(saved)               # unbekannte Schlüssel bleiben erhalten
        except (OSError, ValueError):
            pass
        return data

    def save(self):
        """Datei schreiben und hardware_monitor (falls es läuft) die neuen Werte laden lassen."""
        try:
            self.settings_file.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError as error:
            self.app.toast(f"Speichern fehlgeschlagen: {error.strerror or error}", error=True)
            return
        self.app.run_async(lambda: ipc("reload"))
        self.app.toast("Gespeichert ✓")

    def save_later(self, delay=500):
        """Bei Schiebereglern nicht bei jedem Pixel speichern, sondern kurz nach dem Loslassen."""
        if self.save_job:
            self.after_cancel(self.save_job)
        self.save_job = self.after(delay, self.save)

    def fill_widgets(self):
        """Alle Bedienelemente auf die Werte in self.data setzen (löst keine Speicherung aus)."""
        d = self.data
        self.icon_rate.set(next((k for k, v in ICON_RATES.items() if v == d["icon_interval"]), "2 s"))
        self.popup_rate.set(next((k for k, v in POPUP_RATES.items() if v == d["popup_interval"]), "1 s"))
        self.order.set(next((k for k, v in ORDERS.items() if v == d["icon_order"]), "CPU zuerst"))
        self.cpu_sensor.set(AUTO if d["cpu_sensor"] == "auto" else d["cpu_sensor"])
        self.gpu_sensor.set(AUTO if d["gpu_sensor"] == "auto" else d["gpu_sensor"])
        self.warn_slider.set(d["warn_temp"])
        self.hot_slider.set(d["hot_temp"])
        self.update_threshold_labels()
        hidden = set(d["hidden"])
        for box, patterns in self.preset_boxes:
            box.select() if set(patterns) <= hidden else box.deselect()
        self.custom.delete("1.0", "end")
        self.custom.insert("1.0", "\n".join(p for p in d["hidden"] if p not in PRESET_PATTERNS))
        self.update_order_hint()

    # ---------- Reaktionen auf Bedienung ----------
    def on_icon_rate(self, label):
        self.data["icon_interval"] = ICON_RATES[label]
        self.save()

    def on_popup_rate(self, label):
        self.data["popup_interval"] = POPUP_RATES[label]
        self.save()

    def on_order(self, label):
        self.data["icon_order"] = ORDERS[label]
        self.save()
        self.update_order_hint()

    def on_sensor(self, key, value):
        value = value.strip()
        value = "auto" if not value or value == AUTO else value
        if self.data[key] != value:
            self.data[key] = value
            self.save()

    def on_threshold(self, key, value):
        value = int(round(value))
        self.data[key] = value
        # gelb muss immer unter rot liegen – den anderen Regler notfalls mitziehen
        if self.data["warn_temp"] >= self.data["hot_temp"]:
            if key == "warn_temp":
                self.data["hot_temp"] = value + 1
                self.hot_slider.set(value + 1)
            else:
                self.data["warn_temp"] = value - 1
                self.warn_slider.set(value - 1)
        self.update_threshold_labels()
        self.save_later()

    def update_threshold_labels(self):
        self.warn_label.configure(text=f"Gelb ab {self.data['warn_temp']} °C")
        self.hot_label.configure(text=f"Rot ab {self.data['hot_temp']} °C")

    def on_hidden_changed(self):
        hidden = []
        for box, patterns in self.preset_boxes:
            if box.get():
                hidden += patterns
        for line in self.custom.get("1.0", "end").splitlines():
            if line.strip() and line.strip() not in hidden:
                hidden.append(line.strip())
        self.data["hidden"] = hidden
        self.save()

    def on_task_name(self):
        name = self.task_entry.get().strip() or DEFAULT_TASK
        if name != self.task_name:
            self.app.tool_settings("hardware_monitor")["task_name"] = name
            self.app.save()
            self.refresh_task()

    def reset(self):
        self.data = json.loads(json.dumps(DEFAULTS))
        self.fill_widgets()
        self.save()

    def open_path(self, path):
        try:
            os.startfile(path)                   # öffnet mit dem passenden Programm (nur Windows)
        except (OSError, AttributeError):
            self.app.toast(f"Nicht gefunden: {Path(path).name}", error=True)

    # ---------- Status und Steuerung ----------
    def on_show(self):
        if self.visible:
            return
        self.visible = True
        self.data = self.load()                  # z. B. per Rechtsklick-Menü geänderte Raten übernehmen
        self.fill_widgets()
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

    def show_status(self, status):
        running = status is not None and status.get("ok")
        if running:
            self.dot.configure(text_color=GOOD)
            self.status_label.configure(text=f"Läuft  ·  CPU {fmt_temp(status.get('cpu'))}  ·  "
                                             f"GPU {fmt_temp(status.get('gpu'))}")
            self.running_order = status.get("order")
        else:
            self.dot.configure(text_color=MUTED)
            self.status_label.configure(text="Gestoppt")
            self.running_order = None
        set_enabled(self.start_button, not running)
        set_enabled(self.stop_button, running)
        set_enabled(self.restart_button, running)
        if not self.script.exists():
            self.status_hint.configure(text=f"⚠  {self.script} nicht gefunden – Programm-Ordner im Zahnrad prüfen.")
            self.status_hint.grid(row=4, column=0, columnspan=3, sticky="ew", padx=18, pady=(0, 14))
        else:
            self.status_hint.grid_remove()
        self.update_order_hint()

    def update_order_hint(self):
        changed = self.running_order is not None and self.running_order != self.data["icon_order"]
        self.order_hint.configure(text="Wird nach „Neu starten“ übernommen" if changed else "")

    def start(self):
        if not self.script.exists():
            self.app.toast("hardware_monitor.py nicht gefunden", error=True)
            return
        self.status_label.configure(text="Wird gestartet …")
        self.start_button.configure(state="disabled")
        task, script = self.task_name, self.script

        def work():
            info = winutil.task_info(task)
            usable = info and info.get("state") != "Disabled" and self.task_points_here(info)
            if usable and winutil.run_task(task):
                return "task"
            # Keine passende aktive Aufgabe -> direkt mit Adminrechten starten; Windows fragt per UAC nach
            ok = winutil.run_elevated(winutil.pythonw_exe(), f'"{script}"', cwd=str(script.parent))
            return "direct" if ok else None

        def done(result):
            if result is None:
                self.app.toast("Start abgebrochen oder fehlgeschlagen", error=True)
            self.poll_status_soon()

        self.app.run_async(work, done)

    def stop(self):
        self.status_label.configure(text="Wird beendet …")
        self.app.run_async(lambda: ipc("quit"), lambda result: self.poll_status_soon())

    def restart(self):
        self.status_label.configure(text="Wird neu gestartet …")

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

    def poll_status_soon(self):
        """Nach Start/Stopp ein paar Mal schnell nachsehen, statt 2 Sekunden zu warten."""
        for delay in (400, 1200, 2500):
            self.after(delay, lambda: self.app.run_async(lambda: ipc("status"), self.show_status))

    # ---------- Autostart ----------
    def refresh_task(self):
        task = self.task_name
        self.autostart.configure(state="disabled")
        self.task_label.configure(text=f"Prüfe Aufgabe „{task}“ …", text_color=MUTED)
        self.app.run_async(lambda: winutil.task_info(task), self.show_task)

    def task_points_here(self, info):
        """Startet die Aufgabe wirklich dieses hardware_monitor.py (und nicht z. B. eine alte Kopie unter C:\\Tools)?"""
        arguments = (info.get("arguments") or "").strip().strip('"')
        return Path(arguments).resolve() == self.script.resolve() if arguments else False

    def show_task(self, info):
        task = self.task_name
        if info is None:
            self.autostart.deselect()
            self.autostart.configure(state="disabled")
            self.task_button.configure(text="Aufgabe einrichten")
            self.task_label.configure(text=f"Aufgabe „{task}“ gibt es noch nicht. „Aufgabe einrichten“ legt sie an "
                                           f"(Windows fragt einmal nach Adminrechten).", text_color=WARN)
            return
        enabled = info.get("state") != "Disabled"
        self.autostart.configure(state="normal")
        self.autostart.select() if enabled else self.autostart.deselect()
        if self.task_points_here(info):
            self.task_button.configure(text="Neu einrichten")
            self.task_label.configure(text=f"Aufgabe „{task}“ in der Aufgabenplanung "
                                           f"({'aktiv' if enabled else 'deaktiviert'})", text_color=MUTED)
        else:
            self.task_button.configure(text="Aufgabe aktualisieren")
            self.task_label.configure(text=f"⚠  Aufgabe „{task}“ startet einen anderen Ort: {info.get('arguments')}\n"
                                           f"„Aufgabe aktualisieren“ stellt sie auf {self.script} um.",
                                      text_color=WARN)

    def setup_task(self):
        if not self.script.exists():
            self.app.toast("hardware_monitor.py nicht gefunden", error=True)
            return
        task, script = self.task_name, self.script
        self.task_button.configure(state="disabled")
        self.task_label.configure(text="Richte Aufgabe ein … (bitte die Windows-Abfrage bestätigen)", text_color=MUTED)

        def done(ok):
            self.task_button.configure(state="normal")
            self.app.toast("Aufgabe eingerichtet ✓" if ok else "Einrichten fehlgeschlagen oder abgebrochen",
                           error=not ok)
            self.refresh_task()

        self.app.run_async(lambda: winutil.register_task(task, script), done)

    def toggle_autostart(self):
        enabled = bool(self.autostart.get())
        task = self.task_name
        self.autostart.configure(state="disabled")

        def done(ok):
            if not ok:
                self.app.toast("Ändern fehlgeschlagen oder abgebrochen", error=True)
            self.refresh_task()

        self.app.run_async(lambda: winutil.set_task_enabled(task, enabled), done)
