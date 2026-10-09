"""
Kleine Windows-Helfer für die Toolbox: Befehle ohne aufblitzendes Konsolenfenster ausführen,
Programme mit Adminrechten starten (UAC-Abfrage) und Aufgaben in der Aufgabenplanung steuern.

Außerhalb von Windows geben die Funktionen einfach None/False zurück, statt abzustürzen.
"""

import base64
import ctypes
import json
import subprocess
import sys
from pathlib import Path

CREATE_NO_WINDOW = 0x08000000           # verhindert, dass bei jedem Aufruf kurz eine Konsole aufblitzt


def run_hidden(args, timeout=20):
    """Führt einen Befehl unsichtbar aus. Gibt das Ergebnis zurück oder None, wenn das Programm fehlt."""
    windows = sys.platform == "win32"
    try:
        # Konsolenprogramme (PowerShell, schtasks) schreiben in der OEM-Codepage (cp850: "Überprüfen"),
        # nicht in cp1252 – sonst bricht das Lesen der Ausgabe bei Umlauten ab
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                              encoding="oem" if windows else None, errors="replace",
                              creationflags=CREATE_NO_WINDOW if windows else 0)
    except (OSError, subprocess.TimeoutExpired):
        return None


def powershell(command, timeout=20):
    return run_hidden(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command], timeout)


def ps_quote(text):
    """Text sicher in einfache Anführungszeichen für PowerShell setzen."""
    return "'" + text.replace("'", "''") + "'"


def pythonw_exe():
    """Pfad zu pythonw.exe (Python ohne Konsolenfenster) der gerade laufenden Python-Installation."""
    candidate = Path(sys.executable).with_name("pythonw.exe")
    return str(candidate if candidate.exists() else sys.executable)


# ---------- Mit Adminrechten starten ----------
if sys.platform == "win32":
    from ctypes import wintypes

    class SHELLEXECUTEINFOW(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD), ("fMask", ctypes.c_ulong), ("hwnd", wintypes.HWND),
            ("lpVerb", wintypes.LPCWSTR), ("lpFile", wintypes.LPCWSTR), ("lpParameters", wintypes.LPCWSTR),
            ("lpDirectory", wintypes.LPCWSTR), ("nShow", ctypes.c_int), ("hInstApp", wintypes.HINSTANCE),
            ("lpIDList", ctypes.c_void_p), ("lpClass", wintypes.LPCWSTR), ("hkeyClass", wintypes.HKEY),
            ("dwHotKey", wintypes.DWORD), ("hIconOrMonitor", wintypes.HANDLE), ("hProcess", wintypes.HANDLE),
        ]


def run_elevated(file, params="", cwd=None, wait=False, timeout_ms=60000):
    """Startet ein Programm mit Adminrechten – Windows zeigt dafür die UAC-Abfrage.

    wait=True wartet aufs Ende und meldet, ob es erfolgreich war (Exitcode 0).
    Gibt False zurück, wenn die Abfrage abgelehnt wurde oder es nicht unter Windows läuft.
    """
    if sys.platform != "win32":
        return False
    info = SHELLEXECUTEINFOW()
    info.cbSize = ctypes.sizeof(info)
    info.fMask = 0x00000040                      # SEE_MASK_NOCLOSEPROCESS: Prozess-Handle zurückgeben
    info.lpVerb = "runas"                        # "als Administrator ausführen"
    info.lpFile = file
    info.lpParameters = params
    info.lpDirectory = cwd
    info.nShow = 0                               # SW_HIDE
    if not ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(info)):
        return False
    if not info.hProcess:
        return True
    try:
        if not wait:
            return True
        ctypes.windll.kernel32.WaitForSingleObject(info.hProcess, timeout_ms)
        code = wintypes.DWORD()
        ctypes.windll.kernel32.GetExitCodeProcess(info.hProcess, ctypes.byref(code))
        return code.value == 0
    finally:
        ctypes.windll.kernel32.CloseHandle(info.hProcess)


# ---------- Aufgabenplanung ----------
def task_info(name):
    """Infos zu einer geplanten Aufgabe oder None, wenn es sie nicht gibt:
    {"state": "Ready"/"Running"/"Disabled"/…, "execute": Programm, "arguments": Argumente}

    PowerShell liefert den Zustand unabhängig von der Windows-Sprache – schtasks dagegen würde
    auf deutschem Windows "Bereit"/"Deaktiviert" ausgeben, was sich schlecht auswerten lässt.
    """
    command = (f"$t = Get-ScheduledTask -TaskName {ps_quote(name)} -ErrorAction Stop; "
               "@{state = \"$($t.State)\"; execute = $t.Actions[0].Execute; "
               "arguments = $t.Actions[0].Arguments} | ConvertTo-Json -Compress")
    result = powershell(command)
    if result is None or result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except ValueError:
        return None


def task_state(name):
    info = task_info(name)
    return info["state"] if info else None


def task_command(name, script, exe=None):
    """PowerShell-Befehl, der die Aufgabe "beim Anmelden mit Adminrechten starten" anlegt oder überschreibt.

    Entspricht dem, was man sonst von Hand in der Aufgabenplanung einstellt: Trigger "Bei Anmeldung",
    "Mit höchsten Privilegien", auch im Akkubetrieb, ohne die 3-Tage-Zeitbegrenzung.
    exe: Programm, das das Skript ausführt (Standard: pythonw.exe des laufenden Pythons).
    Braucht Adminrechte – register_task() holt sie per UAC; setup\setup.ps1 ruft es schon mit Adminrechten auf.
    """
    script = Path(script)
    lines = [
        "$ErrorActionPreference = 'Stop'",
        '$user = "$env:USERDOMAIN\\$env:USERNAME"',
        f"$action = New-ScheduledTaskAction -Execute {ps_quote(str(exe or pythonw_exe()))} "
        f"-Argument {ps_quote(chr(34) + str(script) + chr(34))} -WorkingDirectory {ps_quote(str(script.parent))}",
        "$trigger = New-ScheduledTaskTrigger -AtLogOn -User $user",
        "$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Highest",
        "$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries "
        "-ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew",
        f"Register-ScheduledTask -TaskName {ps_quote(name)} -Action $action -Trigger $trigger "
        "-Principal $principal -Settings $settings -Force | Out-Null",
    ]
    return "\n".join(lines)


def register_task(name, script, exe=None):
    """Legt die Aufgabe an oder überschreibt sie (siehe task_command) – mit UAC-Abfrage."""
    # Als Base64 übergeben, damit Anführungszeichen und Leerzeichen in Pfaden keine Probleme machen
    encoded = base64.b64encode(task_command(name, script, exe).encode("utf-16-le")).decode("ascii")
    return run_elevated("powershell.exe", f"-NoProfile -NonInteractive -WindowStyle Hidden -EncodedCommand {encoded}",
                        wait=True)


def set_task_enabled(name, enabled):
    """Aufgabe aktivieren/deaktivieren. Klappt es ohne Adminrechte nicht, kommt die UAC-Abfrage."""
    verb = "Enable" if enabled else "Disable"
    command = f"{verb}-ScheduledTask -TaskName {ps_quote(name)} -ErrorAction Stop | Out-Null"
    result = powershell(command)
    if result is not None and result.returncode == 0:
        return True
    return run_elevated("powershell.exe",
                        f'-NoProfile -NonInteractive -WindowStyle Hidden -Command "{command}"', wait=True)


def run_task(name):
    """Startet eine geplante Aufgabe (läuft mit den dort eingestellten Rechten, ohne UAC-Abfrage)."""
    result = run_hidden(["schtasks.exe", "/run", "/tn", name])
    return result is not None and result.returncode == 0
