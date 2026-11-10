"""Telefon erişimini (Telegram botu ve/veya web arayüzü) adım adım ayarlar.

Çalıştırmak için:
    Windows:  .venv\\Scripts\\python kurulum\\telefon-kur.py
    Mac/Linux: .venv/bin/python kurulum/telefon-kur.py
"""

from __future__ import annotations

import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kurulum.ayarla import get_value, set_value  # noqa: E402


def sor(soru: str, varsayilan: str = "") -> str:
    ek = f" [{varsayilan}]" if varsayilan else ""
    cevap = input(f"{soru}{ek}: ").strip()
    return cevap or varsayilan


def evet_mi(soru: str, varsayilan: bool = True) -> bool:
    secim = "E/h" if varsayilan else "e/H"
    cevap = input(f"{soru} ({secim}): ").strip().lower()
    if not cevap:
        return varsayilan
    return cevap[0] in ("e", "y")


def kur_telegram() -> None:
    print("\n--- Telegram botu ---")
    print("1) Telefonunuzda Telegram'ı açın, @BotFather ile konuşun.")
    print("2) /newbot yazın, bota bir ad ve kullanıcı adı verin.")
    print("3) BotFather size bir TOKEN verecek (123456:ABC... gibi). Onu buraya yapıştırın.")
    token = sor("Bot token")
    if not token:
        print("Token girilmedi, Telegram atlanıyor.")
        return
    set_value("JARVIS_TELEGRAM_TOKEN", token)

    print("\nGüvenlik: Botunuza sadece siz erişebilmelisiniz.")
    print("En kolayı bir 'eşleştirme kodu' belirlemek: botu ilk açtığınızda bu kodu")
    print("bota yazarsınız ve telefonunuz yetkilenir. Kod gizli kalsın.")
    kod = sor("Eşleştirme kodu", secrets.token_hex(3))
    set_value("JARVIS_TELEGRAM_PAIR_CODE", kod)
    print(f"→ Eşleştirme kodunuz: {kod}  (Jarvis'i başlatıp bota bu kodu yazın.)")

    if evet_mi("Sesli mesaja sesli cevap da verilsin mi?", True):
        set_value("JARVIS_TELEGRAM_VOICE_REPLY", "evet")
        print("Not: Sesli mesaj GÖNDEREBİLMEK için şunu da kurun: pip install av")
    else:
        set_value("JARVIS_TELEGRAM_VOICE_REPLY", "hayir")
    print("Telegram ayarlandı.")


def kur_web() -> None:
    print("\n--- Web arayüzü (aynı Wi-Fi'daki telefon tarayıcısı) ---")
    set_value("JARVIS_WEB", "evet")
    token = get_value("JARVIS_WEB_TOKEN") or secrets.token_urlsafe(9)
    set_value("JARVIS_WEB_TOKEN", token)
    port = sor("Web portu", get_value("JARVIS_WEB_PORT") or "8765")
    set_value("JARVIS_WEB_PORT", port)
    print(f"Web arayüzü açık olacak. Jarvis başlayınca size tam adresi (anahtar dahil) yazacak.")
    print("O adresi telefonunuzun tarayıcısında açın. Telefon ev PC'nizle aynı Wi-Fi'da olmalı.")
    print("Adresi kimseyle paylaşmayın: o adrese giren bilgisayarınıza komut verebilir.")


def main() -> int:
    print("=== Jarvis telefon kurulumu ===")
    print("Telefondan Jarvis'e Telegram ve/veya web arayüzü ile ulaşabilirsiniz.")
    if evet_mi("\nTelegram botu kurulsun mu? (her yerden erişim, önerilir)", True):
        kur_telegram()
    if evet_mi("\nWeb arayüzü açılsın mı? (aynı Wi-Fi'dayken tarayıcıdan)", True):
        kur_web()
    print("\nBitti. Artık Jarvis'i her zamanki gibi başlatın; telefon kanalları otomatik açılır.")
    print("Ev PC'nizde mikrofon kullanmadan, sadece telefon için çalıştırmak isterseniz:")
    print("   python jarvis.py --sunucu")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
