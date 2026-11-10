"""Hafıza, notlar ve hatırlatıcı araçları."""

from __future__ import annotations

from datetime import datetime

from ..reminders import REPEAT_TR, parse_when
from . import ToolError


def register(registry, ctx) -> None:
    memory = ctx.memory
    reminders = ctx.reminders

    registry.add(
        "remember",
        "Kullanıcı hakkında kalıcı bir bilgiyi hafızaya kaydeder (adı, doğum günü, sevdiği şeyler, "
        "ailesi, işi, tercihleri vb.). Kullanıcı 'bunu hatırla', 'unutma' dediğinde veya ileride "
        "işe yarayacak kalıcı bir bilgi paylaştığında çağır. Şifre, kart numarası gibi gizli bilgileri ASLA kaydetme.",
        lambda fact: memory.remember(fact),
        {"fact": {"type": "string", "description": "Kaydedilecek bilgi, tek ve açık bir cümle. Örn: 'Kullanıcının adı Ahmet.'"}},
        ["fact"],
        status="🧠 Hafızaya kaydediyor",
    )
    registry.add(
        "forget",
        "Hafızadan bir bilgiyi siler. Kullanıcı 'bunu unut' dediğinde çağır.",
        lambda query: memory.forget(query),
        {"query": {"type": "string", "description": "Silinecek bilginin içinden bir kelime/ifade veya '#3' gibi numarası."}},
        ["query"],
        status="🧠 Hafızadan siliyor",
    )
    registry.add(
        "list_memories",
        "Hafızadaki tüm kalıcı bilgileri numaralarıyla listeler. Kullanıcı 'hakkımda ne biliyorsun' dediğinde çağır.",
        lambda: memory.list_facts(),
        status="🧠 Hafızaya bakıyor",
    )
    registry.add(
        "add_note",
        "Kullanıcının söylediği bir notu kaydeder (alışveriş listesi, fikir, yapılacak iş vb.). "
        "'Not al', 'not et', 'listeye ekle' gibi isteklerde çağır.",
        lambda text: memory.add_note(text),
        {"text": {"type": "string", "description": "Notun tam metni."}},
        ["text"],
        status="📝 Not alıyor",
    )
    registry.add(
        "list_notes",
        "Kayıtlı notları (en yenileri) gösterir.",
        lambda limit=10: memory.list_notes(limit),
        {"limit": {"type": "integer", "description": "Kaç not gösterilsin (varsayılan 10).", "minimum": 1, "maximum": 100}},
        status="📝 Notlara bakıyor",
    )
    registry.add(
        "delete_note",
        "Numarası verilen notu siler.",
        lambda note_id: memory.delete_note(note_id),
        {"note_id": {"type": "integer", "description": "Silinecek notun numarası."}},
        ["note_id"],
        status="📝 Not siliyor",
    )

    def set_reminder(message: str, at: str | None = None, in_minutes: float | None = None, repeat: str = "none") -> str:
        try:
            when = parse_when(at, in_minutes)
            item = reminders.add(message, when, repeat)
        except ValueError as exc:
            raise ToolError(str(exc)) from None
        delta = when - datetime.now()
        mins = max(0, round(delta.total_seconds() / 60))
        return (
            f"Hatırlatıcı #{item['id']} kuruldu: {when:%d.%m.%Y %H:%M}{REPEAT_TR[repeat]} "
            f"(yaklaşık {mins} dakika sonra) - {message}"
        )

    registry.add(
        "set_reminder",
        "Hatırlatıcı, alarm veya zamanlayıcı kurar. Zamanı gelince Jarvis sesli olarak hatırlatır. "
        "'X dakika sonra' için in_minutes, belirli bir saat için 'at' kullan. 'at' için kullanıcının "
        "mesajındaki güncel tarih/saati baz al ve YYYY-MM-DDTHH:MM biçiminde yerel saat yaz.",
        set_reminder,
        {
            "message": {"type": "string", "description": "Hatırlatılacak şey. Örn: 'Annemi ara'."},
            "at": {"type": "string", "description": "Yerel saat, YYYY-MM-DDTHH:MM biçiminde. Örn: 2026-11-10T18:30"},
            "in_minutes": {"type": "number", "description": "Kaç dakika sonra (örn. 10). 'at' yerine kullanılır.", "minimum": 0.1},
            "repeat": {"type": "string", "enum": ["none", "daily", "weekly"], "description": "Tekrar: none (tek sefer), daily (her gün), weekly (her hafta)."},
        },
        ["message"],
        status="⏰ Hatırlatıcı kuruyor",
    )
    registry.add(
        "list_reminders",
        "Bekleyen hatırlatıcıları listeler.",
        lambda: reminders.describe(),
        status="⏰ Hatırlatıcılara bakıyor",
    )

    def cancel_reminder(reminder_id: int) -> str:
        if reminders.cancel(reminder_id):
            return f"Hatırlatıcı #{reminder_id} iptal edildi."
        raise ToolError(f"#{reminder_id} numaralı hatırlatıcı bulunamadı.")

    registry.add(
        "cancel_reminder",
        "Numarası verilen hatırlatıcıyı iptal eder. Numarayı bilmiyorsan önce list_reminders çağır.",
        cancel_reminder,
        {"reminder_id": {"type": "integer", "description": "İptal edilecek hatırlatıcının numarası."}},
        ["reminder_id"],
        status="⏰ Hatırlatıcı iptal ediyor",
    )
