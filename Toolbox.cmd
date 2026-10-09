@echo off
rem Startet die Toolbox mit dem Python aus runtime\ (legt Einrichten.cmd an) - laeuft so auch nach dem Verschieben.
chcp 65001 >nul
if not exist "%~dp0runtime\pythonw.exe" (
    echo runtime\ fehlt – bitte zuerst Einrichten.cmd ausführen.
    pause
    exit /b 1
)
start "" "%~dp0runtime\pythonw.exe" "%~dp0src\gui\toolbox.py"
