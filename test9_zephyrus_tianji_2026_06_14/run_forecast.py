"""
Main forecast runner: Zephyrus-Reflective + TianJi-consensus.

Combines:
1. Zephyrus-Reflective agent (write code -> execute -> observe loop)
2. TianJi-style meta-planner (multi-model weighted consensus)
3. CMA official forecast for ground truth reference

Output: JSON results + Markdown report.

Run: python3 -m run_forecast --date 2026-06-14
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from src.zephyrus_world.open_meteo import (
    get_forecast_multi_model,
    parse_forecast_bundle,
    get_ecmwf_ensemble,
    parse_ensemble_members,
    geocode,
    get_observation,
)
from src.agents.consensus import run_consensus, MODEL_WEIGHTS


# Shanghai Pudong Airport (ZSPD) - 31.1433N, 121.8052E, elev 4m
PUDONG = {"name": "Shanghai Pudong Airport (ZSPD)",
          "lat": 31.1433, "lon": 121.8052, "elev_m": 4.0,
          "wmo_station": "58367"}


def main():
    p = argparse.ArgumentParser(description="Zephyrus + TianJi forecast runner")
    p.add_argument("--date", type=str, required=True, help="Target date (YYYY-MM-DD)")
    p.add_argument("--lat", type=float, default=PUDONG["lat"])
    p.add_argument("--lon", type=float, default=PUDONG["lon"])
    p.add_argument("--name", type=str, default=PUDONG["name"])
    p.add_argument("--out", type=str, default="results")
    p.add_argument("--skip-zephyrus", action="store_true",
                   help="Skip Zephyrus-Reflective loop (faster)")
    p.add_argument("--skip-cma", action="store_true",
                   help="Skip CMA official fetch (faster)")
    args = p.parse_args()

    os.makedirs(args.out, exist_ok=True)
    t_start = time.time()

    print(f"=== Zephyrus + TianJi forecast for {args.date} at ({args.lat}, {args.lon}) ===")
    print(f"Location: {args.name}")
    print(f"Run started: {datetime.now().isoformat()}")
    print()

    # Step 1: Geocode (sanity check)
    print("Step 1: Geocoding sanity check")
    geo = geocode("Pudong")
    if geo:
        print(f"  First match: {geo[0].name}, {geo[0].country} @ ({geo[0].latitude}, {geo[0].longitude})")
    print()

    # Step 2: TianJi-style multi-worker consensus
    print("Step 2: TianJi-style consensus (multi-model + ensemble)")
    tianji_result = run_consensus(args.lat, args.lon, args.date)
    workers_data = [asdict(w) for w in tianji_result.workers]
    for w in tianji_result.workers:
        if w.tmax_c is not None:
            spread_s = f"±{w.spread:.2f}" if w.spread is not None else ""
            print(f"  {w.name:25s} ({w.role:13s}, n={w.raw_count:>2}): "
                  f"T_max={w.tmax_c:5.2f}°C {spread_s} [{w.elapsed_ms:.0f}ms]")
        else:
            print(f"  {w.name:25s} ({w.role:13s}): FAILED [{w.elapsed_ms:.0f}ms]")
    print(f"\n  Consensus: T_max = {tianji_result.consensus.get('tmax_c')}°C "
          f"± {tianji_result.consensus.get('spread_c')} "
          f"(confidence: {tianji_result.consensus.get('confidence')})")
    print()

    # Step 3: Zephyrus-Reflective (if not skipped)
    zephyrus_result = None
    if not args.skip_zephyrus:
        print("Step 3: Zephyrus-Reflective agent loop")
        from src.agents.reflective import reflective_run, NoLLMBackend
        zr = reflective_run(
            question=f"What is the forecast T_max for {args.date} at lat={args.lat}, lon={args.lon}?",
            workdir=Path(args.out) / "_zephyrus_workdir",
            lat=args.lat, lon=args.lon, target_date=args.date,
            backend=NoLLMBackend(),
            max_iterations=1,
        )
        zephyrus_result = {
            "final_answer": zr.final_answer,
            "artifacts": zr.artifacts,
            "n_steps": len(zr.steps),
        }
        print(f"  Zephyrus final: {zr.final_answer}")
        print()

    # Step 4: CMA official forecast
    cma = None
    if not args.skip_cma:
        print("Step 4: CMA official forecast (weather.com.cn)")
        cma = tianji_result.cma_official
        if cma and "items" in cma:
            for item in cma["items"][:5]:
                print(f"  {item}")
        print()

    # Build final answer
    consensus_tmax = tianji_result.consensus.get("tmax_c")
    consensus_spread = tianji_result.consensus.get("spread_c")
    confidence = tianji_result.consensus.get("confidence")

    # Cross-validate with CMA
    cma_6_14_tmax = None
    if cma and "items" in cma:
        for item in cma["items"]:
            text = " ".join(str(x) for x in item)
            # Look for "14日" (14th)
            if "14日" in text or ("15日" in text and "15日" in text and "明天" in text):
                # Extract number before ℃
                import re
                m = re.search(r"(\d+)℃", text)
                if m:
                    cma_6_14_tmax = int(m.group(1))
                    break

    # Final synthesis
    final_synthesis = {
        "tianji_consensus_tmax_c": consensus_tmax,
        "tianji_consensus_spread_c": consensus_spread,
        "tianji_confidence": confidence,
        "cma_official_tmax_c": cma_6_14_tmax,
        "cma_source": cma.get("source") if cma else None,
        "zephyrus_artifacts": zephyrus_result["artifacts"] if zephyrus_result else None,
    }
    # Average TianJi + CMA for a "blend" prediction
    if consensus_tmax and cma_6_14_tmax:
        blend = (consensus_tmax + cma_6_14_tmax) / 2
        # weight: TianJi (0.7) + CMA (0.3) - CMA is human-issued
        weighted_blend = consensus_tmax * 0.7 + cma_6_14_tmax * 0.3
        final_synthesis["blend_tmax_c"] = round(blend, 2)
        final_synthesis["weighted_blend_tmax_c"] = round(weighted_blend, 2)
        final_synthesis["interpretation"] = (
            f"TianJi consensus: {consensus_tmax}°C (models, dynamic). "
            f"CMA official: {cma_6_14_tmax}°C (human-issued). "
            f"Weighted blend (70% TianJi + 30% CMA): {round(weighted_blend, 2)}°C."
        )
    else:
        final_synthesis["interpretation"] = "Incomplete data; use TianJi consensus only."

    print("=" * 60)
    print("FINAL SYNTHESIS")
    print("=" * 60)
    print(json.dumps(final_synthesis, indent=2, ensure_ascii=False))

    # Save outputs
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    json_path = Path(args.out) / f"forecast_{args.date}_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "meta": {
                "run_id": timestamp,
                "date": args.date,
                "lat": args.lat,
                "lon": args.lon,
                "name": args.name,
                "elapsed_s": round(time.time() - t_start, 2),
                "framework": "Zephyrus + TianJi (glue)",
                "data_source": "Open-Meteo (free, no key) + weather.com.cn (CMA)",
            },
            "tianji": {
                "workers": workers_data,
                "consensus": tianji_result.consensus,
            },
            "zephyrus": zephyrus_result,
            "cma": cma,
            "final_synthesis": final_synthesis,
        }, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nJSON saved: {json_path}")

    # Markdown report
    md_path = Path(args.out) / f"forecast_{args.date}_{timestamp}.md"
    write_markdown_report(md_path, args, tianji_result, cma,
                          zephyrus_result, final_synthesis)
    print(f"Markdown report: {md_path}")
    return 0


def write_markdown_report(path, args, tianji_result, cma, zephyrus_result, final):
    lines = [
        f"# Forecast Report: {args.date}",
        "",
        f"**Location**: {args.name} (lat={args.lat}, lon={args.lon})",
        f"**Generated**: {datetime.now().isoformat()}",
        f"**Framework**: Zephyrus-Reflective + TianJi-consensus (glue-programming version)",
        f"**Data source**: Open-Meteo (NWP: ECMWF/GFS/ICON/JMA/GEM/MétéoFrance) + weather.com.cn (CMA)",
        "",
        "## Worker Results",
        "",
        "| Model | Role | N | T_max (°C) | Spread | Latency |",
        "|---|---|---|---|---|---|",
    ]
    for w in tianji_result.workers:
        spread = f"±{w.spread:.2f}" if w.spread is not None else "-"
        tmax = f"{w.tmax_c:.2f}" if w.tmax_c is not None else "FAILED"
        lines.append(f"| {w.name} | {w.role} | {w.raw_count} | {tmax} | {spread} | {w.elapsed_ms:.0f}ms |")
    lines.extend([
        "",
        "## TianJi Consensus",
        "",
        f"- **T_max**: {tianji_result.consensus.get('tmax_c')}°C",
        f"- **Spread**: ±{tianji_result.consensus.get('spread_c')}°C",
        f"- **Confidence**: {tianji_result.consensus.get('confidence')}",
        f"- **N models**: {tianji_result.consensus.get('n_models')}",
        "",
        "## CMA Official Forecast",
        "",
    ])
    if cma and "items" in cma:
        for item in cma["items"][:7]:
            lines.append(f"- " + " | ".join(str(x) for x in item))
    elif cma and "error" in cma:
        lines.append(f"- Error: {cma['error']}")
    if zephyrus_result:
        lines.extend([
            "",
            "## Zephyrus-Reflective",
            "",
            f"**Final answer**: {zephyrus_result['final_answer']}",
            "",
            "**Artifacts**:",
            "",
            "```json",
            json.dumps(zephyrus_result["artifacts"], indent=2, ensure_ascii=False),
            "```",
        ])
    lines.extend([
        "",
        "## Final Synthesis",
        "",
        f"**TianJi consensus T_max**: {final['tianji_consensus_tmax_c']}°C",
        f"**CMA official T_max**: {final['cma_official_tmax_c']}°C",
        f"**Weighted blend (70/30)**: {final.get('weighted_blend_tmax_c')}°C",
        f"**Confidence**: {final['tianji_confidence']}",
        "",
        f"**Interpretation**: {final['interpretation']}",
        "",
        "---",
        "",
        "## Methodology",
        "",
        "**Zephyrus-Reflective** (ICLR 2026): LLM agent writes Python code, executes it",
        "against ZephyrusWorld tools, observes result, refines. We use a deterministic",
        "no-LLM backend (Kaggle free-tier friendly).",
        "",
        "**TianJi** (arxiv 2603.27738, NUIST, 2026): multi-agent framework with",
        "meta-planner + worker agents. We use weighted consensus: ECMWF IFS (30%),",
        "JMA MSM (15%), GFS (15%), ICON (10%), with ensemble boost.",
        "",
        "**Data substitution**: Full WRF/TianJi code not yet open-sourced (per",
        "zwww-www/output README). Zephyrus full benchmark needs 550GB WeatherBench 2",
        "(> Kaggle 20GB limit). We use Open-Meteo (free API) for NWP data - same",
        "ECMWF/GFS/ICON/JMA models, just served differently.",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
