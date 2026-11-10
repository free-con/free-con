#!/usr/bin/env bash
# Jarvis kurulumu (Mac / Linux). Çalıştırmak için: bash kurulum/kur-mac-linux.sh
set -e
cd "$(dirname "$0")/.."
JARVIS_DIR="$(pwd)"
OS="$(uname -s)"

echo
echo "=== Jarvis kurulumu ==="
echo

# 1) Python
PY=""
for c in python3.13 python3.12 python3.11 python3.10 python3; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
    PY="$c"; break
  fi
done
if [ -z "$PY" ]; then
  echo "Python 3.10 veya daha yenisi bulunamadı."
  if [ "$OS" = "Darwin" ]; then
    echo "https://www.python.org/downloads/ adresinden kurun (ya da Homebrew ile: brew install python), sonra bu betiği tekrar çalıştırın."
  else
    echo "Kurmak için: sudo apt install python3 python3-venv  (sonra bu betiği tekrar çalıştırın)"
  fi
  exit 1
fi
echo "Python bulundu: $($PY --version)"

# 2) Linux'ta ses için sistem paketleri
if [ "$OS" = "Linux" ] && command -v apt-get >/dev/null 2>&1; then
  echo "Ses için gerekli sistem paketleri kuruluyor (sudo şifreniz istenebilir)..."
  sudo apt-get install -y python3-venv libportaudio2 flac playerctl || echo "Uyarı: bazı sistem paketleri kurulamadı."
fi

# 3) Sanal ortam ve paketler
if [ ! -x .venv/bin/python ]; then
  echo "Sanal ortam oluşturuluyor (.venv)..."
  "$PY" -m venv .venv
fi
echo "Gerekli paketler yükleniyor (birkaç dakika sürebilir)..."
.venv/bin/python -m pip install --upgrade pip --quiet
.venv/bin/python -m pip install -r requirements.txt
echo "Paketler yüklendi."

# 4) Ayarlar (.env)
if .venv/bin/python kurulum/ayarla.py bos-mu ANTHROPIC_API_KEY; then
  echo
  echo "Jarvis'in çalışması için bir Claude API anahtarı gerekiyor:"
  echo "  1) https://console.anthropic.com adresine girin ve hesap açın"
  echo "  2) Billing bölümünden kredi yükleyin (kullandıkça ödersiniz)"
  echo "  3) Settings > API Keys bölümünden 'Create Key' ile anahtar oluşturun"
  read -r -p "API anahtarınızı yapıştırın (sk-ant-... ile başlar, sonra Enter): " KEY || true
  if [ -n "$KEY" ]; then
    .venv/bin/python kurulum/ayarla.py ayarla ANTHROPIC_API_KEY "$KEY"
    .venv/bin/python kurulum/ayarla.py dogrula || true
  else
    echo "Anahtar girilmedi. Daha sonra .env dosyasına ANTHROPIC_API_KEY=... satırını ekleyebilirsiniz."
  fi
fi
if .venv/bin/python kurulum/ayarla.py bos-mu JARVIS_USER_NAME; then
  read -r -p "Jarvis size nasıl hitap etsin? (örn. Ahmet; boş bırakırsanız 'efendim' der): " NAME || true
  if [ -n "$NAME" ]; then
    .venv/bin/python kurulum/ayarla.py ayarla JARVIS_USER_NAME "$NAME"
  fi
fi

# 5) Başlatma kısayolları
chmod +x jarvis-baslat.sh
if [ "$OS" = "Darwin" ] && [ -d "$HOME/Desktop" ]; then
  printf '#!/bin/bash\ncd "%s" && ./jarvis-baslat.sh\n' "$JARVIS_DIR" > "$HOME/Desktop/Jarvis.command"
  chmod +x "$HOME/Desktop/Jarvis.command"
  echo "Masaüstüne 'Jarvis.command' eklendi (çift tıklayarak açabilirsiniz)."
  echo "Not: İlk açılışta macOS mikrofon izni isteyecek; 'İzin Ver' deyin."
elif [ "$OS" = "Linux" ]; then
  mkdir -p "$HOME/.local/share/applications"
  cat > "$HOME/.local/share/applications/jarvis.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Jarvis
Comment=Claude ile çalışan sesli asistan
Exec=$JARVIS_DIR/jarvis-baslat.sh
Terminal=true
Categories=Utility;
EOF
  echo "Uygulama menüsüne 'Jarvis' eklendi."
fi

echo
echo "=== Kurulum tamamlandı! ==="
read -r -p "Hoparlör ve mikrofon testi yapılsın mı? (E/H): " TEST || true
case "$TEST" in
  [eEyY]*) .venv/bin/python jarvis.py --ses-testi || true ;;
esac
echo
echo "Jarvis'i başlatmak için: ./jarvis-baslat.sh   (yazarak konuşmak için: ./jarvis-baslat.sh --yazi)"
