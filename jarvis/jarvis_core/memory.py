"""Kalıcı hafıza: Jarvis'in sizin hakkınızda hatırladıkları ve notlarınız."""

from __future__ import annotations

import threading
from datetime import datetime
from pathlib import Path

from .storage import load_json, save_json

MAX_FACTS = 200
MAX_FACT_LENGTH = 500
MAX_NOTE_LENGTH = 4000


def _fold(text: str) -> str:
    """Türkçe karakterleri de doğru küçülten karşılaştırma anahtarı."""
    return text.replace("I", "ı").replace("İ", "i").casefold().strip()


class MemoryStore:
    def __init__(self, data_dir: Path):
        self.facts_path = data_dir / "hafiza.json"
        self.notes_path = data_dir / "notlar.json"
        self._lock = threading.Lock()
        self.facts: list[dict] = load_json(self.facts_path, [])
        self.notes: list[dict] = load_json(self.notes_path, [])

    # --- Hafıza (kalıcı bilgiler) ---
    def remember(self, fact: str) -> str:
        fact = " ".join(fact.split())[:MAX_FACT_LENGTH]
        if not fact:
            return "Boş bilgi kaydedilmedi."
        with self._lock:
            if any(_fold(f["text"]) == _fold(fact) for f in self.facts):
                return "Bu bilgi zaten hafızamda."
            next_id = max((f["id"] for f in self.facts), default=0) + 1
            self.facts.append({"id": next_id, "text": fact, "created": datetime.now().isoformat(timespec="minutes")})
            if len(self.facts) > MAX_FACTS:
                self.facts = self.facts[-MAX_FACTS:]
            save_json(self.facts_path, self.facts)
        return f"Hafızaya kaydedildi (#{next_id}): {fact}"

    def forget(self, query: str) -> str:
        key = _fold(query)
        if not key:
            return "Neyi unutacağımı belirtmelisiniz."
        with self._lock:
            if key.lstrip("#").isdigit():
                target = int(key.lstrip("#"))
                removed = [f for f in self.facts if f["id"] == target]
            else:
                removed = [f for f in self.facts if key in _fold(f["text"])]
            if not removed:
                return f"Hafızada '{query}' ile eşleşen bir bilgi bulunamadı."
            ids = {f["id"] for f in removed}
            self.facts = [f for f in self.facts if f["id"] not in ids]
            save_json(self.facts_path, self.facts)
        return "Unutuldu: " + "; ".join(f["text"] for f in removed)

    def list_facts(self) -> str:
        with self._lock:
            if not self.facts:
                return "Hafızada kayıtlı bilgi yok."
            return "\n".join(f"#{f['id']}: {f['text']}" for f in self.facts)

    def facts_for_prompt(self) -> str:
        with self._lock:
            return "\n".join(f"- {f['text']}" for f in self.facts)

    # --- Notlar ---
    def add_note(self, text: str) -> str:
        text = text.strip()[:MAX_NOTE_LENGTH]
        if not text:
            return "Boş not eklenmedi."
        with self._lock:
            next_id = max((n["id"] for n in self.notes), default=0) + 1
            self.notes.append({"id": next_id, "text": text, "created": datetime.now().isoformat(timespec="minutes")})
            save_json(self.notes_path, self.notes)
        return f"Not #{next_id} kaydedildi."

    def list_notes(self, limit: int = 10) -> str:
        with self._lock:
            if not self.notes:
                return "Hiç not yok."
            items = self.notes[-max(1, limit):]
            return "\n".join(f"#{n['id']} ({n['created']}): {n['text']}" for n in items)

    def delete_note(self, note_id: int) -> str:
        with self._lock:
            before = len(self.notes)
            self.notes = [n for n in self.notes if n["id"] != note_id]
            if len(self.notes) == before:
                return f"#{note_id} numaralı not bulunamadı."
            save_json(self.notes_path, self.notes)
        return f"Not #{note_id} silindi."
