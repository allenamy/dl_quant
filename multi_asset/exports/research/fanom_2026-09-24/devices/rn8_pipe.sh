#!/bin/bash
# rn8: NC book with the funding clamp disabled (all-NaN rn8) -> adapter -> guard -> engine -> canonical readout.
# PREREG docs/PREREG_step1_rn8_clamp_2026-09-25.md + AMENDMENT 1 (64f0ebb27).
# news2 root is READ-ONLY: its baseline cell is read for the paired dbar and is NEVER deleted.
set -e
W=/dev/shm/fresh_2026-09-23; FA=/dev/shm/fanom_2026-09-24
NC=/dev/shm/news2_2026-09-23
SEED=$1
BASE="NEWS2_s${SEED}"; VAR="RN8NC"; TAG="${VAR}_s${SEED}"
VDIR=$FA/bvar/${VAR}_$(basename $NC)_s${SEED}
BCELL=$NC/runs/${BASE}_scaled_rule_raw_UAFE
[ -d "$BCELL" ] || { echo "[$TAG] baseline cell missing: $BCELL"; exit 7; }
PRED=500
A=$(df -BM /dev/shm|tail -1|awk '{print $4}'|tr -d M)
echo "[$TAG] shm_gate avail=${A}MiB need=$((PRED+1024))MiB"
[ "$A" -ge $((PRED+1024)) ] || { echo "[$TAG] WAIT"; exit 9; }
mkdir -p $VDIR $FA/logs $FA/runs
# 1. combo with the clamp disabled, real members from NC's own panel
env -i PATH=/usr/bin:/bin HOME=/root nice -n 12 /workspace/venv/bin/python -B $W/devices/fa_rn8combo.py PATH,HOME,LC_CTYPE \
  --legs-root $NC --f10-root $NC --seed $SEED --panel $NC/work/NEWS_FEATURES.npz \
  --out $VDIR --no-rn8-clamp > $FA/logs/combo_$TAG.log 2>&1
tail -1 $FA/logs/combo_$TAG.log
# 2. variant target receipt + combo-level behavioural difference
env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B $W/devices/fa_b8trcpt.py PATH,HOME,LC_CTYPE \
  $NC/work/combo_s${SEED} $VDIR 2>&1 | tail -1
# 3. adapter spec + run config derived from NC's own, pod_root -> MY root, arm/tag UNCHANGED
cd $NC/engine
/workspace/venv/bin/python - "$NC" "$BASE" "$VDIR" "$FA" <<'PY'
import json, hashlib, sys, copy
nc, base, vdir, fa = sys.argv[1:5]
def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda: f.read(1<<22), b""): h.update(b)
    return h.hexdigest()
s = json.load(open(f"{nc}/configs/ADAPTER_SPEC_{base}.json")); before_s = copy.deepcopy(s)
s["data"] = f"DIAGNOSTIC RN8NC on {base}: funding clamp (combo_target L33-34) disabled via all-NaN rn8; research arm"
for k, pol in (("scaled","scaled_diagnostic"), ("lit","literal")):
    s[k] = {"npz": f"{vdir}/{pol}.npz", "sha256": sha(f"{vdir}/{pol}.npz")}
s["new_receipt"] = {"path": f"{vdir}/TARGET_RECEIPT.json", "sha256": sha(f"{vdir}/TARGET_RECEIPT.json")}
json.dump(s, open(f"{vdir}/ADAPTER_SPEC.json","w"), indent=1)
cfgp = f"{nc}/configs/RUN_CONFIG_{base}_2026-09-23.json"
c = json.load(open(cfgp)); before_c = copy.deepcopy(c)
want = f"{base}|scaled|rule|raw|UAFE"
runs = [r for r in c["runs"] if r["tag"] == want]; assert len(runs)==1, [r["tag"] for r in c["runs"]]
r = copy.deepcopy(runs[0])
r["targets"]["sources"] = [{"npz": f"{vdir}/TARGETS.npz", "npz_sha256": "PENDING",
                            "receipt": f"{vdir}/TARGETS.json", "receipt_sha256": "PENDING"}]
r["role"] = r.get("role","") + " | DIAGNOSTIC RN8NC: funding clamp disabled, research only"
c["runs"] = [r]
c["paths"] = dict(c["paths"]); c["paths"]["pod_root"] = fa
c["_diagnostic_note"] = {"variant": "RN8NC", "base": base, "derived_from": cfgp, "derived_from_sha256": sha(cfgp),
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
bad=[x for x in json.dumps(c).split('"') if x=="PENDING"]
assert not bad, "PENDING placeholder survived into launch config"
print("targets shas filled; no PENDING survives")
PY
env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B $W/devices/fa_launch_guard.py PATH,HOME,LC_CTYPE $VDIR/RUN_CONFIG.json
setsid env -i PATH=/usr/bin:/bin HOME=/root nice -n 12 /workspace/venv/bin/python -B bt_launch.py PATH,HOME,LC_CTYPE \
  $VDIR/RUN_CONFIG.json --resume $TAG > $FA/logs/engine_$TAG.log 2>&1 < /dev/null &
sleep 5; echo "[$TAG] engine PGID=$(ps -o pgid= -p $! | tr -d ' ')"
until grep -qE "BT_LAUNCH VERDICT|Traceback|No space left" $FA/logs/engine_$TAG.log 2>/dev/null; do sleep 20; done
grep -E "BT_LAUNCH VERDICT|Traceback|No space left" $FA/logs/engine_$TAG.log | head -1
VCELL=$FA/runs/${BASE}_scaled_rule_raw_UAFE
OUTJ=$FA/receipts/FA_RN8_READ_s${SEED}.json
env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 /workspace/venv/bin/python -B $W/devices/fa_rn8read.py PATH,HOME,LC_CTYPE \
  $VCELL $BCELL $SEED $OUTJ 2>&1 | tail -6
if [ -s "$OUTJ" ] && /workspace/venv/bin/python -c "import json,sys;json.load(open(sys.argv[1]));print('readout loadable')" "$OUTJ"; then
  echo "[$TAG] readout verified -> freeing MY cell only (news2 baseline untouched)"
  rm -rf "$VCELL"
else
  echo "[$TAG] READOUT MISSING - KEEPING CELL"; exit 8
fi
df -h /dev/shm|tail -1
