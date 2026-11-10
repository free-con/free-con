#!/usr/bin/env bash
# Mac'te çift tıklayın. Kurulumu başlatır.
cd "$(dirname "$0")" || exit 1
bash kurulum/kur-mac-linux.sh
echo
read -r -p "Bitti. Kapatmak için Enter'a basın..." _ || true
