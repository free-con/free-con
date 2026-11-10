@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Jarvis henuz kurulmamis. Once kurulum\kur-windows.bat dosyasini calistirin.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" jarvis.py %*
pause
