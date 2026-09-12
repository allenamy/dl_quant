#!/bin/bash
# chain_lib.sh — shared discipline for the v4 chain drivers (review b0a573a1 P1-PIPE, 2026-09-09; round 3 after review 31fa3e4e, 2026-09-10).
#   · a stage may dispatch only on a FRESH PASS receipt OF THE EXPECTED GATE (v4_gate_common.py require <json> gate=<name> name=path ...)
#     — round 3: `gate=` is mandatory, the receipt's self sha must be real, the dependency list may not be empty
#     — round 4: `self_sha=` is mandatory and is computed AT RUN TIME from the gate script this chain invokes (gate_sha <script>):
#       a receipt written by any other program — even a real sha of the judge — is refused (researcher chain_valid_wrong_gate_source)
#     — round 4: the dependency list must contain every input registered for the gate (v4_gate_common.REQUIRED_INPUTS, `profile=<stage>` selects
#       a registered stage subset); a chain that omits a registered input is refused (researcher require_correct_identity_dependency_subset)
#   · every child is waited on BY PID and its rc collected; ANY non-zero rc aborts the driver (no merge, no DONE)
#   · merges must exit 0 AND print their completion marker
#   · the DONE line is written only on success and carries the rc list; failures write FAIL_<stage> and exit non-zero
#   · round 3: `pin_deps <name> path...` writes $R/v4_gates/deps_<name>.json = sha256 of EVERY file the stage is about to consume
#     (trainer/launcher/merge scripts, legs, features, targets); a missing file is fatal. This is PROVENANCE beside the gate receipts:
#     the receipts prove the data passed a gate, the pin proves which exact scripts and files this dispatch used.
# Source it: . chain_lib.sh ; then: SRC=$(gate_sha $R/<gate>.py) || die ... ; require_gate <json> gate=<name> self_sha=$SRC name=path ... ; pin_deps <name> path... ; run_shards <launcher> <T> <SD> ; check_marker <log> <marker>
#   · MONTHLY (2026-09-12, RUNBOOK_2026-10 §0★ 修订 2 (c), review 0dfc0d87 R2): D = the DEVICE dir (scripts, gate sources, contract) and R = the MONTH ROOT
#     (receipts, logs, deps pins) are two variables. The legacy drivers set R only and D defaults to R (device == root, September layout, unchanged).
#     `load_month_env <file>` reads the month configuration contract (v4_month_<YYYY-MM>.env) and DIES on a missing file, a malformed line or ANY
#     missing/empty key of V4_MONTH_KEYS — no path, month set, seed list, generation label or pin is ever inherited from a source constant again.
PY=${PY:-/workspace/venv/bin/python}; R=${R:-/workspace/review_scratch}; L=${L:-$R/v4_commands.txt}; D=${CHAIN_DEVICE_DIR:-$R}   # device dir: the monthly driver exports CHAIN_DEVICE_DIR; legacy drivers get D == R
say(){ echo "[$(date -u +%FT%TZ)] $*" >> "$L"; }
die(){ say "FAIL_$1"; echo "FAIL_$1" >&2; exit "${2:-1}"; }
# the month configuration contract: every key MUST be present and non-empty (schema documented in v4_month_2026-09.env and DESIGN_v4_monthly_chain_2026-09-12.md)
V4_MONTH_KEYS="V4_MONTH R PY CACHE PANEL_SPLICE PANEL_KING RAW_PATCH HOLE_CELLS DLW_RAW DLW_CLIP F8 KING_FEA KING_META MONTHS_ALL SEEDS MWF_ROOT BUNDLE_OUT BUNDLE_TAR BUNDLE_GENERATION BUNDLE_BASE EXPORT_PANEL EMA_STATE_JSON LIVE_PINS FUND_AUG FUNDING_DIR LEGS_OLD LEGS_PANEL DLW_EXT F8_EXT HC KING_DIR EXPORT_ARM SIGNAL_RECEIPT BUILDER_FEA82 BUILDER_FEA89 BASE_TRAINER GATE_STEP1 GATE_STEP2 PREV_BUNDLE PREV_META REF_META"
load_month_env(){  # load_month_env <v4_month.env> — sources the contract (KEY=value lines only; later keys may reference earlier ones as $R/...) and exports it; rc 4 on any defect
  local f=$1 k bad
  [ -n "$f" ] && [ -f "$f" ] || die "month_env_missing_${f:-<none>}" 4
  bad=$(grep -vE '^[[:space:]]*(#|$)' "$f" | grep -vE '^[A-Z_][A-Z0-9_]*=[^;&|`]*$'; grep -vE '^[[:space:]]*#' "$f" | grep -E '\$\(')   # comments are free text; every other line is KEY=value without ; & | ` $(
  [ -z "$bad" ] || { echo "month env $f: malformed line(s): $bad" >&2; die "month_env_malformed_$(basename "$f")" 4; }
  set -a; . "$f"; set +a
  for k in $V4_MONTH_KEYS; do [ -n "${!k:-}" ] || die "month_env_key_missing_$k" 4; done
  V4_MONTH_ENV=$f; export V4_MONTH_ENV
  # the names the child programs read (trainer whitelist, launcher, merge, arms, build_dev): derived from the contract, never from their defaults
  export V4_D="$D" V4_F8="$F8" V4_DLW_RAW="$DLW_RAW" V4_DLW_CLIP="$DLW_CLIP" V4_BASE_TRAINER="$BASE_TRAINER" V4_HC="$HC" V4_KING_DIR="$KING_DIR" V4_R="$R" \
         V4_TRAINER="$D/pod_f10_train_monthly_v4.py" V4_DLW_EXT="$DLW_EXT" V4_F8_EXT="$F8_EXT" V4_DEV_PREDS="$HC/dev_v4/f8_2026-08-22/preds" V4_PREV_BUNDLE="$PREV_BUNDLE" V4_PREV_META="$PREV_META" V4_REF_META="$REF_META"
  L=$R/v4_commands.txt
  echo "MONTH_ENV_OK $f V4_MONTH=$V4_MONTH R=$R D=$D MONTHS_ALL=$MONTHS_ALL SEEDS=$SEEDS BUNDLE_GENERATION=$BUNDLE_GENERATION"
}
gate_sha(){  # gate_sha <gate script> — sha256 of the gate source THIS chain trusts, from the file on disk at run time; non-zero rc if unreadable
  local out; out=$($PY "$D/v4_gate_common.py" sha "$1" 2>/dev/null) || return 3; [ -n "$out" ] || return 3; echo "${out%% *}"
}
require_gate(){  # require_gate <receipt.json> gate=<expected> self_sha=<sha of the gate source, mandatory> name=path ...
  local out; out=$($PY "$D/v4_gate_common.py" require "$@" 2>&1); local rc=$?
  say "require $1: $out"; [ $rc -eq 0 ] || die "gate_require_$(basename "$1" .json)" 3
}
run_gate(){  # run_gate <name> <gate script basename in D> <log> [ENV=val ...] — RUNS a gate program (it writes its own receipt through v4_gate_common.finalize); records rc; returns it (the caller decides: require_gate next, or die)
  local name=$1 script=$2 log=$3; shift 3
  [ -f "$D/$script" ] || die "gate_source_missing_${name}_$script" 3
  env "$@" "$PY" "$D/$script" > "$log" 2>&1; local rc=$?
  say "gate $name ($script rc=$rc) $(tail -1 "$log" | cut -c1-120)"; return $rc
}
pin_deps(){  # pin_deps <name> path... — provenance receipt of every consumed file; any missing file is fatal (exit 3)
  local name=$1; shift; local out="$R/v4_gates/deps_${name}.json"; mkdir -p "$R/v4_gates"
  $PY "$D/v4_gate_common.py" sha "$@" > "$out.txt" 2>&1 || die "deps_${name}_unreadable_file" 3
  $PY - "$out" "$out.txt" "$name" <<'PYEOF' || die "deps_${name}_write" 3
import json, sys, time
out, txt, name = sys.argv[1:4]; d = {}
for line in open(txt):
    line = line.strip()
    if not line: continue
    h, p = line.split(" ", 1); d[p] = h
json.dump({"stage": name, "n": len(d), "deps_sha256": d, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, open(out, "w"), indent=1)
PYEOF
  say "pin_deps $name: $(wc -l < "$out.txt" | tr -d ' ') files -> $out"
}
run_shards(){  # run_shards <launcher.sh> <TARGET> <SEED> ; uses SH0..SH3 (legacy: hand-written; monthly: set by set_shards_from_months_all); sets RCS and returns non-zero if any shard failed
  local launcher=$1 T=$2 SD=$3; local pids=() rcs=() k
  for k in 0 1 2 3; do eval "local M=\$SH$k"; bash "$D/$launcher" "$T" "$SD" "$k" "$M" & pids+=($!); done   # eval (not `local -n`): bash 3.2 has no namerefs; k is a literal 0..3
  for k in 0 1 2 3; do wait "${pids[$k]}"; rcs+=($?); done
  RCS="${rcs[*]}"; say "shards $T s$SD rc=[$RCS]"
  for k in "${rcs[@]}"; do [ "$k" -eq 0 ] || return 1; done; return 0
}
check_marker(){  # check_marker <log> <marker>
  grep -q "$2" "$1" || die "marker_${2}_missing_in_$(basename "$1")" 1
}
check_no_marker(){  # check_no_marker <log> <marker> — a FAIL marker present is fatal even if a DONE marker is also present
  grep -q "$2" "$1" && die "marker_${2}_present_in_$(basename "$1")" 1; return 0
}
set_shards_from_months_all(){  # set_shards_from_months_all — SH0..SH3 = round-robin over $MONTHS_ALL (v4_months.py); replaces the hand-written lists; dies if the month list is malformed
  local line; [ -n "${MONTHS_ALL:-}" ] || die "months_all_unset" 4
  while IFS= read -r line; do case $line in SH[0-3]=*) eval "$line" ;; *) say "shards: $line"; die "months_all_shards_$(echo "$line" | cut -c1-40 | tr ' ' '_')" 4 ;; esac
  done < <($PY "$D/v4_months.py" shards "$MONTHS_ALL" 4 2>&1)
  [ -n "${SH0:-}" ] && [ -n "${SH3:-}" ] || die "months_all_shards_empty" 4
  say "shards from MONTHS_ALL=$MONTHS_ALL: SH0=$SH0 SH1=$SH1 SH2=$SH2 SH3=$SH3"
}
