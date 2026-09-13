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
V4_MONTH_KEYS="V4_MONTH R PY CACHE PANEL_SPLICE PANEL_KING RAW_PATCH HOLE_CELLS DLW_RAW DLW_CLIP F8 KING_FEA KING_META MONTHS_ALL SEEDS MWF_ROOT BUNDLE_OUT BUNDLE_TAR BUNDLE_GENERATION BUNDLE_BASE EXPORT_PANEL EMA_STATE_JSON LIVE_PINS FUND_AUG FUNDING_DIR LEGS_OLD LEGS_PANEL DLW_EXT F8_EXT HC KING_DIR EXPORT_ARM SIGNAL_RECEIPT BUILDER_FEA82 BUILDER_FEA89 BASE_TRAINER GATE_STEP1 GATE_STEP2 PREV_BUNDLE PREV_META REF_META PREV_DLW_CLIP PREV_F8 PREV_KING_FEA PREV_KING_FEA_UNCLAMPED PREV_CLAMP_BUILDER_SHA256"   # 46 keys (W7 2026-09-12: +4 reference keys of the month-generic data gates, PREREG_v4_gates_monthly_2026-09-12 §2; +1 builder identity pin, PREREG AMENDMENT 1 / researcher B-R4)
load_month_env(){  # load_month_env <v4_month.env> — sources the contract (KEY=value lines only; later keys may reference earlier ones as $R/...) and exports it; rc 4 on any defect
  local f=$1 k bad
  [ -n "$f" ] && [ -f "$f" ] || die "month_env_missing_${f:-<none>}" 4
  bad=$(grep -vE '^[[:space:]]*(#|$)' "$f" | grep -vE '^[A-Z_][A-Z0-9_]*=[^;&|`]*$'; grep -vE '^[[:space:]]*#' "$f" | grep -E '\$\(')   # comments are free text; every other line is KEY=value without ; & | ` $(
  [ -z "$bad" ] || { echo "month env $f: malformed line(s): $bad" >&2; die "month_env_malformed_$(basename "$f")" 4; }
  # B-R3 (independent review 2026-09-12): a key must be PRESENT IN THE FILE — a value inherited from the parent shell is not the contract's value.
  #   (1) every key must appear as a `KEY=` line of the file; (2) all contract keys are UNSET before sourcing, so nothing the caller exported survives.
  local present; present=" $(grep -oE '^[A-Z_][A-Z0-9_]*=' "$f" | tr -d '=' | tr '\n' ' ') "
  for k in $V4_MONTH_KEYS; do case "$present" in *" $k "*) ;; *) echo "month env $f: key $k is not a line of the file (an inherited environment value does not count)" >&2; die "month_env_key_missing_$k" 4 ;; esac; done
  unset $V4_MONTH_KEYS V4_MONTH_ENV
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
# ── B-R1 (independent review 2026-09-12): a stage may DISPATCH only after its prerequisites are verified here, bound to THIS month's root/contract —
#    the dependency graph is code, not file order. Every helper dies with FAIL_<stage>_prereq_<name> (rc 3) naming the missing/mismatching item.
prereq_receipt(){  # prereq_receipt <stage> <name> <receipt.json> <gate> — receipt exists, names <gate>, PASS true; PREFLIGHT additionally bound to this contract (month_env_sha256) and root
  local stage=$1 name=$2 rp=$3 gate=$4 out rc
  out=$($PY - "$rp" "$gate" "${V4_MONTH_ENV:-}" "$R" 2>&1 <<'PYEOF'
import hashlib, json, os, sys
rp, gate, envf, root = sys.argv[1:5]
if not os.path.isfile(rp): print(f"receipt missing: {rp}"); sys.exit(3)
try: r = json.load(open(rp))
except Exception as e: print(f"receipt unreadable: {e}"); sys.exit(3)
if r.get("gate") != gate: print(f"receipt is from gate {r.get('gate')!r}, expected {gate!r}"); sys.exit(3)
if r.get("PASS") is not True: print(f"receipt says PASS={r.get('PASS')!r} ({r.get('utc')})"); sys.exit(3)
if gate == "PREFLIGHT":
    h = hashlib.sha256(open(envf, "rb").read()).hexdigest() if envf and os.path.isfile(envf) else None
    if r.get("month_env_sha256") != h: print(f"preflight receipt is bound to contract sha {str(r.get('month_env_sha256'))[:12]}, this run's contract is {str(h)[:12]}"); sys.exit(3)
    if os.path.realpath(str(r.get("root", ""))) != os.path.realpath(root): print(f"preflight receipt root {r.get('root')} != this root {root}"); sys.exit(3)
print(f"ok {gate} {r.get('utc')}")
PYEOF
); rc=$?
  say "prereq $stage/$name: $out"; [ $rc -eq 0 ] || { echo "prereq $stage/$name: $out" >&2; die "${stage}_prereq_${name}" 3; }
}
prereq_marker(){  # prereq_marker <stage> <name> <log> <marker> [<forbidden marker>] — the log exists in THIS root and carries the marker (and not the forbidden one)
  local stage=$1 name=$2 log=$3 marker=$4 bad=${5:-}
  [ -f "$log" ] || { say "prereq $stage/$name: log missing $log"; echo "prereq $stage/$name: log missing $log" >&2; die "${stage}_prereq_${name}" 3; }
  grep -q "$marker" "$log" || { say "prereq $stage/$name: marker $marker absent in $log"; echo "prereq $stage/$name: marker $marker absent in $log" >&2; die "${stage}_prereq_${name}" 3; }
  [ -z "$bad" ] || ! grep -q "$bad" "$log" || { say "prereq $stage/$name: forbidden marker $bad present in $log"; echo "prereq $stage/$name: forbidden marker $bad present in $log" >&2; die "${stage}_prereq_${name}" 3; }
  say "prereq $stage/$name: ok ($marker in $(basename "$log"))"
}
prereq_file(){  # prereq_file <stage> <name> <path>
  [ -f "$3" ] || { say "prereq $1/$2: file missing $3"; echo "prereq $1/$2: file missing $3" >&2; die "${1}_prereq_${2}" 3; }; say "prereq $1/$2: ok $3"
}
prereq_json_eq(){  # prereq_json_eq <stage> <name> <json> <field> <expected> — a recorded identity (e.g. cache_sha256) must equal what this run is about to consume
  local stage=$1 name=$2 jp=$3 field=$4 want=$5 out rc
  out=$($PY -c 'import json,sys;r=json.load(open(sys.argv[1]));v=str(r.get(sys.argv[2]));sys.exit(0 if v==sys.argv[3] else (print(f"{sys.argv[2]}={v[:16]} != expected {sys.argv[3][:16]}") or 3))' "$jp" "$field" "$want" 2>&1); rc=$?
  say "prereq $stage/$name: ${out:-ok $field}"; [ $rc -eq 0 ] || { echo "prereq $stage/$name: $out" >&2; die "${stage}_prereq_${name}" 3; }
}
prereq_deps_identity(){  # prereq_deps_identity <stage> <name> <deps.json> path... — every path's CURRENT sha256 equals the sha pin_deps recorded for it (the dispatch is bound to the files it pinned)
  local stage=$1 name=$2 dp=$3; shift 3; local out rc
  out=$($PY - "$dp" "$@" 2>&1 <<'PYEOF'
import hashlib, json, os, sys
dp = sys.argv[1]; paths = sys.argv[2:]
if not os.path.isfile(dp): print(f"deps receipt missing: {dp}"); sys.exit(3)
d = json.load(open(dp)).get("deps_sha256", {}); bad = []
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
for p in paths:
    if p not in d: bad.append(f"{p}: not pinned"); continue
    if not os.path.isfile(p): bad.append(f"{p}: missing on disk"); continue
    cur = sha(p)
    if cur != d[p]: bad.append(f"{p}: {cur[:12]} != pinned {d[p][:12]}")
if bad: print("; ".join(bad)); sys.exit(3)
print(f"ok {len(paths)} files identical to the pins")
PYEOF
); rc=$?
  say "prereq $stage/$name: $out"; [ $rc -eq 0 ] || { echo "prereq $stage/$name: $out" >&2; die "${stage}_prereq_${name}" 3; }
}
prereq_refit_sidecar(){  # prereq_refit_sidecar <stage> <name> <sidecar.json> <DLW_RAW> <F8> — best_ep_rule fix7, env_given bound to THIS month's dirs, every recorded input sha == the file now on disk
  local stage=$1 name=$2 sc=$3 dlw=$4 f8=$5 out rc
  out=$($PY - "$sc" "$dlw" "$f8" 2>&1 <<'PYEOF'
import hashlib, json, os, sys
sc, dlw, f8 = sys.argv[1:4]
if not os.path.isfile(sc): print(f"refit sidecar missing: {sc}"); sys.exit(3)
m = json.load(open(sc)); bad = []
if m.get("best_ep_rule") != "fix7": bad.append(f"best_ep_rule={m.get('best_ep_rule')!r}")
eg = m.get("env_given") or {}
if eg.get("F10_DLW") != dlw: bad.append(f"env_given.F10_DLW={eg.get('F10_DLW')!r} != {dlw!r}")
if eg.get("F10_OUT") != f8: bad.append(f"env_given.F10_OUT={eg.get('F10_OUT')!r} != {f8!r}")
if str(eg.get("BEST_EP_FIX")) != "7": bad.append(f"env_given.BEST_EP_FIX={eg.get('BEST_EP_FIX')!r}")
ins = m.get("inputs") or {}; shas = m.get("inputs_sha256") or {}
if not ins or not shas: bad.append("sidecar records no inputs/inputs_sha256")
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
for k, p in ins.items():
    if not os.path.isfile(p): bad.append(f"input {k} missing on disk: {p}"); continue
    if sha(p) != shas.get(k): bad.append(f"input {k} changed since refit: {sha(p)[:12]} != {str(shas.get(k))[:12]}")
pt = m.get("pt")
if not pt or not os.path.isfile(pt): bad.append(f"weights missing: {pt}")
elif m.get("pt_sha256") and sha(pt) != m["pt_sha256"]: bad.append(f"weights changed since refit: {sha(pt)[:12]} != {m['pt_sha256'][:12]}")
if bad: print("; ".join(bad)); sys.exit(3)
print(f"ok seed {m.get('seed')} fix7, {len(ins)} inputs + weights identical")
PYEOF
); rc=$?
  say "prereq $stage/$name: $out"; [ $rc -eq 0 ] || { echo "prereq $stage/$name: $out" >&2; die "${stage}_prereq_${name}" 3; }
}
prereq_count(){  # prereq_count <stage> <name> <file> <grep pattern> <min> — at least <min> matching lines
  local stage=$1 name=$2 f=$3 pat=$4 min=$5 n
  n=$(grep -a -c "$pat" "$f" 2>/dev/null || echo 0); say "prereq $stage/$name: $n lines match ($min needed)"
  [ "$n" -ge "$min" ] || { echo "prereq $stage/$name: $n lines match ($min needed) in $f" >&2; die "${stage}_prereq_${name}" 3; }
}
# ── B-R3: subprocesses of the data stage run under `env -i` with ONLY this allowlist passed through + the variables the driver sets explicitly, so an
#    ambient DLWT_RAW_PATCH / F171_* / F8_* / CACHE_IN of the parent shell can never reach a builder. Usage: clean_env; env -i "${CLEAN_ENV[@]}" KEY=val ... "$PY" ...
clean_env(){
  local v; CLEAN_ENV=()
  for v in PATH HOME LANG LC_ALL TMPDIR VIRTUAL_ENV LD_LIBRARY_PATH OMP_NUM_THREADS MKL_NUM_THREADS OPENBLAS_NUM_THREADS PYTHONDONTWRITEBYTECODE CUDA_VISIBLE_DEVICES; do
    [ -n "${!v:-}" ] && CLEAN_ENV+=("$v=${!v}")
  done; return 0
}
