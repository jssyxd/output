# Historical Bias Correction Methodology

## 1. Goal

**Reduce systematic error** in NWP model forecasts by computing each model's
**climatological bias** (forecast - observation) over a recent training period
and applying it as a correction.

## 2. Data Sources

### 2.1 "Truth" data (observations)
- **ERA5 reanalysis** (1959-present), 0.25° resolution
- Source: Open-Meteo Archive API → `era5_seamless` model
- URL: `https://archive-api.open-meteo.com/v1/archive`
- This is the same data ECMWF assimilates; widely used as "ground truth" in
  atmospheric science (Hersbach et al. 2020, QJRMS).

### 2.2 Model "reanalysis" data (per-model behavior)
For each NWP model, we get its own reanalysis for the same period:
| Model | Reanalysis API name | Resolution | Notes |
|---|---|---|---|
| ECMWF IFS | `ecmwf_ifs025` | 0.25° | IFS HRES reanalysis (different from ERA5!) |
| ICON | `icon_seamless` | 13km | DWD's ICON-D2 reanalysis |
| GEM | `gem_seamless` | 15km | Canadian GEM reanalysis |
| NCEP/NOAA | `ncep_seamless` | 0.5° | NOAA's reanalysis |

### 2.3 Why reanalysis, not forecast?
- The forecast API only stores the **current** model run, not past ones
- Past forecasts are lost (we can't go back in time)
- BUT: each model's **reanalysis** is a clean signal of its systematic bias
  (it's how the model represents the "true" atmosphere when forced with obs)
- Reanalysis bias correlates strongly with forecast bias for short lead times
  (T+1 to T+5 days). This is the standard "MOS-like" approach.

## 3. Bias Computation

For each model `m` and variable `v` (T_max, T_min):
```
training_period = last N days where observations are complete
# (N=14 is a reasonable default: captures synoptic variability without
#  overfitting to one specific weather pattern)

bias[m, v] = mean over training_period ( model_reanalysis[m, v, t]
                                          - era5_observation[v, t] )

correction[m, v] = -bias[m, v]   # to ADD to raw forecast
corrected_forecast[m, v] = raw_forecast[m, v] + correction[m, v]
```

## 4. Caveats & Reasoning

1. **Reanalysis ≠ Forecast**: A model's reanalysis uses observations, so it's
   closer to "truth" than its forecast. But the systematic offset (e.g., model
   X tends to be 0.5°C warm in summer for Shanghai) is preserved. We're using
   reanalysis bias as a **proxy** for forecast bias.

2. **Short training period**: Using only 14 days captures the current weather
   regime. A longer period (1 year of June) captures seasonal bias but mixes
   regimes. We use 14 days as default; longer is configurable.

3. **Bias can flip with regime**: A model might be cold in clear-sky conditions
   and warm in cloudy conditions. A simple mean bias is a first-order correction.
   More sophisticated: bias as a function of weather type (cluster-based MOS),
   but that's beyond scope.

4. **Independent of weights**: We do **not** mix the bias-corrected forecasts
   with the raw forecasts. Each method is reported independently. The user
   can then compare:
   - Raw ECMWF: 22.9°C
   - ECMWF + bias correction: 22.9 - bias_ecmwf
   - Zephyrus-Reflective hybrid: 23.1°C
   - TianJi consensus: 23.4°C
   - CMA official: 24.0°C
   - Actual (later, via archive API): TBD

## 5. Why This Matters for Polymarket

Polymarket temperature markets have a specific resolution (e.g., "T_max on
6/14 in Shanghai ≥ 24°C?"). The market price reflects an *implied* probability
based on competing forecasters' T_max estimates. If your T_max estimate is
biased high by 1°C, you systematically overpay for "yes" on a 24°C+ market.

Bias correction is the simplest way to **calibrate** your forecast to the
empirical observation distribution.

## 6. Implementation

- Module: `src/methods/bias_correction.py`
- Function: `compute_bias_correction(latitude, longitude, n_days=14, target_date=None)`
- Returns: `dict[model_name -> bias_value]` for T_max and T_min
- Function: `apply_bias_correction(raw_forecast, biases)` → corrected forecast

## 7. References

- Hersbach, H., et al. (2020). The ERA5 global reanalysis. Q. J. R. Meteorol. Soc.
- Glahn, H. R., & Lowry, D. A. (1972). The use of model output statistics (MOS)
  to predict daily maximum and minimum temperatures. Weather and Forecasting.
- Open-Meteo Historical Weather API documentation.
