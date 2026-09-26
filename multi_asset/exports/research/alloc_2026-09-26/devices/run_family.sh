#!/bin/bash
# run_family.sh — the EXECUTOR (TEAM_PROTOCOL §10-f) for DECISION_RULE_combination_layer_2026-09-26 §2, steps 0 -> 3 and the verdicts.
# Every judge it calls was committed before this driver was started. Line-start markers: "GATE_OK <step>", "STOP <reason>", "DONE".
# A step that fails prints STOP and exits non-zero; nothing after it runs. The session only reads and reports.
# rev 1 (lead 17:5xZ): BTC beta is a process step before the verdicts.
# rev 2 (17:59Z, /workspace quota full killed the red cell and NO STOP line could be written -- the log lived on the full volume):
#   * the executor log and every step log live on tmpfs /dev/shm/alloc_2026-09-26/logs (not under the /workspace quota); each marker is
#     READ BACK after writing, and a mirror copy goes to /workspace/alloc_2026-09-26/logs/family.log (best effort, never trusted);
#   * SPACE GATE before every cell: write + fsync + read back a 400 MiB probe under /workspace/alloc_2026-09-26 (a cell writes ~355 MiB),
#     then delete it; failure = STOP (not a wait);
#   * GO FILE: the executor waits for /dev/shm/alloc_2026-09-26/GO (created by alloc only after the lead confirms space was released);
#   * the red cell is run by THIS executor (the rev 0 control driver died with the quota); step 0a re-checks the two identity receipts.
# rev 3 (rule §7, 22:4xZ): R (fundflip) failed on a wrong expectation; restart with R' = whole combo target negated (mix negbook), judged by
#   alloc_judge --mode RPRIME. Fresh marker log family_rev3.log (the old log ends in the rev 2a STOP, which a regex would re-match);
#   PGID written to $S/PGID_rev3 for INFLIGHT_REGISTRY. Terminal markers: '^STOP ' or '^DONE '.
set -u
B=/workspace/alloc_2026-09-26; D=$B/devices; R=$B/receipts; PY=/workspace/venv/bin/python
S=/dev/shm/alloc_2026-09-26; LG=$S/logs; LOG=$LG/family_rev3.log; MIRROR=$B/logs/family_rev3.log
E="env -i PATH=/usr/bin:/bin HOME=/root"
SEEDS="42 2027 7"
mkdir -p $LG || exit 9
mark() { printf '%s\n' "$*" >> $LOG; tail -1 $LOG | grep -qxF -- "$*" || { printf 'MARK_WRITE_FAILED %s\n' "$*" >&2; exit 4; }; printf '%s\n' "$*" >> $MIRROR 2>/dev/null || true; }
stop() { mark "STOP $1 $(date -u +%FT%TZ)"; exit 3; }
space_gate() {
  local f=$B/.space_probe_$$
  dd if=/dev/zero of=$f bs=1M count=400 conv=fsync status=none 2>/dev/null && [ "$(stat -c %s $f 2>/dev/null)" = "419430400" ] \
    && cmp -s -n 419430400 $f /dev/zero; local ok=$?; rm -f $f
  [ $ok -eq 0 ] || stop "space_gate_$1"
}
cd $D || exit 9
PG=$(ps -o pgid= $$ | tr -d ' '); echo "$PG" > $S/PGID_rev3; [ "$(cat $S/PGID_rev3)" = "$PG" ] || exit 9
mark "START rev3 $(date -u +%FT%TZ) pgid=$PG"
until [ -f $S/GO ]; do sleep 60; done
mark "GO_SEEN $(date -u +%FT%TZ)"
# ── step 0a: red cell R' (rule §7) ──
space_gate redprime
$E $PY -B alloc_chain_run.py PATH,HOME,LC_CTYPE $R --seed 42 --rule inservice --mix negbook --engine > $LG/cell_redprime_s42.log 2>&1 || stop "redprime_cell_rc"
mark "CELL_OK inservice_negbook s42 $(date -u +%FT%TZ)"
# ── step 0b: identity receipts (combo s42 + s2027 bitwise, engine 32/32) and wiring of the red arm ──
$PY -B - <<'EOF' || stop "identity_receipts"
import json
R="/workspace/alloc_2026-09-26/receipts"
a=json.load(open(f"{R}/ALLOC_CHAIN_inservice_shared_s42.json")); b=json.load(open(f"{R}/ALLOC_CHAIN_inservice_shared_s2027.json"))
r=json.load(open(f"{R}/ALLOC_CHAIN_inservice_negbook_s42.json"))
ok = a["COMBO_VS_ARCHIVE"]["ALL_IDENTICAL"] is True and a["ENGINE_IDENTITY"]["ALL_IDENTICAL"] is True and a["ENGINE_IDENTITY"]["n_paths_identical"]==32 \
     and b["COMBO_VS_ARCHIVE"]["ALL_IDENTICAL"] is True and r["COMBO_VS_ARCHIVE"]["ALL_IDENTICAL"] is False
print("IDENTITY combo_s42", a["COMBO_VS_ARCHIVE"]["ALL_IDENTICAL"], "engine_s42", a["ENGINE_IDENTITY"]["n_paths_identical"], "/32 combo_s2027",
      b["COMBO_VS_ARCHIVE"]["ALL_IDENTICAL"], "red_wired", not r["COMBO_VS_ARCHIVE"]["ALL_IDENTICAL"])
raise SystemExit(0 if ok else 1)
EOF
mark "GATE_OK identity_and_wiring"
$E $PY -B alloc_judge.py PATH,HOME,LC_CTYPE --mode IDENTITY --arm inservice_shared --seeds 42 --out $R/JUDGE_IDENTITY.json > $LG/judge_identity.log 2>&1 || stop "judge_identity_rc"
grep -q 'VERDICT=PASS' $LG/judge_identity.log || stop "judge_zero_point"
mark "GATE_OK judge_zero_point"
# ── step 0c: causality probe, every rule (oracle = positive control) ──
$E $PY -B alloc_causality.py $R/ALLOC_CAUSALITY.json > $LG/causality.log 2>&1 || stop "causality_rc"
grep -q '^ALLOC_CAUSALITY VERDICT=PASS' $LG/causality.log || stop "causality_verdict"
mark "GATE_OK causality"
# ── step 0d: red control R' (rule §7; a second failure stops the family with no further revision) ──
$E $PY -B alloc_judge.py PATH,HOME,LC_CTYPE --mode RPRIME --arm inservice_negbook --seeds 42 --out $R/JUDGE_RPRIME.json > $LG/judge_RPRIME.log 2>&1 || stop "judge_RPRIME_rc"
grep -q 'VERDICT=PASS' $LG/judge_RPRIME.log || stop "RED_CONTROL_RPRIME_FAILED_family_stops_final"
mark "GATE_OK red_control"
# ── step 1: ceiling control O (s42) ──
space_gate oracle
$E $PY -B alloc_chain_run.py PATH,HOME,LC_CTYPE $R --seed 42 --rule oracle --mix shared --engine > $LG/cell_oracle_s42.log 2>&1 || stop "oracle_cell_rc"
$E $PY -B alloc_judge.py PATH,HOME,LC_CTYPE --mode O --arm oracle_shared --seeds 42 --out $R/JUDGE_O.json > $LG/judge_O.log 2>&1 || stop "judge_O_rc"
if grep -q 'VERDICT=RUN_A1_A2_A3_A4' $LG/judge_O.log; then ARMS="cap050_shared look1800_shared inservice_orth invvol_shared"
elif grep -q 'VERDICT=RUN_A3_A4_ONLY' $LG/judge_O.log; then ARMS="inservice_orth invvol_shared"
else stop "judge_O_verdict_missing"; fi
mark "GATE_OK oracle arms=[$ARMS]"
# ── step 2: zero-return footprint (combo only, three seeds in parallel per arm) ──
for arm in $ARMS; do
  rule=${arm%_*}; mix=${arm##*_}; pids=""; space_gate footprint_$arm
  for s in $SEEDS; do
    $E $PY -B alloc_chain_run.py PATH,HOME,LC_CTYPE $R/footprint --seed $s --rule $rule --mix $mix > $LG/fp_${arm}_s$s.log 2>&1 & pids="$pids $!"
  done
  for p in $pids; do wait $p || stop "footprint_cell_rc_$arm"; done
done
$E $PY -B alloc_footprint.py $R/FOOTPRINT.json $ARMS > $LG/footprint.log 2>&1 || stop "footprint_rc"
grep -q '^ALLOC_FOOTPRINT DONE' $LG/footprint.log || stop "footprint_done_missing"
ENG_ARMS=""
for arm in $ARMS; do
  v=$(grep "^FOOTPRINT_VERDICT $arm " $LG/footprint.log | sed 's/.*gross_gate=\([A-Z_]*\).*/\1/')
  case "$v" in
    DEPLOYABLE) ENG_ARMS="$ENG_ARMS $arm";;
    NOT_DEPLOYABLE) mark "NOTE $arm NOT_DEPLOYABLE by the gross-gate rule: described at the footprint only, no engine cells";;
    *) stop "footprint_escalate_$arm:$v";;
  esac
done
mark "GATE_OK footprint engine_arms=[$ENG_ARMS]"
# ── step 3: engine cells, one at a time (alloc_chain_run's gate: <= 1 foreign bt_launch group) ──
for arm in $ENG_ARMS; do
  rule=${arm%_*}; mix=${arm##*_}
  for s in $SEEDS; do
    space_gate ${arm}_s$s
    $E $PY -B alloc_chain_run.py PATH,HOME,LC_CTYPE $R --seed $s --rule $rule --mix $mix --engine > $LG/cell_${arm}_s$s.log 2>&1 || stop "engine_cell_rc_${arm}_s$s"
    mark "CELL_OK ${arm} s$s $(date -u +%FT%TZ)"
  done
done
# ── BTC daily beta (rule §5 required report; lead 2026-09-26: a process step BEFORE the verdicts, failure = STOP) ──
for arm in $ENG_ARMS; do
  $E $PY -B alloc_beta.py PATH,HOME,LC_CTYPE $arm 42,2027,7 $R/BETA_$arm.json > $LG/beta_$arm.log 2>&1 || stop "beta_rc_$arm"
  grep -q '^ALLOC_BETA DONE' $LG/beta_$arm.log || stop "beta_done_missing_$arm"
done
mark "GATE_OK btc_beta"
# ── verdicts (rule §3) ──
for arm in $ENG_ARMS; do
  case $arm in cap050_shared) c=A1;; look1800_shared) c=A2;; inservice_orth) c=A3;; invvol_shared) c=A4;; esac
  extra=""
  if [ "$c" = A3 ]; then
    mc=$($PY -c "import json;print(json.load(open('$R/FOOTPRINT.json'))['arms']['inservice_orth']['mechanism_corr_2026_median_mean_over_seeds'])")
    extra="--noninf-mech-corr $mc"
  fi
  $E $PY -B alloc_judge.py PATH,HOME,LC_CTYPE --mode FAMILY --arm $arm --seeds 42,2027,7 --arm-class $c $extra --out $R/JUDGE_FAMILY_$arm.json > $LG/judge_$arm.log 2>&1 || stop "judge_family_rc_$arm"
  mark "VERDICT_OK $arm $(tail -1 $LG/judge_$arm.log)"
done
mark "DONE $(date -u +%FT%TZ)"
