#!/bin/bash
# chain_fp2_run.sh — FP2-8 unattended runner (2026-09-17; DESIGN_FP2-8 §3 + AMENDMENT 2/3). Runs the remaining stages of chain_v4_monthly.sh on the FP2
# contract IN ORDER, stopping at the first non-zero rc; the controls receipt must be PASS before `gates`; both arms are evaluated under the tradable
# umask (V4_UMASK_NPZ, read by run_v4_arms.sh); A0 is RE-RUN under that umask AFTER the driver's arms stage (build_dev_v4 has by then re-linked the dev
# tree to this root and re-projected A0's king score / F10 preds onto this root's axes) and BEFORE judge; the four A0 probe artifacts' shas before/after
# are receipted. usage: bash chain_fp2_run.sh <fp2.env> [stage ...]   default: data_wait controls_run gates king legs mwf refit np_export arms a0rerun judge export; then per_year decision (F03)
set -o pipefail
D=$(cd "$(dirname "$0")" && pwd -P); export CHAIN_DEVICE_DIR=$D; ENVF=$1; shift; STAGES=${*:-"data_wait controls_run gates king legs mwf refit np_export arms a0rerun judge export member_rule per_year decision"}   # R10: the default run ENDS with the decision, not before it
[ -n "$ENVF" ] && [ -f "$ENVF" ] || { echo "usage: chain_fp2_run.sh <fp2.env> [stages]" >&2; exit 2; }
L=/dev/stderr; . "$D/chain_lib.sh"; export D PY R; load_month_env "$ENVF" || exit 4
LOG=$R/chain_fp2_run.log; say2(){ echo "[$(date -u +%FT%TZ)] $*" | tee -a "$LOG"; }
UM=${FP2_UMASK_NPZ:-/workspace/fx_data_2026-09-13/out/inject/umask_UPIT_CRYPTO_tradable_W24H.npz}   # evaluation umask for BOTH arms (DESIGN §2.2 / AMENDMENT 1.2), sha 3badc4b6…
[ -f "$UM" ] || { say2 "FAIL_umask_missing $UM"; exit 3; }
export V4_UMASK_NPZ=$UM
BT=${BUILDER_TARGETS:-pod_dlw_targets_raw.py}; BK=${BUILDER_KING_FEA:-pod_fea_ext_clamp.py}   # same selection rule as the driver
say2 "chain_fp2_run start env=$ENVF sha=$(gate_sha "$ENVF") device=$D root=$R stages=[$STAGES] umask=$UM ($(gate_sha "$UM" | cut -c1-8))"
for st in $STAGES; do
  case $st in
    data_wait)   # the data stage was launched separately (V4_STAGES=data); wait for its subset-DONE marker, fail on its FAIL_ marker
      say2 "data_wait: $R/chain_fp2_stage_data.log"; n=0
      until grep -aq "CHAIN_V4_MONTHLY_STAGES_DONE" "$R/chain_fp2_stage_data.log" 2>/dev/null; do
        grep -aq "^FAIL_\|FAIL_" "$R/chain_fp2_stage_data.log" 2>/dev/null && { say2 "FAIL_data_stage: $(grep -a "FAIL_" "$R/chain_fp2_stage_data.log" | tail -1 | cut -c1-120)"; exit 3; }
        sleep 60; n=$((n+1)); [ $n -gt 300 ] && { say2 "FAIL_data_timeout_5h"; exit 3; }; done
      say2 "data stage DONE ($(grep -a "STAGES_DONE" "$R/chain_fp2_stage_data.log" | tail -1 | cut -c1-100))" ;;
    controls_run)   # AMENDMENT 5: the king builder peaks ~50-58 GB against the container's 61 GB cgroup cap — it must run ALONE, i.e. only after the data stage
      REC=$R/controls/CONTROLS.json
      if [ -f "$REC" ] && [ "$("$PY" -c "import json,sys; print(json.load(open(sys.argv[1])).get('VERDICT'))" "$REC")" = PASS ]; then say2 "controls_run: existing receipt PASS, reused ($(gate_sha "$REC" | cut -c1-8))"
      else
        [ -d "$R/controls" ] && { mv "$R/controls" "$R/controls_failed_$(date -u +%Y%m%dT%H%M%SZ)"; say2 "controls_run: previous controls dir moved aside as a receipt"; }
        say2 "controls_run: fp2_controls.py (alone; king ≈50-58 GB vs cgroup 61 GB)"
        env -i PATH="$PATH" HOME="$HOME" OMP_NUM_THREADS=8 R=$R D=$D PY=$PY CACHE=$CACHE PANEL_SPLICE=$PANEL_SPLICE PANEL_KING=$PANEL_KING RAW_PATCH=$RAW_PATCH \
            SEPT_KING_FEA=${FP2_SEPT_KING_FEA:-/workspace/data/wide_fea_v4.npy} SEPT_KING_META=${FP2_SEPT_KING_META:-/workspace/data/wide_fea_v4_meta.npz} SEPT_DL_TARGETS=${FP2_SEPT_DL_TARGETS:-/workspace/dlw_v4raw/data/dlw_targets.npz} \
            BUILDER_TARGETS=$BT BUILDER_KING_FEA=$BK "$PY" -B "$D/fp2_controls.py" > "$R/fp2_controls.log" 2>&1 < /dev/null; rc=$?
        v=$( [ -f "$REC" ] && "$PY" -c "import json,sys; print(json.load(open(sys.argv[1])).get('VERDICT'))" "$REC" ); say2 "controls_run rc=$rc VERDICT=$v"
        [ "$v" = PASS ] || { say2 "FAIL_controls_verdict_${v:-none}"; exit 3; }
      fi ;;
    controls_wait)
      say2 "controls_wait: $R/controls/CONTROLS.json"; n=0
      until [ -f "$R/controls/CONTROLS.json" ]; do sleep 60; n=$((n+1)); [ $n -gt 300 ] && { say2 "FAIL_controls_timeout_5h"; exit 3; }; done
      v=$("$PY" -c "import json,sys; print(json.load(open(sys.argv[1])).get('VERDICT'))" "$R/controls/CONTROLS.json")
      [ "$v" = PASS ] || { say2 "FAIL_controls_verdict_$v"; exit 3; }; say2 "controls PASS ($(gate_sha "$R/controls/CONTROLS.json" | cut -c1-8))" ;;
    a0rerun)
      REC=$R/v4_gates/A0_RERUN_TRADABLE.json; ARTS="$HC/dev_v4/probe_artifacts"
      say2 "a0rerun: run_v4_arms.sh A0 seeds=[${SEEDS//,/ }] V4_HC=$HC V4_KING_DIR=$KING_DIR V4_UMASK_NPZ=$UM"
      [ -f "$HC/dev_v4/BUILD.json" ] || { say2 "FAIL_a0rerun_prereq_build_dev_v4 (run the arms stage first: build_dev_v4 re-links the dev tree to this root)"; exit 3; }
      BEFORE=$("$PY" - "$ARTS" <<'PY'
import hashlib, json, os, sys
a = sys.argv[1]; fs = sorted(f for f in os.listdir(a) if f.startswith("w10_ablation_series_V4_A0_") and f.endswith(".npz"))
print(json.dumps({f: hashlib.sha256(open(os.path.join(a, f), "rb").read()).hexdigest() for f in fs}))
PY
)
      T_START=$(date +%s)
      ( cd "$HC" && V4_HC=$HC V4_KING_DIR=$KING_DIR V4_UMASK_NPZ=$UM bash "$D/run_v4_arms.sh" A0 "${SEEDS//,/ }" ) > "$R/arms_A0_tradable.log" 2>&1 < /dev/null; rc=$?
      grep -aq "ARMS_DONE" "$R/arms_A0_tradable.log" || rc=$((rc == 0 ? 1 : rc))
      AFTER=$("$PY" - "$ARTS" <<'PY'
import hashlib, json, os, sys
a = sys.argv[1]; fs = sorted(f for f in os.listdir(a) if f.startswith("w10_ablation_series_V4_A0_") and f.endswith(".npz"))
print(json.dumps({f: hashlib.sha256(open(os.path.join(a, f), "rb").read()).hexdigest() for f in fs}))
PY
)
      ARTS=$ARTS "$PY" - "$REC" "$BEFORE" "$AFTER" "$UM" "$rc" "$R/arms_A0_tradable.log" "$T_START" <<'PY'
import hashlib, json, sys, time
out, before, after, um, rc, log = sys.argv[1:7]; b = json.loads(before); a = json.loads(after)
# R11 (independent review round 2): "every artifact changed" rejected a correct idempotent re-run. The receipt now proves EXECUTION and IDENTITY:
#   rc 0 + ARMS_DONE, and every A0 artifact present now was (re)written by THIS run (mtime ≥ the run's start) under THIS umask (its cfg UMASK_NPZ),
#   with the before/after shas recorded as information.
import numpy as np, os
t_start = float(sys.argv[7]) if len(sys.argv) > 7 else 0.0; arts = os.path.dirname(log) and os.path.join(os.environ.get("ARTS", ""), "")
arts_dir = os.environ["ARTS"]; um_sha = hashlib.sha256(open(um, "rb").read()).hexdigest(); per = {}
for f in sorted(a):
    p = os.path.join(arts_dir, f); z = np.load(p, allow_pickle=True); cfg = json.loads(str(z["config_json"])) if "config_json" in z.files else {}
    per[f] = {"written_by_this_run": os.path.getmtime(p) >= t_start, "cfg_umask": cfg.get("UMASK_NPZ"), "cfg_umask_is_this_umask": os.path.realpath(str(cfg.get("UMASK_NPZ") or "")) == os.path.realpath(um), "fseed": cfg.get("FSEED"), "sha_before": b.get(f, "")[:12], "sha_after": a[f][:12], "changed": b.get(f) != a[f]}
ok = rc == "0" and len(a) >= 4 and all(v["written_by_this_run"] and v["cfg_umask_is_this_umask"] for v in per.values())
rec = {"gate": "A0_RERUN_TRADABLE", "PASS": bool(ok), "rc": int(rc), "umask": um, "umask_sha256": um_sha, "run_start_utc": time.strftime("%FT%TZ", time.gmtime(t_start)), "artifacts": per, "log": log, "utc": time.strftime("%FT%TZ", time.gmtime()),
       "meaning": "A0 (in-service form) re-run under the SAME tradable umask as A1 (DESIGN_FP2-8 §2.2): rc 0 + ARMS_DONE, every artifact written by this run and carrying this umask in its cfg; an identical re-run is a PASS (R11)"}
json.dump(rec, open(out, "w"), indent=1); print("A0_RERUN", "PASS" if rec["PASS"] else "FAIL", {k[:40]: (v["written_by_this_run"], v["cfg_umask_is_this_umask"], v["changed"]) for k, v in per.items()})
PY
      say2 "a0rerun rc=$rc receipt $REC"; [ $rc -eq 0 ] && "$PY" -c "import json,sys; sys.exit(0 if json.load(open(sys.argv[1]))['PASS'] else 1)" "$REC" || { say2 "FAIL_a0rerun"; exit 1; } ;;
    member_rule)   # R09: the masked builds must be EXACTLY the builders' rule (recomputed from the cache); receipt bound by the decision stage
      env CACHE=$CACHE RAW_PATCH=$RAW_PATCH MEMBER_MASK=$MEMBER_MASK CONTROL_KING_META=$R/controls/king_nomask/wide_fea_v4_meta.npz MASKED_KING_META=$KING_META \
          CONTROL_DL_TARGETS=$R/controls/dl_nomask/data/dlw_targets.npz MASKED_DL_TARGETS=$DLW_RAW/data/dlw_targets.npz OUT_JSON=$R/v4_gates/MEMBER_RULE_CHECK.json \
          nice -n 10 "$PY" -u "$D/fp2_member_rule_check.py" > "$R/member_rule_check.log" 2>&1 < /dev/null; rc=$?
      say2 "stage member_rule rc=$rc $(tail -1 "$R/member_rule_check.log" | cut -c1-160)"; [ $rc -eq 0 ] || { say2 "FAIL_stage_member_rule_rc_$rc"; exit $rc; } ;;
    per_year)   # F03/F09/F10: the per-year table (judge-same arm records, both arms under the same umask, per-anchor maxDD, W_ALPHA pinned to a time)
      REC=$R/v4_gates/A0_RERUN_TRADABLE.json
      [ -f "$REC" ] && "$PY" -c "import json,sys; sys.exit(0 if json.load(open(sys.argv[1]))['PASS'] else 1)" "$REC" || { say2 "FAIL_per_year_prereq_a0rerun (A0 must be re-run under the same umask first)"; exit 3; }
      grep -aq "ARMS_DONE" "$R/arms_${EXPORT_ARM:-A1}.log" 2>/dev/null || { say2 "FAIL_per_year_prereq_arms_${EXPORT_ARM:-A1}"; exit 3; }
      env ARMS_DIR=$HC/dev_v4/probe_artifacts UMASK_NPZ=$UM ARMS=A0,${EXPORT_ARM:-A1} SEATS=dyn SEEDS=$SEEDS OUT_JSON=$R/v4_gates/PER_YEAR_TABLE.json OUT_MD=$R/v4_gates/PER_YEAR_TABLE.md \
        "$PY" "$D/fp2_per_year_table.py" > "$R/per_year_table.log" 2>&1 < /dev/null; rc=$?
      say2 "stage per_year rc=$rc $(tail -1 "$R/per_year_table.log" | cut -c1-160)"; [ $rc -eq 0 ] || { say2 "FAIL_stage_per_year_rc_$rc"; exit $rc; } ;;
    decision)   # F03: the swap recommendation under AMENDMENT 7 (G1′ non-inferiority × G2 per-year × G3 export gate); judge receipt informational only
      env R=$R D=$D PROFILE=formal PER_YEAR_JSON=$R/v4_gates/PER_YEAR_TABLE.json EXPORT_RECEIPT=$R/v4_gates/BUNDLE_export_v2_${EXPORT_ARM:-A1}.json JUDGE_JSON=$R/v4_gates/JUDGE_v4_eligible.json \
        MEMBER_RULE_JSON=$R/v4_gates/MEMBER_RULE_CHECK.json STEP1_JSON=$R/v4_gates/step1.json EXPECTED_UMASK=$UM \
        OUT_JSON=$R/v4_gates/DECISION_FP2.json OUT_MD=$R/v4_gates/DECISION_FP2.md "$PY" "$D/fp2_decision.py" > "$R/decision_fp2.log" 2>&1 < /dev/null; rc=$?
      say2 "stage decision rc=$rc $(tail -1 "$R/decision_fp2.log" | cut -c1-160)"; [ $rc -eq 0 ] || { say2 "FAIL_stage_decision_rc_$rc"; exit $rc; } ;;
    *)
      say2 "stage $st: V4_STAGES=$st chain_v4_monthly.sh"
      env V4_STAGES=$st bash "$D/chain_v4_monthly.sh" "$ENVF" > "$R/chain_fp2_stage_$st.log" 2>&1 < /dev/null; rc=$?
      say2 "stage $st rc=$rc $(tail -1 "$R/chain_fp2_stage_$st.log" | cut -c1-160)"; [ $rc -eq 0 ] || { say2 "FAIL_stage_${st}_rc_$rc"; exit $rc; } ;;
  esac
done
say2 "CHAIN_FP2_RUN_DONE stages=[$STAGES]"
