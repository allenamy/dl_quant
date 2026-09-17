#!/bin/bash
# run_arm.sh — one device run under a health_check tree (PREREG_live_form_health_check_2026-09-05 §3).
# usage: run_arm.sh <TAG> <log|prod|hf|ref|hf2|raw|refaug|v4> <DEVICE_FILE (relative to the tree)> <ENV assignments...>
#   caliber log  -> cwd dev/     (meta = /workspace/data/wide_fea_v2ext_meta.npz, raw Σ-simple y4, CAL=log = no transform)
#   caliber prod -> cwd dev_alt/ (meta y4 swapped for refute_C6_2/altrun/meta_newprod.npz = Π(1+r5)-1 over [E+1,E+48], CAL=log)
#   caliber v4   -> cwd dev_v4/  (the monthly chain's dev tree built by build_dev_v4.py; RAW accounting)
# Every command is appended verbatim to <tree>/logs/commands.txt; stdout/stderr -> <cwd>/logs/<TAG>.log; artifact -> <cwd>/probe_artifacts/w10_ablation_series_<TAG>.npz
# ★ FP3 item J (2026-09-17): this file lives in the CHAIN DEVICE DIR and is pinned by preflight as a device file; run_v4_arms.sh executes THIS copy
#   (resolved beside itself), never a copy found in the tree. The tree it runs in comes from RUN_ARM_ROOT (the wrapper passes V4_HC) and the
#   interpreter from RUN_ARM_PY (the wrapper passes the driver's V4_PY); both are recorded on the CMD line. Without RUN_ARM_ROOT the script falls
#   back to its own directory, which for the device-dir copy has no dev_*/ tree and is REFUSED (rc 3) — it never silently runs against another tree.
#   Predecessors: September tree copy 69e1e949 (ROOT hardcoded to review_scratch) → FP2 tree copy f30b2c7c (ROOT = its own directory) → this.
TAG=$1; CAL=$2; DEV=$3; shift 3
[ -n "$DEV" ] || { echo "usage: run_arm.sh <TAG> <log|prod|...|v4> <DEVICE_FILE> <ENV...>"; exit 2; }
SELF=$(cd "$(dirname "$0")" && pwd -P)/$(basename "$0")
ROOT=${RUN_ARM_ROOT:-$(cd "$(dirname "$0")" && pwd -P)}; PY=${RUN_ARM_PY:-/workspace/venv/bin/python}
case $CAL in log) d=$ROOT/dev ;; prod) d=$ROOT/dev_alt ;; hf) d=$ROOT/dev_hf ;; ref) d=$ROOT/dev_ref ;; hf2) d=$ROOT/dev_hf2 ;; raw) d=$ROOT/dev_raw ;; refaug) d=$ROOT/dev_refaug ;; v4) d=$ROOT/dev_v4 ;; *) echo "bad cal $CAL"; exit 2 ;; esac
[ -d "$d" ] || { echo "missing tree $d (RUN_ARM_ROOT=${RUN_ARM_ROOT:-unset}; this copy runs only inside a tree named explicitly)"; exit 3; }
[ -f "$ROOT/$DEV" ] || { echo "missing device $ROOT/$DEV"; exit 3; }
[ -x "$PY" ] || { echo "missing interpreter $PY (RUN_ARM_PY=${RUN_ARM_PY:-unset})"; exit 3; }
mkdir -p "$ROOT/logs" "$d/logs" || { echo "cannot create log dirs under $ROOT"; exit 3; }
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
CMD="env $* OUT_TAG=$TAG $PY ../$DEV"
echo "CMD[$TAG] (cwd=$d root=$ROOT run_arm=$SELF) $(date -u +%FT%TZ): $CMD" >> "$ROOT/logs/commands.txt"
cd "$d" && $CMD > "$d/logs/$TAG.log" 2>&1; rc=$?
echo "END[$TAG] rc=$rc $(date -u +%FT%TZ)" >> "$ROOT/logs/commands.txt"
grep -E "^(CONFIG|SLOW override|F10 OOS|MEMBERS_TOPN|UMASK|COSTB|CONFIG_HEALTH|RECEIPT_EX d30|DONE|Traceback|AssertionError|NOTE)" "$d/logs/$TAG.log" | cut -c1-700
exit $rc
