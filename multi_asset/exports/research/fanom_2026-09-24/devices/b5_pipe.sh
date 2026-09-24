#!/bin/bash
# B5: targets already built by fa_b5transform.py (assertion-bound). Derive config -> guard -> engine -> extract -> gated delete.
set -e
W=/dev/shm/fresh_2026-09-23; FA=/dev/shm/fanom_2026-09-24
ARMROOT=$1; SEED=$2
ARMNAME=$(basename $ARMROOT | cut -d_ -f1)
[ "$ARMNAME" = "fresh" ] && BASE="FRESH_s${SEED}" || BASE="NEWS_s${SEED}"
TAG="B5_${ARMNAME}_s${SEED}"; CELLTAG="B5_${BASE}"
VDIR=$FA/bvar/B5T_$(basename $ARMROOT)_s${SEED}
A=$(df -BM /dev/shm|tail -1|awk '{print $4}'|tr -d M)
echo "[$TAG] shm_gate avail=${A}MiB need=1464MiB"; [ "$A" -ge 1464 ] || { echo "[$TAG] WAIT"; exit 9; }
mkdir -p $FA/runs $FA/logs; cd $W/engine
/workspace/venv/bin/python - "$ARMROOT" "$BASE" "$VDIR" "$FA" <<'PY'
import json, hashlib, sys, copy
armroot, base, vdir, fa = sys.argv[1:5]
def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda: f.read(1<<22), b""): h.update(b)
    return h.hexdigest()
cfgp = f"{armroot}/configs/RUN_CONFIG_{base}_2026-09-23.json"
c = json.load(open(cfgp)); want = f"{base}|scaled|rule|raw|UAFE"
runs = [r for r in c["runs"] if r["tag"] == want]; assert len(runs)==1
r = copy.deepcopy(runs[0])            # arm/tag UNCHANGED
r["targets"]["sources"] = [{"npz": f"{vdir}/TARGETS.npz", "npz_sha256": sha(f"{vdir}/TARGETS.npz"),
                            "receipt": f"{vdir}/TARGETS.json", "receipt_sha256": sha(f"{vdir}/TARGETS.json")}]
r["role"] = r.get("role","") + " | DIAGNOSTIC B5: flatten on gate failure, research only"
c["runs"] = [r]; c["paths"] = dict(c["paths"]); c["paths"]["pod_root"] = fa
c["_diagnostic_note"] = {"variant":"B5","base":base,"derived_from":cfgp,"derived_from_sha256":sha(cfgp),
  "changed":["paths.pod_root -> "+fa,"runs[] -> single base cell","runs[0].targets.sources -> B5 transformed targets"],
  "deliberately_unchanged":["runs[0].arm","runs[0].tag"],
  "named_deviation":"targets produced by fa_b5transform.py, which the adapter would refuse; see FA_B5TRANSFORM.json"}
json.dump(c, open(f"{vdir}/RUN_CONFIG.json","w"), indent=1); print("derived config")
PY
env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B $W/devices/fa_launch_guard.py PATH,HOME,LC_CTYPE $VDIR/RUN_CONFIG.json
setsid env -i PATH=/usr/bin:/bin HOME=/root nice -n 12 /workspace/venv/bin/python -B bt_launch.py PATH,HOME,LC_CTYPE \
  $VDIR/RUN_CONFIG.json --resume $TAG > $FA/logs/engine_$TAG.log 2>&1 < /dev/null &
sleep 5; echo "[$TAG] PGID=$(ps -o pgid= -p $! | tr -d ' ')"
until grep -qE "BT_LAUNCH VERDICT|Traceback|No space left" $FA/logs/engine_$TAG.log 2>/dev/null; do sleep 20; done
grep -E "BT_LAUNCH VERDICT|Traceback|No space left" $FA/logs/engine_$TAG.log | head -1
CELL=$FA/runs/${BASE}_scaled_rule_raw_UAFE; SER=$FA/receipts/SER_${CELLTAG}.npz
env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 /workspace/venv/bin/python -B $W/devices/fa_bextract.py PATH,HOME,LC_CTYPE \
  $CELL $([ "$ARMNAME" = "fresh" ] && echo FRESH || echo NEWS) $SEED $SER 2>&1 | tail -1
if [ -s "$SER" ] && /workspace/venv/bin/python -c "import numpy,sys;numpy.load(sys.argv[1])" "$SER"; then
  echo "[$TAG] series verified -> freeing cell"; rm -rf "$CELL"
else echo "[$TAG] SERIES MISSING - KEEPING CELL"; exit 8; fi
df -h /dev/shm|tail -1
