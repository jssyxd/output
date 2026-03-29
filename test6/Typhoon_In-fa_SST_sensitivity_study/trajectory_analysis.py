import pandas as pd
import numpy as np

# Load trajectory data
df = pd.read_csv('typhoon_infa_trajectories.csv')

# Calculate latitude differences (experiment - control)
df['lat_diff'] = df['lat_experiment'] - df['lat_control']
df['lon_diff'] = df['lon_experiment'] - df['lon_control']

# Calculate distance between tracks using haversine formula
def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate the great circle distance between two points on Earth"""
    R = 6371  # Earth radius in km
    
    lat1_rad = np.radians(lat1)
    lon1_rad = np.radians(lon1)
    lat2_rad = np.radians(lat2)
    lon2_rad = np.radians(lon2)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = np.sin(dlat/2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    
    return R * c

df['distance_km'] = haversine_distance(
    df['lat_control'], df['lon_control'], 
    df['lat_experiment'], df['lon_experiment']
)

# Focus on the critical period (July 24-26 when typhoon approaches coast)
critical_period = df[df['time'] >= '2021-07-24T00:00:00']

print("=== TRAJECTORY ANALYSIS RESULTS ===")
print(f"Total time steps: {len(df)}")
print(f"Critical period (Jul 24-26): {len(critical_period)} time steps")
print()

print("LATITUDE DIFFERENCES (Experiment - Control):")
print(f"Mean difference: {df['lat_diff'].mean():.4f}°")
print(f"Max positive difference: {df['lat_diff'].max():.4f}°")
print(f"Max negative difference: {df['lat_diff'].min():.4f}°")
print(f"Std deviation: {df['lat_diff'].std():.4f}°")
print()

print("CRITICAL PERIOD ANALYSIS (Jul 24-26):")
print(f"Mean latitude difference: {critical_period['lat_diff'].mean():.4f}°")
print(f"Max latitude difference: {critical_period['lat_diff'].max():.4f}°")
print(f"Min latitude difference: {critical_period['lat_diff'].min():.4f}°")
print()

print("DISTANCE BETWEEN TRACKS:")
print(f"Mean distance: {df['distance_km'].mean():.2f} km")
print(f"Max distance: {df['distance_km'].max():.2f} km")
print(f"Final distance (Jul 26 00:00): {df['distance_km'].iloc[-1]:.2f} km")
print()

print("SIGNIFICANT DEVIATIONS (>0.1° latitude):")
significant = df[abs(df['lat_diff']) > 0.1]
if len(significant) > 0:
    print(f"Found {len(significant)} time steps with significant deviation")
    print("Times with largest northward shifts:")
    northward = df[df['lat_diff'] > 0].nlargest(5, 'lat_diff')
    for idx, row in northward.iterrows():
        print(f"  {row['time']}: +{row['lat_diff']:.4f}° ({row['distance_km']:.1f} km)")
else:
    print("No significant deviations found")

# Save detailed analysis
df.to_csv('typhoon_infa_trajectories_detailed.csv', index=False)
print("\nDetailed analysis saved to typhoon_infa_trajectories_detailed.csv")