#!/bin/bash
# test_mr_stop_dispatch.sh <devices dir under test> -- red tests of the class "stop checked, then a blocking wait, then a launch"
# (fresh2 2026-09-27; run 3's master dispatched A0_m3's prep 01:39:33Z, 7.5 min after the 01:31:59Z STOP). Runs the REAL device
# scripts, copied into a /tmp sandbox with every /dev/shm and /workspace path rewritten (each rewrite must match; after it no
# /dev/shm or /workspace literal may remain, so nothing here can touch family state) and the polls shortened to 1 s.
#   S  structural: every dispatcher line that invokes mr_prep.sh / mr_engine_queue.sh / bt_launch.py / mr_train_king.py carries
#      mr_guard on the same line; population must be >= 7 (0/0 is not a pass). Dispatchers = the *.sh here that operate on the family
#      root (contain its path), except mr_prep.sh (guarded at entry, T3) and test_* -- derived, not listed: the pod2 devices dir also
#      holds news2's 09-23/24 run_* scripts, which never touch this root and are not family launches.
#   T1 master: STOP lands while the prep loop waits for a slot           => no prep launched after it (run 3's incident)
#   T2 engine queue: STOP lands during the PAUSE wait of a READY cell      => no engine launch
#   T3 consumer mr_prep.sh: STOP after the scope offset / no scope          => rc 3, no FAILED marker, no second STOP line
#   B1/B2/B3 baselines (must be green on the fixed AND unfixed devices, else the guard blocks legitimate runs): a STOP from an
#      EARLIER run (before the offset) must not stop the master, the queue, or a prep.
set -u
DEV=$(cd "$1" && pwd); T=$(mktemp -d /tmp/fresh2_stoptest.XXXXXX); R=$T/root; N=$T/news
npass=0; nfail=0
ok()  { echo "PASS $*"; npass=$((npass + 1)); }
bad() { echo "FAIL $*"; nfail=$((nfail + 1)); }
ts()  { date -u +%Y-%m-%dT%H:%M:%SZ; }
rewrite() {   # <src> <dst>: sandbox copy; each rule must match in the files that carry it
  sed -e "s#/dev/shm/ENGINE_PRIORITY#$T/prio#g" -e "s#/dev/shm/mretrain_2026-09-26#$R#g" -e "s#/dev/shm/news2_2026-09-23#$N#g" \
      -e "s#/dev/shm/nc_2026-09-23#$T/nc#g" -e "s#/dev/shm/fresh_2026-09-23/devices/memgate.sh#$T/stub/memgate.sh#g" \
      -e "s#/dev/shm/fresh_2026-09-23/devices/fa_ladsave.py#$T/stub/fa_ladsave.py#g" -e "s#/workspace/venv/bin/python#python3#g" \
      -e "s#/root/news_2026-09-23_env/venv314/bin/python#python3#g" -e 's#sleep \(20\|30\|60\|120\)#sleep 1#g' \
      -e 's#grep "bt_launch\\.py" | grep -v grep#grep "NO_SUCH_PROCESS_fresh2_test" | grep -v grep#' "$1" > "$2"
  if grep -n "/dev/shm/\|/workspace/" "$2" | grep -v "^[0-9]*:\s*#" | grep -q .; then echo "SANDBOX LEAK in $2:"; grep -n "/dev/shm/\|/workspace/" "$2"; exit 9; fi
}
fresh() {     # new sandbox root with the devices under test
  rm -rf $R $N $T/prio $T/stub $T/launches; mkdir -p $R/devices $R/logs $R/arms $R/gate/A0_m0_dup $N/engine $T/prio $T/stub
  for f in mr_master.sh mr_engine_queue.sh mr_prep.sh mr_stop.sh; do [ -e $DEV/$f ] && rewrite $DEV/$f $R/devices/$f; done
  echo x > $R/gate/A0_m0_dup/KING_OOF.npz
  printf '#!/bin/bash\nexit 0\n' > $T/stub/memgate.sh
  printf 'import sys; open(sys.argv[-1], "w").write("x")\n' > $T/stub/fa_ladsave.py
  printf 'import sys, time; open("%s/launches", "a").write("%%.3f engine %%s\\n" %% (time.time(), sys.argv[-1])); print("BT_LAUNCH VERDICT=PASS")\n' $T > $N/engine/bt_launch.py
  [ "$(grep -c NO_SUCH_PROCESS_fresh2_test $R/devices/mr_engine_queue.sh)" = 1 ] || { echo "capacity-grep rewrite did not apply"; exit 9; }
}
[ "$(grep -c 'grep "bt_launch\\.py" | grep -v grep' $DEV/mr_engine_queue.sh)" = 1 ] || { echo "rewrite target (capacity grep) not found exactly once"; exit 9; }

echo "== S structural (devices dir itself)"
sites=0; unguarded=0
for f in $DEV/*.sh; do
  b=$(basename $f); case $b in mr_prep.sh|test_*) continue;; esac
  grep -q "/dev/shm/mretrain_2026-09-26" $f || { echo "  not a family script (no family root): $b"; continue; }
  while IFS= read -r line; do
    sites=$((sites + 1))
    echo "$line" | grep -q "mr_guard" || { unguarded=$((unguarded + 1)); echo "  unguarded launch $b: $(echo "$line" | cut -c1-140)"; }
  done < <(grep -E '(bash|\$PV[^;|]*|python3?)[^;|]* (\$D/)?(mr_prep\.sh|mr_engine_queue\.sh|bt_launch\.py|mr_train_king\.py)' $f | grep -vE '^\s*#')
done
echo "  launch sites found: $sites, unguarded: $unguarded"
[ $sites -ge 7 ] && [ $unguarded -eq 0 ] && ok "S sites=$sites all guarded" || bad "S sites=$sites unguarded=$unguarded (population >= 7 required)"

# ---- master scenario: 6 listed preps, 3 slots, each prep 6 s; the stub engine queue writes a STOP after 2 s (or not)
master_case() {   # <label> <stop yes|no> <seed an earlier-run STOP yes|no>
  local LB=$1 STOPQ=$2 OLD=$3
  fresh
  cat > $R/devices/mr_prep.sh <<EOF
#!/bin/bash
[ "\$3" = preflight ] && { echo "MR_COMBO_PREFLIGHT PASS stub"; exit 0; }
[ "\$3" = listed ] || exit 0
echo "\$(date +%s.%N) prep \$1 \$2" >> $T/launches; sleep 6; exit 0
EOF
  echo 'print("MR_PREFLIGHT_REFS PASS stub")' > $R/devices/mr_preflight_refs.py
  echo 'print("ALL_PASS=True stub")' > $R/devices/mr_gates.py
  if [ $STOPQ = yes ]; then
    printf '#!/bin/bash\nsleep 2; echo "$(date -u +%%Y-%%m-%%dT%%H:%%M:%%SZ) STOP: engine queue: stub red FAIL" >> %s/logs/master.log; echo x > %s/ENGINE_QUEUE_STOPPED; exit 1\n' $R $R > $R/devices/mr_engine_queue.sh
  else
    printf '#!/bin/bash\nsleep 14; exit 0\n' > $R/devices/mr_engine_queue.sh
  fi
  for k in 1 2 3 4 5 6; do echo "X $k listed"; done > $R/devices/PREP_LIST.txt
  [ $OLD = yes ] && echo "2026-09-27T00:00:00Z STOP: an earlier run's STOP (before this run's offset)" > $R/logs/master.log
  timeout -k 5 60 bash $R/devices/mr_master.sh > $T/master_$LB.out 2>&1
  n=$(grep -c " prep X " $T/launches 2>/dev/null); n=${n:-0}
  echo "  [$LB] preps launched: $n; master.log tail: $(tail -2 $R/logs/master.log | tr '\n' '|' | cut -c1-200)"
}
echo "== T1 master: STOP during the slot wait"
master_case T1 yes no
[ "$n" = 3 ] && grep -q "PREP_QUEUE_STOPPED" $R/logs/master.log && ok "T1 3 preps (all before the STOP), PREP_QUEUE_STOPPED" || bad "T1 $n preps launched (3 expected: the 4th waited for a slot across the STOP)"
echo "== B1 master baseline: an earlier run's STOP before the offset, no new STOP"
master_case B1 no yes
[ "$n" = 6 ] && grep -q "MASTER_DONE" $R/logs/master.log && ok "B1 6/6 preps, MASTER_DONE" || bad "B1 $n/6 preps launched or no MASTER_DONE"

# ---- engine queue scenario: arms A, B READY; PAUSE present; STOP (or not) appended at +2 s; PAUSE removed at +4 s
queue_case() {    # <label> <stop yes|no>
  local LB=$1 STOPQ=$2
  fresh
  for a in A B; do mkdir -p $R/arms/$a/configs; touch $R/arms/$a/READY_s42; done
  printf 'A 42\nB 42\n' > $T/ORDER.txt; touch $R/PAUSE
  echo "2026-09-27T00:00:00Z STOP: an earlier run's STOP (before this run's offset)" > $R/logs/master.log
  export MR_MASTER_LOG=$R/logs/master.log MR_LOG_OFFSET=$(wc -c < $R/logs/master.log | tr -d ' ')   # the test plays the dispatcher
  ( sleep 2; [ $STOPQ = yes ] && echo "$(ts) STOP: prep Z_m9 FAILED: stub" >> $R/logs/master.log; sleep 2; rm -f $R/PAUSE ) &
  timeout -k 5 25 bash $R/devices/mr_engine_queue.sh $T/ORDER.txt > $T/queue_$LB.out 2>&1; qrc=$?
  wait; unset MR_MASTER_LOG MR_LOG_OFFSET
  n=$(grep -c " engine " $T/launches 2>/dev/null); n=${n:-0}
  echo "  [$LB] engine launches: $n, queue rc=$qrc; queue.log tail: $(tail -1 $R/logs/engine/queue.log | cut -c1-160)"
}
echo "== T2 engine queue: STOP during the PAUSE wait"
queue_case T2 yes
[ "$n" = 0 ] && [ $qrc -ne 0 ] && ok "T2 no engine launch after the STOP, rc=$qrc" || bad "T2 $n engine launch(es) after the STOP"
echo "== B2 engine queue baseline: earlier run's STOP only"
queue_case B2 no
[ "$n" -ge 1 ] && ok "B2 $n engine launch(es) (earlier STOP ignored)" || bad "B2 no engine launch (guard blocks a legitimate run)"

# ---- consumer: the real mr_prep.sh
prep_case() {     # <label> <scope: none|after|before>
  local LB=$1 SC=$2
  fresh
  echo "2026-09-27T00:00:00Z STOP: an earlier run's STOP" > $R/logs/master.log
  local off; off=$(wc -c < $R/logs/master.log | tr -d ' ')
  [ $SC = after ] && echo "$(ts) STOP: engine queue: stub" >> $R/logs/master.log
  local before; before=$(grep -c "STOP" $R/logs/master.log)
  if [ $SC = none ]; then env -u MR_MASTER_LOG -u MR_LOG_OFFSET bash $R/devices/mr_prep.sh Y 1 train > $T/prep_$LB.out 2>&1; prc=$?
  else MR_MASTER_LOG=$R/logs/master.log MR_LOG_OFFSET=$off bash $R/devices/mr_prep.sh Y 1 train > $T/prep_$LB.out 2>&1; prc=$?; fi
  added=$(( $(grep -c "STOP" $R/logs/master.log) - before )); failed=no; [ -e $R/arms/Y_m1/FAILED ] && failed=yes
  echo "  [$LB] prep rc=$prc, FAILED marker=$failed, STOP lines added=$added, refused line=$(grep -c REFUSED_LAUNCH $R/logs/Y_m1/prep.log 2>/dev/null)"
}
echo "== T3a consumer: no stop scope declared"
prep_case T3a none
[ $prc = 3 ] && [ $failed = no ] && [ $added = 0 ] && ok "T3a refused rc 3, nothing written" || bad "T3a rc=$prc failed=$failed added=$added"
echo "== T3b consumer: STOP after the offset"
prep_case T3b after
[ $prc = 3 ] && [ $failed = no ] && [ $added = 0 ] && ok "T3b refused rc 3, nothing written" || bad "T3b rc=$prc failed=$failed added=$added"
echo "== B3 consumer baseline: earlier run's STOP only (the prep proceeds; in the sandbox it then fails on missing inputs)"
prep_case B3 before
[ $prc != 3 ] && [ "$(grep -c REFUSED_LAUNCH $R/logs/Y_m1/prep.log 2>/dev/null)" = 0 ] && ok "B3 not refused (rc=$prc)" || bad "B3 refused a legitimate prep"

echo "TEST_MR_STOP_DISPATCH devices=$DEV pass=$npass fail=$nfail sandbox=$T"
[ $nfail -eq 0 ]
