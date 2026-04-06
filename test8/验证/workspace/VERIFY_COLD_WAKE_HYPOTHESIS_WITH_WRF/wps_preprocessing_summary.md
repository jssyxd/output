# WPS Preprocessing Summary

## Overview
Successfully executed all three WPS preprocessing programs in sequence:
1. **geogrid.exe** - Generated static geographical data files
2. **ungrib.exe** - Decoded GRIB meteorological data into intermediate format
3. **metgrid.exe** - Interpolated meteorological data onto WRF model grids

## Files Generated

### Geogrid Output
- `geo_em.d01.nc` - Domain 1 static geographical data
- `geo_em.d02.nc` - Domain 2 static geographical data

### Ungrib Output  
- `FILE:2018-09-27_00` through `FILE:2018-09-30_00` (13 files total)
- Each file contains meteorological data for 6-hour intervals from 2018-09-27 00:00 to 2018-09-30 00:00 UTC

### Metgrid Output
- **Domain 1**: 13 files (`met_em.d01.2018-09-27_00:00:00.nc` through `met_em.d01.2018-09-30_00:00:00.nc`)
- **Domain 2**: 13 files (`met_em.d02.2018-09-27_00:00:00.nc` through `met_em.d02.2018-09-30_00:00:00.nc`)
- Total: 26 met_em files ready for WRF real.exe processing

## Configuration Details
- **Domain Setup**: 2 nested domains with parent_grid_ratio = 3
- **Domain 1**: 201×201 grid points, 18km resolution, Lambert conformal projection
- **Domain 2**: 202×202 grid points, 6km resolution (18km/3), nested within domain 1
- **Time Period**: 2018-09-27 00:00 to 2018-09-30 00:00 UTC (72 hours)
- **Meteorological Data**: FNL (GFS) 0.25° analysis data
- **Output Format**: NetCDF (io_form = 2)

## Status
✅ All preprocessing steps completed successfully
✅ All required output files generated in `/thfs1/home/mengf/Build_WRF/wps/`
✅ Ready for WRF real.exe and wrf.exe execution