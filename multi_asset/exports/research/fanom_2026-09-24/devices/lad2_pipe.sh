#!/bin/bash
# Ladder TWO ENDS re-run with the CLEAN RN8 (lead ruling 2026-09-26).
#   usage: lad2_pipe.sh <LEGS_ROOT> <F10_ROOT> <PREFIX> <DONOR_ROOT> <SWAP> <LABEL> <SEED>
# Why a new pipe rather than lad_pipe.sh: that one hardcodes NEW_S as the swap base (`arm` mode), so it cannot
# express the all_new end (FRESH base + clean RN8 donor). It also carries the unacted-on-Traceback defect fixed
# in the other four pipes. lad_pipe.sh is left untouched because archived ladder results cite it.
#
# Lead's confirmed definition: swap ONLY the RN8 array, on BOTH ends; `none` keeps the NEW_S root so the original
# G definition (FRESH vs NEW_S) is preserved -- the question is how far G moves once RN8 is corrected.
set -e
LEGS=$1; F10=$2; PREFIX=$3; DONOR=$4; SWAP=$5; LABEL=$6; SEED=$7
[ -n "$SEED" ] || { echo "usage: lad2_pipe.sh <LEGS_ROOT> <F10_ROOT> <PREFIX> <DONOR_ROOT> <SWAP> <LABEL> <SEED>"; exit 2; }
W=/dev/shm/fresh_2026-09-23; FA=/dev/shm/fanom_2026-09-24
TAG="${PREFIX}_s${SEED}X"; VDIR=$FA/ladder2/${LABEL}_s${SEED}; PODROOT=$VDIR/podroot
bash $W/devices/memgate.sh
mkdir -p $VDIR $PODROOT/runs $PODROOT/receipts $FA/logs
cd $W/devices
# 1. combo: the arm's own root, with ONLY the named array taken from the donor. fa_ladder asserts the swapped
#    array actually differs from the base one (non-vacuity) and that the legs<->F10 pairing is uncrossed.
env -i PATH=/usr/bin:/bin HOME=/root nice -n 12 /workspace/venv/bin/python -B fa_ladder.py PATH,HOME,LC_CTYPE \
  --legs-root $LEGS --f10-root $F10 --seed $SEED --donor-root $DONOR --swap $SWAP \
  --out $VDIR > $FA/logs/lad2_combo_${LABEL}_s${SEED}.log 2>&1
tail -1 $FA/logs/lad2_combo_${LABEL}_s${SEED}.log | cut -c1-170
# 2. TARGET_RECEIPT + combo-layer behavioural difference vs the arm's own base combo
env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B $W/devices/fa_b8trcpt.py PATH,HOME,LC_CTYPE \
  $LEGS/work/combo_s${SEED} $VDIR 2>&1 | tail -1
# 3. adapter spec + run config derived from the arm's OWN root; pod_root -> isolated per label+seed
cd $LEGS/engine
/workspace/venv/bin/python - "$LEGS" "$SEED" "$VDIR" "$PODROOT" "$PREFIX" "$LABEL" <<'PY'
import json, hashlib, sys, copy
root, seed, vdir, podroot, prefix, label = sys.argv[1:7]
def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda: f.read(1<<22), b""): h.update(b)
    return h.hexdigest()
s = json.load(open(f"{root}/configs/ADAPTER_SPEC_{prefix}_s{seed}.json"))
s["data"] = f"LADDER END {label}: only the RN8 array replaced from the clean NC legs (lead 2026-09-26)"
for k, pol in (("scaled","scaled_diagnostic"), ("lit","literal")):
    s[k] = {"npz": f"{vdir}/{pol}.npz", "sha256": sha(f"{vdir}/{pol}.npz")}
s["new_receipt"] = {"path": f"{vdir}/TARGET_RECEIPT.json", "sha256": sha(f"{vdir}/TARGET_RECEIPT.json")}
json.dump(s, open(f"{vdir}/ADAPTER_SPEC.json","w"), indent=1)
cfgp = f"{root}/configs/RUN_CONFIG_{prefix}_s{seed}X_2026-09-23.json"
c = json.load(open(cfgp))
want = f"{prefix}_s{seed}X|scaled|rule|raw|UAFE"
runs = [r for r in c["runs"] if r["tag"] == want]; assert len(runs)==1, [r["tag"] for r in c["runs"]]
r = copy.deepcopy(runs[0])
r["targets"]["sources"] = [{"npz": f"{vdir}/TARGETS.npz", "npz_sha256": "PENDING",
                            "receipt": f"{vdir}/TARGETS.json", "receipt_sha256": "PENDING"}]
r["role"] = r.get("role","") + f" | LADDER END {label}: clean-RN8 re-run"
c["runs"] = [r]; c["paths"] = dict(c["paths"]); c["paths"]["pod_root"] = podroot
c["_diagnostic_note"] = {"arm": label, "derived_from": cfgp, "derived_from_sha256": sha(cfgp),
                         "changed": ["paths.pod_root -> per-end "+podroot, "runs[0].targets.sources", "runs[0].role"],
                         "deliberately_unchanged": ["runs[0].arm","runs[0].tag","adapter spec arm"],
                         "why_per_end_pod_root": "both ends share a run tag shape; a shared pod_root would collide"}
json.dump(c, open(f"{vdir}/RUN_CONFIG.json","w"), indent=1); print(f"  DERIVED {label} config (extended axis, isolated pod_root)")
PY
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B ovn_adapter.py PATH,HOME,LC_CTYPE \
  $VDIR/ADAPTER_SPEC.json $VDIR/TARGETS.npz $VDIR/TARGETS.json > $FA/logs/lad2_adapter_${LABEL}_s${SEED}.log 2>&1
tail -1 $FA/logs/lad2_adapter_${LABEL}_s${SEED}.log | cut -c1-130
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
print("  targets shas filled")
PY
env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B $W/devices/fa_launch_guard.py PATH,HOME,LC_CTYPE $VDIR/RUN_CONFIG.json
setsid env -i PATH=/usr/bin:/bin HOME=/root nice -n 12 /workspace/venv/bin/python -B bt_launch.py PATH,HOME,LC_CTYPE \
  $VDIR/RUN_CONFIG.json --resume lad2_${LABEL}_$SEED > $FA/logs/engine_lad2_${LABEL}_s${SEED}.log 2>&1 < /dev/null &
sleep 5; PG=$(ps -o pgid= -p $! | tr -d " ")
echo "{\"arm\":\"$LABEL\",\"seed\":\"$SEED\",\"pgid\":\"$PG\",\"config\":\"$VDIR/RUN_CONFIG.json\",\"started_utc\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" > $FA/logs/PGID_lad2_${LABEL}_s${SEED}.json
echo "  engine PGID=$PG (recorded)"
# anchored at line start, and the failure branch ACTS (the defect that let six FX runs report success on a crash)
LOG=$FA/logs/engine_lad2_${LABEL}_s${SEED}.log
until grep -qE "^BT_LAUNCH VERDICT=|^Traceback|No space left" $LOG 2>/dev/null; do sleep 20; done
grep -E "^BT_LAUNCH VERDICT=|^Traceback|No space left" $LOG | head -1
if grep -qE "^Traceback|No space left" $LOG; then echo "  ENGINE FAILED - not saving a series"; exit 9; fi
grep -qE "^BT_LAUNCH VERDICT=PASS" $LOG || { echo "  NO PASS VERDICT - refusing to proceed"; exit 9; }
CELL=$PODROOT/runs/${TAG}_scaled_rule_raw_UAFE
SER=$FA/receipts/SER_LAD2_${LABEL}_s${SEED}.npz
env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 /workspace/venv/bin/python -B $W/devices/fa_ladsave.py PATH,HOME,LC_CTYPE $CELL $SER 2>&1 | tail -1
if [ -s "$SER" ] && /workspace/venv/bin/python -c "import numpy,sys;numpy.load(sys.argv[1]);print('  series loadable')" "$SER"; then
  rm -rf "$CELL"; echo "  freed $CELL"
  rm -f "$VDIR"/scaled_diagnostic.npz "$VDIR"/literal.npz
  echo "  freed $VDIR combo arrays (regenerable by fa_ladder.py; verified run)"
else echo "  SERIES MISSING - KEEPING CELL"; exit 8; fi
