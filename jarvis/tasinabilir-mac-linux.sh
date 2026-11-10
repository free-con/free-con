#!/usr/bin/env bash
# Jarvis'i USB'den (ya da taşınabilir klasörden) Mac/Linux'ta çalıştırır.
# Veriler ve API anahtarı bu klasörde durur; taktığınız her uyumlu PC'de çalışır.
# Not: Hedefte Python 3.10+ kurulu olmalı. Mac dosyası için: tasinabilir-mac-linux.command
cd "$(dirname "$0")" || exit 1
USB="$(pwd)"

case "$(uname -s)" in
  Darwin) OSNAME="mac" ;;
  Linux)  OSNAME="linux" ;;
  *)      OSNAME="other" ;;
esac
VENV="$USB/.portable/$OSNAME"
VPY="$VENV/bin/python"

# Python bul
PY=""
for c in python3.13 python3.12 python3.11 python3.10 python3; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys;sys.exit(0 if sys.version_info>=(3,10) else 1)' 2>/dev/null; then
    PY="$c"; break
  fi
done
if [ -z "$PY" ]; then
  echo "Python 3.10+ bulunamadı. Mac: https://www.python.org/downloads/  |  Linux: sudo apt install python3 python3-venv"
  read -r -p "Çıkmak için Enter'a basın..." _ || true
  exit 1
fi

# Sanal ortam yok ya da bozuksa bu PC için kur
if ! "$VPY" -c "import anthropic" >/dev/null 2>&1; then
  echo "Bu bilgisayar için ilk hazırlık yapılıyor (internet gerekir, birkaç dakika)..."
  "$PY" -m venv "$VENV" || { echo "Sanal ortam oluşturulamadı"; exit 1; }
  "$VPY" -m pip install --upgrade pip --quiet
  "$VPY" -m pip install -r requirements.txt || { echo "Paketler yüklenemedi"; exit 1; }
fi

export JARVIS_PORTABLE=1
export JARVIS_DATA_DIR="$USB/jarvis_veri"
exec "$VPY" jarvis.py "$@"
