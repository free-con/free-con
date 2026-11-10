"""Jarvis servisi: tek bir beyin/araç/hafıza havuzunu birden çok kanala (masaüstü,
Telegram, web) güvenle paylaştırır.

Her kanalın kendi konuşma bağlamı (Brain) olur; hafıza, hatırlatıcılar ve araçlar
(tek bilgisayarda çalıştığı için) ortaktır. Araçlar aynı anda iki kez çalışmasın
diye tüm istekler tek bir kilitle sıraya alınır.
"""

from __future__ import annotations

import threading
from typing import Callable

import anthropic

from .brain import Brain, Reply
from .config import Config
from .memory import MemoryStore
from .reminders import ReminderManager
from .tools import ToolRegistry, build_registry


class _Ctx:
    """build_registry'nin beklediği bağlam (config, memory, reminders)."""

    def __init__(self, config: Config, memory: MemoryStore, reminders: ReminderManager):
        self.config = config
        self.memory = memory
        self.reminders = reminders


class JarvisService:
    def __init__(self, config: Config, client: anthropic.Anthropic | None = None,
                 registry: ToolRegistry | None = None):
        config.data_dir.mkdir(parents=True, exist_ok=True)
        self.config = config
        self.memory = MemoryStore(config.data_dir)
        self.reminders = ReminderManager(config.data_dir, notify=self._fan_reminder)
        self._ctx = _Ctx(config, self.memory, self.reminders)
        self.registry = registry or build_registry(self._ctx)
        self._client = client or anthropic.Anthropic(api_key=config.api_key or None, max_retries=3)
        self._lock = threading.RLock()
        self._brains: dict[str, Brain] = {}
        self._reminder_listeners: list[Callable[[str], None]] = []

    # --- hatırlatıcı bildirimlerini tüm kanallara dağıt ---
    def _fan_reminder(self, text: str) -> None:
        for cb in list(self._reminder_listeners):
            try:
                cb(text)
            except Exception as exc:  # bir kanalın hatası diğerlerini engellemesin
                print(f"[servis] hatırlatıcı bildirimi hatası: {exc}")

    def add_reminder_listener(self, cb: Callable[[str], None]) -> None:
        self._reminder_listeners.append(cb)

    def remove_reminder_listener(self, cb: Callable[[str], None]) -> None:
        if cb in self._reminder_listeners:
            self._reminder_listeners.remove(cb)

    def start_reminders(self) -> None:
        self.reminders.start()

    def stop_reminders(self) -> None:
        self.reminders.stop()

    # --- kanal başına beyin ---
    def get_brain(self, channel: str, mode: str = "text",
                  on_status: Callable[[str], None] | None = None) -> Brain:
        with self._lock:
            brain = self._brains.get(channel)
            if brain is None:
                brain = Brain(self.config, self.registry, self.memory, mode=mode,
                              client=self._client, on_status=on_status or (lambda msg: None))
                self._brains[channel] = brain
            return brain

    def reset_channel(self, channel: str) -> None:
        with self._lock:
            brain = self._brains.get(channel)
            if brain is not None:
                brain.new_session()

    def ask(self, channel: str, text: str, mode: str = "text",
            on_status: Callable[[str], None] | None = None) -> Reply:
        """Bir kanaldan gelen mesabı işler. Araç çalıştırma çakışmasın diye kilitlidir."""
        brain = self.get_brain(channel, mode, on_status)
        with self._lock:
            return brain.ask(text)

    def usage_summary(self) -> str:
        with self._lock:
            if not self._brains:
                return "Henüz istek yok."
            # Tüm kanalların kullanımı aynı istemciden geçtiği için birini özetlemek yeterli değil;
            # her beynin kendi sayacını toplayalım.
            from .brain import Usage

            total = Usage()
            for brain in self._brains.values():
                u = brain.usage
                total.input_tokens += u.input_tokens
                total.output_tokens += u.output_tokens
                total.cache_read += u.cache_read
                total.cache_write += u.cache_write
                total.web_searches += u.web_searches
                total.requests += u.requests
            cost = total.cost(self.config.model)
            cost_text = f", tahmini maliyet ≈ ${cost:.4f}" if cost is not None else ""
            return (f"Bu oturumda {total.requests} istek, "
                    f"{total.input_tokens + total.cache_read + total.cache_write} girdi ve "
                    f"{total.output_tokens} çıktı token'ı, {total.web_searches} web araması{cost_text}.")
