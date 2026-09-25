#!/bin/bash
# FX1/FX2/FX3: 08-30 FTRIM overlay, threshold on last_rate.
# STAGE 1 PROVISIONAL (PREREG_FX1_FX3_same_caliber_2026-09-25.md 修订 1): rate from the LOCAL ledger, NOT reconciled
# to exchange archives; member-level facts only, no family verdict. NC root is READ-ONLY.
# ★ Every per-run path carries ARM: the run TAG is deliberately unchanged across arms, so a shared pod_root would make
#   two arms write the SAME cell directory. Each arm therefore gets its own pod_root.
set -e
SEED=$1; ARM=$2
[ -n "$ARM" ] || { echo "usage: fx_pipe.sh <seed> <ARM>"; exit 2; }
W=/dev/shm/fresh_2026-09-23; FA=/dev/shm/fanom_2026-09-24; NC=/dev/shm/news2_2026-09-23
TAG="NEWS2_s${SEED}X"; VDIR=$FA/fx/${ARM}_s${SEED}; PODROOT=$VDIR/podroot
bash $W/devices/memgate.sh
mkdir -p $FA/logs $PODROOT/runs $PODROOT/receipts   # ★ receipts too: bt_launch.py L67 writes its own
# verdict receipt there and dies with FileNotFoundError if it is absent -- the run completes, the RECEIPT is lost.
/workspace/venv/bin/python -c "
import json,sys; d=json.load(open(sys.argv[1]))
assert d[\"arm\"]==sys.argv[2], (d[\"arm\"], sys.argv[2])
for m,v in d[\"modes\"].items():
    assert v[\"positive_control_gates_reproduce_kernel\"][\"trade_mask\"], m
    assert v[\"positive_control_gates_reproduce_kernel\"][\"reason\"], m
print(\"  FX combo OK (%s, device %s); gate re-eval reproduced kernel output on both policies\" % (d[\"arm\"], d[\"self_sha256\"][:16]))" $VDIR/FA_FX_RECEIPT.json $ARM
env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B $W/devices/fa_b8trcpt.py PATH,HOME,LC_CTYPE \
  $NC/work/combo_s${SEED} $VDIR 2>&1 | tail -1
cd $NC/engine
/workspace/venv/bin/python - "$NC" "$SEED" "$VDIR" "$PODROOT" "$ARM" <<"PY"
import json, hashlib, sys, copy
nc, seed, vdir, podroot, arm = sys.argv[1:6]
def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda: f.read(1<<22), b""): h.update(b)
    return h.hexdigest()
s = json.load(open(f"{nc}/configs/ADAPTER_SPEC_NEWS2_s{seed}.json"))
s["data"] = f"CANDIDATE {arm} (STAGE 1, PROVISIONAL rate source = local ledger last_rate): 08-30 FTRIM overlay"
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
r["role"] = r.get("role","") + f" | CANDIDATE {arm} stage 1: provisional rate source, member-level facts only"
c["runs"] = [r]; c["paths"] = dict(c["paths"]); c["paths"]["pod_root"] = podroot
c["_diagnostic_note"] = {"arm": arm, "derived_from": cfgp, "derived_from_sha256": sha(cfgp),
                         "changed": ["paths.pod_root -> per-arm "+podroot, f"runs[0].targets.sources -> {arm} targets",
                                     "runs[0].role annotated"],
                         "deliberately_unchanged": ["runs[0].arm","runs[0].tag","adapter spec arm"],
                         "why_per_arm_pod_root": "the run tag is identical across arms; a shared pod_root would collide"}
json.dump(c, open(f"{vdir}/RUN_CONFIG.json","w"), indent=1); print(f"  DERIVED {arm} config (extended axis, isolated pod_root)")
PY
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B ovn_adapter.py PATH,HOME,LC_CTYPE \
  $VDIR/ADAPTER_SPEC.json $VDIR/TARGETS.npz $VDIR/TARGETS.json > $FA/logs/fx_adapter_${ARM}_s${SEED}.log 2>&1
tail -1 $FA/logs/fx_adapter_${ARM}_s${SEED}.log | cut -c1-130
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
  $VDIR/RUN_CONFIG.json --resume fx_${ARM}_$SEED > $FA/logs/engine_fx_${ARM}_s${SEED}.log 2>&1 < /dev/null &
sleep 5; PG=$(ps -o pgid= -p $! | tr -d " ")
echo "{\"arm\":\"$ARM\",\"seed\":\"$SEED\",\"pgid\":\"$PG\",\"config\":\"$VDIR/RUN_CONFIG.json\",\"started_utc\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" > $FA/logs/PGID_fx_${ARM}_s${SEED}.json
echo "  engine PGID=$PG (recorded)"
# ★ The pattern is ANCHORED at line start. bt_launch's real verdict line begins with "BT_LAUNCH VERDICT=";
# a traceback frame QUOTING that source line is indented, so an unanchored pattern is satisfied by the CRASH --
# which is how six runs were reported complete while every one of them had died writing its receipt.
LOG=$FA/logs/engine_fx_${ARM}_s${SEED}.log
until grep -qE "^BT_LAUNCH VERDICT=|^Traceback|No space left" $LOG 2>/dev/null; do sleep 20; done
grep -E "^BT_LAUNCH VERDICT=|^Traceback|No space left" $LOG | head -1
if grep -qE "^Traceback|No space left" $LOG; then echo "  ENGINE FAILED (traceback or disk full) - not saving a series"; exit 9; fi
grep -qE "^BT_LAUNCH VERDICT=PASS" $LOG || { echo "  NO PASS VERDICT - refusing to proceed"; exit 9; }
CELL=$PODROOT/runs/${TAG}_scaled_rule_raw_UAFE
SER=$FA/receipts/SER_${ARM}_s${SEED}.npz
env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 /workspace/venv/bin/python -B $W/devices/fa_ladsave.py PATH,HOME,LC_CTYPE $CELL $SER 2>&1 | tail -1
if [ -s "$SER" ] && /workspace/venv/bin/python -c "import numpy,sys;numpy.load(sys.argv[1]);print(\"  series loadable\")" "$SER"; then
  rm -rf "$CELL"; echo "  freed $CELL"
  # ★ free THIS arm's combo too, but only here: we are past the ^BT_LAUNCH VERDICT=PASS gate and past the series
  # read-back, so this run will not need re-running. An EXTERNAL janitor gated only on "the series exists" deleted
  # these arrays while the series was from an UNVERIFIED run, and the re-run then had no inputs: a deletion gate
  # must cover every consumer of the data it destroys, and a re-run of the same arm is one of those consumers.
  rm -f "$VDIR"/scaled_diagnostic.npz "$VDIR"/literal.npz
  echo "  freed $VDIR combo arrays (regenerable by fa_fx.py; verified run, no re-run pending)"
else echo "  SERIES MISSING - KEEPING CELL"; exit 8; fi
