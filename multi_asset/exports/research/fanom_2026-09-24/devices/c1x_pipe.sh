#!/bin/bash
# C1 re-run on the EXTENDED axis (lead 2026-09-25): B4 semantics -- publish the book when the preflight gate fails.
# DECISION_RULE b0a3a96cb + revision 2 (8d2cc5546, extended axis). The short-axis reading (FUS_C1_*) is archive only.. Criteria = frozen family gate b0a3a96cb; NO VERDICT
# until n >= 8. NC root is READ-ONLY.
set -e
W=/dev/shm/fresh_2026-09-23; FA=/dev/shm/fanom_2026-09-24; NC=/dev/shm/news2_2026-09-23
SEED=$1
TAG="NEWS2_s${SEED}X"; VDIR=$FA/c1x/C1X_s${SEED}
bash $W/devices/memgate.sh
mkdir -p $VDIR $FA/logs $FA/runs
# 1. variant combo by POST-PROCESSING (evolve carries kc/fc/raw forward regardless of the gate decision)
env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B $W/devices/fa_bvariant.py PATH,HOME,LC_CTYPE \
  $NC $SEED B4 $VDIR > $FA/logs/c1x_combo_s${SEED}.log 2>&1
tail -1 $FA/logs/c1x_combo_s${SEED}.log | cut -c1-150
# 2. variant TARGET_RECEIPT + combo-layer behavioural difference
env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B $W/devices/fa_b8trcpt.py PATH,HOME,LC_CTYPE \
  $NC/work/combo_s${SEED} $VDIR 2>&1 | tail -1
# 3. adapter + config from NC's own, extended axis, pod_root -> MY root
cd $NC/engine
/workspace/venv/bin/python - "$NC" "$SEED" "$VDIR" "$FA" <<'PY'
import json, hashlib, sys, copy
nc, seed, vdir, fa = sys.argv[1:5]
def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda: f.read(1<<22), b""): h.update(b)
    return h.hexdigest()
s = json.load(open(f"{nc}/configs/ADAPTER_SPEC_NEWS2_s{seed}.json"))
s["data"] = "DIAGNOSTIC C1 (B4): publish on gate failure; a configuration the pipeline cannot produce; research arm"
for k, pol in (("scaled","scaled_diagnostic"), ("lit","literal")):
    s[k] = {"npz": f"{vdir}/{pol}.npz", "sha256": sha(f"{vdir}/{pol}.npz")}
s["new_receipt"] = {"path": f"{vdir}/TARGET_RECEIPT.json", "sha256": sha(f"{vdir}/TARGET_RECEIPT.json")}
json.dump(s, open(f"{vdir}/ADAPTER_SPEC.json","w"), indent=1)
cfgp = f"{nc}/configs/RUN_CONFIG_NEWS2_s{seed}X_2026-09-23.json"
c = json.load(open(cfgp))
want = f"NEWS2_s{seed}X|scaled|rule|raw|UAFE"
runs = [r for r in c["runs"] if r["tag"] == want]; assert len(runs)==1, [r["tag"] for r in c["runs"]]
r = copy.deepcopy(runs[0])
r["targets"]["sources"] = [{"npz": f"{vdir}/TARGETS.npz", "npz_sha256": "PENDING",
                            "receipt": f"{vdir}/TARGETS.json", "receipt_sha256": "PENDING"}]
r["role"] = r.get("role","") + " | DIAGNOSTIC C1: measuring instrument only"
c["runs"] = [r]; c["paths"] = dict(c["paths"]); c["paths"]["pod_root"] = fa
c["_diagnostic_note"] = {"arm": "C1X", "derived_from": cfgp, "derived_from_sha256": sha(cfgp),
                         "changed": ["paths.pod_root -> "+fa, "runs[0].targets.sources -> C3 targets", "runs[0].role annotated"],
                         "deliberately_unchanged": ["runs[0].arm","runs[0].tag","adapter spec arm"]}
json.dump(c, open(f"{vdir}/RUN_CONFIG.json","w"), indent=1); print("DERIVED C1X config (extended axis)")
PY
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B ovn_adapter.py PATH,HOME,LC_CTYPE \
  $VDIR/ADAPTER_SPEC.json $VDIR/TARGETS.npz $VDIR/TARGETS.json > $FA/logs/c1x_adapter_s${SEED}.log 2>&1
tail -1 $FA/logs/c1x_adapter_s${SEED}.log | cut -c1-130
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
assert "PENDING" not in json.dumps(c), "PENDING survived into launch config"
print("targets shas filled")
PY
env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B $W/devices/fa_launch_guard.py PATH,HOME,LC_CTYPE $VDIR/RUN_CONFIG.json
setsid env -i PATH=/usr/bin:/bin HOME=/root nice -n 12 /workspace/venv/bin/python -B bt_launch.py PATH,HOME,LC_CTYPE \
  $VDIR/RUN_CONFIG.json --resume c1x_$SEED > $FA/logs/engine_c1x_$SEED.log 2>&1 < /dev/null &
sleep 5; echo "  engine PGID=$(ps -o pgid= -p $! | tr -d ' ')"
# ★ The detection set included "Traceback" but NOTHING ACTED ON IT: the loop stopped waiting on a crash and the
# pipe then proceeded to save a series anyway. Detection that binds no action is decoration -- six FX runs were
# reported complete on 2026-09-25 while every one had died writing its receipt. Anchored at line start too, so a
# traceback frame quoting the verdict source line cannot be mistaken for the verdict.
LOG=$FA/logs/engine_c1x_$SEED.log
until grep -qE "^BT_LAUNCH VERDICT=|^Traceback|No space left" $LOG 2>/dev/null; do sleep 20; done
grep -E "^BT_LAUNCH VERDICT=|^Traceback|No space left" $LOG | head -1
if grep -qE "^Traceback|No space left" $LOG; then echo "  ENGINE FAILED - not saving a series"; exit 9; fi
grep -qE "^BT_LAUNCH VERDICT=PASS" $LOG || { echo "  NO PASS VERDICT - refusing to proceed"; exit 9; }
CELL=$FA/runs/${TAG}_scaled_rule_raw_UAFE
SER=$FA/receipts/SER_C1X_s${SEED}.npz
env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 /workspace/venv/bin/python -B $W/devices/fa_ladsave.py PATH,HOME,LC_CTYPE $CELL $SER 2>&1 | tail -1
if [ -s "$SER" ] && /workspace/venv/bin/python -c "import numpy,sys;numpy.load(sys.argv[1]);print('  series loadable')" "$SER"; then
  rm -rf "$CELL"; echo "  freed $CELL"
else echo "  SERIES MISSING - KEEPING CELL"; exit 8; fi
