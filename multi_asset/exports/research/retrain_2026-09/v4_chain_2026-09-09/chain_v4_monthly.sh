#!/bin/bash
# chain_v4_monthly.sh — THE single ordered driver of the v4 monthly retrain (RUNBOOK_monthly_retrain_2026-10 §0★ 修订 3, 2026-09-12; independent
# review 0dfc0d87 R1–R5 all accepted). usage:
#   bash chain_v4_monthly.sh <v4_month_<YYYY-MM>.env>            # every stage, in order; DONE only when every stage succeeded
#   V4_STAGES=preflight,gates bash chain_v4_monthly.sh <env>     # a subset (comma list of the stage names below) — every stage still requires its
#                                                                #   upstream receipts/markers, so a subset cannot skip a gate, only skip WORK
#   V4_DRYRUN=1 bash chain_v4_monthly.sh <env>                   # NEGATIVE-CONTROL mode: any stage after preflight dies BEFORE launching anything
# B-R1 (independent review 2026-09-12): EVERY stage first verifies its PREREQUISITES in this root, bound to this contract/inputs (chain_lib prereq_*: preflight
#   receipt PASS with this contract's sha, upstream receipts/markers, pinned-input identity, refit sidecars fix7 + identical inputs, END rows) and dies
#   FAIL_<stage>_prereq_<name> (rc 3) BEFORE any guard/dispatch — a subset such as V4_STAGES=refit cannot skip a gate. B-R3: the data stage's subprocesses run
#   under `env -i` with an allowlist + every variable they read set explicitly (the CLIP build gets DLWT_RAW_PATCH= empty), so nothing ambient leaks in.
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
# ★ FP2-8 (2026-09-17, DESIGN_FP2-8 AMENDMENT 1.3): the data-stage builders are contract-selected BY BASENAME in D (optional keys; default = the frozen
#   v1 names, so every existing contract is unchanged); a selected builder must be a bare basename that exists in D. MEMBER_MASK (optional) reaches
#   BOTH builders as MEMBER_MASK_NPZ; empty ⇒ the builders behave as v1 (all-True). Both selected builders join DEV_FILES (sha-recorded by preflight). Defined at TOP LEVEL: every stage subset (V4_STAGES=data …) needs them, not only preflight.
BT=${BUILDER_TARGETS:-pod_dlw_targets_raw.py}; BK=${BUILDER_KING_FEA:-pod_fea_ext_clamp.py}
case "$BT$BK" in */*) die "builder_key_not_a_basename_${BT}_${BK}" 4 ;; esac
[ -f "$D/$BT" ] || die "builder_missing_in_D_$BT" 3; [ -f "$D/$BK" ] || die "builder_missing_in_D_$BK" 3
# ★ R12-C5 (2026-09-18): a DECLARED-but-absent mask is reported by PREFLIGHT ("input missing: MEMBER_MASK=…"), not by a top-level die. The same
#   reasoning the roll gate carries: a prerequisite that stops before any receipt is written reads exactly like a crash, and the negative control's
#   criterion is an HONEST preflight receipt. Every stage that consumes the mask sits behind `prereq_receipt <stage> preflight`, so a missing mask
#   still blocks all of them — it just does so with a named failure in the receipt. (Same for UMASK_NPZ below.)
# ★ FP3 F (2026-09-18, user word on PROPOSED6): the MEMBER_LIVENESS gate is contract-selected BY BASENAME (optional key GATE_LIVENESS, default the frozen name),
#   must exist in D, is a DEV_FILE, its approval is checked in preflight (4th approval) and it RUNS in the gates stage on the produced member sets; the export
#   stage re-runs it on the shipped bundle's live list. UMASK_NPZ (optional key) is the evaluation umask of the decision path; preflight binds its sha to the
#   contract's approved_baseline.umask_npz_sha256 (a different mask cannot reach per_year/decision).
GL=${GATE_LIVENESS:-v4_gate_member_liveness.py}; case "$GL" in */*|.*) die "gate_liveness_not_a_basename_$GL" 4 ;; esac; [ -f "$D/$GL" ] || die "gate_liveness_missing_in_D_$GL" 3
# ★ R13-C1 (independent review round 13): the artefacts a MEMBER_LIVENESS receipt must have been produced FROM, for this run. Passed to every
#   consumer's prereq_receipt so a genuine PASS written from another candidate's data is refused (the reviewer transplanted exactly such a ticket
#   into a root whose own run FAILS the gate, and both the prerequisite and the decision accepted it). The export end adds bundle_config.
LIVE_BIND=("cache=$CACHE" "hole_cells=$HOLE_CELLS" "wide_fea_v4_meta=$KING_META" "dlw_v4raw_targets=$DLW_RAW/data/dlw_targets.npz")
[ -z "${MEMBER_MASK:-}" ] || LIVE_BIND+=("member_mask=$MEMBER_MASK")   # an ARRAY: a path with a space must not word-split into two bindings

stage "chain_v4_monthly start month=$V4_MONTH env=$ENVF sha=$(gate_sha "$ENVF" || echo unreadable) device=$D root=$R stages=$V4_STAGES dryrun=$DRY"

# ── preflight ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
if want preflight; then
  # ── FX-TRAIN TRN-01: for any month AFTER September, preflight additionally requires the ROLL_PATHS receipt. Preflight checks that
  #    each contract path EXISTS, and a path that exists because LAST month put it there passes — which is exactly how a new month
  #    ends up reading September's data or overwriting files September's receipts hash (E-0912-B). ROLL_PATHS decides the other
  #    question: that this month is not pointed at the previous month's artifacts. September is excluded by construction — its
  #    contract predates the isolation convention and is the counter-example the gate exists for; string comparison is correct for
  #    YYYY-MM. It is checked INSIDE preflight, not as a prerequisite, so a missing or wrong receipt appears in preflight's own
  #    fails list: the negative control's criterion is that the empty root produces an HONEST preflight receipt (PASS=false with
  #    named failures), and a prerequisite would stop before any receipt was written, which reads the same as a crash.
  V4_ROLL_REQUIRED=0; [ "$V4_MONTH" \> "2026-09" ] && V4_ROLL_REQUIRED=1
  V4_ROLL_SRC=""; [ "$V4_ROLL_REQUIRED" = 1 ] && { V4_ROLL_SRC=$(gate_sha "$D/v4_gate_roll_paths.py") || die "gate_source_unreadable_v4_gate_roll_paths" 3; }
  stage "preflight: device files, gate approval, inputs (roll_paths required: $V4_ROLL_REQUIRED)"
  DEV_FILES="chain_lib.sh chain_v4_monthly.sh v4_months.py v4_gate_common.py ELIGIBILITY_CONTRACT.json $GATE_STEP1 $GATE_STEP2 ${GATE_EXPORT:-v4e_gate_export_v2.py} v4e_export_baseline_lib.py $GL v4_member_mask_liveness.py fp2_gate_lib.py fp2_controls.py fp2_member_rule_check.py fp2_per_year_table.py fp2_decision.py pod_dlw_targets_raw.py pod_fea_ext_clamp.py $BT $BK pod_export_bundle_v4.py pod_legs_v4b.py pod_f10_train_monthly_v4.py launch_mwf_v4b.sh merge_mwf_v4b.py pod_f10_refit_v4.py build_dev_v4.py run_v4_arms.sh run_arm.sh judge_v4.py v4e_gate_export_v2.py gate_signal_parity_v2.py cache_coverage_gate_v2.py"
  PF_INPUTS="CACHE PANEL_SPLICE PANEL_KING RAW_PATCH HOLE_CELLS BUNDLE_BASE EXPORT_PANEL EMA_STATE_JSON LIVE_PINS FUND_AUG FUNDING_DIR LEGS_OLD LEGS_PANEL SIGNAL_RECEIPT BUILDER_FEA82 BUILDER_FEA89 BASE_TRAINER PREV_META REF_META"
  [ -z "${MEMBER_MASK:-}" ] || PF_INPUTS="$PF_INPUTS MEMBER_MASK"   # FP2-8: a declared mask is a preflight-hashed input
  [ -z "${UMASK_NPZ:-}" ] || PF_INPUTS="$PF_INPUTS UMASK_NPZ"   # FP3 F: the evaluation umask is a preflight-hashed input, bound to the contract sha below
  # ★ R12-C5 (independent review round 12): the controls stage's REFERENCE builds are the thing its verdict is measured against, so they are
  #   preflight-hashed inputs AND bound to a per-month approval in the contract — the same shape as UMASK_NPZ. Without this a month could aim the
  #   comparison at any file and still be told PASS.
  for _k in CONTROLS_REF_KING_FEA CONTROLS_REF_KING_META CONTROLS_REF_DL_TARGETS; do
    eval "_v=\${$_k:-}"; [ -z "$_v" ] || PF_INPUTS="$PF_INPUTS $_k"
  done
  # ★ FP2-3 (2026-09-17): for a month that needs the roll gate, the previous contract and its sha record must be DECLARED in this
  #   month's contract (optional keys PREV_MONTH_ENV / PREV_SHA_JSON), and the roll gate is RE-RUN HERE, live, against them — an
  #   archived ROLL_PATHS receipt is no longer sufficient: "改旧 CACHE 后旧 PASS 仍被接受" (independent review 2026-09-17). The live
  #   rerun's receipt is written beside the archived one and its VERDICT must be PASS (three-state; UNAVAILABLE is not PASS).
  V4_ROLL_LIVE_RC=""; V4_ROLL_LIVE_OUT="$R/v4_gates/ROLL_PATHS_preflight_live.json"
  if [ "$V4_ROLL_REQUIRED" = 1 ] && [ -n "${PREV_MONTH_ENV:-}" ] && [ -n "${PREV_SHA_JSON:-}" ] && [ -f "$D/v4_gate_roll_paths.py" ]; then
    env -i PATH="$PATH" HOME="$HOME" V4_MONTH_ENV="$ENVF" ROLL_PREV_MONTH_ENV="$PREV_MONTH_ENV" ROLL_PREV_SHA_JSON="$PREV_SHA_JSON" \
        ROLL_ALLOW_OUTSIDE_ROOT="${ROLL_ALLOW_OUTSIDE_ROOT:-}" ROLL_OUT="$V4_ROLL_LIVE_OUT" "$PY" "$D/v4_gate_roll_paths.py" > "$R/v4_gates/roll_paths_preflight_live.log" 2>&1
    V4_ROLL_LIVE_RC=$?
  fi
  V4_DEV_FILES="$DEV_FILES" V4_PF_INPUTS="$PF_INPUTS" V4_ROLL_REQUIRED="$V4_ROLL_REQUIRED" V4_ROLL_SRC="$V4_ROLL_SRC" V4_MONTH_ENV="$V4_MONTH_ENV" \
  V4_ROLL_LIVE_RC="$V4_ROLL_LIVE_RC" V4_ROLL_LIVE_OUT="$V4_ROLL_LIVE_OUT" V4_PREV_MONTH_ENV="${PREV_MONTH_ENV:-}" V4_PREV_SHA_JSON="${PREV_SHA_JSON:-}" "$PY" - "$R/v4_gates/preflight.json" <<'PYEOF'; rc=$?
import hashlib, json, os, re, subprocess, sys, time
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
# FX-TRAIN TRN-01: the roll receipt, verified here so its verdict lands in THIS receipt's fails (see the comment above the stage)
roll = {"required": E.get("V4_ROLL_REQUIRED") == "1"}
if roll["required"]:
    rp = os.path.join(R, "v4_gates", "ROLL_PATHS.json"); roll["receipt"] = rp
    if not os.path.isfile(rp):
        fails.append(f"roll receipt missing: {rp} (every month after 2026-09 must pass v4_gate_roll_paths.py first)")
    else:
        try:
            rr = json.load(open(rp))
        except Exception as e:                                                  # noqa: BLE001
            rr = None; fails.append(f"roll receipt unreadable: {type(e).__name__}: {e}")
        if rr is not None:
            roll["gate"], roll["PASS"], roll["self_sha256"] = rr.get("gate"), rr.get("PASS"), rr.get("self_sha256")
            if rr.get("gate") != "ROLL_PATHS": fails.append(f"roll receipt is from gate {rr.get('gate')!r}, expected 'ROLL_PATHS'")
            if rr.get("PASS") is not True: fails.append(f"roll receipt says PASS={rr.get('PASS')!r} ({rr.get('utc')})")
            if E.get("V4_ROLL_SRC") and rr.get("self_sha256") != E["V4_ROLL_SRC"]:
                fails.append(f"roll receipt was written by gate source {str(rr.get('self_sha256'))[:12]}, this chain trusts {E['V4_ROLL_SRC'][:12]}")
            me = E.get("V4_MONTH_ENV") or ""
            rec_env = (rr.get("inputs_sha256") or {}).get("month_env")
            roll["month_env_sha256_recorded"] = rec_env
            if not me or not os.path.isfile(me):
                fails.append(f"roll receipt cannot be bound: V4_MONTH_ENV={me!r} is not a readable file")
            elif rec_env != sha(me):
                fails.append(f"roll receipt was written for a contract with sha {str(rec_env)[:12]}, this run's contract is {sha(me)[:12]}")
    # ★ FP2-3: the previous contract must be DECLARED and the roll gate RE-RUN live now — the archived receipt above proves what was true
    #   when it was written, not that the previous month's artifacts are still what its record says.
    roll["prev_month_env"] = E.get("V4_PREV_MONTH_ENV") or None; roll["prev_sha_json"] = E.get("V4_PREV_SHA_JSON") or None
    if not roll["prev_month_env"] or not roll["prev_sha_json"]:
        fails.append("previous contract not declared: this month's contract must carry PREV_MONTH_ENV and PREV_SHA_JSON (FP2-3) so the roll gate can be re-verified at startup")
    else:
        for k in ("prev_month_env", "prev_sha_json"):
            if not os.path.isfile(roll[k]): fails.append(f"{k}={roll[k]} is not a readable file")
        lrc = E.get("V4_ROLL_LIVE_RC"); lout = E.get("V4_ROLL_LIVE_OUT")
        roll["live_rerun"] = {"rc": lrc, "receipt": lout}
        lr = None
        if os.path.isfile(lout or ""):
            try: lr = json.load(open(lout))
            except Exception as e:                                              # noqa: BLE001
                fails.append(f"live roll rerun receipt unreadable: {type(e).__name__}: {e}")
        if lr is None:
            fails.append(f"live roll gate rerun produced no receipt (rc={lrc!r})")
        else:
            roll["live_rerun"].update({"VERDICT": lr.get("VERDICT"), "PASS": lr.get("PASS"), "failed_checks": lr.get("failed_checks"), "unevaluated_checks": lr.get("unevaluated_checks")})
            if lrc != "0" or lr.get("VERDICT") != "PASS" or lr.get("PASS") is not True:
                fails.append(f"live roll gate rerun is not PASS: rc={lrc} VERDICT={lr.get('VERDICT')!r} failed={lr.get('failed_checks')} unevaluated={lr.get('unevaluated_checks')}")
for k in E["V4_PF_INPUTS"].split():
    p = E[k]
    if os.path.exists(p): inputs[k] = {"path": p, "bytes": os.path.getsize(p) if os.path.isfile(p) else None, "is_dir": os.path.isdir(p), "sha256": (sha(p) if os.path.isfile(p) else None)}   # FP3 J (review C2): content identity, not existence
    else: fails.append(f"input missing: {k}={p}")
for k in ("DLW_EXT", "F8_EXT"):
    for rel in (("data/dlw_targets.npz",) if k == "DLW_EXT" else tuple(f"preds/f10_V2MAIN_s{s}.npy" for s in E["SEEDS"].split(","))):
        p = os.path.join(E[k], rel)
        if os.path.isfile(p): inputs[f"{k}/{rel}"] = {"path": p, "bytes": os.path.getsize(p), "sha256": sha(p)}
        else: fails.append(f"input missing: {k}/{rel}={p}")
p = os.path.join(E["PREV_BUNDLE"], "slow_pred_pinned.npy")
if os.path.isfile(p): inputs["PREV_BUNDLE/slow_pred_pinned.npy"] = {"path": p, "bytes": os.path.getsize(p), "sha256": sha(p)}
else: fails.append(f"input missing: PREV_BUNDLE/slow_pred_pinned.npy={p}")
HC = E["HC"]
for rel in ["masks/umask_UPIT_CRYPTO.npz", "calib/costb_fee_steady.json"] + [f"dev_v4/probe_artifacts/w10_ablation_series_V4_A0_{seat}_s{s}.npz" for seat in ("dyn", "fix") for s in (42, 2027)]:   # FP3 J: run_arm.sh is a DEVICE file now (DEV_FILES), not a tree input
    p = os.path.join(HC, rel)
    if os.path.isfile(p): inputs[f"HC/{rel}"] = {"path": p, "bytes": os.path.getsize(p), "sha256": sha(p)}
    else: fails.append(f"dev tree file missing: HC/{rel}={p}")
approval = {}
if E.get("UMASK_NPZ"):   # FP3 F: the evaluation umask must be an APPROVED file (sha), not "whatever is on disk"
    _c = json.load(open(os.path.join(D, "ELIGIBILITY_CONTRACT.json")))
    # ★ R12-C5 follow-on: this was bound to gates.BUNDLE_export.approved_baseline.umask_npz_sha256 for EVERY month — but that value is SEPTEMBER's
    #   evaluation umask, so a later month had to reuse September's mask or be refused for the wrong reason. The approval is per month; the
    #   baseline field is the 2026-09 entry. A month with no entry is refused BY NAME instead of being compared against another month's file.
    _pm = ((((_c.get("month_contract_rulings") or {}).get("CONTROLS_REF_identity") or {}).get("approved_controls_refs") or {}).get(E["V4_MONTH"]) or {})
    _want = ((_pm.get("UMASK_NPZ") or {}).get("sha256")) or None
    _got = inputs.get("UMASK_NPZ", {}).get("sha256")
    if "UMASK_NPZ" in inputs: inputs["UMASK_NPZ"]["contract_umask_npz_sha256"] = _want
    if not _want: fails.append(f"no approved UMASK_NPZ for month {E['V4_MONTH']} in the contract (month_contract_rulings.CONTROLS_REF_identity.approved_controls_refs): "
                               f"the evaluation umask is a per-month approval object and this month has none (R12-C5)")
    elif not _got or _got != _want: fails.append(f"UMASK_NPZ sha {str(_got)[:12]} != the sha approved for month {E['V4_MONTH']} {str(_want)[:12]} (R12-C5)")
# ★ R12-C5 (a): a month AFTER September must DECLARE the member mask and the evaluation umask. With the v1 defaults the data stage builds members
#   WITHOUT the liveness mask, and the MEMBER_LIVENESS gate would then fail the very month it governs — a silent wrong-input run, not a refusal.
#   September is excluded by construction (its contract predates both keys and is the counter-example); string comparison is correct for YYYY-MM.
# `V4_MONTH` must look like a CALENDAR month for this rule to apply: the test harness uses deliberately impossible labels (e.g. 2026-99) to
#   exercise driver plumbing, and a synthetic month cannot satisfy a real approval. A real month cannot hide behind that: an impossible label is
#   recorded in the receipt as `month_label_not_calendar`, and every path/roll check still applies to it.
_cal = bool(re.fullmatch(r"20\d\d-(0[1-9]|1[0-2])", str(E["V4_MONTH"] or "")))
if not _cal: inputs["_month_label"] = {"value": E["V4_MONTH"], "month_label_not_calendar": True}
_post_sept = _cal and str(E["V4_MONTH"]) > "2026-09"
if _post_sept:
    for _k in ("MEMBER_MASK", "UMASK_NPZ"):
        if not E.get(_k): fails.append(f"month {E['V4_MONTH']} is after 2026-09 and its contract does not declare {_k}: the data stage would build members without the liveness mask (R12-C5)")
# ★ R12-C5 (b): every DECLARED controls reference must carry the sha approved for THIS month in the contract; a month with no approved entry
#   cannot run the controls stage at all, and says so by name rather than comparing against whatever happens to be on disk.
_refs = {k: E.get(k) for k in ("CONTROLS_REF_KING_FEA", "CONTROLS_REF_KING_META", "CONTROLS_REF_DL_TARGETS") if E.get(k)}
if _refs:
    _cc = json.load(open(os.path.join(D, "ELIGIBILITY_CONTRACT.json")))
    _all = (((_cc.get("month_contract_rulings") or {}).get("CONTROLS_REF_identity") or {}).get("approved_controls_refs") or {})
    _app = _all.get(E["V4_MONTH"])
    if not _app:
        fails.append(f"no approved CONTROLS_REF for month {E['V4_MONTH']} in the contract (month_contract_rulings.CONTROLS_REF_identity.approved_controls_refs): "
                     f"the controls stage's reference builds are a per-month approval object and this month has none (R12-C5)")
    else:
        for _k, _v in _refs.items():
            _want = (_app.get(_k) or {}).get("sha256"); _got = inputs.get(_k, {}).get("sha256")
            if _k in inputs: inputs[_k]["contract_approved_sha256"] = _want
            if not _want: fails.append(f"{_k} is declared but not approved for month {E['V4_MONTH']} in the contract (R12-C5)")
            elif not _got or _got != _want: fails.append(f"{_k} sha {str(_got)[:12]} != approved {str(_want)[:12]} for month {E['V4_MONTH']} (R12-C5)")
# ★ TRN-15 (2026-09-21): the export gate's approved LIVE_PINS / BUNDLE_BASE are a PER-MONTH approval object too (the pins are
#   re-copied and the baseline json re-established EVERY month, RUNBOOK §0★ step 0). E2b enforces it, but E2b runs in the EXPORT
#   stage — after the whole chain. A month with no approved entry must be told here, in the same place UMASK_NPZ and
#   CONTROLS_REF_* are told. Preflight does NOT hash the two files (October's do not exist yet): it checks that an APPROVED
#   OBJECT exists for this month, which is the one thing building artefacts cannot fix.
sys.path.insert(0, D)
import v4e_export_baseline_lib as _xbl
_xc = json.load(open(os.path.join(D, "ELIGIBILITY_CONTRACT.json")))
_xent, _xwhy, _xdet = _xbl.approved_export_baseline(_xc, E["V4_MONTH"])
inputs["_export_baseline_approval"] = {"month": E["V4_MONTH"], "approved": _xent is not None, "refused": _xwhy,
                                       "months_declared": _xdet.get("months_declared"),
                                       "approved_shas": None if _xent is None else {k: _xent[k] for k in ("live_pins_sha256", "bundle_base_sha256")}}
inputs["_export_baseline_approval"]["enforced"] = _cal          # same scoping as R12-C5's MEMBER_MASK/UMASK rule: a CALENDAR month is a real
if _xent is None and _cal:                                      # month and must be approved; a non-calendar fixture label is RECORDED, not failed
    fails.append(f"no approved export baseline for month {E['V4_MONTH']} ({_xwhy}): LIVE_PINS / BUNDLE_BASE are a per-month approval "
                 f"object (month_contract_rulings.{_xbl.RULING_KEY}.{_xbl.MAP_KEY}); without it the export stage's E2b refuses "
                 f"AFTER the whole chain has run (TRN-15)")
elif _xent is None:
    inputs["_export_baseline_approval"]["not_enforced_why"] = ("V4_MONTH is not a calendar month (month_label_not_calendar), so this preflight "
        "check RECORDS the absence instead of failing — the same scoping R12-C5 gave MEMBER_MASK/UMASK. The EXPORT stage's E2b is NOT scoped "
        "this way: it refuses any month with no approved entry, calendar or not. ★ OPEN (inherited, RUNBOOK §0★ 修订 9): a non-calendar V4_MONTH "
        "is still only recorded and not refused anywhere in preflight.")
for gate, src in (("STEP1", E["GATE_STEP1"]), ("STEP2", E["GATE_STEP2"]), ("BUNDLE_export", E.get("GATE_EXPORT") or "v4e_gate_export_v2.py"), ("MEMBER_LIVENESS", E.get("GATE_LIVENESS") or "v4_gate_member_liveness.py")):
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
       "device_sha256": dev, "external_sha256": ext, "inputs": inputs, "gate_approval": approval, "months_all": E["MONTHS_ALL"], "seeds": seeds, "generation": E["BUNDLE_GENERATION"], "roll_paths": roll,
       "roll": roll,                                   # FP2-3: what preflight verified about the roll gate (archived receipt + live rerun)
       "fails": fails, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "dryrun": E.get("V4_DRYRUN", "0")}
os.makedirs(os.path.dirname(out), exist_ok=True); json.dump(res, open(out, "w"), indent=1)
print(f"PREFLIGHT {'PASS' if not fails else 'FAIL'} device_files={len(dev)} inputs={len(inputs)} approvals={sum(1 for a in approval.values() if a['ok'])}/4 fails={len(fails)}")
for f in fails[:12]: print("  -", f)
sys.exit(0 if not fails else 3)
PYEOF
  stage "preflight rc=$rc $(tail -1 "$R/v4_gates/preflight.json" >/dev/null 2>&1 && "$PY" -c "import json,sys;d=json.load(open(sys.argv[1]));print('PASS' if d['PASS'] else 'FAIL', len(d['fails']), 'fails', d['fails'][:3])" "$R/v4_gates/preflight.json")"
  [ $rc -eq 0 ] || die "preflight_rc_$rc" 3
  pin_deps preflight_device $(for f in $DEV_FILES; do echo "$D/$f"; done) "$BUILDER_FEA82" "$BUILDER_FEA89" "$BASE_TRAINER" "$ENVF"
fi

# ── cache coverage gate ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
if want cache; then
  prereq_receipt cache preflight "$R/v4_gates/preflight.json" PREFLIGHT
  guard cache; clean_env; CLEAN_ENV_C=("${CLEAN_ENV[@]}"); stage "cache: coverage gate v2 on $CACHE"
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
  # ── RAW_PATCH_COVERAGE (FX-TRAIN TRN-02): the second statement about this cache as a training input — that the raw-return patch
  #    covers EVERY clipped bar of it and that each patch row still addresses its recorded ts and symbol. STEP1 part A cannot see an
  #    OMISSION (a bar missing from the patch leaves RAW == CLIP there, so there is no difference to find), which is how E-0908-B can
  #    return silently on a new month: the September patch on the r6 x0910 cache leaves AKEUSDT / BULLAUSDT / WOOUSDT at +0.30.
  #    It runs HERE, beside the cache gate, and the data stage requires its receipt as a PREREQUISITE — so the data stage's five
  #    sealed subprocesses are unchanged, and no subset invocation can reach a builder without the receipt.
  #    Manifest path = the fixed sibling rule of v4_rawpatch_lib.manifest_path_for (<patch> minus .npz, plus .manifest.json): no new
  #    month-contract key, because the delivered contracts pin 46 keys verbatim.
  RPM=${RAW_PATCH%.npz}.manifest.json; RPR=$R/v4_gates/RAW_PATCH_COVERAGE.json
  stage "cache: RAW_PATCH_COVERAGE gate on $CACHE + $RAW_PATCH (manifest $RPM)"
  env -i "${CLEAN_ENV_C[@]}" CACHE=$CACHE RAW_PATCH=$RAW_PATCH RAW_PATCH_MANIFEST=$RPM RAWPATCH_OUT=$RPR "$PY" "$D/v4_gate_rawpatch.py" > "$R/raw_patch_coverage.log" 2>&1; rc=$?
  stage "rawpatch gate rc=$rc $(tail -1 "$R/raw_patch_coverage.log" | cut -c1-140)"; [ $rc -eq 0 ] || die "raw_patch_coverage_rc_$rc" 3
  RP_SRC=$(gate_sha "$D/v4_gate_rawpatch.py") || die "gate_source_unreadable_v4_gate_rawpatch" 3
  require_gate "$RPR" gate=RAW_PATCH_COVERAGE self_sha=$RP_SRC cache=$CACHE raw_patch=$RAW_PATCH raw_patch_manifest=$RPM
fi

# ── data chain ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
if want data; then
  prereq_receipt data preflight "$R/v4_gates/preflight.json" PREFLIGHT
  prereq_receipt data cache_coverage "$R/v4_gates/cache_coverage.json" CACHE_COVERAGE_v2
  prereq_json_eq data cache_identity "$R/v4_gates/cache_coverage.json" cache_sha256 "$(gate_sha "$CACHE")"   # the cache the coverage gate passed is the cache this stage reads
  # FX-TRAIN TRN-02: the raw-patch coverage receipt is a PREREQUISITE of this stage, produced by the cache stage. As a prerequisite it
  # is checked before the guard, so no subset invocation (V4_STAGES=data) can reach a builder without it, and require_gate re-verifies
  # that the receipt's recorded cache / patch / manifest shas are the files THIS stage is about to read.
  prereq_receipt data raw_patch_coverage "$R/v4_gates/RAW_PATCH_COVERAGE.json" RAW_PATCH_COVERAGE
  RPM=${RAW_PATCH%.npz}.manifest.json; RP_SRC=$(gate_sha "$D/v4_gate_rawpatch.py") || die "gate_source_unreadable_v4_gate_rawpatch" 3
  require_gate "$R/v4_gates/RAW_PATCH_COVERAGE.json" gate=RAW_PATCH_COVERAGE self_sha=$RP_SRC cache=$CACHE raw_patch=$RAW_PATCH raw_patch_manifest=$RPM
  guard data; DL=$R/chain_v4_data.log; : > "$DL"; clean_env
  mkdir -p "$DLW_RAW/data" "$DLW_RAW/results" "$DLW_CLIP/data" "$DLW_CLIP/results" "$F8/data" "$F8/results" "$F8/preds" "$F8/models" "$F8/logs" "$F8/gates" "$(dirname "$KING_FEA")" || die "data_mkdir" 1
  stage "data: RAW targets (holefix2 + raw_patch) -> $DLW_RAW"
  env -i "${CLEAN_ENV[@]}" DLWT_CACHE=$CACHE DLWT_PANEL=$PANEL_SPLICE DLWT_OUT=$DLW_RAW DLWT_RET_CH=0 DLWT_RAW_PATCH=$RAW_PATCH MEMBER_MASK_NPZ=${MEMBER_MASK:-} "$PY" "$D/$BT" >> "$DL" 2>&1 || die "targets_raw" 1   # B-R3: every DLWT_* the builder reads is set here
  [ -f "$DLW_RAW/data/dlw_targets.npz" ] || die "targets_raw_output_missing" 1
  stage "data: CLIP targets (holefix2, clipped ret5 channel, no patch) -> $DLW_CLIP"
  env -i "${CLEAN_ENV[@]}" DLWT_CACHE=$CACHE DLWT_PANEL=$PANEL_SPLICE DLWT_OUT=$DLW_CLIP DLWT_RET_CH=0 DLWT_RAW_PATCH= MEMBER_MASK_NPZ=${MEMBER_MASK:-} "$PY" "$D/$BT" >> "$DL" 2>&1 || die "targets_clip" 1   # B-R3: DLWT_RAW_PATCH EXPLICITLY EMPTY — the CLIP build never inherits a patch
  [ -f "$DLW_CLIP/data/dlw_targets.npz" ] || die "targets_clip_output_missing" 1
  stage "data: fea82 -> $DLW_CLIP (copied + verified to $DLW_RAW)"
  ( cd "$(dirname "$BUILDER_FEA82")" && env -i "${CLEAN_ENV[@]}" F171_CACHE=$CACHE F171_PANEL=$PANEL_SPLICE F171_OUT=$DLW_CLIP "$PY" "$BUILDER_FEA82" ) >> "$DL" 2>&1 || die "fea82" 1   # B-R3: the three F171_* the builder reads
  [ -f "$DLW_CLIP/data/dlw_fea82.npz" ] || die "fea82_output_missing" 1
  cp "$DLW_CLIP/data/dlw_fea82.npz" "$DLW_RAW/data/dlw_fea82.npz" || die "cp_fea82_to_raw" 1
  cmp -s "$DLW_CLIP/data/dlw_fea82.npz" "$DLW_RAW/data/dlw_fea82.npz" || die "cp_fea82_verify_mismatch" 1
  [ -f "$DLW_CLIP/results/dlw_features_report.json" ] && { cp "$DLW_CLIP/results/dlw_features_report.json" "$DLW_RAW/results/" || die "cp_fea82_report" 1; }
  stage "data: fea89 -> $F8"
  ( cd "$(dirname "$BUILDER_FEA89")" && env -i "${CLEAN_ENV[@]}" F8_DLW=$DLW_CLIP F8_CACHE=$CACHE F8_OUT=$F8 "$PY" "$BUILDER_FEA89" build ) >> "$DL" 2>&1 || die "fea89" 1   # B-R3: the three F8_* the builder reads
  [ -f "$F8/data/f8_fea89.npz" ] || die "fea89_output_missing" 1
  stage "data: king features ($BK) -> $KING_FEA"
  env -i "${CLEAN_ENV[@]}" CACHE_IN=$CACHE PANEL_IN=$PANEL_KING FEA_OUT=$KING_FEA META_OUT=$KING_META MEMBER_MASK_NPZ=${MEMBER_MASK:-} "$PY" "$D/$BK" >> "$DL" 2>&1 || die "king_fea" 1   # B-R3: the four env the clamp builder reads
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
# ── R03 (independent review round 2, 2026-09-17): every `require` of a STEP1/STEP2 receipt passes recorded_extras=1 — the inputs the RECEIPT recorded
#    beyond the caller's static declaration (controls receipt, member mask, gate helper, …) are re-hashed from the receipt's own inputs_path at every
#    later stage. A controls receipt edited after the gates passed made `require` say REQUIRE_OK before this (reviewer's counterexample).
# ── decision path (FP3 J, 2026-09-18; independent review round 11 C1): the single entry `chain_v4_monthly.sh <env>` used to END after export with
#    CHAIN_V4_MONTHLY_DONE and no formal decision; the formal steps lived only in chain_fp2_run.sh. They are stages of THIS driver now, in order
#    controls → a0rerun → member_rule → per_year → decision, each behind its prerequisites (a subset run cannot skip them), and `all` does not
#    write MONTHLY_DONE.json before the decision receipt exists. Ported verbatim from chain_fp2_run.sh (R09/F03/F09/F10 semantics); the month
#    contract supplies UMASK_NPZ (bound to the contract sha in preflight) and CONTROLS_REF_* (the reference builds the controls compare against).
#    ★ OPEN (stated, not hidden): fp2_decision.py's FORMAL profile is frozen on the FP2 evaluation window (W_ALPHA … 2026-08-30 20Z); a later month
#      needs its own pre-registered decision profile — until then the decision stage of a post-September month REFUSES (rc 3), by design.
if want controls; then
  prereq_receipt controls preflight "$R/v4_gates/preflight.json" PREFLIGHT
  for T in RAW CLIP; do prereq_file controls f10_gate_$T "$F8/gates/F10_GATE_$T.json"; done
  [ -n "${CONTROLS_REF_KING_FEA:-}" ] && [ -n "${CONTROLS_REF_KING_META:-}" ] && [ -n "${CONTROLS_REF_DL_TARGETS:-}" ] || die "controls_prereq_ref_keys_missing (month contract must set CONTROLS_REF_KING_FEA / CONTROLS_REF_KING_META / CONTROLS_REF_DL_TARGETS)" 3
  for f in "$CONTROLS_REF_KING_FEA" "$CONTROLS_REF_KING_META" "$CONTROLS_REF_DL_TARGETS"; do [ -f "$f" ] || die "controls_prereq_ref_missing_$(basename "$f")" 3; done
  guard controls; REC=$R/controls/CONTROLS.json
  if [ -f "$REC" ] && [ "$("$PY" -c "import json,sys; print(json.load(open(sys.argv[1])).get('VERDICT'))" "$REC")" = PASS ]; then stage "controls: existing receipt PASS, reused ($(gate_sha "$REC" | cut -c1-8))"
  else
    [ -d "$R/controls" ] && { mv "$R/controls" "$R/controls_failed_$(date -u +%Y%m%dT%H%M%SZ)"; stage "controls: previous controls dir moved aside as a receipt"; }
    stage "controls: fp2_controls.py (alone; king ≈50-58 GB vs cgroup 61 GB) refs $CONTROLS_REF_KING_META / $CONTROLS_REF_DL_TARGETS"
    env -i PATH="$PATH" HOME="$HOME" OMP_NUM_THREADS=8 R=$R D=$D PY=$PY CACHE=$CACHE PANEL_SPLICE=$PANEL_SPLICE PANEL_KING=$PANEL_KING RAW_PATCH=$RAW_PATCH \
        SEPT_KING_FEA=$CONTROLS_REF_KING_FEA SEPT_KING_META=$CONTROLS_REF_KING_META SEPT_DL_TARGETS=$CONTROLS_REF_DL_TARGETS \
        BUILDER_TARGETS=$BT BUILDER_KING_FEA=$BK "$PY" -B "$D/fp2_controls.py" > "$R/fp2_controls.log" 2>&1 < /dev/null; rc=$?
    v=$( [ -f "$REC" ] && "$PY" -c "import json,sys; print(json.load(open(sys.argv[1])).get('VERDICT'))" "$REC" ); stage "controls rc=$rc VERDICT=$v"
    [ "$v" = PASS ] || die "controls_verdict_${v:-none}" 3
  fi
fi

if want gates; then
  prereq_receipt gates preflight "$R/v4_gates/preflight.json" PREFLIGHT
  for T in RAW CLIP; do prereq_file gates f10_gate_$T "$F8/gates/F10_GATE_$T.json"; done   # the data stage finished in THIS root (identity receipts written last)
  prereq_json_eq gates f10_gate_raw_targets "$F8/gates/F10_GATE_RAW.json" targets_sha256 "$(gate_sha "$DLW_RAW/data/dlw_targets.npz")"
  prereq_json_eq gates f10_gate_clip_targets "$F8/gates/F10_GATE_CLIP.json" targets_sha256 "$(gate_sha "$DLW_CLIP/data/dlw_targets.npz")"
  prereq_json_eq gates f10_gate_fea89 "$F8/gates/F10_GATE_RAW.json" fea89_sha256 "$(gate_sha "$F8/data/f8_fea89.npz")"
  # ★ R12-C1 (round 12): the FP2 data gates call fp2_gate_lib.bind_controls, which refuses a root without $R/controls/CONTROLS.json — the
  #   controls stage used to run AFTER gates, so a fresh full run could never reach it. controls is a stage prerequisite of gates now.
  case "${GATE_STEP1}${GATE_STEP2}" in *fp2_gate_step*) prereq_file gates controls "$R/controls/CONTROLS.json"; prereq_json_eq gates controls_verdict "$R/controls/CONTROLS.json" VERDICT PASS ;; esac
  guard gates; stage "gates: run $GATE_STEP1 and $GATE_STEP2, then require both"
  run_gate STEP1 "$GATE_STEP1" "$R/gate_step1.log" STEP1_OUT="$R/v4_gates/step1.json"; rc1=$?
  run_gate STEP2 "$GATE_STEP2" "$R/gate_step2.log" STEP2_OUT="$R/v4_gates/step2.json"; rc2=$?
  stage "gates ran: STEP1 rc=$rc1 STEP2 rc=$rc2 (receipts $R/v4_gates/step{1,2}.json)"
  S1_SRC=$(gate_sha "$D/$GATE_STEP1") || die "gate_source_unreadable_$GATE_STEP1" 3
  S2_SRC=$(gate_sha "$D/$GATE_STEP2") || die "gate_source_unreadable_$GATE_STEP2" 3
  require_gate "$R/v4_gates/step1.json" recorded_extras=1 gate=STEP1 profile=v4 self_sha=$S1_SRC dlw_v4raw_targets=$DLW_RAW/data/dlw_targets.npz dlw_hf3_targets=$DLW_CLIP/data/dlw_targets.npz fea82_v4raw=$DLW_RAW/data/dlw_fea82.npz fea89_f8v4=$F8/data/f8_fea89.npz
  require_gate "$R/v4_gates/step2.json" recorded_extras=1 gate=STEP2 self_sha=$S2_SRC wide_fea_v4=$KING_FEA wide_fea_v4_meta=$KING_META
  [ $rc1 -eq 0 ] && [ $rc2 -eq 0 ] || die "gates_rc_${rc1}_${rc2}" 3
  # ★ FP3 F: MEMBER_LIVENESS on the PRODUCED member sets (king meta + DL targets), re-derived from CACHE + HOLE_CELLS — it does not trust MEMBER_MASK
  run_gate LIVENESS "$GL" "$R/gate_liveness.log" CACHE=$CACHE HOLE_CELLS=$HOLE_CELLS KING_META=$KING_META DLW_TARGETS=$DLW_RAW/data/dlw_targets.npz MEMBER_MASK=${MEMBER_MASK:-} OUT=$R/v4_gates/member_liveness.json; rc3=$?
  GL_SRC=$(gate_sha "$D/$GL") || die "gate_source_unreadable_$GL" 3
  require_gate "$R/v4_gates/member_liveness.json" recorded_extras=1 gate=MEMBER_LIVENESS self_sha=$GL_SRC cache=$CACHE hole_cells=$HOLE_CELLS wide_fea_v4_meta=$KING_META dlw_v4raw_targets=$DLW_RAW/data/dlw_targets.npz
  [ $rc3 -eq 0 ] || die "gates_liveness_rc_$rc3" 3
  stage "gates PASS + required (STEP1 self $S1_SRC, STEP2 self $S2_SRC, MEMBER_LIVENESS self $GL_SRC)"
fi

# ── king export (BEFORE legs: legs need THIS month's PRED) ────────────────────────────────────────────────────────────────────────────────
if want king; then
  prereq_receipt king preflight "$R/v4_gates/preflight.json" PREFLIGHT
  prereq_receipt king step2 "$R/v4_gates/step2.json" STEP2
  prereq_receipt king liveness "$R/v4_gates/member_liveness.json" MEMBER_LIVENESS "${LIVE_BIND[@]}"
  guard king; stage "king: export bundle generation=$BUNDLE_GENERATION -> $BUNDLE_OUT (requires the STEP2 receipt bound to $KING_FEA/$KING_META)"
  S2_SRC=$(gate_sha "$D/$GATE_STEP2") || die "gate_source_unreadable_$GATE_STEP2" 3
  require_gate "$R/v4_gates/step2.json" recorded_extras=1 gate=STEP2 self_sha=$S2_SRC wide_fea_v4=$KING_FEA wide_fea_v4_meta=$KING_META
  env BUNDLE_OUT=$BUNDLE_OUT BUNDLE_BASE=$BUNDLE_BASE BUNDLE_FEA=$KING_FEA BUNDLE_META=$KING_META BUNDLE_CACHE=$CACHE BUNDLE_TAR=$BUNDLE_TAR EXPORT_PANEL=$EXPORT_PANEL EMA_STATE_JSON=$EMA_STATE_JSON \
      LIVE_PINS=$LIVE_PINS FUND_AUG=$FUND_AUG FUNDING_DIR=$FUNDING_DIR BUNDLE_GENERATION=$BUNDLE_GENERATION V4_MONTH_ENV=$V4_MONTH_ENV "$PY" "$D/pod_export_bundle_v4.py" > "$R/export_v4.log" 2>&1; rc=$?
  stage "king export rc=$rc $(tail -1 "$R/export_v4.log" | cut -c1-120)"; [ $rc -eq 0 ] || die "king_export_rc_$rc" 1
  check_marker "$R/export_v4.log" "BUNDLE_DONE"; check_no_marker "$R/export_v4.log" "BUNDLE_FAIL"
  [ -f "$BUNDLE_OUT/slow_pred_pinned.npy" ] && [ -f "$BUNDLE_OUT/config.json" ] && [ -f "$BUNDLE_OUT/MANIFEST.json" ] || die "king_export_outputs_missing" 1
  "$PY" -c "import json,sys;p=json.load(open(sys.argv[1]))['provenance'];assert p['generation']==sys.argv[2],(p['generation'],sys.argv[2]);print('provenance generation',p['generation'],'king_train_end_utc',p['king_train_end_utc'],'built_utc',p['built_utc'])" "$BUNDLE_OUT/config.json" "$BUNDLE_GENERATION" >> "$STAGE_LOG" 2>&1 || die "king_export_generation_mismatch" 1
fi

# ── legs (in-service rows verbatim + new anchors from THIS month's king PRED) ──────────────────────────────────────────────────────────────
if want legs; then
  prereq_receipt legs preflight "$R/v4_gates/preflight.json" PREFLIGHT
  prereq_receipt legs step1 "$R/v4_gates/step1.json" STEP1; S1_SRC=$(gate_sha "$D/$GATE_STEP1") || die "gate_source_unreadable_$GATE_STEP1" 3
  prereq_receipt legs liveness "$R/v4_gates/member_liveness.json" MEMBER_LIVENESS "${LIVE_BIND[@]}"
  require_gate "$R/v4_gates/step1.json" recorded_extras=1 gate=STEP1 profile=v4 self_sha=$S1_SRC dlw_v4raw_targets=$DLW_RAW/data/dlw_targets.npz dlw_hf3_targets=$DLW_CLIP/data/dlw_targets.npz fea82_v4raw=$DLW_RAW/data/dlw_fea82.npz fea89_f8v4=$F8/data/f8_fea89.npz   # legs read THIS month's RAW targets: bound through STEP1
  guard legs; stage "legs: pod_legs_v4b.py LEGS_PRED=$BUNDLE_OUT/slow_pred_pinned.npy LEGS_OLD=$LEGS_OLD"
  [ -f "$BUNDLE_OUT/slow_pred_pinned.npy" ] || die "legs_king_pred_missing" 3
  check_marker "$R/export_v4.log" "BUNDLE_DONE"; check_no_marker "$R/export_v4.log" "BUNDLE_FAIL"   # legs consume THIS month's export: its marker must be present in this root
  # TRN-17: LEGS_MAX_NO_PANEL = 5 is the STRUCTURAL frontier shortfall, not a tolerance: the panels require E+288 <= TT while the
  # king/DL axis requires E+48 <= TT, so the panel is always 288-48 = 240 five-minute rows = 20 h = 5 four-hour anchors short at the
  # frontier (September measured exactly 5). More than 5, or any no-panel anchor at or before the panel end, refuses with nothing written.
  env LEGS_TG=$DLW_RAW/data/dlw_targets.npz LEGS_META=$KING_META LEGS_PRED=$BUNDLE_OUT/slow_pred_pinned.npy LEGS_OUT=$F8/data/f10v2_legs.npz LEGS_OLD=$LEGS_OLD LEGS_PANEL=$LEGS_PANEL LEGS_MAX_NO_PANEL=5 "$PY" "$D/pod_legs_v4b.py" > "$R/legs_v4.log" 2>&1; rc=$?
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
  prereq_receipt mwf preflight "$R/v4_gates/preflight.json" PREFLIGHT
  prereq_receipt mwf step1 "$R/v4_gates/step1.json" STEP1; prereq_marker mwf legs "$R/legs_v4.log" LEGS_V4B_DONE
  prereq_receipt mwf liveness "$R/v4_gates/member_liveness.json" MEMBER_LIVENESS "${LIVE_BIND[@]}"
  guard mwf; stage "mwf: MONTHS_ALL=$MONTHS_ALL seeds=[$SEED_LIST] root=$F8/$MWF_ROOT"
  "$PY" "$D/v4_months.py" check "$DLW_RAW/data/dlw_targets.npz" "$MONTHS_ALL" >> "$STAGE_LOG" 2>&1 || die "months_all_not_admissible_for_axis" 3
  set_shards_from_months_all; export MWF_ROOT
  S1_SRC=$(gate_sha "$D/$GATE_STEP1") || die "gate_source_unreadable_$GATE_STEP1" 3
  require_gate "$R/v4_gates/step1.json" recorded_extras=1 gate=STEP1 profile=v4 self_sha=$S1_SRC dlw_v4raw_targets=$DLW_RAW/data/dlw_targets.npz dlw_hf3_targets=$DLW_CLIP/data/dlw_targets.npz fea82_v4raw=$DLW_RAW/data/dlw_fea82.npz fea89_f8v4=$F8/data/f8_fea89.npz
  check_marker "$R/legs_v4.log" "LEGS_V4B_DONE"; [ -f "$F8/data/f10v2_legs.npz" ] || die "legs_missing" 3
  pin_deps v4_monthly_mwf "$D/pod_f10_train_monthly_v4.py" "$D/launch_mwf_v4b.sh" "$D/merge_mwf_v4b.py" "$D/chain_lib.sh" "$D/v4_months.py" "$BASE_TRAINER" "$F8/data/f10v2_legs.npz" "$F8/data/f8_fea89.npz" "$DLW_RAW/data/dlw_targets.npz" "$DLW_CLIP/data/dlw_targets.npz" "$DLW_RAW/data/dlw_fea82.npz" "$F8/gates/F10_GATE_RAW.json" "$ENVF"
  for SD in $SEED_LIST; do
    stage "F10 chain RAW s$SD start (monthly, legs v4b, FIX7, shards from MONTHS_ALL)"
    run_shards launch_mwf_v4b.sh RAW "$SD" || die "shards_RAW_s${SD}_rc_[$RCS]" 1
    run_device_stripped "$D/merge_mwf_v4b.py" "$F8/logs/merge_v4b_RAW_s${SD}.log" RAW "$SD"; rc=$?; stage "merge RAW s$SD rc=$rc $(tail -1 "$F8/logs/merge_v4b_RAW_s${SD}.log" | cut -c1-80)"   # ★ R15-C1: same ambient strip as run_gate — an ungoverned V4_HF2_PREDS from the launching shell cannot reach the merge; V4_TRAINER etc. arrive governed or the device refuses
    [ $rc -eq 0 ] || die "merge_RAW_s${SD}_rc_$rc" 1; check_marker "$F8/logs/merge_v4b_RAW_s${SD}.log" "MERGE_DONE"
  done
  stage "CHAIN_V4_MONTHLY_MWF_DONE (shards rc=0, merges rc=0 + MERGE_DONE; deps in v4_gates/deps_v4_monthly_mwf.json)"
fi

# ── refit (deployment weights), explicit env, FIX7 ──────────────────────────────────────────────────────────────────────────────────────────
if want refit; then
  prereq_receipt refit preflight "$R/v4_gates/preflight.json" PREFLIGHT
  prereq_receipt refit step1 "$R/v4_gates/step1.json" STEP1; S1_SRC=$(gate_sha "$D/$GATE_STEP1") || die "gate_source_unreadable_$GATE_STEP1" 3
  prereq_receipt refit liveness "$R/v4_gates/member_liveness.json" MEMBER_LIVENESS "${LIVE_BIND[@]}"
  require_gate "$R/v4_gates/step1.json" recorded_extras=1 gate=STEP1 profile=v4 self_sha=$S1_SRC dlw_v4raw_targets=$DLW_RAW/data/dlw_targets.npz dlw_hf3_targets=$DLW_CLIP/data/dlw_targets.npz fea82_v4raw=$DLW_RAW/data/dlw_fea82.npz fea89_f8v4=$F8/data/f8_fea89.npz
  prereq_marker refit legs "$R/legs_v4.log" LEGS_V4B_DONE; prereq_file refit legs_file "$F8/data/f10v2_legs.npz"
  for SD in $SEED_LIST; do prereq_marker refit merge_s$SD "$F8/logs/merge_v4b_RAW_s$SD.log" MERGE_DONE; done
  prereq_deps_identity refit mwf_inputs "$R/v4_gates/deps_v4_monthly_mwf.json" "$F8/data/f10v2_legs.npz" "$F8/data/f8_fea89.npz" "$DLW_RAW/data/dlw_targets.npz" "$DLW_CLIP/data/dlw_targets.npz" "$DLW_RAW/data/dlw_fea82.npz" "$D/pod_f10_train_monthly_v4.py"   # the mwf dispatch pinned these; refit consumes the same files
  guard refit
  for SD in $SEED_LIST; do
    stage "refit s$SD: env F10_DLW=$DLW_RAW F10_OUT=$F8 SEED=$SD BEST_EP_FIX=7 EMBARGO=1"
    env F10_DLW=$DLW_RAW F10_OUT=$F8 SEED=$SD BEST_EP_FIX=7 EMBARGO=1 V4_MONTH=$V4_MONTH V4_MONTH_ENV=$V4_MONTH_ENV "$PY" "$D/pod_f10_refit_v4.py" > "$R/refit_s$SD.log" 2>&1; rc=$?
    stage "refit s$SD rc=$rc $(tail -1 "$R/refit_s$SD.log" | cut -c1-140)"; [ $rc -eq 0 ] || die "refit_s${SD}_rc_$rc" 1
    check_marker "$R/refit_s$SD.log" "REFIT_DONE"; [ -f "$F8/models/f10_live_s$SD.pt" ] && [ -f "$F8/models/f10_live_s$SD.json" ] || die "refit_s${SD}_outputs_missing" 1
    "$PY" -c "import json,sys;m=json.load(open(sys.argv[1]));assert m['best_ep_rule']=='fix7' and m['env_given']['BEST_EP_FIX']=='7' and m['env_given']['F10_DLW']==sys.argv[2],(m['best_ep_rule'],m['env_given']);print('refit s'+str(m['seed']),'rule',m['best_ep_rule'],'label cutoff',m['trained_through_label_utc'],'pool end',m['trained_through_pool_end_utc'],'pt',m['pt_sha256'][:12])" "$F8/models/f10_live_s$SD.json" "$DLW_RAW" >> "$STAGE_LOG" 2>&1 || die "refit_s${SD}_rule_not_fix7" 3
  done
fi

# ── np_export (the file the live DL leg loads), FX-TRAIN TRN-03/TRN-14 2026-09-16 ───────────────────────────────────────────────────────────
# Before this stage existed the deployable npz was made by a manual call to T/pod_f10_np_export.py, whose defaults pointed at the IN-SERVICE
# generation and which wrote the artifact BEFORE its own V1 gate decided (FACT_TABLE_TRN 03.1-03.3). Every locator below is explicit, the
# sidecar binding is chain_lib's prereq_refit_sidecar (the same contract the arms stage uses — not a second implementation), and the program
# refuses to write on a V1 FAIL. F10_BEST_EP_RULE must stay the literal that matches BEST_EP_FIX in the refit stage above (asserted by [X]).
if want np_export; then
  prereq_receipt np_export preflight "$R/v4_gates/preflight.json" PREFLIGHT
  for SD in $SEED_LIST; do
    prereq_marker np_export refit_s$SD "$R/refit_s$SD.log" REFIT_DONE
    prereq_file np_export pt_s$SD "$F8/models/f10_live_s$SD.pt"
    prereq_refit_sidecar np_export refit_s$SD "$F8/models/f10_live_s$SD.json" "$DLW_RAW" "$F8" "$SD" "$D/pod_f10_refit_v4.py"
  done
  guard np_export
  for SD in $SEED_LIST; do
    NPO=$F8/models/f10_live_s${SD}_np.npz; NPR=$R/v4_gates/NP_EXPORT_s$SD.json
    stage "np_export s$SD: F10_OUT=$F8 F10_DLW=$DLW_RAW -> $NPO (generation $BUNDLE_GENERATION, rule fix7)"
    env F10_OUT=$F8 F10_DLW=$DLW_RAW SEED=$SD F10_SIDECAR=$F8/models/f10_live_s$SD.json F10_NP_OUT=$NPO \
        F10_NP_RECEIPT=$NPR F10_GENERATION=$BUNDLE_GENERATION F10_BEST_EP_RULE=fix7 \
        "$PY" "$D/pod_f10_np_export_v4.py" > "$R/np_export_s$SD.log" 2>&1; rc=$?
    stage "np_export s$SD rc=$rc $(tail -1 "$R/np_export_s$SD.log" | cut -c1-140)"; [ $rc -eq 0 ] || die "np_export_s${SD}_rc_$rc" 3
    check_marker "$R/np_export_s$SD.log" "NP_EXPORT_DONE"; [ -f "$NPO" ] || die "np_export_s${SD}_npz_missing" 1
    NP_SRC=$(gate_sha "$D/pod_f10_np_export_v4.py") || die "np_export_source_unreadable" 3
    require_gate "$NPR" gate=F10_NP_EXPORT self_sha=$NP_SRC pt=$F8/models/f10_live_s$SD.pt refit_sidecar=$F8/models/f10_live_s$SD.json npz=$NPO
  done
fi

# ── book layer: dev tree + arms ─────────────────────────────────────────────────────────────────────────────────────────────────────────────
if want arms; then
  prereq_receipt arms preflight "$R/v4_gates/preflight.json" PREFLIGHT
  prereq_receipt arms step2 "$R/v4_gates/step2.json" STEP2; S2_SRC=$(gate_sha "$D/$GATE_STEP2") || die "gate_source_unreadable_$GATE_STEP2" 3
  prereq_receipt arms liveness "$R/v4_gates/member_liveness.json" MEMBER_LIVENESS "${LIVE_BIND[@]}"
  require_gate "$R/v4_gates/step2.json" recorded_extras=1 gate=STEP2 self_sha=$S2_SRC wide_fea_v4=$KING_FEA wide_fea_v4_meta=$KING_META   # build_dev reads KING_META
  prereq_marker arms bundle "$R/export_v4.log" BUNDLE_DONE BUNDLE_FAIL; prereq_file arms king_pred "$BUNDLE_OUT/slow_pred_pinned.npy"
  for SD in $SEED_LIST; do prereq_refit_sidecar arms refit_s$SD "$F8/models/f10_live_s$SD.json" "$DLW_RAW" "$F8" "$SD" "$D/pod_f10_refit_v4.py"; done   # round 3: expected SEED + complete key set + this month's expected paths + the ACTUAL sha of the .pt and all four inputs + which program wrote the sidecar
  guard arms; stage "arms: build_dev_v4 (raw meta, SLOW_v4 from $BUNDLE_OUT, A0 preds) then run_v4_arms.sh $EXPORT_ARM seeds [$SEED_LIST]"
  mkdir -p "$HC/dev_v4/logs" "$KING_DIR" || die "arms_mkdir" 1
  env KING_META=$KING_META DLW_RAW=$DLW_RAW CACHE=$CACHE HOLE_CELLS=$HOLE_CELLS BUNDLE_OUT=$BUNDLE_OUT DEV_MEMBER_MASK_NPZ=${MEMBER_MASK:-} "$PY" "$D/build_dev_v4.py" > "$R/build_dev_v4.log" 2>&1; rc=$?   # FP2-8: the declared member mask reaches the dev-tree self-check
  stage "build_dev_v4 rc=$rc $(tail -1 "$R/build_dev_v4.log" | cut -c1-100)"; [ $rc -eq 0 ] || die "build_dev_v4_rc_$rc" 1; check_marker "$R/build_dev_v4.log" "DEV_V4_DONE"
  [ -f "$D/run_arm.sh" ] || die "arms_device_run_arm_missing_$D/run_arm.sh" 1   # FP3 J: the wrapper executes the device copy; the tree copy (if any) is dead
  N0=$(grep -a -c "^END\[V4_${EXPORT_ARM}_.*rc=0" "$HC/logs/commands.txt" 2>/dev/null || echo 0)
  # ★ R12-C3: the candidate arms get the SAME contract-bound, preflight-verified mask the baseline rerun gets — explicitly on the command line
  [ -n "${UMASK_NPZ:-}" ] || die "arms_prereq_umask_npz_missing" 3
  V4_PY="$PY" V4_UMASK_NPZ="$UMASK_NPZ" bash "$D/run_v4_arms.sh" "$EXPORT_ARM" "$SEED_LIST" > "$R/arms_${EXPORT_ARM}.log" 2>&1; rc=$?   # FP3 J: the interpreter reaches the device runner by name (inline, not via the loader export set)
  N1=$(grep -a -c "^END\[V4_${EXPORT_ARM}_.*rc=0" "$HC/logs/commands.txt" 2>/dev/null || echo 0); NEED=$(( 2 * $(echo $SEED_LIST | wc -w) ))
  stage "arms $EXPORT_ARM rc=$rc fresh END rc=0 lines $((N1 - N0))/$NEED"; [ $rc -eq 0 ] || die "arms_${EXPORT_ARM}_rc_$rc" 1
  check_marker "$R/arms_${EXPORT_ARM}.log" "ARMS_DONE"; [ $((N1 - N0)) -ge $NEED ] || die "arms_${EXPORT_ARM}_fresh_END_lines_$((N1 - N0))_lt_$NEED" 1
fi

if want a0rerun; then
  prereq_receipt a0rerun preflight "$R/v4_gates/preflight.json" PREFLIGHT
  prereq_marker a0rerun arms "$R/arms_${EXPORT_ARM}.log" ARMS_DONE ARMS_FAIL
  [ -f "$HC/dev_v4/BUILD.json" ] || die "a0rerun_prereq_build_dev_v4 (the arms stage re-links the dev tree to this root first)" 3
  [ -n "${UMASK_NPZ:-}" ] || die "a0rerun_prereq_umask_npz_missing (month contract must set UMASK_NPZ; preflight binds it to the contract sha)" 3
  UM=$UMASK_NPZ; REC=$R/v4_gates/A0_RERUN_TRADABLE.json; ARTS="$HC/dev_v4/probe_artifacts"
  guard a0rerun; stage "a0rerun: run_v4_arms.sh A0 seeds=[$SEED_LIST] V4_HC=$HC V4_KING_DIR=$KING_DIR V4_UMASK_NPZ=$UM"
  BEFORE=$("$PY" - "$ARTS" <<'PY'
import hashlib, json, os, sys
a = sys.argv[1]; fs = sorted(f for f in os.listdir(a) if f.startswith("w10_ablation_series_V4_A0_") and f.endswith(".npz"))
print(json.dumps({f: hashlib.sha256(open(os.path.join(a, f), "rb").read()).hexdigest() for f in fs}))
PY
)
  T_START=$(date +%s)
  ( cd "$HC" && V4_HC=$HC V4_KING_DIR=$KING_DIR V4_PY="$PY" V4_UMASK_NPZ=$UM bash "$D/run_v4_arms.sh" A0 "$SEED_LIST" ) > "$R/arms_A0_tradable.log" 2>&1 < /dev/null; rc=$?
  grep -aq "ARMS_DONE" "$R/arms_A0_tradable.log" || rc=$((rc == 0 ? 1 : rc))
  AFTER=$("$PY" - "$ARTS" <<'PY'
import hashlib, json, os, sys
a = sys.argv[1]; fs = sorted(f for f in os.listdir(a) if f.startswith("w10_ablation_series_V4_A0_") and f.endswith(".npz"))
print(json.dumps({f: hashlib.sha256(open(os.path.join(a, f), "rb").read()).hexdigest() for f in fs}))
PY
)
  ARTS=$ARTS "$PY" - "$REC" "$BEFORE" "$AFTER" "$UM" "$rc" "$R/arms_A0_tradable.log" "$T_START" <<'PY'
import hashlib, json, sys, time, os
import numpy as np
out, before, after, um, rc, log = sys.argv[1:7]; b = json.loads(before); a = json.loads(after)
t_start = float(sys.argv[7]) if len(sys.argv) > 7 else 0.0
arts_dir = os.environ["ARTS"]; um_sha = hashlib.sha256(open(um, "rb").read()).hexdigest(); per = {}
for f in sorted(a):
    p = os.path.join(arts_dir, f); z = np.load(p, allow_pickle=True); cfg = json.loads(str(z["config_json"])) if "config_json" in z.files else {}
    per[f] = {"written_by_this_run": os.path.getmtime(p) >= t_start, "cfg_umask": cfg.get("UMASK_NPZ"), "cfg_umask_is_this_umask": os.path.realpath(str(cfg.get("UMASK_NPZ") or "")) == os.path.realpath(um),
              "sha_before": b.get(f), "sha_after": a.get(f), "changed": b.get(f) != a.get(f)}
ok = rc == "0" and len(a) >= 4 and all(v["written_by_this_run"] and v["cfg_umask_is_this_umask"] for v in per.values())
rec = {"gate": "A0_RERUN_TRADABLE", "PASS": bool(ok), "rc": int(rc), "umask": um, "umask_sha256": um_sha, "run_start_utc": time.strftime("%FT%TZ", time.gmtime(t_start)), "artifacts": per, "log": log,
       "meaning": "A0 (in-service form) re-run under the SAME evaluation umask as the candidate (DESIGN_FP2-8 §2.2): rc 0 + ARMS_DONE, every artifact written by this run and carrying this umask in its cfg; an identical re-run is a PASS (idempotent), the before/after shas are information"}
json.dump(rec, open(out, "w"), indent=1); print("A0_RERUN", "PASS" if rec["PASS"] else "FAIL", {k[:40]: (v["written_by_this_run"], v["cfg_umask_is_this_umask"], v["changed"]) for k, v in per.items()})
PY
  stage "a0rerun rc=$rc receipt $REC"; [ $rc -eq 0 ] && "$PY" -c "import json,sys; sys.exit(0 if json.load(open(sys.argv[1]))['PASS'] else 1)" "$REC" || die "a0rerun" 1
fi

# ── judge ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
if want judge; then
  prereq_receipt judge preflight "$R/v4_gates/preflight.json" PREFLIGHT
  prereq_marker judge build_dev "$R/build_dev_v4.log" DEV_V4_DONE; prereq_marker judge arms "$R/arms_${EXPORT_ARM}.log" ARMS_DONE ARMS_FAIL
  prereq_count judge arms_end_rows "$HC/logs/commands.txt" "^END\[V4_${EXPORT_ARM}_.*rc=0" $(( 2 * $(echo $SEED_LIST | wc -w) ))
  # ★ R12-C1: the judge and the export gate compare against the A0 baseline books, so the baseline rerun must already have happened —
  #   it used to run AFTER export, which left the export receipt's book identity stale as soon as A0's bytes changed.
  prereq_receipt judge a0rerun "$R/v4_gates/A0_RERUN_TRADABLE.json" A0_RERUN_TRADABLE
  guard judge; stage "judge: JUDGE_HC=$HC -> $R/v4_gates/JUDGE_v4.json"
  JUDGE_HC=$HC JUDGE_OUT=$R/v4_gates/JUDGE_v4.json "$PY" "$D/judge_v4.py" > "$R/judge_v4.log" 2>&1; rc=$?
  stage "judge rc=$rc $(grep -a "JUDGE_V4_DONE\|JUDGE_REFUSED" "$R/judge_v4.log" | tail -1 | cut -c1-140)"; [ $rc -eq 0 ] || die "judge_rc_$rc" 1
  check_marker "$R/judge_v4.log" "JUDGE_V4_DONE"
fi

# ── export gate v2: gate, require, then judge WITH the eligibility locator ──────────────────────────────────────────────────────────────────
if want export; then
  prereq_receipt export preflight "$R/v4_gates/preflight.json" PREFLIGHT
  prereq_marker export judge "$R/judge_v4.log" JUDGE_V4_DONE; prereq_file export judge_json "$R/v4_gates/JUDGE_v4.json"
  prereq_marker export arms "$R/arms_${EXPORT_ARM}.log" ARMS_DONE ARMS_FAIL; prereq_marker export bundle "$R/export_v4.log" BUNDLE_DONE BUNDLE_FAIL
  prereq_receipt export a0rerun "$R/v4_gates/A0_RERUN_TRADABLE.json" A0_RERUN_TRADABLE   # ★ R12-C1: the approved baseline books must be final BEFORE the export identity is taken
  GE=${GATE_EXPORT:-v4e_gate_export_v2.py}; case "$GE" in */*|.*) die "export_gate_not_a_basename_$GE" 3;; esac; [ -f "$D/$GE" ] || die "export_gate_missing_$GE" 3   # PROPOSED5: the month contract may select an approved variant, by BASENAME only (round 5 P2)
  guard export; stage "export: $GE gate + require on arm $EXPORT_ARM (V4CHAIN_DIR=$D)"
  # ★ FP3 F: third end of MEMBER_LIVENESS — every name in the shipped bundle's symbols_live must have a real bar in the cache's last 24 h
  run_gate LIVENESS_EXPORT "$GL" "$R/gate_liveness_export.log" CACHE=$CACHE HOLE_CELLS=$HOLE_CELLS KING_META=$KING_META DLW_TARGETS=$DLW_RAW/data/dlw_targets.npz MEMBER_MASK=${MEMBER_MASK:-} BUNDLE_CONFIG=$BUNDLE_OUT/config.json OUT=$R/v4_gates/member_liveness_export.json; rcl=$?
  GL_SRC=$(gate_sha "$D/$GL") || die "gate_source_unreadable_$GL" 3
  require_gate "$R/v4_gates/member_liveness_export.json" recorded_extras=1 gate=MEMBER_LIVENESS self_sha=$GL_SRC cache=$CACHE hole_cells=$HOLE_CELLS wide_fea_v4_meta=$KING_META dlw_v4raw_targets=$DLW_RAW/data/dlw_targets.npz bundle_config=$BUNDLE_OUT/config.json
  [ -f "$BUNDLE_OUT/MANIFEST.json" ] || stage "export liveness: bundle has no MANIFEST.json (nothing to bind for R14-C2)"
  [ $rcl -eq 0 ] || die "export_liveness_rc_$rcl" 3
  GX="V4_MONTH=$V4_MONTH EXPORT_ARM=$EXPORT_ARM BUNDLE_OUT=$BUNDLE_OUT BUNDLE_FEA=$KING_FEA BUNDLE_META=$KING_META BUNDLE_BASE=$BUNDLE_BASE EXPORT_PANEL=$EXPORT_PANEL BUNDLE_CACHE=$CACHE FUND_AUG=$FUND_AUG LIVE_PINS=$LIVE_PINS JUDGE_HC=$HC V4CHAIN_DIR=$D SIGNAL_RECEIPT=$SIGNAL_RECEIPT"
  REC=$R/v4_gates/BUNDLE_export_v2_${EXPORT_ARM}.json
  env $GX EXPORT_GATE_OUT=$REC "$PY" "$D/$GE" > "$R/export_gate_v2.log" 2>&1; rc=$?
  stage "export gate rc=$rc $(tail -1 "$R/export_gate_v2.log" | cut -c1-140)"; [ $rc -eq 0 ] || die "export_gate_v2_rc_$rc" 3
  env $GX EXPORT_GATE_OUT=/dev/null REQUIRE_OUT=$R/v4_gates/REQUIRE_v2_${EXPORT_ARM}.json "$PY" "$D/$GE" require "$REC" > "$R/export_require_v2.log" 2>&1; rc=$?
  stage "export require rc=$rc $(tail -1 "$R/export_require_v2.log" | cut -c1-140)"; [ $rc -eq 0 ] || die "export_require_v2_rc_$rc" 3
  check_marker "$R/export_require_v2.log" "REQUIRE_OK"
  "$PY" -c "import json,sys;r=json.load(open(sys.argv[1]));json.dump({sys.argv[2]:{'receipt':sys.argv[1],'inputs':r['inputs_path']}},open(sys.argv[3],'w'),indent=1);print('eligibility locator',sys.argv[3],len(r['inputs_path']),'inputs')" "$REC" "$EXPORT_ARM" "$R/v4_gates/JUDGE_ELIGIBILITY.json" >> "$STAGE_LOG" 2>&1 || die "eligibility_locator_write" 3
  JUDGE_HC=$HC JUDGE_OUT=$R/v4_gates/JUDGE_v4_eligible.json JUDGE_ELIGIBILITY=$R/v4_gates/JUDGE_ELIGIBILITY.json "$PY" "$D/judge_v4.py" > "$R/judge_v4_eligible.log" 2>&1; rc=$?
  stage "judge (with eligibility) rc=$rc $(grep -a "JUDGE_V4_DONE\|JUDGE_REFUSED" "$R/judge_v4_eligible.log" | tail -1 | cut -c1-140)"; [ $rc -eq 0 ] || die "judge_eligible_rc_$rc" 1
  check_marker "$R/judge_v4_eligible.log" "JUDGE_V4_DONE"
fi




if want member_rule; then   # R09: the masked builds must be EXACTLY the builders' rule (recomputed from the cache); receipt bound by the decision stage
  prereq_receipt member_rule preflight "$R/v4_gates/preflight.json" PREFLIGHT
  prereq_receipt member_rule liveness "$R/v4_gates/member_liveness.json" MEMBER_LIVENESS "${LIVE_BIND[@]}"
  [ -n "${MEMBER_MASK:-}" ] || die "member_rule_prereq_member_mask_missing (the rule check needs the declared mask)" 3
  for f in "$R/controls/king_nomask/wide_fea_v4_meta.npz" "$R/controls/dl_nomask/data/dlw_targets.npz"; do [ -f "$f" ] || die "member_rule_prereq_controls_missing_$(basename "$f")" 3; done
  guard member_rule; stage "member_rule: fp2_member_rule_check.py"
  env CACHE=$CACHE RAW_PATCH=$RAW_PATCH MEMBER_MASK=$MEMBER_MASK CONTROL_KING_META=$R/controls/king_nomask/wide_fea_v4_meta.npz MASKED_KING_META=$KING_META \
      CONTROL_DL_TARGETS=$R/controls/dl_nomask/data/dlw_targets.npz MASKED_DL_TARGETS=$DLW_RAW/data/dlw_targets.npz OUT_JSON=$R/v4_gates/MEMBER_RULE_CHECK.json \
      nice -n 10 "$PY" -u "$D/fp2_member_rule_check.py" > "$R/member_rule_check.log" 2>&1 < /dev/null; rc=$?
  stage "member_rule rc=$rc $(tail -1 "$R/member_rule_check.log" | cut -c1-160)"; [ $rc -eq 0 ] || die "stage_member_rule_rc_$rc" $rc
fi

if want per_year; then   # F03/F09/F10: the per-year table (both arms under the same umask, per-anchor maxDD, W_ALPHA pinned to a time)
  prereq_receipt per_year preflight "$R/v4_gates/preflight.json" PREFLIGHT
  prereq_receipt per_year a0rerun "$R/v4_gates/A0_RERUN_TRADABLE.json" A0_RERUN_TRADABLE
  prereq_marker per_year arms "$R/arms_${EXPORT_ARM}.log" ARMS_DONE ARMS_FAIL
  [ -n "${UMASK_NPZ:-}" ] || die "per_year_prereq_umask_npz_missing" 3
  guard per_year; stage "per_year: fp2_per_year_table.py arms A0,$EXPORT_ARM seats dyn seeds $SEEDS"
  env ARMS_DIR=$HC/dev_v4/probe_artifacts UMASK_NPZ=$UMASK_NPZ ARMS=A0,$EXPORT_ARM SEATS=dyn SEEDS=$SEEDS OUT_JSON=$R/v4_gates/PER_YEAR_TABLE.json OUT_MD=$R/v4_gates/PER_YEAR_TABLE.md \
    "$PY" "$D/fp2_per_year_table.py" > "$R/per_year_table.log" 2>&1 < /dev/null; rc=$?
  stage "per_year rc=$rc $(tail -1 "$R/per_year_table.log" | cut -c1-160)"; [ $rc -eq 0 ] || die "stage_per_year_rc_$rc" $rc
fi

if want decision; then   # F03: the swap recommendation under AMENDMENT 7 (G1′ non-inferiority × G2 per-year × G3 export gate); judge receipt informational only
  prereq_receipt decision preflight "$R/v4_gates/preflight.json" PREFLIGHT
  prereq_receipt decision step1 "$R/v4_gates/step1.json" STEP1 v4
  prereq_receipt decision liveness "$R/v4_gates/member_liveness.json" MEMBER_LIVENESS "${LIVE_BIND[@]}"
  # ★ R14-C2: the MANIFEST takes part in the export end's anchor selection, so when it exists it is a RECORDED dependency of that receipt and
  #   must be bound here too — `recorded_extras` can only re-hash what the gate wrote down.
  LIVE_BIND_X=("${LIVE_BIND[@]}" "bundle_config=$BUNDLE_OUT/config.json")
  [ -f "$BUNDLE_OUT/MANIFEST.json" ] && LIVE_BIND_X+=("bundle_manifest=$BUNDLE_OUT/MANIFEST.json")
  prereq_receipt decision liveness_export "$R/v4_gates/member_liveness_export.json" MEMBER_LIVENESS "${LIVE_BIND_X[@]}"
  prereq_file decision per_year "$R/v4_gates/PER_YEAR_TABLE.json"; prereq_file decision member_rule "$R/v4_gates/MEMBER_RULE_CHECK.json"
  prereq_file decision export_receipt "$R/v4_gates/BUNDLE_export_v2_${EXPORT_ARM}.json"; prereq_marker decision judge_eligible "$R/judge_v4_eligible.log" JUDGE_V4_DONE
  [ -n "${UMASK_NPZ:-}" ] || die "decision_prereq_umask_npz_missing" 3
  guard decision; stage "decision: fp2_decision.py PROFILE=formal export gate ${GATE_EXPORT:-v4e_gate_export_v2.py}"
  env V4_MONTH=$V4_MONTH R=$R D=$D PROFILE=formal EXPORT_GATE=${GATE_EXPORT:-v4e_gate_export_v2.py} PER_YEAR_JSON=$R/v4_gates/PER_YEAR_TABLE.json EXPORT_RECEIPT=$R/v4_gates/BUNDLE_export_v2_${EXPORT_ARM}.json JUDGE_JSON=$R/v4_gates/JUDGE_v4_eligible.json \
    MEMBER_RULE_JSON=$R/v4_gates/MEMBER_RULE_CHECK.json STEP1_JSON=$R/v4_gates/step1.json EXPECTED_UMASK=$UMASK_NPZ \
    LIVENESS_JSON=$R/v4_gates/member_liveness.json LIVENESS_EXPORT_JSON=$R/v4_gates/member_liveness_export.json \
    OUT_JSON=$R/v4_gates/DECISION_FP2.json OUT_MD=$R/v4_gates/DECISION_FP2.md "$PY" "$D/fp2_decision.py" > "$R/decision_fp2.log" 2>&1 < /dev/null; rc=$?
  stage "decision rc=$rc $(tail -1 "$R/decision_fp2.log" | cut -c1-160)"; [ $rc -eq 0 ] || die "stage_decision_rc_$rc" $rc
  [ -f "$R/v4_gates/DECISION_FP2.json" ] || die "decision_receipt_missing" 3
fi

if [ "$V4_STAGES" = all ]; then
  [ -f "$R/v4_gates/DECISION_FP2.json" ] || die "monthly_done_without_decision_receipt" 3   # FP3 J: a full run ends at a decision, or not at all
  stage "CHAIN_V4_MONTHLY_DONE month=$V4_MONTH (every stage rc=0 with its marker/receipt, decision receipt $R/v4_gates/DECISION_FP2.json; a candidate still needs the user ruling)"; MD=$R/v4_gates/MONTHLY_DONE.json
else
  stage "CHAIN_V4_MONTHLY_STAGES_DONE month=$V4_MONTH stages=$V4_STAGES (a SUBSET ran, rc=0 each — NOT the full chain; no MONTHLY_DONE.json)"; MD=$R/v4_gates/MONTHLY_STAGES_DONE.json
fi
"$PY" -c "import json,sys,time;json.dump({'DONE':sys.argv[2]=='all','month':sys.argv[1],'stages':sys.argv[2],'env':sys.argv[3],'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())},open(sys.argv[4],'w'),indent=1)" "$V4_MONTH" "$V4_STAGES" "$ENVF" "$MD"
