"""Telefon kanalları (Telegram, web) ve servis katmanı testleri. Gerçek ağ/API kullanmaz."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jarvis_core.brain import Reply  # noqa: E402
from jarvis_core.channels.telegram_bot import TelegramBot  # noqa: E402
from jarvis_core.channels.web import WebInterface  # noqa: E402
from jarvis_core.config import Config, load_config  # noqa: E402
from jarvis_core.service import JarvisService  # noqa: E402


class FakeService:
    def __init__(self):
        self.asked = []
        self.resets = []
        self.memory = SimpleNamespace(list_facts=lambda: "Kayıt yok.")

    def ask(self, channel, text, mode="text", on_status=None):
        self.asked.append((channel, text, mode))
        return Reply(f"cevap: {text}")

    def reset_channel(self, channel):
        self.resets.append(channel)


class FakeTelegramAPI:
    """Telegram HTTP API'sini taklit eder; gönderilen mesajları kaydeder."""

    def __init__(self, get_file_path="voice/file_1.ogg"):
        self.calls = []
        self.get_file_path = get_file_path

    def __call__(self, method, params=None, files=None, timeout=None):
        self.calls.append({"method": method, "params": params or {}, "files": files})
        if method == "getFile":
            return {"ok": True, "result": {"file_path": self.get_file_path}}
        if method == "getMe":
            return {"ok": True, "result": {"username": "test_bot"}}
        return {"ok": True, "result": {}}

    def sent(self, method="sendMessage"):
        return [c for c in self.calls if c["method"] == method]

    def texts(self):
        return [c["params"].get("text", "") for c in self.sent("sendMessage")]


def make_bot(tmp_path, pair_code="", allowed=None, voice_reply=True):
    cfg = Config(data_dir=tmp_path, telegram_token="T", telegram_pair_code=pair_code,
                 telegram_allowed=allowed or [], telegram_voice_reply=voice_reply)
    api = FakeTelegramAPI()
    bot = TelegramBot(FakeService(), cfg, api=api)
    return bot, api


def text_update(chat_id, text):
    return {"update_id": 1, "message": {"chat": {"id": chat_id}, "text": text}}


def voice_update(chat_id):
    return {"update_id": 2, "message": {"chat": {"id": chat_id}, "voice": {"file_id": "f1"}}}


# ------------------------------------------------------------ Telegram güvenlik
def test_telegram_blocks_unauthorized(tmp_path):
    bot, api = make_bot(tmp_path)
    bot.handle_update(text_update(999, "bilgisayarı kapat"))
    assert isinstance(bot.service, FakeService) and bot.service.asked == []  # komut ÇALIŞMADI
    assert any("tanımıyorum" in t and "999" in t for t in api.texts())


def test_telegram_pairing_authorizes_and_persists(tmp_path):
    bot, api = make_bot(tmp_path, pair_code="gizli42")
    bot.handle_update(text_update(555, "gizli42"))
    assert "555" in bot.allowed
    assert any("Eşleştirildi" in t for t in api.texts())
    # Kalıcı: yeni bir bot aynı dosyadan yetkiyi okur
    bot2, _ = make_bot(tmp_path, pair_code="gizli42")
    assert "555" in bot2.allowed
    # Yetkili artık komut çalıştırabilir
    bot.handle_update(text_update(555, "saat kaç"))
    assert bot.service.asked[-1] == ("telegram:555", "saat kaç", "phone")


def test_telegram_wrong_pair_code_denied(tmp_path):
    bot, _ = make_bot(tmp_path, pair_code="dogru")
    bot.handle_update(text_update(7, "yanlis"))
    assert "7" not in bot.allowed and bot.service.asked == []


def test_telegram_allowed_from_config(tmp_path):
    bot, api = make_bot(tmp_path, allowed=["42"])
    bot.handle_update(text_update(42, "Spotify'ı aç"))
    assert bot.service.asked == [("telegram:42", "Spotify'ı aç", "phone")]
    assert "cevap: Spotify'ı aç" in api.texts()


def test_telegram_slash_commands(tmp_path):
    bot, api = make_bot(tmp_path, allowed=["42"])
    bot.handle_update(text_update(42, "/yeni"))
    assert bot.service.resets == ["telegram:42"]
    bot.handle_update(text_update(42, "/yardim"))
    assert any("Komutlar" in t for t in api.texts())


def test_telegram_voice_message(tmp_path, monkeypatch):
    bot, api = make_bot(tmp_path, allowed=["42"], voice_reply=True)
    monkeypatch.setattr(bot, "_download", lambda fp: b"ogg-bytes")
    import jarvis_core.voice as voice_mod

    monkeypatch.setattr(voice_mod, "transcribe_bytes", lambda cfg, data: "ışıkları aç")
    monkeypatch.setattr(voice_mod, "synthesize_mp3", lambda cfg, text: b"MP3DATA")
    bot.handle_update(voice_update(42))
    assert bot.service.asked[-1] == ("telegram:42", "ışıkları aç", "phone")
    assert any("🎤" in t and "ışıkları aç" in t for t in api.texts())  # tanınan metni gösterdi
    assert api.sent("sendAudio") and api.sent("sendAudio")[0]["files"]  # sesli cevap gönderildi


def test_telegram_poll_advances_offset(tmp_path):
    bot, api = make_bot(tmp_path, allowed=["42"])

    def api_with_updates(method, params=None, files=None, timeout=None):
        if method == "getUpdates":
            return {"ok": True, "result": [text_update(42, "merhaba")]}
        return api(method, params, files, timeout)

    bot._api = api_with_updates
    assert bot.poll_once(timeout=0) == 1
    assert bot._offset == 2  # update_id + 1
    assert bot.service.asked[-1][1] == "merhaba"


def test_telegram_reminder_notifies_allowed(tmp_path):
    bot, api = make_bot(tmp_path, allowed=["1", "2"])
    bot.notify_reminder("Çayın hazır")
    targets = {c["params"]["chat_id"] for c in api.sent("sendMessage")}
    assert targets == {"1", "2"}
    assert all("⏰" in t for t in api.texts())


# ------------------------------------------------------------------- Web arayüzü
@pytest.fixture
def web_server(tmp_path):
    cfg = Config(data_dir=tmp_path, web_token="gizlianahtar", web_host="127.0.0.1", web_port=0)
    service = FakeService()
    web = WebInterface(service, cfg)
    web.start()
    port = web._server.server_address[1]
    yield web, service, port
    web.stop()


def _http(port, path, method="GET", token=None, body=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-Jarvis-Token"] = token
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()


def test_web_serves_page(web_server):
    _web, _service, port = web_server
    status, body = _http(port, "/")
    assert status == 200 and "JARVIS" in body


def test_web_requires_token(web_server):
    _web, service, port = web_server
    status, _ = _http(port, "/api/ask", method="POST", body={"text": "merhaba"})
    assert status == 401 and service.asked == []
    status, _ = _http(port, "/api/ask", method="POST", token="yanlis", body={"text": "merhaba"})
    assert status == 401 and service.asked == []


def test_web_ask_with_token(web_server):
    _web, service, port = web_server
    status, body = _http(port, "/api/ask", method="POST", token="gizlianahtar", body={"text": "selam"})
    assert status == 200
    data = json.loads(body)
    assert data["ok"] and data["reply"] == "cevap: selam"
    assert service.asked == [("web", "selam", "phone")]


def test_web_events_deliver_reminders(web_server):
    web, _service, port = web_server
    web.add_event("İlacını al")
    status, body = _http(port, "/api/events?after=0", token="gizlianahtar")
    assert status == 200
    reminders = json.loads(body)["reminders"]
    assert reminders and reminders[0]["text"] == "İlacını al"
    # Aynı id'den sonrası boş gelir
    _status, body2 = _http(port, f"/api/events?after={reminders[0]['id']}", token="gizlianahtar")
    assert json.loads(body2)["reminders"] == []


# ------------------------------------------------------------------- Servis katmanı
class FakeMessages:
    def __init__(self):
        self.count = 0

    def create(self, **kwargs):
        self.count += 1
        usage = SimpleNamespace(input_tokens=5, output_tokens=2, cache_read_input_tokens=0,
                                cache_creation_input_tokens=0, server_tool_use=None)
        return SimpleNamespace(stop_reason="end_turn",
                               content=[SimpleNamespace(type="text", text="tamam")], usage=usage)


def fake_client():
    return SimpleNamespace(beta=SimpleNamespace(messages=FakeMessages()))


def test_service_separate_contexts_shared_memory(tmp_path):
    cfg = Config(data_dir=tmp_path, api_key="x")
    svc = JarvisService(cfg, client=fake_client())
    svc.ask("masaüstü", "ben Ali")
    svc.ask("telegram:1", "merhaba")
    # Her kanalın kendi konuşması var
    assert set(svc._brains) == {"masaüstü", "telegram:1"}
    assert len(svc._brains["masaüstü"].messages) == 2
    assert len(svc._brains["telegram:1"].messages) == 2
    # Hafıza ortak (bir kanaldan kaydedilen diğerinin sistem isteminde görünür)
    svc.memory.remember("Kullanıcının adı Ali.")
    svc.reset_channel("telegram:1")
    assert "Ali" in svc.get_brain("telegram:1").system


def test_service_reminder_fanout_isolates_errors(tmp_path):
    svc = JarvisService(Config(data_dir=tmp_path, api_key="x"), client=fake_client())
    got = []
    svc.add_reminder_listener(lambda t: (_ for _ in ()).throw(RuntimeError("patla")))
    svc.add_reminder_listener(got.append)
    svc._fan_reminder("hatırlatma")
    assert got == ["hatırlatma"]  # bir dinleyicinin hatası diğerini engellemedi


def test_service_usage_aggregates(tmp_path):
    svc = JarvisService(Config(data_dir=tmp_path, api_key="x"), client=fake_client())
    svc.ask("a", "x")
    svc.ask("b", "y")
    summary = svc.usage_summary()
    assert "2 istek" in summary


# ------------------------------------------------------------------- Ayarlar
def test_config_phone_parsing(tmp_path, monkeypatch):
    for key in list(__import__("os").environ):
        if key.startswith(("JARVIS_", "ANTHROPIC_", "HA_")):
            monkeypatch.delenv(key, raising=False)
    env = tmp_path / ".env"
    env.write_text(
        "ANTHROPIC_API_KEY=k\n"
        "JARVIS_TELEGRAM_TOKEN=123:ABC\n"
        "JARVIS_TELEGRAM_ALLOWED=11, 22 ; 33\n"
        "JARVIS_TELEGRAM_PAIR_CODE=kod\n"
        "JARVIS_WEB=evet\n"
        "JARVIS_WEB_PORT=9000\n"
        "JARVIS_PORTABLE=1\n",
        encoding="utf-8",
    )
    cfg = load_config(env)
    assert cfg.telegram_enabled and cfg.telegram_token == "123:ABC"
    assert cfg.telegram_allowed == ["11", "22", "33"]
    assert cfg.telegram_pair_code == "kod"
    assert cfg.web_enabled and cfg.web_port == 9000
    assert cfg.portable and cfg.phone_enabled
