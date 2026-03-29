# Typhoon In-fa SST Sensitivity Study: Trajectory Analysis Report

## Executive Summary

This analysis examines the impact of +2°C sea surface temperature (SST) perturbation on Typhoon In-fa's track during July 23-26, 2021. Contrary to the initial hypothesis of a significant northward shift, the results show a complex pattern with both northward and southward deviations, but **no consistent northward bias** throughout the simulation period.

## Data and Methodology

- **Control Group**: Standard SST conditions
- **Experiment Group**: +2°C SST perturbation applied
- **Simulation Period**: July 23, 2021 00:00 UTC to July 26, 2021 00:00 UTC
- **Output Frequency**: Every 3 hours (25 time steps total)
- **Typhoon Center Identification**: Minimum Sea Level Pressure (SLP) at each time step
- **Domain**: East China Sea region (120°-127°E, 23°-32°N)

## Key Findings

### 1. Overall Track Differences
- **Mean latitude difference**: -0.0292° (experiment slightly south of control on average)
- **Maximum separation**: 111.91 km between tracks
- **Final separation** (July 26, 00:00 UTC): 92.32 km

### 2. Critical Period Analysis (July 24-26)
During the period when Typhoon In-fa approached the East China coast:
- **Mean latitude difference**: -0.0585° (southward bias)
- **Maximum northward deviation**: +0.1787° at July 24, 09:00 UTC
- **Maximum southward deviation**: -0.3387° at July 25, 12:00 UTC

### 3. Temporal Evolution of Deviations

**Early Stage (July 23)**: Minimal differences between tracks
- Both simulations show nearly identical positions until July 23, 12:00 UTC

**Mid Stage (July 24)**: Mixed behavior with some northward shifts
- July 24, 00:00-09:00 UTC: Experiment shows northward shift (+0.0888° to +0.1787°)
- July 24, 12:00-18:00 UTC: Continued northward tendency (+0.0023° to +0.0927°)

**Late Stage (July 25-26)**: Predominantly southward shift
- July 25, 03:00 UTC onwards: Experiment consistently south of control
- Maximum southward deviation of -0.3387° at July 25, 12:00 UTC

## Scientific Conclusion

**The hypothesis that +2°C SST causes a significant northward shift in Typhoon In-fa's track is NOT supported by the evidence.**

### Evidence Against Northward Shift Hypothesis:
1. **Negative mean bias**: The experiment track is actually slightly south of the control on average (-0.0292°)
2. **Late-stage southward dominance**: During the critical landfall period (July 25-26), the experiment consistently tracks south of the control
3. **Inconsistent directional pattern**: While there are brief northward deviations on July 24, these are followed by more substantial southward shifts

### Possible Explanations:
1. **Non-linear SST response**: The relationship between SST and typhoon track may not be linear or monotonic
2. **Steering flow interactions**: Changes in SST may alter the larger-scale atmospheric circulation patterns that steer the typhoon
3. **Intensity-track coupling**: The +2°C SST leads to significantly lower central pressure (924.7 hPa vs 944.2 hPa minimum), which may affect the storm's interaction with steering currents

### Statistical Significance:
- Latitude differences range from -0.34° to +0.18°
- Most differences are within typical model uncertainty ranges
- The maximum separation of ~112 km is significant for operational forecasting but does not show consistent directional bias

## Implications

1. **Forecast sensitivity**: SST perturbations can cause meaningful track differences (~100 km), highlighting the importance of accurate SST specification in typhoon forecasting
2. **Complex response**: The track response to SST changes is not simply northward; it depends on the interaction between storm intensity, steering flows, and regional atmospheric conditions
3. **Model validation**: These results suggest that simple hypotheses about SST effects on typhoon tracks may be insufficient; comprehensive sensitivity studies are needed

## Recommendations

1. **Multi-member ensemble**: Conduct ensemble simulations to better quantify uncertainty
2. **Different SST perturbation magnitudes**: Test various SST increase scenarios to understand non-linear responses
3. **Mechanistic analysis**: Investigate the specific atmospheric processes causing the observed track differences
4. **Operational consideration**: Account for SST uncertainty in operational typhoon forecasting systems

## Data Availability

- Trajectory data: `typhoon_infa_trajectories.csv`
- Detailed analysis: `typhoon_infa_trajectories_detailed.csv`
- Visualization: `typhoon_infa_both_trajectories.png`

---
*Analysis completed on Typhoon In-fa SST sensitivity study dataset*