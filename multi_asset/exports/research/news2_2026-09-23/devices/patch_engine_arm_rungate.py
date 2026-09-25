#!/usr/bin/env python3
"""Wire the team run gate into ladder_engine_arm.sh, and record this cell's own PGID unconditionally.

TWO FIXES, one of them for a failure of mine:

(1) RUN GATE (lead's final rule): before the engine step, require other bt_launch groups <= 2 (counted
    by DISTINCT OTHER PGID), cgroup headroom >= 24 GiB, /dev/shm free >= 4 GiB; recheck every 60 s;
    all three numbers into a receipt; read-only, never signal another process.

(2) SELF-PGID RECORDING -- the class-shaped fix for a real failure. lead asked me to identify a third
    bt_launch group (pgid 3062350) against my own records, and I COULD NOT ANSWER, because I launched
    the FUND_res_ncfill cell with a direct `ssh pod2 'bash ladder_engine_arm.sh ...'` instead of the
    setsid wrapper that writes a .pgid file. Every queued cell recorded a PGID; the one cell I ran by
    hand did not, and that is exactly the cell whose window overlaps the unattributed group.
    The instance fix would be "remember to use the wrapper". The class fix is that the SCRIPT records
    its own PGID on every invocation, so no future cell can be launched in a way that leaves it
    unattributable -- however it is started, by a queue or by hand.
"""
p = "/dev/shm/pnoise_2026-09-24/devices/ladder_engine_arm.sh"
s = open(p).read()
n0 = len(s)

s = s.replace(
    '''LAD=$EXP/work/ladder_$ARM''',
    '''# (2) record THIS cell's own PGID, unconditionally, however this script was started.
MY_PGID=$(ps -o pgid= -p $$ | tr -d ' ')
mkdir -p $L
printf '%s\\n' "PGID $MY_PGID arm=$ARM started=$(date -u +%H:%M:%SZ) launcher=$0" \\
  > $L/enginearm_$ARM.pgid
say "own PGID $MY_PGID recorded to $L/enginearm_$ARM.pgid"

LAD=$EXP/work/ladder_$ARM''', 1)

s = s.replace(
    '''say "engine base cell"
cd $E''',
    '''# (1) team run gate -- blocks until other bt_launch groups <= 2, headroom >= 24 GiB, shm >= 4 GiB
say "run gate"
bash $D/rungate.sh "$ARM" "$EXP/receipts/STEP3_RUNGATE_$ARM.json" 2>&1 | tee -a $L/step3_engine.log
if [ ! -s "$EXP/receipts/STEP3_RUNGATE_$ARM.json" ]; then say "RUN GATE produced no receipt"; exit 5; fi

say "engine base cell"
cd $E''', 1)

open(p, "w").write(s)
ok = all(k in s for k in ("rungate.sh", "enginearm_$ARM.pgid", "own PGID"))
print("patched:", ok, "bytes", n0, "->", len(s))
