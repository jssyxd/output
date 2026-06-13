# Zephyrus T+12h Cron Job

## 📅 Schedule

| When | Time | UTC | CST (Beijing) |
|---|---|---|---|
| **T0** (now) | 2026-06-13 16:53 UTC | system time when T0 was run | 00:53 CST (6/14) |
| **T+12h** | 2026-06-14 04:53 UTC | 12h later | 12:53 CST (6/14) |

**Cron entry**:
```
53 12 14 6 * /home/da/桌面/Zephyrus/cron/run_t12h.sh >> /home/da/桌面/Zephyrus/logs/cron.log 2>&1
```

(Cron uses **local time** on Ubuntu. `12:53 CST on June 14` = 04:53 UTC on June 14.)

## 🔧 What the script does

1. **Guard checks** (in order):
   - T0 sentinel exists at `results_v2/T0/.done`? → If not, exit 1
   - T1 sentinel already exists at `results_v2/T1/.done`? → If yes, exit 0 (idempotent)
   - Is current time ≥ 2026-06-14 04:53 UTC? → If not, sleep until then

2. **Run T+12h forecast**:
   - `python3 run_forecast_v2_later.py --dates 2026-06-14 2026-06-15 2026-06-16 --run-tag T1 --compare-with results_v2/T0`
   - Fetches 06Z NWP data (fresher than T0's 12Z data)
   - Fetches ERA5 actual for 6/14 (now available)
   - Generates per-method error table for 6/14

3. **Generate summary**:
   - `summary.md` with method ranking, evolution table, errors

4. **Git commit + push**:
   - Clone `jssyxd/output` (your fork)
   - Copy T1 results to `test10.../T1_results/`
   - Commit + push

5. **Add PR comment**:
   - POST to PR #1 with top-10 error table + summary link

6. **Create sentinel**: `results_v2/T1/.done` (prevents re-runs)

## 🔐 Security

- Tokens are in `cron/env.sh` (chmod 600)
- NOT in crontab (visible to all users)
- NOT in git (we'll add `cron/env.sh` to `.gitignore`)

## 🛠️ Installation

The crontab is already installed. To verify:
```bash
crontab -l
```

To re-install (if you modify the crontab):
```bash
crontab /home/da/桌面/Zephyrus/cron/zephyrus_crontab
```

To uninstall:
```bash
crontab -r   # WARNING: removes ALL your crontabs
# OR
crontab -l | grep -v zephyrus | crontab -
```

## 🧪 Manual test run

To test the script without waiting 12h:
```bash
# Skip the time check (run NOW):
cd /home/da/桌面/Zephyrus
SKIP_TIME_CHECK=1 bash cron/run_t12h.sh
```

Or modify `run_t12h.sh` to remove the `sleep` line.

## 📂 Files

```
cron/
├── env.sh                  # Tokens + paths (sourced by run_t12h.sh)
├── run_t12h.sh             # Main cron job script
├── zephyrus_crontab        # Crontab file (installed via `crontab`)
├── install_crontab.sh      # Helper to install crontab
└── README.md               # This file
```

## 📋 Verification checklist

After the cron job runs (around 6/14 12:53 CST):

- [ ] `results_v2/T1/` directory exists with `.done` sentinel
- [ ] `results_v2/T1/summary.md` exists with error table
- [ ] `results_v2/T1/evolution_T1_vs_T0.json` exists with forecast evolution
- [ ] GitHub fork `jssyxd/output` has `test10.../T1_results/` with new files
- [ ] PR #1 has a new comment with top-10 error table
- [ ] `logs/cron.log` shows successful execution

## ⏱️ Backup plan

If cron doesn't fire (e.g., machine was asleep):

```bash
# Check cron logs
grep -i zephyrus /var/log/syslog
tail -50 /home/da/桌面/Zephyrus/logs/cron.log

# Manually trigger
bash /home/da/桌面/Zephyrus/cron/run_t12h.sh
```

If you want to **disable** the cron job:
```bash
crontab -l | grep -v zephyrus | crontab -
# Or comment out the line in cron/zephyrus_crontab and re-install
```
