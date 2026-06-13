# Shanghai 2026-06-14/15/16 T_max Forecast (Independent Methods Comparison)

**Run**: T0 (initial)
**Generated**: 2026-06-13 ~22:00 UTC (14:00 CST) - approximately 2h after 12Z model runs
**Location**: Shanghai Pudong Airport (ZSPD, 31.1433°N, 121.8052°E)
**Framework**: Zephyrus + TianJi (glue-programming version) with **24 independent methods**

---

## 📊 Method Comparison Table

Each method runs **independently** (no weighted blending across methods).

| Method | 6/14 (°C) | 6/15 (°C) | 6/16 (°C) | σ |
|---|---|---|---|---|
| **Raw NWP models (no processing)** | | | | |
| raw_ecmwf_ifs025 | 22.90 | 24.10 | 24.80 | 0.96 |
| raw_gfs_seamless | 24.60 | 24.90 | 25.80 | 0.62 |
| raw_icon_seamless | 23.00 | 25.80 | 26.90 | 2.01 |
| raw_icon_global | 23.00 | 25.80 | 26.90 | 2.01 |
| raw_gem_seamless | 25.50 | 24.00 | 25.00 | 0.76 |
| raw_jma_msm | 23.30 | 24.20 | n/a | 0.64 |
| raw_jma_seamless | 23.30 | 24.20 | 25.30 | 1.00 |
| raw_meteofrance_seamless | 24.10 | 25.00 | 24.80 | 0.47 |
| raw_metno_seamless | 23.00 | 24.20 | 25.10 | 1.05 |
| raw_ukmo_seamless | 23.90 | 24.40 | 25.20 | 0.66 |
| **Aggregate methods (no bias correction)** | | | | |
| simple_mean | 23.66 | 24.66 | 25.53 | 0.94 |
| median | 23.30 | 24.30 | 25.20 | 0.95 |
| ecmwf_ensemble_mean | 23.08 | 24.44 | 25.03 | 1.00 |
| tianji_weighted | 23.48 | 24.53 | 25.35 | 0.94 |
| zephyrus_hybrid | 23.18 | 24.48 | 25.11 | 0.98 |
| cma_official | 24.00 | 24.00 | 24.00 | 0.00 |
| era5_persistence | 26.20 | n/a | n/a | - |
| **Bias-corrected methods** | | | | |
| bias_corrected_ecmwf_ifs025 | 21.95 | 23.15 | 23.85 | 0.96 |
| bias_corrected_gfs_seamless | 23.70 | 24.00 | 24.90 | 0.62 |
| bias_corrected_icon_seamless | 22.30 | 25.10 | 26.20 | 2.01 |
| bias_corrected_jma_msm | 23.30 | 24.20 | n/a | 0.64 |
| bias_corrected_mean | 23.41 | 24.41 | 25.26 | 0.93 |

## 📈 Visual Summary (T_max per method per date)

```
6/14  T_max range: 21.7 (bc_ecmwf) to 25.5 (raw_gem)  — spread = 3.8°C
6/15  T_max range: 23.2 (bc_ecmwf) to 25.8 (raw_icon)  — spread = 2.6°C
6/16  T_max range: 23.9 (bc_ecmwf) to 26.9 (raw_icon)  — spread = 3.0°C
```

The **wide spread** shows real inter-model disagreement. Bias correction
generally **lowers** the forecast (because reanalysis bias is positive in this
period for these models).

## 🔬 Bias Correction Methodology (摘要)

See full doc: `docs/bias_correction.md`

**Quick version**:
1. Pull ERA5 (truth) + per-model reanalysis for past 10 days (2026-06-04 to 2026-06-13)
2. Compute `bias[model] = mean(model_reanalysis - ERA5)`
3. Apply: `corrected_forecast = raw_forecast - bias[model]`

**Bias values found** (training: 2026-06-04 to 2026-06-13, n=4-9 days):
- ECMWF IFS: +0.95°C (warm bias)
- ICON: +0.70°C
- GEM: +0.83°C
- NCEP/GFS: +0.90°C (with high variance)

**Caveat**: Reanalysis bias ≠ forecast bias (reanalysis uses obs, forecast doesn't).
But the systematic offset is often correlated. We treat bias as a first-order correction.

## 🏗️ Frameworks Used

### Zephyrus (ICLR 2026, arxiv 2510.04017)
- **ZephyrusWorld**: Python API for weather tools (geolocation, forecasting, simulation, climatology)
- **Zephyrus-Direct**: single-shot code generation
- **Zephyrus-Reflective**: write-execute-observe-refine loop
- We use: `ZephyrusWorld-lite` (Open-Meteo wrapper) + `Zephyrus-Reflective` with no-LLM backend

### TianJi (arxiv 2603.27738, NUIST, March 2026)
- Multi-agent framework: meta-planner + worker agents
- Original: drives WRF numerical model
- We use: TianJi-style weighted consensus (ECMWF 30%, JMA 15%, GFS 15%, ICON 10%, etc.)

### Open-Meteo (data source)
- Free API, no key needed
- 10+ NWP models (ECMWF, GFS, ICON, JMA, GEM, MétéoFrance, UKMO, MET Norway)
- ECMWF 50-member ensemble
- ERA5 reanalysis (archive)
- 10k requests/day per IP

## 🔄 T+12h Re-run Plan

**Open-Meteo forecast data updates** every ~6h (00Z, 06Z, 12Z, 18Z model runs).
At T+12h (6/14 ~10:00 UTC = 18:00 CST), we'll have:
- 06Z model data (~4h old, fresh)
- 6/14 max temp will be observed by ~08:00 UTC (16:00 CST) - **known by T+12h!**

**To run the T+12h re-run**:
```bash
cd /home/da/桌面/Zephyrus
python3 run_forecast_v2_later.py --dates 2026-06-14 2026-06-15 2026-06-16 \
    --run-tag T1 --compare-with results_v2/T0
```

This will:
1. Re-fetch forecasts (likely different due to fresh 06Z model data)
2. Fetch actual ERA5 observation for 6/14 (now available)
3. Compute error table (predicted - actual) for each method
4. Show forecast evolution (T0 vs T+12h)

**Why we can't auto-run T+12h now**:
Open-Meteo doesn't expose historical model runs. To get the "12h later" data,
we need to actually wait for the next model cycle. The T+12h script is ready
to run when you are.

## 📁 Output Files

```
results_v2/T0/
├── 2026-06-14.json          # Full per-date results
├── 2026-06-15.json
├── 2026-06-16.json
├── comparison_T0.csv        # Cross-date comparison table
├── summary_T0.json          # Run metadata
└── REPORT.md                # This file
```

## ⚠️ Limitations

1. **Bias correction is single-regime**: Trained on past 10 days only. Doesn't
   capture seasonal/regime-dependent bias. Use with caution.
2. **JMA MSM unavailable for 6/16**: JMA MSM only has 1.5-day lead (vs 6/16
   being 3 days out). Fall back to JMA Seamless.
3. **Persistence baseline (era5_persistence) unreliable**: Only available when
   "yesterday" is in the past. Not computed for 6/15 and 6/16.
4. **CMA fetch is best-effort**: web scraping of weather.com.cn may break if
   site changes.
5. **No real T+12h demonstration**: The T+12h re-run must be executed manually
   ~12h from now.
