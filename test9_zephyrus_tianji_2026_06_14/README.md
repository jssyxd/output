# Zephyrus + TianJi Shanghai 2026-06-14 Forecast (Polymarket test)

## Quick summary
- **TianJi consensus T_max**: 23.44°C (high confidence, spread ±0.79°C)
- **CMA official T_max**: 24°C
- **Final prediction (weighted blend 70/30)**: 23.61°C

## Run platform
- Kaggle kernel: opclown1/shanghai-forecast-zephyrus-tianji-v2
- Total runtime: 14.5s (no GPU)
- Data: 6 NWP models + 50 ECMWF ensemble + CMA official

## Files
- `REPORT.md` - Full human-readable report
- `forecast_kaggle.json` - Raw JSON output from Kaggle
- `kaggle_run.log` - Kaggle kernel stdout/stderr
- `kaggle_kernel_singlfile.py` - Self-contained Kaggle kernel (all source inlined)
- `src/` - Local Python source
- `run_forecast.py` - Local CLI runner
- `build_kernel.py` - Script to build the Kaggle kernel

## Reproducibility
```bash
python3 run_forecast.py --date 2026-06-14
```
