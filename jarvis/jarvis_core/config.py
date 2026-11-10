"""Ayarlar: .env dosyasından ve ortam değişkenlerinden okunur."""

from __future__ import annotations

import os
import platform
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent

# Sunucu taraflı "fallback" (bir istek güvenlik filtresine takılırsa başka
# modelle yeniden deneme) bu modellerde "default" biçimiyle destekleniyor.
FALLBACK_MODELS = {
    "claude-opus-5-5",
    "claude-opus-5",
    "claude-sonnet-5-5",
    "claude-fable-5-2",
    "claude-fable-5-1",
}

# Gelişmiş web arama/okuma araçlarını (_20260209) desteklemeyen modeller
# temel sürümleri kullanır.
BASIC_WEB_TOOL_PREFIXES = ("claude-haiku",)


def _parse_env_file(path: Path) -> dict[str, str]:
    """Basit bir .env okuyucu: ANAHTAR=değer satırları, # ile yorum."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key.startswith("export "):
            key = key[len("export "):].strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key] = value
    return values


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "evet", "yes", "on", "acik", "açık"}


@dataclass
class Config:
    api_key: str = ""
    model: str = "claude-opus-5-5"
    effort: str = "low"
    assistant_name: str = "Jarvis"
    user_name: str = ""
    city: str = "İstanbul"
    country: str = "TR"
    timezone: str = "Europe/Istanbul"
    voice: str = "tr-TR-AhmetNeural"
    voice_rate: str = "+8%"
    wake_words: list[str] = field(
        default_factory=lambda: ["jarvis", "carvis", "cervis", "ceyvis", "çarvis", "jarviz", "jervis"]
    )
    stt_engine: str = "google"
    whisper_model: str = "small"
    language: str = "tr-TR"
    mic_device: str = ""
    follow_up_seconds: float = 8.0
    use_fallbacks: bool = True
    data_dir: Path = field(default_factory=lambda: Path.home() / "Jarvis")
    ha_url: str = ""
    ha_token: str = ""

    @property
    def os_name(self) -> str:
        return platform.system()  # "Windows", "Darwin" (Mac), "Linux"

    @property
    def fallbacks_enabled(self) -> bool:
        return self.use_fallbacks and self.model in FALLBACK_MODELS

    @property
    def uses_basic_web_tools(self) -> bool:
        return self.model.startswith(BASIC_WEB_TOOL_PREFIXES)

    @property
    def smarthome_enabled(self) -> bool:
        return bool(self.ha_url and self.ha_token)


def load_config(env_file: Path | None = None) -> Config:
    """Önce .env dosyasını, sonra gerçek ortam değişkenlerini okur (ortam kazanır)."""
    env_path = env_file or (PROJECT_DIR / ".env")
    values = _parse_env_file(env_path)
    values.update({k: v for k, v in os.environ.items() if k.startswith(("JARVIS_", "HA_", "ANTHROPIC_"))})

    def get(key: str, default: str = "") -> str:
        value = values.get(key)
        return value.strip() if value and value.strip() else default

    cfg = Config()
    cfg.api_key = get("ANTHROPIC_API_KEY")
    cfg.model = get("JARVIS_MODEL", cfg.model)
    cfg.effort = get("JARVIS_EFFORT", cfg.effort).lower()
    cfg.assistant_name = get("JARVIS_NAME", cfg.assistant_name)
    cfg.user_name = get("JARVIS_USER_NAME", cfg.user_name)
    cfg.city = get("JARVIS_CITY", cfg.city)
    cfg.country = get("JARVIS_COUNTRY", cfg.country).upper()
    cfg.timezone = get("JARVIS_TIMEZONE", cfg.timezone)
    cfg.voice = get("JARVIS_VOICE", cfg.voice)
    cfg.voice_rate = get("JARVIS_VOICE_RATE", cfg.voice_rate)
    wake = get("JARVIS_WAKE_WORDS")
    if wake:
        cfg.wake_words = [w.strip().lower() for w in wake.split(",") if w.strip()]
    cfg.stt_engine = get("JARVIS_STT", cfg.stt_engine).lower()
    cfg.whisper_model = get("JARVIS_WHISPER_MODEL", cfg.whisper_model)
    cfg.language = get("JARVIS_LANGUAGE", cfg.language)
    cfg.mic_device = get("JARVIS_MIC")
    try:
        cfg.follow_up_seconds = float(get("JARVIS_FOLLOW_UP_SECONDS", str(cfg.follow_up_seconds)))
    except ValueError:
        pass
    cfg.use_fallbacks = _as_bool(values.get("JARVIS_FALLBACKS"), True)
    data_dir = get("JARVIS_DATA_DIR")
    if data_dir:
        cfg.data_dir = Path(os.path.expandvars(os.path.expanduser(data_dir)))
    cfg.ha_url = get("HA_URL").rstrip("/")
    cfg.ha_token = get("HA_TOKEN")
    return cfg
