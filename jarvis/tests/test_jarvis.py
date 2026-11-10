"""Jarvis testleri: python -m pytest tests  (gerçek API çağrısı yapmaz)."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import anthropic
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jarvis_core import brain as brain_mod  # noqa: E402
from jarvis_core.app import JarvisContext  # noqa: E402
from jarvis_core.brain import Brain, sanitize_content  # noqa: E402
from jarvis_core.config import Config, load_config  # noqa: E402
from jarvis_core.memory import MemoryStore  # noqa: E402
from jarvis_core.reminders import ReminderManager, parse_when  # noqa: E402
from jarvis_core.tools import ToolRegistry, build_registry, computer, info  # noqa: E402
from jarvis_core.voice import clean_for_speech, find_wake_word, is_exit_command  # noqa: E402


# --------------------------------------------------------------- yardımcılar
def block(type_, **kw):
    return SimpleNamespace(type=type_, **kw)


def response(stop, *blocks):
    usage = SimpleNamespace(input_tokens=10, output_tokens=5, cache_read_input_tokens=0,
                            cache_creation_input_tokens=0, server_tool_use=None)
    return SimpleNamespace(stop_reason=stop, content=list(blocks), usage=usage)


class FakeMessages:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append({**kwargs, "messages": list(kwargs["messages"])})
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def fake_client(*responses):
    msgs = FakeMessages(responses)
    return SimpleNamespace(beta=SimpleNamespace(messages=msgs)), msgs


@pytest.fixture
def ctx(tmp_path):
    cfg = Config(data_dir=tmp_path, api_key="test")
    memory = MemoryStore(tmp_path)
    reminders = ReminderManager(tmp_path, notify=lambda t: None)
    return JarvisContext(cfg, memory, reminders)


def make_brain(ctx, *responses, mode="text"):
    client, msgs = fake_client(*responses)
    registry = build_registry(ctx)
    return Brain(ctx.config, registry, ctx.memory, mode=mode, client=client), msgs


# ------------------------------------------------------------------- beyin
def test_simple_reply_and_request_shape(ctx):
    brain, msgs = make_brain(ctx, response("end_turn", block("thinking", thinking=""), block("text", text="Merhaba efendim.")))
    reply = brain.ask("selam")
    assert reply.ok and reply.text == "Merhaba efendim."
    call = msgs.calls[0]
    assert call["model"] == "claude-opus-5-5"
    assert call["fallbacks"] == "default" and call["betas"] == ["server-side-fallback-2026-07-01"]
    assert call["output_config"] == {"effort": "low"}
    assert call["cache_control"] == {"type": "ephemeral"}
    assert "thinking" not in call  # Opus 5.5'te düşünme her zaman açık; parametre gönderilmez
    tool_types = [t.get("type") for t in call["tools"]]
    assert "web_search_20260209" in tool_types and "web_fetch_20260209" in tool_types
    first = call["messages"][0]
    assert first["role"] == "user" and first["content"].startswith("[") and first["content"].endswith("selam")
    # Asistan cevabı (düşünme bloğu dahil) geçmişe değiştirilmeden eklenir
    assert brain.messages[1]["content"][0].type == "thinking"


def test_tool_loop_runs_tool_and_returns_result(ctx):
    brain, msgs = make_brain(
        ctx,
        response("tool_use", block("text", text="Kaydediyorum."),
                 block("tool_use", id="tu_1", name="remember", input={"fact": "Kullanıcının adı Ali."})),
        response("end_turn", block("text", text="Adınızı hatırlayacağım, Ali.")),
    )
    reply = brain.ask("benim adım Ali, unutma")
    assert reply.text == "Adınızı hatırlayacağım, Ali."
    assert reply.tools_used == ["remember"]
    assert "Ali" in ctx.memory.list_facts()
    second_call_messages = msgs.calls[1]["messages"]
    tool_result = second_call_messages[-1]["content"][0]
    assert tool_result["type"] == "tool_result" and tool_result["tool_use_id"] == "tu_1"
    assert "is_error" not in tool_result


def test_invalid_tool_input_returns_error_result(ctx):
    brain, msgs = make_brain(
        ctx,
        response("tool_use", block("tool_use", id="tu_1", name="set_volume", input={"level": "çok"})),
        response("end_turn", block("text", text="Ses seviyesini anlayamadım.")),
    )
    brain.ask("sesi çok yap")
    result = msgs.calls[1]["messages"][-1]["content"][0]
    assert result["is_error"] is True and "integer" in result["content"]


def test_refusal_rolls_back_history(ctx):
    brain, _ = make_brain(ctx, response("refusal"))
    reply = brain.ask("yasaklı bir şey")
    assert not reply.ok
    assert brain.messages == []


def test_api_error_is_friendly_and_rolls_back(ctx):
    import httpx2

    err = anthropic.APIConnectionError(request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages"))
    brain, _ = make_brain(ctx, err)
    reply = brain.ask("merhaba")
    assert not reply.ok and "İnternet" in reply.text
    assert brain.messages == []


def test_pause_turn_continues(ctx):
    brain, msgs = make_brain(
        ctx,
        response("pause_turn", block("server_tool_use", id="srv_1", name="web_search", input={"query": "dolar kuru"})),
        response("end_turn", block("text", text="Dolar 34 lira.")),
    )
    assert brain.ask("dolar kaç").text == "Dolar 34 lira."
    assert len(msgs.calls) == 2
    # Devam isteğine fazladan kullanıcı mesajı eklenmez; son mesaj duraklatılan asistan turudur
    assert msgs.calls[1]["messages"][-1]["role"] == "assistant"


def test_sanitize_drops_blocks_before_fallback():
    blocks = [
        block("thinking", thinking=""),
        block("text", text="Kısmi"),
        block("tool_use", id="t1", name="x", input={}),
        block("server_tool_use", id="s1", name="web_search", input={}),
        block("fallback"),
        block("thinking", thinking=""),
        block("text", text="Cevap"),
    ]
    kept, start = sanitize_content(blocks)
    assert [b.type for b in kept] == ["text", "fallback", "thinking", "text"]
    assert [b.type for b in kept[start:]] == ["thinking", "text"]


def test_no_fallback_kept_as_is():
    blocks = [block("thinking", thinking=""), block("text", text="a")]
    kept, start = sanitize_content(blocks)
    assert kept == blocks and start == 0


def test_haiku_uses_basic_search_and_no_fallbacks(ctx):
    ctx.config.model = "claude-haiku-5-5"
    brain, msgs = make_brain(ctx, response("end_turn", block("text", text="ok")))
    brain.ask("test")
    call = msgs.calls[0]
    assert "fallbacks" not in call and "betas" not in call
    assert [t.get("type") for t in call["tools"] if "type" in t] == ["web_search_20250305"]


def test_session_resets_after_idle(ctx, monkeypatch):
    brain, _ = make_brain(ctx, response("end_turn", block("text", text="1")), response("end_turn", block("text", text="2")))
    brain.ask("bir")
    assert len(brain.messages) == 2
    brain.last_activity -= brain_mod.SESSION_IDLE_SECONDS + 1
    brain.ask("iki")
    assert len(brain.messages) == 2  # eski oturum silindi, yeni oturum başladı


def test_system_prompt_contains_memory_and_mode(ctx):
    ctx.memory.remember("Kullanıcı kahveyi şekersiz içer.")
    brain, _ = make_brain(ctx, mode="voice")
    assert "kahveyi şekersiz" in brain.system
    assert "SESLİ" in brain.system


# ------------------------------------------------------------ araç sistemi
def test_registry_specs_are_valid_and_unique(ctx):
    registry = build_registry(ctx)
    names = registry.names()
    assert len(names) == len(set(names))
    for spec in registry.specs():
        assert set(spec) == {"name", "description", "input_schema"}
        schema = spec["input_schema"]
        assert schema["type"] == "object" and schema["additionalProperties"] is False
        assert set(schema["required"]) <= set(schema["properties"])
        json.dumps(spec)
    assert "ha_control" not in names  # Home Assistant ayarlı değil


def test_registry_validation():
    reg = ToolRegistry()
    reg.add("t", "test", lambda n, flag=False: f"{n}-{flag}",
            {"n": {"type": "integer", "minimum": 0, "maximum": 5}, "flag": {"type": "boolean"}}, ["n"])
    assert reg.run("t", {"n": 3}).content == "3-False"
    assert reg.run("t", {"n": True}).is_error            # bool, integer yerine geçmez
    assert reg.run("t", {"n": 9}).is_error               # sınır dışı
    assert reg.run("t", {}).is_error                     # eksik
    assert reg.run("t", {"n": 1, "x": 2}).is_error       # bilinmeyen parametre
    assert reg.run("yok", {}).is_error


def test_tool_exception_does_not_crash():
    reg = ToolRegistry()
    reg.add("boom", "patlar", lambda: 1 / 0)
    result = reg.run("boom", {})
    assert result.is_error and "ZeroDivisionError" in result.content


def test_open_website(monkeypatch):
    opened = []
    monkeypatch.setattr(computer.webbrowser, "open", opened.append)
    computer.open_website("youtube.com")
    computer.open_website("en iyi pizza tarifi")
    assert opened[0] == "https://youtube.com"
    assert opened[1].startswith("https://www.google.com/search?q=en+iyi+pizza")
    with pytest.raises(computer.ToolError):
        computer.open_website("file://C:/Windows/program.exe")


def test_open_path_blocks_programs(tmp_path, monkeypatch):
    exe = tmp_path / "virus.exe"
    exe.write_text("x")
    with pytest.raises(computer.ToolError):
        computer.open_path(str(exe))
    doc = tmp_path / "rapor.pdf"
    doc.write_text("x")
    opened = []
    monkeypatch.setattr(computer, "open_with_default_app", opened.append)
    computer.open_path(str(doc))
    assert opened == [str(doc)]


def test_app_name_rejects_shell_characters():
    with pytest.raises(computer.ToolError):
        computer.open_app("notepad & del *")


def test_search_files(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    (tmp_path / "Documents").mkdir()
    (tmp_path / "Documents" / "Fatura_Kasım.pdf").write_text("x")
    (tmp_path / ".gizli").mkdir()
    (tmp_path / ".gizli" / "fatura_gizli.pdf").write_text("x")
    out = computer.search_files("fatura")
    assert "Fatura_Kasım.pdf" in out and "fatura_gizli" not in out


def test_close_app_protects_system_processes():
    with pytest.raises(computer.ToolError):
        computer.close_app("py")  # 3 harften kısa


def test_system_status_runs():
    out = computer.system_status()
    assert "İşlemci" in out and "Bellek" in out


def test_weather_formats(monkeypatch):
    class Resp:
        def __init__(self, data):
            self._data = data

        def raise_for_status(self):
            pass

        def json(self):
            return self._data

    def fake_get(url, params=None, timeout=None):
        if "geocoding" in url:
            return Resp({"results": [{"name": "Ankara", "admin1": "Ankara", "country": "Türkiye", "latitude": 39.9, "longitude": 32.8}]})
        return Resp({
            "current": {"temperature_2m": 12.3, "apparent_temperature": 10.1, "relative_humidity_2m": 60, "weather_code": 2, "wind_speed_10m": 9},
            "daily": {"time": ["2026-11-10", "2026-11-11"], "weather_code": [2, 61], "temperature_2m_max": [14, 11],
                      "temperature_2m_min": [5, 4], "precipitation_probability_max": [10, 80]},
        })

    monkeypatch.setattr(info.requests, "get", fake_get)
    out = info.get_weather("Ankara", days=2)
    assert "Ankara" in out and "parçalı bulutlu" in out and "Yarın" in out and "yağmurlu" in out


# --------------------------------------------------- hafıza ve hatırlatıcı
def test_memory_remember_forget(tmp_path):
    m = MemoryStore(tmp_path)
    m.remember("Kullanıcının kedisinin adı Pamuk.")
    assert "zaten" in m.remember("kullanıcının kedisinin adı pamuk.")
    assert "Pamuk" in MemoryStore(tmp_path).list_facts()  # diske kaydedildi
    assert "Unutuldu" in m.forget("pamuk")
    assert "yok" in m.list_facts()


def test_turkish_casefold_in_memory(tmp_path):
    m = MemoryStore(tmp_path)
    m.remember("Kullanıcı IŞIK sanatçısını sever.")
    assert "Unutuldu" in m.forget("ışık")


def test_parse_when():
    now = datetime(2026, 11, 10, 14, 0)
    assert parse_when(in_minutes=10, now=now) == now + timedelta(minutes=10)
    assert parse_when("2026-11-10T18:30", now=now) == datetime(2026, 11, 10, 18, 30)
    assert parse_when("09:00", now=now) == datetime(2026, 11, 11, 9, 0)  # geçtiyse yarın
    with pytest.raises(ValueError):
        parse_when("yarın akşam", now=now)


def test_reminders_fire_and_repeat(tmp_path):
    r = ReminderManager(tmp_path)
    soon = datetime.now() + timedelta(seconds=1)
    r.add("Su iç", soon, "daily")
    r.add("Tek sefer", soon)
    due = r.pop_due(now=soon + timedelta(seconds=1))
    assert sorted(d["message"] for d in due) == ["Su iç", "Tek sefer"]
    remaining = ReminderManager(tmp_path).items  # diskten
    assert [x["message"] for x in remaining] == ["Su iç"]
    assert datetime.fromisoformat(remaining[0]["due"]) > soon + timedelta(hours=23)


def test_reminder_tool_via_registry(ctx):
    registry = build_registry(ctx)
    out = registry.run("set_reminder", {"message": "Çayı kapat", "in_minutes": 5})
    assert not out.is_error and "#1" in out.content
    assert "Çayı kapat" in registry.run("list_reminders", {}).content
    assert not registry.run("cancel_reminder", {"reminder_id": 1}).is_error
    assert registry.run("cancel_reminder", {"reminder_id": 1}).is_error


# --------------------------------------------------------------------- ses
@pytest.mark.parametrize("text,expected", [
    ("Jarvis müzik aç", (True, "müzik aç")),
    ("hey jarvis", (True, "")),
    ("Carvis hava nasıl", (True, "hava nasıl")),
    ("ışıkları kapat Jarvis", (True, "ışıkları kapat")),
    ("Jarvis'e sor bakalım", (True, "sor bakalım")),
    ("bugün servis geç geldi", (False, "")),
    ("cervis saat kaç", (True, "saat kaç")),
    ("televizyonu aç", (False, "")),
])
def test_wake_word(text, expected):
    assert find_wake_word(text, Config().wake_words) == expected


def test_clean_for_speech():
    text = "**Hava** %80 nemli, 12°C. Detay: https://ornek.com 🌧️\n- madde"
    out = clean_for_speech(text)
    assert out == "Hava yüzde 80 nemli, 12 derece. Detay: madde"


def test_exit_command():
    assert is_exit_command("kendini kapat")
    assert not is_exit_command("bilgisayarı kapat")


# ------------------------------------------------------------------ ayarlar
def test_load_config_from_env_file(tmp_path, monkeypatch):
    for key in list(__import__("os").environ):
        if key.startswith(("JARVIS_", "ANTHROPIC_", "HA_")):
            monkeypatch.delenv(key, raising=False)
    env = tmp_path / ".env"
    env.write_text('ANTHROPIC_API_KEY="sk-ant-test"\nJARVIS_MODEL=claude-sonnet-5-5\nJARVIS_WAKE_WORDS=Cuma, cumi\n'
                   "JARVIS_FALLBACKS=hayır\nHA_URL=http://ev:8123/\n", encoding="utf-8")
    cfg = load_config(env)
    assert cfg.api_key == "sk-ant-test"
    assert cfg.model == "claude-sonnet-5-5"
    assert cfg.wake_words == ["cuma", "cumi"]
    assert cfg.fallbacks_enabled is False
    assert cfg.ha_url == "http://ev:8123" and not cfg.smarthome_enabled


# ------------------------------------------------------- mikrofon (sahte)
class FakeStream:
    """Önce sessizlik, sonra 'konuşma' (yüksek genlik), sonra tekrar sessizlik verir."""

    def __init__(self, plan):
        self.plan = list(plan)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self, n):
        from array import array

        amp = self.plan.pop(0) if self.plan else 0
        return array("h", [amp if i % 2 else -amp for i in range(n)]).tobytes(), False


def make_listener(plan):
    from jarvis_core import voice

    listener = voice.Listener.__new__(voice.Listener)
    listener.sd = SimpleNamespace(RawInputStream=lambda **kw: FakeStream(plan))
    listener.device = None
    listener.noise, listener.threshold = 100.0, 350.0
    return listener


def test_record_phrase_captures_speech_until_silence():
    from jarvis_core.voice import BLOCK

    plan = [50] * 20 + [3000] * 30 + [50] * 40 + [3000] * 10  # sondaki konuşma ayrı bir cümle
    raw = make_listener(plan).record_phrase()
    blocks = len(raw) // (BLOCK * 2)
    assert 30 + 30 <= blocks <= 13 + 30 + 31  # ön kayıt + konuşma + ~0.9 sn sessizlik


def test_record_phrase_ignores_clicks_and_times_out():
    assert make_listener([50] * 5 + [3000] * 2 + [50] * 60).record_phrase() == b""
    assert make_listener([50] * 400).record_phrase(max_wait=0.0) is None


def test_empty_response_not_added_to_history(ctx):
    brain, _ = make_brain(ctx, response("end_turn"), response("end_turn", block("text", text="Buradayım.")))
    assert brain.ask("orada mısın").text == "Tamam."
    assert all(m["role"] == "user" for m in brain.messages)
    assert brain.ask("cevap ver").text == "Buradayım."
