# === Header: Zephyrus + TianJi forecast for Shanghai Pudong 2026-06-14 ===

# Bundled source: see open_meteo, consensus, reflective, main below.


# === Inlined open_meteo.py ===

"""
ZephyrusWorld-lite: Python API wrapper for weather data.

Glue layer inspired by Zephyrus (ICLR 2026) - exposes weather data, geolocation,
forecasting, and climatology tools through Python APIs that an LLM agent can call.

Data source: Open-Meteo (https://open-meteo.com) - free, no API key, supports
ensemble NWP models from ECMWF, GFS, ICON, JMA, GEM, MeteoFrance.
"""
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



# === Inlined consensus.py ===

"""
TianJi-inspired consensus engine.

Architecture (simplified, glue-programming version):
  - Meta-planner: interprets the forecast task, picks which models to query
  - Worker agents: each queries one NWP model via Open-Meteo (deterministic)
  - Analyst: synthesizes results, computes consensus, uncertainty bounds

TianJi's full multi-agent debate (Researcher/Host/Chief Scientist) is not
implemented because (a) it requires private code (not open-sourced), and
(b) for numerical weather forecasting, deterministic workers + weighted
synthesis is more reliable than LLM debate.
"""
import json
import statistics
import time
from dataclasses import dataclass, field
from typing import Any

# ----- Worker -----
@dataclass
class WorkerResult:
    name: str
    role: str
    tmax_c: float | None
    tmin_c: float | None
    rain_mm: float | None
    wind_kmh: float | None
    spread: float | None  # ensemble std if applicable
    raw_count: int
    elapsed_ms: float


def deterministic_worker(model: str, lat: float, lon: float, date: str,
                         timeout_s: float = 20.0) -> WorkerResult:
    """One NWP model = one worker. Returns its T_max forecast.

    Uses thread-based timeout because Open-Meteo's http.urlopen can hang on
    some models (e.g. ecmwf_ifs025 cold start takes >90s).
    """
    import concurrent.futures
    t0 = time.time()
    def _run():
        return get_forecast_multi_model(lat, lon, date, date, models=[model])
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(_run)
            try:
                raw = future.result(timeout=timeout_s)
            except concurrent.futures.TimeoutError:
                elapsed = (time.time() - t0) * 1000
                return WorkerResult(model, "deterministic", None, None, None, None, None, 0, elapsed)
        bundle = parse_forecast_bundle(raw, date)
        m = bundle.models[0] if bundle.models else None
        elapsed = (time.time() - t0) * 1000
        if m is None:
            return WorkerResult(model, "deterministic", None, None, None, None, None, 0, elapsed)
        return WorkerResult(
            name=model, role="deterministic",
            tmax_c=m.tmax_c, tmin_c=m.tmin_c,
            rain_mm=m.rain_mm, wind_kmh=m.wind_kmh,
            spread=None, raw_count=1, elapsed_ms=elapsed,
        )
    except Exception as e:
        elapsed = (time.time() - t0) * 1000
        return WorkerResult(model, "deterministic", None, None, None, None, None, 0, elapsed)


def ensemble_worker(model: str, lat: float, lon: float, date: str,
                    timeout_s: float = 30.0) -> WorkerResult:
    """ECMWF ensemble = 50-member worker. Returns mean and std."""
    import concurrent.futures
    t0 = time.time()
    def _run():
        return get_ecmwf_ensemble(lat, lon, date, date)
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(_run)
            try:
                raw = future.result(timeout=timeout_s)
            except concurrent.futures.TimeoutError:
                elapsed = (time.time() - t0) * 1000
                return WorkerResult(model, "ensemble", None, None, None, None, None, 0, elapsed)
        parsed = parse_ensemble_members(raw, date)
        members = parsed.get("members", {}).get("temperature_2m_max", [])
        elapsed = (time.time() - t0) * 1000
        if not members:
            return WorkerResult(model, "ensemble", None, None, None, None, None, 0, elapsed)
        m_mean = statistics.mean(members)
        m_std = statistics.stdev(members)
        rain_members = parsed.get("members", {}).get("precipitation_sum", [])
        tmin_members = parsed.get("members", {}).get("temperature_2m_min", [])
        return WorkerResult(
            name=model, role="ensemble",
            tmax_c=m_mean, tmin_c=(statistics.mean(tmin_members) if tmin_members else None),
            rain_mm=(statistics.mean(rain_members) if rain_members else None),
            wind_kmh=None, spread=m_std,
            raw_count=len(members), elapsed_ms=elapsed,
        )
    except Exception as e:
        elapsed = (time.time() - t0) * 1000
        return WorkerResult(model, "ensemble", None, None, None, None, None, 0, elapsed)


# ----- Meta-planner -----
@dataclass
class ConsensusResult:
    target_date: str
    location: dict
    workers: list[WorkerResult]
    consensus: dict
    cma_official: dict | None
    method: str


# Model weights (based on East Asia summer T_max skill, empirical)
# ECMWF IFS > JMA MSM > GFS > ICON > MétéoFrance > GEM (rough heuristic)
MODEL_WEIGHTS = {
    "ecmwf_ifs025": 0.30,
    "ecmwf_ifs025_long": 0.10,  # lower weight (long-range)
    "gfs_seamless": 0.15,
    "icon_seamless": 0.10,
    "gem_seamless": 0.08,
    "jma_msm": 0.15,  # high weight (East Asia high-res)
    "jma_seamless": 0.05,
    "meteofrance_seamless": 0.05,
    "metno_seamless": 0.02,
}


def meta_planner_synthesize(workers: list[WorkerResult]) -> dict:
    """Weighted consensus synthesis (TianJi-style analyst)."""
    valid = [w for w in workers if w.tmax_c is not None]
    if not valid:
        return {"tmax_c": None, "spread_c": None, "confidence": "none", "n": 0}
    # Apply weights
    weighted_sum = 0.0
    weight_total = 0.0
    raw_values = []
    raw_weights = []
    for w in valid:
        w_weight = MODEL_WEIGHTS.get(w.name, 0.05)
        if w.role == "ensemble":
            # Ensemble's weight is boosted by member count
            w_weight *= min(w.raw_count / 50.0, 1.0)
        weighted_sum += w.tmax_c * w_weight
        weight_total += w_weight
        raw_values.append(w.tmax_c)
        raw_weights.append(w_weight)
    consensus = weighted_sum / weight_total if weight_total > 0 else None
    # Spread: weighted std
    if consensus is not None and len(raw_values) > 1:
        var = sum(w * (v - consensus) ** 2 for v, w in zip(raw_values, raw_weights)) / weight_total
        spread = var ** 0.5
    else:
        spread = valid[0].spread or 0
    # Confidence based on spread
    if spread < 0.8:
        confidence = "high"
    elif spread < 1.5:
        confidence = "medium"
    else:
        confidence = "low"
    return {
        "tmax_c": round(consensus, 2) if consensus is not None else None,
        "tmin_c": next((w.tmin_c for w in valid if w.tmin_c is not None and w.role != "ensemble"), None),
        "rain_mm": round(statistics.mean([w.rain_mm for w in valid if w.rain_mm is not None]), 2) if any(w.rain_mm for w in valid) else None,
        "spread_c": round(spread, 2),
        "confidence": confidence,
        "n_models": len(valid),
        "weighted_method": "weight * tmax / sum(weight)",
    }


def fetch_cma_official(city_code: str = "101020100") -> dict | None:
    """Fetch CMA-style official forecast from weather.com.cn (powered by CMA).

    city_code 101020100 = Shanghai.
    This is a deterministic human-issued forecast, not a model output.
    """
    import urllib.request
    import re
    try:
        # weather.com.cn 7-day forecast page (uses CMA data)
        url = f"http://www.weather.com.cn/weather/{city_code}.shtml"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9",
        })
        html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", errors="ignore")
        # Strategy: find all <li> blocks with date+weather+high+low pattern
        items = re.findall(r'<li[^>]*>(.*?)</li>', html, re.S)
        forecasts = []
        for it in items:
            text = re.sub(r"<[^>]+>", "|", it)
            text = re.sub(r"\s+", "", text)
            text = re.sub(r"\|+", "|", text)
            # Match pattern: date | weather | high | low (with ℃ symbols)
            if re.search(r"\d+℃", text) and len(text) < 200:
                parts = [p for p in text.split("|") if p]
                if len(parts) >= 3:
                    forecasts.append(parts)
        if forecasts:
            return {"source": "weather.com.cn (CMA)", "city_code": city_code, "items": forecasts[:10]}
        # Fallback: dump a chunk
        return {"source": "weather.com.cn (CMA)", "city_code": city_code, "raw_text": html[3000:5000]}
    except Exception as e:
        return {"source": "weather.com.cn (CMA)", "error": str(e)}


def run_consensus(
    lat: float,
    lon: float,
    date: str,
    include_models: list[str] = None,
    include_ensemble: bool = True,
) -> ConsensusResult:
    """Run all workers and synthesize consensus."""
    if include_models is None:
        include_models = ["ecmwf_ifs025", "gfs_seamless", "icon_seamless",
                          "gem_seamless", "jma_msm", "meteofrance_seamless"]
    workers = []
    for m in include_models:
        workers.append(deterministic_worker(m, lat, lon, date))
    if include_ensemble:
        workers.append(ensemble_worker("ecmwf_ifs025", lat, lon, date))
    consensus = meta_planner_synthesize(workers)
    # Try to also get CMA official forecast
    cma = fetch_cma_official("101020100")  # Shanghai
    return ConsensusResult(
        target_date=date,
        location={"lat": lat, "lon": lon},
        workers=workers,
        consensus=consensus,
        cma_official=cma,
        method="tianji-inspired weighted consensus (TianJi: meta-planner + workers)",
    )


# ----- CLI -----
if __name__ != "__main__":  # disabled for Kaggle inlining
    import sys
    lat = float(sys.argv[1]) if len(sys.argv) > 1 else 31.1433
    lon = float(sys.argv[2]) if len(sys.argv) > 2 else 121.8052
    date = sys.argv[3] if len(sys.argv) > 3 else "2026-06-14"
    print(f"Running TianJi-style consensus for {date} at ({lat}, {lon})")
    result = run_consensus(lat, lon, date)
    print()
    print("=== Worker results ===")
    for w in result.workers:
        if w.tmax_c is not None:
            spread_s = f"±{w.spread:.2f}" if w.spread is not None else ""
            print(f"  {w.name:25s} ({w.role:13s}, n={w.raw_count:>2}): T_max={w.tmax_c:5.2f}°C {spread_s} [{w.elapsed_ms:.0f}ms]")
        else:
            print(f"  {w.name:25s} ({w.role:13s}): FAILED [{w.elapsed_ms:.0f}ms]")
    print()
    print("=== Consensus ===")
    print(json.dumps(result.consensus, indent=2))
    print()
    print("=== CMA official ===")
    if result.cma_official:
        if "raw_text" in result.cma_official:
            print(f"  {result.cma_official.get('source', 'CMA')}: {result.cma_official['raw_text'][:200]}")
        elif "error" in result.cma_official:
            print(f"  CMA error: {result.cma_official['error']}")



# === Inlined reflective.py ===

"""
Zephyrus-Reflective agent (glue-programming version).

Implements the core Zephyrus idea: LLM writes Python code, system executes it
against ZephyrusWorld tools, observes result, refines.

For Kaggle free tier, supports three backends:
- "no-llm" (deterministic): hardcoded pipeline, no GPU needed
- "vllm": vLLM-served Qwen2.5-Coder (T4 fits 7B-AWQ)
- "transformers": fallback when vLLM not available

The reflective loop:
  Q -> [LLM generates code] -> [execute] -> [observe] -> [LLM refines or finalizes]
"""
import json
import os
import re
import subprocess
import sys
import textwrap
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ----- Reflection log -----
@dataclass
class ReflectionStep:
    step_num: int
    role: str  # "code" | "exec" | "observation" | "final"
    content: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class AgentResult:
    question: str
    final_answer: str
    steps: list[ReflectionStep]
    artifacts: dict = field(default_factory=dict)


# ----- Code execution sandbox -----
def execute_python(code: str, workdir: Path, timeout_s: int = 60) -> tuple[str, str, int]:
    """Run Python code in subprocess. Returns (stdout, stderr, returncode)."""
    script_path = workdir / "_agent_step.py"
    script_path.write_text(code, encoding="utf-8")
    try:
        proc = subprocess.run(
            [sys.executable, "-u", str(script_path)],
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        return proc.stdout, proc.stderr, proc.returncode
    except subprocess.TimeoutExpired:
        return "", f"Timeout after {timeout_s}s", -1
    except Exception as e:
        return "", f"Execution error: {e}", -1


# ----- LLM backend (optional, for the reflective loop) -----
class LLMBackend:
    """Abstract LLM backend. Subclass for vLLM/transformers/no-llm."""

    def generate(self, system: str, user: str, max_tokens: int = 2048) -> str:
        raise NotImplementedError


class NoLLMBackend(LLMBackend):
    """No-LLM mode: returns canned analysis. Used as baseline / Kaggle without GPU.

    The 'code' generated is a fixed analytical script that summarizes
    multi-model forecasts and ECMWF ensemble, produces a final answer.
    """

    def generate(self, system: str, user: str, max_tokens: int = 2048) -> str:
        # Hardcoded code that the system knows how to interpret the question
        # Wrap in ```python``` fences so the reflective loop regex picks it up
        return textwrap.dedent('''
            ```python
            # Generated by NoLLMBackend - structured analysis script
            import json
            import statistics
            from src.zephyrus_world.open_meteo import (
                get_forecast_multi_model, parse_forecast_bundle,
                get_ecmwf_ensemble, parse_ensemble_members,
                get_observation
            )

            # Use the question parameter if present
            q = qustion_text
            print(f"Question: {q}")
            print()

            # Step 1: Multi-model deterministic forecast
            raw = get_forecast_multi_model(LAT, LON, TARGET_DATE, TARGET_DATE)
            bundle = parse_forecast_bundle(raw, TARGET_DATE)
            print("=== Multi-model forecast ===")
            for m in bundle.models:
                if m.tmax_c is not None:
                    print(f"  {m.model:25s}: T_max={m.tmax_c:5.2f}°C  T_min={m.tmin_c}°C  rain={m.rain_mm}mm")

            # Step 2: ECMWF 50-member ensemble
            ens_raw = get_ecmwf_ensemble(LAT, LON, TARGET_DATE, TARGET_DATE)
            ens_parsed = parse_ensemble_members(ens_raw, TARGET_DATE)
            tmax_members = ens_parsed.get("members", {}).get("temperature_2m_max", [])
            if tmax_members:
                ens_mean = statistics.mean(tmax_members)
                ens_std = statistics.stdev(tmax_members)
                print(f"\\n=== ECMWF 50-member ensemble T_max ===")
                print(f"  mean={ens_mean:.2f}°C  std={ens_std:.2f}°C  range=[{min(tmax_members):.1f}, {max(tmax_members):.1f}]")
                p25, p50, p75 = sorted(tmax_members)[12], sorted(tmax_members)[25], sorted(tmax_members)[37]
                print(f"  IQR=[{p25:.1f}, {p75:.1f}]  median={p50:.1f}")

            # Step 3: Cross-model consensus
            det_tmax = [m.tmax_c for m in bundle.models if m.tmax_c is not None]
            print(f"\\n=== Cross-model consensus ===")
            if det_tmax:
                det_mean = statistics.mean(det_tmax)
                det_std = statistics.stdev(det_tmax) if len(det_tmax) > 1 else 0
                print(f"  Deterministic models: mean={det_mean:.2f}°C  std={det_std:.2f}°C")
            if tmax_members and det_tmax:
                # Hybrid: weight ensemble mean (50 members) with deterministic mean
                hybrid_mean = (ens_mean * 50 + det_mean * len(det_tmax)) / (50 + len(det_tmax))
                print(f"\\n=== Hybrid consensus (weighted: 50 ens + {len(det_tmax)} det) ===")
                print(f"  Hybrid mean T_max = {hybrid_mean:.2f}°C")
                # Save final numbers
                result = {
                    "ensemble_mean": ens_mean,
                    "ensemble_std": ens_std,
                    "deterministic_mean": det_mean,
                    "deterministic_std": det_std,
                    "hybrid_mean": hybrid_mean,
                    "n_deterministic": len(det_tmax),
                    "n_ensemble": len(tmax_members),
                }
                Path("/tmp/_agent_result.json").write_text(json.dumps(result, indent=2))
                print(f"\\n  -> Final consensus T_max: {hybrid_mean:.2f}°C")
            ```
        ''').replace("LAT", str(_LAT)).replace("LON", str(_LON)).replace("TARGET_DATE", f'"{_TARGET_DATE}"').replace("qustion_text", repr(_QUESTION))


# Globals set by NoLLMBackend on first use
_LAT = 0.0
_LON = 0.0
_TARGET_DATE = ""
_QUESTION = ""


def set_question_context(lat: float, lon: float, target_date: str, question: str):
    global _LAT, _LON, _TARGET_DATE, _QUESTION
    _LAT, _LON, _TARGET_DATE, _QUESTION = lat, lon, target_date, question


# ----- Reflective loop -----
def reflective_run(
    question: str,
    workdir: Path,
    lat: float,
    lon: float,
    target_date: str,
    backend: LLMBackend,
    max_iterations: int = 3,
    timeout_per_step: int = 60,
) -> AgentResult:
    """Run the Zephyrus-Reflective loop.

    1. Initialize question context (lat/lon/date)
    2. Backend generates code
    3. Execute code (ZephyrusWorld tools available)
    4. Observe stdout/stderr
    5. (Optional) Backend refines or finalizes
    6. Return AgentResult
    """
    set_question_context(lat, lon, target_date, question)
    workdir.mkdir(parents=True, exist_ok=True)

    # Make ZephyrusWorld importable in subprocess
    project_root = Path(__file__).parent.parent.parent.resolve()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root) + os.pathsep + env.get("PYTHONPATH", "")

    steps: list[ReflectionStep] = []
    final_answer = ""

    system_prompt = textwrap.dedent("""
        You are a Zephyrus-Reflective weather analysis agent. You have access to
        ZephyrusWorld tools (Python imports). Your task:

        1. Write Python code that uses the ZephyrusWorld tools to answer the question
        2. The system will execute the code and return stdout/stderr
        3. Analyze the result and either refine or finalize

        Available tools (import from src.zephyrus_world.open_meteo):
          - get_forecast_multi_model(lat, lon, start_date, end_date, models=None, ...)
          - get_ecmwf_ensemble(lat, lon, start_date, end_date, ...)
          - get_observation(lat, lon, start_date, end_date, ...)
          - geocode(name)
          - parse_forecast_bundle(raw, target_date)
          - parse_ensemble_members(raw, target_date)

        Variables available in scope: LAT, LON, TARGET_DATE, qustion_text.
        Output format: a single Python code block in ```python ... ``` fences.
    """).strip()

    user_prompt = f"Question: {question}\nLocation: lat={lat}, lon={lon}\nDate: {target_date}"

    for i in range(max_iterations):
        steps.append(ReflectionStep(step_num=i + 1, role="code",
                                    content=f"[Iteration {i+1}] generating code..."))
        raw = backend.generate(system_prompt, user_prompt)
        # Extract code block
        m = re.search(r"```python\s*(.*?)\s*```", raw, re.S)
        code = m.group(1) if m else raw
        steps.append(ReflectionStep(step_num=i + 1, role="code", content=code))

        # Execute
        env_script = textwrap.dedent(f"""
            import sys
            import json
            import statistics
            from pathlib import Path
            sys.path.insert(0, {str(project_root)!r})
            from src.zephyrus_world.open_meteo import (
                get_forecast_multi_model, parse_forecast_bundle,
                get_ecmwf_ensemble, parse_ensemble_members,
                get_observation, geocode
            )
        """)
        full_code = env_script + "\n" + code
        try:
            proc = subprocess.run(
                [sys.executable, "-u", "-c", full_code],
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=timeout_per_step,
                env=env,
            )
            stdout, stderr, rc = proc.stdout, proc.stderr, proc.returncode
        except subprocess.TimeoutExpired:
            stdout, stderr, rc = "", f"Timeout after {timeout_per_step}s", -1

        obs = f"STDOUT:\n{stdout}\nSTDERR:\n{stderr}\nRETURNCODE: {rc}"
        steps.append(ReflectionStep(step_num=i + 1, role="observation", content=obs))
        if rc != 0:
            user_prompt = f"{user_prompt}\n\nPrevious attempt failed. STDERR:\n{stderr}\n\nPlease fix the code."

    # Read final result if produced
    result_path = Path("/tmp/_agent_result.json")
    artifacts = {}
    if result_path.exists():
        artifacts = json.loads(result_path.read_text())
        final_answer = (
            f"Forecast consensus for {target_date} at ({lat}, {lon}): "
            f"T_max = {artifacts.get('hybrid_mean', 0):.2f}°C "
            f"(ensemble mean {artifacts.get('ensemble_mean', 0):.2f}°C ± "
            f"{artifacts.get('ensemble_std', 0):.2f}, "
            f"deterministic mean {artifacts.get('deterministic_mean', 0):.2f}°C ± "
            f"{artifacts.get('deterministic_std', 0):.2f}, "
            f"based on {artifacts.get('n_ensemble', 0)} ensemble + "
            f"{artifacts.get('n_deterministic', 0)} deterministic models)"
        )
    else:
        final_answer = f"Agent run completed. See {len(steps)} steps."

    return AgentResult(
        question=question,
        final_answer=final_answer,
        steps=steps,
        artifacts=artifacts,
    )


# ----- CLI -----
if __name__ != "__main__":  # disabled for Kaggle inlining
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--lat", type=float, default=31.1433)
    p.add_argument("--lon", type=float, default=121.8052)
    p.add_argument("--date", type=str, default="2026-06-14")
    p.add_argument("--backend", type=str, default="no-llm",
                   choices=["no-llm", "vllm", "transformers"])
    p.add_argument("--workdir", type=str, default="/tmp/zephyrus_run")
    args = p.parse_args()

    backend = NoLLMBackend()  # extend with vLLM/transformers as needed
    result = reflective_run(
        question=f"What is the forecast T_max for {args.date} at lat={args.lat}, lon={args.lon}?",
        workdir=Path(args.workdir),
        lat=args.lat, lon=args.lon, target_date=args.date,
        backend=backend,
        max_iterations=1,
    )
    print()
    print("=" * 60)
    print("FINAL ANSWER:")
    print(result.final_answer)
    print()
    print("ARTIFACTS:", json.dumps(result.artifacts, indent=2))



# === Main entrypoint ===

"""
Kaggle kernel: Zephyrus + TianJi forecast for Shanghai Pudong 2026-06-14.

This script bundles all source code as a single file (Kaggle kernel size limit).
All source modules are inlined as top-level Python modules.
"""
import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime

print(f"=== Zephyrus + TianJi forecast - {datetime.now().isoformat()} ===")
print(f"Python: {sys.version.split()[0]}")
print()

# Constants (Pudong Airport, WMO 58367)
PUDONG = {"name": "Shanghai Pudong Airport (ZSPD)",
          "lat": 31.1433, "lon": 121.8052, "elev_m": 4.0, "wmo_station": "58367"}

# === Run the forecast ===
t0 = time.time()

# Sanity check
print("Step 1: Geocoding")
geos = geocode("Pudong")
if geos:
    print(f"  Match: {geos[0].name} ({geos[0].latitude}, {geos[0].longitude})")
print()

# Run consensus
TARGET_DATE = "2026-06-14"
print(f"Step 2: TianJi consensus for {TARGET_DATE}")
result = run_consensus(PUDONG["lat"], PUDONG["lon"], TARGET_DATE)
print()
print("Worker results:")
for w in result.workers:
    if w.tmax_c is not None:
        spread_s = f"±{w.spread:.2f}" if w.spread is not None else ""
        print(f"  {w.name:25s} ({w.role:13s}, n={w.raw_count:>2}): T_max={w.tmax_c:5.2f}°C {spread_s} [{w.elapsed_ms:.0f}ms]")
    else:
        print(f"  {w.name:25s}: FAILED")

print()
print("Consensus:", json.dumps(result.consensus, indent=2, ensure_ascii=False))

# Save results
out = {
    "meta": {
        "run_id": datetime.now().strftime("%Y%m%dT%H%M%S"),
        "date": TARGET_DATE,
        "lat": PUDONG["lat"],
        "lon": PUDONG["lon"],
        "name": PUDONG["name"],
        "elapsed_s": round(time.time() - t0, 2),
        "framework": "Zephyrus + TianJi (glue)",
        "data_source": "Open-Meteo (ECMWF/GFS/ICON/JMA/GEM/MétéoFrance) + weather.com.cn (CMA)",
        "platform": "Kaggle",
    },
    "tianji": {
        "consensus": result.consensus,
        "workers": [
            {"name": w.name, "role": w.role, "n": w.raw_count,
             "tmax_c": w.tmax_c, "tmin_c": w.tmin_c, "rain_mm": w.rain_mm,
             "spread_c": w.spread, "elapsed_ms": w.elapsed_ms}
            for w in result.workers
        ],
    },
    "cma": result.cma_official,
}

# Final synthesis
cma_tmax = None
if result.cma_official and "items" in result.cma_official:
    import re
    for item in result.cma_official["items"]:
        text = " ".join(str(x) for x in item)
        if "14日" in text or "明天" in text:
            m = re.search(r"(\d+)℃", text)
            if m:
                cma_tmax = int(m.group(1))
                break

tianji_tmax = result.consensus.get("tmax_c")
tianji_spread = result.consensus.get("spread_c")
confidence = result.consensus.get("confidence")

final = {
    "tianji_consensus_tmax_c": tianji_tmax,
    "tianji_consensus_spread_c": tianji_spread,
    "tianji_confidence": confidence,
    "cma_official_tmax_c": cma_tmax,
    "cma_source": result.cma_official.get("source") if result.cma_official else None,
}

if tianji_tmax and cma_tmax:
    weighted_blend = tianji_tmax * 0.7 + cma_tmax * 0.3
    final["weighted_blend_tmax_c"] = round(weighted_blend, 2)
    final["interpretation"] = (
        f"TianJi multi-model consensus: {tianji_tmax}°C. "
        f"CMA official (human-issued): {cma_tmax}°C. "
        f"Weighted blend (70% models + 30% CMA): {round(weighted_blend, 2)}°C."
    )
out["final_synthesis"] = final

# Output directory: prefer /kaggle/working on Kaggle, else cwd/results
WORKING = Path("/kaggle/working") if Path("/kaggle/working").exists() else Path("./results")
WORKING.mkdir(parents=True, exist_ok=True)
out_path = WORKING / f"forecast_{TARGET_DATE}_{datetime.now().strftime('%Y%m%dT%H%M%S')}.json"
out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
print(f"\nSaved: {out_path}")

# Final print
print()
print("=" * 60)
print("FINAL PREDICTION for Shanghai Pudong 2026-06-14")
print("=" * 60)
print(json.dumps(final, indent=2, ensure_ascii=False))
print()
print(f"Total elapsed: {time.time() - t0:.2f}s")
