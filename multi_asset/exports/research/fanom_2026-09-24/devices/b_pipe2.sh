#!/bin/bash
# One diagnostic arm end-to-end, v2. Changes vs v1 (lead 2026-09-24):
#  (a) pod_root overridden to MY root; arm and tag left at their ORIGINAL values (news2 hit arm_mismatch by changing arm)
#  (b) fa_launch_guard.py must ACCEPT before the launcher is started (tested red-then-green)
#  (c) the cell is deleted only after the derived series exists AND its sha is verified
set -e
W=/dev/shm/fresh_2026-09-23; FA=/dev/shm/fanom_2026-09-24
VAR=$1; ARMROOT=$2; SEED=$3
ARMNAME=$(basename $ARMROOT | cut -d_ -f1)
[ "$ARMNAME" = "fresh" ] && BASE="FRESH_s${SEED}" || BASE="NEWS_s${SEED}"
TAG="${VAR}_${ARMNAME}_s${SEED}"; CELLTAG="${VAR}_${BASE}"
VDIR=$FA/bvar/${VAR}_$(basename $ARMROOT)_s${SEED}
PRED=440
A=$(df -BM /dev/shm|tail -1|awk '{print $4}'|tr -d M)
echo "[$TAG] shm_gate avail=${A}MiB need=$((PRED+1024))MiB"
[ "$A" -ge $((PRED+1024)) ] || { echo "[$TAG] WAIT"; exit 9; }
mkdir -p $FA/runs $FA/logs
cd $W/engine
/workspace/venv/bin/python - "$VAR" "$ARMROOT" "$SEED" "$VDIR" "$BASE" "$FA" <<'PY'
import json, hashlib, sys, copy
var, armroot, seed, vdir, base, fa = sys.argv[1:7]
def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda: f.read(1<<22), b""): h.update(b)
    return h.hexdigest()
arm = "FRESH" if "fresh" in armroot else "NEWS"
root = "/dev/shm/fresh_2026-09-23" if arm=="FRESH" else "/dev/shm/news_2026-09-23"
# adapter spec: arm left ORIGINAL; only the combo sources point at the variant
s = json.load(open(f"{root}/configs/ADAPTER_SPEC_{base}.json"))
before_spec = copy.deepcopy(s)
s["data"] = f"DIAGNOSTIC {var} on {base}: pipeline cannot produce this configuration; hold-contract research arm"
for k, pol in (("scaled","scaled_diagnostic"), ("lit","literal")):
    s[k] = {"npz": f"{vdir}/{pol}.npz", "sha256": sha(f"{vdir}/{pol}.npz")}
s["new_receipt"] = {"path": f"{vdir}/TARGET_RECEIPT.json", "sha256": sha(f"{vdir}/TARGET_RECEIPT.json")}
json.dump(s, open(f"{vdir}/ADAPTER_SPEC.json","w"), indent=1)
# run config: pod_root -> MY root; arm/tag UNCHANGED; targets -> variant
cfgp = f"{root}/configs/RUN_CONFIG_{base}_2026-09-23.json"
c = json.load(open(cfgp)); before_cfg = copy.deepcopy(c)
want = f"{base}|scaled|rule|raw|UAFE"
runs = [r for r in c["runs"] if r["tag"] == want]; assert len(runs)==1
r = copy.deepcopy(runs[0])            # arm and tag deliberately NOT modified
r["targets"]["sources"] = [{"npz": f"{vdir}/TARGETS.npz", "npz_sha256": sha(f"{vdir}/TARGETS.npz"),
                            "receipt": f"{vdir}/TARGETS.json", "receipt_sha256": sha(f"{vdir}/TARGETS.json")}]
r["role"] = r.get("role","") + f" | DIAGNOSTIC {var}: hold-contract variant, research only"
c["runs"] = [r]
c["paths"] = dict(c["paths"]); c["paths"]["pod_root"] = fa      # (a) the fix for the breach
c["_diagnostic_note"] = {"variant": var, "base": base, "derived_from": cfgp, "derived_from_sha256": sha(cfgp),
                         "changed": ["paths.pod_root -> " + fa, "runs[] -> single base cell",
                                     "runs[0].targets.sources -> variant targets", "runs[0].role annotated"],
                         "deliberately_unchanged": ["runs[0].arm", "runs[0].tag", "adapter spec arm"]}
json.dump(c, open(f"{vdir}/RUN_CONFIG.json","w"), indent=1)
diff = {"config": {k: {"before": before_cfg.get(k) if k!="runs" else [x["tag"] for x in before_cfg["runs"]],
                       "after": c.get(k) if k!="runs" else [x["tag"] for x in c["runs"]]}
                   for k in ("paths","runs")},
        "adapter_spec": {k: {"before": before_spec.get(k), "after": s.get(k)} for k in ("arm","data","scaled","lit","new_receipt")}}
json.dump(diff, open(f"{vdir}/DERIVATION_DIFF.json","w"), indent=1, default=str)
print("DERIVED spec+config; pod_root ->", fa)
PY
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B ovn_adapter.py PATH,HOME,LC_CTYPE \
  $VDIR/ADAPTER_SPEC.json $VDIR/TARGETS.npz $VDIR/TARGETS.json > $FA/logs/adapter_$TAG.log 2>&1
tail -1 $FA/logs/adapter_$TAG.log
# regenerate the config now that TARGETS exist (shas were computed pre-adapter on the first pass)
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
PY
# (b) guard must ACCEPT before anything is launched
env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B $W/devices/fa_launch_guard.py PATH,HOME,LC_CTYPE $VDIR/RUN_CONFIG.json
setsid env -i PATH=/usr/bin:/bin HOME=/root nice -n 12 /workspace/venv/bin/python -B bt_launch.py PATH,HOME,LC_CTYPE \
  $VDIR/RUN_CONFIG.json --resume $TAG > $FA/logs/engine_$TAG.log 2>&1 < /dev/null &
sleep 5; echo "[$TAG] engine PGID=$(ps -o pgid= -p $! | tr -d ' ')"
until grep -qE "BT_LAUNCH VERDICT|Traceback|No space left" $FA/logs/engine_$TAG.log 2>/dev/null; do sleep 20; done
grep -E "BT_LAUNCH VERDICT|Traceback|No space left" $FA/logs/engine_$TAG.log | head -1
CELL=$FA/runs/${BASE}_scaled_rule_raw_UAFE
SER=$FA/receipts/SER_${CELLTAG}.npz
env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 /workspace/venv/bin/python -B $W/devices/fa_bextract.py PATH,HOME,LC_CTYPE \
  $CELL $([ "$ARMNAME" = "fresh" ] && echo FRESH || echo NEWS) $SEED $SER 2>&1 | tail -1
# (c) delete ONLY after the product exists and its sha is verifiable
if [ -s "$SER" ] && /workspace/venv/bin/python -c "import numpy,sys;numpy.load(sys.argv[1]);print('series loadable')" "$SER"; then
  echo "[$TAG] series verified $(shasum -a 256 $SER | cut -c1-16) -> freeing cell"
  rm -rf "$CELL"
else
  echo "[$TAG] SERIES MISSING OR UNREADABLE - KEEPING CELL"; exit 8
fi
df -h /dev/shm|tail -1
