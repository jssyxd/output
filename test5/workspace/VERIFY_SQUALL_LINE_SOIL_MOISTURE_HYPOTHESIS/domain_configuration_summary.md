# Jianghuai Region Squall Line Domain Configuration (2020-06-12)

## Domain Specifications
- **Region**: Jianghuai region (28-35°N, 115-122°E)
- **Simulation Period**: 2020-06-12 00:00 UTC to 2020-06-13 00:00 UTC (24 hours)
- **Domain Type**: Single domain (d01)
- **Grid Resolution**: 4 km × 4 km

## Grid Parameters
- **Grid Points**: 201 × 201 (e_we × e_sn)
- **Total Domain Size**: ~800 km × ~800 km
- **Center Latitude**: 31.5°N
- **Center Longitude**: 118.5°E

## Projection Details
- **Projection Type**: Lambert Conformal
- **True Latitude 1**: 30°N
- **True Latitude 2**: 33°N
- **Standard Longitude**: 118.5°E

## WPS Configuration Summary
- **max_dom**: 1
- **start_date**: '2020-06-12_00:00:00'
- **end_date**: '2020-06-13_00:00:00'
- **interval_seconds**: 21600 (6 hours)
- **dx/dy**: 4000 meters
- **map_proj**: 'lambert'

## Output Files Generated
- **geo_em.d01.nc**: Successfully generated in /home/zkk/Build_WRF/WPS/
- **geogrid.log**: Contains successful completion message

## Notes
This configuration is optimized for squall line simulation with 4 km resolution, which is appropriate for resolving convective-scale features while maintaining computational efficiency for the Jianghuai region case study on June 12, 2020.