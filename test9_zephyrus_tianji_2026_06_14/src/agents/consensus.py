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
from __future__ import annotations

import json
import statistics
import time
from dataclasses import dataclass, field
from typing import Any

from src.zephyrus_world.open_meteo import (
    get_forecast_multi_model,
    parse_forecast_bundle,
    get_ecmwf_ensemble,
    parse_ensemble_members,
    get_observation,
)


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
if __name__ == "__main__":
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
