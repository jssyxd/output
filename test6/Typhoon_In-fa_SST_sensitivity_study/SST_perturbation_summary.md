# SST Perturbation Summary Report

## Task Overview
Created perturbed met_em files for the experiment group by increasing the Sea Surface Temperature (SST) variable by exactly 2°C globally across all time steps.

## Process Completed

### 1. Target Directory Creation
- Successfully created directory: `./workspace/Typhoon_In-fa_SST_sensitivity_study/wps_met_em_perturbed/`

### 2. File Copying
- Copied all 13 met_em.d01.*.nc files from `/home/zkk/Build_WRF/WPS/` to the target directory
- Files cover the period from 2021-07-23_00:00:00 to 2021-07-26_00:00:00 UTC

### 3. SST Variable Identification
- Discovered that the SST variable in met_em files is named `SKINTEMP` (Skin temperature)
- Confirmed SKINTEMP represents sea surface temperature over ocean areas
- Variable units are in Kelvin (K)

### 4. Perturbation Application
- Applied +2.0 K (+2°C) perturbation to the SKINTEMP variable in all 13 met_em files
- Used the `perturb_wrf_nc` tool with global scope (no spatial filtering)
- All other meteorological variables remain unchanged
- The tool automatically created .bak backup files for each original file

### 5. Verification Results
- **Files processed**: 13/13 successful
- **Perturbation magnitude**: Exactly +2.0 K confirmed by before/after statistics
- **Example verification**: 
  - Original mean SKINTEMP: 300.40 K
  - Perturbed mean SKINTEMP: 302.40 K
  - Difference: +2.0 K (+2°C)
- **Backup files**: 13 .bak files created and preserved
- **File integrity**: All files maintain original structure with only SKINTEMP modified

## Final Status
The experiment group met_em files are now ready for WRF simulation with +2°C SST perturbation. These files differ from the control group only in the SKINTEMP (SST) field, providing the required experimental setup for SST sensitivity analysis.