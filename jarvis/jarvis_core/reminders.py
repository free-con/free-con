"""Hatırlatıcılar: zamanı gelince Jarvis sesli olarak haber verir."""

from __future__ import annotations

import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

from .storage import load_json, save_json

REPEATS = {"none": None, "daily": timedelta(days=1), "weekly": timedelta(weeks=1)}
REPEAT_TR = {"none": "", "daily": " (her gün)", "weekly": " (her hafta)"}


def parse_when(at: str | None = None, in_minutes: float | None = None, now: datetime | None = None) -> datetime:
    """'2026-11-10T15:30' gibi yerel bir saat veya 'X dakika sonra' bilgisini çözer."""
    now = now or datetime.now()
    if in_minutes is not None:
        if in_minutes <= 0:
            raise ValueError("Dakika sayısı sıfırdan büyük olmalı.")
        return now + timedelta(minutes=in_minutes)
    if not at:
        raise ValueError("Ya 'at' (saat) ya da 'in_minutes' (dakika) verilmeli.")
    text = at.strip().replace(" ", "T", 1)
    try:
        when = datetime.fromisoformat(text)
    except ValueError:
        # Sadece saat verildiyse ("15:30") bugüne, geçtiyse yarına kur.
        try:
            t = datetime.strptime(at.strip(), "%H:%M").time()
        except ValueError:
            raise ValueError(f"Saat anlaşılamadı: '{at}'. Örnek biçim: 2026-11-10T15:30") from None
        when = datetime.combine(now.date(), t)
        if when <= now:
            when += timedelta(days=1)
    if when.tzinfo is not None:
        when = when.astimezone().replace(tzinfo=None)
    return when


class ReminderManager:
    def __init__(self, data_dir: Path, notify: Callable[[str], None] | None = None):
        self.path = data_dir / "hatirlaticilar.json"
        self.notify = notify or (lambda text: print(text))
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.items: list[dict] = load_json(self.path, [])

    def _save(self) -> None:
        save_json(self.path, self.items)

    def add(self, message: str, when: datetime, repeat: str = "none") -> dict:
        if repeat not in REPEATS:
            raise ValueError("repeat şunlardan biri olmalı: none, daily, weekly")
        if when <= datetime.now() and repeat == "none":
            raise ValueError("Hatırlatma zamanı geçmişte olamaz.")
        with self._lock:
            next_id = max((r["id"] for r in self.items), default=0) + 1
            item = {"id": next_id, "message": message.strip(), "due": when.isoformat(timespec="seconds"), "repeat": repeat}
            self.items.append(item)
            self._save()
        return item

    def cancel(self, reminder_id: int) -> bool:
        with self._lock:
            before = len(self.items)
            self.items = [r for r in self.items if r["id"] != reminder_id]
            changed = len(self.items) != before
            if changed:
                self._save()
        return changed

    def describe(self) -> str:
        with self._lock:
            if not self.items:
                return "Bekleyen hatırlatıcı yok."
            items = sorted(self.items, key=lambda r: r["due"])
            return "\n".join(
                f"#{r['id']}: {datetime.fromisoformat(r['due']):%d.%m.%Y %H:%M} - {r['message']}{REPEAT_TR.get(r['repeat'], '')}"
                for r in items
            )

    def pop_due(self, now: datetime | None = None) -> list[dict]:
        """Zamanı gelmiş hatırlatıcıları döndürür; tekrarlıları ileri kaydırır."""
        now = now or datetime.now()
        due: list[dict] = []
        with self._lock:
            keep: list[dict] = []
            for r in self.items:
                when = datetime.fromisoformat(r["due"])
                if when > now:
                    keep.append(r)
                    continue
                due.append(dict(r))
                step = REPEATS.get(r.get("repeat", "none"))
                if step:
                    while when <= now:
                        when += step
                    keep.append({**r, "due": when.isoformat(timespec="seconds")})
            if due:
                self.items = keep
                self._save()
        return due

    def _run(self) -> None:
        while not self._stop.wait(1.0):
            for r in self.pop_due():
                late = datetime.now() - datetime.fromisoformat(r["due"])
                prefix = "Kaçırılan hatırlatma" if late > timedelta(minutes=2) else "Hatırlatma"
                try:
                    self.notify(f"{prefix}: {r['message']}")
                except Exception as exc:  # bildirim hatası döngüyü durdurmasın
                    print(f"[hatırlatıcı] bildirim hatası: {exc}")

    def start(self) -> None:
        if self._thread is None:
            self._thread = threading.Thread(target=self._run, name="hatirlatici", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()
