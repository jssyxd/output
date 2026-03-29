# Jianghuai Squall Line Analysis: Control vs Perturbed Soil Moisture Simulations

## Executive Summary

This analysis compares WRF simulations of the 2020-06-12 Jianghuai squall line under control and perturbed soil moisture conditions. Key findings indicate that soil moisture perturbation significantly disrupts squall line coherence and weakens cold pool characteristics, while maintaining similar overall lifecycle duration.

## Methodology

### Data Sources
- **Control Simulation**: `/home/zkk/Build_WRF/WRF/run/control_simulation/`
- **Perturbed Simulation**: `/home/zkk/Build_WRF/WRF/run/perturbed_simulation/`
- **Variables Analyzed**: T2 (2m temperature), U10/V10 (10m winds), RAINNC (accumulated precipitation), SLP (sea level pressure)
- **Time Period**: 2020-06-12 00:00 - 23:45 UTC (96 time steps)

### Analysis Techniques
- Feature tracking using `locate_feature` on precipitation fields
- Radial statistics within 50km radius of squall line centers
- Temperature deficit calculation (pre-squall minus post-squall)
- Wind speed estimation from U10/V10 components
- Propagation speed calculation using haversine distance formula
- Statistical comparisons using RMSE and Pearson correlation

## Key Results

### 1. Squall Line Location and Timing

**Control Simulation:**
- Initial convection: 01:45 UTC at ~116.4°E, 34.9°N
- Main squall line phase: 08:30-19:00 UTC in Jianghuai region (~118.3°E, 32.7°N)
- Secondary activity: 22:45-23:45 UTC at ~117.1°E, 33.1°N
- Maximum precipitation: 195.0 mm at 23:45 UTC

**Perturbed Simulation:**
- Initial convection: 01:45 UTC at ~116.4°E, 34.9°N (same as control)
- Main activity shift: 12:00-19:00 UTC at ~115.6°E, 30.1°N (southward displacement)
- Secondary activity: 21:45-23:45 UTC at ~122.7°E, 33.5°N (far eastward)
- Maximum precipitation: 172.6 mm at 23:45 UTC

### 2. Cold Pool Characteristics

**Temperature Deficit Analysis (50km radius around squall line center):**

| Metric | Control | Perturbed | Difference | % Change |
|--------|---------|-----------|------------|----------|
| Pre-squall T2 (10:00 UTC) | 300.33 K | 302.35 K | +2.02 K | +0.67% |
| Post-squall T2 (13:00 UTC) | 298.81 K | 301.14 K | +2.33 K | +0.78% |
| **Temperature Deficit** | **1.52 K** | **1.21 K** | **-0.31 K** | **-20.4%** |

The perturbed simulation shows a 20.4% weaker cold pool, indicating reduced evaporative cooling or altered boundary layer processes due to soil moisture changes.

### 3. Wind Speed Enhancement

**Maximum Wind Speed Estimates:**

| Time | Control (m/s) | Perturbed (m/s) | Notes |
|------|---------------|-----------------|-------|
| 10:00 UTC (pre-squall) | ~14.5 | ~15.8 | Similar background flow |
| 13:00 UTC (post-squall) | ~14.5 | ~13.6 | Control maintains, perturbed decreases |

Neither simulation shows strong gust front wind enhancement, suggesting limitations in model resolution or squall line representation.

### 4. Squall Line Propagation Speed

**Control Simulation (Coherent Structure):**
- Period: 11:00-13:00 UTC
- Distance traveled: 155.6 km
- **Average speed: 77.8 km/h northeastward**

**Perturbed Simulation (Disrupted Structure):**
- No coherent propagation observed
- Discontinuous jump from 117.9°E, 32.6°N to 115.6°E, 30.0°N between 11:45-12:00 UTC
- Indicates squall line dissipation and new convection initiation

### 5. System Lifecycle Duration

| Metric | Control | Perturbed | Difference |
|--------|---------|-----------|------------|
| Total active period | 22 hours | 22 hours | 0 hours |
| Coherent squall line phase | ~10.5 hours | ~3.5 hours | -7 hours |
| Peak intensity timing | 23:45 UTC | 23:45 UTC | Same |

Both simulations maintain similar total lifecycle duration, but the perturbed case shows significantly reduced coherent squall line duration.

### 6. Statistical Comparisons

| Metric | Value | Interpretation |
|--------|-------|----------------|
| Temperature RMSE | 0.45 K | Small systematic differences |
| Precipitation RMSE | 6.34 mm | Moderate spatial/temporal displacement |
| Precipitation Correlation | 0.85 | High overall similarity with displacement |

## Conclusions

1. **Soil moisture perturbation disrupts squall line coherence**: The perturbed simulation fails to maintain a continuous squall line structure, instead showing separate convective systems.

2. **Weaker cold pool development**: The 20.4% reduction in temperature deficit suggests altered boundary layer thermodynamics due to modified surface fluxes.

3. **Spatial displacement**: The main convective activity shifts ~280 km southward in the perturbed case, indicating significant sensitivity to soil moisture conditions.

4. **Maintained lifecycle duration**: Despite structural differences, both simulations show similar total active periods, suggesting soil moisture affects organization more than overall storm longevity.

## Implications

These results support the hypothesis that soil moisture conditions significantly influence squall line organization and cold pool strength in the Jianghuai region. The perturbed (likely drier) soil conditions lead to:
- Reduced evaporative cooling efficiency
- Weaker cold pool-driven propagation
- Loss of coherent squall line structure
- Southward displacement of convective activity

This has important implications for weather forecasting and climate modeling in regions where soil moisture-atmosphere feedbacks are critical for convective system development.