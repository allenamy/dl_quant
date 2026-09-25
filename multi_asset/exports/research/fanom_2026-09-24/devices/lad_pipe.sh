#!/bin/bash
# FRESH gap-carrier ladder, one cell. PREREG_fresh_gap_carrier_ladder_2026-09-25.md + amendment 1 (a9a5fe8a5).
# usage: lad_pipe.sh baseline <ROOT> <PREFIX> <SEED>          re-run an existing X config into MY root
#        lad_pipe.sh arm      <SWAPLIST> <LABEL> <SEED>       swap donor arrays into NEW_S, then adapter -> engine
# Extended axis throughout (X configs, last anchor 2026-09-18 20:00Z). Donor roots are READ-ONLY.
set -e
W=/dev/shm/fresh_2026-09-23; FA=/dev/shm/fanom_2026-09-24
N=/dev/shm/news_2026-09-23; F=/dev/shm/fresh_2026-09-23
MODE=$1
bash $W/devices/memgate.sh 3000
mkdir -p $FA/logs $FA/runs $FA/ladder

if [ "$MODE" = "baseline" ]; then
  ROOT=$2; PREFIX=$3; SEED=$4
  TAG="${PREFIX}_s${SEED}X"; VDIR=$FA/ladder/BASE_${TAG}
  mkdir -p $VDIR
  # The X config pins its targets npz by sha. If that file was deleted (FRESH's were), regenerate it with the arm's
  # own adapter spec and ASSERT the regenerated sha equals the pinned one -- a bitwise reproduction of the targets,
  # which is a stronger statement than "a file with the right name exists".
  PINNED_NPZ=$(/workspace/venv/bin/python -c "
import json,sys
c=json.load(open('$ROOT/configs/RUN_CONFIG_${PREFIX}_s${SEED}X_2026-09-23.json'))
r=[x for x in c['runs'] if x['tag']=='${PREFIX}_s${SEED}X|scaled|rule|raw|UAFE'][0]
print(r['targets']['sources'][0]['npz'])")
  PINNED_SHA=$(/workspace/venv/bin/python -c "
import json,sys
c=json.load(open('$ROOT/configs/RUN_CONFIG_${PREFIX}_s${SEED}X_2026-09-23.json'))
r=[x for x in c['runs'] if x['tag']=='${PREFIX}_s${SEED}X|scaled|rule|raw|UAFE'][0]
print(r['targets']['sources'][0]['npz_sha256'])")
  if [ ! -s "$PINNED_NPZ" ]; then
    echo "  targets missing ($PINNED_NPZ) -> regenerating into MY root and checking against the pinned sha"
    cd $ROOT/engine
    env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B ovn_adapter.py PATH,HOME,LC_CTYPE \
      $ROOT/configs/ADAPTER_SPEC_${PREFIX}_s${SEED}.json $VDIR/TARGETS.npz $VDIR/TARGETS.json \
      > $FA/logs/lad_adapter_BASE_${PREFIX}_${SEED}.log 2>&1
    tail -1 $FA/logs/lad_adapter_BASE_${PREFIX}_${SEED}.log | cut -c1-140
    GOT=$(sha256sum $VDIR/TARGETS.npz | cut -d" " -f1)
    echo "  regenerated targets sha: $GOT"
    echo "  config pinned sha      : $PINNED_SHA"
    [ "$GOT" = "$PINNED_SHA" ] || { echo "  TARGETS DO NOT REPRODUCE THE PINNED SHA -> refusing to run"; exit 8; }
    echo "  targets reproduce the pinned sha BITWISE"
    REGEN=1
  fi
  cd $ROOT/engine
  /workspace/venv/bin/python - "$ROOT" "$PREFIX" "$SEED" "$VDIR" "$FA" <<'PY'
import json, hashlib, sys, copy
root, prefix, seed, vdir, fa = sys.argv[1:6]
def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda: f.read(1<<22), b""): h.update(b)
    return h.hexdigest()
cfgp = f"{root}/configs/RUN_CONFIG_{prefix}_s{seed}X_2026-09-23.json"
c = json.load(open(cfgp))
want = f"{prefix}_s{seed}X|scaled|rule|raw|UAFE"
runs = [r for r in c["runs"] if r["tag"] == want]; assert len(runs)==1, [r["tag"] for r in c["runs"]]
r0 = copy.deepcopy(runs[0])
import os
mine = f"{vdir}/TARGETS.npz"
if os.path.exists(mine):
    r0["targets"]["sources"] = [{"npz": mine, "npz_sha256": sha(mine),
                                 "receipt": f"{vdir}/TARGETS.json", "receipt_sha256": sha(f"{vdir}/TARGETS.json")}]
c["runs"] = [r0]
c["paths"] = dict(c["paths"]); c["paths"]["pod_root"] = fa
c["_diagnostic_note"] = {"purpose": "ladder baseline on the extended axis", "derived_from": cfgp,
                         "derived_from_sha256": sha(cfgp), "changed": ["paths.pod_root -> "+fa],
                         "deliberately_unchanged": ["runs[0].arm","runs[0].tag","runs[0].targets"]}
json.dump(c, open(f"{vdir}/RUN_CONFIG.json","w"), indent=1); print("DERIVED baseline config", want)
PY
else
  SWAP=$2; LABEL=$3; SEED=$4
  TAG="NEWS_s${SEED}X"; VDIR=$FA/ladder/${LABEL}_s${SEED}
  mkdir -p $VDIR
  cd $W/devices
  env -i PATH=/usr/bin:/bin HOME=/root nice -n 12 /workspace/venv/bin/python -B fa_ladder.py PATH,HOME,LC_CTYPE \
    --legs-root $N --f10-root $N --seed $SEED --donor-root $F --swap $SWAP --allow-crossed \
    --out $VDIR > $FA/logs/lad_combo_${LABEL}_s${SEED}.log 2>&1
  tail -1 $FA/logs/lad_combo_${LABEL}_s${SEED}.log | cut -c1-160
  cd $N/engine
  /workspace/venv/bin/python - "$N" "$SEED" "$VDIR" "$FA" "$LABEL" <<'PY'
import json, hashlib, sys, copy
n, seed, vdir, fa, label = sys.argv[1:6]
def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda: f.read(1<<22), b""): h.update(b)
    return h.hexdigest()
s = json.load(open(f"{n}/configs/ADAPTER_SPEC_NEWS_s{seed}.json"))
s["data"] = f"DIAGNOSTIC ladder {label}: donor arrays swapped in at the combo layer; a configuration the pipeline cannot produce"
for k, pol in (("scaled","scaled_diagnostic"), ("lit","literal")):
    s[k] = {"npz": f"{vdir}/{pol}.npz", "sha256": sha(f"{vdir}/{pol}.npz")}
s["new_receipt"] = {"path": f"{vdir}/TARGET_RECEIPT.json", "sha256": sha(f"{vdir}/TARGET_RECEIPT.json")}
json.dump(s, open(f"{vdir}/ADAPTER_SPEC.json","w"), indent=1)
cfgp = f"{n}/configs/RUN_CONFIG_NEWS_s{seed}X_2026-09-23.json"
c = json.load(open(cfgp))
want = f"NEWS_s{seed}X|scaled|rule|raw|UAFE"
runs = [r for r in c["runs"] if r["tag"] == want]; assert len(runs)==1, [r["tag"] for r in c["runs"]]
r = copy.deepcopy(runs[0])
r["targets"]["sources"] = [{"npz": f"{vdir}/TARGETS.npz", "npz_sha256": "PENDING",
                            "receipt": f"{vdir}/TARGETS.json", "receipt_sha256": "PENDING"}]
r["role"] = r.get("role","") + f" | DIAGNOSTIC ladder {label}: measuring instrument only"
c["runs"] = [r]; c["paths"] = dict(c["paths"]); c["paths"]["pod_root"] = fa
c["_diagnostic_note"] = {"ladder_arm": label, "derived_from": cfgp, "derived_from_sha256": sha(cfgp),
                         "changed": ["paths.pod_root -> "+fa, "runs[0].targets.sources -> arm targets", "runs[0].role annotated"],
                         "deliberately_unchanged": ["runs[0].arm","runs[0].tag","adapter spec arm"]}
json.dump(c, open(f"{vdir}/RUN_CONFIG.json","w"), indent=1); print("DERIVED arm config", label)
PY
  env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B ovn_adapter.py PATH,HOME,LC_CTYPE \
    $VDIR/ADAPTER_SPEC.json $VDIR/TARGETS.npz $VDIR/TARGETS.json > $FA/logs/lad_adapter_${LABEL}_s${SEED}.log 2>&1
  tail -1 $FA/logs/lad_adapter_${LABEL}_s${SEED}.log | cut -c1-140
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
print("targets shas filled")
PY
fi
VDIR=$(ls -d $FA/ladder/* | grep -E "/(BASE_${2}_s${4}X|${3}_s${4})$" | head -1)
[ -n "$VDIR" ] || VDIR=$([ "$MODE" = "baseline" ] && echo "$FA/ladder/BASE_${3}_s${4}X" || echo "$FA/ladder/${3}_s${4}")
env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B $W/devices/fa_launch_guard.py PATH,HOME,LC_CTYPE $VDIR/RUN_CONFIG.json
RTAG=$([ "$MODE" = "baseline" ] && echo "${3}_s${4}X" || echo "NEWS_s${4}X")
cd $([ "$MODE" = "baseline" ] && echo "$2/engine" || echo "$N/engine")
setsid env -i PATH=/usr/bin:/bin HOME=/root nice -n 12 /workspace/venv/bin/python -B bt_launch.py PATH,HOME,LC_CTYPE \
  $VDIR/RUN_CONFIG.json --resume lad_$3_$4 > $FA/logs/engine_lad_$3_$4.log 2>&1 < /dev/null &
sleep 5; echo "  engine PGID=$(ps -o pgid= -p $! | tr -d ' ')"
until grep -qE "BT_LAUNCH VERDICT|Traceback|No space left" $FA/logs/engine_lad_$3_$4.log 2>/dev/null; do sleep 20; done
grep -E "BT_LAUNCH VERDICT|Traceback|No space left" $FA/logs/engine_lad_$3_$4.log | head -1
CELL=$FA/runs/${RTAG}_scaled_rule_raw_UAFE
SER=$FA/receipts/SER_LAD_$3_s$4.npz
# save the complete per-path series, THEN free the cell. Cells are ~0.44 GiB each; without this the queue starves
# itself on the run gate's own /dev/shm floor (observed after the first two baselines).
env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 /workspace/venv/bin/python -B $W/devices/fa_ladsave.py PATH,HOME,LC_CTYPE \
  $CELL $SER 2>&1 | tail -1
if [ -s "$SER" ] && /workspace/venv/bin/python -c "import numpy,sys;numpy.load(sys.argv[1]);print('  series loadable')" "$SER"; then
  rm -rf "$CELL"; echo "  freed $CELL"
else
  echo "  SERIES MISSING - KEEPING CELL"; exit 8
fi
df -BM /dev/shm | tail -1
