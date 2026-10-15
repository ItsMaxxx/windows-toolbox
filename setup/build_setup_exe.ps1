<#
Builds Setup.exe and Uninstall.exe in the main folder from setup\setup_exe.cs – only needed when setup_exe.cs has
changed. Then commit both .exe files: they are in the repo ready-made, because after cloning there would otherwise be
nothing that builds them.

Call (in the terminal, in the main folder):  powershell -NoProfile -ExecutionPolicy Bypass -File setup\build_setup_exe.ps1

csc.exe is the C# compiler of the .NET Framework 4 that comes with Windows 10/11. It automatically embeds a manifest
with "asInvoker" – important because Windows treats .exe files with "setup" or "install" in their name as installers
without a manifest and immediately shows a UAC prompt. setup.ps1 should run without admin rights though and only get
them for individual steps.
#>
$ErrorActionPreference = 'Stop'
$Root   = Split-Path -Parent $PSScriptRoot
$Csc    = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
$Source = (Join-Path $PSScriptRoot 'setup_exe.cs'), (Join-Path $PSScriptRoot 'arguments.cs')
$Icon   = Join-Path $Root 'toolbox\toolbox.ico'

foreach ($exe in @(@('Setup.exe', @()), @('Uninstall.exe', @('/define:UNINSTALL')))) {
    $target = Join-Path $Root $exe[0]
    & $Csc /nologo /target:exe /optimize+ "/win32icon:$Icon" "/out:$target" @($exe[1]) $Source
    if ($LASTEXITCODE -ne 0) { throw "csc reports errors for $($exe[0])" }
    Write-Host "$($exe[0]) built"
}
