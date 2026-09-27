#!/bin/bash
# mr_prep.sh <ARM> <M> [train|shuffle|kingonly|preflight]   -- one (arm, member) of the King monthly-retrain family up to READY engine configs.
# DECISION_RULE_king_monthly_retrain_2026-09-26.md (1f2f5c4e9). Steps: root -> King -> legs -> combo s42/s2027 -> specs -> adapter
# -> X run configs -> READY_s{seed}. Any non-zero rc or Traceback stops THIS job with a FAILED marker (the queue then stops).
# Space: combo arrays, legs and the OOF are deleted once the targets exist (regenerable, shas kept in receipts), except A0_m0
# which the device gates read.
# Pre-flight (fresh2 2026-09-27, after the 18:35Z STOP): before any training, every file the combo step reads is checked by
# mr_combo.py --preflight (derived from mr_combo's own path lists, pinned to the in-service combo receipt); mode preflight stops there.
set -euo pipefail
ARM=$1; M=$2; MODE=${3:-train}
R=/dev/shm/a1seat_2026-09-27; D=/dev/shm/mretrain_2026-09-26/devices; N=/dev/shm/news2_2026-09-23; NC=/dev/shm/nc_2026-09-23
LBL=${ARM}_m${M}; [ "$MODE" = shuffle ] && LBL=RED_m${M}
W=$R/arms/$LBL; L=$R/logs/$LBL
PV=/workspace/venv/bin/python; P314=/root/news_2026-09-23_env/venv314/bin/python
NPY="X86_V4 AVX512_ICL AVX512_SPR"
mkdir -p $L
say() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [$LBL] $*" | tee -a $L/prep.log; }
ML=${MR_MASTER_LOG:-$R/logs/master.log}   # the registered log of the job that runs this prep (root-cause cells use their own)
fail() { say "FAILED: $*"; touch $W/FAILED; echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) STOP: prep $LBL FAILED: $*" >> $ML; exit 1; }
DUP_MEMBERS="A1_m0 A3_m0"   # rule §7 (revision 1, da04c28f9): one duplicate-trained member per candidate arm, scores must be bitwise equal
trap 'fail "rc=$? at line $LINENO"' ERR
# consumer-side stop guard (mr_stop.sh rule 3): whoever dispatched this prep, a STOP in its registered log after its start offset
# (or no declared scope) => refuse with rc 3 before touching anything; not a failure (no FAILED marker, no second STOP line)
. $D/mr_stop.sh
if ! mr_guard "prep $LBL $MODE" 2>> $L/prep.log; then echo "$LBL REFUSED: family stopped (see $L/prep.log)"; exit 3; fi
[ -e $W/FAILED ] && { echo "$LBL has a FAILED marker; refusing"; exit 1; }
mkdir -p $W/{work,receipts,inputs,configs,targets}
ln -f $N/work/NEWS_FEATURES.npz $W/work/NEWS_FEATURES.npz
cp -f $N/receipts/P2B_FEATURES.json $W/receipts/; ln -f $N/receipts/P1_members_2025H2on.npz $W/receipts/P1_members_2025H2on.npz
cp -f $N/inputs/bundle_config.json $W/inputs/
# the ONE vendoring rule: the path combo_target.source_kernels() reads, asked from the device itself (never an arm-local copy)
STAGE=$(cd $D && MR_W=$W $P314 -B mr_combo.py --stage-path); mkdir -p $(dirname $STAGE)
[ -e $STAGE ] || ln $N/vendor_live/fea171/combo_stage.py $STAGE || [ -e $STAGE ]   # a concurrent prep may have linked it first
say "START mode=$MODE stage=$STAGE"
cd $D && MR_W=$W NPY_DISABLE_CPU_FEATURES="$NPY" OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 $P314 -B -u mr_combo.py --preflight > $L/preflight.log 2>&1 || true
grep -q "^MR_COMBO_PREFLIGHT PASS" $L/preflight.log || fail "combo preflight (see $L/preflight.log)"
say "$(grep '^MR_COMBO_PREFLIGHT' $L/preflight.log)"
[ "$MODE" = preflight ] && { say "PREFLIGHT_ONLY_DONE"; exit 0; }
if [ -e $W/READY_s42 ] && [ -e $W/READY_s2027 ]; then say "already READY"; exit 0; fi   # after the pre-flight: a READY arm is re-checked too
if [ ! -s $W/work/king/KING_OOF.npz ]; then
  rm -rf $W/work/king
  if [ "$MODE" = shuffle ]; then
    $PV -B $D/mr_shuffle_king.py $R/arms/A0_m0/work/king/KING_OOF.npz $W/work/king > $L/king.log 2>&1
  else
    KEEP=""; [ "$LBL" = A0_m0 ] && KEEP=--keep-models
    cd $D && nice -n 12 $PV -B mr_train_king.py --out $W/work/king --arm $ARM --rs $M $KEEP > $L/king.log 2>&1
  fi
  grep -q "^Traceback" $L/king.log && fail "king traceback"
fi
say "king sha=$(sha256sum $W/work/king/KING_OOF.npz | cut -c1-16)"
# rule §7 report: model-text shas and score-array shas of this member (kept in receipts/, which the space cleanup never deletes)
$PV -B $D/mr_gates.py --identity $W/work/king/KING_OOF.npz $W/receipts/KING_IDENTITY.json > $L/identity.log 2>&1 || fail "king identity (see $L/identity.log)"
say "$(grep '^MR_IDENTITY' $L/identity.log | cut -c1-300)"
if [ "$MODE" = train ] && [[ " $DUP_MEMBERS " == *" $LBL "* ]] && ! grep -qs '"PASS": true' $R/gate/${LBL}_dup/DUP_CHECK.json; then
  if [ ! -s $R/gate/${LBL}_dup/KING_OOF.npz ]; then
    rm -rf $R/gate/${LBL}_dup
    cd $D && nice -n 12 $PV -B mr_train_king.py --out $R/gate/${LBL}_dup --arm $ARM --rs $M > $L/king_dup.log 2>&1
    grep -q "^Traceback" $L/king_dup.log && fail "duplicate king traceback"
  fi
  $PV -B $D/mr_gates.py --dup $W/work/king/KING_OOF.npz $R/gate/${LBL}_dup/KING_OOF.npz $R/gate/${LBL}_dup/DUP_CHECK.json > $L/dup.log 2>&1 || true
  grep -q "^MR_DUP PASS=True" $L/dup.log || fail "rule section 7 duplicate training: scores not bitwise equal (see $L/dup.log) -> family stops"
  say "$(grep '^MR_DUP' $L/dup.log | cut -c1-300)"
fi
[ "$MODE" = kingonly ] && { say "KINGONLY_DONE"; exit 0; }
if [ ! -s $W/receipts/P3_LEGS.json ]; then
  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NPY_DISABLE_CPU_FEATURES="$NPY" NC_W=$NC NC_TREE=$NC/tree NC_WS=$NC/ws \
    NC_CFG=$N/inputs/bundle_config.json nice -n 12 $P314 -B -u $D/nc_legs.py $W/work/NEWS_FEATURES.npz $W/work/king/KING_OOF.npz \
    $W/work/legs.npz > $L/legs.log 2>&1
  grep -q "^NC_LEGS_DONE" $L/legs.log || fail "legs no DONE line"
  cp -f $W/work/NC_LEGS_RECEIPT.json $W/receipts/P3_LEGS.json
fi
say "legs sha=$(sha256sum $W/work/legs.npz | cut -c1-16)"
for s in 42 2027; do
  if [ ! -s $W/work/combo_s$s/TARGET_RECEIPT.json ]; then
    rm -rf $W/work/combo_s$s
    cd $D && MR_W=$W NPY_DISABLE_CPU_FEATURES="$NPY" OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 nice -n 12 $P314 -B -u mr_combo.py --seed $s > $L/combo_s$s.log 2>&1
    grep -q "^Traceback" $L/combo_s$s.log && fail "combo s$s traceback"
  fi
done
say "combo done"
env -i PATH=/usr/bin:/bin HOME=/root $PV -B $D/news2_adapter_specs.py PATH,HOME,LC_CTYPE $W > $L/specs.log 2>&1
for s in 42 2027; do
  cd $N/engine
  env -i PATH=/usr/bin:/bin HOME=/root nice -n 12 $PV -B ovn_adapter.py PATH,HOME,LC_CTYPE \
    $W/configs/ADAPTER_SPEC_NEWS2_s$s.json $W/targets/TARGETS_NEWS2_s$s.npz $W/targets/TARGETS_NEWS2_s$s.json > $L/adapter_s$s.log 2>&1
  grep -q "VERDICT=PASS" $L/adapter_s$s.log || fail "adapter s$s not PASS"
  $PV - "$N" "$W" "$s" <<'PY'
import json, hashlib, sys
N, W, s = sys.argv[1:4]
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
src = f"{N}/configs/RUN_CONFIG_NEWS2_s{s}X_2026-09-23.json"; c = json.load(open(src))
want = f"NEWS2_s{s}X|scaled|rule|raw|UAFE"; runs = [r for r in c["runs"] if r["tag"] == want]; assert len(runs) == 1
r = runs[0]; npz = f"{W}/targets/TARGETS_NEWS2_s{s}.npz"; rj = npz[:-4] + ".json"
old = r["targets"]["sources"]; assert len(old) == 1
r["targets"]["sources"] = [{"npz": npz, "npz_sha256": sha(npz), "receipt": rj, "receipt_sha256": sha(rj)}]
c["runs"] = [r]; c["paths"] = dict(c["paths"]); c["paths"]["pod_root"] = f"{W}/pod_s{s}"
c["_mretrain_note"] = {"derived_from": src, "derived_from_sha256": sha(src), "in_service_targets_sha256": old[0]["npz_sha256"],
                       "changed": ["runs filtered to the base tag", "runs[0].targets.sources", "paths.pod_root"]}
json.dump(c, open(f"{W}/configs/RUN_CONFIG_MR_s{s}.json", "w"), indent=1)
print("config", s, sha(npz)[:16])
PY
  mkdir -p $W/pod_s$s/runs $W/pod_s$s/receipts
done
if [ "$LBL" != A0_m0 ]; then rm -f $W/work/combo_s*/literal.npz $W/work/combo_s*/scaled_diagnostic.npz $W/work/legs.npz $W/work/king/KING_OOF.npz; fi
for s in 42 2027; do touch $W/READY_s$s; done
say "PREP_DONE"
