#!/bin/bash
# Q1: re-run the EXTENDED-axis NC cells (9,252 anchors to 2026-09-18 20:00Z) into MY root, then read the live window.
# The X configs already exist in news2 and previously completed rc=0; only paths.pod_root is overridden.
set -e
W=/dev/shm/fresh_2026-09-23; FA=/dev/shm/fanom_2026-09-24
NC=/dev/shm/news2_2026-09-23
SEED=$1
TAG="NEWS2_s${SEED}X"
VDIR=$FA/ext/${TAG}
PRED=520
A=$(df -BM /dev/shm|tail -1|awk '{print $4}'|tr -d M)
echo "[$TAG] shm_gate avail=${A}MiB need=$((PRED+1024))MiB"
[ "$A" -ge $((PRED+1024)) ] || { echo "[$TAG] WAIT"; exit 9; }
mkdir -p $VDIR $FA/logs $FA/runs
cd $NC/engine
/workspace/venv/bin/python - "$NC" "$SEED" "$VDIR" "$FA" <<'PY'
import json, hashlib, sys, copy
nc, seed, vdir, fa = sys.argv[1:5]
def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda: f.read(1<<22), b""): h.update(b)
    return h.hexdigest()
cfgp = f"{nc}/configs/RUN_CONFIG_NEWS2_s{seed}X_2026-09-23.json"
c = json.load(open(cfgp))
want = f"NEWS2_s{seed}X|scaled|rule|raw|UAFE"
runs = [r for r in c["runs"] if r["tag"] == want]
assert len(runs) == 1, [r["tag"] for r in c["runs"]]
c["runs"] = [copy.deepcopy(runs[0])]                 # arm/tag/targets UNCHANGED
c["paths"] = dict(c["paths"]); c["paths"]["pod_root"] = fa
c["_diagnostic_note"] = {"purpose": "Q1: extended axis to 2026-09-18 20:00Z so the live drawdown window is inside the backtest",
                         "derived_from": cfgp, "derived_from_sha256": sha(cfgp),
                         "changed": ["paths.pod_root -> "+fa],
                         "deliberately_unchanged": ["runs[0].arm", "runs[0].tag", "runs[0].targets"]}
json.dump(c, open(f"{vdir}/RUN_CONFIG.json","w"), indent=1)
print("DERIVED config for", want, "; pod_root ->", fa)
PY
env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B $W/devices/fa_launch_guard.py PATH,HOME,LC_CTYPE $VDIR/RUN_CONFIG.json
setsid env -i PATH=/usr/bin:/bin HOME=/root nice -n 12 /workspace/venv/bin/python -B bt_launch.py PATH,HOME,LC_CTYPE \
  $VDIR/RUN_CONFIG.json --resume $TAG > $FA/logs/engine_$TAG.log 2>&1 < /dev/null &
sleep 5; echo "[$TAG] engine PGID=$(ps -o pgid= -p $! | tr -d ' ')"
until grep -qE "BT_LAUNCH VERDICT|Traceback|No space left" $FA/logs/engine_$TAG.log 2>/dev/null; do sleep 20; done
grep -E "BT_LAUNCH VERDICT|Traceback|No space left" $FA/logs/engine_$TAG.log | head -1
echo "[$TAG] cell: $FA/runs/${TAG}_scaled_rule_raw_UAFE"
df -h /dev/shm|tail -1
