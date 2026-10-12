<#
Einrichten und Entfernen der windows-toolbox. Aufgerufen von Setup.exe bzw. Uninstall.exe im Hauptordner – kleine
Starter aus setup\setup_exe.cs, die fertig im Repo liegen (ein Doppelklick auf eine .ps1 würde sie nur im Editor
öffnen). Neu bauen nach einer Änderung an setup_exe.cs: setup\setup_exe_bauen.ps1.

Welche Programme es gibt, steht in den Ausweisen: toolbox\programm.json und programme\<programm>\programm.json
(Name, Version, Skript, Starter-.exe, Downloads). Die Schritte 3 und 4 gelten für jedes eingerichtete Programm.

Welche Programme eingerichtet sind, steht in daten\installiert.json (ohne die Toolbox – die ist immer dabei). Fehlt
die Datei, gelten alle als eingerichtet: So war es, bevor man wählen konnte – und beim ersten Einrichten sind damit
alle vorausgewählt. Die Toolbox liest dieselbe Datei und zeigt nur eingerichtete Programme.

Einrichten (ohne Parameter) – erst ein kleines Fenster: welche Programme? (Abgewählte, die eingerichtet waren, werden
entfernt.) Danach alles, was nach dem Klonen fehlt:
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
  5. nur mit Hardware-Monitor, mit einer UAC-Abfrage: PawnIO installieren und die geplante Aufgabe HardwareMonitor
     einrichten
  6. alles wie vorher: Was Einrichten anfassen könnte, wird ganz am Anfang gemerkt und am Ende wiederhergestellt –
     auch wenn unterwegs etwas abbricht (Zustand-Merken / Zustand-Abgleichen): Autostart an/aus, ob der
     Hardware-Monitor lief (dann läuft er danach wieder, mit dem neuen Code), die Einstellungsdateien in daten\.
     Ein Update ändert so nie etwas, das man selbst eingestellt hat.
  Jeder Schritt prüft vorher, ob er schon erledigt ist – Einrichten lässt sich also jederzeit erneut ausführen,
  z. B. nach dem Verschieben des Ordners (dann wird nur die Aufgabe neu eingerichtet) oder nach einem git pull.
  Eine laufende Toolbox wird dafür beendet und am Ende wieder gestartet – mit der neuen Auswahl.

  -Programme <ids>  diese Programme zusätzlich einrichten, ohne Fenster (mit Komma getrennt, z. B.
                    -Programme hardware_monitor – so ruft „Installieren“ in der Toolbox das Skript auf).
                    Schritte 3–6 dann nur für diese; 1–2 (Python, runtime\) brauchen alle, die laufen immer.
  -OhneAdmin        nur Schritte 1–4, ohne UAC-Abfrage
  -Neustart         ohne Fenster, die eingerichteten Programme wie bisher; lief der Hardware-Monitor, ihn in
                    Schritt 6 auf jeden Fall neu starten, damit er neuen Code lädt (nach einem Update –
                    „Aktualisieren“ und „Neu einrichten“ in den Toolbox-Einstellungen übergeben das)

-Entfernen – das Gegenstück: Toolbox und Hardware-Monitor beenden, Aufgabe löschen, auf Wunsch alles Erzeugte und
  Heruntergeladene löschen (runtime\, Starter, Downloads). daten\ bleibt.
  PawnIO bleibt installiert, weil es auch andere Programme nutzen (entfernen: winget uninstall namazso.PawnIO).
  Mit -Programme <ids> nur diese Programme: beenden, Aufgabe löschen, Starter und Downloads löschen, aus
  daten\installiert.json streichen – ohne Rückfrage („Entfernen“ in der Toolbox fragt vorher selbst).

-Admin <Schritte> – intern: der Teil mit Adminrechten. Das Skript startet sich dafür selbst nach einer UAC-Abfrage
  noch einmal (Schritte, mit Komma getrennt: pawnio, aufgabe, autostart-an, autostart-aus, monitor-starten,
  aufgabe-loeschen).

Aufteilung des Ordners: Code = Repo (toolbox\, programme\, setup\), runtime\ = wegwerfbar (Python und Pakete –
lässt sich jederzeit neu einrichten), daten\ = Einstellungen (eine .json je Programm) und Logs.
#>
param([switch]$Entfernen, [string]$Programme, [switch]$OhneAdmin, [switch]$Neustart, [string]$Admin)

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
$Alle      = @($Toolbox) + @(Get-ChildItem (Join-Path $Root 'programme\*\programm.json') | ForEach-Object { Lade-Programm $_.FullName })
$Monitor   = $Alle | Where-Object id -eq 'hardware_monitor'

# Welche Programme eingerichtet sind (ohne die Toolbox) – liest auch toolbox.py (installierte_ids)
$InstalliertDatei = Join-Path $Root 'daten\installiert.json'

function Installierte {
    <# IDs der eingerichteten Programme. Fehlt die Datei (oder ist sie kaputt): alle. #>
    if (Test-Path $InstalliertDatei) {
        try { return @((Get-Content -Raw -Encoding UTF8 $InstalliertDatei | ConvertFrom-Json).programme | Where-Object { $_ }) }
        catch { }
    }
    @($Alle | Where-Object id -ne 'toolbox' | ForEach-Object id)
}

function Installierte-Speichern($ids) {
    New-Item -ItemType Directory -Force (Split-Path -Parent $InstalliertDatei) | Out-Null
    $json = ConvertTo-Json @{ programme = @($ids) }
    [IO.File]::WriteAllText($InstalliertDatei, $json, (New-Object Text.UTF8Encoding $false))   # ohne BOM, für Python
}

function Programm-Ids($text) {
    <# "a,b" aus -Programme -> geprüfte IDs. Die Toolbox gehört nicht dazu, die ist immer eingerichtet. #>
    $ids = @($text -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ -and $_ -ne 'toolbox' })
    foreach ($id in $ids) {
        if (-not ($Alle | Where-Object id -eq $id)) {
            throw "Unbekanntes Programm: $id (bekannt: $(($Alle | Where-Object id -ne 'toolbox' | ForEach-Object id) -join ', '))"
        }
    }
    $ids
}

# Aus den Ausweisen – dieselben Werte lesen toolbox.py und hardware_monitor_einstellungen.py
$Aufgabe   = $Monitor.aufgabe                    # geplante Aufgabe, die den Monitor beim Anmelden startet
$IpcPort   = $Monitor.port                       # Fernsteuerung des Monitors
$GuiPort   = $Toolbox.port                       # Fernsteuerung der Toolbox


# ---------- Helfer ----------
function Schritt($text) { Write-Host ""; Write-Host "== $text" -ForegroundColor Cyan }
function Ok($text)      { Write-Host "   [OK] $text" -ForegroundColor Green }
function Info($text)    { Write-Host "   $text" }
$Warnungen = 0                                   # gezählt: mit Warnungen bleibt das Fenster am Ende offen
function Warnung($text) { $script:Warnungen++; Write-Host "   [!] $text" -ForegroundColor Yellow }

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

function Monitor-Beenden { Programm-Beenden $Monitor }

function Programm-Beenden($p) {
    <# Beendet ein Programm über seinen Port ("port" in programm.json) und wartet bis zu 5 s darauf. #>
    Befehl-Senden $p.port 'quit' | Out-Null
    for ($i = 0; $i -lt 50 -and (Befehl-Senden $p.port 'status'); $i++) { Start-Sleep -Milliseconds 100 }
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
        # Ohne -Wait: Das wartet in Windows PowerShell auch auf alles, was der Admin-Durchlauf startet – nach
        # monitor-starten also auf den Hardware-Monitor, d. h. ewig. WaitForExit wartet nur auf das Fenster selbst.
        $p = Start-Process powershell.exe -Verb RunAs -PassThru -ArgumentList '-NoProfile',
            '-ExecutionPolicy', 'Bypass', '-File', "`"$PSCommandPath`"", '-Admin', ($schritte -join ',')
        $null = $p.Handle                         # Handle gleich holen, sonst fehlt am Ende der ExitCode
        $p.WaitForExit()
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


# ---------- Auswahlfenster ----------
function Auswahl-Fenster($vorher) {
    <# Fragt in einem kleinen Fenster, welche Programme eingerichtet sein sollen ($vorher ist vorausgewählt).
       Rückgabe: die gewählten IDs (ohne Toolbox, evtl. leer) – oder $null bei Abbrechen.
       WinForms gehört zum .NET Framework von Windows – Python und damit tkinter gibt es an dieser Stelle ja noch nicht. #>
    Add-Type -AssemblyName System.Windows.Forms, System.Drawing
    # Selbst skalieren statt von Windows unscharf hochzeichnen lassen (bei Anzeige-Skalierung über 100 %)
    Add-Type -Namespace Toolbox -Name Dpi -MemberDefinition '[DllImport("user32.dll")] public static extern bool SetProcessDPIAware();'
    [Toolbox.Dpi]::SetProcessDPIAware() | Out-Null
    [Windows.Forms.Application]::EnableVisualStyles()

    $form = New-Object Windows.Forms.Form
    $s = $form.CreateGraphics().DpiX / 96                 # Skalierung für feste Pixelmaße
    $form.Text = 'Toolbox einrichten'
    $form.Icon = New-Object Drawing.Icon (Join-Path $Root 'toolbox\toolbox.ico')
    $form.Font = New-Object Drawing.Font('Segoe UI', 9)
    $form.FormBorderStyle = 'FixedDialog'
    $form.MaximizeBox = $form.MinimizeBox = $false
    $form.StartPosition = 'CenterScreen'
    $form.AutoSize = $true
    $form.AutoSizeMode = 'GrowAndShrink'
    $form.TopMost = $true                                 # nicht hinter dem Konsolenfenster verschwinden
    $form.Add_Shown({ $form.Activate() })

    $liste = New-Object Windows.Forms.TableLayoutPanel
    $liste.AutoSize = $true
    $liste.ColumnCount = 1
    $liste.Padding = New-Object Windows.Forms.Padding ([int](14 * $s))
    $form.Controls.Add($liste)

    function Zeile($control, $abstandOben = 0, $einzug = 0) {
        $control.AutoSize = $true
        $control.Margin = New-Object Windows.Forms.Padding ([int]($einzug * $s)), ([int]($abstandOben * $s)), 0, 0
        $liste.Controls.Add($control)
    }

    $titel = New-Object Windows.Forms.Label
    $titel.Text = 'Welche Programme sollen eingerichtet werden?'
    $titel.Font = New-Object Drawing.Font($form.Font, [Drawing.FontStyle]::Bold)
    Zeile $titel

    $grau = [Drawing.SystemColors]::GrayText
    $kaestchen = @()
    foreach ($p in $Alle) {
        $box = New-Object Windows.Forms.CheckBox
        $box.Text = "$($p.name) $($p.version)"
        $box.Tag = $p.id
        $box.Checked = $p.id -eq 'toolbox' -or $vorher -contains $p.id
        $box.Enabled = $p.id -ne 'toolbox'                # die Toolbox ist immer dabei
        Zeile $box 10
        $kaestchen += $box
        if ($p.beschreibung) {
            $text = New-Object Windows.Forms.Label
            $text.Text = $p.beschreibung
            $text.ForeColor = $grau
            $text.MaximumSize = New-Object Drawing.Size ([int](380 * $s)), 0      # lange Texte umbrechen
            Zeile $text 0 18
        }
    }

    $alle = New-Object Windows.Forms.LinkLabel
    $alle.Text = 'Alle auswählen'
    $alle.Add_LinkClicked({ foreach ($box in $kaestchen) { $box.Checked = $true } }.GetNewClosure())
    Zeile $alle 12

    $hinweis = New-Object Windows.Forms.Label
    $hinweis.Text = "Abgewählte Programme werden entfernt, ihre Einstellungen bleiben.`n" +
                    'Ändern geht jederzeit: Setup.exe erneut ausführen oder in der Toolbox unter Zahnrad → Programme.'
    $hinweis.ForeColor = $grau
    $hinweis.MaximumSize = New-Object Drawing.Size ([int](380 * $s)), 0
    Zeile $hinweis 8

    $knoepfe = New-Object Windows.Forms.FlowLayoutPanel
    $knoepfe.FlowDirection = 'RightToLeft'
    $abbrechen = New-Object Windows.Forms.Button
    $abbrechen.Text = 'Abbrechen'
    $abbrechen.DialogResult = 'Cancel'
    $ok = New-Object Windows.Forms.Button
    $ok.Text = 'Einrichten'
    $ok.DialogResult = 'OK'
    foreach ($knopf in $abbrechen, $ok) {
        $knopf.AutoSize = $true
        $knopf.MinimumSize = New-Object Drawing.Size ([int](88 * $s)), 0
        $knoepfe.Controls.Add($knopf)
    }
    $form.AcceptButton = $ok
    $form.CancelButton = $abbrechen
    Zeile $knoepfe 14
    $knoepfe.Dock = 'Fill'                                # nach Zeile: Knöpfe rechtsbündig über die volle Breite

    $ergebnis = $form.ShowDialog()
    $ids = @($kaestchen | Where-Object { $_.Checked -and $_.Tag -ne 'toolbox' } | ForEach-Object { $_.Tag })
    $form.Dispose()
    if ($ergebnis -ne 'OK') { return $null }
    , $ids                                                # Komma: eine leere Liste bleibt eine Liste (nicht $null)
}


# ---------- Zustand vor dem Einrichten – ist danach genauso (auch nach einem Update) ----------
function Autostart {
    <# 'an' oder 'aus' (Schalter „Autostart“ in der Toolbox) – $null, wenn es die Aufgabe nicht gibt. #>
    $task = Get-ScheduledTask -TaskName $Aufgabe -ErrorAction SilentlyContinue
    if (-not $task) { $null } elseif ($task.State -eq 'Disabled') { 'aus' } else { 'an' }
}

function Zustand-Merken {
    <# Hält ganz am Anfang fest, was der Nutzer eingestellt hat und das Einrichten anfassen könnte –
       Zustand-Abgleichen stellt es am Ende wieder her:
       - Autostart: die Aufgabe liegt in Windows, nicht in daten\ – und Windows legt sie beim Neu-Einrichten aktiv an
       - ob der Hardware-Monitor lief (ob die Toolbox lief, merkt sich Einrichten selbst: $toolboxLief)
       - die Einstellungsdateien in daten\ (Einrichten selbst schreibt dort nur installiert.json – die Auswahl) #>
    $dateien = @{}
    foreach ($f in Get-ChildItem (Join-Path $Root 'daten\*.json') -ErrorAction SilentlyContinue) {
        if ($f.Name -ne (Split-Path -Leaf $InstalliertDatei)) { $dateien[$f.Name] = [IO.File]::ReadAllText($f.FullName) }
    }
    [pscustomobject]@{ Autostart = Autostart; MonitorLief = [bool](Monitor-Befehl 'status'); Dateien = $dateien }
}

function Json-Lesbar($pfad) {
    try { $text = [IO.File]::ReadAllText($pfad); if (-not $text.Trim()) { return $false }; $null = $text | ConvertFrom-Json; $true }
    catch { $false }
}

function Zustand-Abgleichen($vor, $monitorDa, $neuStarten) {
    <# Stellt her, was Zustand-Merken festgehalten hat. Läuft auch, wenn das Einrichten unterwegs abbricht.
       $monitorDa: Hardware-Monitor ist (noch) eingerichtet. $neuStarten: läuft er, mit dem neuen Code neu starten
       (-Neustart nach einem Update, in Schritt 3 für die neue .exe beendet, Aufgabe zeigt jetzt woandershin). #>
    Schritt 'Alles wie vorher? (Autostart, laufende Programme, Einstellungen)'
    $admin = @()                                  # was nur mit Adminrechten geht – zusammen in EINER UAC-Abfrage

    # Autostart: genau wie vorher. Gab es die Aufgabe noch nicht, ist er aus (so legt task_command sie an).
    $soll = if ($vor.Autostart) { $vor.Autostart } else { 'aus' }
    $ist = Autostart
    if (-not $ist) {
        if ($monitorDa -and $vor.Autostart) { Warnung "Aufgabe $Aufgabe fehlt – Setup.exe erneut ausführen." }
    } elseif ($ist -eq $soll) {
        Ok $(if ($vor.Autostart) { "Autostart: $ist – wie vorher" } else { 'Autostart: aus (einschalten in der Toolbox)' })
    } else {
        Info "Autostart ist $ist, war $soll – wird zurückgestellt"
        $admin += "autostart-$soll"               # die Aufgabe läuft mit Adminrechten -> ändern nur mit Adminrechten
    }

    # Hardware-Monitor: lief er vorher, läuft er danach wieder (mit dem neuen Code); lief er nicht, bleibt er aus
    $laeuft = [bool](Monitor-Befehl 'status')
    if (-not $monitorDa) {
        # abgewählt oder nie eingerichtet – nichts zu tun
    } elseif (-not $vor.MonitorLief) {
        Ok $(if ($laeuft) { 'Hardware-Monitor läuft' } else { 'Hardware-Monitor: nicht gestartet – wie vorher (Start über die Toolbox)' })
    } elseif ($laeuft -and -not $neuStarten) {
        Ok 'Hardware-Monitor läuft – wie vorher'
    } elseif (-not (Test-Path $Monitor.StarterPfad)) {
        Warnung "Hardware-Monitor lief vorher, aber $(Split-Path -Leaf $Monitor.StarterPfad) fehlt (siehe oben) – Setup.exe erneut ausführen."
    } else {
        if ($laeuft) { Monitor-Beenden }          # läuft noch mit dem alten Code
        if ($ist -eq 'an') {                      # über die Aufgabe: ohne UAC-Abfrage
            Start-ScheduledTask -TaskName $Aufgabe
            Ok $(if ($laeuft) { 'Hardware-Monitor neu gestartet – lief vorher' } else { 'Hardware-Monitor wieder gestartet – lief vorher' })
        } else {
            $admin += 'monitor-starten'           # Autostart aus -> braucht für die CPU-Werte Adminrechte
        }
    }

    if ($admin.Count -gt 0) {
        $meldungen = @{ 'autostart-an' = 'Autostart: an – wie vorher'; 'autostart-aus' = 'Autostart: aus – wie vorher'
                        'monitor-starten' = 'Hardware-Monitor wieder gestartet – lief vorher' }
        if ($OhneAdmin) { Warnung "übersprungen (-OhneAdmin): $($admin -join ', ') – in der Toolbox nachholen." }
        elseif (Als-Admin $admin) { foreach ($s in $admin) { Ok $meldungen[$s] } }
        else { Warnung 'Nicht alles ließ sich wiederherstellen – in der Toolbox nachholen (Seite Hardware-Monitor).' }
    }

    # Einstellungen in daten\: fehlt eine Datei oder ist sie kaputt, kommt die von vorher zurück
    $gleich = 0
    foreach ($name in $vor.Dateien.Keys) {
        $pfad = Join-Path $Root "daten\$name"
        if (-not (Json-Lesbar $pfad)) {
            [IO.File]::WriteAllText($pfad, $vor.Dateien[$name], (New-Object Text.UTF8Encoding $false))
            Ok "daten\$name war weg oder kaputt – wiederhergestellt"
        } elseif ([IO.File]::ReadAllText($pfad) -eq $vor.Dateien[$name]) {
            $gleich++
        } else {                                  # z. B. Fensterposition, die der Monitor beim Beenden speichert
            Info "daten\${name}: vom Programm selbst gespeichert (z. B. beim Beenden)"
        }
    }
    if ($vor.Dateien.Count -eq 0) { Ok 'Einstellungen: noch keine gespeichert' }
    elseif ($gleich -eq $vor.Dateien.Count) { Ok "Einstellungen in daten\: alle $gleich Dateien unverändert" }
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
        & $RuntimePy -B -c $PyAufgabe (Join-Path $Root 'toolbox') $Aufgabe $Monitor.StarterPfad | Out-Host
        if ($LASTEXITCODE -ne 0) { Warnung 'fehlgeschlagen'; $ok = $false } else { Ok 'eingerichtet' }
    }
    # Zurückstellen, wie es vor dem Einrichten war (Zustand-Abgleichen)
    if ($schritte -contains 'autostart-an') {
        Schritt 'Autostart wieder einschalten'
        try { Enable-ScheduledTask -TaskName $Aufgabe | Out-Null; Ok 'an, wie vorher' }
        catch { Warnung $_; $ok = $false }
    }
    if ($schritte -contains 'autostart-aus') {
        Schritt 'Autostart wieder ausschalten'
        try { Disable-ScheduledTask -TaskName $Aufgabe | Out-Null; Ok 'aus, wie vorher' }
        catch { Warnung $_; $ok = $false }
    }
    if ($schritte -contains 'monitor-starten') {        # mit Adminrechten gestartet -> der Monitor hat sie auch
        Schritt 'Hardware-Monitor wieder starten'
        try { Start-Process $Monitor.StarterPfad -WorkingDirectory $Monitor.Ordner; Ok 'gestartet' }
        catch { Warnung $_; $ok = $false }
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
    # Merken, was eingestellt ist, bevor irgendetwas passiert – am Ende ist es wieder genauso (Zustand-Abgleichen)
    $vorZustand = Zustand-Merken

    # 0. Welche Programme: aus -Programme, wie bisher (-Neustart) oder aus dem Fenster
    $vorher = Installierte
    if ($Programme) { $ids = @($vorher) + @(Programm-Ids $Programme) | Select-Object -Unique }
    elseif ($Neustart) { $ids = $vorher }
    else {
        $ids = Auswahl-Fenster $vorher
        if ($null -eq $ids) { Write-Host 'Abgebrochen – nichts geändert.'; return }
    }
    $ids = @($ids)
    Installierte-Speichern $ids                   # gleich speichern: Bricht unten etwas ab, gilt die Wahl trotzdem
    # Schritte 3–6 für alle gewählten Programme – mit -Programme nur für die genannten (die übrigen sind ja schon
    # eingerichtet). Python und runtime\ (1–2) brauchen alle, die werden immer geprüft.
    $Auswahl = @($Alle | Where-Object {
        if ($Programme) { (Programm-Ids $Programme) -contains $_.id } else { $_.id -eq 'toolbox' -or $ids -contains $_.id }
    })
    $mitMonitor = $Auswahl -contains $Monitor

    # Eine laufende Toolbox hält Dateien in runtime\ fest (Pakete, Toolbox.exe) -> vorher beenden, am Ende neu starten
    $toolboxLief = Toolbox-Beenden
    if ($toolboxLief) { Info 'Toolbox für die Einrichtung beendet – wird am Ende wieder gestartet.' }

    # Die Schritte selbst; Abgleichen und Toolbox-Start kommen auch dann, wenn unterwegs etwas abbricht
    $lauf = @{ NeuStarten = [bool]$Neustart }     # Monitor neu starten (-Neustart: nach einem Update) – setzen die Schritte
    try {
        Einrichten-Schritte $vorher $ids $Auswahl $mitMonitor $lauf | Out-Host
    } finally {
        try { Zustand-Abgleichen $vorZustand ($ids -contains $Monitor.id) $lauf.NeuStarten }
        catch { Warnung "Abgleichen fehlgeschlagen: $_" }
        if ($toolboxLief) { Toolbox-Starten }
    }

    Write-Host ""
    if ($script:Warnungen) {
        Write-Host "Fertig, aber nicht alles hat geklappt – siehe die gelben [!]-Zeilen oben." -ForegroundColor Yellow
    } elseif ($toolboxLief) {
        Write-Host "Fertig. Die Toolbox wurde wieder gestartet." -ForegroundColor Green
    } else {
        Write-Host "Fertig. Die Toolbox startest du mit Toolbox.exe." -ForegroundColor Green
    }
}

function Einrichten-Schritte($vorher, $ids, $Auswahl, $mitMonitor, $lauf) {
    foreach ($p in $Alle | Where-Object { $vorher -contains $_.id -and $ids -notcontains $_.id }) {
        Programm-Entfernen $p                     # im Fenster abgewählt
    }

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
    & $RuntimePy -c 'import tkinter, customtkinter, pystray, PIL, clr, pygame'
    if ($LASTEXITCODE -ne 0) { throw 'runtime\ ist unvollständig – Ordner runtime\ löschen und erneut einrichten' }
    Ok 'Pakete vollständig'

    # 3. Je Programm: pythonw.exe-Kopie mit eigenem Namen und Symbol + Starter
    foreach ($p in $Auswahl | Where-Object StarterPfad) {
        Schritt "$($p.name): $(Split-Path -Leaf $p.StarterPfad)"
        $meldung = & $RuntimePy -B (Join-Path $PSScriptRoot 'exe_anlegen.py') $p.HostPfad $p.name $p.SymbolPfad
        # 2 = Datei gesperrt, weil das Programm läuft. Den Monitor dürfen wir kurz beenden (Schritt 6 startet ihn neu),
        # die Toolbox nicht – da bleibt die alte Datei bis zum nächsten Einrichten.
        if ($LASTEXITCODE -eq 2 -and $p -eq $Monitor -and (Monitor-Befehl 'status')) {
            Info 'Hardware-Monitor läuft noch mit der alten Datei – wird kurz beendet …'
            Monitor-Beenden
            $lauf.NeuStarten = $true
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
    foreach ($p in $Auswahl) {
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

    if ($mitMonitor) { Monitor-Einrichten $lauf }
    # 6. (Neu) starten, was vorher lief, Autostart wie vorher: Zustand-Abgleichen (in Einrichten)
}

function Monitor-Einrichten($lauf) {
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
    # Autostart bleibt dabei, wie er war: task_command schaltet die neu angelegte Aufgabe gleich wieder aus, wenn sie
    # vorher aus war oder fehlte; Zustand-Abgleichen prüft es am Ende noch einmal

    if ($schritte.Count -eq 0) {
        # nichts zu tun
    } elseif ($OhneAdmin) {
        Warnung 'übersprungen (-OhneAdmin)'
    } elseif (Als-Admin $schritte) {
        Ok 'erledigt'
        # Ein laufender Monitor kam noch von der alten Aufgabe (anderer Ordner) -> neu starten
        if ($schritte -contains 'aufgabe') { $lauf.NeuStarten = $true }
    } else {
        Warnung 'Nicht alles hat geklappt – Setup.exe erneut ausführen.'
    }
}


# ---------- Entfernen ----------
function Aufgabe-Loeschen {
    if (-not (Get-ScheduledTask -TaskName $Aufgabe -ErrorAction SilentlyContinue)) {
        Ok "Aufgabe $Aufgabe gibt es nicht"
        return
    }
    try {
        Unregister-ScheduledTask -TaskName $Aufgabe -Confirm:$false
        Ok "Aufgabe $Aufgabe gelöscht"
    } catch {                                     # die Aufgabe läuft mit Adminrechten – zum Löschen braucht es meist auch welche
        if (Als-Admin @('aufgabe-loeschen')) { Ok "Aufgabe $Aufgabe gelöscht" } else { Warnung "Die Aufgabe $Aufgabe ist noch da." }
    }
}

function Programm-Entfernen($p) {
    <# Ein Programm wieder ausbauen: beenden, Aufgabe löschen, Starter, pythonw.exe-Kopie und Downloads löschen.
       Der Code bleibt (gehört zum Repo), die Einstellungen in daten\ auch – Einrichten macht es wieder vollständig. #>
    Schritt "$($p.name) entfernen"
    $etwas = $false
    if ($p.port -and (Befehl-Senden $p.port 'status')) { Programm-Beenden $p; Ok 'beendet'; $etwas = $true }
    if ($p.id -eq $Monitor.id -and (Get-ScheduledTask -TaskName $Aufgabe -ErrorAction SilentlyContinue)) {
        Aufgabe-Loeschen; $etwas = $true
    }
    $pfade = @($p.StarterPfad, $p.HostPfad, (Join-Path $Runtime "starter\$($p.id).cs")) +
             @(@($p.downloads | Where-Object { $_ }) | ForEach-Object { Join-Path $p.Ordner $_.ordner }) |
             Where-Object { $_ -and (Test-Path $_) }
    foreach ($pfad in $pfade) {
        # Ein gerade beendetes Programm hält seine .exe noch kurz fest – bis zu 10 s erneut versuchen
        for ($i = 0; ; $i++) {
            try { Remove-Item $pfad -Recurse -Force; Ok "gelöscht: $pfad"; break }
            catch {
                if ($i -ge 20) { Warnung "ließ sich nicht löschen: $pfad"; break }
                Start-Sleep -Milliseconds 500
            }
        }
        $etwas = $true
    }
    if (-not $etwas) { Ok 'war nicht eingerichtet' }
}

function Programme-Entfernen {
    <# -Entfernen -Programme <ids>: nur diese Programme. Die Toolbox wird dafür beendet und danach neu gestartet,
       damit sie die geänderte Auswahl zeigt. #>
    if (($Programme -split ',' | ForEach-Object { $_.Trim() }) -contains 'toolbox') {
        Warnung 'Die Toolbox selbst entfernt Uninstall.exe ohne -Programme.'
    }
    $ids = @(Programm-Ids $Programme)
    if (-not $ids) { return }
    $toolboxLief = Toolbox-Beenden
    foreach ($p in $Alle | Where-Object { $ids -contains $_.id }) { Programm-Entfernen $p }
    Installierte-Speichern @(Installierte | Where-Object { $ids -notcontains $_ })

    Write-Host ""
    if ($toolboxLief) {
        Toolbox-Starten
        Write-Host "Fertig. Die Toolbox wurde wieder gestartet." -ForegroundColor Green
    } else {
        Write-Host "Fertig." -ForegroundColor Green
    }
}

function Entfernen {
    Schritt 'Toolbox beenden'
    if (Toolbox-Beenden) { Ok 'beendet' } else { Ok 'lief nicht' }

    Schritt 'Hardware-Monitor beenden'
    if (Monitor-Befehl 'status') { Monitor-Beenden; Ok 'beendet' } else { Ok 'lief nicht' }

    Schritt "Aufgabe $Aufgabe löschen"
    Aufgabe-Loeschen

    Schritt 'Erzeugte und heruntergeladene Dateien'
    $pfade = @($Runtime) + @($Alle | ForEach-Object {
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
elseif ($Entfernen -and $Programme) { Programme-Entfernen }
elseif ($Entfernen) { Entfernen }
else { Einrichten }
# Exit-Code für Setup.exe/Uninstall.exe: 0 = alles geklappt -> Fenster schließt sich von selbst; 2 = fertig, aber mit
# Warnungen -> bleibt offen, damit man sie lesen kann (1 = abgebrochen, das macht PowerShell bei einem Fehler selbst)
exit $(if ($Warnungen) { 2 } else { 0 })
