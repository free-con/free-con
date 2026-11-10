"""Akıllı ev: Home Assistant ile ışık, priz, klima vb. kontrolü.

Sadece .env dosyasında HA_URL ve HA_TOKEN ayarlıysa etkinleşir.
Güvenlik için kapı kilidi ve alarm gibi cihazlar kontrol edilmez.
"""

from __future__ import annotations

import requests

from . import ToolError

CONTROLLABLE_DOMAINS = {"light", "switch", "fan", "cover", "climate", "media_player", "scene", "script", "input_boolean", "vacuum", "humidifier"}
LISTED_DOMAINS = CONTROLLABLE_DOMAINS | {"sensor", "binary_sensor", "weather"}
ACTIONS = {"turn_on", "turn_off", "toggle"}


class HomeAssistant:
    def __init__(self, url: str, token: str):
        self.url = url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def _request(self, method: str, path: str, **kwargs):
        try:
            resp = requests.request(method, self.url + path, headers=self.headers, timeout=10, **kwargs)
        except requests.RequestException as exc:
            raise ToolError(f"Home Assistant'a ulaşılamadı: {exc}") from None
        if resp.status_code == 401:
            raise ToolError("Home Assistant anahtarı (HA_TOKEN) geçersiz.")
        if resp.status_code >= 400:
            raise ToolError(f"Home Assistant hatası ({resp.status_code}): {resp.text[:200]}")
        return resp.json() if resp.content else None

    def list_devices(self, domain: str | None = None) -> str:
        states = self._request("GET", "/api/states") or []
        lines = []
        for s in states:
            entity = s.get("entity_id", "")
            dom = entity.split(".", 1)[0]
            if dom not in LISTED_DOMAINS or (domain and dom != domain):
                continue
            attrs = s.get("attributes", {})
            unit = attrs.get("unit_of_measurement", "")
            lines.append(f"{entity} | {attrs.get('friendly_name', entity)} | durum: {s.get('state')}{(' ' + unit) if unit else ''}")
        if not lines:
            return "Uygun cihaz bulunamadı."
        return "\n".join(lines[:80])

    def control(self, entity_id: str, action: str, brightness_pct: int | None = None, temperature: float | None = None) -> str:
        if "." not in entity_id:
            raise ToolError("entity_id 'light.salon' gibi olmalı. Önce ha_list_devices çağır.")
        domain = entity_id.split(".", 1)[0]
        if domain not in CONTROLLABLE_DOMAINS:
            raise ToolError(f"Güvenlik nedeniyle '{domain}' türündeki cihazlar kontrol edilemez.")
        payload: dict = {"entity_id": entity_id}
        service = action
        if domain in ("scene", "script") and action != "turn_off":
            service = "turn_on"
        if brightness_pct is not None and domain == "light":
            payload["brightness_pct"] = brightness_pct
            service = "turn_on"
        if temperature is not None and domain == "climate":
            payload["temperature"] = temperature
            service = "set_temperature"
        self._request("POST", f"/api/services/{domain}/{service}", json=payload)
        return f"{entity_id}: {service} komutu gönderildi."


def register(registry, ctx) -> None:
    ha = HomeAssistant(ctx.config.ha_url, ctx.config.ha_token)
    registry.add(
        "ha_list_devices",
        "Home Assistant'taki akıllı ev cihazlarını (ışık, priz, klima, sensör vb.) ve durumlarını listeler. "
        "Bir cihazı kontrol etmeden önce doğru entity_id'yi bulmak için çağır.",
        lambda domain=None: ha.list_devices(domain),
        {"domain": {"type": "string", "description": "Sadece bu türü listele: light, switch, climate, sensor vb. (isteğe bağlı)"}},
        status="🏠 Cihazlara bakıyor",
    )
    registry.add(
        "ha_control",
        "Bir akıllı ev cihazını açar, kapatır veya ayarlar (ışık parlaklığı, klima sıcaklığı).",
        lambda entity_id, action="toggle", brightness_pct=None, temperature=None: ha.control(entity_id, action, brightness_pct, temperature),
        {
            "entity_id": {"type": "string", "description": "Cihaz kimliği, örn. 'light.salon'."},
            "action": {"type": "string", "enum": sorted(ACTIONS), "description": "turn_on, turn_off veya toggle."},
            "brightness_pct": {"type": "integer", "description": "Işık parlaklığı yüzdesi (0-100).", "minimum": 0, "maximum": 100},
            "temperature": {"type": "number", "description": "Klima için hedef sıcaklık (°C)."},
        },
        ["entity_id"],
        status="🏠 Cihaz kontrol ediyor",
    )
