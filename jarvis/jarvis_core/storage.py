"""Küçük JSON dosyaları için güvenli okuma/yazma."""

from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any

_lock = threading.Lock()


def load_json(path: Path, default: Any) -> Any:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except (json.JSONDecodeError, OSError):
        # Bozuk dosyayı kaybetmemek için yedekle, varsayılanla devam et.
        try:
            path.replace(path.with_suffix(path.suffix + ".bozuk"))
        except OSError:
            pass
        return default


def save_json(path: Path, data: Any) -> None:
    """Önce geçici dosyaya yazar, sonra yerine koyar (yarım dosya kalmaz)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
