"""Jarvis'in beyni: Claude ile konuşur, araçları çalıştırır, konuşma geçmişini tutar."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

import anthropic

from .prompts import build_system_prompt

MAX_TOKENS = 16000
MAX_STEPS = 15                # bir istekte en fazla kaç model/araç turu
SESSION_IDLE_SECONDS = 20 * 60  # bu kadar sessizlikten sonra yeni oturum
MAX_HISTORY_MESSAGES = 120      # geçmiş bu kadar uzarsa yeni oturum
FALLBACK_BETA = "server-side-fallback-2026-07-01"

DAYS_TR = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]

# Milyon token başına yaklaşık dolar fiyatları (girdi, çıktı, önbellekten okuma).
PRICES = {
    "claude-opus-5-5": (4.00, 20.00, 0.20),
    "claude-sonnet-5-5": (2.00, 10.00, 0.10),
    "claude-haiku-5-5": (0.10, 0.50, 0.01),
}

# Bir fallback sınırından önce kalan bu blok türleri geri gönderilmez.
_DROP_BEFORE_FALLBACK = {"thinking", "redacted_thinking", "tool_use"}


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read: int = 0
    cache_write: int = 0
    web_searches: int = 0
    requests: int = 0

    def add(self, usage: Any) -> None:
        if usage is None:
            return
        self.requests += 1
        self.input_tokens += getattr(usage, "input_tokens", 0) or 0
        self.output_tokens += getattr(usage, "output_tokens", 0) or 0
        self.cache_read += getattr(usage, "cache_read_input_tokens", 0) or 0
        self.cache_write += getattr(usage, "cache_creation_input_tokens", 0) or 0
        stu = getattr(usage, "server_tool_use", None)
        if stu is not None:
            self.web_searches += getattr(stu, "web_search_requests", 0) or 0

    def cost(self, model: str) -> float | None:
        price = PRICES.get(model)
        if price is None:
            return None
        inp, out, cache_read = price
        total = (
            self.input_tokens * inp
            + self.cache_write * inp * 1.25
            + self.cache_read * cache_read
            + self.output_tokens * out
        ) / 1_000_000
        return total + self.web_searches * 0.01


@dataclass
class Reply:
    text: str
    ok: bool = True
    tools_used: list[str] = field(default_factory=list)


def _block_type(block: Any) -> str:
    return block.get("type", "") if isinstance(block, dict) else getattr(block, "type", "")


def _get(block: Any, key: str, default: Any = None) -> Any:
    return block.get(key, default) if isinstance(block, dict) else getattr(block, key, default)


def sanitize_content(content: list[Any]) -> tuple[list[Any], int]:
    """Bir istek güvenlik filtresine takılıp başka modele devredildiyse (fallback),
    sınırdan önceki düşünme/araç bloklarını çıkarır. (Kalan liste, başlangıç indeksi)."""
    blocks = list(content)
    last = max((i for i, b in enumerate(blocks) if _block_type(b) == "fallback"), default=-1)
    if last < 0:
        return blocks, 0
    result_ids = {_get(b, "tool_use_id") for b in blocks if _block_type(b).endswith("_tool_result")}
    kept: list[Any] = []
    for i, b in enumerate(blocks):
        t = _block_type(b)
        if i < last:
            if t in _DROP_BEFORE_FALLBACK:
                continue
            if t == "server_tool_use" and _get(b, "id") not in result_ids:
                continue
            if t not in {"text", "server_tool_use"} and not t.endswith("_tool_result"):
                continue
        kept.append(b)
    # Birden fazla fallback varsa sonuncusunun sonrası geçerli cevaptır.
    start = max(i for i, b in enumerate(kept) if _block_type(b) == "fallback") + 1
    return kept, start


def extract_text(blocks: list[Any]) -> str:
    parts = [_get(b, "text", "") for b in blocks if _block_type(b) == "text"]
    return "\n".join(p.strip() for p in parts if p and p.strip()).strip()


def friendly_error(exc: Exception) -> str:
    if isinstance(exc, anthropic.AuthenticationError):
        return "API anahtarım geçersiz görünüyor. Lütfen .env dosyasındaki ANTHROPIC_API_KEY değerini kontrol edin."
    if isinstance(exc, anthropic.PermissionDeniedError):
        return "API anahtarımın bu modele erişim izni yok."
    if isinstance(exc, anthropic.NotFoundError):
        return "Ayarlardaki model adı bulunamadı. JARVIS_MODEL değerini kontrol edin."
    if isinstance(exc, anthropic.RateLimitError):
        return "Şu an çok fazla istek gönderdim, lütfen biraz bekleyip tekrar deneyin."
    if isinstance(exc, anthropic.BadRequestError):
        msg = str(getattr(exc, "message", exc))
        if "credit balance" in msg.lower():
            return "Claude API bakiyeniz bitmiş. console.anthropic.com adresinden kredi yüklemeniz gerekiyor."
        return f"İstek reddedildi: {msg[:200]}"
    if isinstance(exc, anthropic.APIStatusError):
        return "Claude sunucuları şu an meşgul, birazdan tekrar deneyin."
    if isinstance(exc, anthropic.APIConnectionError):
        return "İnternet bağlantısı kuramadım. Bağlantınızı kontrol eder misiniz?"
    return f"Beklenmeyen bir hata oluştu: {exc}"


class Brain:
    def __init__(
        self,
        config,
        registry,
        memory,
        mode: str = "voice",
        client: Any = None,
        on_status: Callable[[str], None] | None = None,
    ):
        self.config = config
        self.registry = registry
        self.memory = memory
        self.mode = mode
        self.on_status = on_status or (lambda msg: None)
        self.client = client or anthropic.Anthropic(api_key=config.api_key or None, max_retries=3)
        self.usage = Usage()
        self.tools = self._build_tools()
        self.messages: list[dict] = []
        self.system = ""
        self.last_activity = 0.0
        self.new_session()

    # ------------------------------------------------------------- kurulum
    def _build_tools(self) -> list[dict]:
        location = {"type": "approximate", "city": self.config.city, "country": self.config.country,
                    "timezone": self.config.timezone}
        if self.config.uses_basic_web_tools:
            server_tools = [{"type": "web_search_20250305", "name": "web_search", "max_uses": 5, "user_location": location}]
        else:
            server_tools = [
                {"type": "web_search_20260209", "name": "web_search", "max_uses": 5, "user_location": location},
                {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 3},
            ]
        return self.registry.specs() + server_tools

    def new_session(self) -> None:
        """Yeni bir konuşma başlatır. Kalıcı hafıza sistem istemine eklenir."""
        self.messages = []
        self.system = build_system_prompt(self.config, self.memory.facts_for_prompt(), self.mode, self.registry.names())

    def _request_kwargs(self) -> dict:
        kwargs: dict[str, Any] = {
            "model": self.config.model,
            "max_tokens": MAX_TOKENS,
            "system": self.system,
            "messages": self.messages,
            "tools": self.tools,
            "cache_control": {"type": "ephemeral"},
        }
        if self.config.effort:
            kwargs["output_config"] = {"effort": self.config.effort}
        if self.config.fallbacks_enabled:
            # Güvenlik filtresi yanlışlıkla reddederse istek sunucuda uygun bir modelle yeniden denenir.
            kwargs["betas"] = [FALLBACK_BETA]
            kwargs["fallbacks"] = "default"
        return kwargs

    # -------------------------------------------------------------- konuşma
    def ask(self, text: str) -> Reply:
        now = datetime.now()
        idle = time.monotonic() - self.last_activity
        if self.messages and (idle > SESSION_IDLE_SECONDS or len(self.messages) > MAX_HISTORY_MESSAGES):
            self.new_session()
        self.last_activity = time.monotonic()

        stamp = f"[{now:%d.%m.%Y} {DAYS_TR[now.weekday()]} {now:%H:%M}]"
        checkpoint = len(self.messages)
        self.messages.append({"role": "user", "content": f"{stamp} {text.strip()}"})
        try:
            reply = self._loop()
        except Exception as exc:
            del self.messages[checkpoint:]  # yarım kalan turu geri al
            return Reply(friendly_error(exc), ok=False)
        if not reply.ok:
            del self.messages[checkpoint:]
        self.last_activity = time.monotonic()
        return reply

    def _loop(self) -> Reply:
        tools_used: list[str] = []
        for _ in range(MAX_STEPS):
            response = self.client.beta.messages.create(**self._request_kwargs())
            self.usage.add(getattr(response, "usage", None))
            stop = response.stop_reason

            if stop == "refusal":
                return Reply("Üzgünüm, bu isteğe yardımcı olamıyorum.", ok=False, tools_used=tools_used)

            content, start = sanitize_content(response.content)
            if not content:
                # Boş asistan mesajı geçmişe eklenirse sonraki istek reddedilir.
                return Reply("Tamam.", tools_used=tools_used)
            self.messages.append({"role": "assistant", "content": content})
            current = content[start:]

            for block in current:
                if _block_type(block) == "server_tool_use":
                    query = (_get(block, "input") or {}).get("query") or (_get(block, "input") or {}).get("url") or ""
                    label = "🔎 İnternette arıyor" if _get(block, "name") == "web_search" else "🌐 Sayfa okuyor"
                    self.on_status(f"{label}: {query}" if query else label)

            if stop == "pause_turn":
                continue  # sunucu taraflı arama sürüyor; aynı geçmişle devam et

            tool_uses = [b for b in current if _block_type(b) == "tool_use"]
            if stop == "tool_use" and tool_uses:
                results = []
                for block in tool_uses:
                    name = _get(block, "name")
                    tool = self.registry.get(name)
                    self.on_status(tool.status if tool and tool.status else f"⚙️ {name}")
                    tools_used.append(name)
                    result = self.registry.run(name, _get(block, "input"))
                    entry = {"type": "tool_result", "tool_use_id": _get(block, "id"), "content": result.content}
                    if result.is_error:
                        entry["is_error"] = True
                    results.append(entry)
                self.messages.append({"role": "user", "content": results})
                continue

            text = extract_text(current)
            if stop == "max_tokens":
                text = (text + " ...") if text else "Cevabım çok uzun oldu ve yarıda kesildi."
            return Reply(text or "Tamam.", tools_used=tools_used)

        return Reply("Bu iş beklediğimden fazla adım gerektirdi, burada duruyorum. Daha basit parçalara bölebilir misiniz?",
                     tools_used=tools_used)

    def usage_summary(self) -> str:
        u = self.usage
        cost = u.cost(self.config.model)
        cost_text = f", tahmini maliyet ≈ ${cost:.4f}" if cost is not None else ""
        return (f"Bu oturumda {u.requests} istek, {u.input_tokens + u.cache_read + u.cache_write} girdi ve "
                f"{u.output_tokens} çıktı token'ı, {u.web_searches} web araması{cost_text}.")
