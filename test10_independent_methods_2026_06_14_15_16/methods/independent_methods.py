"""
Independent forecast methods.

Each method produces a T_max estimate **independently** (no weighted blending
across methods). The user can then compare which method is closest to truth.

Methods (in increasing complexity):
  M01. raw_<model>             - Just the raw NWP output
  M02. simple_mean             - Unweighted mean across all valid NWP models
  M03. median                  - Median across NWP models
  M04. ecmwf_ifs025            - Just ECMWF (often most accurate globally)
  M05. jma_msm                 - Just JMA MSM (often best for East Asia)
  M06. tianji_weighted         - TianJi-style weighted consensus (ECMWF 30%, JMA 15%, GFS 15%, ICON 10%, GEM 8%, MétéoFrance 5%, ensemble boost)
  M07. zephyrus_hybrid         - Zephyrus-Reflective hybrid (50 ens + N det, weighted)
  M08. bias_corrected          - simple_mean applied with bias correction
  M09. bias_corrected_ecmwf    - ECMWF raw with bias correction
  M10. cma_official            - CMA human-issued forecast (ground truth proxy)
  M11. era5_persistence        - "Tomorrow = today" (naive baseline)
  M12. ecmwf_ensemble_mean     - ECMWF 50-member mean
"""
from __future__ import annotations

import json
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from src.zephyrus_world.open_meteo import (
    FORECAST_URL, ENSEMBLE_URL, ARCHIVE_URL,
    get_forecast_multi_model, parse_forecast_bundle,
    get_ecmwf_ensemble, parse_ensemble_members,
    get_observation, _http_get_json,
)
from src.methods.bias_correction import compute_bias, apply_bias_correction, BiasEstimate


# ----- Model registry -----
# (forecast_name, archive_name) - some models are forecast-only or archive-only
FORECAST_MODELS = [
    "ecmwf_ifs025",
    "gfs_seamless",
    "icon_seamless",
    "icon_global",
    "gem_seamless",
    "jma_msm",
    "jma_seamless",
    "meteofrance_seamless",
    "metno_seamless",
    "ukmo_seamless",
]

ARCHIVE_COMPATIBLE = {
    "ecmwf_ifs025": "ecmwf_ifs025",
    "icon_seamless": "icon_seamless",
    "gem_seamless": "gem_seamless",
    "gfs_seamless": "ncep_seamless",   # GFS forecast = NCEP reanalysis
}


@dataclass
class MethodResult:
    """Result from a single independent method."""
    method: str
    description: str
    tmax_c: float | None
    tmin_c: float | None
    confidence: str
    components: dict = field(default_factory=dict)
    notes: str = ""


def _fetch_model_with_timeout(model: str, lat: float, lon: float, date: str, timeout_s: float = 20.0) -> dict | None:
    """Fetch a single model's forecast with timeout."""
    def _run():
        return get_forecast_multi_model(lat, lon, date, date, models=[model])
    try:
        with ThreadPoolExecutor(max_workers=1) as ex:
            return ex.submit(_run).result(timeout=timeout_s)
    except Exception:
        return None


def fetch_all_models(lat: float, lon: float, date: str, models: list[str] = None) -> dict[str, float | None]:
    """Fetch T_max from all NWP models in parallel. Returns {model: tmax or None}."""
    if models is None:
        models = FORECAST_MODELS
    out = {}
    with ThreadPoolExecutor(max_workers=len(models)) as ex:
        futures = {ex.submit(_fetch_model_with_timeout, m, lat, lon, date): m for m in models}
        for fut in as_completed(futures):
            m = futures[fut]
            raw = fut.result()
            if raw is None:
                out[m] = None
                continue
            bundle = parse_forecast_bundle(raw, date)
            if bundle.models and bundle.models[0].tmax_c is not None:
                out[m] = bundle.models[0].tmax_c
            else:
                out[m] = None
    return out


def fetch_all_models_tmin(lat: float, lon: float, date: str, models: list[str] = None) -> dict[str, float | None]:
    """Same as fetch_all_models but for T_min."""
    if models is None:
        models = FORECAST_MODELS
    out = {}
    def _run(m):
        raw = _fetch_model_with_timeout(m, lat, lon, date)
        if raw is None:
            return m, None
        bundle = parse_forecast_bundle(raw, date)
        if bundle.models:
            return m, bundle.models[0].tmin_c
        return m, None
    with ThreadPoolExecutor(max_workers=len(models)) as ex:
        for m, v in [r for r in ex.map(_run, models)]:
            out[m] = v
    return out


def fetch_ecmwf_ensemble_stats(lat: float, lon: float, date: str) -> dict | None:
    """Fetch ECMWF 50-member ensemble stats."""
    try:
        raw = get_ecmwf_ensemble(lat, lon, date, date)
        parsed = parse_ensemble_members(raw, date)
        members = parsed.get("members", {}).get("temperature_2m_max", [])
        if not members:
            return None
        sorted_m = sorted(members)
        return {
            "mean": round(statistics.mean(members), 2),
            "median": sorted_m[len(members)//2],
            "std": round(statistics.stdev(members), 2),
            "p10": sorted_m[len(members)//10],
            "p90": sorted_m[(len(members)*9)//10],
            "min": sorted_m[0],
            "max": sorted_m[-1],
            "n": len(members),
        }
    except Exception:
        return None


def fetch_cma_forecast(city_code: str = "101020100") -> dict | None:
    """Fetch CMA official forecast (weather.com.cn powered by CMA)."""
    import urllib.request
    import re
    try:
        url = f"http://www.weather.com.cn/weather/{city_code}.shtml"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9",
        })
        html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", errors="ignore")
        items = re.findall(r'<li[^>]*>(.*?)</li>', html, re.S)
        forecasts = []
        for it in items:
            text = re.sub(r"<[^>]+>", "|", it)
            text = re.sub(r"\s+", "", text)
            text = re.sub(r"\|+", "|", text)
            if re.search(r"\d+℃", text) and len(text) < 200:
                parts = [p for p in text.split("|") if p]
                if len(parts) >= 3:
                    forecasts.append(parts)
        return {"source": "weather.com.cn (CMA)", "city_code": city_code, "items": forecasts[:10]}
    except Exception as e:
        return {"source": "weather.com.cn (CMA)", "error": str(e)}


def parse_cma_tmax(cma_data: dict, target_date: str) -> float | None:
    """Extract T_max for a specific date from CMA forecast."""
    if not cma_data or "items" not in cma_data:
        return None
    import re
    # target_date "2026-06-14" -> match "14日"
    day = target_date.split("-")[2]
    day_match = f"{int(day)}日"
    for item in cma_data["items"]:
        text = " ".join(str(x) for x in item)
        if day_match in text or "明天" in text:  # 明天 = "tomorrow" (only matches if target is +1)
            m = re.search(r"(\d+)℃", text)
            if m:
                return int(m.group(1))
    return None


# ----- Methods -----
MODEL_WEIGHTS_TIANJI = {
    "ecmwf_ifs025": 0.30,
    "gfs_seamless": 0.15,
    "icon_seamless": 0.10,
    "icon_global": 0.05,
    "gem_seamless": 0.08,
    "jma_msm": 0.15,
    "jma_seamless": 0.05,
    "meteofrance_seamless": 0.05,
    "metno_seamless": 0.02,
    "ukmo_seamless": 0.03,
}


def method_raw_models(per_model: dict[str, float | None]) -> dict[str, MethodResult]:
    """M01 family: just the raw NWP model output, no processing."""
    out = {}
    for model, tmax in per_model.items():
        if tmax is None:
            continue
        out[f"raw_{model}"] = MethodResult(
            method=f"raw_{model}",
            description=f"Raw forecast from {model} (no processing)",
            tmax_c=tmax, tmin_c=None, confidence="medium",
            components={"model": model, "raw_tmax": tmax},
        )
    return out


def method_simple_mean(per_model: dict[str, float | None]) -> MethodResult:
    """M02: Unweighted mean across all valid NWP models."""
    valid = [v for v in per_model.values() if v is not None]
    if not valid:
        return MethodResult("simple_mean", "Unweighted mean", None, None, "none")
    mean = round(statistics.mean(valid), 2)
    return MethodResult(
        method="simple_mean",
        description=f"Unweighted mean of {len(valid)} NWP models",
        tmax_c=mean, tmin_c=None,
        confidence="medium" if len(valid) >= 5 else "low",
        components={"n_models": len(valid), "values": list(valid)},
    )


def method_median(per_model: dict[str, float | None]) -> MethodResult:
    """M03: Median across NWP models (robust to outliers)."""
    valid = [v for v in per_model.values() if v is not None]
    if not valid:
        return MethodResult("median", "Median", None, None, "none")
    return MethodResult(
        method="median",
        description=f"Median of {len(valid)} NWP models",
        tmax_c=round(statistics.median(valid), 2), tmin_c=None,
        confidence="medium" if len(valid) >= 5 else "low",
        components={"n_models": len(valid), "values": sorted(valid)},
    )


def method_single_model(per_model: dict[str, float | None], model: str) -> MethodResult:
    """M04/M05: Single model."""
    v = per_model.get(model)
    return MethodResult(
        method=model,
        description=f"Raw output from {model} only",
        tmax_c=v, tmin_c=None,
        confidence="medium" if v is not None else "none",
        components={"model": model},
    )


def method_tianji_weighted(per_model: dict[str, float | None], ens_mean: float | None, ens_count: int = 0) -> MethodResult:
    """M06: TianJi-style weighted consensus."""
    valid = {m: v for m, v in per_model.items() if v is not None}
    if not valid:
        return MethodResult("tianji_weighted", "TianJi weighted consensus", None, None, "none")
    weighted_sum = 0.0
    weight_total = 0.0
    for m, v in valid.items():
        w = MODEL_WEIGHTS_TIANJI.get(m, 0.05)
        weighted_sum += v * w
        weight_total += w
    if ens_mean is not None and ens_count > 0:
        # Add ensemble member with reduced weight (correlated with deterministic)
        ens_weight = 0.20 * min(ens_count / 50.0, 1.0)
        weighted_sum += ens_mean * ens_weight
        weight_total += ens_weight
    if weight_total == 0:
        return MethodResult("tianji_weighted", "TianJi weighted consensus", None, None, "none")
    consensus = round(weighted_sum / weight_total, 2)
    spread = round(statistics.stdev(list(valid.values())), 2) if len(valid) > 1 else 0.5
    confidence = "high" if spread < 0.8 else ("medium" if spread < 1.5 else "low")
    return MethodResult(
        method="tianji_weighted",
        description=f"TianJi-style weighted consensus ({len(valid)} det + ensemble boost)",
        tmax_c=consensus, tmin_c=None, confidence=confidence,
        components={"weights": {m: MODEL_WEIGHTS_TIANJI.get(m, 0.05) for m in valid},
                    "ensemble_mean": ens_mean, "n_models": len(valid)},
    )


def method_zephyrus_hybrid(per_model: dict[str, float | None], ens_mean: float | None, ens_std: float | None) -> MethodResult:
    """M07: Zephyrus-Reflective hybrid (50 ens + N det, member-weighted)."""
    det_valid = [v for v in per_model.values() if v is not None]
    if not det_valid and ens_mean is None:
        return MethodResult("zephyrus_hybrid", "Zephyrus hybrid", None, None, "none")
    det_mean = statistics.mean(det_valid) if det_valid else 0
    n_det = len(det_valid)
    n_ens = 50 if ens_mean is not None else 0
    if n_ens == 0:
        # Fallback: simple mean
        return method_simple_mean(per_model).__class__(
            method="zephyrus_hybrid",
            description="Zephyrus hybrid (degraded: no ensemble)",
            tmax_c=round(det_mean, 2) if det_valid else None,
            tmin_c=None, confidence="low",
            components={"det_mean": det_mean, "n_det": n_det, "n_ens": 0},
        )
    hybrid = round((ens_mean * 50 + det_mean * n_det) / (50 + n_det), 2)
    return MethodResult(
        method="zephyrus_hybrid",
        description=f"Zephyrus hybrid: 50 ensemble + {n_det} deterministic, member-weighted",
        tmax_c=hybrid, tmin_c=None, confidence="high" if n_det >= 3 else "medium",
        components={"det_mean": det_mean, "n_det": n_det, "ens_mean": ens_mean, "ens_std": ens_std},
    )


def method_bias_corrected(per_model: dict[str, float | None], biases: dict, variable: str = "temperature_2m_max") -> MethodResult:
    """M08: Simple mean with bias correction applied per model."""
    corrected = apply_bias_correction(per_model, biases, variable)
    valid = [v for v in corrected.values() if v is not None]
    raw_valid = [v for v in per_model.values() if v is not None]
    if not valid:
        return MethodResult("bias_corrected_mean", "Bias-corrected mean", None, None, "none")
    mean = round(statistics.mean(valid), 2)
    return MethodResult(
        method="bias_corrected_mean",
        description=f"Bias-corrected mean: per-model ERA5 bias subtracted, then averaged ({len(valid)} models)",
        tmax_c=mean, tmin_c=None, confidence="high" if len(valid) >= 5 else "medium",
        components={"corrected": corrected, "raw": per_model,
                    "biases_applied": {m: biases.get(m, {}).get(variable, BiasEstimate(m, variable, 0, 0, 0, "", "")).bias
                                       for m in per_model if m in biases}},
    )


def method_bias_corrected_single(per_model: dict[str, float | None], biases: dict, model: str) -> MethodResult:
    """M09: Single model with bias correction."""
    raw = per_model.get(model)
    if raw is None:
        return MethodResult(f"bias_corrected_{model}", f"{model} + bias", None, None, "none")
    bias = biases.get(model, {}).get("temperature_2m_max")
    if bias is None:
        # Use NCEP if GFS
        if model == "gfs_seamless":
            bias = biases.get("ncep_seamless", {}).get("temperature_2m_max")
    if bias is None:
        return MethodResult(f"bias_corrected_{model}", f"{model} + bias (no bias data)",
                          tmax_c=raw, tmin_c=None, confidence="none")  # placeholder
    corrected = round(raw - bias.bias, 2)
    return MethodResult(
        method=f"bias_corrected_{model}",
        description=f"{model} raw - bias ({bias.bias:+.2f}°C) = bias-corrected forecast",
        tmax_c=corrected, tmin_c=None, confidence="medium",
        components={"raw": raw, "bias_value": bias.bias, "bias_std": bias.std, "n_samples": bias.n_samples},
    )


def method_cma_official(cma_data: dict, target_date: str) -> MethodResult:
    """M10: CMA official forecast (human-issued, not from NWP)."""
    tmax = parse_cma_tmax(cma_data, target_date)
    return MethodResult(
        method="cma_official",
        description="CMA 中央气象台 official human-issued forecast",
        tmax_c=tmax, tmin_c=None, confidence="high" if tmax is not None else "none",
        components={"source": "weather.com.cn (CMA)", "cma_data": cma_data},
    )


def method_era5_persistence(lat: float, lon: float, target_date: str) -> MethodResult:
    """M11: Naive baseline. T_max(tomorrow) = T_max(today)."""
    yesterday = (datetime.strptime(target_date, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
    tmax_yesterday = None
    try:
        obs = get_observation(lat, lon, yesterday, yesterday)
        daily = obs.get("daily", {})
        tmax_yesterday = daily.get("temperature_2m_max", [None])[0]
    except Exception as e:
        return MethodResult(
            method="era5_persistence",
            description=f"Naive persistence: cannot fetch yesterday ({yesterday}) data - {e}",
            tmax_c=None, tmin_c=None, confidence="none",
            components={"yesterday": yesterday, "error": str(e)},
        )
    return MethodResult(
        method="era5_persistence",
        description=f"Naive: today's T_max ({tmax_yesterday}°C) used as tomorrow's forecast",
        tmax_c=tmax_yesterday, tmin_c=None, confidence="low",
        components={"yesterday": yesterday, "yesterday_tmax": tmax_yesterday},
    )


def method_ecmwf_ensemble_mean(ens_stats: dict | None) -> MethodResult:
    """M12: ECMWF 50-member ensemble mean."""
    if not ens_stats:
        return MethodResult("ecmwf_ensemble_mean", "ECMWF 50-member ensemble mean", None, None, "none")
    return MethodResult(
        method="ecmwf_ensemble_mean",
        description=f"ECMWF 50-member ensemble mean (std={ens_stats['std']}°C)",
        tmax_c=ens_stats["mean"], tmin_c=None, confidence="high",
        components=ens_stats,
    )


# ----- Master runner -----
def run_all_methods(
    lat: float, lon: float, target_date: str,
    bias_training_end: str = None,
    n_bias_days: int = 14,
    include_models: list[str] = None,
    verbose: bool = True,
    precomputed_biases: dict = None,  # Allow passing pre-computed biases (for efficiency)
) -> dict[str, Any]:
    """Run all independent methods for a single target date.

    Returns dict with keys:
      - 'methods': {method_name: MethodResult}
      - 'per_model': {model: tmax or None}  (raw)
      - 'ens_stats': {stats}
      - 'cma_data': {cma}
      - 'biases': {bias_obj}
      - 'meta': {lat, lon, date, bias_training_period}
    """
    if include_models is None:
        include_models = FORECAST_MODELS

    if verbose:
        print(f"=== Running independent methods for {target_date} at ({lat}, {lon}) ===")
        print()

    # 1. Fetch all NWP models in parallel
    if verbose:
        print(f"Step 1: Fetching {len(include_models)} NWP models...")
    per_model = fetch_all_models(lat, lon, target_date, include_models)
    if verbose:
        for m, v in sorted(per_model.items()):
            print(f"  {m:25s}: {v if v is not None else 'FAILED'}°C")

    # 2. ECMWF ensemble
    if verbose:
        print()
        print("Step 2: ECMWF 50-member ensemble...")
    ens_stats = fetch_ecmwf_ensemble_stats(lat, lon, target_date)
    if verbose and ens_stats:
        print(f"  mean={ens_stats['mean']}°C  std={ens_stats['std']}  range=[{ens_stats['min']}, {ens_stats['max']}]")

    # 3. CMA
    if verbose:
        print()
        print("Step 3: CMA official forecast...")
    cma_data = fetch_cma_forecast()
    cma_tmax = parse_cma_tmax(cma_data, target_date)
    if verbose:
        print(f"  CMA T_max for {target_date}: {cma_tmax}°C")

    # 4. Bias correction
    biases = precomputed_biases
    if biases is None:
        if bias_training_end is None:
            bias_training_end = (datetime.strptime(target_date, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        if verbose:
            print()
            print(f"Step 4: Bias correction (training end: {bias_training_end}, days: {n_bias_days})")
        try:
            biases = compute_bias(lat, lon, bias_training_end, n_bias_days,
                                  models=list(ARCHIVE_COMPATIBLE.values()))
            if verbose:
                for model_name, var_dict in biases.items():
                    if "temperature_2m_max" in var_dict:
                        est = var_dict["temperature_2m_max"]
                        print(f"  {model_name:25s}: bias={est.bias:+.3f}°C  std={est.std:.3f}  n={est.n_samples}")
        except Exception as e:
            if verbose:
                print(f"  Bias computation failed: {e}")
            biases = {}
    elif verbose:
        print()
        print(f"Step 4: Bias correction (using precomputed biases, {len(biases)} models)")

    # 5. Run all methods
    if verbose:
        print()
        print("Step 5: Running methods (independent)...")
    methods: dict[str, MethodResult] = {}

    # Per-model raw (M01 family)
    methods.update(method_raw_models(per_model))

    # Aggregate methods
    methods["simple_mean"] = method_simple_mean(per_model)
    methods["median"] = method_median(per_model)
    methods["ecmwf_ifs025"] = method_single_model(per_model, "ecmwf_ifs025")
    methods["jma_msm"] = method_single_model(per_model, "jma_msm")
    ens_mean = ens_stats["mean"] if ens_stats else None
    ens_std = ens_stats["std"] if ens_stats else None
    methods["tianji_weighted"] = method_tianji_weighted(per_model, ens_mean, 50)
    methods["zephyrus_hybrid"] = method_zephyrus_hybrid(per_model, ens_mean, ens_std)
    if biases:
        methods["bias_corrected_mean"] = method_bias_corrected(per_model, biases)
        # Per-model bias-corrected
        for model in ["ecmwf_ifs025", "gfs_seamless", "jma_msm", "icon_seamless"]:
            if model in per_model:
                key = f"bias_corrected_{model}"
                methods[key] = method_bias_corrected_single(per_model, biases, model)
    methods["cma_official"] = method_cma_official(cma_data, target_date)
    methods["era5_persistence"] = method_era5_persistence(lat, lon, target_date)
    methods["ecmwf_ensemble_mean"] = method_ecmwf_ensemble_mean(ens_stats)

    if verbose:
        print()
        print(f"Step 6: Results ({len(methods)} methods)")
        print(f"{'Method':<35} {'T_max (°C)':>10} {'Conf':>10}")
        print("-" * 60)
        for name, m in sorted(methods.items()):
            tmax_s = f"{m.tmax_c:.2f}" if m.tmax_c is not None else "n/a"
            print(f"{name:<35} {tmax_s:>10} {m.confidence:>10}")
    return {
        "meta": {
            "lat": lat, "lon": lon, "target_date": target_date,
            "bias_training_end": bias_training_end,
            "n_bias_days": n_bias_days,
            "n_models_attempted": len(include_models),
            "n_models_succeeded": sum(1 for v in per_model.values() if v is not None),
        },
        "per_model": per_model,
        "ens_stats": ens_stats,
        "cma_data": cma_data,
        "biases": biases,
        "methods": methods,
    }
