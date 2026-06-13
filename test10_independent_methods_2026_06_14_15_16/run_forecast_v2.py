"""
Multi-date independent forecast runner.

Runs all independent methods for multiple target dates, with optional re-run
at a later time for forecast evolution comparison.

Usage:
  python3 run_forecast_v2.py --dates 2026-06-14 2026-06-15 2026-06-16
  python3 run_forecast_v2.py --dates 2026-06-14 2026-06-15 2026-06-16 --re-run-tag T0
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from src.methods.independent_methods import run_all_methods, FORECAST_MODELS
from src.zephyrus_world.open_meteo import get_observation

# Shanghai Pudong Airport (ZSPD)
PUDONG = {"name": "Shanghai Pudong Airport (ZSPD)",
          "lat": 31.1433, "lon": 121.8052, "elev_m": 4.0, "wmo_station": "58367"}


def main():
    p = argparse.ArgumentParser(description="Multi-date independent forecast runner")
    p.add_argument("--dates", nargs="+", required=True, help="Target dates YYYY-MM-DD")
    p.add_argument("--lat", type=float, default=PUDONG["lat"])
    p.add_argument("--lon", type=float, default=PUDONG["lon"])
    p.add_argument("--name", type=str, default=PUDONG["name"])
    p.add_argument("--out", type=str, default="results_v2")
    p.add_argument("--run-tag", type=str, default=None,
                   help="Label for this run (e.g., T0, T1, T12h). Auto = timestamp")
    p.add_argument("--n-bias-days", type=int, default=10,
                   help="Days of ERA5 reanalysis for bias correction training")
    p.add_argument("--quiet", action="store_true")
    args = p.parse_args()

    if args.run_tag is None:
        args.run_tag = f"T_{datetime.now().strftime('%Y%m%dT%H%M%S')}"
    out_dir = Path(args.out) / args.run_tag
    out_dir.mkdir(parents=True, exist_ok=True)
    t_start = time.time()

    print(f"=== Multi-date forecast ({args.run_tag}) ===")
    print(f"Location: {args.name} (lat={args.lat}, lon={args.lon})")
    print(f"Target dates: {args.dates}")
    print(f"Bias training days: {args.n_bias_days}")
    print(f"Output dir: {out_dir}")
    print()

    # Compute bias ONCE for all dates (bias is a model property, not a date property)
    # Use the most recent possible training end
    from datetime import datetime as dt, timedelta
    today = dt.now().strftime("%Y-%m-%d")
    yesterday = (dt.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    # The latest possible training end is the day before "today" (must be in past for ERA5)
    bias_training_end = yesterday

    print(f"Step 0: Computing bias correction ONCE (training end: {bias_training_end}, days: {args.n_bias_days})")
    from src.methods.bias_correction import compute_bias
    from src.methods.independent_methods import ARCHIVE_COMPATIBLE
    try:
        precomputed_biases = compute_bias(
            args.lat, args.lon, bias_training_end, args.n_bias_days,
            models=list(ARCHIVE_COMPATIBLE.values()),
        )
        print(f"  Bias computed for {len(precomputed_biases)} models")
        for m, v in precomputed_biases.items():
            if "temperature_2m_max" in v:
                est = v["temperature_2m_max"]
                print(f"    {m:25s}: bias={est.bias:+.3f}°C  std={est.std:.3f}  n={est.n_samples}")
    except Exception as e:
        print(f"  Bias pre-computation failed: {e}, will skip bias correction for all dates")
        precomputed_biases = {}
    print()

    all_results = {}
    for date in args.dates:
        result = run_all_methods(
            args.lat, args.lon, date,
            precomputed_biases=precomputed_biases,
            n_bias_days=args.n_bias_days,
            verbose=not args.quiet,
        )
        all_results[date] = result
        # Save per-date JSON
        date_path = out_dir / f"{date}.json"
        # MethodResult is a dataclass, need to serialize
        serializable = json.loads(json.dumps(result, default=lambda o: o.__dict__))
        date_path.write_text(json.dumps(serializable, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        print()
        print(f"  Saved: {date_path}")
        print()

    # ----- Build comparison table -----
    print("=" * 80)
    print("METHOD COMPARISON (per-date T_max in °C)")
    print("=" * 80)
    # Collect all method names
    all_methods: set[str] = set()
    for date, r in all_results.items():
        all_methods.update(r["methods"].keys())
    # Sort: per-model raw first, then aggregates, then bias-corrected
    def sort_key(name):
        if name.startswith("raw_"):
            return (0, name)
        if "bias_corrected" in name:
            return (2, name)
        return (1, name)
    sorted_methods = sorted(all_methods, key=sort_key)

    # Header
    print(f"{'Method':<32}", end="")
    for date in args.dates:
        print(f" {date:>11}", end="")
    print(f" {'std':>7}")
    print("-" * (32 + 12 * len(args.dates) + 8))

    # Rows
    for method in sorted_methods:
        print(f"{method:<32}", end="")
        vals = []
        for date in args.dates:
            m = all_results[date]["methods"].get(method)
            if m and m.tmax_c is not None:
                v = m.tmax_c
                vals.append(v)
                print(f" {v:>10.2f} ", end="")
            else:
                print(f" {'n/a':>10} ", end="")
        if vals:
            import statistics
            std = statistics.stdev(vals) if len(vals) > 1 else 0
            print(f" {std:>6.2f}")
        else:
            print(f" {'-':>6}")

    # Save CSV
    csv_path = out_dir / f"comparison_{args.run_tag}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["method"] + args.dates + ["std_across_dates", "n_valid_dates"])
        for method in sorted_methods:
            row = [method]
            vals = []
            for date in args.dates:
                m = all_results[date]["methods"].get(method)
                v = m.tmax_c if (m and m.tmax_c is not None) else ""
                row.append(v)
                if v != "":
                    vals.append(float(v))
            import statistics
            std = statistics.stdev(vals) if len(vals) > 1 else 0
            row.append(round(std, 2))
            row.append(len(vals))
            w.writerow(row)
    print(f"\nCSV saved: {csv_path}")

    # Save summary
    summary_path = out_dir / f"summary_{args.run_tag}.json"
    summary = {
        "meta": {
            "run_tag": args.run_tag,
            "lat": args.lat, "lon": args.lon, "name": args.name,
            "dates": args.dates,
            "n_bias_days": args.n_bias_days,
            "elapsed_s": round(time.time() - t_start, 2),
            "platform": sys.platform,
            "framework": "Zephyrus + TianJi (glue) v2",
            "models_attempted": FORECAST_MODELS,
        },
        "per_date_results": {
            date: {
                "n_models_succeeded": r["meta"]["n_models_succeeded"],
                "ensemble_stats": r["ens_stats"],
                "methods": {
                    name: {
                        "tmax_c": m.tmax_c,
                        "tmin_c": m.tmin_c,
                        "confidence": m.confidence,
                        "description": m.description,
                    }
                    for name, m in r["methods"].items()
                },
            }
            for date, r in all_results.items()
        },
    }
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"Summary: {summary_path}")
    print(f"\nTotal elapsed: {time.time() - t_start:.2f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
