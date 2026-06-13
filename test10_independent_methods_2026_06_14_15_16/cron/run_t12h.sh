#!/usr/bin/env bash
#
# Zephyrus T+12h re-run cron job.
# This script:
#   1. Waits until target time (idempotent)
#   2. Runs the T+12h re-run (different methods, no weighted blend)
#   3. Compares with T0 (results_v2/T0)
#   4. Fetches actual ERA5 observation for 6/14 (available by then)
#   5. Commits results to git, pushes to jssyxd/output fork
#   6. Adds a comment to PR #1 with T+12h findings
#
# Schedule (cron):
#   53 4 14 6 *  -> 2026-06-14 04:53 UTC = 12:53 CST
#   (This is T+12h from 2026-06-13 16:53 UTC system time)
#
# Idempotency: if results_v2/T1_*/DONE exists, exits early.

set -euo pipefail
source "$(dirname "$0")/env.sh"

# ----- Config -----
TARGET_DATE="2026-06-14"   # 第一个 verification target
DATES=("2026-06-14" "2026-06-15" "2026-06-16")
RUN_TAG="T1"
COMPARE_WITH="results_v2/T0"
T0_SENTINEL="${ZEPHYRUS_RESULTS}/T0/.done"
T1_SENTINEL="${ZEPHYRUS_RESULTS}/${RUN_TAG}/.done"

LOG_FILE="${ZEPHYRUS_LOGS}/t12h_$(date -u '+%Y%m%dT%H%M%SZ').log"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "=================================================="
echo "Zephyrus T+12h cron job started: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "Target dates: ${DATES[*]}"
echo "Run tag: ${RUN_TAG}"
echo "Log: $LOG_FILE"
echo "=================================================="

# ----- Guard 1: Was T0 done? -----
if [[ ! -f "$T0_SENTINEL" ]]; then
    echo "ERROR: T0 sentinel not found at $T0_SENTINEL"
    echo "  Make sure you've run T0 first: python3 run_forecast_v2.py --dates ${DATES[*]} --run-tag T0"
    exit 1
fi
echo "OK: T0 sentinel found"

# ----- Guard 2: Already done? -----
if [[ -f "$T1_SENTINEL" ]]; then
    echo "OK: T1 already completed (sentinel exists). Exiting."
    exit 0
fi

# ----- Guard 3: Is it time? -----
# We want to run at 2026-06-14 04:53 UTC. If too early, wait.
TARGET_EPOCH=$(date -u -d "2026-06-14 04:53:00" '+%s' 2>/dev/null || echo "0")
NOW_EPOCH=$(date -u '+%s')
if [[ "$NOW_EPOCH" -lt "$TARGET_EPOCH" ]]; then
    WAIT_SECONDS=$((TARGET_EPOCH - NOW_EPOCH))
    echo "Too early. Sleeping $WAIT_SECONDS seconds until 2026-06-14 04:53 UTC..."
    # Don't sleep in cron context - just exit and let cron re-trigger
    # Actually, we want this to be a one-shot, so sleep is OK
    sleep "$WAIT_SECONDS" || true
fi
echo "Run time reached: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"

# ----- Step 1: Run the T+12h forecast -----
cd "$ZEPHYRUS_HOME"
echo "Step 1: Running T+12h forecast..."
python3 run_forecast_v2_later.py \
    --dates "${DATES[@]}" \
    --run-tag "$RUN_TAG" \
    --compare-with "$COMPARE_WITH" \
    --n-bias-days 10
echo "  Forecast complete. Output: ${ZEPHYRUS_RESULTS}/${RUN_TAG}/"

# ----- Step 2: Generate a comparison summary -----
echo ""
echo "Step 2: Generating T+12h summary..."
SUMMARY_PATH="${ZEPHYRUS_RESULTS}/${RUN_TAG}/summary.md"
python3 << PYEOF
import json
from pathlib import Path
res_dir = Path("${ZEPHYRUS_RESULTS}/${RUN_TAG}")
dates = "${DATES[*]}".split()
# Read summary.json
summary = json.load(open(res_dir / "summary_${RUN_TAG}.json"))
actual = summary.get("actual_observations", {})

# Read comparison CSV
import csv
methods = {}
with open(res_dir / f"comparison_${RUN_TAG}.csv") as f:
    for row in csv.DictReader(f):
        methods[row["method"]] = row

# Build error table for 6/14 if actual available
err_table = []
if "2026-06-14" in actual:
    actual_614 = actual["2026-06-14"]
    for m, row in methods.items():
        v = row.get("2026-06-14")
        if v:
            try:
                err = float(v) - actual_614
                err_table.append((m, float(v), err))
            except ValueError:
                pass
    err_table.sort(key=lambda x: abs(x[2]))

# Write markdown summary
md = []
md.append(f"# T+12h Re-run Summary")
md.append("")
md.append(f"**Run tag**: {summary['meta']['run_tag']}")
md.append(f"**Run time (UTC)**: {summary['meta'].get('elapsed_s')}s total")
md.append("")
md.append("## Actual Observations (ERA5)")
md.append("")
if actual:
    md.append("| Date | T_max (°C) |")
    md.append("|------|-----------|")
    for d, t in sorted(actual.items()):
        md.append(f"| {d} | {t} |")
else:
    md.append("*(No actual observations yet - target dates still in future)*")
md.append("")

if err_table:
    md.append("## Method Error Table (6/14 T_max)")
    md.append("")
    md.append(f"**Actual**: {actual_614}°C")
    md.append("")
    md.append("| Method | Predicted (°C) | Error (°C) |")
    md.append("|--------|----------------|------------|")
    for m, v, e in err_table:
        md.append(f"| {m} | {v:.2f} | {e:+.2f} |")
    md.append("")

# Forecast evolution (if compare_with worked)
evo_path = res_dir / f"evolution_${RUN_TAG}_vs_T0.json"
if evo_path.exists():
    evo = json.load(open(evo_path))
    md.append("## Forecast Evolution (T0 → T+12h)")
    md.append("")
    for date in dates:
        if date not in evo:
            continue
        md.append(f"### {date}")
        md.append("")
        md.append("| Method | T0 | T+12h | Δ |")
        md.append("|--------|----|----|---|")
        for m, vals in sorted(evo[date].items(), key=lambda x: (x[1].get("delta") or 0)):
            t0 = vals.get("T0")
            t1 = vals.get("T1")
            d = vals.get("delta")
            if t0 is None and t1 is None:
                continue
            t0s = f"{t0:.2f}" if t0 is not None else "n/a"
            t1s = f"{t1:.2f}" if t1 is not None else "n/a"
            ds = f"{d:+.2f}" if d is not None else "n/a"
            md.append(f"| {m} | {t0s} | {t1s} | {ds} |")
        md.append("")

out_path = Path("$SUMMARY_PATH")
out_path.write_text("\n".join(md), encoding="utf-8")
print(f"Summary written: {out_path}")
PYEOF

# ----- Step 3: Create sentinel -----
touch "$T1_SENTINEL"
echo "Sentinel created: $T1_SENTINEL"

# ----- Step 4: Git commit + push -----
echo ""
echo "Step 3: Git commit + push to fork..."
cd "$ZEPHYRUS_HOME"
# Add all new files in results_v2/T1/
git add "results_v2/${RUN_TAG}/" 2>/dev/null || true
# Use a separate clone to avoid touching the main repo
TMPDIR=$(mktemp -d)
git clone "https://x-access-token:${GITHUB_TOKEN}@github.com/jssyxd/output.git" "$TMPDIR/jssyxd-output" 2>&1 | tail -3
# Copy results into the cloned repo
mkdir -p "$TMPDIR/jssyxd-output/test10_independent_methods_2026_06_14_15_16/T1_results"
cp -r "${ZEPHYRUS_RESULTS}/${RUN_TAG}/." "$TMPDIR/jssyxd-output/test10_independent_methods_2026_06_14_15_16/T1_results/" 2>&1 || true

cd "$TMPDIR/jssyxd-output"
git config user.email "$GIT_AUTHOR_EMAIL"
git config user.name "$GIT_AUTHOR_NAME"
git add "test10_independent_methods_2026_06_14_15_16/T1_results/"
git commit -m "Add T+12h re-run results (2026-06-14 04:53 UTC)" 2>&1 | tail -3
git push origin main 2>&1 | tail -3
rm -rf "$TMPDIR"

# ----- Step 5: Add PR comment -----
echo ""
echo "Step 4: Add PR comment with T+12h results..."
ACTUAL_614=$(python3 -c "
import json
d = json.load(open('${ZEPHYRUS_RESULTS}/${RUN_TAG}/summary_${RUN_TAG}.json'))
print(d.get('actual_observations', {}).get('2026-06-14', 'N/A'))
" 2>/dev/null || echo "N/A")

# Build a short error table
ERRORS=$(python3 -c "
import json, csv
from pathlib import Path
res_dir = Path('${ZEPHYRUS_RESULTS}/${RUN_TAG}')
summary = json.load(open(res_dir / 'summary_${RUN_TAG}.json'))
actual = summary.get('actual_observations', {}).get('2026-06-14')
if actual is None:
    print('No actual obs yet.')
else:
    methods = []
    with open(res_dir / f'comparison_${RUN_TAG}.csv') as f:
        for row in csv.DictReader(f):
            v = row.get('2026-06-14')
            if v:
                try:
                    err = float(v) - actual
                    methods.append((row['method'], float(v), err))
                except ValueError:
                    pass
    methods.sort(key=lambda x: abs(x[2]))
    out = '| Method | Predicted | Error |\\n|--------|-----------|-------|\\n'
    for m, v, e in methods[:10]:
        out += f'| {m} | {v:.2f} | {e:+.2f} |\\n'
    print(out)
" 2>/dev/null || echo "Error table generation failed")

cat > /tmp/pr_comment.json <<EOF
{
  "body": "## T+12h Re-run Completed (2026-06-14 04:53 UTC = 12:53 CST)\n\n**Actual observation for 6/14**: ${ACTUAL_614}°C\n\n### Top-10 Method Error Table (sorted by |error|)\n\n${ERRORS}\n\n### Forecast Evolution (T0 → T+12h)\n\nSee test10.../T1_results/ for full details.\n\nAuto-generated by Zephyrus cron job at $(date -u '+%Y-%m-%d %H:%M:%S UTC')."
}
EOF

curl -sX POST "https://api.github.com/repos/zwww-www/output/issues/1/comments" \
    -H "Authorization: token ${GITHUB_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    --data @/tmp/pr_comment.json | python3 -c "
import json, sys
d = json.load(sys.stdin)
if 'id' in d:
    print(f'PR comment added: {d[\"html_url\"]}')
else:
    print(f'PR comment error: {d.get(\"message\")}')
"

echo ""
echo "=================================================="
echo "Zephyrus T+12h cron job complete: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "=================================================="
