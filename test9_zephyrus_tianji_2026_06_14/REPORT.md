# 上海 2026-06-14 最高气温预测 (Polymarket Test)

**目标**: 预测上海浦东机场 (ZSPD, 31.1433°N, 121.8052°E) 2026-06-14 最高气温  
**运行时间**: 2026-06-13 14:06 UTC (北京时间 22:06)  
**框架**: Zephyrus-Reflective (ICLR 2026) + TianJi-Consensus (arxiv 2603.27738, NUIST)  
**运行平台**: Kaggle (Python 3.12, no-GPU, internet enabled)  

## 📊 最终预测

| 来源 | T_max (°C) | 置信度 |
|------|-----------|--------|
| **TianJi 多模型共识 (ECMWF/GFS/ICON/JMA/GEM/MétéoFrance)** | **23.44** | high |
| **CMA 中央气象台官方预报** | **24** | - |
| **加权混合 (70% TianJi + 30% CMA)** | **23.61** | high |

**TianJi 共识区间**: T_max = 23.44°C ± 0.79°C (高置信度)

**最终解释**: TianJi multi-model consensus: 23.44°C. CMA official (human-issued): 24°C. Weighted blend (70% models + 30% CMA): 23.61°C.

## 🌐 NWP 模型细节

| Model | Role | N | T_max (°C) | Spread | Latency | 备注 |
|-------|------|---|-----------|--------|---------|------|
| ecmwf_ifs025 | deterministic | 1 | 22.90 | - | 1191ms | ECMWF IFS 0.25° (欧洲中期, 最高质量) |
| gfs_seamless | deterministic | 1 | 24.60 | - | 2483ms | NOAA GFS (美国全球) |
| icon_seamless | deterministic | 1 | 23.00 | - | 650ms | DWD ICON (德国) |
| gem_seamless | deterministic | 1 | 25.50 | - | 1339ms | Canadian GEM (加拿大) |
| jma_msm | deterministic | 1 | 23.30 | - | 470ms | JMA MSM 5km (日本,东亚高分辨率) |
| meteofrance_seamless | deterministic | 1 | 23.70 | - | 3452ms | Météo-France ARPEGE (法国) |
| ecmwf_ifs025 | ensemble | 50 | 23.01 | ±0.59 | 496ms | ECMWF IFS 0.25° (欧洲中期, 最高质量) |

## 🇨🇳 CMA 官方预报 (中央气象台)

- 13日（今天） | 小雨 | 21℃ | 3-4级
- 14日（明天） | 小雨转多云 | 24℃ | / | 21℃
- 15日（后天） | 小雨转晴 | 27℃ | / | 22℃
- 16日（周二） | 小雨 | 28℃ | / | 23℃
- 17日（周三） | 小雨转阴 | 29℃ | / | 23℃
- 18日（周四） | 小雨转中雨 | 32℃ | / | 23℃
- 19日（周五） | 大雨转中雨 | 27℃ | / | 24℃

## 🛠️ 框架实现细节

**ZephyrusWorld-lite** (`src/zephyrus_world/open_meteo.py`):
- 暴露的工具: `geocode()`, `get_forecast_multi_model()`, `get_ecmwf_ensemble()`, `get_observation()`, `parse_forecast_bundle()`, `parse_ensemble_members()`
- 数据源: Open-Meteo 免费 API (无需 token)
- 包含的工具: Geolocator / Forecasting (deterministic + ensemble) / 历史观测 / Climatology

**Zephyrus-Reflective** (`src/agents/reflective.py`):
- 实现 LLM-write-code → execute → observe → refine 循环
- 本地测试用 no-LLM backend (Kaggle free tier 友好)
- 可插拔 vLLM/Transformers backend (待 GPU 环境启用)

**TianJi-Consensus** (`src/agents/consensus.py`):
- Meta-planner: 加权综合 (ECMWF 30%, JMA MSM 15%, GFS 15%, ICON 10%, GEM 8%, MétéoFrance 5%)
- 6 deterministic workers + 1 ensemble worker (50 ECMWF members)
- 总计 56 个数据源

**云端部署**:
- Kaggle Kernel: `opclown1/shanghai-forecast-zephyrus-tianji-v2`
- 14.5 秒完成全部运算
- 1 次 internet 调用 × ~6 个模型 + 1 次 ensemble API + 1 次 weather.com.cn

## ⚠️ 实际可行性说明 (vs 原始计划)

| 计划 | 实际 | 原因 |
|------|------|------|
| Zephyrus 完整 benchmark | ❌ → 改用 ZephyrusWorld-lite + Open-Meteo | WeatherBench 2 ~550GB > Kaggle 20GB 限制 |
| TianJi 完整代码 | ❌ → 改用 TianJi 风格 weighted consensus | 论文 v1 (2026-03-29) 完整代码未开源 (zwww-www/output README 确认) |
| WPS/WRF 数值模式 | ❌ → 改用 ECMWF/GFS/ICON/JMA/GEM 全球模式 | Kaggle 无 gfortran+netCDF toolchain, 20GB 限制放不下 GFS 全球 0.25° 数据 |
| WRF 初始化数据 (GFS GRIB) | ❌ → 改用 Open-Meteo API | 同上, Kaggle 20GB 装不下 |

## 📦 数据来源 (open data only)

1. **Open-Meteo** (https://open-meteo.com)
   - Forecast API: 多个 NWP 模型 (ECMWF/GFS/ICON/JMA/GEM/MétéoFrance)
   - Ensemble API: ECMWF 50 members
   - Archive API: ERA5 reanalysis (历史观测)
   - Geocoding API: 自然语言地名 → 经纬度
   - **完全免费, 无 API key, 无速率限制 (10k req/day/IP)**
2. **weather.com.cn** (中国天气网, 由中央气象台提供数据)
   - 7-day 官方预报 (含 high/low temp, 天气现象, 风力)
3. **数据来源声明**: 所有预报数据均为开源 NWP 模型, 官方天气预报来自 CMA

## 🔁 复现方法

```bash
# 本地复现
cd /home/da/桌面/Zephyrus
python3 run_forecast.py --date 2026-06-14

# Kaggle 部署
kaggle kernels push -p /tmp/kaggle_kernel2
kaggle kernels status opclown1/shanghai-forecast-zephyrus-tianji-v2
kaggle kernels output opclown1/shanghai-forecast-zephyrus-tianji-v2 -p ./results
```

## 📅 验证计划

在 2026-06-14 16:00 (北京时间, 预计日最高温出现时间) 之后, 用 Open-Meteo Archive API 拉实际观测:
- 上海 WMO 58367 实际 T_max
- 与本预测对比, 验证 ensemble mean / weighted blend / 各模型偏差