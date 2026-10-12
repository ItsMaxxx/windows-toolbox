"""
Kleine Windows-Helfer für die Toolbox: Befehle ohne aufblitzendes Konsolenfenster ausführen,
Programme mit Adminrechten starten (UAC-Abfrage) und Aufgaben in der Aufgabenplanung steuern.
"""

import base64
import ctypes
import json
import subprocess
import sys
from ctypes import wintypes
from pathlib import Path

CREATE_NO_WINDOW = 0x08000000           # verhindert, dass bei jedem Aufruf kurz eine Konsole aufblitzt


def run_hidden(args, timeout=20):
    """Führt einen Befehl unsichtbar aus. Gibt das Ergebnis zurück oder None, wenn das Programm fehlt."""
    try:
        # Konsolenprogramme (PowerShell, schtasks) schreiben in der OEM-Codepage (cp850: "Überprüfen"),
        # nicht in cp1252 – sonst bricht das Lesen der Ausgabe bei Umlauten ab
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout, encoding="oem",
                              errors="replace", creationflags=CREATE_NO_WINDOW)
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


def wait_for_exit(pid, timeout=10):
    """Wartet, bis der Prozess pid beendet ist – höchstens timeout Sekunden.
    True = beendet (oder gab es gar nicht), False = läuft noch oder Warten nicht möglich.

    Wichtig vor einem Neustart: Ein Programm antwortet oft schon nicht mehr, räumt aber noch auf. Solange es lebt,
    hält es seine .exe gesperrt und seinen „läuft schon“-Schutz (Mutex bzw. Port) – ein neuer Start würde sich
    sofort wieder beenden. Klappt auch bei Programmen mit Adminrechten (z. B. dem Hardware-Monitor).
    """
    if not pid:
        return False
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.restype = wintypes.HANDLE
    handle = kernel32.OpenProcess(0x00100000, False, int(pid))         # SYNCHRONIZE: nur darauf warten dürfen
    if not handle:
        return ctypes.get_last_error() == 87                            # ERROR_INVALID_PARAMETER: gibt es nicht
    try:
        return kernel32.WaitForSingleObject(wintypes.HANDLE(handle), int(timeout * 1000)) == 0
    finally:
        kernel32.CloseHandle(wintypes.HANDLE(handle))


# ---------- Mit Adminrechten starten ----------
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
    Gibt False zurück, wenn die Abfrage abgelehnt wurde.
    """
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


def task_command(name, exe, cwd=None):
    """PowerShell-Befehl, der die Aufgabe "beim Anmelden mit Adminrechten starten" anlegt oder überschreibt.

    Entspricht dem, was man sonst von Hand in der Aufgabenplanung einstellt: Trigger "Bei Anmeldung",
    "Mit höchsten Privilegien", auch im Akkubetrieb, ohne die 3-Tage-Zeitbegrenzung.
    exe: das gestartete Programm, z. B. der Starter HardwareMonitor.exe (braucht keine Argumente).
    cwd: Arbeitsordner (Standard: Ordner von exe).
    Autostart: Gab es die Aufgabe noch nicht (erstes Einrichten) oder war sie ausgeschaltet, wird sie gleich wieder
    ausgeschaltet – Windows legt sie sonst immer aktiv an. Nur eine Aufgabe, die schon an war, bleibt an.
    Braucht Adminrechte – register_task() holt sie per UAC; setup\\setup.ps1 ruft es schon mit Adminrechten auf.
    """
    lines = [
        "$ErrorActionPreference = 'Stop'",
        f"$alt = Get-ScheduledTask -TaskName {ps_quote(name)} -ErrorAction SilentlyContinue",
        '$user = "$env:USERDOMAIN\\$env:USERNAME"',
        f"$action = New-ScheduledTaskAction -Execute {ps_quote(str(exe))} "
        f"-WorkingDirectory {ps_quote(str(cwd or Path(exe).parent))}",
        "$trigger = New-ScheduledTaskTrigger -AtLogOn -User $user",
        "$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Highest",
        "$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries "
        "-ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew",
        f"Register-ScheduledTask -TaskName {ps_quote(name)} -Action $action -Trigger $trigger "
        "-Principal $principal -Settings $settings -Force | Out-Null",
        f"if (-not $alt -or $alt.State -eq 'Disabled') {{ Disable-ScheduledTask -TaskName {ps_quote(name)} | Out-Null }}",
    ]
    return "\n".join(lines)


def powershell_elevated(command):
    """PowerShell-Befehl mit Adminrechten ausführen (UAC-Abfrage) und aufs Ende warten. True = hat geklappt."""
    # Als Base64 übergeben, damit Anführungszeichen und Leerzeichen in Pfaden keine Probleme machen
    encoded = base64.b64encode(command.encode("utf-16-le")).decode("ascii")
    return run_elevated("powershell.exe", f"-NoProfile -NonInteractive -WindowStyle Hidden -EncodedCommand {encoded}",
                        wait=True)


def register_task(name, exe, cwd=None):
    """Legt die Aufgabe an oder überschreibt sie (siehe task_command) – mit UAC-Abfrage."""
    return powershell_elevated(task_command(name, exe, cwd))


def set_task_enabled(name, enabled):
    """Aufgabe aktivieren/deaktivieren. Klappt es ohne Adminrechte nicht, kommt die UAC-Abfrage."""
    verb = "Enable" if enabled else "Disable"
    command = f"{verb}-ScheduledTask -TaskName {ps_quote(name)} -ErrorAction Stop | Out-Null"
    result = powershell(command)
    if result is not None and result.returncode == 0:
        return True
    return powershell_elevated(command)


def run_task(name):
    """Startet eine geplante Aufgabe (läuft mit den dort eingestellten Rechten, ohne UAC-Abfrage)."""
    result = run_hidden(["schtasks.exe", "/run", "/tn", name])
    return result is not None and result.returncode == 0


# ---------- Autostart ohne Adminrechte ----------
# Für Programme, die keine Adminrechte brauchen (z. B. Discord Plus), reicht ein Eintrag unter HKCU\...\Run – den
# darf jeder Benutzer selbst setzen, ganz ohne UAC-Abfrage. Der Hardware-Monitor braucht Adminrechte und startet
# deshalb über die Aufgabenplanung (siehe oben).
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
# Hier merkt sich Windows, wenn man den Eintrag im Task-Manager unter „Autostart“ deaktiviert hat
RUN_ERLAUBT_KEY = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"


def autostart_info(name):
    """{"ziel": gestarteter Befehl, "an": bool} – oder None, wenn es den Eintrag name nicht gibt.
    "an" ist False, wenn der Eintrag im Task-Manager unter „Autostart“ deaktiviert wurde."""
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            ziel = winreg.QueryValueEx(k, name)[0]
    except OSError:
        return None
    an = True
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_ERLAUBT_KEY) as k:
            wert = winreg.QueryValueEx(k, name)[0]
            an = not (isinstance(wert, bytes) and wert and wert[0] & 1)    # 02 = erlaubt, 03 = deaktiviert
    except OSError:
        pass
    return {"ziel": ziel, "an": an}


def autostart_setzen(name, exe=None):
    """Beim Anmelden exe starten – oder mit exe=None den Eintrag löschen. True, wenn es geklappt hat.
    Ein im Task-Manager deaktivierter Eintrag wird dabei wieder erlaubt."""
    import winreg
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            if exe:
                winreg.SetValueEx(k, name, 0, winreg.REG_SZ, f'"{exe}"')
            else:
                try:
                    winreg.DeleteValue(k, name)
                except FileNotFoundError:
                    pass
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_ERLAUBT_KEY, 0, winreg.KEY_SET_VALUE) as k:
                winreg.DeleteValue(k, name)
        except FileNotFoundError:
            pass
        return True
    except OSError:
        return False


# ---------- Toolbox auf der Seite eines Programms öffnen ----------
ROOT = Path(__file__).resolve().parents[1]
TOOLBOX_PORT = json.loads((ROOT / "toolbox" / "programm.json").read_text(encoding="utf-8"))["port"]


def toolbox_befehl(befehl):
    """Schickt der laufenden Toolbox einen Befehl (siehe instance_server in toolbox.py). True, wenn sie „ok“ sagt."""
    import socket
    try:
        with socket.create_connection(("127.0.0.1", TOOLBOX_PORT), timeout=0.5) as conn:
            conn.sendall(f"{befehl}\n".encode())
            return conn.recv(16).startswith(b"ok")
    except OSError:
        return False


def toolbox_oeffnen(programm_id):
    """Die Seite eines Programms in der Toolbox zeigen – blockiert bis zu 15 s, also im Hintergrund aufrufen.
    Läuft die Toolbox, genügt „show <programm_id>“; sonst wird sie gestartet und bekommt den Befehl, sobald sie
    antwortet. True, wenn die Toolbox die Seite zeigt. (Wie toolbox_oeffnen in detailfenster.py.)"""
    import time
    ctypes.windll.user32.AllowSetForegroundWindow(-1)  # ASFW_ANY: die Toolbox darf ihr Fenster nach vorne holen
    befehl = f"show {programm_id}"
    if toolbox_befehl(befehl):
        return True
    starter = ROOT / "Toolbox.exe"
    try:
        # über explorer.exe: startet sie als normales Programm, auch wenn der Aufrufer Adminrechte hat
        subprocess.Popen(["explorer.exe", str(starter)])
    except OSError:
        return False
    for _ in range(60):
        time.sleep(0.25)
        if toolbox_befehl(befehl):
            return True
    return False
