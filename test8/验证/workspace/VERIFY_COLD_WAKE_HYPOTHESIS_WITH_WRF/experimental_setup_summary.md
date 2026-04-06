# Experimental Setup Summary

## Overview
Two experimental setups have been created from the original WPS met_em files for Typhoon Trami (2018):

1. **Control Setup**: Unmodified met_em files (baseline experiment)
2. **Perturbed Setup**: met_em files with -4.0°C cold wake SST perturbation applied

## File Organization

### Control Directory
- **Path**: `./workspace/VERIFY_COLD_WAKE_HYPOTHESIS_WITH_WRF/control/`
- **Contents**: 26 unmodified met_em files (13 for domain 1, 13 for domain 2)
- **Time Period**: 2018-09-27_00:00:00 to 2018-09-30_00:00:00 UTC (13 time steps)

### Perturbed Directory  
- **Path**: `./workspace/VERIFY_COLD_WAKE_HYPOTHESIS_WITH_WRF/perturbed/`
- **Contents**: 26 met_em files with SKINTEMP perturbations applied
- **Time Period**: Same as control (2018-09-27_00:00:00 to 2018-09-30_00:00:00 UTC)

## Perturbation Details

### Target Variable
- **Variable**: `SKINTEMP` (Surface skin temperature in Kelvin)
- **Rationale**: SKINTEMP represents sea surface temperature over ocean areas in met_em files

### Perturbation Magnitude
- **Value**: -4.0 K (-4.0°C)
- **Action**: Addition (subtract 4.0 from original values)

### Spatial Configuration
- **Geometric Type**: Sector (annular segment)
- **Radial Range**: 120-180 km from typhoon center
- **Angular Width**: 26 degrees (212° to 238° azimuth)
- **Sector Center**: 225° (southwest direction)
- **Rationale**: Represents upshear-left quadrant approximation for Northwest Pacific typhoons

### Temporal Configuration
- **Storm Centers**: Applied using time-varying typhoon track positions from filtered track data
- **Time Steps**: 13 time steps matching met_em file timestamps
- **Center Positions**: Mapped from `trami_2018_track_filtered.csv`

### Smoothing
- **Gaussian Smoothing**: σ = 2.0 grid points
- **Purpose**: Prevent numerical instability during WRF integration by creating smooth transitions

## Storm Center Mapping

| Timestamp | Latitude | Longitude |
|-----------|----------|-----------|
| 2018-09-27_00:00:00 | 21.5 | 129.1 |
| 2018-09-27_06:00:00 | 21.7 | 129.0 |
| 2018-09-27_12:00:00 | 21.9 | 128.8 |
| 2018-09-27_18:00:00 | 22.2 | 128.4 |
| 2018-09-28_00:00:00 | 22.5 | 127.9 |
| 2018-09-28_06:00:00 | 23.1 | 127.4 |
| 2018-09-28_12:00:00 | 23.8 | 127.0 |
| 2018-09-28_18:00:00 | 24.6 | 126.7 |
| 2018-09-29_00:00:00 | 25.4 | 126.8 |
| 2018-09-29_06:00:00 | 26.4 | 127.4 |
| 2018-09-29_12:00:00 | 27.8 | 128.4 |
| 2018-09-29_18:00:00 | 29.1 | 129.4 |
| 2018-09-30_00:00:00 | 30.5 | 130.9 |

## Technical Implementation

### Tools Used
- `perturb_wrf_nc`: Applied spatially-constrained perturbations to NetCDF files
- Standard shell commands: File copying and directory management

### Backup Files
- All original files automatically backed up with `.bak` extension before modification
- Backup files located in perturbed directory alongside modified files

### Validation
- Both domain 1 (18km) and domain 2 (6km) files successfully processed
- Total files processed: 26 (13 per domain)
- All perturbations applied successfully with appropriate smoothing

## Next Steps

These experimental setups are ready for:
1. WRF `real.exe` processing to generate initial/boundary conditions
2. WRF `wrf.exe` simulation execution
3. Comparative analysis between control and perturbed experiments

The perturbed setup specifically tests the hypothesis that a cold wake in the upshear-left quadrant affects typhoon intensity evolution.