#!/bin/bash
# run_v4_arms.sh — PREREG_v4 §2.5 book-layer arms on the dev_v4 tree (RAW accounting). usage: run_v4_arms.sh <ARM: A0|A0p|A1|A1s|A1e|A2|A3> [seeds="42 2027"]
# monthly (2026-09-12, RUNBOOK_2026-10 §0★ 修订 2 (c); review R3 step 6): the dev tree and the king SLOW files are locators from the month env
# (V4_HC / V4_KING_DIR; defaults = the September constants), and every arm process is waited on BY PID with its rc collected — the old bare
# `wait; grep ... | tail -4` could read a previous run's END lines as this run's result. Non-zero rc of any arm ⇒ exit 1 (no silent success).
SELF_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)   # ★ J-01 (independent review 2026-09-18): resolve our own directory BEFORE cd — a relative `bash run_v4_arms.sh` from the device dir used to resolve run_arm.sh inside the tree after the cd
ARM=$1; SEEDS=${2:-"42 2027"}; H=${V4_HC:-/workspace/review_scratch/health_check}; KD=${V4_KING_DIR:-/workspace/review_scratch/king_v4}; cd $H || exit 2
# ★ FP3 item J (2026-09-17): the per-arm runner is the DEVICE-DIR run_arm.sh beside this wrapper (pinned by preflight as a device file), never a copy
#   found in the tree; it receives the tree (RUN_ARM_ROOT=$H) and the interpreter (RUN_ARM_PY = the driver's V4_PY) explicitly, and both are on its
#   CMD line in $H/logs/commands.txt. Absent beside the wrapper ⇒ ARMS_FAIL rc 3 before any arm is launched (no fallback to $H/run_arm.sh).
RA=$SELF_DIR/run_arm.sh; PYX=${V4_PY:-/workspace/venv/bin/python}
[ -f "$RA" ] || { echo "ARMS_FAIL missing device run_arm.sh beside this wrapper: $RA"; exit 3; }
_sha256() { (sha256sum "$1" 2>/dev/null || shasum -a 256 "$1") | cut -c1-64; }
echo "RUN_ARM=$RA sha256=$(_sha256 "$RA") RUN_ARM_ROOT=$H RUN_ARM_PY=$PYX"
# FP2-8 §2.2: V4_UMASK_NPZ overrides the evaluation umask for EVERY arm run by this call (A0 and A1 alike); the path lands in each arm's config_json via UMASK_NPZ.
# ★ F01 (independent review 2026-09-17, P1): the first version of this edit put the comment ON the assignment line and swallowed K3/K4/K4E, so SLOW_NPY
#   was EMPTY for every arm and w10_health.py fell back to slow_pred_hist_oos.npy — which build_dev_v4 links to the CANDIDATE king. A0 would have used
#   the new king. Assignments live on their own line now, SL is required non-empty AND an existing file, and tests_run_v4_arms.py drives this wrapper.
UP=${V4_UMASK_NPZ:-$H/masks/umask_UPIT_CRYPTO.npz}; CB=$H/calib/costb_fee_steady.json
K3=$KD/SLOW_v3_on_v4axis.npy; K4=$KD/SLOW_v4.npy; K4E=$KD/SLOW_v4e.npy
COMMON="LEGS=101 CAL=log WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=m1 UMASK_NPZ=$UP COSTB_JSON=$CB"
pids=(); names=()
for s in $SEEDS; do
  case $ARM in A0) SL=$K3; FP=f10_A0_s$s.npy ;; A1) SL=$K4; FP=f10_v4RAW_s$s.npy ;; A2) SL=$K4; FP=f10_v4CLIP_s$s.npy ;; A3) SL=$K4; FP=f10_A0_s$s.npy ;; A1s) SL=$K4; FP=f10_v4sRAW_s$s.npy ;; A1e) SL=$K4E; FP=f10_v4RAW_s$s.npy ;; *) echo "bad arm $ARM"; exit 2 ;; esac
  [ -n "$SL" ] && [ -f "$SL" ] || { echo "ARMS_FAIL missing SLOW_NPY for arm $ARM: '$SL'"; exit 3; }   # F01: empty/absent king score file is a hard refusal, never a silent fallback
  [ -f "$H/dev_v4/f8_2026-08-22/preds/$FP" ] || { echo "missing FPRED $FP"; exit 3; }
  [ -f $SL ] || { echo "missing SLOW $SL"; exit 3; }
  RUN_ARM_ROOT=$H RUN_ARM_PY=$PYX bash "$RA" V4_${ARM}_dyn_s$s v4 w10_health.py $COMMON SLOW_NPY=$SL FSEED=$s FPRED=$FP > $H/dev_v4/logs/V4_${ARM}_dyn_s$s.out 2>&1 & pids+=($!); names+=("dyn_s$s")
  RUN_ARM_ROOT=$H RUN_ARM_PY=$PYX bash "$RA" V4_${ARM}_fix_s$s v4 w10_health.py $COMMON SLOW_NPY=$SL FSEED=$s FPRED=$FP W3FIX=0.21,0,0.79 > $H/dev_v4/logs/V4_${ARM}_fix_s$s.out 2>&1 & pids+=($!); names+=("fix_s$s")
done
rcs=(); k=0; bad=0
for p in "${pids[@]}"; do wait $p; rc=$?; rcs+=($rc); [ $rc -eq 0 ] || bad=1; echo "arm V4_${ARM}_${names[$k]} pid $p rc=$rc"; k=$((k + 1)); done
echo "ARMS ${ARM} seeds [$SEEDS] rc=[${rcs[*]}]"
grep -a -E "^END\[V4_${ARM}_" $H/logs/commands.txt | tail -$(( ${#pids[@]} ))
[ $bad -eq 0 ] || { echo "ARMS_FAIL ${ARM} rc=[${rcs[*]}]"; exit 1; }
echo "ARMS_DONE ${ARM}"
