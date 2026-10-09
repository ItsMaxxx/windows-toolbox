<#
Entfernen.cmd ruft dieses Skript auf – das Gegenstück zu einrichten.ps1:

  1. Hardware-Monitor beenden
  2. geplante Aufgabe HardwareMonitor löschen (falls nötig mit UAC-Abfrage)
  3. auf Wunsch runtime\ und src\hardware_monitor\lhm\ löschen

Danach kann der Ordner einfach gelöscht werden. PawnIO bleibt installiert, weil es auch andere Programme nutzen
(entfernen mit: winget uninstall namazso.PawnIO).
#>

$ErrorActionPreference = 'Stop'
$Root    = Split-Path -Parent $PSScriptRoot
$Aufgabe = 'HardwareMonitor'                     # wie DEFAULT_TASK in hardware_monitor_gui.py
$IpcPort = 47815                                 # wie IPC_PORT in hardware_monitor.py

function Schritt($text) { Write-Host ""; Write-Host "== $text" -ForegroundColor Cyan }
function Ok($text)      { Write-Host "   [OK] $text" -ForegroundColor Green }
function Warnung($text) { Write-Host "   [!] $text" -ForegroundColor Yellow }

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


Schritt 'Hardware-Monitor beenden'
if (Monitor-Befehl 'quit') {
    for ($i = 0; $i -lt 50 -and (Monitor-Befehl 'status'); $i++) { Start-Sleep -Milliseconds 100 }
    Ok 'beendet'
} else {
    Ok 'lief nicht'
}


Schritt "Aufgabe $Aufgabe löschen"
if (-not (Get-ScheduledTask -TaskName $Aufgabe -ErrorAction SilentlyContinue)) {
    Ok 'gibt es nicht'
} else {
    try {
        Unregister-ScheduledTask -TaskName $Aufgabe -Confirm:$false
        Ok 'gelöscht'
    } catch {
        # Die Aufgabe läuft mit Adminrechten – zum Löschen braucht es meist auch welche
        Write-Host '   Windows fragt jetzt nach Adminrechten …'
        try {
            $befehl = "Unregister-ScheduledTask -TaskName '$Aufgabe' -Confirm:`$false"
            $p = Start-Process powershell.exe -ArgumentList '-NoProfile', '-Command', $befehl `
                -Verb RunAs -Wait -PassThru -WindowStyle Hidden
            if ($p.ExitCode -eq 0) { Ok 'gelöscht' } else { Warnung 'Löschen fehlgeschlagen' }
        } catch {
            Warnung 'Adminrechte abgelehnt – die Aufgabe ist noch da.'
        }
    }
}


Schritt 'Heruntergeladene Dateien'
$ordner = @('runtime', 'src\hardware_monitor\lhm') | ForEach-Object { Join-Path $Root $_ } | Where-Object { Test-Path $_ }
if (-not $ordner) {
    Ok 'nichts da'
} else {
    $ordner | ForEach-Object { Write-Host "   $_" }
    $antwort = Read-Host '   Diese Ordner auch löschen? (j/n)'
    if ($antwort -match '^[jJyY]') {
        try {
            $ordner | ForEach-Object { Remove-Item $_ -Recurse -Force }
            Ok 'gelöscht'
        } catch {
            Warnung 'Nicht alles ließ sich löschen – läuft die Toolbox noch? Dann schließen und erneut versuchen.'
        }
    } else {
        Ok 'bleiben'
    }
}

Write-Host ""
Write-Host "Fertig. Den Ordner kannst du jetzt löschen. PawnIO bleibt installiert (entfernen: winget uninstall namazso.PawnIO)." -ForegroundColor Green
