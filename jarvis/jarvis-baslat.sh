#!/usr/bin/env bash
# Jarvis'i başlatır (Mac/Linux). Örnek: ./jarvis-baslat.sh --yazi
cd "$(dirname "$0")" || exit 1
if [ ! -x .venv/bin/python ]; then
  echo "Jarvis henüz kurulmamış. Önce şunu çalıştırın: bash kurulum/kur-mac-linux.sh"
  exit 1
fi
exec .venv/bin/python jarvis.py "$@"
