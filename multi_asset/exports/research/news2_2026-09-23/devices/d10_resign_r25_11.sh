#!/usr/bin/env bash
# d10_resign_r25_11.sh -- re-sign today's archive-backed conclusions under the FIXED gate (R25-11).
#
# lead: "改为: checksum_match 必须为 True、集合相等、逐个 ZIP 重新哈希。今天已出的审计结论(305/305 等)
#        用修好的门重签一次。"
#
# Order is deliberate:
#   0. the gate proves it can detect, on a synthetic fixture (local + pod2) -- an undetectable gate
#      re-signs nothing. Baseline green first, then each mutation must be caught.
#   1. only then re-verify the real months, 2026-08 first (it carries the 305/305 conclusion).
#   2. only then re-run the consumer that produced 305/305, whose receipt now records gate_sha256.
#
# Read-only against the venue: no fapi call, no download. Hashing only. Safe outside the quiet window,
# but NOT inside the executor release blackout (13:00-15:40Z) because it drives pod2 over ssh.
set -u
REPO=/Users/haosiyu/Desktop/quant_research
DEV=$REPO/multi_asset/exports/research/news2_2026-09-23/devices
EXP=/dev/shm/d10_2026-09-25
PY=/workspace/venv/bin/python
SCR=${SCR:-/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/scratchpad/d10}
LOG=$SCR/resign_r25_11.log
mkdir -p "$SCR"
say() { echo "$(date -u +%H:%M:%SZ) $*" | tee -a "$LOG"; }

say "=== R25-11 re-sign start ==="

# ---- step 0a: the gate detects, locally -----------------------------------------------------------
say "step 0a: local synthetic self-test"
python3 -B "$DEV/d10_manifest_gate.py" --selftest-synthetic 2>&1 | tee -a "$LOG"
grep -q "SELFTEST GREEN" "$LOG" || { say "LOCAL SELFTEST NOT GREEN -> stopping, nothing is re-signed"; exit 1; }

# ---- step 0b: same gate, same result, in the interpreter that will judge the real months ----------
say "step 0b: ship the gate to pod2 and run the same self-test there"
scp -q "$DEV/d10_manifest_gate.py" "$DEV/d10_month_state.py" "$DEV/d10_drop_mismatched.py" \
       "$DEV/d10_live_ledger_vs_archive.py" "$DEV/d10_year_event_table.py" \
       "$DEV/d10_fxfield_adjudicate.py" "$DEV/d10_nc_fundnow_vs_archive.py" pod2:$EXP/devices/ \
  || { say "scp FAILED -> stopping"; exit 1; }
say "gate sha here : $(shasum -a 256 "$DEV/d10_manifest_gate.py" | cut -c1-16)"
say "gate sha there: $(ssh pod2 "sha256sum $EXP/devices/d10_manifest_gate.py" | cut -c1-16)"
ssh pod2 "$PY -B $EXP/devices/d10_manifest_gate.py --selftest-synthetic" 2>&1 | tee -a "$LOG"

# ---- step 1: which months exist, and what does the fixed gate say about each ----------------------
say "step 1: fixed-gate verdict for every month on pod2"
ssh pod2 "ls -d $EXP/zips/*-* 2>/dev/null | xargs -n1 basename" > "$SCR/months_present.txt" 2>/dev/null
say "months present: $(tr '\n' ' ' < "$SCR/months_present.txt")"
MONTHS=$(tr '\n' ' ' < "$SCR/months_present.txt")
[ -n "${MONTHS// /}" ] || { say "no months on pod2 -> nothing to re-sign"; exit 1; }
for M in $MONTHS; do
  say "  $M: $(ssh pod2 "$PY -B $EXP/devices/d10_manifest_gate.py $EXP/zips/$M $M" 2>&1 | head -2 | tr '\n' ' ')"
done

say "=== R25-11 re-sign: gate verdicts recorded; consumer re-runs follow in the next step ==="
