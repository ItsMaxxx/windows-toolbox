@echo off
rem Startet die Toolbox mit dem Python aus runtime\ (legt Einrichten.cmd an) - laeuft so auch nach dem Verschieben.
rem Toolbox.exe ist pythonw.exe mit eigenem Namen und Symbol (fuer den Task-Manager); fehlt sie, geht es auch so.
chcp 65001 >nul
if not exist "%~dp0runtime\pythonw.exe" (
    echo runtime\ fehlt – bitte zuerst Einrichten.cmd ausführen.
    pause
    exit /b 1
)
set "EXE=%~dp0runtime\Toolbox.exe"
if not exist "%EXE%" set "EXE=%~dp0runtime\pythonw.exe"
start "" "%EXE%" "%~dp0src\gui\toolbox.py"
