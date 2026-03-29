import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# 台风强度数据（每隔6小时的中心最低气压）
times = ['09/14 00Z', '09/14 06Z', '09/14 12Z', '09/14 18Z', 
         '09/15 00Z', '09/15 06Z', '09/15 12Z', '09/15 18Z', '09/16 00Z']
slp_values = [922.7690, 929.7853, 928.2644, 924.5787, 
              940.0131, 940.7062, 938.9000, 939.2540, 940.3863]

# 转换为数值时间（用于绘图）
time_indices = np.arange(len(times))

# 创建图表
plt.figure(figsize=(12, 8))
plt.plot(time_indices, slp_values, 'b-o', linewidth=2, markersize=6)

# 标注最低气压点（台风最强时刻）
min_slp = min(slp_values)
min_index = slp_values.index(min_slp)
plt.plot(min_index, min_slp, 'ro', markersize=10, label=f'最低气压: {min_slp:.1f} hPa\n({times[min_index]})')

# 添加标注文本
plt.annotate(f'最低气压: {min_slp:.1f} hPa\n{times[min_index]}', 
             xy=(min_index, min_slp), 
             xytext=(min_index+0.5, min_slp+5),
             arrowprops=dict(arrowstyle='->', color='red', lw=1.5),
             fontsize=12, color='red', fontweight='bold')

# 设置图表属性
plt.xlabel('时间', fontsize=12)
plt.ylabel('中心最低气压 (hPa)', fontsize=12)
plt.title('台风生命史强度变化 - 中心最低气压演变', fontsize=14, fontweight='bold')
plt.xticks(time_indices, times, rotation=45)
plt.grid(True, alpha=0.3)
plt.legend()

# 调整布局
plt.tight_layout()

# 保存图表
plt.savefig('./workspace/analyze_typhoon_intensity/typhoon_intensity_evolution.png', dpi=300, bbox_inches='tight')
print('图表已保存为 typhoon_intensity_evolution.png')
print(f'台风最强时刻: {times[min_index]}')
print(f'最低中心气压: {min_slp:.4f} hPa')