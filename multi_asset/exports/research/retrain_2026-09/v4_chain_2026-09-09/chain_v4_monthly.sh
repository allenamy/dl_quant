#!/bin/bash
# chain_v4_monthly.sh — THE single ordered driver of the v4 monthly retrain (RUNBOOK_monthly_retrain_2026-10 §0★ 修订 3, 2026-09-12; independent
# review 0dfc0d87 R1–R5 all accepted). usage:
#   bash chain_v4_monthly.sh <v4_month_<YYYY-MM>.env>            # every stage, in order; DONE only when every stage succeeded
#   V4_STAGES=preflight,gates bash chain_v4_monthly.sh <env>     # a subset (comma list of the stage names below) — every stage still requires its
#                                                                #   upstream receipts/markers, so a subset cannot skip a gate, only skip WORK
#   V4_DRYRUN=1 bash chain_v4_monthly.sh <env>                   # NEGATIVE-CONTROL mode: any stage after preflight dies BEFORE launching anything
# Discipline (chain_lib.sh): every child's rc is collected; a gate is required BY NAME with self_sha= computed at run time and the full registered
# input set; every producer is followed by an output-existence check and its completion marker; a stage's failure writes FAIL_<reason> to
# $R/v4_commands.txt and exits non-zero; CHAIN_V4_MONTHLY_DONE is written only at the end of a fully successful run.
# Stages (order is the dependency graph the reviewer found missing, R3):
#   preflight  month env (every key) · month root exists · device files present + sha-pinned (deps_preflight) · STEP1/STEP2/BUNDLE_export gate sources
#              APPROVED in the frozen contract · every input path exists · A0 baseline books present  → v4_gates/preflight.json (PASS) else rc 3
#   cache      cache_coverage_gate_v2.py $CACHE (rc) → v4_gates/cache_coverage.json
#   data       RAW targets (+raw_patch) → $DLW_RAW · CLIP targets → $DLW_CLIP · fea82 → $DLW_CLIP, copied + byte-verified → $DLW_RAW · fea89 → $F8 ·
#              king features (clamp) → $KING_FEA/$KING_META · F10_GATE_{RAW,CLIP}.json identity receipts
#   gates      RUN $GATE_STEP1 → v4_gates/step1.json and $GATE_STEP2 → v4_gates/step2.json, then require_gate both (gate= self_sha= full inputs)
#   king       pod_export_bundle_v4.py, env verbatim from the contract + BUNDLE_GENERATION (BUNDLE_DONE, no BUNDLE_FAIL)  ← BEFORE legs (R3 ③)
#   legs       pod_legs_v4b.py, LEGS_PRED = THIS month's king PRED ($BUNDLE_OUT/slow_pred_pinned.npy) (LEGS_V4B_DONE; 2023 king seat ≥ 0.4)
#   mwf        MONTHS_ALL checked against the targets axis · SH0..SH3 from MONTHS_ALL · pin_deps · RAW × SEEDS shards by PID · merge (MERGE_DONE)
#   refit      per seed: explicit env F10_DLW F10_OUT SEED BEST_EP_FIX=7 EMBARGO=1 (REFIT_DONE; sidecar best_ep_rule == fix7)
#   arms       build_dev_v4.py (DEV_V4_DONE) → run_v4_arms.sh $EXPORT_ARM (per-PID rc, ARMS_DONE, fresh END rc=0 lines counted)
#   judge      judge_v4.py (JUDGE_V4_DONE)
#   export     v4e_gate_export_v2.py gate (rc 0) → require (REQUIRE_OK) → judge re-run WITH the eligibility locator (JUDGE_v4_eligible.json)
set -o pipefail
CHAIN_DEVICE_DIR=$(cd "$(dirname "$0")" && pwd -P); export CHAIN_DEVICE_DIR   # chain_lib sets D from it (a plain `D` could be inherited from any shell)
L=/dev/stderr; export L                      # until the month root is known, nothing is appended to any September log
. "$CHAIN_DEVICE_DIR/chain_lib.sh"; export D PY R   # D was set by chain_lib from CHAIN_DEVICE_DIR; the stage heredocs read D/R/PY from the environment
ENVF=$1; [ -n "$ENVF" ] || { echo "usage: chain_v4_monthly.sh <v4_month.env>" >&2; exit 2; }
load_month_env "$ENVF" || exit 4
V4_STAGES=${V4_STAGES:-all}; DRY=${V4_DRYRUN:-0}
[ -d "$R" ] || { L=/dev/stderr; die "month_root_missing_$R" 3; }
mkdir -p "$R/v4_gates" || die "month_root_unwritable" 3
STAGE_LOG=$R/chain_v4_monthly.log
stage(){ say "$*"; echo "[$(date -u +%FT%TZ)] $*" | tee -a "$STAGE_LOG"; }
want(){ [ "$V4_STAGES" = all ] || [[ ",$V4_STAGES," == *",$1,"* ]]; }
guard(){ [ "$DRY" = 1 ] && die "dryrun_guard_${1}_would_launch" 9; return 0; }
SEED_LIST=${SEEDS//,/ }
stage "chain_v4_monthly start month=$V4_MONTH env=$ENVF sha=$(gate_sha "$ENVF" || echo unreadable) device=$D root=$R stages=$V4_STAGES dryrun=$DRY"

# ── preflight ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
if want preflight; then
  stage "preflight: device files, gate approval, inputs"
  DEV_FILES="chain_lib.sh chain_v4_monthly.sh v4_months.py v4_gate_common.py ELIGIBILITY_CONTRACT.json $GATE_STEP1 $GATE_STEP2 pod_dlw_targets_raw.py pod_fea_ext_clamp.py pod_export_bundle_v4.py pod_legs_v4b.py pod_f10_train_monthly_v4.py launch_mwf_v4b.sh merge_mwf_v4b.py pod_f10_refit_v4.py build_dev_v4.py run_v4_arms.sh judge_v4.py v4e_gate_export_v2.py gate_signal_parity_v2.py cache_coverage_gate_v2.py"
  PF_INPUTS="CACHE PANEL_SPLICE PANEL_KING RAW_PATCH HOLE_CELLS BUNDLE_BASE EXPORT_PANEL EMA_STATE_JSON LIVE_PINS FUND_AUG FUNDING_DIR LEGS_OLD LEGS_PANEL SIGNAL_RECEIPT BUILDER_FEA82 BUILDER_FEA89 BASE_TRAINER PREV_META REF_META"
  V4_DEV_FILES="$DEV_FILES" V4_PF_INPUTS="$PF_INPUTS" "$PY" - "$R/v4_gates/preflight.json" <<'PYEOF'; rc=$?
import hashlib, json, os, subprocess, sys, time
out = sys.argv[1]; E = os.environ; D = E["D"]; R = E["R"]; fails = []; dev = {}; ext = {}; inputs = {}
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
for f in E["V4_DEV_FILES"].split():
    p = os.path.join(D, f)
    if os.path.isfile(p): dev[f] = sha(p)
    else: fails.append(f"device file missing: {p}")
for k in ("BUILDER_FEA82", "BUILDER_FEA89", "BASE_TRAINER"):
    p = E[k]
    if os.path.isfile(p): ext[k] = {"path": p, "sha256": sha(p)}
    else: fails.append(f"external builder missing: {k}={p}")
for k in E["V4_PF_INPUTS"].split():
    p = E[k]
    if os.path.exists(p): inputs[k] = {"path": p, "bytes": os.path.getsize(p) if os.path.isfile(p) else None, "is_dir": os.path.isdir(p)}
    else: fails.append(f"input missing: {k}={p}")
for k in ("DLW_EXT", "F8_EXT"):
    for rel in (("data/dlw_targets.npz",) if k == "DLW_EXT" else tuple(f"preds/f10_V2MAIN_s{s}.npy" for s in E["SEEDS"].split(","))):
        p = os.path.join(E[k], rel)
        if os.path.isfile(p): inputs[f"{k}/{rel}"] = {"path": p, "bytes": os.path.getsize(p)}
        else: fails.append(f"input missing: {k}/{rel}={p}")
p = os.path.join(E["PREV_BUNDLE"], "slow_pred_pinned.npy")
if os.path.isfile(p): inputs["PREV_BUNDLE/slow_pred_pinned.npy"] = {"path": p, "bytes": os.path.getsize(p)}
else: fails.append(f"input missing: PREV_BUNDLE/slow_pred_pinned.npy={p}")
HC = E["HC"]
for rel in ["masks/umask_UPIT_CRYPTO.npz", "calib/costb_fee_steady.json", "run_arm.sh"] + [f"dev_v4/probe_artifacts/w10_ablation_series_V4_A0_{seat}_s{s}.npz" for seat in ("dyn", "fix") for s in (42, 2027)]:
    p = os.path.join(HC, rel)
    if os.path.isfile(p): inputs[f"HC/{rel}"] = {"path": p, "bytes": os.path.getsize(p)}
    else: fails.append(f"dev tree file missing: HC/{rel}={p}")
approval = {}
for gate, src in (("STEP1", E["GATE_STEP1"]), ("STEP2", E["GATE_STEP2"]), ("BUNDLE_export", "v4e_gate_export_v2.py")):
    p = os.path.join(D, src)
    if not os.path.isfile(p): approval[gate] = {"source": src, "ok": False, "why": "source missing"}; continue
    r = subprocess.run([E["PY"], os.path.join(D, "v4_gate_common.py"), "approved", gate, sha(p)], capture_output=True, text=True)
    approval[gate] = {"source": src, "sha256": sha(p), "ok": r.returncode == 0, "why": (r.stdout + r.stderr).strip()[:300]}
    if r.returncode != 0: fails.append(f"gate source NOT approved in the frozen contract: {gate} <- {src} ({sha(p)[:12]})")
try:
    ms = [int(x) for x in E["MONTHS_ALL"].split(",")]; assert all(200001 <= m <= 209912 and 1 <= m % 100 <= 12 for m in ms) and ms == sorted(set(ms)), ms
except Exception as e:                        # noqa: BLE001
    fails.append(f"MONTHS_ALL malformed: {e}")
seeds = E["SEEDS"].split(",")
if not all(s in ("42", "2027") for s in seeds): fails.append(f"SEEDS not in the trainer whitelist {{42,2027}}: {seeds}")
res = {"gate": "PREFLIGHT", "PASS": not fails, "month": E["V4_MONTH"], "month_env": E["V4_MONTH_ENV"], "month_env_sha256": sha(E["V4_MONTH_ENV"]), "device_dir": D, "root": R,
       "device_sha256": dev, "external_sha256": ext, "inputs": inputs, "gate_approval": approval, "months_all": E["MONTHS_ALL"], "seeds": seeds, "generation": E["BUNDLE_GENERATION"],
       "fails": fails, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "dryrun": E.get("V4_DRYRUN", "0")}
os.makedirs(os.path.dirname(out), exist_ok=True); json.dump(res, open(out, "w"), indent=1)
print(f"PREFLIGHT {'PASS' if not fails else 'FAIL'} device_files={len(dev)} inputs={len(inputs)} approvals={sum(1 for a in approval.values() if a['ok'])}/3 fails={len(fails)}")
for f in fails[:12]: print("  -", f)
sys.exit(0 if not fails else 3)
PYEOF
  stage "preflight rc=$rc $(tail -1 "$R/v4_gates/preflight.json" >/dev/null 2>&1 && "$PY" -c "import json,sys;d=json.load(open(sys.argv[1]));print('PASS' if d['PASS'] else 'FAIL', len(d['fails']), 'fails', d['fails'][:3])" "$R/v4_gates/preflight.json")"
  [ $rc -eq 0 ] || die "preflight_rc_$rc" 3
  pin_deps preflight_device $(for f in $DEV_FILES; do echo "$D/$f"; done) "$BUILDER_FEA82" "$BUILDER_FEA89" "$BASE_TRAINER" "$ENVF"
fi

# ── cache coverage gate ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
if want cache; then
  guard cache; stage "cache: coverage gate v2 on $CACHE"
  "$PY" "$D/cache_coverage_gate_v2.py" "$CACHE" > "$R/cache_coverage.log" 2>&1; rc=$?
  "$PY" - "$R/v4_gates/cache_coverage.json" "$CACHE" "$rc" "$R/cache_coverage.log" <<'PYEOF'
import hashlib, json, sys, time
out, cache, rc, log = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
h = hashlib.sha256()
with open(cache, "rb") as f:
    for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
json.dump({"gate": "CACHE_COVERAGE_v2", "PASS": rc == 0, "rc": rc, "cache": cache, "cache_sha256": h.hexdigest(), "log_tail": open(log).read()[-2000:], "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, open(out, "w"), indent=1)
PYEOF
  stage "cache gate rc=$rc $(tail -1 "$R/cache_coverage.log" | cut -c1-120)"; [ $rc -eq 0 ] || die "cache_coverage_rc_$rc" 3
fi

# ── data chain ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
if want data; then
  guard data; DL=$R/chain_v4_data.log; : > "$DL"
  mkdir -p "$DLW_RAW/data" "$DLW_RAW/results" "$DLW_CLIP/data" "$DLW_CLIP/results" "$F8/data" "$F8/results" "$F8/preds" "$F8/models" "$F8/logs" "$F8/gates" "$(dirname "$KING_FEA")" || die "data_mkdir" 1
  stage "data: RAW targets (holefix2 + raw_patch) -> $DLW_RAW"
  DLWT_CACHE=$CACHE DLWT_PANEL=$PANEL_SPLICE DLWT_OUT=$DLW_RAW DLWT_RET_CH=0 DLWT_RAW_PATCH=$RAW_PATCH "$PY" "$D/pod_dlw_targets_raw.py" >> "$DL" 2>&1 || die "targets_raw" 1
  [ -f "$DLW_RAW/data/dlw_targets.npz" ] || die "targets_raw_output_missing" 1
  stage "data: CLIP targets (holefix2, clipped ret5 channel, no patch) -> $DLW_CLIP"
  DLWT_CACHE=$CACHE DLWT_PANEL=$PANEL_SPLICE DLWT_OUT=$DLW_CLIP DLWT_RET_CH=0 "$PY" "$D/pod_dlw_targets_raw.py" >> "$DL" 2>&1 || die "targets_clip" 1
  [ -f "$DLW_CLIP/data/dlw_targets.npz" ] || die "targets_clip_output_missing" 1
  stage "data: fea82 -> $DLW_CLIP (copied + verified to $DLW_RAW)"
  ( cd "$(dirname "$BUILDER_FEA82")" && F171_CACHE=$CACHE F171_PANEL=$PANEL_SPLICE F171_OUT=$DLW_CLIP "$PY" "$BUILDER_FEA82" ) >> "$DL" 2>&1 || die "fea82" 1
  [ -f "$DLW_CLIP/data/dlw_fea82.npz" ] || die "fea82_output_missing" 1
  cp "$DLW_CLIP/data/dlw_fea82.npz" "$DLW_RAW/data/dlw_fea82.npz" || die "cp_fea82_to_raw" 1
  cmp -s "$DLW_CLIP/data/dlw_fea82.npz" "$DLW_RAW/data/dlw_fea82.npz" || die "cp_fea82_verify_mismatch" 1
  [ -f "$DLW_CLIP/results/dlw_features_report.json" ] && { cp "$DLW_CLIP/results/dlw_features_report.json" "$DLW_RAW/results/" || die "cp_fea82_report" 1; }
  stage "data: fea89 -> $F8"
  ( cd "$(dirname "$BUILDER_FEA89")" && F8_DLW=$DLW_CLIP F8_CACHE=$CACHE F8_OUT=$F8 "$PY" "$BUILDER_FEA89" build ) >> "$DL" 2>&1 || die "fea89" 1
  [ -f "$F8/data/f8_fea89.npz" ] || die "fea89_output_missing" 1
  stage "data: king features (clamp) -> $KING_FEA"
  CACHE_IN=$CACHE PANEL_IN=$PANEL_KING FEA_OUT=$KING_FEA META_OUT=$KING_META "$PY" "$D/pod_fea_ext_clamp.py" >> "$DL" 2>&1 || die "king_fea" 1
  [ -f "$KING_FEA" ] && [ -f "$KING_META" ] || die "king_fea_output_missing" 1
  for T in RAW CLIP; do
    case $T in RAW) DW=$DLW_RAW ;; CLIP) DW=$DLW_CLIP ;; esac
    "$PY" - "$F8/gates/F10_GATE_$T.json" "$DW/data/dlw_targets.npz" "$DW/data/dlw_fea82.npz" "$F8/data/f8_fea89.npz" <<'PYEOF' || die "f10_gate_json_$T" 1
import hashlib, json, sys
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
json.dump({"targets_sha256": sha(sys.argv[2]), "fea82_sha256": sha(sys.argv[3]), "fea89_sha256": sha(sys.argv[4])}, open(sys.argv[1], "w"), indent=1)
PYEOF
  done
  stage "CHAIN_V4_MONTHLY_DATA_DONE"
fi

# ── STEP1 / STEP2 gates: RUN, then REQUIRE ──────────────────────────────────────────────────────────────────────────────────────────────────
if want gates; then
  guard gates; stage "gates: run $GATE_STEP1 and $GATE_STEP2, then require both"
  run_gate STEP1 "$GATE_STEP1" "$R/gate_step1.log" STEP1_OUT="$R/v4_gates/step1.json"; rc1=$?
  run_gate STEP2 "$GATE_STEP2" "$R/gate_step2.log" STEP2_OUT="$R/v4_gates/step2.json"; rc2=$?
  stage "gates ran: STEP1 rc=$rc1 STEP2 rc=$rc2 (receipts $R/v4_gates/step{1,2}.json)"
  S1_SRC=$(gate_sha "$D/$GATE_STEP1") || die "gate_source_unreadable_$GATE_STEP1" 3
  S2_SRC=$(gate_sha "$D/$GATE_STEP2") || die "gate_source_unreadable_$GATE_STEP2" 3
  require_gate "$R/v4_gates/step1.json" gate=STEP1 profile=v4 self_sha=$S1_SRC dlw_v4raw_targets=$DLW_RAW/data/dlw_targets.npz dlw_hf3_targets=$DLW_CLIP/data/dlw_targets.npz fea82_v4raw=$DLW_RAW/data/dlw_fea82.npz fea89_f8v4=$F8/data/f8_fea89.npz
  require_gate "$R/v4_gates/step2.json" gate=STEP2 self_sha=$S2_SRC wide_fea_v4=$KING_FEA wide_fea_v4_meta=$KING_META
  [ $rc1 -eq 0 ] && [ $rc2 -eq 0 ] || die "gates_rc_${rc1}_${rc2}" 3
  stage "gates PASS + required (STEP1 self $S1_SRC, STEP2 self $S2_SRC)"
fi

# ── king export (BEFORE legs: legs need THIS month's PRED) ────────────────────────────────────────────────────────────────────────────────
if want king; then
  guard king; stage "king: export bundle generation=$BUNDLE_GENERATION -> $BUNDLE_OUT (requires the STEP2 receipt bound to $KING_FEA/$KING_META)"
  S2_SRC=$(gate_sha "$D/$GATE_STEP2") || die "gate_source_unreadable_$GATE_STEP2" 3
  require_gate "$R/v4_gates/step2.json" gate=STEP2 self_sha=$S2_SRC wide_fea_v4=$KING_FEA wide_fea_v4_meta=$KING_META
  env BUNDLE_OUT=$BUNDLE_OUT BUNDLE_BASE=$BUNDLE_BASE BUNDLE_FEA=$KING_FEA BUNDLE_META=$KING_META BUNDLE_CACHE=$CACHE BUNDLE_TAR=$BUNDLE_TAR EXPORT_PANEL=$EXPORT_PANEL EMA_STATE_JSON=$EMA_STATE_JSON \
      LIVE_PINS=$LIVE_PINS FUND_AUG=$FUND_AUG FUNDING_DIR=$FUNDING_DIR BUNDLE_GENERATION=$BUNDLE_GENERATION V4_MONTH_ENV=$V4_MONTH_ENV "$PY" "$D/pod_export_bundle_v4.py" > "$R/export_v4.log" 2>&1; rc=$?
  stage "king export rc=$rc $(tail -1 "$R/export_v4.log" | cut -c1-120)"; [ $rc -eq 0 ] || die "king_export_rc_$rc" 1
  check_marker "$R/export_v4.log" "BUNDLE_DONE"; check_no_marker "$R/export_v4.log" "BUNDLE_FAIL"
  [ -f "$BUNDLE_OUT/slow_pred_pinned.npy" ] && [ -f "$BUNDLE_OUT/config.json" ] && [ -f "$BUNDLE_OUT/MANIFEST.json" ] || die "king_export_outputs_missing" 1
  "$PY" -c "import json,sys;p=json.load(open(sys.argv[1]))['provenance'];assert p['generation']==sys.argv[2],(p['generation'],sys.argv[2]);print('provenance generation',p['generation'],'king_train_end_utc',p['king_train_end_utc'],'built_utc',p['built_utc'])" "$BUNDLE_OUT/config.json" "$BUNDLE_GENERATION" >> "$STAGE_LOG" 2>&1 || die "king_export_generation_mismatch" 1
fi

# ── legs (in-service rows verbatim + new anchors from THIS month's king PRED) ──────────────────────────────────────────────────────────────
if want legs; then
  guard legs; stage "legs: pod_legs_v4b.py LEGS_PRED=$BUNDLE_OUT/slow_pred_pinned.npy LEGS_OLD=$LEGS_OLD"
  [ -f "$BUNDLE_OUT/slow_pred_pinned.npy" ] || die "legs_king_pred_missing" 3
  check_marker "$R/export_v4.log" "BUNDLE_DONE"; check_no_marker "$R/export_v4.log" "BUNDLE_FAIL"   # legs consume THIS month's export: its marker must be present in this root
  env LEGS_TG=$DLW_RAW/data/dlw_targets.npz LEGS_META=$KING_META LEGS_PRED=$BUNDLE_OUT/slow_pred_pinned.npy LEGS_OUT=$F8/data/f10v2_legs.npz LEGS_OLD=$LEGS_OLD LEGS_PANEL=$LEGS_PANEL "$PY" "$D/pod_legs_v4b.py" > "$R/legs_v4.log" 2>&1; rc=$?
  stage "legs rc=$rc $(tail -1 "$R/legs_v4.log" | cut -c1-120)"; [ $rc -eq 0 ] || die "legs_rc_$rc" 1
  check_marker "$R/legs_v4.log" "LEGS_V4B_DONE"; [ -f "$F8/data/f10v2_legs.npz" ] || die "legs_output_missing" 1
  "$PY" - "$R/legs_v4.log" <<'PYEOF' >> "$STAGE_LOG" 2>&1 || die "legs_2023_king_seat_check" 3
import ast, re, sys
txt = open(sys.argv[1]).read(); m = re.search(r"WL mean by year \(king, rev24, fund\): (\{.*\})", txt)
assert m, "legs log has no 'WL mean by year' line (AMENDMENT 5 self-check missing)"
wl = ast.literal_eval(m.group(1)); k23 = wl[2023][0]; print("legs WL 2023 king seat", k23, "(AMENDMENT 5: ~0.59 expected; < 0.4 = the all-rows recomputation defect)")
assert k23 >= 0.4, f"2023 king seat {k23} < 0.4"
PYEOF
fi

# ── F10 monthly walk-forward (RAW x seeds) + merge ──────────────────────────────────────────────────────────────────────────────────────────
if want mwf; then
  guard mwf; stage "mwf: MONTHS_ALL=$MONTHS_ALL seeds=[$SEED_LIST] root=$F8/$MWF_ROOT"
  "$PY" "$D/v4_months.py" check "$DLW_RAW/data/dlw_targets.npz" "$MONTHS_ALL" >> "$STAGE_LOG" 2>&1 || die "months_all_not_admissible_for_axis" 3
  set_shards_from_months_all; export MWF_ROOT
  S1_SRC=$(gate_sha "$D/$GATE_STEP1") || die "gate_source_unreadable_$GATE_STEP1" 3
  require_gate "$R/v4_gates/step1.json" gate=STEP1 profile=v4 self_sha=$S1_SRC dlw_v4raw_targets=$DLW_RAW/data/dlw_targets.npz dlw_hf3_targets=$DLW_CLIP/data/dlw_targets.npz fea82_v4raw=$DLW_RAW/data/dlw_fea82.npz fea89_f8v4=$F8/data/f8_fea89.npz
  check_marker "$R/legs_v4.log" "LEGS_V4B_DONE"; [ -f "$F8/data/f10v2_legs.npz" ] || die "legs_missing" 3
  pin_deps v4_monthly_mwf "$D/pod_f10_train_monthly_v4.py" "$D/launch_mwf_v4b.sh" "$D/merge_mwf_v4b.py" "$D/chain_lib.sh" "$D/v4_months.py" "$BASE_TRAINER" "$F8/data/f10v2_legs.npz" "$F8/data/f8_fea89.npz" "$DLW_RAW/data/dlw_targets.npz" "$DLW_CLIP/data/dlw_targets.npz" "$DLW_RAW/data/dlw_fea82.npz" "$F8/gates/F10_GATE_RAW.json" "$ENVF"
  for SD in $SEED_LIST; do
    stage "F10 chain RAW s$SD start (monthly, legs v4b, FIX7, shards from MONTHS_ALL)"
    run_shards launch_mwf_v4b.sh RAW "$SD" || die "shards_RAW_s${SD}_rc_[$RCS]" 1
    "$PY" "$D/merge_mwf_v4b.py" RAW "$SD" > "$F8/logs/merge_v4b_RAW_s${SD}.log" 2>&1; rc=$?; stage "merge RAW s$SD rc=$rc $(tail -1 "$F8/logs/merge_v4b_RAW_s${SD}.log" | cut -c1-80)"
    [ $rc -eq 0 ] || die "merge_RAW_s${SD}_rc_$rc" 1; check_marker "$F8/logs/merge_v4b_RAW_s${SD}.log" "MERGE_DONE"
  done
  stage "CHAIN_V4_MONTHLY_MWF_DONE (shards rc=0, merges rc=0 + MERGE_DONE; deps in v4_gates/deps_v4_monthly_mwf.json)"
fi

# ── refit (deployment weights), explicit env, FIX7 ──────────────────────────────────────────────────────────────────────────────────────────
if want refit; then
  guard refit
  for SD in $SEED_LIST; do
    stage "refit s$SD: env F10_DLW=$DLW_RAW F10_OUT=$F8 SEED=$SD BEST_EP_FIX=7 EMBARGO=1"
    env F10_DLW=$DLW_RAW F10_OUT=$F8 SEED=$SD BEST_EP_FIX=7 EMBARGO=1 V4_MONTH=$V4_MONTH V4_MONTH_ENV=$V4_MONTH_ENV "$PY" "$D/pod_f10_refit_v4.py" > "$R/refit_s$SD.log" 2>&1; rc=$?
    stage "refit s$SD rc=$rc $(tail -1 "$R/refit_s$SD.log" | cut -c1-140)"; [ $rc -eq 0 ] || die "refit_s${SD}_rc_$rc" 1
    check_marker "$R/refit_s$SD.log" "REFIT_DONE"; [ -f "$F8/models/f10_live_s$SD.pt" ] && [ -f "$F8/models/f10_live_s$SD.json" ] || die "refit_s${SD}_outputs_missing" 1
    "$PY" -c "import json,sys;m=json.load(open(sys.argv[1]));assert m['best_ep_rule']=='fix7' and m['env_given']['BEST_EP_FIX']=='7' and m['env_given']['F10_DLW']==sys.argv[2],(m['best_ep_rule'],m['env_given']);print('refit s'+str(m['seed']),'rule',m['best_ep_rule'],'label cutoff',m['trained_through_label_utc'],'pool end',m['trained_through_pool_end_utc'],'pt',m['pt_sha256'][:12])" "$F8/models/f10_live_s$SD.json" "$DLW_RAW" >> "$STAGE_LOG" 2>&1 || die "refit_s${SD}_rule_not_fix7" 3
  done
fi

# ── book layer: dev tree + arms ─────────────────────────────────────────────────────────────────────────────────────────────────────────────
if want arms; then
  guard arms; stage "arms: build_dev_v4 (raw meta, SLOW_v4 from $BUNDLE_OUT, A0 preds) then run_v4_arms.sh $EXPORT_ARM seeds [$SEED_LIST]"
  mkdir -p "$HC/dev_v4/logs" "$KING_DIR" || die "arms_mkdir" 1
  env KING_META=$KING_META DLW_RAW=$DLW_RAW CACHE=$CACHE HOLE_CELLS=$HOLE_CELLS BUNDLE_OUT=$BUNDLE_OUT "$PY" "$D/build_dev_v4.py" > "$R/build_dev_v4.log" 2>&1; rc=$?
  stage "build_dev_v4 rc=$rc $(tail -1 "$R/build_dev_v4.log" | cut -c1-100)"; [ $rc -eq 0 ] || die "build_dev_v4_rc_$rc" 1; check_marker "$R/build_dev_v4.log" "DEV_V4_DONE"
  N0=$(grep -a -c "^END\[V4_${EXPORT_ARM}_.*rc=0" "$HC/logs/commands.txt" 2>/dev/null || echo 0)
  bash "$D/run_v4_arms.sh" "$EXPORT_ARM" "$SEED_LIST" > "$R/arms_${EXPORT_ARM}.log" 2>&1; rc=$?
  N1=$(grep -a -c "^END\[V4_${EXPORT_ARM}_.*rc=0" "$HC/logs/commands.txt" 2>/dev/null || echo 0); NEED=$(( 2 * $(echo $SEED_LIST | wc -w) ))
  stage "arms $EXPORT_ARM rc=$rc fresh END rc=0 lines $((N1 - N0))/$NEED"; [ $rc -eq 0 ] || die "arms_${EXPORT_ARM}_rc_$rc" 1
  check_marker "$R/arms_${EXPORT_ARM}.log" "ARMS_DONE"; [ $((N1 - N0)) -ge $NEED ] || die "arms_${EXPORT_ARM}_fresh_END_lines_$((N1 - N0))_lt_$NEED" 1
fi

# ── judge ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
if want judge; then
  guard judge; stage "judge: JUDGE_HC=$HC -> $R/v4_gates/JUDGE_v4.json"
  JUDGE_HC=$HC JUDGE_OUT=$R/v4_gates/JUDGE_v4.json "$PY" "$D/judge_v4.py" > "$R/judge_v4.log" 2>&1; rc=$?
  stage "judge rc=$rc $(grep -a "JUDGE_V4_DONE\|JUDGE_REFUSED" "$R/judge_v4.log" | tail -1 | cut -c1-140)"; [ $rc -eq 0 ] || die "judge_rc_$rc" 1
  check_marker "$R/judge_v4.log" "JUDGE_V4_DONE"
fi

# ── export gate v2: gate, require, then judge WITH the eligibility locator ──────────────────────────────────────────────────────────────────
if want export; then
  guard export; stage "export: v4e_gate_export_v2.py gate + require on arm $EXPORT_ARM (V4CHAIN_DIR=$D)"
  GX="EXPORT_ARM=$EXPORT_ARM BUNDLE_OUT=$BUNDLE_OUT BUNDLE_FEA=$KING_FEA BUNDLE_META=$KING_META BUNDLE_BASE=$BUNDLE_BASE EXPORT_PANEL=$EXPORT_PANEL BUNDLE_CACHE=$CACHE FUND_AUG=$FUND_AUG LIVE_PINS=$LIVE_PINS JUDGE_HC=$HC V4CHAIN_DIR=$D SIGNAL_RECEIPT=$SIGNAL_RECEIPT"
  REC=$R/v4_gates/BUNDLE_export_v2_${EXPORT_ARM}.json
  env $GX EXPORT_GATE_OUT=$REC "$PY" "$D/v4e_gate_export_v2.py" > "$R/export_gate_v2.log" 2>&1; rc=$?
  stage "export gate rc=$rc $(tail -1 "$R/export_gate_v2.log" | cut -c1-140)"; [ $rc -eq 0 ] || die "export_gate_v2_rc_$rc" 3
  env $GX EXPORT_GATE_OUT=/dev/null REQUIRE_OUT=$R/v4_gates/REQUIRE_v2_${EXPORT_ARM}.json "$PY" "$D/v4e_gate_export_v2.py" require "$REC" > "$R/export_require_v2.log" 2>&1; rc=$?
  stage "export require rc=$rc $(tail -1 "$R/export_require_v2.log" | cut -c1-140)"; [ $rc -eq 0 ] || die "export_require_v2_rc_$rc" 3
  check_marker "$R/export_require_v2.log" "REQUIRE_OK"
  "$PY" -c "import json,sys;r=json.load(open(sys.argv[1]));json.dump({sys.argv[2]:{'receipt':sys.argv[1],'inputs':r['inputs_path']}},open(sys.argv[3],'w'),indent=1);print('eligibility locator',sys.argv[3],len(r['inputs_path']),'inputs')" "$REC" "$EXPORT_ARM" "$R/v4_gates/JUDGE_ELIGIBILITY.json" >> "$STAGE_LOG" 2>&1 || die "eligibility_locator_write" 3
  JUDGE_HC=$HC JUDGE_OUT=$R/v4_gates/JUDGE_v4_eligible.json JUDGE_ELIGIBILITY=$R/v4_gates/JUDGE_ELIGIBILITY.json "$PY" "$D/judge_v4.py" > "$R/judge_v4_eligible.log" 2>&1; rc=$?
  stage "judge (with eligibility) rc=$rc $(grep -a "JUDGE_V4_DONE\|JUDGE_REFUSED" "$R/judge_v4_eligible.log" | tail -1 | cut -c1-140)"; [ $rc -eq 0 ] || die "judge_eligible_rc_$rc" 1
  check_marker "$R/judge_v4_eligible.log" "JUDGE_V4_DONE"
fi

if [ "$V4_STAGES" = all ]; then
  stage "CHAIN_V4_MONTHLY_DONE month=$V4_MONTH (every stage rc=0 with its marker/receipt; a candidate still needs judge (A) + user ruling)"; MD=$R/v4_gates/MONTHLY_DONE.json
else
  stage "CHAIN_V4_MONTHLY_STAGES_DONE month=$V4_MONTH stages=$V4_STAGES (a SUBSET ran, rc=0 each — NOT the full chain; no MONTHLY_DONE.json)"; MD=$R/v4_gates/MONTHLY_STAGES_DONE.json
fi
"$PY" -c "import json,sys,time;json.dump({'DONE':sys.argv[2]=='all','month':sys.argv[1],'stages':sys.argv[2],'env':sys.argv[3],'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())},open(sys.argv[4],'w'),indent=1)" "$V4_MONTH" "$V4_STAGES" "$ENVF" "$MD"
