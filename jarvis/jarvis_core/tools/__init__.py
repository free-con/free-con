"""Araç kayıt sistemi: Jarvis'in bilgisayarda yapabildiği işler.

Her araç bir isim, Claude'un okuyacağı bir açıklama, bir JSON şeması ve
çalıştırılacak bir Python fonksiyonundan oluşur. Claude bir aracı
çağırdığında girdiler önce burada doğrulanır, sonra fonksiyon çalışır.
"""

from __future__ import annotations

import traceback
from dataclasses import dataclass, field
from typing import Any, Callable

_JSON_TYPES: dict[str, tuple[type, ...]] = {
    "string": (str,),
    "integer": (int,),
    "number": (int, float),
    "boolean": (bool,),
    "array": (list,),
    "object": (dict,),
}


class ToolError(Exception):
    """Kullanıcıya/Claude'a gösterilecek, beklenen bir hata."""


@dataclass
class ToolResult:
    content: str | list[dict]
    is_error: bool = False


@dataclass
class Tool:
    name: str
    description: str
    func: Callable[..., Any]
    properties: dict[str, dict] = field(default_factory=dict)
    required: list[str] = field(default_factory=list)
    status: str = ""  # konsolda gösterilecek kısa durum mesajı

    def spec(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": self.properties,
                "required": self.required,
                "additionalProperties": False,
            },
        }

    def validate(self, args: Any) -> dict:
        if not isinstance(args, dict):
            raise ToolError("Girdi bir JSON nesnesi olmalı.")
        unknown = set(args) - set(self.properties)
        if unknown:
            raise ToolError(f"Bilinmeyen parametre(ler): {', '.join(sorted(unknown))}")
        missing = [p for p in self.required if p not in args]
        if missing:
            raise ToolError(f"Eksik parametre(ler): {', '.join(missing)}")
        clean: dict[str, Any] = {}
        for key, value in args.items():
            schema = self.properties[key]
            expected = schema.get("type")
            if expected:
                types = _JSON_TYPES.get(expected, (object,))
                is_bool = isinstance(value, bool)
                if (is_bool and expected != "boolean") or not isinstance(value, types):
                    raise ToolError(f"'{key}' parametresi {expected} türünde olmalı.")
            if "enum" in schema and value not in schema["enum"]:
                raise ToolError(f"'{key}' şunlardan biri olmalı: {', '.join(map(str, schema['enum']))}")
            if expected in ("integer", "number"):
                lo, hi = schema.get("minimum"), schema.get("maximum")
                if (lo is not None and value < lo) or (hi is not None and value > hi):
                    raise ToolError(f"'{key}' {lo} ile {hi} arasında olmalı.")
            clean[key] = value
        return clean


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def add(
        self,
        name: str,
        description: str,
        func: Callable[..., Any],
        properties: dict[str, dict] | None = None,
        required: list[str] | None = None,
        status: str = "",
    ) -> None:
        if name in self._tools:
            raise ValueError(f"Araç zaten kayıtlı: {name}")
        self._tools[name] = Tool(name, description, func, properties or {}, required or [], status)

    def names(self) -> list[str]:
        return list(self._tools)

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def specs(self) -> list[dict]:
        # Kayıt sırası sabit kalır; bu, istem önbelleğinin (prompt cache) bozulmamasını sağlar.
        return [t.spec() for t in self._tools.values()]

    def run(self, name: str, args: Any) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(f"'{name}' adında bir araç yok.", is_error=True)
        try:
            clean = tool.validate(args)
            output = tool.func(**clean)
        except ToolError as exc:
            return ToolResult(f"Hata: {exc}", is_error=True)
        except Exception as exc:  # beklenmeyen hata: Claude'a bildir, uygulama çökmesin
            traceback.print_exc()
            return ToolResult(f"Beklenmeyen hata ({type(exc).__name__}): {exc}", is_error=True)
        if isinstance(output, ToolResult):
            return output
        if output is None:
            output = "Tamam."
        if isinstance(output, list):
            return ToolResult(output)
        return ToolResult(str(output))


def build_registry(ctx: Any) -> ToolRegistry:
    """Tüm araç modüllerini kaydeder. ctx: JarvisContext."""
    from . import computer, info, media, personal, smarthome

    registry = ToolRegistry()
    personal.register(registry, ctx)
    computer.register(registry, ctx)
    media.register(registry, ctx)
    info.register(registry, ctx)
    if ctx.config.smarthome_enabled:
        smarthome.register(registry, ctx)
    return registry
