"""Ses: mikrofondan dinleme, konuşmayı yazıya çevirme, uyanma kelimesi ve sesli cevap."""

from __future__ import annotations

import asyncio
import collections
import difflib
import math
import os
import re
import tempfile
import threading
import time
import unicodedata
from array import array
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

SAMPLE_RATE = 16000
BLOCK = 480  # 30 ms
FILLERS = {"hey", "hi", "ey", "merhaba", "selam", "heey", "hay", "ok", "okey", "tamam"}


# ------------------------------------------------------------ metin yardımcıları
def fold(text: str) -> str:
    return text.replace("I", "ı").replace("İ", "i").casefold()


def _tokens(text: str) -> list[str]:
    return re.findall(r"[\w']+", text, flags=re.UNICODE)


def find_wake_word(text: str, wake_words: list[str]) -> tuple[bool, str]:
    """Metinde uyanma kelimesi (Jarvis) var mı? Varsa (True, kalan komut) döner.

    "Jarvis müzik aç" -> (True, "müzik aç"); "ışıkları kapat jarvis" -> (True, "ışıkları kapat");
    "hey jarvis" -> (True, "").
    """
    words = _tokens(text)
    wakes = [fold(w) for w in wake_words]
    main = wakes[0] if wakes else ""
    for i, word in enumerate(words):
        base = fold(word).split("'")[0]
        if not base:
            continue
        # Listedeki yazımlar birebir eşleşmeli; benzerlik toleransı sadece asıl isim için
        # (yoksa "servis" gibi gerçek kelimeler "cervis"e benzeyip yanlışlıkla uyandırır).
        hit = base in wakes or (
            len(base) >= 5 and difflib.SequenceMatcher(None, base, main).ratio() >= 0.8
        )
        if hit:
            rest = words[:i] + words[i + 1:]
            if all(fold(w) in FILLERS for w in rest):
                return True, ""
            # Baştaki "hey" gibi dolgu kelimelerini at.
            while rest and fold(rest[0]) in FILLERS:
                rest.pop(0)
            command = " ".join(rest)
            return True, command
    return False, ""


def clean_for_speech(text: str) -> str:
    """Markdown, bağlantı ve emojileri temizler; birimleri okunur hale getirir."""
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)      # [yazı](link) -> yazı
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[*_#`>|]+", "", text)
    text = re.sub(r"^\s*[-•]\s+", "", text, flags=re.M)
    text = re.sub(r"%\s?(\d+(?:[.,]\d+)?)", r"yüzde \1", text)
    text = re.sub(r"(\d)\s?°C", r"\1 derece", text)
    text = text.replace("°", " derece")
    text = "".join(
        ch for ch in text
        if unicodedata.category(ch) != "So" and ch not in "\ufe0e\ufe0f\u200d" and ord(ch) < 0x1F000
    )
    return re.sub(r"\s+", " ", text).strip()


def is_exit_command(text: str) -> bool:
    t = fold(text)
    return any(p in t for p in ("kendini kapat", "programı kapat", "programdan çık", "jarvis kapan", "kapan artık"))


# ------------------------------------------------------------------- konuşma
class Speaker:
    """Microsoft Edge'in doğal Türkçe sesleri (edge-tts) ile konuşur; olmazsa pyttsx3 dener."""

    def __init__(self, config):
        self.voice = config.voice
        self.rate = config.voice_rate
        self.tmp_dir = Path(tempfile.gettempdir()) / "jarvis_ses"
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.engine = None
        self._pyttsx3 = None
        self._pyttsx3_tried = False
        try:
            import edge_tts  # noqa: F401
            import pygame

            pygame.mixer.init()
            self._pygame = pygame
            self.engine = "edge"
        except Exception:
            if self._get_pyttsx3() is not None:
                self.engine = "pyttsx3"

    def _get_pyttsx3(self):
        """Yedek (internetsiz) sesi ilk ihtiyaçta bir kez hazırlar; kurulu değilse None."""
        if not self._pyttsx3_tried:
            self._pyttsx3_tried = True
            try:
                import pyttsx3

                engine = pyttsx3.init()
                for v in engine.getProperty("voices"):
                    if "tr" in (getattr(v, "id", "") + str(getattr(v, "languages", ""))).lower():
                        engine.setProperty("voice", v.id)
                        break
                self._pyttsx3 = engine
            except Exception:
                self._pyttsx3 = None
        return self._pyttsx3

    @property
    def available(self) -> bool:
        return self.engine is not None

    def say(self, text: str) -> None:
        clean = clean_for_speech(text)
        if not clean or self.engine is None:
            return
        with self._lock:
            if self.engine == "edge":
                try:
                    self._say_edge(clean)
                    return
                except Exception as exc:
                    # Geçici bir sorun olabilir (ör. internet): doğal ses sonraki cevapta yeniden denenir.
                    print(f"[ses] Doğal ses şu an kullanılamadı ({exc}).")
            fallback = self._get_pyttsx3()
            if fallback is not None:
                try:
                    fallback.say(clean)
                    fallback.runAndWait()
                except Exception as exc:
                    print(f"[ses] Yedek ses de çalışmadı ({exc}).")

    def _say_edge(self, text: str) -> None:
        import edge_tts

        path = self.tmp_dir / f"cevap_{threading.get_ident()}_{time.time_ns()}.mp3"

        async def synth() -> None:
            await edge_tts.Communicate(text, self.voice, rate=self.rate).save(str(path))

        asyncio.run(synth())
        music = self._pygame.mixer.music
        try:
            music.load(str(path))
            music.play()
            while music.get_busy():
                time.sleep(0.05)
        finally:
            try:
                music.unload()
            except Exception:
                pass
            try:
                path.unlink()
            except OSError:
                pass


# ------------------------------------------------------------------- dinleme
class SpeechServiceError(Exception):
    pass


def _rms(samples: array) -> float:
    if not samples:
        return 0.0
    return math.sqrt(sum(s * s for s in samples) / len(samples))


class Listener:
    """Mikrofondan konuşmayı yakalar (sessizlik algılamalı) ve yazıya çevirir."""

    def __init__(self, config):
        import sounddevice as sd

        self.sd = sd
        self.config = config
        self.device = self._pick_device(config.mic_device)
        self.threshold = 500.0
        self.noise = 150.0
        self._whisper = None
        if config.stt_engine == "google":
            import speech_recognition as sr

            self.sr = sr
            self.recognizer = sr.Recognizer()

    def _pick_device(self, wanted: str):
        if not wanted:
            return None
        if wanted.isdigit():
            return int(wanted)
        for i, dev in enumerate(self.sd.query_devices()):
            if dev.get("max_input_channels", 0) > 0 and fold(wanted) in fold(dev.get("name", "")):
                return i
        return None

    def calibrate(self, seconds: float = 1.0) -> None:
        """Ortam gürültüsünü ölçer ve konuşma eşiğini ayarlar."""
        frames = int(SAMPLE_RATE * seconds)
        data = self.sd.rec(frames, samplerate=SAMPLE_RATE, channels=1, dtype="int16", device=self.device)
        self.sd.wait()
        samples = array("h", data.tobytes())
        self.noise = max(_rms(samples), 50.0)
        self.threshold = max(self.noise * 3.0, 350.0)

    def record_phrase(self, max_wait: float | None = None, max_phrase: float = 15.0, silence: float = 0.9) -> bytes | None:
        """Biri konuşmaya başlayınca kaydeder, susunca durur. max_wait saniyede ses gelmezse None."""
        pre_roll: collections.deque[bytes] = collections.deque(maxlen=int(0.4 * SAMPLE_RATE / BLOCK))
        frames: list[bytes] = []
        started = False
        quiet_blocks = 0
        needed_quiet = int(silence * SAMPLE_RATE / BLOCK)
        max_blocks = int(max_phrase * SAMPLE_RATE / BLOCK)
        begin = time.monotonic()
        with self.sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=BLOCK, channels=1, dtype="int16", device=self.device) as stream:
            while True:
                chunk, _overflow = stream.read(BLOCK)
                chunk = bytes(chunk)
                level = _rms(array("h", chunk))
                if not started:
                    if level > self.threshold:
                        started = True
                        frames.extend(pre_roll)
                        frames.append(chunk)
                    else:
                        pre_roll.append(chunk)
                        # Gürültü seviyesini yavaşça takip et (klima, fan vb. değişirse).
                        self.noise = 0.98 * self.noise + 0.02 * level
                        self.threshold = max(self.noise * 3.0, 350.0)
                        if max_wait is not None and time.monotonic() - begin > max_wait:
                            return None
                    continue
                frames.append(chunk)
                quiet_blocks = quiet_blocks + 1 if level < self.threshold * 0.6 else 0
                if quiet_blocks >= needed_quiet or len(frames) >= max_blocks:
                    break
        speech_blocks = len(frames) - quiet_blocks
        if speech_blocks * BLOCK / SAMPLE_RATE < 0.3:
            return b""  # çok kısa: muhtemelen bir tıkırtı
        return b"".join(frames)

    def transcribe(self, raw: bytes) -> str:
        if not raw:
            return ""
        if self.config.stt_engine == "whisper":
            return self._transcribe_whisper(raw)
        audio = self.sr.AudioData(raw, SAMPLE_RATE, 2)
        try:
            return self.recognizer.recognize_google(audio, language=self.config.language)
        except self.sr.UnknownValueError:
            return ""
        except self.sr.RequestError as exc:
            raise SpeechServiceError(f"Konuşma tanıma servisine ulaşılamadı: {exc}") from exc

    def _transcribe_whisper(self, raw: bytes) -> str:
        import numpy as np

        if self._whisper is None:
            from faster_whisper import WhisperModel

            print(f"[ses] Whisper '{self.config.whisper_model}' modeli yükleniyor (ilk seferde indirilir)...")
            self._whisper = WhisperModel(self.config.whisper_model, device="cpu", compute_type="int8")
        audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        lang = self.config.language.split("-")[0]
        segments, _info = self._whisper.transcribe(audio, language=lang, beam_size=1)
        return " ".join(s.text.strip() for s in segments).strip()

    def listen(self, max_wait: float | None = None) -> str | None:
        raw = self.record_phrase(max_wait=max_wait)
        if raw is None:
            return None
        return self.transcribe(raw)


def list_microphones() -> str:
    import sounddevice as sd

    lines = []
    default_in = sd.default.device[0] if isinstance(sd.default.device, (list, tuple)) else sd.default.device
    for i, dev in enumerate(sd.query_devices()):
        if dev.get("max_input_channels", 0) > 0:
            mark = "  (varsayılan)" if i == default_in else ""
            lines.append(f"  {i}: {dev['name']}{mark}")
    return "\n".join(lines) or "  Hiç mikrofon bulunamadı."
