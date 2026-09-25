#!/bin/zsh
# Pre-window gates for the v2 + B + C release, 09:00Z quiet window, STRICTLY sequential (C-4, 2026-09-25).
# 1 F-2 rollback rehearsal (treeNC5 old = production, treeNC7 new; A0 = 20Z 09-24)
# 2 gate 3' in the POST-INSTALL layout (--archive-k1), NC5 vs NC7, all eligible NC-era anchors
# 3 rev1 judge on that run dir
# 4 test_m3_v2_ret5.py full (T1..T5) on NC7 with --installed = a moved-layout copy of the installed code set
# 5 beta parity (SERVED == DIRECT) on NC7 from the gate run
# Every step: command, start/end, real exit code, verdict line. Never calls the exchange; writes only under $OUT.
set -u
RC=~/Desktop/quant_research/multi_asset/exports/research/nc_2026-09-23; NCW=~/cc_tmp/nc_20260923; PY=~/wide_shadow/venv/bin/python
OUT=${1:?out dir}; mkdir -p $OUT; LOG=$OUT/PREWINDOW_RUN.log
step() { echo "=== $1 start $(date -u +%FT%TZ)" >> $LOG; }
fin()  { echo "=== $1 end $(date -u +%FT%TZ) rc=$2" >> $LOG; }
freegb() { df -g / | tail -1 | awk '{print $4}'; }
{ echo "host $(hostname) start $(date -u +%FT%TZ) free_GiB=$(freegb)"; echo "shas: NC5 shadow_loop $(shasum -a 256 $NCW/treeNC5/shadow_loop_v3.py | cut -c1-12) NC7 shadow_loop $(shasum -a 256 $NCW/treeNC7/shadow_loop_v3.py | cut -c1-12) prod shadow_loop $(shasum -a 256 ~/wide_shadow/shadow_loop_v3.py | cut -c1-12)"; } >> $LOG
[ "$(freegb)" -ge 15 ] || { echo "ABORT free < 15 GiB" >> $LOG; exit 9; }
/usr/bin/python3 /Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/common/venue_quiet_window.py >> $LOG 2>&1; echo "venue_quiet_window rc=$?" >> $LOG

step F2; CMD=($PY -B $RC/devices/test_c_rollback_rehearsal.py $NCW/treeNC5 $NCW/treeNC7 1790280000 $OUT/f2)
echo "cmd: ${CMD[*]}" >> $LOG; ${CMD[@]} > $OUT/f2.log 2>&1; r=$?; tail -3 $OUT/f2.log >> $LOG; fin F2 $r
echo "free_GiB=$(freegb)" >> $LOG

step GATE3P; CMD=($PY -B $RC/devices/nc_v2_nonbeta_gate.py $NCW/treeNC5 $NCW/treeNC7 $OUT/g3p --archive-k1)
echo "cmd: ${CMD[*]}" >> $LOG; ${CMD[@]} > $OUT/g3p.log 2>&1; r=$?; grep -E "^anchor |NC_V2_NONBETA_GATE" $OUT/g3p.log | cut -c1-260 >> $LOG; fin GATE3P $r
echo "free_GiB=$(freegb)" >> $LOG

step REV1; CMD=($PY -B $RC/devices/nc_v2_nonbeta_gate_rev1.py $NCW/treeNC5 $NCW/treeNC7 $OUT/g3p $OUT/NC_V2_NONBETA_GATE_REV1_postinstall.json)
echo "cmd: ${CMD[*]}" >> $LOG; ${CMD[@]} > $OUT/rev1.log 2>&1; r=$?; grep -E "^anchor |NC_V2_NONBETA_GATE|census|REFUSED" $OUT/rev1.log | cut -c1-260 >> $LOG; fin REV1 $r

step T1; I=$OUT/installed_moved; mkdir -p $I/fea171/_archive_2026-09-25
cp -p ~/wide_shadow/shadow_loop_v3.py $I/; for f in ~/wide_shadow/fea171/*.py ~/wide_shadow/fea171/*.sh; do cp -p $f $I/fea171/; done
for f in sidecar_blend.py combo_stage_t3c_candidate.py sidecar_daemon.sh; do mv $I/fea171/$f $I/fea171/_archive_2026-09-25/$f; done
echo "installed_moved: $(ls $I/fea171 | wc -l | tr -d ' ') entries in fea171; archived: $(ls $I/fea171/_archive_2026-09-25 | tr '\n' ' ')" >> $LOG
CMD=($PY -B $RC/devices/test_m3_v2_ret5.py $NCW/treeNC7 $NCW/treeNC5 --installed $I)
echo "cmd: ${CMD[*]}" >> $LOG; ${CMD[@]} > $OUT/t1_full.log 2>&1; r=$?; grep -E "T1 census|TEST_M3_V2|checks passed|FAIL" $OUT/t1_full.log | cut -c1-260 >> $LOG; fin T1 $r

step BETAPARITY; CMD=($PY -B $RC/devices/nc_v2_beta_parity.py $NCW/treeNC7 $OUT/g3p $OUT/NC_V2_BETA_PARITY_postinstall.json)
echo "cmd: ${CMD[*]}" >> $LOG; ${CMD[@]} > $OUT/betaparity.log 2>&1; r=$?; grep -E "BETA_PARITY|RED|anchor" $OUT/betaparity.log | cut -c1-260 >> $LOG; fin BETAPARITY $r
echo "ALL DONE $(date -u +%FT%TZ) free_GiB=$(freegb)" >> $LOG
