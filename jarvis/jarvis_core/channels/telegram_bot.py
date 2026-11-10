"""Telegram botu: telefondan Jarvis'e yazarak veya sesli mesajla ulaşmanızı sağlar.

GÜVENLİK: Bot ev bilgisayarınızı kontrol edebildiği için yalnızca yetkili sohbetlere
cevap verir. Yetkisiz biri bota yazsa bile hiçbir komut çalışmaz; yetkiyi yalnızca
eşleştirme kodunu (JARVIS_TELEGRAM_PAIR_CODE) göndererek ya da sohbet kimliğinizi
JARVIS_TELEGRAM_ALLOWED'a ekleyerek alırsınız.
"""

from __future__ import annotations

import threading
from typing import Any, Callable

import requests

from ..storage import load_json, save_json

HELP = (
    "Ben Jarvis. Buraya yazdıklarınızı ev bilgisayarımda yaparım.\n"
    "Sesli mesaj da gönderebilirsiniz.\n\n"
    "Komutlar:\n"
    "/yeni – yeni konuşma başlat\n"
    "/hafiza – hakkınızda hatırladıklarım\n"
    "/yardim – bu yardım"
)


class TelegramBot:
    def __init__(self, service, config, api: Callable[..., dict] | None = None,
                 on_log: Callable[[str], None] | None = None):
        self.service = service
        self.config = config
        self.token = config.telegram_token
        self.pair_code = (config.telegram_pair_code or "").strip()
        self.voice_reply = config.telegram_voice_reply
        self.log = on_log or (lambda msg: print(msg))
        self._api = api or self._http_api
        self._stop = threading.Event()
        self._offset = 0
        self._greeted: set[str] = set()
        self._allowed_path = config.data_dir / "telegram_allowed.json"
        stored = load_json(self._allowed_path, [])
        self.allowed: set[str] = {str(x) for x in stored} | {str(x) for x in config.telegram_allowed}

    # ---- düşük seviye Telegram API ----
    def _http_api(self, method: str, params: dict | None = None, files: dict | None = None,
                  timeout: float = 65) -> dict:
        url = f"https://api.telegram.org/bot{self.token}/{method}"
        resp = requests.post(url, data=params or {}, files=files, timeout=timeout)
        return resp.json()

    def _download(self, file_path: str) -> bytes:
        url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        return resp.content

    def _send(self, chat_id: Any, text: str) -> None:
        for i in range(0, len(text) or 1, 4000):  # Telegram mesaj sınırı
            self._api("sendMessage", {"chat_id": chat_id, "text": text[i:i + 4000]})

    def _send_voice(self, chat_id: Any, text: str) -> None:
        from .. import voice as voice_mod

        data = voice_mod.synthesize_mp3(self.config, text)
        if data:
            self._api("sendAudio", {"chat_id": chat_id, "title": "Jarvis"}, files={"audio": ("jarvis.mp3", data)})

    def _typing(self, chat_id: Any) -> None:
        try:
            self._api("sendChatAction", {"chat_id": chat_id, "action": "typing"})
        except Exception:
            pass

    # ---- yetkilendirme ----
    def _authorize(self, chat_id: str, text: str) -> str:
        """'ok', 'paired' veya 'denied' döndürür."""
        if chat_id in self.allowed:
            return "ok"
        if self.pair_code and text.strip() == self.pair_code:
            self.allowed.add(chat_id)
            save_json(self._allowed_path, sorted(self.allowed))
            self.log(f"[telegram] yeni cihaz eşleştirildi: {chat_id}")
            return "paired"
        return "denied"

    # ---- mesaj işleme ----
    def handle_update(self, update: dict) -> None:
        message = update.get("message") or update.get("edited_message")
        if not message:
            return
        chat_id = str(message.get("chat", {}).get("id", ""))
        if not chat_id:
            return
        is_voice = "voice" in message or "audio" in message
        text = (message.get("text") or message.get("caption") or "").strip()

        status = self._authorize(chat_id, text)
        if status == "denied":
            self._send(chat_id, "Üzgünüm, sizi tanımıyorum. Bu bot özeldir.\n"
                                f"Sohbet kimliğiniz: {chat_id}\n"
                                "Yetki için eşleştirme kodunu gönderin ya da bu kimliği sahibine iletin.")
            self.log(f"[telegram] yetkisiz erişim engellendi: {chat_id}")
            return
        if status == "paired":
            self._send(chat_id, "Eşleştirildi! Artık bana komut verebilirsiniz. /yardim ile başlayın.")
            return

        channel = f"telegram:{chat_id}"
        if is_voice:
            try:
                text = self._transcribe_voice(message)
            except Exception as exc:
                self._send(chat_id, f"Sesli mesajı çözemedim: {exc}\nYazarak dener misiniz?")
                return
            if not text:
                self._send(chat_id, "Sesli mesajı anlayamadım, tekrar dener misiniz?")
                return
            self._send(chat_id, f"🎤 \"{text}\"")

        if not text:
            if chat_id not in self._greeted:
                self._greeted.add(chat_id)
                self._send(chat_id, HELP)
            return

        low = text.lower()
        if low in ("/start", "/baslat", "/yardim", "/help"):
            self._greeted.add(chat_id)
            self._send(chat_id, HELP)
            return
        if low == "/yeni":
            self.service.reset_channel(channel)
            self._send(chat_id, "Yeni konuşma başladı.")
            return
        if low in ("/hafiza", "/hafıza"):
            self._send(chat_id, self.service.memory.list_facts())
            return

        self._typing(chat_id)
        reply = self.service.ask(channel, text, mode="phone")
        self._send(chat_id, reply.text)
        if is_voice and self.voice_reply and reply.ok:
            self._send_voice(chat_id, reply.text)

    def _transcribe_voice(self, message: dict) -> str:
        from .. import voice as voice_mod

        media = message.get("voice") or message.get("audio") or {}
        file_id = media.get("file_id")
        if not file_id:
            return ""
        info = self._api("getFile", {"file_id": file_id})
        file_path = info.get("result", {}).get("file_path")
        if not file_path:
            raise RuntimeError("dosya alınamadı")
        data = self._download(file_path)
        return voice_mod.transcribe_bytes(self.config, data)

    # ---- hatırlatıcı bildirimi (tüm yetkili cihazlara) ----
    def notify_reminder(self, text: str) -> None:
        for chat_id in list(self.allowed):
            try:
                self._send(chat_id, f"⏰ {text}")
            except Exception:
                pass

    # ---- ana döngü ----
    def poll_once(self, timeout: int = 50) -> int:
        resp = self._api("getUpdates", {"offset": self._offset, "timeout": timeout}, timeout=timeout + 15)
        updates = resp.get("result", []) if resp.get("ok", True) else []
        for update in updates:
            self._offset = max(self._offset, update.get("update_id", 0) + 1)
            try:
                self.handle_update(update)
            except Exception as exc:
                self.log(f"[telegram] mesaj işlenemedi: {exc}")
        return len(updates)

    def run(self) -> None:
        # Başlarken birikmiş eski mesajları atla.
        try:
            resp = self._api("getUpdates", {"offset": -1, "timeout": 0}, timeout=20)
            for update in resp.get("result", []):
                self._offset = max(self._offset, update.get("update_id", 0) + 1)
            me = self._api("getMe", {}, timeout=20)
            uname = me.get("result", {}).get("username")
            self.log(f"[telegram] bot hazır: @{uname}" if uname else "[telegram] bot hazır.")
        except Exception as exc:
            self.log(f"[telegram] başlatılamadı: {exc}")
            return
        import time as _time

        while not self._stop.is_set():
            try:
                self.poll_once()
            except requests.RequestException:
                _time.sleep(5)  # ağ aksaklığı: biraz bekle, yeniden dene
            except Exception as exc:
                self.log(f"[telegram] döngü hatası: {exc}")
                _time.sleep(5)

    def start(self) -> threading.Thread:
        thread = threading.Thread(target=self.run, name="telegram", daemon=True)
        thread.start()
        return thread

    def stop(self) -> None:
        self._stop.set()
