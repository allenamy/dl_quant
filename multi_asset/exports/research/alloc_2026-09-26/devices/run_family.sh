#!/bin/bash
# run_family.sh — the EXECUTOR (TEAM_PROTOCOL §10-f) for DECISION_RULE_combination_layer_2026-09-26 §2, steps 0 -> 3 and the verdicts.
# Every judge it calls was committed before this driver was started. rev 1 (lead 17:5xZ): BTC beta is a process step before the verdicts. Line-start markers: "GATE_OK <step>", "STOP <reason>", "DONE".
# A step that fails prints STOP and exits non-zero; nothing after it runs. The session only reads and reports.
set -u
B=/workspace/alloc_2026-09-26; D=$B/devices; R=$B/receipts; PY=/workspace/venv/bin/python
E="env -i PATH=/usr/bin:/bin HOME=/root"
SEEDS="42 2027 7"
cd $D || { echo "STOP no devices dir"; exit 9; }
stop() { echo "STOP $1 $(date -u +%FT%TZ)"; exit 3; }
echo "START $(date -u +%FT%TZ) pgid=$(ps -o pgid= $$ | tr -d ' ')"

# ── step 0a: wait for the device-control driver (run_controls.sh, PGID 3285286) to END; Traceback = failure ──
until grep -qE '^END |Traceback' $B/logs/controls.log; do
  if ! ps -eo pgid= | tr -d ' ' | grep -qx 3285286; then grep -q '^END ' $B/logs/controls.log || stop "controls_driver_gone_without_END"; fi
  sleep 60
done
grep -q Traceback $B/logs/controls.log && stop "controls_traceback"
grep -q '^RC identity_s42=0' $B/logs/controls.log || stop "identity_s42_rc"
grep -q '^RC identity_s2027_combo=0' $B/logs/controls.log || stop "identity_s2027_rc"
grep -q '^RC red_s42=0' $B/logs/controls.log || stop "red_cell_rc"
# ── step 0b: identity receipts (combo s42 + s2027 bitwise, engine 32/32) and wiring of the red arm ──
$PY -B - <<'EOF' || stop "identity_receipts"
import json
R="/workspace/alloc_2026-09-26/receipts"
a=json.load(open(f"{R}/ALLOC_CHAIN_inservice_shared_s42.json")); b=json.load(open(f"{R}/ALLOC_CHAIN_inservice_shared_s2027.json"))
r=json.load(open(f"{R}/ALLOC_CHAIN_inservice_fundflip_s42.json"))
ok = a["COMBO_VS_ARCHIVE"]["ALL_IDENTICAL"] is True and a["ENGINE_IDENTITY"]["ALL_IDENTICAL"] is True and a["ENGINE_IDENTITY"]["n_paths_identical"]==32 \
     and b["COMBO_VS_ARCHIVE"]["ALL_IDENTICAL"] is True and r["COMBO_VS_ARCHIVE"]["ALL_IDENTICAL"] is False
print("IDENTITY combo_s42", a["COMBO_VS_ARCHIVE"]["ALL_IDENTICAL"], "engine_s42", a["ENGINE_IDENTITY"]["n_paths_identical"], "/32 combo_s2027",
      b["COMBO_VS_ARCHIVE"]["ALL_IDENTICAL"], "red_wired", not r["COMBO_VS_ARCHIVE"]["ALL_IDENTICAL"])
raise SystemExit(0 if ok else 1)
EOF
echo "GATE_OK identity_and_wiring"
$E $PY -B alloc_judge.py PATH,HOME,LC_CTYPE --mode IDENTITY --arm inservice_shared --seeds 42 --out $R/JUDGE_IDENTITY.json > $B/logs/judge_identity.log 2>&1 || stop "judge_identity_rc"
grep -q 'VERDICT=PASS' $B/logs/judge_identity.log || stop "judge_zero_point"
echo "GATE_OK judge_zero_point"
# ── step 0c: causality probe, every rule (oracle = positive control) ──
$E $PY -B alloc_causality.py $R/ALLOC_CAUSALITY.json > $B/logs/causality.log 2>&1 || stop "causality_rc"
grep -q '^ALLOC_CAUSALITY VERDICT=PASS' $B/logs/causality.log || stop "causality_verdict"
echo "GATE_OK causality"
# ── step 0d: red control R ──
$E $PY -B alloc_judge.py PATH,HOME,LC_CTYPE --mode R --arm inservice_fundflip --seeds 42 --out $R/JUDGE_R.json > $B/logs/judge_R.log 2>&1 || stop "judge_R_rc"
grep -q 'VERDICT=PASS' $B/logs/judge_R.log || stop "RED_CONTROL_FAILED_family_stops"
echo "GATE_OK red_control"
# ── step 1: ceiling control O (s42) ──
$E $PY -B alloc_chain_run.py PATH,HOME,LC_CTYPE $R --seed 42 --rule oracle --mix shared --engine > $B/logs/cell_oracle_s42.log 2>&1 || stop "oracle_cell_rc"
$E $PY -B alloc_judge.py PATH,HOME,LC_CTYPE --mode O --arm oracle_shared --seeds 42 --out $R/JUDGE_O.json > $B/logs/judge_O.log 2>&1 || stop "judge_O_rc"
if grep -q 'VERDICT=RUN_A1_A2_A3_A4' $B/logs/judge_O.log; then ARMS="cap050_shared look1800_shared inservice_orth invvol_shared"
elif grep -q 'VERDICT=RUN_A3_A4_ONLY' $B/logs/judge_O.log; then ARMS="inservice_orth invvol_shared"
else stop "judge_O_verdict_missing"; fi
echo "GATE_OK oracle arms=[$ARMS]"
# ── step 2: zero-return footprint (combo only, three seeds in parallel per arm) ──
for arm in $ARMS; do
  rule=${arm%_*}; mix=${arm##*_}; pids=""
  for s in $SEEDS; do
    $E $PY -B alloc_chain_run.py PATH,HOME,LC_CTYPE $R/footprint --seed $s --rule $rule --mix $mix > $B/logs/fp_${arm}_s$s.log 2>&1 & pids="$pids $!"
  done
  for p in $pids; do wait $p || stop "footprint_cell_rc_$arm"; done
done
$E $PY -B alloc_footprint.py $R/FOOTPRINT.json $ARMS > $B/logs/footprint.log 2>&1 || stop "footprint_rc"
grep -q '^ALLOC_FOOTPRINT DONE' $B/logs/footprint.log || stop "footprint_done_missing"
ENG_ARMS=""
for arm in $ARMS; do
  v=$(grep "^FOOTPRINT_VERDICT $arm " $B/logs/footprint.log | sed 's/.*gross_gate=\([A-Z_]*\).*/\1/')
  case "$v" in
    DEPLOYABLE) ENG_ARMS="$ENG_ARMS $arm";;
    NOT_DEPLOYABLE) echo "NOTE $arm NOT_DEPLOYABLE by the gross-gate rule: described at the footprint only, no engine cells";;
    *) stop "footprint_escalate_$arm:$v";;
  esac
done
echo "GATE_OK footprint engine_arms=[$ENG_ARMS]"
# ── step 3: engine cells, one at a time (alloc_chain_run's gate: <= 1 foreign bt_launch group) ──
for arm in $ENG_ARMS; do
  rule=${arm%_*}; mix=${arm##*_}
  for s in $SEEDS; do
    $E $PY -B alloc_chain_run.py PATH,HOME,LC_CTYPE $R --seed $s --rule $rule --mix $mix --engine > $B/logs/cell_${arm}_s$s.log 2>&1 || stop "engine_cell_rc_${arm}_s$s"
    echo "CELL_OK ${arm} s$s $(date -u +%FT%TZ)"
  done
done
# ── BTC daily beta (rule §5 required report; lead 2026-09-26: a process step BEFORE the verdicts, failure = STOP) ──
for arm in $ENG_ARMS; do
  $E $PY -B alloc_beta.py PATH,HOME,LC_CTYPE $arm 42,2027,7 $R/BETA_$arm.json > $B/logs/beta_$arm.log 2>&1 || stop "beta_rc_$arm"
  grep -q '^ALLOC_BETA DONE' $B/logs/beta_$arm.log || stop "beta_done_missing_$arm"
done
echo "GATE_OK btc_beta"
# ── verdicts (rule §3) ──
for arm in $ENG_ARMS; do
  case $arm in cap050_shared) c=A1;; look1800_shared) c=A2;; inservice_orth) c=A3;; invvol_shared) c=A4;; esac
  extra=""
  if [ "$c" = A3 ]; then
    mc=$($PY -c "import json;print(json.load(open('$R/FOOTPRINT.json'))['arms']['inservice_orth']['mechanism_corr_2026_median_mean_over_seeds'])")
    extra="--noninf-mech-corr $mc"
  fi
  $E $PY -B alloc_judge.py PATH,HOME,LC_CTYPE --mode FAMILY --arm $arm --seeds 42,2027,7 --arm-class $c $extra --out $R/JUDGE_FAMILY_$arm.json > $B/logs/judge_$arm.log 2>&1 || stop "judge_family_rc_$arm"
  echo "VERDICT_OK $arm $(tail -1 $B/logs/judge_$arm.log)"
done
echo "DONE $(date -u +%FT%TZ)"
