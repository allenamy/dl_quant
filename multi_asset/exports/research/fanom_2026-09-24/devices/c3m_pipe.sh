#!/bin/bash
# C3m: C3 weights under the BASE publish decision. PREREG_C3m_exposure_vs_gate_2026-09-25.md (ebba4ece7).
# lead-approved as a DIAGNOSTIC arm: no verdict, not a family candidate. NC root is READ-ONLY.
# The combo is built beforehand by fa_c3m.py (which enforces the prereg S3 controls), so step 1 here only ASSERTS it.
set -e
W=/dev/shm/fresh_2026-09-23; FA=/dev/shm/fanom_2026-09-24; NC=/dev/shm/news2_2026-09-23
SEED=$1
TAG="NEWS2_s${SEED}X"; VDIR=$FA/c3m/C3m_s${SEED}
bash $W/devices/memgate.sh
mkdir -p $FA/logs $FA/runs
# 1. the combo must already exist AND have passed its own controls -- never rebuild it inside the launch path
/workspace/venv/bin/python -c "
import json,sys; d=json.load(open(sys.argv[1]))
assert d[\"all_controls_ok\"], d
print(\"  C3m combo controls OK (device %s)\" % d[\"self_sha256\"][:16])" $VDIR/FA_C3M_RECEIPT.json
# 2. TARGET_RECEIPT + an INDEPENDENT check of prereg control 1: vs the BASE, trade_mask must differ on 0 anchors
env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B $W/devices/fa_b8trcpt.py PATH,HOME,LC_CTYPE \
  $NC/work/combo_s${SEED} $VDIR 2>&1 | tail -1
/workspace/venv/bin/python -c "
import json,sys; d=json.load(open(sys.argv[1]+\"/FA_B8TRCPT_RECEIPT.json\"))
bad={k:v[\"anchors_with_trade_mask_differing\"] for k,v in d[\"policies\"].items() if v[\"anchors_with_trade_mask_differing\"]!=0}
assert not bad, \"prereg control 1 FAILED: publish decision differs from base on %s\" % bad
print(\"  control 1 re-verified independently: trade_mask identical to base on both policies\")" $VDIR
# 3. adapter + config derived from NC own, extended axis, pod_root -> MY root
cd $NC/engine
/workspace/venv/bin/python - "$NC" "$SEED" "$VDIR" "$FA" <<"PY"
import json, hashlib, sys, copy
nc, seed, vdir, fa = sys.argv[1:5]
def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda: f.read(1<<22), b""): h.update(b)
    return h.hexdigest()
s = json.load(open(f"{nc}/configs/ADAPTER_SPEC_NEWS2_s{seed}.json"))
s["data"] = "DIAGNOSTIC C3m: C3 weights under the BASE publish decision; isolates cut-exposure from gate-bites-less"
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
r["role"] = r.get("role","") + " | DIAGNOSTIC C3m: measuring instrument only, no verdict"
c["runs"] = [r]; c["paths"] = dict(c["paths"]); c["paths"]["pod_root"] = fa
c["_diagnostic_note"] = {"arm": "C3m", "derived_from": cfgp, "derived_from_sha256": sha(cfgp),
                         "changed": ["paths.pod_root -> "+fa, "runs[0].targets.sources -> C3m targets", "runs[0].role annotated"],
                         "deliberately_unchanged": ["runs[0].arm","runs[0].tag","adapter spec arm"],
                         "order_warning": "d(C3) != d(C3m) + d(pure gate effect); the split is order-dependent"}
json.dump(c, open(f"{vdir}/RUN_CONFIG.json","w"), indent=1); print("  DERIVED C3m config (extended axis)")
PY
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B ovn_adapter.py PATH,HOME,LC_CTYPE \
  $VDIR/ADAPTER_SPEC.json $VDIR/TARGETS.npz $VDIR/TARGETS.json > $FA/logs/c3m_adapter_s${SEED}.log 2>&1
tail -1 $FA/logs/c3m_adapter_s${SEED}.log | cut -c1-130
/workspace/venv/bin/python - "$VDIR" <<"PY"
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
print("  targets shas filled")
PY
env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B $W/devices/fa_launch_guard.py PATH,HOME,LC_CTYPE $VDIR/RUN_CONFIG.json
setsid env -i PATH=/usr/bin:/bin HOME=/root nice -n 12 /workspace/venv/bin/python -B bt_launch.py PATH,HOME,LC_CTYPE \
  $VDIR/RUN_CONFIG.json --resume c3m_$SEED > $FA/logs/engine_c3m_$SEED.log 2>&1 < /dev/null &
sleep 5; echo "  engine PGID=$(ps -o pgid= -p $! | tr -d \" \")"
until grep -qE "BT_LAUNCH VERDICT|Traceback|No space left" $FA/logs/engine_c3m_$SEED.log 2>/dev/null; do sleep 20; done
grep -E "BT_LAUNCH VERDICT|Traceback|No space left" $FA/logs/engine_c3m_$SEED.log | head -1
CELL=$FA/runs/${TAG}_scaled_rule_raw_UAFE
SER=$FA/receipts/SER_C3M_s${SEED}.npz
env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 /workspace/venv/bin/python -B $W/devices/fa_ladsave.py PATH,HOME,LC_CTYPE $CELL $SER 2>&1 | tail -1
if [ -s "$SER" ] && /workspace/venv/bin/python -c "import numpy,sys;numpy.load(sys.argv[1]);print(\"  series loadable\")" "$SER"; then
  rm -rf "$CELL"; echo "  freed $CELL"
else echo "  SERIES MISSING - KEEPING CELL"; exit 8; fi
