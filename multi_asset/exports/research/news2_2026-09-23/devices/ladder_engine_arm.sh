#!/usr/bin/env bash
# ladder_engine_arm.sh <ARM>  -- step 3: one ladder arm's combo output through adapter -> engine base
# cell -> dbar. Pre-registration revision 1: docs/PREREG_gap_carrier_ladder_2026-09-25.md @ dd57ac30f
# (sha256 893abd37cfa87a0d07457bbdd62a5ccab804579605e1bac73244af1bdcf1ac03).
#
# Reuses the EXACT adapter/config/engine path steps 0-2 used (pnoise_run_from_king.sh L56-87) -- no new
# code path -- by placing the arm's two policy files where news2_adapter_specs.py looks for them
# ($EXP/work/combo_s42) together with a TARGET_RECEIPT.json carrying their real shas.
#
# lead's revision-1 discipline: ONE cell at a time, and the cgroup memory headroom
# (memory.max - anon - shmem) is MEASURED before each cell and written into a receipt. An oom_kill 9
# happened at 04:33Z, so this is a gate, not a note.
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

# (2) record THIS cell's own PGID, unconditionally, however this script was started.
MY_PGID=$(ps -o pgid= -p $$ | tr -d ' ')
mkdir -p $L
printf '%s\n' "PGID $MY_PGID arm=$ARM started=$(date -u +%H:%M:%SZ) launcher=$0" \
  > $L/enginearm_$ARM.pgid
say "own PGID $MY_PGID recorded to $L/enginearm_$ARM.pgid"

LAD=$EXP/work/ladder_$ARM
[ -s $LAD/literal.npz ] && [ -s $LAD/scaled_diagnostic.npz ] || { say "FATAL: arm combo missing"; exit 2; }

# ---- lead's memory gate: MEASURE, write a receipt, and refuse if short -------------------------
# Engine measured footprint: ~3.0-3.1 GiB anon per bt_launch (own_GiB 3.00-3.04 in the engine logs).
# Threshold 8 GiB = 2x the measured footprint plus ~2 GiB margin.
MEMGATE=$EXP/receipts/STEP3_MEMGATE_$ARM.json
$PV - "$ARM" "$MEMGATE" <<'PY' || { say "MEMGATE REFUSED"; exit 4; }
import datetime, json, sys
arm, out = sys.argv[1], sys.argv[2]
def rd(p):
    return open(p).read().strip()
mx = rd("/sys/fs/cgroup/memory.max")
mx = None if mx == "max" else int(mx)
st = dict(l.split()[:2] for l in open("/sys/fs/cgroup/memory.stat"))
anon, shmem = int(st["anon"]), int(st["shmem"])
cur = int(rd("/sys/fs/cgroup/memory.current"))
G = 1 << 30
need = 8 * G
head = None if mx is None else mx - anon - shmem
rec = {"arm": arm, "measured_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
       "formula": "headroom = memory.max - anon - shmem  (lead's revision-1 wording)",
       "memory_max_bytes": mx, "memory_current_bytes": cur, "anon_bytes": anon, "shmem_bytes": shmem,
       "headroom_bytes": head,
       "memory_max_GiB": None if mx is None else round(mx / G, 3),
       "anon_GiB": round(anon / G, 3), "shmem_GiB": round(shmem / G, 3),
       "headroom_GiB": None if head is None else round(head / G, 3),
       "threshold_GiB": 8.0,
       "threshold_basis": ("engine measured anon footprint 3.00-3.04 GiB per bt_launch (own_GiB in the "
                           "engine logs); threshold = 2x that plus ~2 GiB margin"),
       "why_this_gate_exists": "cgroup oom_kill 9 at 2026-09-25T04:33Z killed another agent's job"}
rec["verdict"] = "PASS" if (head is not None and head >= need) else "REFUSE"
json.dump(rec, open(out, "w"), indent=2)
print("MEMGATE %s headroom=%s GiB (threshold %s GiB) anon=%s shmem=%s"
      % (rec["verdict"], rec["headroom_GiB"], rec["threshold_GiB"], rec["anon_GiB"], rec["shmem_GiB"]))
sys.exit(0 if rec["verdict"] == "PASS" else 1)
PY
say "memgate receipt $MEMGATE"

# measured disk gate before the engine, never assumed (engine run measured at ~346 MiB)
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
       "memgate_receipt": {"path": f"{EXP}/receipts/STEP3_MEMGATE_{arm}.json",
                           "sha256": sha(f"{EXP}/receipts/STEP3_MEMGATE_{arm}.json")},
       "combo_code": lad["combo_code"],
       "limits": ["NOT a deployable version and NOT a producer parity replay: this is one array swapped "
                  "between two books, a measuring instrument only",
                  "arms are NOT additive",
                  "no execution/cash or policy-stop result",
                  "scaled_diagnostic changes historical publication gate; never current-live literal"]}
if "cells_filled_with_nc_because_new_had_no_score" in lad:
    rec["nc_fill"] = lad["cells_filled_with_nc_because_new_had_no_score"]
    rec["fill_rule"] = lad.get("fill_rule")
with open(f"{EXP}/work/combo_s42/TARGET_RECEIPT.json", "w") as f:
    json.dump(rec, f, indent=1, allow_nan=False)
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
with open(f"{EXP}/configs/RUN_CONFIG_PNOISE.json","w") as f:
    json.dump(src,f,indent=1)
print("config ok", h[:16], rh[:16])
PY
say "config done"

# (1) team run gate -- blocks until other bt_launch groups <= 2, headroom >= 24 GiB, shm >= 4 GiB
say "run gate"
bash $D/rungate.sh "$ARM" "$EXP/receipts/STEP3_RUNGATE_$ARM.json" 2>&1 | tee -a $L/step3_engine.log
if [ ! -s "$EXP/receipts/STEP3_RUNGATE_$ARM.json" ]; then say "RUN GATE produced no receipt"; exit 5; fi

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
HEAD=$($PV -c "import json;print(json.load(open('$MEMGATE'))['headroom_GiB'])")
printf "%s\tOK\t%s\t%s\theadroom_GiB=%s\n" "$ARM" "$PRE" "$Y26" "$HEAD" >> $EXP/receipts/STEP3_DBAR_SUMMARY.tsv
say "DONE pre2026=$PRE 2026=$Y26 headroom_GiB=$HEAD"

# the 911-day supplementary reading lead asked for lives in a separate device run over the same paths,
# so the run directory is kept until that device has read it, then freed by the batch driver.
