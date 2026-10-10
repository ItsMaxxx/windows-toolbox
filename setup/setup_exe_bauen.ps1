<#
Baut Setup.exe und Uninstall.exe im Hauptordner aus setup\setup_exe.cs – nur nötig, wenn sich setup_exe.cs geändert
hat. Danach beide .exe committen: Sie liegen fertig im Repo, weil nach dem Klonen sonst nichts da wäre, was sie baut.

Aufruf (im Terminal, im Hauptordner):  powershell -NoProfile -ExecutionPolicy Bypass -File setup\setup_exe_bauen.ps1

csc.exe ist der C#-Compiler des .NET Framework 4, der bei Windows 10/11 dabei ist. Er bettet automatisch ein Manifest
mit „asInvoker“ ein – wichtig, weil Windows .exe mit „setup“ oder „install“ im Namen ohne Manifest für Installer hält
und sofort eine UAC-Abfrage zeigt. setup.ps1 soll aber ohne Adminrechte laufen und sie nur für einzelne Schritte holen.
#>
$ErrorActionPreference = 'Stop'
$Root   = Split-Path -Parent $PSScriptRoot
$Csc    = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
$Quelle = Join-Path $PSScriptRoot 'setup_exe.cs'
$Symbol = Join-Path $Root 'toolbox\toolbox.ico'

foreach ($exe in @(@('Setup.exe', @()), @('Uninstall.exe', @('/define:ENTFERNEN')))) {
    $ziel = Join-Path $Root $exe[0]
    & $Csc /nologo /target:exe /optimize+ "/win32icon:$Symbol" "/out:$ziel" @($exe[1]) $Quelle
    if ($LASTEXITCODE -ne 0) { throw "csc meldet Fehler bei $($exe[0])" }
    Write-Host "$($exe[0]) gebaut"
}
