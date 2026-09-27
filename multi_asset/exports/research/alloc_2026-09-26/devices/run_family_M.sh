#!/bin/bash
# run_family_M.sh — EXECUTOR (TEAM_PROTOCOL §10-f) for DECISION_RULE_combination_layer §9 (family M, risk-control shape).
# Order (rule §9): device re-identity -> zero-return footprint + MECHANISM GATE + variance-only power projection -> WAIT for the lead's
# GO_M_ENGINE (the projection is reported first) -> red control R_M (conc20, s42) -> M engine cells x {42, 2027, 7} -> BTC beta -> verdict.
# Markers on tmpfs with read-back (E-0926-E); every cell behind a 400 MiB space gate; candidate cells also wait on HOLD_CANDIDATE_CELLS
# (lead's engine priority) inside alloc_chain_run. Terminal markers: '^STOP ' or '^DONE '.
set -u
B=/workspace/alloc_2026-09-26; D=$B/devices; R=$B/receipts/M; PY=/workspace/venv/bin/python
S=/dev/shm/alloc_2026-09-26; LG=$S/logs; LOG=$LG/family_M.log; MIRROR=$B/logs/family_M.log
E="env -i PATH=/usr/bin:/bin HOME=/root"
SEEDS="42 2027 7"
mkdir -p $LG $R || exit 9
mark() { printf '%s\n' "$*" >> $LOG; tail -1 $LOG | grep -qxF -- "$*" || { printf 'MARK_WRITE_FAILED %s\n' "$*" >&2; exit 4; }; printf '%s\n' "$*" >> $MIRROR 2>/dev/null || true; }
stop() { mark "STOP $1 $(date -u +%FT%TZ)"; exit 3; }
space_gate() {
  local f=$B/.space_probe_$$
  dd if=/dev/zero of=$f bs=1M count=400 conv=fsync status=none 2>/dev/null && [ "$(stat -c %s $f 2>/dev/null)" = "419430400" ] \
    && cmp -s -n 419430400 $f /dev/zero; local ok=$?; rm -f $f
  [ $ok -eq 0 ] || stop "space_gate_$1"
}
cd $D || exit 9
PG=$(ps -o pgid= $$ | tr -d ' '); echo "$PG" > $S/PGID_M; [ "$(cat $S/PGID_M)" = "$PG" ] || exit 9
mark "START familyM $(date -u +%FT%TZ) pgid=$PG"
# ── step 0: the combo code changed (momneutral / conc20 added): the in-service arm must still reproduce the archive bit for bit ──
space_gate reidentity
$E $PY -B alloc_chain_run.py PATH,HOME,LC_CTYPE $R --seed 42 --rule inservice --mix shared --label reidentity_M_s42 > $LG/M_reidentity_s42.log 2>&1 || stop "reidentity_rc"
grep -q 'combo_vs_archive=True' $LG/M_reidentity_s42.log || stop "reidentity_not_bitwise"
mark "GATE_OK reidentity_combo_s42"
# ── step 1: zero-return footprint combos (M x 3 seeds, R_M s42), mechanism gate, variance-only power projection ──
space_gate footprint
pids=""
for s in $SEEDS; do $E $PY -B alloc_chain_run.py PATH,HOME,LC_CTYPE $R/footprint --seed $s --rule inservice --mix momneutral > $LG/M_fp_s$s.log 2>&1 & pids="$pids $!"; done
$E $PY -B alloc_chain_run.py PATH,HOME,LC_CTYPE $R/footprint --seed 42 --rule inservice --mix conc20 > $LG/M_fp_rm_s42.log 2>&1 & pids="$pids $!"
for p in $pids; do wait $p || stop "footprint_cell_rc"; done
$E $PY -B alloc_mfoot.py $R/MFOOT.json > $LG/M_mfoot.log 2>&1 || stop "mfoot_rc"
grep -q '^ALLOC_MFOOT MECHANISM_GATE=PASS' $LG/M_mfoot.log || stop "MECHANISM_GATE_FAILED"
mark "GATE_OK mechanism (power projection in $R/MFOOT.json; waiting for $S/GO_M_ENGINE)"
until [ -f $S/GO_M_ENGINE ]; do sleep 60; done
mark "GO_M_ENGINE_SEEN $(date -u +%FT%TZ)"
# ── step 2: red control R_M (s42) ──
space_gate rm
$E $PY -B alloc_chain_run.py PATH,HOME,LC_CTYPE $R --seed 42 --rule inservice --mix conc20 --engine > $LG/M_cell_rm_s42.log 2>&1 || stop "rm_cell_rc"
mark "CELL_OK inservice_conc20 s42 $(date -u +%FT%TZ)"
$E $PY -B alloc_judge.py PATH,HOME,LC_CTYPE --mode RM --arm inservice_conc20 --seeds 42 --out $R/JUDGE_RM.json > $LG/M_judge_RM.log 2>&1 || stop "judge_RM_rc"
grep -q 'VERDICT=PASS' $LG/M_judge_RM.log || stop "RED_CONTROL_RM_FAILED_family_M_stops"
mark "GATE_OK red_control_RM"
# ── step 3: M engine cells (candidate: also waits on HOLD_CANDIDATE_CELLS inside alloc_chain_run) ──
for s in $SEEDS; do
  space_gate m_s$s
  $E $PY -B alloc_chain_run.py PATH,HOME,LC_CTYPE $R --seed $s --rule inservice --mix momneutral --engine > $LG/M_cell_s$s.log 2>&1 || stop "m_cell_rc_s$s"
  mark "CELL_OK inservice_momneutral s$s $(date -u +%FT%TZ)"
done
# ── step 4: BTC beta (required report, before the verdict) ──
$E $PY -B alloc_beta.py PATH,HOME,LC_CTYPE inservice_momneutral 42,2027,7 $R/BETA_momneutral.json > $LG/M_beta.log 2>&1 || stop "beta_rc"
grep -q '^ALLOC_BETA DONE' $LG/M_beta.log || stop "beta_done_missing"
mark "GATE_OK btc_beta"
# ── step 5: verdict ──
$E $PY -B alloc_judge.py PATH,HOME,LC_CTYPE --mode MFAM --arm inservice_momneutral --seeds 42,2027,7 --out $R/JUDGE_MFAM.json > $LG/M_judge_MFAM.log 2>&1 || stop "judge_MFAM_rc"
mark "VERDICT_OK momneutral $(tail -1 $LG/M_judge_MFAM.log)"
mark "DONE $(date -u +%FT%TZ)"
