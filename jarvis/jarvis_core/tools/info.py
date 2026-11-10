"""Bilgi araçları: hava durumu (Open-Meteo, ücretsiz, anahtar gerektirmez)."""

from __future__ import annotations

from datetime import date

import requests

from . import ToolError

WEATHER_CODES = {
    0: "açık", 1: "çoğunlukla açık", 2: "parçalı bulutlu", 3: "kapalı",
    45: "sisli", 48: "kırağılı sis",
    51: "hafif çisenti", 53: "çisenti", 55: "yoğun çisenti", 56: "dondurucu çisenti", 57: "yoğun dondurucu çisenti",
    61: "hafif yağmurlu", 63: "yağmurlu", 65: "şiddetli yağmurlu", 66: "dondurucu yağmur", 67: "şiddetli dondurucu yağmur",
    71: "hafif kar yağışlı", 73: "kar yağışlı", 75: "yoğun kar yağışlı", 77: "kar taneli",
    80: "hafif sağanak", 81: "sağanak yağışlı", 82: "şiddetli sağanak",
    85: "hafif kar sağanağı", 86: "yoğun kar sağanağı",
    95: "gök gürültülü fırtına", 96: "dolu ile fırtına", 99: "şiddetli dolu ile fırtına",
}
DAYS_TR = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]


def get_weather(city: str, days: int = 1) -> str:
    city = city.strip()
    if not city:
        raise ToolError("Şehir adı boş.")
    try:
        geo = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "language": "tr", "format": "json"},
            timeout=8,
        )
        geo.raise_for_status()
        results = geo.json().get("results") or []
        if not results:
            raise ToolError(f"'{city}' adında bir yer bulunamadı.")
        place = results[0]
        forecast = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "current": "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m",
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                "timezone": "auto",
                "forecast_days": max(1, min(days, 7)),
            },
            timeout=8,
        )
        forecast.raise_for_status()
        data = forecast.json()
    except requests.RequestException as exc:
        raise ToolError(f"Hava durumu servisine ulaşılamadı: {exc}") from None

    name = ", ".join(x for x in (place.get("name"), place.get("admin1"), place.get("country")) if x)
    cur = data.get("current", {})
    lines = [
        f"{name} - şu an: {cur.get('temperature_2m')}°C (hissedilen {cur.get('apparent_temperature')}°C), "
        f"{WEATHER_CODES.get(cur.get('weather_code'), 'bilinmiyor')}, nem %{cur.get('relative_humidity_2m')}, "
        f"rüzgâr {cur.get('wind_speed_10m')} km/sa."
    ]
    daily = data.get("daily", {})
    for i, day in enumerate(daily.get("time", [])):
        d = date.fromisoformat(day)
        label = "Bugün" if i == 0 else ("Yarın" if i == 1 else DAYS_TR[d.weekday()])
        lines.append(
            f"{label} ({d:%d.%m}): {WEATHER_CODES.get(daily['weather_code'][i], 'bilinmiyor')}, "
            f"en düşük {daily['temperature_2m_min'][i]}°C, en yüksek {daily['temperature_2m_max'][i]}°C, "
            f"yağış ihtimali %{daily['precipitation_probability_max'][i]}"
        )
    return "\n".join(lines)


def register(registry, ctx) -> None:
    default_city = ctx.config.city
    registry.add(
        "get_weather",
        f"Bir şehrin güncel hava durumunu ve tahminini verir. Şehir söylenmezse kullanıcının şehri: {default_city}. "
        "Hava, sıcaklık, yağmur, şemsiye, ne giysem gibi sorularda çağır.",
        lambda city=default_city, days=1: get_weather(city, days),
        {
            "city": {"type": "string", "description": f"Şehir adı (varsayılan {default_city})."},
            "days": {"type": "integer", "description": "Kaç günlük tahmin (1-7, varsayılan 1).", "minimum": 1, "maximum": 7},
        },
        status="🌤️ Hava durumuna bakıyor",
    )
