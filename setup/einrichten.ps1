<#
Einrichten.cmd ruft dieses Skript auf. Es richtet alles ein, was nach dem Klonen fehlt:

  1. Python finden (oder per winget installieren)
  2. runtime\ anlegen: eigenes Python im Projektordner, mit den Paketen aus requirements.txt
  3. runtime\HardwareMonitor.exe anlegen (damit der Monitor im Task-Manager unter seinem Namen erscheint)
  4. LibreHardwareMonitor herunterladen (feste Version) nach src\hardware_monitor\lhm\
  5. mit einer UAC-Abfrage: PawnIO installieren und die geplante Aufgabe HardwareMonitor einrichten (setup\admin.py)
  6. Hardware-Monitor (neu) starten

Jeder Schritt prüft vorher, ob er schon erledigt ist – das Skript lässt sich also jederzeit erneut ausführen,
z. B. nach dem Verschieben des Ordners (dann wird nur die Aufgabe neu eingerichtet) oder nach einem git pull.

  -OhneAdmin   nur Schritte 1–4, ohne UAC-Abfrage
#>
param([switch]$OhneAdmin)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'         # Fortschrittsbalken bremsen Invoke-WebRequest stark aus

$Root      = Split-Path -Parent $PSScriptRoot
$Runtime   = Join-Path $Root 'runtime'
$RuntimePy = Join-Path $Runtime 'python.exe'
$MonitorExe = Join-Path $Runtime 'HardwareMonitor.exe'
$Script    = Join-Path $Root 'src\hardware_monitor\hardware_monitor.py'
$Lhm       = Join-Path $Root 'src\hardware_monitor\lhm'
$Aufgabe   = 'HardwareMonitor'                   # wie DEFAULT_TASK in hardware_monitor_gui.py
$IpcPort   = 47815                               # wie IPC_PORT in hardware_monitor.py

# LibreHardwareMonitor: feste Version, damit die Sensornamen in detailfenster_inhalt.py passen
$LhmVersion = '0.9.6'
$LhmUrl     = "https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases/download/v$LhmVersion/LibreHardwareMonitor.zip"
$LhmSha256  = '086D9F1B5A99E643EDC2CFAAAC16051685B551E4C5AC0B32A57C58C0E529C001'

function Schritt($text) { Write-Host ""; Write-Host "== $text" -ForegroundColor Cyan }
function Ok($text)      { Write-Host "   [OK] $text" -ForegroundColor Green }
function Info($text)    { Write-Host "   $text" }
function Warnung($text) { Write-Host "   [!] $text" -ForegroundColor Yellow }


# ---------- 1. Python ----------
function Finde-Python {
    <# Höchste registrierte Python-Version ab 3.10 (64 Bit), aus der Registry (PEP 514) – oder $null. #>
    $kandidaten = foreach ($hive in 'HKCU:', 'HKLM:') {
        Get-ChildItem "$hive\Software\Python\PythonCore" -ErrorAction SilentlyContinue | ForEach-Object {
            $version = $_.PSChildName
            $exe = (Get-ItemProperty (Join-Path $_.PSPath 'InstallPath') -ErrorAction SilentlyContinue).ExecutablePath
            if ($version -match '^3\.(\d+)$' -and [int]$Matches[1] -ge 10 -and $exe -and (Test-Path $exe)) {
                [pscustomobject]@{ Version = [version]$version; Exe = $exe }
            }
        }
    }
    $kandidaten | Sort-Object Version -Descending | Select-Object -First 1
}

Schritt 'Python'
if (Test-Path $RuntimePy) {
    Ok 'runtime\ ist schon da – das installierte Python wird nicht gebraucht'
} else {
    $python = Finde-Python
    if (-not $python) {
        Info 'Kein Python gefunden – wird per winget installiert …'
        winget install --id Python.Python.3.14 --exact --scope user --accept-package-agreements --accept-source-agreements
        $python = Finde-Python
        if (-not $python) { throw 'Python konnte nicht installiert werden. Bitte von python.org installieren und erneut starten.' }
    }
    Ok "Python $($python.Version): $($python.Exe)"
}


# ---------- 2. runtime\ ----------
Schritt 'Eigenes Python im Projektordner (runtime\)'
if (-not (Test-Path $RuntimePy)) {
    $basis = Split-Path -Parent $python.Exe
    Info "Kopiere $basis …"
    # Ohne Doku, Tests, Entwickler-Dateien und die installierten Pakete (die kommen gleich frisch dazu)
    robocopy $basis $Runtime /E /NFL /NDL /NJH /NJS /NP `
        /XD (Join-Path $basis 'Doc') (Join-Path $basis 'include') (Join-Path $basis 'libs') `
            (Join-Path $basis 'Scripts') (Join-Path $basis 'Tools') (Join-Path $basis 'Lib\site-packages') `
            (Join-Path $basis 'Lib\test') __pycache__ `
        /XF *.pyc | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "Kopieren fehlgeschlagen (robocopy-Code $LASTEXITCODE)" }
    New-Item -ItemType Directory -Force (Join-Path $Runtime 'Lib\site-packages') | Out-Null

    # Python soll nur nutzen, was in runtime\ liegt – nichts aus dem installierten Python oder dem Benutzerordner.
    # So fällt sofort auf, wenn etwas fehlt, statt erst auf einem anderen PC.
    # ._pth-Datei: feste Suchpfade, Umgebungsvariablen wie PYTHONPATH zählen nicht
    $dll = Get-ChildItem $Runtime -Filter 'python3*.dll' | Where-Object Name -ne 'python3.dll' | Select-Object -First 1
    "$($dll.BaseName).zip`r`nDLLs`r`nLib`r`nimport site`r`n" |
        Set-Content -Encoding ASCII (Join-Path $Runtime "$($dll.BaseName)._pth")
    # sitecustomize.py: nimmt die Pakete aus %APPDATA%\Python wieder heraus (die ._pth-Datei allein tut das nicht)
    "# Angelegt von Einrichten.cmd: keine Pakete aus dem Benutzerordner (%APPDATA%\Python) verwenden`r`n" +
    "import site, sys`r`n" +
    "if site.getusersitepackages() in sys.path:`r`n" +
    "    sys.path.remove(site.getusersitepackages())`r`n" |
        Set-Content -Encoding ASCII (Join-Path $Runtime 'Lib\sitecustomize.py')

    Info 'Installiere pip …'
    # Ausgabe verwerfen (u. a. die Warnung, runtime\Scripts stehe nicht im PATH – braucht es auch nicht);
    # 'Continue', weil PowerShell 5.1 Text auf stderr sonst als Fehler wertet
    $ErrorActionPreference = 'Continue'
    & $RuntimePy -m ensurepip --default-pip 2>&1 | Out-Null
    $ErrorActionPreference = 'Stop'
    if ($LASTEXITCODE -ne 0) { throw 'pip konnte nicht eingerichtet werden' }
    Ok 'runtime\ angelegt'
}
Info 'Pakete aus requirements.txt …'
& $RuntimePy -m pip install --disable-pip-version-check --no-warn-script-location --quiet `
    -r (Join-Path $Root 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Pakete konnten nicht installiert werden' }
& $RuntimePy -c 'import tkinter, customtkinter, pystray, PIL, clr'
if ($LASTEXITCODE -ne 0) { throw 'runtime\ ist unvollständig – Ordner runtime\ löschen und erneut einrichten' }
Ok 'Pakete vollständig'


# ---------- 3. HardwareMonitor.exe ----------
Schritt 'HardwareMonitor.exe'
$pythonw = Join-Path $Runtime 'pythonw.exe'
if ((Test-Path $MonitorExe) -and (Get-FileHash $MonitorExe).Hash -eq (Get-FileHash $pythonw).Hash) {
    Ok 'schon da'
} else {
    try {
        Copy-Item $pythonw $MonitorExe -Force
        Ok 'angelegt (Kopie von pythonw.exe)'
    } catch {
        Warnung 'Konnte nicht angelegt werden – läuft der Hardware-Monitor gerade? Dann nach dem Beenden erneut einrichten.'
    }
}


# ---------- 4. LibreHardwareMonitor ----------
Schritt "LibreHardwareMonitor $LhmVersion"
if (Test-Path (Join-Path $Lhm 'LibreHardwareMonitorLib.dll')) {
    $vorhanden = (Get-Item (Join-Path $Lhm 'LibreHardwareMonitorLib.dll')).VersionInfo.ProductVersion -replace '\+.*$', ''
    if ($vorhanden -eq $LhmVersion) { Ok 'schon da' }
    else { Warnung "lhm\ enthält Version $vorhanden statt $LhmVersion – bleibt so (zum Ersetzen lhm\ löschen)." }
} else {
    $zip = Join-Path ([IO.Path]::GetTempPath()) "LibreHardwareMonitor-$LhmVersion.zip"
    Info 'Lade von GitHub …'
    Invoke-WebRequest $LhmUrl -OutFile $zip -UseBasicParsing
    if ((Get-FileHash $zip -Algorithm SHA256).Hash -ne $LhmSha256) {
        Remove-Item $zip
        throw 'Prüfsumme der heruntergeladenen Datei stimmt nicht – Download abgebrochen.'
    }
    Expand-Archive $zip -DestinationPath $Lhm -Force
    Remove-Item $zip
    Get-ChildItem $Lhm -Recurse -File | Unblock-File    # „aus dem Internet“-Markierung entfernen, sonst lädt .NET die DLLs nicht
    Ok "entpackt nach $Lhm"
}


# ---------- 5. Adminrechte: PawnIO und Aufgabe ----------
function Monitor-Befehl($befehl) {
    <# Schickt einen Befehl an den laufenden Hardware-Monitor (wie ipc() in hardware_monitor_gui.py). #>
    try {
        $client = New-Object Net.Sockets.TcpClient
        $client.Connect('127.0.0.1', $IpcPort)
        $client.ReceiveTimeout = 1000
        $stream = $client.GetStream()
        $bytes = [Text.Encoding]::UTF8.GetBytes("$befehl`n")
        $stream.Write($bytes, 0, $bytes.Length)
        $antwort = (New-Object IO.StreamReader($stream)).ReadLine()
        $client.Close()
        return $antwort
    } catch {
        return $null
    }
}

Schritt 'PawnIO und Autostart-Aufgabe'
$argumente = @()
if (Get-Service PawnIO -ErrorAction SilentlyContinue) { Ok 'PawnIO ist installiert' }
else { Info 'PawnIO fehlt'; $argumente += '--pawnio' }

$task = Get-ScheduledTask -TaskName $Aufgabe -ErrorAction SilentlyContinue
$taskPasst = $task -and $task.Actions[0].Execute -eq $MonitorExe -and "$($task.Actions[0].Arguments)".Trim('"') -eq $Script
if ($taskPasst) { Ok "Aufgabe $Aufgabe zeigt auf diesen Ordner" }
elseif ($task) { Info "Aufgabe $Aufgabe zeigt noch auf: $($task.Actions[0].Execute) $($task.Actions[0].Arguments)"; $argumente += '--aufgabe' }
else { Info "Aufgabe $Aufgabe fehlt"; $argumente += '--aufgabe' }

$neuStarten = $false
if ($argumente.Count -eq 0) {
    # nichts zu tun
} elseif ($OhneAdmin) {
    Warnung 'übersprungen (-OhneAdmin)'
} else {
    Info 'Windows fragt jetzt einmal nach Adminrechten …'
    try {
        $p = Start-Process $RuntimePy -ArgumentList (@('-B', "`"$PSScriptRoot\admin.py`"") + $argumente) `
            -Verb RunAs -Wait -PassThru
        if ($p.ExitCode -eq 0) { Ok 'erledigt'; $neuStarten = $argumente -contains '--aufgabe' }
        else { Warnung 'Es gab Fehler (siehe Adminfenster). Einrichten.cmd danach erneut ausführen.' }
    } catch {
        Warnung 'Adminrechte abgelehnt – PawnIO bzw. Aufgabe fehlen noch. Einrichten.cmd erneut ausführen.'
    }
}


# ---------- 6. Hardware-Monitor starten ----------
Schritt 'Hardware-Monitor'
$task = Get-ScheduledTask -TaskName $Aufgabe -ErrorAction SilentlyContinue
$laeuft = [bool](Monitor-Befehl 'status')
if (-not $task -or $task.State -eq 'Disabled') {
    Info $(if ($laeuft) { 'läuft' } else { 'nicht gestartet (Aufgabe fehlt oder Autostart ist aus) – Start über die Toolbox' })
} elseif ($laeuft -and -not $neuStarten) {
    Ok 'läuft'
} else {
    if ($laeuft) {                                # läuft noch mit dem alten Programm -> beenden und neu starten
        Monitor-Befehl 'quit' | Out-Null
        for ($i = 0; $i -lt 50 -and (Monitor-Befehl 'status'); $i++) { Start-Sleep -Milliseconds 100 }
    }
    Start-ScheduledTask -TaskName $Aufgabe
    Ok $(if ($laeuft) { 'neu gestartet' } else { 'gestartet' })
}

Write-Host ""
Write-Host "Fertig. Die Toolbox startest du mit Toolbox.cmd." -ForegroundColor Green
