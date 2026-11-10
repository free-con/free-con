"""Müzik ve ses kontrolü: YouTube/Spotify'da çalma, medya tuşları, ses seviyesi."""

from __future__ import annotations

import platform
import re
import shutil
import subprocess
import time
import webbrowser
from urllib.parse import quote, quote_plus

import requests

from . import ToolError
from .computer import CREATE_NO_WINDOW, open_with_default_app

SYSTEM = platform.system()

# Windows sanal tuş kodları (medya ve ses tuşları)
VK = {
    "play_pause": 0xB3, "next": 0xB0, "previous": 0xB1, "stop": 0xB2,
    "volume_mute": 0xAD, "volume_down": 0xAE, "volume_up": 0xAF,
}

_VIDEO_ID = re.compile(r'"videoId":"([A-Za-z0-9_-]{11})"')


def _press_windows_key(vk: int, times: int = 1) -> None:
    import ctypes

    user32 = ctypes.windll.user32  # type: ignore[attr-defined]
    for _ in range(times):
        user32.keybd_event(vk, 0, 1, 0)       # KEYEVENTF_EXTENDEDKEY
        user32.keybd_event(vk, 0, 1 | 2, 0)   # + KEYEVENTF_KEYUP
        if times > 1:
            time.sleep(0.01)


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True, timeout=10, creationflags=CREATE_NO_WINDOW)


def _osascript(script: str) -> str:
    return _run(["osascript", "-e", script]).stdout.strip()


def find_youtube_video(query: str) -> str | None:
    """YouTube arama sonuçlarındaki ilk videonun adresini bulur."""
    try:
        resp = requests.get(
            "https://www.youtube.com/results",
            params={"search_query": query},
            headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "tr-TR,tr;q=0.9"},
            cookies={"CONSENT": "YES+1"},
            timeout=8,
        )
        resp.raise_for_status()
    except requests.RequestException:
        return None
    match = _VIDEO_ID.search(resp.text)
    return f"https://www.youtube.com/watch?v={match.group(1)}" if match else None


def play_music(query: str, platform_name: str = "youtube") -> str:
    query = query.strip()
    if not query:
        raise ToolError("Ne çalınacağını belirtmelisiniz.")
    if platform_name == "spotify":
        try:
            open_with_default_app(f"spotify:search:{quote(query)}")
            return f"Spotify'da '{query}' araması açıldı. Çalmak için ilk sonuca tıklanabilir ya da media_control ile oynatılabilir."
        except OSError:
            webbrowser.open(f"https://open.spotify.com/search/{quote(query)}")
            return f"Spotify web'de '{query}' araması açıldı."
    url = find_youtube_video(query)
    if url:
        webbrowser.open(url)
        return f"YouTube'da '{query}' çalınıyor: {url}"
    webbrowser.open("https://www.youtube.com/results?search_query=" + quote_plus(query))
    return f"YouTube'da '{query}' arama sonuçları açıldı."


def media_control(action: str) -> str:
    labels = {"play_pause": "Oynat/duraklat", "next": "Sonraki parça", "previous": "Önceki parça", "stop": "Durdur"}
    if SYSTEM == "Windows":
        _press_windows_key(VK[action])
    elif SYSTEM == "Darwin":
        commands = {"play_pause": "playpause", "next": "next track", "previous": "previous track", "stop": "pause"}
        for app in ("Spotify", "Music"):
            running = _osascript(f'application "{app}" is running') == "true"
            if running:
                _osascript(f'tell application "{app}" to {commands[action]}')
                break
        else:
            raise ToolError("Çalışan Spotify veya Müzik uygulaması yok.")
    else:
        if not shutil.which("playerctl"):
            raise ToolError("Linux'ta medya kontrolü için 'playerctl' kurulmalı (sudo apt install playerctl).")
        cmd = {"play_pause": "play-pause", "next": "next", "previous": "previous", "stop": "stop"}[action]
        _run(["playerctl", cmd])
    return f"{labels[action]} yapıldı."


def set_volume(level: int | None = None, change: str | None = None) -> str:
    if level is None and change is None:
        raise ToolError("Ya 'level' (0-100) ya da 'change' (up/down/mute) verilmeli.")
    if SYSTEM == "Windows":
        if level is not None:
            # Her tuş basışı sesi %2 değiştirir: önce sıfırla, sonra istenen seviyeye çık.
            _press_windows_key(VK["volume_down"], 50)
            _press_windows_key(VK["volume_up"], round(level / 2))
            return f"Ses seviyesi yaklaşık %{level} yapıldı."
        if change == "mute":
            _press_windows_key(VK["volume_mute"])
            return "Ses kapatıldı/açıldı."
        _press_windows_key(VK["volume_up" if change == "up" else "volume_down"], 5)
        return "Ses %10 " + ("açıldı." if change == "up" else "kısıldı.")
    if SYSTEM == "Darwin":
        if level is not None:
            _osascript(f"set volume output volume {level}")
        elif change == "mute":
            muted = _osascript("output muted of (get volume settings)") == "true"
            _osascript(f"set volume output muted {'false' if muted else 'true'}")
        else:
            sign = "+" if change == "up" else "-"
            _osascript(f"set volume output volume ((output volume of (get volume settings)) {sign} 10)")
        return "Ses ayarlandı."
    if shutil.which("pactl"):
        sink = "@DEFAULT_SINK@"
        if level is not None:
            _run(["pactl", "set-sink-volume", sink, f"{level}%"])
        elif change == "mute":
            _run(["pactl", "set-sink-mute", sink, "toggle"])
        else:
            _run(["pactl", "set-sink-volume", sink, "+10%" if change == "up" else "-10%"])
    elif shutil.which("amixer"):
        if level is not None:
            _run(["amixer", "-q", "set", "Master", f"{level}%"])
        elif change == "mute":
            _run(["amixer", "-q", "set", "Master", "toggle"])
        else:
            _run(["amixer", "-q", "set", "Master", "10%+" if change == "up" else "10%-"])
    else:
        raise ToolError("Ses kontrolü için pactl veya amixer bulunamadı.")
    return "Ses ayarlandı."


def register(registry, ctx) -> None:
    registry.add(
        "play_music",
        "Şarkı, sanatçı, çalma listesi veya video çalar. Varsayılan olarak YouTube'da ilk sonucu açar; kullanıcı "
        "Spotify derse platform_name='spotify' kullan. 'Tarkan çal', 'rahatlatıcı müzik aç' gibi isteklerde çağır.",
        lambda query, platform_name="youtube": play_music(query, platform_name),
        {
            "query": {"type": "string", "description": "Ne çalınacak. Örn: 'Tarkan Şımarık', 'lofi çalışma müziği'."},
            "platform_name": {"type": "string", "enum": ["youtube", "spotify"], "description": "Varsayılan youtube."},
        },
        ["query"],
        status="🎵 Müzik açıyor",
    )
    registry.add(
        "media_control",
        "Çalan müziği/videoyu kontrol eder: oynat/duraklat, sonraki, önceki, durdur.",
        media_control,
        {"action": {"type": "string", "enum": ["play_pause", "next", "previous", "stop"]}},
        ["action"],
        status="🎵 Medya kontrolü",
    )
    registry.add(
        "set_volume",
        "Bilgisayarın ses seviyesini ayarlar. Belirli seviye için level (0-100), 'sesi aç/kıs/kapat' için change kullan.",
        set_volume,
        {
            "level": {"type": "integer", "description": "Hedef ses seviyesi yüzdesi (0-100).", "minimum": 0, "maximum": 100},
            "change": {"type": "string", "enum": ["up", "down", "mute"], "description": "up=%10 aç, down=%10 kıs, mute=sessize al/aç."},
        },
        status="🔊 Ses ayarlıyor",
    )
