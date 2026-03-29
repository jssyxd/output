import matplotlib.pyplot as plt
import numpy as np

# Typhoon intensity data (minimum central pressure every 6 hours)
times = ['09/14 00Z', '09/14 06Z', '09/14 12Z', '09/14 18Z', 
         '09/15 00Z', '09/15 06Z', '09/15 12Z', '09/15 18Z', '09/16 00Z']
slp_values = [922.7690, 929.7853, 928.2644, 924.5787, 
              940.0131, 940.7062, 938.9000, 939.2540, 940.3863]

# Create the plot
plt.figure(figsize=(12, 8))
plt.plot(range(len(times)), slp_values, 'b-o', linewidth=2, markersize=6)

# Find and mark the minimum pressure point (strongest typhoon)
min_slp = min(slp_values)
min_index = slp_values.index(min_slp)
plt.plot(min_index, min_slp, 'ro', markersize=10)

# Add annotation for the minimum pressure
plt.annotate(f'Minimum Pressure: {min_slp:.1f} hPa\n({times[min_index]})', 
             xy=(min_index, min_slp), 
             xytext=(min_index+0.5, min_slp+5),
             arrowprops=dict(arrowstyle='->', color='red', lw=1.5),
             fontsize=12, color='red', fontweight='bold')

# Set plot properties
plt.xlabel('Time', fontsize=12)
plt.ylabel('Minimum Central Pressure (hPa)', fontsize=12)
plt.title('Typhoon Intensity Evolution - Minimum Central Pressure', fontsize=14, fontweight='bold')
plt.xticks(range(len(times)), times, rotation=45)
plt.grid(True, alpha=0.3)
plt.ylim(920, 945)

# Adjust layout and save
plt.tight_layout()
plt.savefig('typhoon_intensity_evolution.png', dpi=300, bbox_inches='tight')
print('Chart saved as typhoon_intensity_evolution.png')
print(f'Strongest typhoon time: {times[min_index]}')
print(f'Minimum central pressure: {min_slp:.4f} hPa')