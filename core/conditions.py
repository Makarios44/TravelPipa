"""
Weather, sun and tide conditions for Pipa.

* Weather: MET Norway Locationforecast 2.0 (free, commercial use allowed under
  CC BY 4.0 / NLOD; requires an identifying User-Agent and caching).
* Sunrise / sunset: calculated locally (NOAA solar algorithm) - no API call.
* Tides (TIDES_PROVIDER):
  - "tabuamare" (default): Tábua de Maré API (tabuamare.api.br), free. It serves the
    Brazilian Navy (DHN) official predictions for the nearest port (Natal for Pipa).
    Works without a key (16 req/min shared per IP); a free key gives 32,000 req/month.
  - "worldtides": WorldTides API v3 (paid), needs WORLDTIDES_API_KEY.
  Without data, the site links to the official Brazilian Navy tables.

Every external call is cached. A second "stale" copy is kept for longer, so the
site keeps showing the last good data if a provider is temporarily down.
Nothing here ever raises: on failure the functions return None.
"""
import datetime as dt
import json
import logging
import math
import urllib.parse
import urllib.request
from collections import OrderedDict

from django.conf import settings
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)

LOCAL_TZ = dt.timezone(dt.timedelta(hours=-3), "BRT")  # Rio Grande do Norte has no daylight saving

METNO_URL = "https://api.met.no/weatherapi/locationforecast/2.0/compact"
WORLDTIDES_URL = "https://www.worldtides.info/api/v3"
TABUAMARE_URL = "https://tabuamare.api.br/api/v2"
NAVY_TIDE_TABLES_URL = "https://www.marinha.mil.br/chm/tabuas-de-mare"

WEATHER_TTL = 30 * 60          # MET updates roughly every hour
TIDES_TTL = 12 * 60 * 60       # predictions do not change; refreshed twice a day
STALE_TTL = 3 * 24 * 60 * 60   # fallback copy if a provider is down
FAILURE_BACKOFF = 5 * 60       # do not retry a failing provider on every page view
HTTP_TIMEOUT = 6

# MET Norway symbol codes (without _day/_night suffix) -> (Bootstrap icon, label)
WEATHER_SYMBOLS = {
    "clearsky": ("sun", _("Clear sky")),
    "fair": ("sun", _("Fair")),
    "partlycloudy": ("cloud-sun", _("Partly cloudy")),
    "cloudy": ("cloud", _("Cloudy")),
    "fog": ("cloud-fog2", _("Fog")),
    "lightrainshowers": ("cloud-drizzle", _("Light showers")),
    "rainshowers": ("cloud-rain", _("Showers")),
    "heavyrainshowers": ("cloud-rain-heavy", _("Heavy showers")),
    "lightrain": ("cloud-drizzle", _("Light rain")),
    "rain": ("cloud-rain", _("Rain")),
    "heavyrain": ("cloud-rain-heavy", _("Heavy rain")),
    "lightrainshowersandthunder": ("cloud-lightning-rain", _("Thunderstorms")),
    "rainshowersandthunder": ("cloud-lightning-rain", _("Thunderstorms")),
    "heavyrainshowersandthunder": ("cloud-lightning-rain", _("Thunderstorms")),
    "lightrainandthunder": ("cloud-lightning-rain", _("Thunderstorms")),
    "rainandthunder": ("cloud-lightning-rain", _("Thunderstorms")),
    "heavyrainandthunder": ("cloud-lightning-rain", _("Thunderstorms")),
}
DEFAULT_SYMBOL = ("cloud-sun", _("Variable"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def now():
    """Current time in Pipa (a function so tests can replace it)."""
    return dt.datetime.now(LOCAL_TZ)


def _get_json(url, params=None, headers=None):
    if params:
        url = f"{url}?{urllib.parse.urlencode(params, doseq=True)}"
    request = urllib.request.Request(url, headers={"Accept": "application/json", **(headers or {})})
    with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:  # noqa: S310 (fixed https URLs)
        return json.loads(response.read().decode("utf-8"))


def _cached(key, ttl, loader):
    """Return fresh cached data, or load it; on failure fall back to the stale copy."""
    data = cache.get(key)
    if data is not None:
        return data
    stale_key, failed_key = f"{key}:stale", f"{key}:failed"
    if cache.get(failed_key):
        return cache.get(stale_key)
    try:
        data = loader()
    except Exception:  # network error, bad JSON, provider down...
        logger.warning("Conditions provider failed for %s", key, exc_info=True)
        cache.set(failed_key, True, FAILURE_BACKOFF)
        return cache.get(stale_key)
    if data is None:
        cache.set(failed_key, True, FAILURE_BACKOFF)
        return cache.get(stale_key)
    cache.set(key, data, ttl)
    cache.set(stale_key, data, STALE_TTL)
    return data


def coordinates():
    return round(settings.CONDITIONS_LAT, 4), round(settings.CONDITIONS_LON, 4)


def symbol_info(symbol_code):
    base = (symbol_code or "").split("_")[0]
    icon, label = WEATHER_SYMBOLS.get(base, DEFAULT_SYMBOL)
    if base in ("clearsky", "fair") and (symbol_code or "").endswith("_night"):
        icon = "moon-stars"
    return {"icon": icon, "label": str(label)}


# ---------------------------------------------------------------------------
# Weather (MET Norway)
# ---------------------------------------------------------------------------
def parse_metno(payload, today=None):
    """Turn a Locationforecast 'compact' response into current conditions + daily forecast."""
    series = payload["properties"]["timeseries"]
    if not series:
        return None
    today = today or now().date()

    first = series[0]
    details = first["data"]["instant"]["details"]
    nxt = first["data"].get("next_1_hours") or first["data"].get("next_6_hours") or {}
    current = {
        "temperature": round(details.get("air_temperature", 0)),
        "wind_kmh": round(details.get("wind_speed", 0) * 3.6),
        "humidity": round(details.get("relative_humidity", 0)) if "relative_humidity" in details else None,
        "symbol": (nxt.get("summary") or {}).get("symbol_code", ""),
        "precipitation_mm": (nxt.get("details") or {}).get("precipitation_amount", 0.0),
    }

    days = OrderedDict()
    covered_until = None  # avoids counting the same rain twice when 1h and 6h blocks overlap
    for entry in series:
        moment = dt.datetime.fromisoformat(entry["time"].replace("Z", "+00:00")).astimezone(LOCAL_TZ)
        day = moment.date()
        if day < today:
            continue
        info = days.setdefault(day.isoformat(), {"temps": [], "rain": 0.0, "symbol": "", "symbol_hour": 99})
        temp = entry["data"]["instant"]["details"].get("air_temperature")
        if temp is not None:
            info["temps"].append(temp)
        one_hour = entry["data"].get("next_1_hours")
        six_hours = entry["data"].get("next_6_hours")
        rain_block, block_hours = (one_hour, 1) if one_hour else (six_hours, 6)
        if rain_block and (covered_until is None or moment >= covered_until):
            info["rain"] += (rain_block.get("details") or {}).get("precipitation_amount", 0.0)
            covered_until = moment + dt.timedelta(hours=block_hours)
        # The symbol closest to midday represents the day.
        block = one_hour or six_hours
        if block and abs(moment.hour - 12) < abs(info["symbol_hour"] - 12):
            info["symbol"] = (block.get("summary") or {}).get("symbol_code", "")
            info["symbol_hour"] = moment.hour

    daily = []
    for iso, info in days.items():
        if not info["temps"]:
            continue
        daily.append({
            "date": iso,
            "min": round(min(info["temps"])),
            "max": round(max(info["temps"])),
            "rain_mm": round(info["rain"], 1),
            "symbol": info["symbol"],
        })
    return {"current": current, "daily": daily[:6], "updated": payload["properties"].get("meta", {}).get("updated_at")}


def _load_weather():
    lat, lon = coordinates()
    payload = _get_json(METNO_URL, {"lat": lat, "lon": lon}, headers={"User-Agent": settings.WEATHER_USER_AGENT})
    return parse_metno(payload)


def get_weather():
    if not settings.WEATHER_ENABLED:
        return None
    data = _cached("conditions:weather", WEATHER_TTL, _load_weather)
    if not data:
        return None
    return decorate_weather(data)


def decorate_weather(data):
    """Add icon/label/date objects (kept out of the cache so labels follow the active language)."""
    current = dict(data["current"], **symbol_info(data["current"]["symbol"]))
    daily = []
    for day in data["daily"]:
        item = dict(day, **symbol_info(day["symbol"]))
        item["date_obj"] = dt.date.fromisoformat(day["date"])
        daily.append(item)
    return {"current": current, "daily": daily}


# ---------------------------------------------------------------------------
# Sunrise / sunset (NOAA algorithm, accurate to about one minute)
# ---------------------------------------------------------------------------
def sun_times(day=None, lat=None, lon=None):
    day = day or now().date()
    lat = settings.CONDITIONS_LAT if lat is None else lat
    lon = settings.CONDITIONS_LON if lon is None else lon

    def event(rising):
        n = day.timetuple().tm_yday
        approx = n + ((6 if rising else 18) - lon / 15) / 24
        mean_anomaly = 0.9856 * approx - 3.289
        true_long = (mean_anomaly + 1.916 * math.sin(math.radians(mean_anomaly))
                     + 0.020 * math.sin(math.radians(2 * mean_anomaly)) + 282.634) % 360
        right_asc = math.degrees(math.atan(0.91764 * math.tan(math.radians(true_long)))) % 360
        right_asc = (right_asc + (math.floor(true_long / 90) - math.floor(right_asc / 90)) * 90) / 15
        sin_dec = 0.39782 * math.sin(math.radians(true_long))
        cos_dec = math.cos(math.asin(sin_dec))
        cos_hour = ((math.cos(math.radians(90.833)) - sin_dec * math.sin(math.radians(lat)))
                    / (cos_dec * math.cos(math.radians(lat))))
        if not -1 <= cos_hour <= 1:
            return None
        hour_angle = (360 - math.degrees(math.acos(cos_hour))) if rising else math.degrees(math.acos(cos_hour))
        local_mean = hour_angle / 15 + right_asc - 0.06571 * approx - 6.622
        utc_hours = (local_mean - lon / 15) % 24
        moment = dt.datetime.combine(day, dt.time(), tzinfo=dt.timezone.utc) + dt.timedelta(hours=utc_hours)
        return moment.astimezone(LOCAL_TZ)

    return {"sunrise": event(True), "sunset": event(False)}


# ---------------------------------------------------------------------------
# Tides — Tábua de Maré API (Brazilian Navy predictions), free
# ---------------------------------------------------------------------------
def _days_param(days):
    """[11,12,13] -> '[11-13]'; non-contiguous days are listed: '[1,3-5]'."""
    days = sorted(set(days))
    parts, start = [], days[0]
    for previous, current in zip(days, days[1:] + [None]):
        if current != previous + 1:
            parts.append(str(start) if start == previous else f"{start}-{previous}")
            start = current
    return "[" + ",".join(parts) + "]"


def parse_tabuamare(payload, year_hint=None):
    """
    Response: {"data": [{"year", "harbor_name", "data_collection_institution", "mean_level",
               "months": [{"month", "days": [{"day", "hours": [{"hour": "06:01:00", "level": 1.87}]}]}]}],
               "total": 1}
    The Navy tables list only the extremes (high and low tides) of each day.
    """
    if payload.get("error") or not payload.get("data"):
        logger.warning("Tábua de Maré API error: %s", payload.get("error"))
        return None
    table = payload["data"][0]
    year = int(table.get("year") or year_hint or now().year)
    points = []
    for month in table.get("months", []):
        for day in month.get("days", []):
            for reading in day.get("hours", []):
                hh, mm, *_ = (str(reading["hour"]).split(":") + ["0"])[:3]
                moment = dt.datetime(year, int(month["month"]), int(day["day"]), int(hh), int(mm), tzinfo=LOCAL_TZ)
                points.append((moment, float(reading["level"])))
    points.sort()
    events = []
    mean_level = table.get("mean_level")
    for i, (moment, level) in enumerate(points):
        neighbours = [points[j][1] for j in (i - 1, i + 1) if 0 <= j < len(points)]
        if neighbours:
            kind = "high" if all(level > n for n in neighbours) else "low"
        else:
            kind = "high" if mean_level is not None and level > float(mean_level) else "low"
        events.append({"timestamp": int(moment.timestamp()), "type": kind, "height": round(level, 1)})
    return {"extremes": events, "harbor": table.get("harbor_name", ""),
            "institution": table.get("data_collection_institution", ""), "provider": "tabuamare"}


def _load_tabuamare():
    lat, lon = coordinates()
    today = now().date()
    by_month = OrderedDict()
    for offset in range(8):
        day = today + dt.timedelta(days=offset)
        if day.year != today.year:
            break  # the API serves the current year's tables
        by_month.setdefault(day.month, []).append(day.day)
    headers = {"User-Agent": settings.WEATHER_USER_AGENT}
    if settings.TABUAMARE_API_KEY:
        headers["Authorization"] = f"Bearer {settings.TABUAMARE_API_KEY}"
    merged = None
    for month, days in by_month.items():
        path = f"/geo-tabua-mare/[{lat},{lon}]/{settings.TIDES_STATE}/{month}/{_days_param(days)}"
        result = parse_tabuamare(_get_json(TABUAMARE_URL + path, headers=headers), year_hint=today.year)
        if result is None:
            return None
        if merged is None:
            merged = result
        else:
            merged["extremes"].extend(result["extremes"])
    return merged


# ---------------------------------------------------------------------------
# Tides — WorldTides (paid alternative)
# ---------------------------------------------------------------------------
def parse_worldtides(payload):
    if payload.get("status") != 200:
        logger.warning("WorldTides error: %s", payload.get("error"))
        return None
    events = []
    for item in payload.get("extremes", []):
        events.append({
            "timestamp": item["dt"],
            "type": "low" if str(item.get("type", "")).lower().startswith("l") else "high",
            "height": round(float(item.get("height", 0)), 1),
        })
    return {"extremes": events, "copyright": payload.get("copyright", ""), "provider": "worldtides"}


def _load_worldtides():
    lat, lon = coordinates()
    params = {"extremes": "", "lat": lat, "lon": lon, "date": now().date().isoformat(),
              "days": 7, "datum": "CD", "key": settings.WORLDTIDES_API_KEY}
    return parse_worldtides(_get_json(WORLDTIDES_URL, params))


TIDE_PROVIDERS = {"tabuamare": _load_tabuamare, "worldtides": _load_worldtides}


def tides_enabled():
    provider = settings.TIDES_PROVIDER
    if provider == "worldtides":
        return bool(settings.WORLDTIDES_API_KEY)
    return provider in TIDE_PROVIDERS


def tide_source_text(data):
    if data.get("provider") == "tabuamare":
        return str(_("Tide predictions for %(harbor)s (%(institution)s), via Tábua de Maré API. "
                     "Times in Pipa may differ by a few minutes.") % {
            "harbor": data.get("harbor") or "Natal", "institution": data.get("institution") or "DHN"})
    return data.get("copyright", "")


def get_tides(days=7):
    """Tide extremes grouped by local day: [{'date': date, 'events': [...]}, ...]."""
    if not tides_enabled():
        return None
    provider = settings.TIDES_PROVIDER
    data = _cached(f"conditions:tides:{provider}", TIDES_TTL, TIDE_PROVIDERS[provider])
    if not data:
        return None
    current_time = now()
    grouped = OrderedDict()
    for event in data["extremes"]:
        moment = dt.datetime.fromtimestamp(event["timestamp"], tz=dt.timezone.utc).astimezone(LOCAL_TZ)
        if moment.date() < current_time.date():
            continue
        grouped.setdefault(moment.date(), []).append(dict(event, time=moment, past=moment < current_time))
    table = [{"date": day, "events": events} for day, events in list(grouped.items())[:days]]
    upcoming_lows = [e for day in table for e in day["events"] if e["type"] == "low" and not e["past"]]
    return {
        "days": table,
        "next_low": upcoming_lows[0] if upcoming_lows else None,
        "upcoming_lows": upcoming_lows[:4],
        "copyright": tide_source_text(data),
    }


def get_conditions():
    """Everything the templates need, in one call."""
    return {
        "weather": get_weather(),
        "sun": sun_times(),
        "tides": get_tides(),
        "tides_enabled": tides_enabled(),
        "navy_url": NAVY_TIDE_TABLES_URL,
    }
