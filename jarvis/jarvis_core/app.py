"""Jarvis'in ana döngüsü: yazı modu ve sesli mod."""

from __future__ import annotations

import os
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime

from .config import PROJECT_DIR, Config
from .memory import MemoryStore
from .reminders import ReminderManager
from .service import JarvisService

DIM, BOLD, CYAN, GREEN, YELLOW, RED, RESET = "\033[2m", "\033[1m", "\033[36m", "\033[32m", "\033[33m", "\033[31m", "\033[0m"

HELP_TEXT = f"""{BOLD}Komutlar:{RESET}
  /yeni      Yeni konuşma başlat (Jarvis bu konuşmayı unutur, kalıcı hafızası kalır)
  /hafiza    Jarvis'in sizin hakkınızda hatırladıkları
  /maliyet   Bu oturumda harcanan token ve tahmini maliyet
  /yardim    Bu yardım
  /cikis     Çıkış
{BOLD}Örnekler:{RESET} "Spotify'ı aç", "Tarkan çal", "10 dakika sonra çayı hatırlat",
  "yarın hava nasıl", "ekranımda ne var", "bilgisayar neden yavaş", "dolar kaç TL"
"""


AUDIO_HINT = (
    "Linux'ta ses kütüphanesi eksik olabilir: sudo apt install libportaudio2\n"
    "Windows/Mac'te mikrofonun bağlı olduğundan ve uygulamalara mikrofon izni verildiğinden emin olun."
)


@dataclass
class JarvisContext:
    config: Config
    memory: MemoryStore
    reminders: ReminderManager


_print_lock = threading.Lock()


def say_line(text: str, color: str = "") -> None:
    with _print_lock:
        print(f"{color}{text}{RESET if color else ''}", flush=True)


def greeting(name: str) -> str:
    hour = datetime.now().hour
    if 5 <= hour < 12:
        hello = "Günaydın"
    elif 12 <= hour < 18:
        hello = "İyi günler"
    elif 18 <= hour < 23:
        hello = "İyi akşamlar"
    else:
        hello = "İyi geceler"
    who = f" {name}" if name else " efendim"
    return f"{hello}{who}. Sistemler hazır, sizi dinliyorum."


def _setup_console() -> None:
    if os.name == "nt":
        os.system("")  # Windows konsolunda renkleri etkinleştirir
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass


def check_api_key(config: Config) -> bool:
    if config.api_key or os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        return True
    say_line("Claude API anahtarı bulunamadı.", RED)
    say_line(
        f"1) https://console.anthropic.com adresinden bir API anahtarı alın (Settings > API Keys).\n"
        f"2) {PROJECT_DIR / '.env'} dosyasını açıp şu satırı ekleyin:\n"
        f"   ANTHROPIC_API_KEY=sk-ant-...\n"
        f"   (Kurulum betiğini çalıştırdıysanız anahtarı orada da girebilirsiniz.)",
        YELLOW,
    )
    return False


def _handle_slash(command: str, service: JarvisService, channel: str) -> bool:
    """Eğik çizgiyle başlayan komutları işler. Çıkış istenirse False döner."""
    cmd = command.lower().strip()
    if cmd in ("/cikis", "/çıkış", "/exit", "/quit"):
        return False
    if cmd == "/yeni":
        service.reset_channel(channel)
        say_line("Yeni konuşma başladı.", GREEN)
    elif cmd in ("/hafiza", "/hafıza"):
        say_line(service.memory.list_facts(), CYAN)
    elif cmd == "/maliyet":
        say_line(service.usage_summary(), CYAN)
    else:
        say_line(HELP_TEXT)
    return True


def start_phone_channels(service: JarvisService, config: Config):
    """Yapılandırılmışsa Telegram ve web kanallarını başlatır. (durdurma fonksiyonu) döndürür."""
    stoppers = []
    if config.telegram_enabled:
        try:
            from .channels.telegram_bot import TelegramBot

            bot = TelegramBot(service, config, on_log=lambda m: say_line(m, DIM))
            service.add_reminder_listener(bot.notify_reminder)
            bot.start()
            stoppers.append(bot.stop)
            if not bot.allowed and not bot.pair_code:
                say_line("📱 Telegram botu açık ama henüz yetkili cihaz yok.", YELLOW)
                say_line("   Telefonunuzdan bota /start yazın; size cihaz kimliğinizi söyleyecek. "
                         "Onu .env dosyasındaki JARVIS_TELEGRAM_ALLOWED satırına ekleyin "
                         "(ya da JARVIS_TELEGRAM_PAIR_CODE belirleyip o kodu gönderin).", DIM)
            else:
                say_line("📱 Telegram botu açık — telefonunuzdan yazabilir/konuşabilirsiniz.", GREEN)
        except Exception as exc:
            say_line(f"Telegram başlatılamadı: {exc}", RED)
    if config.web_enabled:
        try:
            from .channels.web import WebInterface

            web = WebInterface(service, config)
            service.add_reminder_listener(web.add_event)
            web.start()
            stoppers.append(web.stop)
            say_line("🌐 Web arayüzü açık. Telefonunuzun tarayıcısında şu adresi açın:", GREEN)
            say_line(f"   {web.url}", BOLD + CYAN)
            say_line("   (Telefon ev bilgisayarınızla aynı Wi-Fi'da olmalı. Adresi paylaşmayın: komut çalıştırır.)", DIM)
        except OSError as exc:
            say_line(f"Web arayüzü başlatılamadı (port {config.web_port} meşgul olabilir): {exc}", RED)
        except Exception as exc:
            say_line(f"Web arayüzü başlatılamadı: {exc}", RED)

    def stop_all() -> None:
        for stop in stoppers:
            try:
                stop()
            except Exception:
                pass

    return stop_all


def run_text(config: Config, speak: bool = False) -> None:
    speaker = None
    if speak:
        from .voice import Speaker

        speaker = Speaker(config)
        if not speaker.available:
            say_line("Ses çıkışı kullanılamıyor; sadece yazıyla devam ediliyor.", YELLOW)
            speaker = None

    service = JarvisService(config)
    channel = "masaüstü"
    mode = "voice" if speaker else "text"

    def notify(text: str) -> None:
        say_line(f"\n⏰ {text}", YELLOW + BOLD)
        print("\a", end="", flush=True)
        if speaker:
            speaker.say(text)

    service.add_reminder_listener(notify)
    stop_phone = start_phone_channels(service, config)
    service.get_brain(channel, mode, on_status=lambda msg: say_line(f"  {msg}", DIM))
    service.start_reminders()

    name = config.assistant_name
    hello = greeting(config.user_name).replace("sizi dinliyorum", "yazmanızı bekliyorum")
    say_line(f"\n{BOLD}{CYAN}{name}{RESET} ({config.model}) - {hello}")
    say_line("Yardım için /yardim yazın. Çıkmak için /cikis.\n", DIM)
    if speaker:
        speaker.say(hello)
    try:
        while True:
            try:
                text = input(f"{BOLD}Sen:{RESET} ").strip()
            except EOFError:
                break
            if not text:
                continue
            if text.startswith("/"):
                if not _handle_slash(text, service, channel):
                    break
                continue
            reply = service.ask(channel, text, mode)
            say_line(f"{BOLD}{CYAN}{name}:{RESET} {reply.text}\n", "" if reply.ok else YELLOW)
            if speaker:
                speaker.say(reply.text)
    except KeyboardInterrupt:
        pass
    finally:
        stop_phone()
        service.stop_reminders()
        say_line(f"\n{service.usage_summary()}", DIM)
        say_line("Görüşmek üzere.", CYAN)


def run_voice(config: Config) -> None:
    from .voice import Listener, SpeechServiceError, Speaker, find_wake_word, is_exit_command

    speaker = Speaker(config)
    if not speaker.available:
        say_line("Uyarı: ses çıkışı kullanılamıyor, cevaplar sadece ekrana yazılacak.", YELLOW)
    try:
        listener = Listener(config)
        listener.calibrate()
    except Exception as exc:
        say_line(f"Mikrofon açılamadı: {exc}", RED)
        say_line(AUDIO_HINT, YELLOW)
        if config.phone_enabled:
            say_line("Mikrofonsuz sunucu moduna geçiliyor (telefondan kullanabilirsiniz).", YELLOW)
            run_server(config)
        else:
            say_line("Yazı moduna geçiliyor. (Mikrofonları görmek için: python jarvis.py --mikrofonlar)", YELLOW)
            run_text(config, speak=speaker.available)
        return

    service = JarvisService(config)
    channel = "masaüstü"

    def notify(text: str) -> None:
        say_line(f"⏰ {text}", YELLOW + BOLD)
        speaker.say(text)

    service.add_reminder_listener(notify)
    stop_phone = start_phone_channels(service, config)
    service.get_brain(channel, "voice", on_status=lambda msg: say_line(f"  {msg}", DIM))
    service.start_reminders()

    name = config.assistant_name
    wake_hint = config.wake_words[0].capitalize()
    say_line(f"\n{BOLD}{CYAN}{name}{RESET} ({config.model}) hazır. Konuşmak için '{wake_hint} ...' diye başlayın.")
    say_line(f"Örnek: '{wake_hint}, Spotify'ı aç' veya '{wake_hint}, yarın hava nasıl?'. Kapatmak için '{wake_hint}, kendini kapat' ya da Ctrl+C.\n", DIM)
    hello = greeting(config.user_name)
    say_line(f"{CYAN}{name}:{RESET} {hello}")
    speaker.say(hello)

    awake_until = 0.0
    errors_in_a_row = 0
    try:
        while True:
            try:
                heard = listener.listen()
                errors_in_a_row = 0
            except SpeechServiceError as exc:
                errors_in_a_row += 1
                if errors_in_a_row == 1:
                    say_line(str(exc), RED)
                time.sleep(min(30, 2 ** errors_in_a_row))
                continue
            if not heard:
                continue
            woke, command = find_wake_word(heard, config.wake_words)
            in_follow_up = time.monotonic() < awake_until
            if not woke and not in_follow_up:
                say_line(f"  (duyuldu: {heard})", DIM)
                continue
            if woke and not command:
                say_line(f"{CYAN}{name}:{RESET} Efendim?")
                speaker.say("Efendim?")
                awake_until = time.monotonic() + config.follow_up_seconds
                continue
            command = command if woke else heard
            say_line(f"{BOLD}Sen:{RESET} {command}")
            if is_exit_command(command):
                speaker.say("Kendimi kapatıyorum. Görüşmek üzere.")
                break
            reply = service.ask(channel, command, "voice")
            say_line(f"{BOLD}{CYAN}{name}:{RESET} {reply.text}", "" if reply.ok else YELLOW)
            speaker.say(reply.text)
            awake_until = time.monotonic() + config.follow_up_seconds
    except KeyboardInterrupt:
        pass
    finally:
        stop_phone()
        service.stop_reminders()
        say_line(f"\n{service.usage_summary()}", DIM)
        say_line("Görüşmek üzere.", CYAN)


def run_server(config: Config) -> None:
    """Mikrofonsuz sunucu modu: sadece telefon kanalları. Ev PC'si açık dururken telefondan kullanılır."""
    service = JarvisService(config)
    service.add_reminder_listener(lambda text: say_line(f"⏰ {text}", YELLOW + BOLD))
    stop_phone = start_phone_channels(service, config)
    service.start_reminders()
    if not config.phone_enabled:
        say_line("Sunucu modu için en az bir telefon kanalı açık olmalı.", RED)
        say_line("Telegram için JARVIS_TELEGRAM_TOKEN, web için JARVIS_WEB=evet ayarlayın "
                 "(python kurulum/telefon-kur.py ile kolayca yapabilirsiniz).", YELLOW)
        stop_phone()
        return
    name = config.assistant_name
    say_line(f"\n{BOLD}{CYAN}{name}{RESET} ({config.model}) sunucu modunda çalışıyor. "
             "Telefonunuzdan ulaşabilirsiniz. Durdurmak için Ctrl+C.\n", DIM)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass
    finally:
        stop_phone()
        service.stop_reminders()
        say_line(f"\n{service.usage_summary()}", DIM)
        say_line("Sunucu kapatıldı.", CYAN)


def sound_test(config: Config) -> None:
    from .voice import Listener, Speaker

    say_line("1) Ses çıkışı test ediliyor...", BOLD)
    speaker = Speaker(config)
    if speaker.available:
        speaker.say("Merhaba, ben Jarvis. Sesimi duyuyorsanız hoparlör çalışıyor.")
        say_line(f"   Kullanılan ses motoru: {speaker.engine}", GREEN)
    else:
        say_line("   Ses çıkışı bulunamadı (edge-tts/pygame kurulu mu?).", RED)
    say_line("2) Mikrofon test ediliyor: bir saniye sessiz kalın...", BOLD)
    try:
        listener = Listener(config)
        listener.calibrate()
        say_line(f"   Ortam gürültüsü: {listener.noise:.0f}, konuşma eşiği: {listener.threshold:.0f}", DIM)
        say_line("   Şimdi bir cümle söyleyin (10 saniye içinde)...", BOLD)
        text = listener.listen(max_wait=10)
        if text is None:
            say_line("   Ses algılanmadı. Mikrofon seçili ve açık mı? (--mikrofonlar ile listeleyin)", RED)
        elif text:
            say_line(f"   Anlaşılan: {text}", GREEN)
        else:
            say_line("   Ses algılandı ama anlaşılamadı. Biraz daha yakından ve net konuşmayı deneyin.", YELLOW)
    except Exception as exc:
        say_line(f"   Mikrofon hatası: {exc}", RED)
        say_line(AUDIO_HINT, YELLOW)


def main(argv: list[str] | None = None) -> int:
    import argparse

    from .config import load_config

    _setup_console()
    parser = argparse.ArgumentParser(description="Jarvis - Claude ile çalışan kişisel asistan")
    parser.add_argument("--yazi", action="store_true", help="Sesli değil, klavyeden yazarak konuş")
    parser.add_argument("--konus", action="store_true", help="Yazı modunda cevapları sesli de oku")
    parser.add_argument("--sunucu", action="store_true",
                        help="Mikrofonsuz sunucu modu: sadece telefon (Telegram/web) kanalları")
    parser.add_argument("--ses-testi", action="store_true", help="Hoparlör ve mikrofonu test et")
    parser.add_argument("--mikrofonlar", action="store_true", help="Bağlı mikrofonları listele")
    parser.add_argument("--model", help="Bu çalıştırma için Claude modeli (örn. claude-haiku-5-5)")
    args = parser.parse_args(argv)

    config = load_config()
    if args.model:
        config.model = args.model

    if args.mikrofonlar:
        try:
            from .voice import list_microphones

            mics = list_microphones()
        except Exception as exc:
            say_line(f"Mikrofonlar okunamadı: {exc}", RED)
            say_line(AUDIO_HINT, YELLOW)
            return 1
        say_line("Mikrofonlar (.env içinde JARVIS_MIC=numara ile seçebilirsiniz):", BOLD)
        say_line(mics)
        return 0
    if args.ses_testi:
        sound_test(config)
        return 0
    if not check_api_key(config):
        return 1
    if args.sunucu:
        run_server(config)
    elif args.yazi:
        run_text(config, speak=args.konus)
    else:
        run_voice(config)
    return 0
