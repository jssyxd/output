"""
Historical bias correction using ERA5 reanalysis as ground truth.

For each NWP model available in Open-Meteo Archive API, compute its systematic
bias vs ERA5 over a recent training period. Apply correction to raw forecasts.

See docs/bias_correction.md for full methodology.
"""
from __future__ import annotations

import json
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from src.zephyrus_world.open_meteo import _http_get_json, ARCHIVE_URL


# Models available in BOTH forecast and archive APIs
# (must be in archive to compute bias)
ARCHIVE_COMPATIBLE_MODELS = [
    "era5_seamless",      # The "truth"
    "ecmwf_ifs025",       # ECMWF reanalysis
    "icon_seamless",      # DWD ICON
    "gem_seamless",       # Canadian GEM
    "ncep_seamless",      # NCEP/NOAA
    "ecmwf_ifs_analysis", # ECMWF analysis (similar to IFS025)
]


@dataclass
class BiasEstimate:
    """Bias estimate for a single model and variable."""
    model: str
    variable: str
    bias: float           # mean(model - era5) over training period
    std: float            # std of (model - era5)
    n_samples: int
    training_start: str
    training_end: str
    per_day_bias: list[float] = field(default_factory=list)


def get_reanalysis_data(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    models: list[str] = None,
) -> dict:
    """Fetch reanalysis data from Open-Meteo Archive API.

    Returns raw response with per-model daily T_max/T_min.
    """
    if models is None:
        models = ARCHIVE_COMPATIBLE_MODELS
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
        "models": ",".join(models),
        "timezone": "Asia/Shanghai",
    }
    return _http_get_json(ARCHIVE_URL, params)


def compute_bias(
    latitude: float,
    longitude: float,
    training_end_date: str,   # last day of training period (e.g., "2026-06-12")
    n_days: int = 14,
    models: list[str] = None,
) -> dict[str, dict[str, BiasEstimate]]:
    """Compute per-model, per-variable bias vs ERA5 over the last N days.

    Returns: { model_name: { variable: BiasEstimate } }
    """
    if models is None:
        models = [m for m in ARCHIVE_COMPATIBLE_MODELS if m != "era5_seamless"]
    # ERA5 is always included
    all_models = ["era5_seamless"] + [m for m in models if m != "era5_seamless"]

    end_dt = datetime.strptime(training_end_date, "%Y-%m-%d")
    start_dt = end_dt - timedelta(days=n_days - 1)
    start_date = start_dt.strftime("%Y-%m-%d")

    print(f"  Fetching reanalysis: {start_date} to {training_end_date} ({n_days} days)")
    raw = get_reanalysis_data(latitude, longitude, start_date, training_end_date, all_models)
    daily = raw.get("daily", {})
    time_arr = daily.get("time", [])

    out: dict[str, dict[str, BiasEstimate]] = {}
    # ERA5 baseline (try with and without suffix)
    era5_tmax = daily.get("temperature_2m_max_era5_seamless", daily.get("temperature_2m_max", []))
    era5_tmin = daily.get("temperature_2m_min_era5_seamless", daily.get("temperature_2m_min", []))
    if not era5_tmax:
        raise ValueError("No ERA5 data returned")

    for model in models:
        if model == "era5_seamless":
            continue
        out[model] = {}
        for var, era5_arr in [("temperature_2m_max", era5_tmax),
                              ("temperature_2m_min", era5_tmin)]:
            model_arr = daily.get(f"{var}_{model}", [])
            if not model_arr or len(model_arr) != len(era5_arr):
                # Try with archive-specific suffix
                for suffix in ["", "_analysis"]:
                    key = f"{var}_{model}{suffix}"
                    arr = daily.get(key)
                    if arr and len(arr) == len(era5_arr):
                        model_arr = arr
                        break
            if not model_arr or len(model_arr) != len(era5_arr):
                continue
            diffs = [m - e for m, e in zip(model_arr, era5_arr) if m is not None and e is not None]
            if not diffs:
                continue
            mean_bias = statistics.mean(diffs)
            std_bias = statistics.stdev(diffs) if len(diffs) > 1 else 0.0
            out[model][var] = BiasEstimate(
                model=model, variable=var,
                bias=round(mean_bias, 3),
                std=round(std_bias, 3),
                n_samples=len(diffs),
                training_start=start_date,
                training_end=training_end_date,
                per_day_bias=[round(d, 2) for d in diffs],
            )
    return out


def apply_bias_correction(
    raw_forecast: dict[str, float | None],
    biases: dict[str, dict[str, BiasEstimate]],
    variable: str = "temperature_2m_max",
) -> dict[str, float | None]:
    """Apply bias correction to a raw forecast.

    raw_forecast: { model_name: tmax_value or None }
    biases: { model_name: { variable: BiasEstimate } }
    Returns: { model_name: corrected_tmax or None }
    """
    out = {}
    for model, raw_val in raw_forecast.items():
        if raw_val is None:
            out[model] = None
            continue
        bias_obj = biases.get(model, {}).get(variable)
        if bias_obj is None:
            out[model] = raw_val
            continue
        # Correction: subtract the bias (model tends to be X high, so subtract X)
        out[model] = round(raw_val - bias_obj.bias, 2)
    return out


# ----- Quick CLI test -----
if __name__ == "__main__":
    # Use 2026-06-12 as training end (today is 6/13)
    print("Computing bias correction using ERA5 + per-model reanalysis...")
    biases = compute_bias(
        latitude=31.1433, longitude=121.8052,
        training_end_date="2026-06-12",
        n_days=14,
    )
    print()
    print(f"{'Model':<25} {'Variable':<25} {'Bias':>8} {'Std':>8} {'N':>4}")
    print("-" * 75)
    for model, var_dict in biases.items():
        for var, est in var_dict.items():
            print(f"{model:<25} {var:<25} {est.bias:>+7.3f}  {est.std:>6.3f}  {est.n_samples:>4}")
    print()
    print("Per-day bias (for T_max):")
    for model, var_dict in biases.items():
        if "temperature_2m_max" in var_dict:
            est = var_dict["temperature_2m_max"]
            print(f"  {model:25s}: {est.per_day_bias}")
