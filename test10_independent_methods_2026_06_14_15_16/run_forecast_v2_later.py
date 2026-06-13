"""
T+12h re-run script. Run this ~12 hours after the T0 run.

Compares two snapshots of the same forecast to see how it evolves, and
(if available) fetches the actual ERA5 observation to validate which method
was closest.

Usage:
  # First, run T0 (in another terminal or earlier):
  python3 run_forecast_v2.py --dates 2026-06-14 2026-06-15 2026-06-16 --run-tag T0

  # 12 hours later, run T1 (this script):
  python3 run_forecast_v2_later.py --dates 2026-06-14 2026-06-15 2026-06-16 \
      --compare-with results_v2/T0 --run-tag T1
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from src.methods.independent_methods import run_all_methods, FORECAST_MODELS
from src.zephyrus_world.open_meteo import get_observation

PUDONG = {"name": "Shanghai Pudong Airport (ZSPD)",
          "lat": 31.1433, "lon": 121.8052, "elev_m": 4.0, "wmo_station": "58367"}


def fetch_actual_observation(lat: float, lon: float, date: str) -> dict | None:
    """Fetch ERA5 actual for a past date (only works if date is in the past)."""
    today = datetime.now().strftime("%Y-%m-%d")
    if date >= today:
        return None  # Not yet observed
    try:
        obs = get_observation(lat, lon, date, date)
        daily = obs.get("daily", {})
        return {
            "tmax_c": daily.get("temperature_2m_max", [None])[0],
            "tmin_c": daily.get("temperature_2m_min", [None])[0],
            "rain_mm": daily.get("precipitation_sum", [None])[0],
        }
    except Exception as e:
        return {"error": str(e)}


def main():
    p = argparse.ArgumentParser(description="T+12h re-run with comparison")
    p.add_argument("--dates", nargs="+", required=True)
    p.add_argument("--compare-with", type=str, default=None,
                   help="Path to previous run dir (e.g., results_v2/T0)")
    p.add_argument("--lat", type=float, default=PUDONG["lat"])
    p.add_argument("--lon", type=float, default=PUDONG["lon"])
    p.add_argument("--name", type=str, default=PUDONG["name"])
    p.add_argument("--out", type=str, default="results_v2")
    p.add_argument("--run-tag", type=str, default=None)
    p.add_argument("--n-bias-days", type=int, default=10)
    p.add_argument("--quiet", action="store_true")
    args = p.parse_args()

    if args.run_tag is None:
        args.run_tag = f"T_{datetime.now().strftime('%Y%m%dT%H%M%S')}"
    out_dir = Path(args.out) / args.run_tag
    out_dir.mkdir(parents=True, exist_ok=True)
    t_start = time.time()

    print(f"=== T+12h Re-run ({args.run_tag}) ===")
    print(f"Target dates: {args.dates}")
    print(f"Compare with: {args.compare_with}")
    print(f"Output dir: {out_dir}")

    # Bias pre-computation (same as before)
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    bias_training_end = yesterday
    print(f"\nStep 0: Bias correction (training end: {bias_training_end})")
    from src.methods.bias_correction import compute_bias
    from src.methods.independent_methods import ARCHIVE_COMPATIBLE
    try:
        precomputed_biases = compute_bias(
            args.lat, args.lon, bias_training_end, args.n_bias_days,
            models=list(ARCHIVE_COMPATIBLE.values()),
        )
        print(f"  Bias for {len(precomputed_biases)} models")
    except Exception as e:
        print(f"  Failed: {e}, will skip bias correction")
        precomputed_biases = {}

    # Run all methods
    all_results = {}
    actual_obs = {}
    for date in args.dates:
        print(f"\n=== Date: {date} ===")
        result = run_all_methods(
            args.lat, args.lon, date,
            precomputed_biases=precomputed_biases,
            n_bias_days=args.n_bias_days,
            verbose=not args.quiet,
        )
        all_results[date] = result
        # Save per-date
        date_path = out_dir / f"{date}.json"
        serializable = json.loads(json.dumps(result, default=lambda o: o.__dict__))
        date_path.write_text(json.dumps(serializable, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

        # Fetch actual observation if available
        actual = fetch_actual_observation(args.lat, args.lon, date)
        if actual and "tmax_c" in actual and actual["tmax_c"] is not None:
            actual_obs[date] = actual["tmax_c"]
            print(f"  *** ACTUAL OBSERVATION for {date}: T_max = {actual['tmax_c']}°C ***")
        else:
            print(f"  (No actual observation available for {date} yet)")

    # Save per-date results with actual
    for date, r in all_results.items():
        r["actual_observation"] = actual_obs.get(date)
        r_path = out_dir / f"{date}.json"
        serializable = json.loads(json.dumps(r, default=lambda o: o.__dict__))
        r_path.write_text(json.dumps(serializable, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    # ----- Build comparison table -----
    print("\n" + "=" * 80)
    print("METHOD COMPARISON (T+12h re-run, per-date T_max in °C)")
    print("=" * 80)
    all_methods: set[str] = set()
    for date, r in all_results.items():
        all_methods.update(r["methods"].keys())
    def sort_key(name):
        if name.startswith("raw_"):
            return (0, name)
        if "bias_corrected" in name:
            return (2, name)
        return (1, name)
    sorted_methods = sorted(all_methods, key=sort_key)

    print(f"{'Method':<32}", end="")
    for date in args.dates:
        print(f" {date:>11}", end="")
    if actual_obs:
        print(f" {'actual':>9}", end="")
    print()
    print("-" * (32 + 12 * len(args.dates) + (10 if actual_obs else 0)))

    for method in sorted_methods:
        print(f"{method:<32}", end="")
        for date in args.dates:
            m = all_results[date]["methods"].get(method)
            if m and m.tmax_c is not None:
                print(f" {m.tmax_c:>10.2f} ", end="")
            else:
                print(f" {'n/a':>10} ", end="")
        if actual_obs:
            # Show first available actual
            first_date = args.dates[0]
            actual = actual_obs.get(first_date)
            if actual is not None:
                m = all_results[first_date]["methods"].get(method)
                if m and m.tmax_c is not None:
                    err = m.tmax_c - actual
                    print(f" err={err:+.2f}", end="")
                else:
                    print(f" {'-':>9}", end="")
            else:
                print(f" {'-':>9}", end="")
        print()

    # Save CSV
    csv_path = out_dir / f"comparison_{args.run_tag}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        header = ["method"] + args.dates
        if actual_obs:
            header.append("actual_tmax_c")
            header.append("error_vs_actual")
        w.writerow(header)
        for method in sorted_methods:
            row = [method]
            for date in args.dates:
                m = all_results[date]["methods"].get(method)
                v = m.tmax_c if (m and m.tmax_c is not None) else ""
                row.append(v)
            if actual_obs:
                first_date = args.dates[0]
                actual = actual_obs.get(first_date)
                if actual is not None:
                    row.append(actual)
                    m = all_results[first_date]["methods"].get(method)
                    if m and m.tmax_c is not None:
                        row.append(round(m.tmax_c - actual, 2))
                    else:
                        row.append("")
                else:
                    row.extend(["", ""])
            w.writerow(row)
    print(f"\nCSV: {csv_path}")

    # Compare with previous run if provided
    if args.compare_with and Path(args.compare_with).exists():
        prev_dir = Path(args.compare_with)
        compare_path = out_dir / f"evolution_{args.run_tag}_vs_{prev_dir.name}.json"
        evolution = {"meta": {"new_run": args.run_tag, "previous_run": prev_dir.name}}
        for date in args.dates:
            prev_csv = prev_dir / f"comparison_{prev_dir.name}.csv"
            if not prev_csv.exists():
                continue
            # Parse previous CSV
            prev_data = {}
            with open(prev_csv) as f:
                r = csv.DictReader(f)
                for row in r:
                    if date in row and row[date]:
                        prev_data[row["method"]] = float(row[date])
            # Compare
            evo_date = {}
            for method in sorted_methods:
                m = all_results[date]["methods"].get(method)
                if m and m.tmax_c is not None:
                    new_v = m.tmax_c
                    old_v = prev_data.get(method)
                    if old_v is not None:
                        evo_date[method] = {"T0": old_v, "T1": new_v, "delta": round(new_v - old_v, 2)}
                    else:
                        evo_date[method] = {"T0": None, "T1": new_v, "delta": None}
            evolution[date] = evo_date
        compare_path.write_text(json.dumps(evolution, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        print(f"\nEvolution comparison: {compare_path}")

        # Print evolution table
        print("\n" + "=" * 80)
        print("FORECAST EVOLUTION (T0 -> T+12h)")
        print("=" * 80)
        print(f"{'Method':<32} {'6/14 Δ':>8} {'6/15 Δ':>8} {'6/16 Δ':>8}")
        print("-" * 60)
        for method in sorted_methods:
            deltas = []
            for date in args.dates:
                d = evolution.get(date, {}).get(method, {}).get("delta")
                deltas.append(f"{d:+.2f}" if d is not None else "  n/a")
            print(f"{method:<32} {deltas[0]:>8} {deltas[1]:>8} {deltas[2]:>8}")

    # Save final summary
    summary_path = out_dir / f"summary_{args.run_tag}.json"
    summary = {
        "meta": {
            "run_tag": args.run_tag,
            "lat": args.lat, "lon": args.lon, "name": args.name,
            "dates": args.dates,
            "elapsed_s": round(time.time() - t_start, 2),
            "framework": "Zephyrus + TianJi (glue) v2 T+12h re-run",
        },
        "actual_observations": actual_obs,
        "per_date": {
            date: {
                "n_models_succeeded": r["meta"]["n_models_succeeded"],
                "methods_tmax": {n: m.tmax_c for n, m in r["methods"].items()},
            }
            for date, r in all_results.items()
        },
    }
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"\nSummary: {summary_path}")
    print(f"\nTotal elapsed: {time.time() - t_start:.2f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
