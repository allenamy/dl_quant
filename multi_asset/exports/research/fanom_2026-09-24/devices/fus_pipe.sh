#!/bin/bash
# One fusion arm on one family member, end to end. DECISION_RULE b0a3a96cb; new order C1 -> A3 -> A2 -> (B1/C2/B3) -> B2.
# usage: fus_pipe.sh <ARM> <MEMBER_ROOT> <SEED> <MEMBER_LABEL>
#   ARM=C1  -> B4 semantics (publish on gate failure), built by post-processing the member's combo (fa_bvariant.py)
# Member roots are READ-ONLY. Baseline cell is the member's own engine cell, never deleted.
set -e
W=/dev/shm/fresh_2026-09-23; FA=/dev/shm/fanom_2026-09-24
ARM=$1; MROOT=$2; SEED=$3; MLABEL=$4
case "$ARM" in
  C1) BASE_TAG="B4" ;;
  *) echo "[$ARM] no builder wired for this arm yet"; exit 6 ;;
esac
BASE="NEWS2_s${SEED}"
TAG="${ARM}_${MLABEL}"
VDIR=$FA/bvar/${ARM}_${MLABEL}
BCELL=$MROOT/runs/${BASE}_scaled_rule_raw_UAFE
BCOMBO=$MROOT/work/combo_s${SEED}
[ -d "$BCELL" ] || { echo "[$TAG] baseline cell missing: $BCELL"; exit 7; }
[ -d "$BCOMBO" ] || { echo "[$TAG] baseline combo missing: $BCOMBO"; exit 7; }
PRED=500
A=$(df -BM /dev/shm|tail -1|awk '{print $4}'|tr -d M)
echo "[$TAG] shm_gate avail=${A}MiB need=$((PRED+1024))MiB"
[ "$A" -ge $((PRED+1024)) ] || { echo "[$TAG] WAIT"; exit 9; }
mkdir -p $VDIR $FA/logs $FA/runs
# 1. build the variant combo by post-processing (evolve carries kc/fc/raw forward regardless of the gate decision)
env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B $W/devices/fa_bvariant.py PATH,HOME,LC_CTYPE \
  $MROOT $SEED $BASE_TAG $VDIR 2>&1 | tail -1
# 2. adapter spec + run config from the member's own, pod_root -> MY root, arm/tag UNCHANGED
cd $MROOT/engine
/workspace/venv/bin/python - "$MROOT" "$BASE" "$VDIR" "$FA" "$ARM" <<'PY'
import json, hashlib, sys, copy
mroot, base, vdir, fa, arm = sys.argv[1:6]
def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda: f.read(1<<22), b""): h.update(b)
    return h.hexdigest()
s = json.load(open(f"{mroot}/configs/ADAPTER_SPEC_{base}.json"))
s["data"] = f"DIAGNOSTIC {arm} on {base}: fusion-layer research arm; pipeline does not produce this configuration"
for k, pol in (("scaled","scaled_diagnostic"), ("lit","literal")):
    s[k] = {"npz": f"{vdir}/{pol}.npz", "sha256": sha(f"{vdir}/{pol}.npz")}
s["new_receipt"] = {"path": f"{vdir}/TARGET_RECEIPT.json", "sha256": sha(f"{vdir}/TARGET_RECEIPT.json")}
json.dump(s, open(f"{vdir}/ADAPTER_SPEC.json","w"), indent=1)
cfgp = f"{mroot}/configs/RUN_CONFIG_{base}_2026-09-23.json"
c = json.load(open(cfgp))
want = f"{base}|scaled|rule|raw|UAFE"
runs = [r for r in c["runs"] if r["tag"] == want]; assert len(runs)==1, [r["tag"] for r in c["runs"]]
r = copy.deepcopy(runs[0])
r["targets"]["sources"] = [{"npz": f"{vdir}/TARGETS.npz", "npz_sha256": "PENDING",
                            "receipt": f"{vdir}/TARGETS.json", "receipt_sha256": "PENDING"}]
r["role"] = r.get("role","") + f" | DIAGNOSTIC {arm}: fusion arm, research only"
c["runs"] = [r]
c["paths"] = dict(c["paths"]); c["paths"]["pod_root"] = fa
c["_diagnostic_note"] = {"arm": arm, "base": base, "derived_from": cfgp, "derived_from_sha256": sha(cfgp),
                         "changed": ["paths.pod_root -> "+fa, "runs[] -> single base cell",
                                     "runs[0].targets.sources -> variant targets", "runs[0].role annotated"],
                         "deliberately_unchanged": ["runs[0].arm", "runs[0].tag", "adapter spec arm"]}
json.dump(c, open(f"{vdir}/RUN_CONFIG.json","w"), indent=1)
print("DERIVED spec+config; pod_root ->", fa)
PY
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B ovn_adapter.py PATH,HOME,LC_CTYPE \
  $VDIR/ADAPTER_SPEC.json $VDIR/TARGETS.npz $VDIR/TARGETS.json > $FA/logs/adapter_$TAG.log 2>&1
tail -1 $FA/logs/adapter_$TAG.log
/workspace/venv/bin/python - "$VDIR" <<'PY'
import json, hashlib, sys
v = sys.argv[1]
def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda: f.read(1<<22), b""): h.update(b)
    return h.hexdigest()
c = json.load(open(f"{v}/RUN_CONFIG.json"))
c["runs"][0]["targets"]["sources"] = [{"npz": f"{v}/TARGETS.npz", "npz_sha256": sha(f"{v}/TARGETS.npz"),
                                       "receipt": f"{v}/TARGETS.json", "receipt_sha256": sha(f"{v}/TARGETS.json")}]
json.dump(c, open(f"{v}/RUN_CONFIG.json","w"), indent=1)
assert "PENDING" not in json.dumps(c), "PENDING placeholder survived into launch config"
print("targets shas filled; no PENDING survives")
PY
env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B $W/devices/fa_launch_guard.py PATH,HOME,LC_CTYPE $VDIR/RUN_CONFIG.json
setsid env -i PATH=/usr/bin:/bin HOME=/root nice -n 12 /workspace/venv/bin/python -B bt_launch.py PATH,HOME,LC_CTYPE \
  $VDIR/RUN_CONFIG.json --resume $TAG > $FA/logs/engine_$TAG.log 2>&1 < /dev/null &
sleep 5; echo "[$TAG] engine PGID=$(ps -o pgid= -p $! | tr -d ' ')"
until grep -qE "BT_LAUNCH VERDICT|Traceback|No space left" $FA/logs/engine_$TAG.log 2>/dev/null; do sleep 20; done
grep -E "BT_LAUNCH VERDICT|Traceback|No space left" $FA/logs/engine_$TAG.log | head -1
VCELL=$FA/runs/${BASE}_scaled_rule_raw_UAFE
OUTJ=$FA/receipts/FUS_${ARM}_${MLABEL}.json
env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 /workspace/venv/bin/python -B $W/devices/fa_fusread.py PATH,HOME,LC_CTYPE \
  $VCELL $BCELL $SEED $OUTJ $VDIR $BCOMBO $ARM $MLABEL 2>&1 | tail -22
if [ -s "$OUTJ" ] && /workspace/venv/bin/python -c "import json,sys;json.load(open(sys.argv[1]));print('readout loadable')" "$OUTJ"; then
  echo "[$TAG] readout verified -> freeing MY cell only (member baseline untouched)"
  rm -rf "$VCELL"
else
  echo "[$TAG] READOUT MISSING - KEEPING CELL"; exit 8
fi
df -h /dev/shm|tail -1
