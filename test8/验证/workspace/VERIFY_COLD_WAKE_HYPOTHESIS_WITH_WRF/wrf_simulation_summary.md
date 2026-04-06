# WRF Simulation Summary Report

## Task Overview
This report documents the successful completion of WRF simulations for both control and perturbed experiments to verify the cold wake hypothesis for Typhoon Trami (2018).

## Execution Summary

### Control Experiment
- **Met_em files**: Successfully copied from `./workspace/VERIFY_COLD_WAKE_HYPOTHESIS_WITH_WRF/control/`
- **real.exe**: Completed successfully with 4 nodes, 64 cores
- **Initialization files generated**: 
  - `wrfinput_d01`, `wrfinput_d02`
  - `wrfbdy_d01`
- **wrf.exe**: Completed successfully with 8 nodes, 128 cores
- **Output files**: All `wrfout_d01_*` and `wrfout_d02_*` files generated for period 2018-09-27_00:00:00 to 2018-09-30_00:00:00
- **Output location**: `./workspace/VERIFY_COLD_WAKE_HYPOTHESIS_WITH_WRF/control_output/`

### Perturbed Experiment  
- **Met_em files**: Successfully copied from `./workspace/VERIFY_COLD_WAKE_HYPOTHESIS_WITH_WRF/perturbed/`
- **real.exe**: Completed successfully with 4 nodes, 64 cores
- **Initialization files generated**: 
  - `wrfinput_d01`, `wrfinput_d02`
  - `wrfbdy_d01`
- **wrf.exe**: Completed successfully with 8 nodes, 128 cores
- **Output files**: All `wrfout_d01_*` and `wrfout_d02_*` files generated for period 2018-09-27_00:00:00 to 2018-09-30_00:00:00
- **Output location**: `./workspace/VERIFY_COLD_WAKE_HYPOTHESIS_WITH_WRF/perturbed_output/`

## Namelist Configuration Issues Resolved

### Issue 1: SST Update Configuration
- **Problem**: Initial namelist had `sst_update = 1` but missing required parameters (`io_form_auxinput4`, `auxinput4_interval_s`)
- **Solution**: Added required parameters initially, then ultimately disabled SST updates by setting `sst_update = 0` to avoid dependency on external SST files

### Issue 2: Domain Dimension Mismatch
- **Problem**: Met_em files had different dimensions for domains 1 and 2 (d01: 201x201, d02: 202x202)
- **Solution**: Updated namelist.input `e_we` and `e_sn` parameters to `[201, 202]` to match actual met_em file dimensions

### Issue 3: Vertical Levels Mismatch
- **Problem**: Namelist specified `num_metgrid_levels = 34` but met_em files contained 32 levels
- **Solution**: Updated `num_metgrid_levels = 32` in namelist.input

## Final Configuration
The final working namelist.input configuration includes:
- `e_we = [201, 202]`
- `e_sn = [201, 202]`  
- `num_metgrid_levels = 32`
- `sst_update = 0`
- Proper time control settings for 3-day simulation (2018-09-27 to 2018-09-30)

## Output Files Verification
Both experiments successfully generated complete sets of output files:
- **Domain 1**: Hourly output from 2018-09-27_00:00:00 to 2018-09-30_00:00:00 (73 files)
- **Domain 2**: 1-hourly output from 2018-09-27_00:00:00 to 2018-09-30_00:00:00 (73 files)

All output files have been moved to their respective directories in the workspace as requested.

## Next Steps
The WRF simulations are now complete and ready for analysis to verify the cold wake hypothesis. The control and perturbed experiment outputs can be compared to assess the impact of the perturbation on typhoon intensity and structure.