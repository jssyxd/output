"""
ZephyrusWorld-lite: Python API wrapper for weather data.

Glue layer inspired by Zephyrus (ICLR 2026) - exposes weather data, geolocation,
forecasting, and climatology tools through Python APIs that an LLM agent can call.

Data source: Open-Meteo (https://open-meteo.com) - free, no API key, supports
ensemble NWP models from ECMWF, GFS, ICON, JMA, GEM, MeteoFrance.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from typing import Any

import urllib.request
import urllib.parse


# ----- Constants -----
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ENSEMBLE_URL = "https://ensemble-api.open-meteo.com/v1/ensemble"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"

# Models available on Open-Meteo. East Asia coverage varies.
AVAILABLE_MODELS = [
    "ecmwf_ifs025",       # ECMWF IFS 0.25° (best global, HRES) - 6 day lead
    "ecmwf_ifs025_long",  # ECMWF IFS 0.25° long range (ENS extended) - 15 day lead
    "gfs_seamless",       # NOAA GFS 0.25° - 16 day lead
    "gfs_hrrr",           # NOAA HRRR (US only) - not for Shanghai
    "icon_seamless",      # DWD ICON - 7.5 day lead
    "gem_seamless",       # Canadian GEM - 10 day lead
    "jma_msm",            # JMA Mesoscale (East Asia high res, 5km) - 1.5 day lead
    "jma_seamless",       # JMA global
    "meteofrance_seamless",  # Météo-France ARPEGE/AROME
    "metno_seamless",     # MET Norway
]

# Variable names per Open-Meteo daily API
DAILY_VARS = [
    "temperature_2m_max",
    "temperature_2m_min",
    "apparent_temperature_max",
    "apparent_temperature_min",
    "precipitation_sum",
    "rain_sum",
    "showers_sum",
    "snowfall_sum",
    "precipitation_hours",
    "precipitation_probability_max",
    "wind_speed_10m_max",
    "wind_gusts_10m_max",
    "wind_direction_10m_dominant",
    "uv_index_max",
    "sunrise",
    "sunset",
]


# ----- Result containers -----
@dataclass
class GeocodeResult:
    name: str
    latitude: float
    longitude: float
    elevation: float
    country: str
    admin1: str
    timezone: str


@dataclass
class ForecastDay:
    date: str
    tmax_c: float | None = None
    tmin_c: float | None = None
    rain_mm: float | None = None
    wind_kmh: float | None = None
    wind_dir_deg: float | None = None
    uv_max: float | None = None


@dataclass
class ModelForecast:
    model: str
    tmax_c: float | None = None
    tmin_c: float | None = None
    rain_mm: float | None = None
    wind_kmh: float | None = None
    wind_dir_deg: float | None = None
    members_tmax: list[float] | None = None  # for ensemble


@dataclass
class ForecastBundle:
    location: dict
    target_date: str
    models: list[ModelForecast]
    issue_time: str  # when forecast was issued
    raw: dict


# ----- HTTP helper -----
def _http_get_json(url: str, params: dict, retries: int = 3) -> dict:
    """GET JSON with retry. Open-Meteo is rate-limited 10k req/day per IP."""
    qs = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    full = f"{url}?{qs}"
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(full, headers={"User-Agent": "ZephyrusWorld-lite/0.1"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            last_err = e
            time.sleep(1.0 * (attempt + 1))
    raise RuntimeError(f"Open-Meteo request failed after {retries} retries: {last_err}")


# ----- Geocoding -----
def geocode(name: str, count: int = 5) -> list[GeocodeResult]:
    """Natural-language place name -> coordinates. Returns multiple candidates."""
    data = _http_get_json(GEOCODE_URL, {"name": name, "count": count, "language": "en", "format": "json"})
    out = []
    for r in data.get("results", []):
        out.append(GeocodeResult(
            name=r.get("name", ""),
            latitude=r.get("latitude"),
            longitude=r.get("longitude"),
            elevation=r.get("elevation", 0.0),
            country=r.get("country", ""),
            admin1=r.get("admin1", ""),
            timezone=r.get("timezone", "UTC"),
        ))
    return out


# ----- Forecasting -----
def get_forecast_multi_model(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    models: list[str] = None,
    daily_vars: list[str] = None,
    timezone: str = "Asia/Shanghai",
) -> dict:
    """Get deterministic forecast from multiple NWP models in one call."""
    if models is None:
        models = ["ecmwf_ifs025", "gfs_seamless", "icon_seamless",
                  "gem_seamless", "jma_msm", "meteofrance_seamless"]
    if daily_vars is None:
        daily_vars = ["temperature_2m_max", "temperature_2m_min",
                      "precipitation_sum", "wind_speed_10m_max",
                      "wind_direction_10m_dominant"]
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": ",".join(daily_vars),
        "models": ",".join(models),
        "timezone": timezone,
        "start_date": start_date,
        "end_date": end_date,
    }
    return _http_get_json(FORECAST_URL, params)


def get_ecmwf_ensemble(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    daily_vars: list[str] = None,
    timezone: str = "Asia/Shanghai",
) -> dict:
    """Get full ECMWF 50-member ensemble forecast (T+0 to T+15 days)."""
    if daily_vars is None:
        daily_vars = ["temperature_2m_max", "temperature_2m_min",
                      "precipitation_sum"]
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": ",".join(daily_vars),
        "models": "ecmwf_ifs025",
        "timezone": timezone,
        "start_date": start_date,
        "end_date": end_date,
    }
    return _http_get_json(ENSEMBLE_URL, params)


def parse_forecast_bundle(raw: dict, target_date: str) -> ForecastBundle:
    """Parse Open-Meteo response into structured ForecastBundle.

    Handles two response formats:
    - single-model query: keys are 'temperature_2m_max' (no model suffix)
    - multi-model query: keys are 'temperature_2m_max_<model>' (with suffix)
    """
    loc = {"lat": raw["latitude"], "lon": raw["longitude"],
           "elev_m": raw.get("elevation"), "tz": raw["timezone"]}
    daily = raw.get("daily", {})
    time_arr = daily.get("time", [])
    if target_date not in time_arr:
        raise ValueError(f"target_date {target_date} not in response: {time_arr}")
    idx = time_arr.index(target_date)
    issue_time = raw.get("current", {}).get("time", "unknown")
    # Discover model suffixes from keys. Suffixes may be empty (single-model).
    base_vars = ["temperature_2m_max", "temperature_2m_min",
                 "precipitation_sum", "wind_speed_10m_max",
                 "wind_direction_10m_dominant", "apparent_temperature_max"]
    seen: set[str] = set()
    for key in daily:
        for v in base_vars:
            if key == v:
                seen.add("")  # single-model (no suffix)
            elif key.startswith(v + "_"):
                seen.add(key[len(v) + 1:])
    models: list[ModelForecast] = []
    for model in sorted(seen):
        suffix = f"_{model}" if model else ""
        def get(var):
            arr = daily.get(f"{var}{suffix}")
            return arr[idx] if arr else None
        models.append(ModelForecast(
            model=model or "default",
            tmax_c=get("temperature_2m_max"),
            tmin_c=get("temperature_2m_min"),
            rain_mm=get("precipitation_sum"),
            wind_kmh=get("wind_speed_10m_max"),
            wind_dir_deg=get("wind_direction_10m_dominant"),
        ))
    return ForecastBundle(
        location=loc,
        target_date=target_date,
        models=models,
        issue_time=issue_time,
        raw=raw,
    )


def parse_ensemble_members(raw: dict, target_date: str) -> dict:
    """Parse ECMWF 50-member ensemble into per-member arrays."""
    daily = raw.get("daily", {})
    time_arr = daily.get("time", [])
    if target_date not in time_arr:
        return {}
    idx = time_arr.index(target_date)
    out = {"target_date": target_date, "members": {}}
    for var in ["temperature_2m_max", "temperature_2m_min", "precipitation_sum"]:
        members = []
        for i in range(1, 51):
            # Try both key formats
            for key_fmt in [f"{var}_member{i:02d}_ecmwf_ifs025_ensemble",
                            f"{var}_member{i:02d}"]:
                key = key_fmt
                arr = daily.get(key)
                if arr:
                    members.append(arr[idx])
                    break
        if members:
            out["members"][var] = members
    return out


# ----- Observation -----
def get_observation(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    timezone: str = "Asia/Shanghai",
) -> dict:
    """Get actual historical weather observations (ERA5 reanalysis from Open-Meteo)."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max",
        "timezone": timezone,
    }
    return _http_get_json(ARCHIVE_URL, params)


# ----- Quick CLI test -----
if __name__ == "__main__":
    # Geocode test
    print("Geocoding 'Shanghai Pudong Airport':")
    for g in geocode("Pudong"):
        print(f"  {g.name}, {g.country} @ ({g.latitude}, {g.longitude}) elev={g.elevation}m")
    print()
    # Forecast test
    print("Multi-model forecast 2026-06-14:")
    raw = get_forecast_multi_model(31.1433, 121.8052, "2026-06-14", "2026-06-14")
    bundle = parse_forecast_bundle(raw, "2026-06-14")
    for m in bundle.models:
        print(f"  {m.model:25s}: T_max={m.tmax_c}°C, T_min={m.tmin_c}°C, rain={m.rain_mm}mm")
    print()
    # Ensemble test
    print("ECMWF 50-member ensemble for 2026-06-14:")
    ens = get_ecmwf_ensemble(31.1433, 121.8052, "2026-06-14", "2026-06-14")
    parsed = parse_ensemble_members(ens, "2026-06-14")
    for var, members in parsed.get("members", {}).items():
        if members:
            m_min, m_max = min(members), max(members)
            m_mean = sum(members) / len(members)
            print(f"  {var:25s}: n={len(members)}, mean={m_mean:.2f}, range=[{m_min}, {m_max}]")
