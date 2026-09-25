#!/usr/bin/env bash
# ladder_engine_arm.sh <ARM>  -- step 3: one ladder arm's combo output through adapter -> engine base
# cell -> dbar. Pre-registration: docs/PREREG_gap_carrier_ladder_2026-09-25.md (be4a013a8), step 3.
#
# The arm's combo npz files are already built by pnoise_ladder_combo.py. This script reuses the
# EXACT adapter/config/engine path steps 0-2 used (pnoise_run_from_king.sh L56-87) -- no new code
# path -- by placing the arm's two policy files where news2_adapter_specs.py looks for them
# ($EXP/work/combo_s42) together with a TARGET_RECEIPT.json carrying their real shas.
#
# Every arm is a pipeline-unproducible combination and only a measuring instrument, never a
# deployable version. Any non-zero rc stops (lead: 任一次失败就停下报告, 不自动重试).
set -uo pipefail
ARM="${1:?usage: ladder_engine_arm.sh <ARM>}"
EXP=/dev/shm/pnoise_2026-09-24
SRC=/dev/shm/news2_2026-09-23
D=$EXP/devices; E=$EXP/engine; L=$EXP/logs; W=$EXP
PV=/workspace/venv/bin/python
TAGD=NEWS2_s42_scaled_rule_raw_UAFE
NCRUN=$SRC/runs/$TAGD
say() { echo "$(date -u +%H:%M:%S) [eng:$ARM] $*" | tee -a $L/step3_engine.log; }

LAD=$EXP/work/ladder_$ARM
[ -s $LAD/literal.npz ] && [ -s $LAD/scaled_diagnostic.npz ] || { say "FATAL: arm combo missing"; exit 2; }

# measured disk gate before the engine, never assumed
AVAIL=$(df -k /dev/shm | tail -1 | awk '{print $4}')
say "df /dev/shm avail=${AVAIL}K"
if [ "$AVAIL" -lt 1509376 ]; then say "STOP: need engine room + 1.0 GiB margin, only ${AVAIL}K"; exit 3; fi

say "stage arm combo into work/combo_s42"
rm -rf $EXP/work/combo_s42
mkdir -p $EXP/work/combo_s42
cp -a $LAD/literal.npz $LAD/scaled_diagnostic.npz $EXP/work/combo_s42/
$PV - "$ARM" <<'PY' >> $L/step3_engine.log 2>&1 || { say "RECEIPT BUILD FAILED"; exit 1; }
import hashlib, json, sys
arm = sys.argv[1]
EXP = "/dev/shm/pnoise_2026-09-24"
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()
lad = json.load(open(f"{EXP}/receipts/LADDER_{arm}.json"))
out = {}
for pol in ("literal", "scaled_diagnostic"):
    p = f"{EXP}/work/combo_s42/{pol}.npz"
    got = sha(p)
    # the staged copy must be the very file the ladder device wrote
    assert got == lad["policies"][pol]["sha"], ("staged file is not the arm's combo output", pol, got)
    out[pol] = {"path": p, "sha": got, "reasons": lad["policies"][pol]["reasons"],
                "years": lad["policies"][pol]["years"]}
rec = {"status": "LADDER_ARM_PIPELINE_UNPRODUCIBLE_COMBINATION_MEASURING_INSTRUMENT_ONLY",
       "seed": 42, "arm": arm, "substituted": lad["substituted"],
       "state_init": "zero at 2023-01-01; hypothetical common start, not live archived state",
       "hold_contract": "trade_mask False = maintain quantities, never King substitution",
       "policies": out,
       "ladder_receipt": {"path": f"{EXP}/receipts/LADDER_{arm}.json",
                          "sha256": sha(f"{EXP}/receipts/LADDER_{arm}.json")},
       "combo_code": lad["combo_code"],
       "limits": ["NOT a deployable version and NOT a producer parity replay: this is one array swapped "
                  "between two books, a measuring instrument only",
                  "arms are NOT additive",
                  "no execution/cash or policy-stop result",
                  "scaled_diagnostic changes historical publication gate; never current-live literal"]}
json.dump(rec, open(f"{EXP}/work/combo_s42/TARGET_RECEIPT.json", "w"), indent=1, allow_nan=False)
print("arm", arm, "TARGET_RECEIPT staged; shas verified against the ladder receipt")
PY
say "staged"

rm -rf $EXP/runs/* $EXP/targets/*
rm -f $EXP/configs/ADAPTER_SPEC_NEWS2_s42.json $EXP/configs/RUN_CONFIG_PNOISE.json

say "adapter"
env -i PATH=/usr/bin:/bin HOME=/root $PV -B $D/news2_adapter_specs.py PATH,HOME,LC_CTYPE $W \
  > $L/adapter_specs_ladder_$ARM.log 2>&1 || { say "SPECS FAILED"; exit 1; }
cd $E
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $PV -B ovn_adapter.py PATH,HOME,LC_CTYPE \
  $W/configs/ADAPTER_SPEC_NEWS2_s42.json $W/targets/TARGETS_NEWS2_s42.npz \
  $W/targets/TARGETS_NEWS2_s42.json > $L/adapter_ladder_$ARM.log 2>&1 || { say "ADAPTER FAILED"; exit 1; }
say "adapter done TARGET_SHA=$(sha256sum $W/targets/TARGETS_NEWS2_s42.npz | cut -d' ' -f1 | cut -c1-16)"

say "config"
$PV - <<'PY' >> $L/step3_engine.log 2>&1 || { say "CONFIG FAILED"; exit 1; }
import json, hashlib
SRC="/dev/shm/news2_2026-09-23"; EXP="/dev/shm/pnoise_2026-09-24"
src=json.load(open(f"{SRC}/configs/RUN_CONFIG_NEWS2_s42_2026-09-23.json"))
npz=f"{EXP}/targets/TARGETS_NEWS2_s42.npz"; rj=npz.replace(".npz",".json")
h=hashlib.sha256(open(npz,"rb").read()).hexdigest(); rh=hashlib.sha256(open(rj,"rb").read()).hexdigest()
base=src["runs"][0]
assert base["tag"]=="NEWS2_s42|scaled|rule|raw|UAFE", base["tag"]
for x in base["targets"]["sources"]:
    x["npz"]=npz; x["npz_sha256"]=h; x["receipt"]=rj; x["receipt_sha256"]=rh
src["runs"]=[base]; src["paths"]["pod_root"]=EXP; src["config"]="RUN_CONFIG_PNOISE"
json.dump(src,open(f"{EXP}/configs/RUN_CONFIG_PNOISE.json","w"),indent=1)
print("config ok", h[:16], rh[:16])
PY
say "config done"

say "engine base cell"
cd $E
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $PV -B bt_launch.py PATH,HOME,LC_CTYPE \
  $W/configs/RUN_CONFIG_PNOISE.json --resume "ladder_$ARM" > $L/engine_ladder_$ARM.log 2>&1 \
  || { say "ENGINE FAILED"; exit 1; }
say "engine done"

say "dbar"
$PV -B $D/pnoise_dbar.py --news-devices $SRC/engine \
  --new-dir $EXP/runs/$TAGD --new-tag $TAGD --nc-dir $NCRUN --nc-tag $TAGD \
  --random-state "ladder_$ARM" --out $EXP/receipts/STEP3_DBAR_$ARM.json >> $L/step3_engine.log 2>&1 \
  || { say "DBAR FAILED"; exit 1; }
PRE=$($PV -c "import json;print('%.6f'%json.load(open('$EXP/receipts/STEP3_DBAR_$ARM.json'))['dbar_vs_nc']['pre2026']['mean_bps_per_day'])")
Y26=$($PV -c "import json;print('%.6f'%json.load(open('$EXP/receipts/STEP3_DBAR_$ARM.json'))['dbar_vs_nc']['2026']['mean_bps_per_day'])")
printf "%s\tOK\t%s\t%s\n" "$ARM" "$PRE" "$Y26" >> $EXP/receipts/STEP3_DBAR_SUMMARY.tsv
say "DONE pre2026=$PRE 2026=$Y26"
rm -rf $EXP/runs/*
say "runs freed"
