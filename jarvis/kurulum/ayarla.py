"""Kurulum yardımcısı: .env dosyasına ayar yazar ve API anahtarını doğrular.

    python kurulum/ayarla.py ayarla ANAHTAR DEĞER   # .env içinde ANAHTAR=DEĞER yapar
    python kurulum/ayarla.py bos-mu ANAHTAR         # boşsa çıkış kodu 0, doluysa 1
    python kurulum/ayarla.py dogrula                # API anahtarını ücretsiz bir istekle dener
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV = ROOT / ".env"
EXAMPLE = ROOT / ".env.example"


def _ensure_env() -> None:
    if not ENV.exists():
        shutil.copyfile(EXAMPLE, ENV)


def get_value(key: str) -> str:
    _ensure_env()
    for line in ENV.read_text(encoding="utf-8-sig").splitlines():
        if line.startswith(key + "="):
            return line.split("=", 1)[1].strip()
    return ""


def set_value(key: str, value: str) -> None:
    _ensure_env()
    value = value.strip().replace("\n", "").replace("\r", "")
    text = ENV.read_text(encoding="utf-8-sig")
    pattern = re.compile(rf"^{re.escape(key)}=.*$", re.M)
    if pattern.search(text):
        text = pattern.sub(lambda _m: f"{key}={value}", text, count=1)
    else:
        text = text.rstrip("\n") + f"\n{key}={value}\n"
    ENV.write_text(text, encoding="utf-8")


def verify() -> int:
    sys.path.insert(0, str(ROOT))
    from jarvis_core.config import load_config

    import anthropic

    cfg = load_config()
    if not cfg.api_key:
        print("API anahtarı girilmemiş.")
        return 1
    try:
        anthropic.Anthropic(api_key=cfg.api_key).models.list(limit=1)
    except anthropic.AuthenticationError:
        print("HATA: API anahtarı geçersiz. Anahtarı console.anthropic.com adresinden kontrol edin.")
        return 1
    except anthropic.APIConnectionError:
        print("Uyarı: İnternete bağlanılamadı, anahtar şimdi doğrulanamadı.")
        return 0
    except anthropic.APIStatusError as exc:
        print(f"Uyarı: Anahtar doğrulanamadı ({exc.status_code}).")
        return 0
    print("API anahtarı çalışıyor.")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) >= 3 and argv[0] == "ayarla":
        set_value(argv[1], argv[2])
        return 0
    if len(argv) == 2 and argv[0] == "bos-mu":
        return 0 if not get_value(argv[1]) else 1
    if argv == ["dogrula"]:
        return verify()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
