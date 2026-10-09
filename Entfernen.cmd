@echo off
rem Gegenstueck zu Einrichten.cmd (Details in setup\setup.ps1).
chcp 65001 >nul
rem Modulpfad von PowerShell 7 nicht erben, sonst fehlen Windows PowerShell 5.1 Befehle
set "PSModulePath="
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup\setup.ps1" -Entfernen
echo.
pause
