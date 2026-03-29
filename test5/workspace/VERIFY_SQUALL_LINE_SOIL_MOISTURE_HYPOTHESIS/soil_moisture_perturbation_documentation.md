# Soil Moisture Perturbation Documentation for Jianghuai Squall Line Case (2020-06-12)

## Overview
This document describes the methodology used to create control and perturbed initial conditions for the Jianghuai squall line case study on June 12, 2020, by modifying soil moisture fields in the wrfinput files.

## Domain Configuration
- **Region**: Jianghuai region (28-35°N, 115-122°E)
- **Simulation Period**: 2020-06-12 00:00 UTC to 2020-06-13 00:00 UTC (24 hours)
- **Domain Type**: Single domain (d01)
- **Grid Resolution**: 4 km × 4 km
- **Grid Points**: 201 × 201 (e_we × e_sn)
- **Total Domain Size**: ~800 km × ~800 km
- **Center Latitude**: 31.5°N
- **Center Longitude**: 118.5°E
- **Actual Domain Bounds**: 
  - Latitude: 27.86°N to 35.08°N
  - Longitude: 114.14°E to 122.86°E

## Meteorological Data Processing
- **Input Data**: FNL (Final Operational Global Analysis) meteorological data
- **Time Steps**: 5 time steps at 6-hour intervals (00Z, 06Z, 12Z, 18Z on 2020-06-12, and 00Z on 2020-06-13)
- **Processing Chain**: ungrib.exe → metgrid.exe → real.exe
- **Soil Layers**: 4 layers (consistent with Noah LSM)

## Perturbation Methodology

### Rationale
For the Jianghuai squall line case on June 12, 2020, historical analysis indicates that convection typically initiates in the western part of the Jianghuai region and propagates eastward/northeastward. The perturbation was applied to the region **ahead** of the expected squall line propagation path to test the hypothesis that soil moisture conditions in the downstream region influence squall line development and intensity.

### Perturbation Region Selection
Based on the typical squall line propagation pattern and domain configuration:

- **Latitude Range**: 30.0°N to 34.0°N
  - Covers the main squall line corridor within the Jianghuai region
  - Avoids extreme northern and southern boundaries
  
- **Longitude Range**: 119.0°E to 122.0°E  
  - Represents the eastern/northeastern portion of the domain
  - Located ahead of the typical initial convection area (which would be west of 119°E)
  - Includes areas where the squall line is expected to propagate into

### Perturbation Parameters
- **Variable Modified**: SMOIS (soil moisture content)
- **Reduction Factor**: 50% (multiply by 0.5)
- **Spatial Smoothing**: Gaussian smoothing with σ = 2 grid points
  - Applied to prevent sharp gradients that could cause numerical instability
  - Creates smooth transition zones at the perturbation boundaries
- **Soil Layers Affected**: All 4 soil layers (surface to deep soil)

### Files Generated
1. **control_wrfinput_d01**: Original wrfinput file with unmodified soil moisture
2. **perturbed_wrfinput_d01**: wrfinput file with 50% soil moisture reduction in the specified region

### Verification Statistics
- **Control File**: Mean soil moisture = 0.46 m³/m³
- **Perturbed File**: Mean soil moisture = 0.41 m³/m³
- **Overall Reduction**: ~11% domain-wide average reduction
- **Local Reduction**: 50% reduction within the specified perturbation region

## Technical Implementation
- **Tool Used**: `perturb_wrf_nc` function with precise lat/lon bounds
- **Backup Created**: Original wrfinput_d01 automatically backed up as wrfinput_d01.bak
- **File Format**: NetCDF format compatible with WRF v4.x
- **Physics Scheme**: Noah Land Surface Model (LSM) with 4 soil layers

## Expected Impact
The 50% soil moisture reduction in the downstream region is expected to:
1. Reduce evapotranspiration and latent heat flux
2. Increase sensible heat flux and surface temperature
3. Modify boundary layer structure and stability
4. Potentially influence squall line propagation speed and intensity
5. Test the sensitivity of convective systems to antecedent soil moisture conditions

This experimental design allows for direct comparison between control and perturbed simulations to quantify the impact of soil moisture on squall line dynamics in the Jianghuai region.