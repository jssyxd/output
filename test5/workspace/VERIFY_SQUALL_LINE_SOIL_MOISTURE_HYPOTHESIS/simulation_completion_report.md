# WRF Simulation Completion Report

## Original Task
Run WRF simulations for both control and perturbed cases using 16 threads on the local machine for the Jianghuai squall line case on 2020-06-12.

## Execution Summary
Both control and perturbed WRF simulations have been successfully executed with the following specifications:
- **Domain**: 4km resolution, 201x201 grid points, 51 vertical levels
- **Physics**: WSM6 microphysics, Noah LSM, YSU boundary layer
- **Time period**: 2020-06-12 00:00 UTC to 2020-06-13 00:00 UTC (24 hours)
- **Output frequency**: Every 15 minutes (97 files per simulation)
- **Computational resources**: 16 MPI threads
- **Execution method**: Asynchronous background execution using launch_wrf_async tool

## Results
- Control simulation: 97 output files saved in `/home/zkk/Build_WRF/WRF/run/control_simulation/`
- Perturbed simulation: 97 output files saved in `/home/zkk/Build_WRF/WRF/run/perturbed_simulation/`
- Both simulations completed successfully with full 24-hour coverage
- All required input files were verified and properly configured

## Files Generated
- Detailed execution summary: `/home/zkk/Build_WRF/WRF/run/simulation_execution_summary.md`
- Organized output directories with complete simulation results