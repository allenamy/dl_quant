#!/bin/bash
# Regenerate an ORIGINAL arm's base cell into MY root and save a COMPLETE per-anchor series (price + daily r),
# so no later diagnostic arm ever needs the original cell again. This closes the gap that bit me twice.
set -e
W=/dev/shm/fresh_2026-09-23; FA=/dev/shm/fanom_2026-09-24
ARMROOT=$1; SEED=$2
ARMNAME=$(basename $ARMROOT | cut -d_ -f1)
[ "$ARMNAME" = "fresh" ] && BASE="FRESH_s${SEED}" || BASE="NEWS_s${SEED}"
TAG="orig_${ARMNAME}_s${SEED}"; VDIR=$FA/orig/${BASE}
PRED=440
A=$(df -BM /dev/shm|tail -1|awk '{print $4}'|tr -d M)
echo "[$TAG] shm_gate avail=${A}MiB need=$((PRED+1024))MiB"; [ "$A" -ge $((PRED+1024)) ] || { echo "[$TAG] WAIT"; exit 9; }
mkdir -p $VDIR $FA/runs $FA/logs; cd $W/engine
/workspace/venv/bin/python - "$ARMROOT" "$SEED" "$BASE" "$VDIR" "$FA" <<'PY'
import json, hashlib, sys, copy
armroot, seed, base, vdir, fa = sys.argv[1:6]
def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda: f.read(1<<22), b""): h.update(b)
    return h.hexdigest()
root = armroot
cfgp = f"{root}/configs/RUN_CONFIG_{base}_2026-09-23.json"
c = json.load(open(cfgp))
want = f"{base}|scaled|rule|raw|UAFE"
runs = [r for r in c["runs"] if r["tag"] == want]; assert len(runs)==1
c["runs"] = [copy.deepcopy(runs[0])]          # arm/tag UNCHANGED
c["paths"] = dict(c["paths"]); c["paths"]["pod_root"] = fa
c["_note"] = {"purpose": "regenerate the ORIGINAL base cell into my own root to save a complete per-anchor series",
              "derived_from": cfgp, "derived_from_sha256": sha(cfgp),
              "changed": ["paths.pod_root -> "+fa, "runs[] -> single base cell"],
              "deliberately_unchanged": ["runs[0].arm", "runs[0].tag", "runs[0].targets"]}
json.dump(c, open(f"{vdir}/RUN_CONFIG.json","w"), indent=1); print("derived config, pod_root ->", fa)
PY
env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B $W/devices/fa_launch_guard.py PATH,HOME,LC_CTYPE $VDIR/RUN_CONFIG.json
setsid env -i PATH=/usr/bin:/bin HOME=/root nice -n 12 /workspace/venv/bin/python -B bt_launch.py PATH,HOME,LC_CTYPE \
  $VDIR/RUN_CONFIG.json --resume $TAG > $FA/logs/engine_$TAG.log 2>&1 < /dev/null &
sleep 5; echo "[$TAG] PGID=$(ps -o pgid= -p $! | tr -d ' ')"
until grep -qE "BT_LAUNCH VERDICT|Traceback|No space left" $FA/logs/engine_$TAG.log 2>/dev/null; do sleep 20; done
grep -E "BT_LAUNCH VERDICT|Traceback|No space left" $FA/logs/engine_$TAG.log | head -1
CELL=$FA/runs/${BASE}_scaled_rule_raw_UAFE
SER=$FA/receipts/SER_ORIG_${BASE}.npz
env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 /workspace/venv/bin/python -B - "$CELL" "$SER" "$BASE" <<'PY'
import os, sys, json, hashlib
import numpy as np
sys.path.insert(0, "/dev/shm/fresh_2026-09-23/engine")
import bt_tables as BT, bt_driver_lib as DL
CELL, OUT, BASE = sys.argv[1:4]
def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda: f.read(1<<22), b""): h.update(b)
    return h.hexdigest()
tag = os.path.basename(CELL); P=[]
for k in range(32):
    s=f"{CELL}/PATH_{tag}_seed_{k:02d}"
    J=json.load(open(s+".json")); assert J["npz_sha256"]==sha(s+".npz")
    assert DL.audits_clean(J["audits"]) and int(J["seed"])==k
    P.append(BT.series_from_path(np.load(s+".npz")))
ax=P[0]["A"]
for p in P: assert np.array_equal(p["A"],ax)
np.savez_compressed(OUT, anchors=ax, price_bps=np.mean([p["pnl"] for p in P],axis=0),
                    daily_r=np.mean([p["r"] for p in P],axis=0),
                    g_bps=np.mean([p["g"] for p in P],axis=0) if "g" in P[0] else np.zeros(len(ax)))
print("SER_ORIG", BASE, sha(OUT)[:16], "anchors", len(ax), flush=True)
PY
SER=$FA/receipts/SER_ORIG_${BASE}.npz
if [ -s "$SER" ] && /workspace/venv/bin/python -c "import numpy,sys;numpy.load(sys.argv[1]);print('loadable')" "$SER"; then
  echo "[$TAG] verified -> freeing cell"; rm -rf "$CELL"
else echo "[$TAG] SERIES MISSING - KEEPING CELL"; exit 8; fi
df -h /dev/shm|tail -1
