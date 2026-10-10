<#
Einrichten und Entfernen der windows-toolbox. Aufgerufen von Setup.exe bzw. Uninstall.exe im Hauptordner – kleine
Starter aus setup\setup_exe.cs, die fertig im Repo liegen (ein Doppelklick auf eine .ps1 würde sie nur im Editor
öffnen). Neu bauen nach einer Änderung an setup_exe.cs: setup\setup_exe_bauen.ps1.

Welche Programme es gibt, steht in den Ausweisen: toolbox\programm.json und programme\<programm>\programm.json
(Name, Version, Skript, Starter-.exe, Downloads). Die Schritte 3 und 4 gelten für jedes Programm darin.

Einrichten (ohne Parameter) – alles, was nach dem Klonen fehlt:
  1. Python $PythonVersion finden (oder per winget installieren) – genau diese Version, keine ältere oder neuere
  2. runtime\ anlegen: eigenes Python im Projektordner, mit den Paketen aus requirements.txt (feste Versionen)
  3. je Programm zwei .exe:
       - runtime\<Name>.exe: Kopie von pythonw.exe mit eigenem Namen und Symbol, damit es im Task-Manager als eigenes
         Programm erscheint statt als „Python“ (setup\exe_anlegen.py)
       - der Starter (Toolbox.exe im Hauptordner, HardwareMonitor.exe im Programmordner): startet die Kopie mit dem
         Skript, alle Pfade relativ – Doppelklick und Verknüpfungen funktionieren auch nach dem Verschieben
         (setup\starter.cs, übersetzt mit csc.exe aus dem .NET Framework von Windows)
  4. je Programm die Downloads aus programm.json (feste Version, Prüfsumme), z. B. LibreHardwareMonitor nach
     programme\hardware_monitor\lhm\
  5. mit einer UAC-Abfrage: PawnIO installieren und die geplante Aufgabe HardwareMonitor einrichten
  6. Hardware-Monitor (neu) starten
  Jeder Schritt prüft vorher, ob er schon erledigt ist – Einrichten lässt sich also jederzeit erneut ausführen,
  z. B. nach dem Verschieben des Ordners (dann wird nur die Aufgabe neu eingerichtet) oder nach einem git pull.

  -OhneAdmin    nur Schritte 1–4, ohne UAC-Abfrage
  -Neustart     Hardware-Monitor in Schritt 6 auf jeden Fall neu starten, damit er neuen Code lädt
                (nach einem Update – „Aktualisieren“ in den Toolbox-Einstellungen übergibt das)

-Entfernen – das Gegenstück: Toolbox und Hardware-Monitor beenden, Aufgabe löschen, auf Wunsch alles Erzeugte und
  Heruntergeladene löschen (runtime\, Starter, Downloads). daten\ bleibt.
  PawnIO bleibt installiert, weil es auch andere Programme nutzen (entfernen: winget uninstall namazso.PawnIO).

-Admin <Schritte> – intern: der Teil mit Adminrechten. Das Skript startet sich dafür selbst nach einer UAC-Abfrage
  noch einmal (Schritte, mit Komma getrennt: pawnio, aufgabe, aufgabe-loeschen).

Aufteilung des Ordners: Code = Repo (toolbox\, programme\, setup\), runtime\ = wegwerfbar (Python und Pakete –
lässt sich jederzeit neu einrichten), daten\ = Einstellungen (eine .json je Programm) und Logs.
#>
param([switch]$Entfernen, [switch]$OhneAdmin, [switch]$Neustart, [string]$Admin)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'         # Fortschrittsbalken bremsen Invoke-WebRequest stark aus

$Root       = Split-Path -Parent $PSScriptRoot
$Runtime    = Join-Path $Root 'runtime'
$RuntimePy  = Join-Path $Runtime 'python.exe'
$Symbol     = Join-Path $Root 'toolbox\programm.ico'   # Standardsymbol der Programme (⚒ auf Grün); die Toolbox hat
                                                     # ihr eigenes ("symbol" in toolbox\programm.json)
$Csc        = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'

# Python: genau diese Version (Major.Minor) – mit ihr sind die festen Paketversionen in requirements.txt geprüft.
# Zum Wechseln: hier ändern, runtime\ löschen, Setup.exe ausführen, testen, requirements.txt anpassen.
$PythonVersion = '3.14'

# Richtet die Aufgabe über winutil.task_command() ein – denselben Befehl nutzt die Toolbox bei „Aufgabe einrichten“.
# (Ohne doppelte Anführungszeichen, die würde Windows PowerShell 5.1 bei der Übergabe an python.exe verstümmeln.)
$PyAufgabe = 'import sys; sys.path.insert(0, sys.argv[1]); import winutil; ' +
             'r = winutil.powershell(winutil.task_command(*sys.argv[2:4])); ok = r is not None and r.returncode == 0; ' +
             'ok or print(r.stderr if r else None); sys.exit(0 if ok else 1)'


# ---------- Programme (aus den programm.json) ----------
function Lade-Programm($datei) {
    <# Liest einen Ausweis und ergänzt die fertigen Pfade: Ordner, Skript, Starter (die .exe zum Doppelklicken) und
       Host (die pythonw.exe-Kopie in runtime\, die der Starter aufruft – gleicher Dateiname wie der Starter). #>
    $p = Get-Content -Raw -Encoding UTF8 $datei | ConvertFrom-Json
    $ordner = Split-Path -Parent $datei
    $p | Add-Member Ordner $ordner
    if ($p.starter) {                             # nur bei Programmen, die eigenständig laufen (nicht nur eine Seite)
        $p | Add-Member SkriptPfad (Join-Path $ordner $p.skript)
        $p | Add-Member StarterPfad ([IO.Path]::GetFullPath((Join-Path $ordner $p.starter)))
        $p | Add-Member HostPfad (Join-Path $Runtime (Split-Path -Leaf $p.starter))
        $p | Add-Member SymbolPfad $(if ($p.symbol) { Join-Path $ordner $p.symbol } else { $Symbol })
    }
    $p
}

$Toolbox   = Lade-Programm (Join-Path $Root 'toolbox\programm.json')
$Programme = @($Toolbox) + @(Get-ChildItem (Join-Path $Root 'programme\*\programm.json') | ForEach-Object { Lade-Programm $_.FullName })
$Monitor   = $Programme | Where-Object id -eq 'hardware_monitor'

# Aus den Ausweisen – dieselben Werte lesen toolbox.py und hardware_monitor_einstellungen.py
$Aufgabe   = $Monitor.aufgabe                    # geplante Aufgabe, die den Monitor beim Anmelden startet
$IpcPort   = $Monitor.port                       # Fernsteuerung des Monitors
$GuiPort   = $Toolbox.port                       # Fernsteuerung der Toolbox


# ---------- Helfer ----------
function Schritt($text) { Write-Host ""; Write-Host "== $text" -ForegroundColor Cyan }
function Ok($text)      { Write-Host "   [OK] $text" -ForegroundColor Green }
function Info($text)    { Write-Host "   $text" }
function Warnung($text) { Write-Host "   [!] $text" -ForegroundColor Yellow }

function Monitor-Befehl($befehl) {
    <# Schickt einen Befehl an den laufenden Hardware-Monitor (wie ipc() in hardware_monitor_gui.py) – $null, wenn er
       nicht läuft. #>
    Befehl-Senden $IpcPort $befehl
}

function Toolbox-Befehl($befehl) {
    <# Dasselbe für die Toolbox ("status", "quit", "show" – siehe instance_server in toolbox.py). #>
    Befehl-Senden $GuiPort $befehl
}

function Befehl-Senden($port, $befehl) {
    try {
        $client = New-Object Net.Sockets.TcpClient
        $client.Connect('127.0.0.1', $port)
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

function Monitor-Beenden {
    Monitor-Befehl 'quit' | Out-Null
    for ($i = 0; $i -lt 50 -and (Monitor-Befehl 'status'); $i++) { Start-Sleep -Milliseconds 100 }   # bis zu 5 s
}

function Toolbox-Beenden {
    <# $true, wenn die Toolbox lief (und jetzt beendet ist). #>
    if (-not (Toolbox-Befehl 'status')) { return $false }
    Toolbox-Befehl 'quit' | Out-Null
    for ($i = 0; $i -lt 50 -and (Toolbox-Befehl 'status'); $i++) { Start-Sleep -Milliseconds 100 }
    Start-Sleep -Milliseconds 500                 # Prozess räumt nach dem Schließen des Ports noch kurz auf
    return $true
}

function Toolbox-Starten {
    if (Test-Path $Toolbox.StarterPfad) { Start-Process $Toolbox.StarterPfad; return }
    $exe = if (Test-Path $Toolbox.HostPfad) { $Toolbox.HostPfad } else { Join-Path $Runtime 'pythonw.exe' }
    Start-Process $exe -ArgumentList "`"$($Toolbox.SkriptPfad)`"" -WorkingDirectory $Toolbox.Ordner
}

function Als-Admin($schritte) {
    <# Startet dieses Skript mit -Admin nach einer UAC-Abfrage noch einmal. $true, wenn dort alles geklappt hat. #>
    Info 'Windows fragt jetzt nach Adminrechten …'
    try {
        $p = Start-Process powershell.exe -Verb RunAs -Wait -PassThru -ArgumentList '-NoProfile',
            '-ExecutionPolicy', 'Bypass', '-File', "`"$PSCommandPath`"", '-Admin', ($schritte -join ',')
        return $p.ExitCode -eq 0
    } catch {
        Warnung 'Adminrechte abgelehnt.'
        return $false
    }
}

function Relativ($von, $nach) {
    <# Pfad von Ordner $von nach $nach, z. B. "..\..\runtime" – für den Starter, der so nach dem Verschieben noch passt.
       (Windows PowerShell 5.1 hat kein [IO.Path]::GetRelativePath, deshalb über Uri.) #>
    $basis = New-Object Uri ($von.TrimEnd('\') + '\')
    $rel = [Uri]::UnescapeDataString($basis.MakeRelativeUri((New-Object Uri $nach)).ToString()) -replace '/', '\'
    if ($rel) { $rel } else { '.' }
}

function Starter-Bauen($p) {
    <# Übersetzt setup\starter.cs (+ argumente.cs) für dieses Programm. Rückgabe: Meldung. Gebaut wird nur, wenn sich der erzeugte
       Quelltext oder das Symbol geändert hat (csc erzeugt bei jedem Lauf eine leicht andere Datei – ein
       Byte-Vergleich ginge nicht). #>
    $ordner = Split-Path -Parent $p.StarterPfad
    $werte = [ordered]@{
        '%NAME%' = $p.name; '%VERSION%' = $p.version; '%HOST%' = (Split-Path -Leaf $p.HostPfad)
        '%RUNTIME%' = (Relativ $ordner $Runtime); '%SKRIPT%' = (Relativ $ordner $p.SkriptPfad)
    }
    $quelle = (Get-Content -Raw -Encoding UTF8 (Join-Path $PSScriptRoot 'starter.cs')) + "`r`n" +
              (Get-Content -Raw -Encoding UTF8 (Join-Path $PSScriptRoot 'argumente.cs'))
    foreach ($platzhalter in $werte.Keys) { $quelle = $quelle.Replace($platzhalter, $werte[$platzhalter]) }
    # Prüfsumme des Symbols mit in den Quelltext – so wird nach einem neuen Symbol auch neu gebaut
    $quelle += "`r`n// Symbol: $((Get-FileHash $p.SymbolPfad -Algorithm SHA256).Hash)`r`n"
    $merker = Join-Path $Runtime "starter\$($p.id).cs"          # zuletzt übersetzter Quelltext (gehört zu runtime\)
    if ((Test-Path $p.StarterPfad) -and (Test-Path $merker) -and
        (Get-Content -Raw -Encoding UTF8 $merker) -eq $quelle) { return "$(Split-Path -Leaf $p.StarterPfad) ist schon aktuell" }
    if (-not (Test-Path $Csc)) { throw "C#-Compiler nicht gefunden ($Csc)" }

    New-Item -ItemType Directory -Force (Split-Path -Parent $merker) | Out-Null
    $tmp = Join-Path (Split-Path -Parent $merker) "$($p.id).tmp.cs"
    [IO.File]::WriteAllText($tmp, $quelle, (New-Object Text.UTF8Encoding $true))    # mit BOM, sonst kein „ü“ in csc
    $neu = "$($p.StarterPfad).neu"
    $ausgabe = & $Csc /nologo /target:winexe /optimize+ "/win32icon:$($p.SymbolPfad)" "/out:$neu" $tmp 2>&1
    if ($LASTEXITCODE -ne 0) { throw "csc meldet: $ausgabe" }
    Move-Item -Force $neu $p.StarterPfad
    Move-Item -Force $tmp $merker
    "$(Split-Path -Leaf $p.StarterPfad) angelegt"
}


# ---------- Der Teil mit Adminrechten (läuft im eigenen Fenster) ----------
function Admin-Schritte($schritte) {
    $ok = $true
    if ($schritte -contains 'pawnio') {
        Schritt 'PawnIO installieren'
        winget install --id namazso.PawnIO --exact --accept-package-agreements --accept-source-agreements | Out-Host
        if ($LASTEXITCODE -eq 0) { Ok 'installiert' } else { Warnung "winget meldet Code $LASTEXITCODE"; $ok = $false }
    }
    if ($schritte -contains 'aufgabe') {
        Schritt "Aufgabe $Aufgabe einrichten"
        $vorher = Get-ScheduledTask -TaskName $Aufgabe -ErrorAction SilentlyContinue
        & $RuntimePy -B -c $PyAufgabe (Join-Path $Root 'toolbox') $Aufgabe $Monitor.StarterPfad | Out-Host
        if ($LASTEXITCODE -ne 0) {
            Warnung 'fehlgeschlagen'; $ok = $false
        } else {
            if ($vorher -and $vorher.State -eq 'Disabled') {      # Autostart war bewusst aus -> so lassen
                Disable-ScheduledTask -TaskName $Aufgabe | Out-Null
                Info 'Autostart bleibt ausgeschaltet, wie vorher'
            }
            Ok 'eingerichtet'
        }
    }
    if ($schritte -contains 'aufgabe-loeschen') {
        Schritt "Aufgabe $Aufgabe löschen"
        try { Unregister-ScheduledTask -TaskName $Aufgabe -Confirm:$false; Ok 'gelöscht' }
        catch { Warnung $_; $ok = $false }
    }
    if (-not $ok) { Read-Host "`nEnter drücken zum Schließen" | Out-Null }   # Fehler lesbar lassen
    return $ok
}


# ---------- Einrichten ----------
function Finde-Python {
    <# Registriertes Python $PythonVersion (64 Bit) aus der Registry (PEP 514) – oder $null.
       Andere Versionen zählen bewusst nicht: requirements.txt ist nur mit $PythonVersion geprüft. #>
    foreach ($hive in 'HKCU:', 'HKLM:') {
        $exe = (Get-ItemProperty "$hive\Software\Python\PythonCore\$PythonVersion\InstallPath" `
                    -ErrorAction SilentlyContinue).ExecutablePath
        if ($exe -and (Test-Path $exe)) { return [pscustomobject]@{ Version = $PythonVersion; Exe = $exe } }
    }
    $null
}

function Runtime-Version {
    <# Major.Minor des Pythons in runtime\, z. B. "3.14". #>
    & $RuntimePy -c 'import sys; print(*sys.version_info[:2], sep=''.'')'
}

function Einrichten {
    # Eine laufende Toolbox hält Dateien in runtime\ fest (Pakete, Toolbox.exe) -> vorher beenden, am Ende neu starten
    $toolboxLief = Toolbox-Beenden
    if ($toolboxLief) { Info 'Toolbox für die Einrichtung beendet – wird am Ende wieder gestartet.' }

    # 1. Python
    Schritt "Python $PythonVersion"
    if (Test-Path $RuntimePy) {
        $vorhanden = Runtime-Version
        if ($vorhanden -eq $PythonVersion) { Ok 'runtime\ ist schon da – das installierte Python wird nicht gebraucht' }
        else { Warnung "runtime\ enthält Python $vorhanden statt $PythonVersion – zum Wechseln runtime\ löschen und erneut einrichten." }
    } else {
        $python = Finde-Python
        if (-not $python) {
            Info "Python $PythonVersion nicht gefunden – wird per winget installiert …"
            winget install --id "Python.Python.$PythonVersion" --exact --scope user --accept-package-agreements --accept-source-agreements
            $python = Finde-Python
            if (-not $python) { throw "Python $PythonVersion konnte nicht installiert werden. Bitte von python.org installieren und erneut starten." }
        }
        Ok "Python $($python.Version): $($python.Exe)"
    }

    # 2. runtime\
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
        "# Angelegt von Setup.exe: keine Pakete aus dem Benutzerordner (%APPDATA%\Python) verwenden`r`n" +
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
    # Ohne ssl lädt pip nichts von PyPI – z. B. wenn beim Kopieren libcrypto-3.dll fehlte. Lieber hier klar abbrechen.
    & $RuntimePy -c 'import ssl'
    if ($LASTEXITCODE -ne 0) { throw 'runtime\ ist unvollständig (ssl fehlt) – Ordner runtime\ löschen und erneut einrichten' }
    Info 'Pakete aus requirements.txt (feste Versionen) …'
    & $RuntimePy -m pip install --disable-pip-version-check --no-warn-script-location --quiet `
        -r (Join-Path $Root 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Pakete konnten nicht installiert werden' }
    & $RuntimePy -c 'import tkinter, customtkinter, pystray, PIL, clr'
    if ($LASTEXITCODE -ne 0) { throw 'runtime\ ist unvollständig – Ordner runtime\ löschen und erneut einrichten' }
    Ok 'Pakete vollständig'

    # 3. Je Programm: pythonw.exe-Kopie mit eigenem Namen und Symbol + Starter
    $neuStarten = [bool]$Neustart                 # Monitor in Schritt 6 neu starten (-Neustart: nach einem Update)
    foreach ($p in $Programme | Where-Object StarterPfad) {
        Schritt "$($p.name): $(Split-Path -Leaf $p.StarterPfad)"
        $meldung = & $RuntimePy -B (Join-Path $PSScriptRoot 'exe_anlegen.py') $p.HostPfad $p.name $p.SymbolPfad
        # 2 = Datei gesperrt, weil das Programm läuft. Den Monitor dürfen wir kurz beenden (Schritt 6 startet ihn neu),
        # die Toolbox nicht – da bleibt die alte Datei bis zum nächsten Einrichten.
        if ($LASTEXITCODE -eq 2 -and $p -eq $Monitor -and (Monitor-Befehl 'status')) {
            Info 'Hardware-Monitor läuft noch mit der alten Datei – wird kurz beendet …'
            Monitor-Beenden
            $neuStarten = $true
            # Der Prozess räumt nach dem letzten IPC-Lebenszeichen noch kurz auf (LHM schließen) – so lange ist die
            # Datei noch gesperrt. Bis zu 10 s erneut versuchen.
            for ($i = 0; $i -lt 20; $i++) {
                $meldung = & $RuntimePy -B (Join-Path $PSScriptRoot 'exe_anlegen.py') $p.HostPfad $p.name $p.SymbolPfad
                if ($LASTEXITCODE -ne 2) { break }
                Start-Sleep -Milliseconds 500
            }
        }
        if ($LASTEXITCODE -eq 0) { Ok "runtime\$meldung" }
        elseif ($LASTEXITCODE -eq 2) { Warnung "$meldung (z. B. Toolbox schließen)" }
        else { Warnung $meldung }

        try { Ok (Starter-Bauen $p) }
        catch { Warnung "Starter nicht angelegt: $_" }
    }

    # 4. Je Programm: Downloads aus programm.json
    foreach ($p in $Programme) {
        foreach ($d in @($p.downloads | Where-Object { $_ })) {
            Schritt "$($d.name) $($d.version) für $($p.name)"
            $ziel = Join-Path $p.Ordner $d.ordner
            $pruefdatei = Join-Path $ziel $d.pruefdatei
            if (Test-Path $pruefdatei) {
                $vorhanden = (Get-Item $pruefdatei).VersionInfo.ProductVersion -replace '\+.*$', ''
                if ($vorhanden -eq $d.version) { Ok 'schon da' }
                else { Warnung "$($d.ordner)\ enthält Version $vorhanden statt $($d.version) – bleibt so (zum Ersetzen den Ordner löschen)." }
            } else {
                $zip = Join-Path ([IO.Path]::GetTempPath()) "$($p.id)-$($d.ordner)-$($d.version).zip"
                Info "Lade $($d.url) …"
                Invoke-WebRequest $d.url -OutFile $zip -UseBasicParsing
                if ((Get-FileHash $zip -Algorithm SHA256).Hash -ne $d.sha256) {
                    Remove-Item $zip
                    throw 'Prüfsumme der heruntergeladenen Datei stimmt nicht – Download abgebrochen.'
                }
                Expand-Archive $zip -DestinationPath $ziel -Force
                Remove-Item $zip
                Get-ChildItem $ziel -Recurse -File | Unblock-File    # „aus dem Internet“-Markierung entfernen, sonst lädt .NET die DLLs nicht
                Ok "entpackt nach $ziel"
            }
        }
    }

    # 5. Adminrechte: PawnIO und Aufgabe
    Schritt 'PawnIO und Autostart-Aufgabe'
    $schritte = @()
    if (Get-Service PawnIO -ErrorAction SilentlyContinue) { Ok 'PawnIO ist installiert' }
    else { Info 'PawnIO fehlt'; $schritte += 'pawnio' }

    # Die Aufgabe startet den Starter ohne Argumente (wie task_points_here in hardware_monitor_gui.py)
    $task = Get-ScheduledTask -TaskName $Aufgabe -ErrorAction SilentlyContinue
    $taskPasst = $task -and $task.Actions[0].Execute -eq $Monitor.StarterPfad -and -not $task.Actions[0].Arguments
    if ($taskPasst) { Ok "Aufgabe $Aufgabe zeigt auf diesen Ordner" }
    elseif (-not (Test-Path $Monitor.StarterPfad)) { Warnung "$($Monitor.StarterPfad) fehlt (siehe oben) – Aufgabe bleibt, wie sie ist" }
    elseif ($task) { Info "Aufgabe $Aufgabe zeigt noch auf: $($task.Actions[0].Execute) $($task.Actions[0].Arguments)"; $schritte += 'aufgabe' }
    else { Info "Aufgabe $Aufgabe fehlt"; $schritte += 'aufgabe' }

    if ($schritte.Count -eq 0) {
        # nichts zu tun
    } elseif ($OhneAdmin) {
        Warnung 'übersprungen (-OhneAdmin)'
    } elseif (Als-Admin $schritte) {
        Ok 'erledigt'
        $neuStarten = $neuStarten -or ($schritte -contains 'aufgabe')
    } else {
        Warnung 'Nicht alles hat geklappt – Setup.exe erneut ausführen.'
    }

    # 6. Hardware-Monitor starten
    Schritt 'Hardware-Monitor'
    $task = Get-ScheduledTask -TaskName $Aufgabe -ErrorAction SilentlyContinue
    $laeuft = [bool](Monitor-Befehl 'status')
    if (-not $task -or $task.State -eq 'Disabled') {
        Info $(if ($laeuft) { 'läuft' } else { 'nicht gestartet (Aufgabe fehlt oder Autostart ist aus) – Start über die Toolbox' })
    } elseif ($laeuft -and -not $neuStarten) {
        Ok 'läuft'
    } else {
        if ($laeuft) { Monitor-Beenden }          # läuft noch mit dem alten Programm -> beenden und neu starten
        Start-ScheduledTask -TaskName $Aufgabe
        Ok $(if ($laeuft) { 'neu gestartet' } else { 'gestartet' })
    }

    Write-Host ""
    if ($toolboxLief) {
        Toolbox-Starten
        Write-Host "Fertig. Die Toolbox wurde wieder gestartet." -ForegroundColor Green
    } else {
        Write-Host "Fertig. Die Toolbox startest du mit Toolbox.exe." -ForegroundColor Green
    }
}


# ---------- Entfernen ----------
function Entfernen {
    Schritt 'Toolbox beenden'
    if (Toolbox-Beenden) { Ok 'beendet' } else { Ok 'lief nicht' }

    Schritt 'Hardware-Monitor beenden'
    if (Monitor-Befehl 'status') { Monitor-Beenden; Ok 'beendet' } else { Ok 'lief nicht' }

    Schritt "Aufgabe $Aufgabe löschen"
    if (-not (Get-ScheduledTask -TaskName $Aufgabe -ErrorAction SilentlyContinue)) {
        Ok 'gibt es nicht'
    } else {
        try {
            Unregister-ScheduledTask -TaskName $Aufgabe -Confirm:$false
            Ok 'gelöscht'
        } catch {                                 # die Aufgabe läuft mit Adminrechten – zum Löschen braucht es meist auch welche
            if (Als-Admin @('aufgabe-loeschen')) { Ok 'gelöscht' } else { Warnung 'Die Aufgabe ist noch da.' }
        }
    }

    Schritt 'Erzeugte und heruntergeladene Dateien'
    $pfade = @($Runtime) + @($Programme | ForEach-Object {
        $p = $_
        $p.StarterPfad
        @($p.downloads | Where-Object { $_ }) | ForEach-Object { Join-Path $p.Ordner $_.ordner }
    }) | Where-Object { $_ -and (Test-Path $_) }
    if (-not $pfade) {
        Ok 'nichts da'
    } else {
        $pfade | ForEach-Object { Info $_ }
        if ((Read-Host '   Das alles löschen? (j/n)') -match '^[jJyY]') {
            try {
                $pfade | ForEach-Object { Remove-Item $_ -Recurse -Force }
                Ok 'gelöscht'
            } catch {
                Warnung 'Nicht alles ließ sich löschen – läuft die Toolbox noch? Dann schließen und erneut versuchen.'
            }
        } else {
            Ok 'bleiben'
        }
    }

    Write-Host ""
    Write-Host "Fertig. Den Ordner kannst du jetzt löschen (daten\ enthält deine Einstellungen)." -ForegroundColor Green
    Write-Host "PawnIO bleibt installiert (entfernen: winget uninstall namazso.PawnIO)." -ForegroundColor Green
}


if ($Admin) { exit $(if (Admin-Schritte ($Admin -split ',')) { 0 } else { 1 }) }
elseif ($Entfernen) { Entfernen }
else { Einrichten }
