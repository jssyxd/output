import pandas as pd
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from cartopy.mpl.ticker import LongitudeFormatter, LatitudeFormatter

# Load trajectory data
df = pd.read_csv('typhoon_infa_trajectories.csv')

# Create figure with cartopy projection
fig = plt.figure(figsize=(12, 10))
ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())

# Set extent to focus on East China Sea region
ax.set_extent([120, 127, 23, 32], crs=ccrs.PlateCarree())

# Add coastlines and borders
ax.add_feature(cfeature.COASTLINE, linewidth=0.8)
ax.add_feature(cfeature.BORDERS, linewidth=0.5)
ax.add_feature(cfeature.LAND, facecolor='lightgray', alpha=0.3)
ax.add_feature(cfeature.OCEAN, facecolor='lightblue', alpha=0.3)

# Plot control trajectory (blue)
ax.plot(df['lon_control'], df['lat_control'], 'b-o', 
        markersize=4, linewidth=2, label='Control (-2°C SST)', 
        transform=ccrs.PlateCarree())

# Plot experiment trajectory (red)
ax.plot(df['lon_experiment'], df['lat_experiment'], 'r-s', 
        markersize=4, linewidth=2, label='Experiment (+2°C SST)', 
        transform=ccrs.PlateCarree())

# Add start and end markers
ax.plot(df['lon_control'].iloc[0], df['lat_control'].iloc[0], 'bo', 
        markersize=8, markerfacecolor='blue', transform=ccrs.PlateCarree())
ax.plot(df['lon_control'].iloc[-1], df['lat_control'].iloc[-1], 'bo', 
        markersize=8, markerfacecolor='darkblue', transform=ccrs.PlateCarree())

ax.plot(df['lon_experiment'].iloc[0], df['lat_experiment'].iloc[0], 'rs', 
        markersize=8, markerfacecolor='red', transform=ccrs.PlateCarree())
ax.plot(df['lon_experiment'].iloc[-1], df['lat_experiment'].iloc[-1], 'rs', 
        markersize=8, markerfacecolor='darkred', transform=ccrs.PlateCarree())

# Add gridlines
gl = ax.gridlines(draw_labels=True, linewidth=0.5, color='gray', alpha=0.5, linestyle='--')
gl.top_labels = False
gl.right_labels = False
gl.xlabel_style = {'size': 10}
gl.ylabel_style = {'size': 10}

# Labels and title
ax.set_title('Typhoon In-fa Trajectories: Control vs +2°C SST Experiment\n(July 23-26, 2021)', 
             fontsize=14, fontweight='bold')
ax.legend(loc='upper right', fontsize=12)

# Save the plot
plt.savefig('typhoon_infa_both_trajectories.png', dpi=300, bbox_inches='tight')
plt.close()

print("Enhanced trajectory plot saved as typhoon_infa_both_trajectories.png")