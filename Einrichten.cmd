@echo off
rem Richtet alles ein, was nach dem Klonen fehlt (Details in setup\einrichten.ps1).
rem Kann jederzeit erneut ausgefuehrt werden, z. B. nach dem Verschieben des Ordners.
chcp 65001 >nul
rem Modulpfad von PowerShell 7 nicht erben, sonst fehlen Windows PowerShell 5.1 Befehle
set "PSModulePath="
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup\einrichten.ps1" %*
echo.
pause
