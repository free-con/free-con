@echo off
chcp 65001 >nul
rem Jarvis'i USB'den (ya da taşınabilir klasörden) Windows'ta çalıştırır.
rem Veriler ve API anahtarı bu klasörde durur; USB'yi taktığınız her Windows PC'de çalışır.
rem Not: Hedef PC'de Python 3.10+ kurulu olmalı (yoksa kurulum\kur-windows.bat ile kurun).
setlocal
cd /d "%~dp0"

set "VENV=.portable\windows"
set "VPY=%VENV%\Scripts\python.exe"

rem Python'u bul
set "PY="
for %%C in ("py -3" "python" "python3") do (
  if not defined PY (
    %%~C -c "import sys;sys.exit(0 if sys.version_info>=(3,10) else 1)" >nul 2>&1 && set "PY=%%~C"
  )
)
if not defined PY (
  echo Python 3.10+ bulunamadi. https://www.python.org/downloads/ adresinden kurun
  echo ve kurulumda "Add python.exe to PATH" kutucugunu isaretleyin.
  pause
  exit /b 1
)

rem Sanal ortam yoksa ya da bozuksa bu PC icin kur
"%VPY%" -c "import anthropic" >nul 2>&1
if errorlevel 1 (
  echo Bu bilgisayar icin ilk hazirlik yapiliyor ^(internet gerekir, birkaç dakika^)...
  %PY% -m venv "%VENV%" || (echo Sanal ortam olusturulamadi & pause & exit /b 1)
  "%VPY%" -m pip install --upgrade pip --quiet
  "%VPY%" -m pip install -r requirements.txt || (echo Paketler yuklenemedi & pause & exit /b 1)
)

set "JARVIS_PORTABLE=1"
set "JARVIS_DATA_DIR=%~dp0jarvis_veri"
"%VPY%" jarvis.py %*
pause
