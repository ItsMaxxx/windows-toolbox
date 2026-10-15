"""
Small Windows helpers for the Toolbox: run commands without a flashing console window,
start programs with admin rights (UAC prompt) and control tasks in the Task Scheduler.
"""

import base64
import ctypes
import json
import subprocess
import sys
from ctypes import wintypes
from pathlib import Path

CREATE_NO_WINDOW = 0x08000000           # prevents a console from flashing up briefly on every call


def run_hidden(args, timeout=20):
    """Runs a command invisibly. Returns the result or None if the program is missing."""
    try:
        # Console programs (PowerShell, schtasks) write in the OEM code page (cp850: "Überprüfen"),
        # not in cp1252 – otherwise reading the output breaks on umlauts
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout, encoding="oem",
                              errors="replace", creationflags=CREATE_NO_WINDOW)
    except (OSError, subprocess.TimeoutExpired):
        return None


def powershell(command, timeout=20):
    return run_hidden(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command], timeout)


def ps_quote(text):
    """Put text safely into single quotes for PowerShell."""
    return "'" + text.replace("'", "''") + "'"


def pythonw_exe():
    """Path to pythonw.exe (Python without a console window) of the currently running Python installation."""
    candidate = Path(sys.executable).with_name("pythonw.exe")
    return str(candidate if candidate.exists() else sys.executable)


def wait_for_exit(pid, timeout=10):
    """Waits until the process pid has ended – at most timeout seconds.
    True = ended (or never existed), False = still running or waiting not possible.

    Important before a restart: a program often stops answering but is still cleaning up. As long as it lives,
    it keeps its .exe locked and its "already running" guard (mutex or port) – a new start would quit again
    immediately. Also works for programs with admin rights (e.g. the Hardware Monitor).
    """
    if not pid:
        return False
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.restype = wintypes.HANDLE
    handle = kernel32.OpenProcess(0x00100000, False, int(pid))         # SYNCHRONIZE: only allowed to wait for it
    if not handle:
        return ctypes.get_last_error() == 87                            # ERROR_INVALID_PARAMETER: doesn't exist
    try:
        return kernel32.WaitForSingleObject(wintypes.HANDLE(handle), int(timeout * 1000)) == 0
    finally:
        kernel32.CloseHandle(wintypes.HANDLE(handle))


# ---------- Start with admin rights ----------
class SHELLEXECUTEINFOW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD), ("fMask", ctypes.c_ulong), ("hwnd", wintypes.HWND),
        ("lpVerb", wintypes.LPCWSTR), ("lpFile", wintypes.LPCWSTR), ("lpParameters", wintypes.LPCWSTR),
        ("lpDirectory", wintypes.LPCWSTR), ("nShow", ctypes.c_int), ("hInstApp", wintypes.HINSTANCE),
        ("lpIDList", ctypes.c_void_p), ("lpClass", wintypes.LPCWSTR), ("hkeyClass", wintypes.HKEY),
        ("dwHotKey", wintypes.DWORD), ("hIconOrMonitor", wintypes.HANDLE), ("hProcess", wintypes.HANDLE),
    ]


def run_elevated(file, params="", cwd=None, wait=False, timeout_ms=60000):
    """Starts a program with admin rights – Windows shows the UAC prompt for it.

    wait=True waits for the end and reports whether it succeeded (exit code 0).
    Returns False if the prompt was declined.
    """
    info = SHELLEXECUTEINFOW()
    info.cbSize = ctypes.sizeof(info)
    info.fMask = 0x00000040                      # SEE_MASK_NOCLOSEPROCESS: return the process handle
    info.lpVerb = "runas"                        # "run as administrator"
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


# ---------- Task Scheduler ----------
def task_info(name):
    """Info about a scheduled task or None if it doesn't exist:
    {"state": "Ready"/"Running"/"Disabled"/…, "execute": program, "arguments": arguments}

    PowerShell returns the state independent of the Windows language – schtasks on the other hand would
    print "Bereit"/"Deaktiviert" on a German Windows, which is hard to evaluate.
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
    """PowerShell command that creates or overwrites the task "start at logon with admin rights".

    Matches what you would otherwise set by hand in the Task Scheduler: trigger "At log on",
    "Run with highest privileges", also on battery, without the 3-day time limit.
    exe: the started program, e.g. the starter HardwareMonitor.exe (needs no arguments).
    cwd: working folder (default: folder of exe).
    Autostart: if the task didn't exist yet (first setup) or was disabled, it gets disabled again right away –
    Windows otherwise always creates it enabled. Only a task that was already on stays on.
    Needs admin rights – register_task() gets them via UAC; setup\\setup.ps1 already calls it with admin rights.
    """
    lines = [
        "$ErrorActionPreference = 'Stop'",
        f"$old = Get-ScheduledTask -TaskName {ps_quote(name)} -ErrorAction SilentlyContinue",
        '$user = "$env:USERDOMAIN\\$env:USERNAME"',
        f"$action = New-ScheduledTaskAction -Execute {ps_quote(str(exe))} "
        f"-WorkingDirectory {ps_quote(str(cwd or Path(exe).parent))}",
        "$trigger = New-ScheduledTaskTrigger -AtLogOn -User $user",
        "$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Highest",
        "$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries "
        "-ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew",
        f"Register-ScheduledTask -TaskName {ps_quote(name)} -Action $action -Trigger $trigger "
        "-Principal $principal -Settings $settings -Force | Out-Null",
        f"if (-not $old -or $old.State -eq 'Disabled') {{ Disable-ScheduledTask -TaskName {ps_quote(name)} | Out-Null }}",
    ]
    return "\n".join(lines)


def powershell_elevated(command):
    """Run a PowerShell command with admin rights (UAC prompt) and wait for the end. True = worked."""
    # Passed as Base64 so that quotes and spaces in paths don't cause problems
    encoded = base64.b64encode(command.encode("utf-16-le")).decode("ascii")
    return run_elevated("powershell.exe", f"-NoProfile -NonInteractive -WindowStyle Hidden -EncodedCommand {encoded}",
                        wait=True)


def register_task(name, exe, cwd=None):
    """Creates or overwrites the task (see task_command) – with UAC prompt."""
    return powershell_elevated(task_command(name, exe, cwd))


def set_task_enabled(name, enabled):
    """Enable/disable a task. If it doesn't work without admin rights, the UAC prompt comes."""
    verb = "Enable" if enabled else "Disable"
    command = f"{verb}-ScheduledTask -TaskName {ps_quote(name)} -ErrorAction Stop | Out-Null"
    result = powershell(command)
    if result is not None and result.returncode == 0:
        return True
    return powershell_elevated(command)


def run_task(name):
    """Starts a scheduled task (runs with the rights set there, without UAC prompt)."""
    result = run_hidden(["schtasks.exe", "/run", "/tn", name])
    return result is not None and result.returncode == 0


# ---------- Autostart without admin rights ----------
# For programs that don't need admin rights (e.g. Discord Plus), an entry under HKCU\...\Run is enough – every user
# may set it themselves, without any UAC prompt. The Hardware Monitor needs admin rights and therefore starts
# via the Task Scheduler (see above).
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
# This is where Windows remembers if you disabled the entry in the Task Manager under "Startup apps"
RUN_APPROVED_KEY = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"


def autostart_info(name):
    """{"target": started command, "enabled": bool} – or None if the entry name doesn't exist.
    "enabled" is False if the entry was disabled in the Task Manager under "Startup apps"."""
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            target = winreg.QueryValueEx(k, name)[0]
    except OSError:
        return None
    enabled = True
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_APPROVED_KEY) as k:
            value = winreg.QueryValueEx(k, name)[0]
            enabled = not (isinstance(value, bytes) and value and value[0] & 1)    # 02 = allowed, 03 = disabled
    except OSError:
        pass
    return {"target": target, "enabled": enabled}


def set_autostart(name, exe=None):
    """Start exe at logon – or delete the entry with exe=None. True if it worked.
    An entry disabled in the Task Manager is allowed again in the process."""
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
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_APPROVED_KEY, 0, winreg.KEY_SET_VALUE) as k:
                winreg.DeleteValue(k, name)
        except FileNotFoundError:
            pass
        return True
    except OSError:
        return False


# ---------- Open the Toolbox on a program's page ----------
ROOT = Path(__file__).resolve().parents[1]
TOOLBOX_PORT = json.loads((ROOT / "toolbox" / "program.json").read_text(encoding="utf-8"))["port"]


def toolbox_command(command):
    """Sends a command to the running Toolbox (see instance_server in toolbox.py). True if it says "ok"."""
    import socket
    try:
        with socket.create_connection(("127.0.0.1", TOOLBOX_PORT), timeout=0.5) as conn:
            conn.sendall(f"{command}\n".encode())
            return conn.recv(16).startswith(b"ok")
    except OSError:
        return False


def open_toolbox(program_id):
    """Show a program's page in the Toolbox – blocks for up to 15 s, so call it in the background.
    If the Toolbox is running, "show <program_id>" is enough; otherwise it is started and gets the command as soon as
    it answers. True if the Toolbox shows the page. (Like open_toolbox in detail_window.py.)"""
    import time
    ctypes.windll.user32.AllowSetForegroundWindow(-1)  # ASFW_ANY: the Toolbox may bring its window to the front
    command = f"show {program_id}"
    if toolbox_command(command):
        return True
    starter = ROOT / "Toolbox.exe"
    try:
        # via explorer.exe: starts it as a normal program, even if the caller has admin rights
        subprocess.Popen(["explorer.exe", str(starter)])
    except OSError:
        return False
    for _ in range(60):
        time.sleep(0.25)
        if toolbox_command(command):
            return True
    return False
