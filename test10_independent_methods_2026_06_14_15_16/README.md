# Independent Methods Forecast: Shanghai 2026-06-14/15/16 (Polymarket test v2)

## What's new vs test9
- **No weighted blending across methods** — each method is reported independently
- **24 methods total** (raw, aggregate, bias-corrected, naive baselines)
- **Bias correction** using ERA5 reanalysis vs per-model reanalysis (10 days)
- **Multi-date**: 6/14, 6/15, 6/16 simultaneously
- **T+12h re-run script** ready (`run_forecast_v2_later.py`)

## Results (T0)
See `T0_results/REPORT.md` for the full comparison table.

Quick summary (6/14 T_max):
- TianJi weighted: 23.48°C
- Zephyrus hybrid: 23.18°C
- CMA official: 24.00°C
- Simple mean: 23.66°C
- ECMWF raw: 22.90°C
- Bias-corrected ECMWF: 21.95°C (lowest)
- Raw GEM: 25.50°C (highest)
- Range: 21.95 - 25.50°C (3.55°C spread)

## Run instructions
```bash
# T0 (already done):
python3 run_forecast_v2.py --dates 2026-06-14 2026-06-15 2026-06-16 --run-tag T0

# T+12h re-run (12h from now):
python3 run_forecast_v2_later.py --dates 2026-06-14 2026-06-15 2026-06-16 \
    --run-tag T1 --compare-with T0_results
```
