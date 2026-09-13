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
  # ★ ROUND 3 (2026-09-13, review §3.D / researcher probe BR3_file_key_indirect_ambient_reference_ACCEPTED): the presence check above proves the KEY is in the file,
  #   not that its VALUE is. `SEEDS=$UNLISTED_SEEDS` is a line of the file, survives the unset below (only CONTRACT keys are unset) and is filled in by the parent
  #   shell at `. "$f"` — so a 46-key contract could still be steered from outside. A blanket "no $ in a value" would reject both delivered contracts (the September
  #   one has 5 `$R/...` values, the October template 12), so the rule is the narrow one the reviewer proposed: a value may reference ONLY a CONTRACT key that is
  #   already DEFINED EARLIER IN THIS FILE. Command substitution and backticks stay rejected by the grep above and are re-rejected here (defence in depth).
  local unbound; unbound=$(awk -v KEYS="$V4_MONTH_KEYS" '
    BEGIN{ n = split(KEYS, a, " "); for (i = 1; i <= n; i++) contract[a[i]] = 1 }
    /^[[:space:]]*(#|$)/ { next }
    { e = index($0, "="); if (e == 0) next; key = substr($0, 1, e - 1); s = substr($0, e + 1)
      while ((p = index(s, "$")) > 0) { rest = substr(s, p + 1); brace = 0
        if (substr(rest, 1, 1) == "{") { brace = 1; rest = substr(rest, 2) }
        if (match(rest, /^[A-Za-z_][A-Za-z0-9_]*/)) { name = substr(rest, 1, RLENGTH); s = substr(rest, RLENGTH + 1)
          if (brace) { if (substr(s, 1, 1) != "}") printf "%s: malformed ${...} reference; ", key; else s = substr(s, 2) }
          if (!(name in contract)) printf "%s: $%s is not a contract key (the parent shell would fill it in); ", key, name
          else if (!(name in defined)) printf "%s: $%s is referenced before it is defined in this file; ", key, name
        } else { printf "%s: a bare $ / command substitution is not allowed in a contract value; ", key; s = rest } }
      defined[key] = 1 }' "$f")
  [ -z "$unbound" ] || { echo "month env $f: unbound reference(s): $unbound" >&2; die "month_env_unbound_reference_$(basename "$f")" 4; }
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
# ★ ROUND 3 (2026-09-13, independent review REVIEW_code_and_research_2026-09-13 §3.D / probe F-R1): the old helper proved that A JSON EXISTS, not WHAT IT IS ABOUT.
#   Three states it admitted (researcher fixtures, all rc 0): (a) weights changed and the `pt_sha256` key DELETED — `elif m.get("pt_sha256") and …` made a missing
#   sha a SKIP; (b) the four declared inputs shrunk to one — the loop walked whatever the sidecar happened to list; (c) a complete seed-42 sidecar dropped into the
#   seed-2027 slot — the function had no expected seed and read none of the seed fields. This gate runs BEFORE arms dispatch, so it is a resume-gate promise.
#   Scope of the defect (DESIGN §9.1): arms consume the monthly prediction .npy, so there is NO evidence a wrong .pt was ever used for a real prediction; what was
#   broken is the PROMISE that the refit artefacts were verified, not a proven bad training. Now: expected seed, COMPLETE key set (a missing required key is a
#   refusal — never "absent ⇒ skip"), the expected paths of this month's contract, and the ACTUAL sha256 of the .pt and of every declared input, unconditionally.
prereq_refit_sidecar(){  # prereq_refit_sidecar <stage> <name> <sidecar.json> <DLW_RAW> <F8> <expected seed> <refit source .py> — every argument is mandatory
  local stage=$1 name=$2 sc=$3 dlw=$4 f8=$5 seed=$6 src=$7 out rc
  [ -n "$seed" ] && [ -n "$src" ] || { echo "prereq $stage/$name: expected seed and refit source are MANDATORY arguments of prereq_refit_sidecar (an unbound call verifies nothing)" >&2; die "${stage}_prereq_${name}" 3; }
  out=$($PY - "$sc" "$dlw" "$f8" "$seed" "$src" 2>&1 <<'PYEOF'
import hashlib, json, os, sys
sc, dlw, f8, seed_s, src = sys.argv[1:6]
if not os.path.isfile(sc): print(f"refit sidecar missing: {sc}"); sys.exit(3)
try: m = json.load(open(sc))
except Exception as e: print(f"refit sidecar unreadable: {e}"); sys.exit(3)
if not isinstance(m, dict): print(f"refit sidecar is not a JSON object: {sc}"); sys.exit(3)
try: seed = int(seed_s)
except ValueError: print(f"expected seed {seed_s!r} is not an integer"); sys.exit(3)
bad = []
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
def _empty(v): return v is None or (isinstance(v, (str, dict, list, tuple)) and len(v) == 0)
# (1) COMPLETE KEY SET — pod_f10_refit_v4.py writes every one of these; a missing key is a REFUSAL, never a skipped check (researcher F-R1 (a))
_TOP = ("seed", "best_ep_rule", "best_ep_kept", "env_given", "inputs", "inputs_sha256", "pt", "pt_sha256", "self_sha256")
_miss = [k for k in _TOP if k not in m or _empty(m[k])]
if _miss: bad.append(f"sidecar key(s) missing or empty: {_miss} (the refit writer emits all of {list(_TOP)})")
eg = m.get("env_given") if isinstance(m.get("env_given"), dict) else {}
_egmiss = [k for k in ("F10_DLW", "F10_OUT", "SEED", "BEST_EP_FIX") if k not in eg or _empty(eg[k])]
if _egmiss: bad.append(f"env_given key(s) missing or empty: {_egmiss}")
ins = m.get("inputs") if isinstance(m.get("inputs"), dict) else {}
shas = m.get("inputs_sha256") if isinstance(m.get("inputs_sha256"), dict) else {}
_WANT = {"targets": f"{dlw}/data/dlw_targets.npz", "fea82": f"{dlw}/data/dlw_fea82.npz", "fea89": f"{f8}/data/f8_fea89.npz", "legs": f"{f8}/data/f10v2_legs.npz"}
if set(ins) != set(_WANT): bad.append(f"inputs names {sorted(ins)} != the four artefacts the refit consumes {sorted(_WANT)} (researcher F-R1 (b): a shrunk set used to pass)")
if set(shas) != set(_WANT): bad.append(f"inputs_sha256 names {sorted(shas)} != {sorted(_WANT)}")
# (2) EXPECTED PATHS — the sidecar must be about THIS month's contract directories, not merely about four files that happen to exist
for k in sorted(_WANT):
    p = ins.get(k)
    if p is not None and os.path.realpath(str(p)) != os.path.realpath(_WANT[k]): bad.append(f"input {k} path {p!r} != this month's {_WANT[k]!r}")
_ptw = f"{f8}/models/f10_live_s{seed}.pt"
if m.get("pt") is not None and os.path.realpath(str(m["pt"])) != os.path.realpath(_ptw): bad.append(f"pt path {m.get('pt')!r} != this month's {_ptw!r}")
# (3) EXPECTED SEED — all four seed carriers must agree with the seed the driver is verifying (researcher F-R1 (c))
if m.get("seed") != seed: bad.append(f"seed={m.get('seed')!r} != expected {seed}")
if str(eg.get("SEED")) != str(seed): bad.append(f"env_given.SEED={eg.get('SEED')!r} != expected {seed}")
if os.path.basename(sc) != f"f10_live_s{seed}.json": bad.append(f"sidecar file {os.path.basename(sc)!r} is not the seed-{seed} slot f10_live_s{seed}.json")
# recipe + month binding (round 2 checks, kept verbatim in meaning)
if m.get("best_ep_rule") != "fix7": bad.append(f"best_ep_rule={m.get('best_ep_rule')!r}")
if str(eg.get("BEST_EP_FIX")) != "7": bad.append(f"env_given.BEST_EP_FIX={eg.get('BEST_EP_FIX')!r}")
if m.get("best_ep_kept") != 7: bad.append(f"best_ep_kept={m.get('best_ep_kept')!r} != 7 (the fix7 rule keeps exactly epoch 7)")
if eg.get("F10_DLW") != dlw: bad.append(f"env_given.F10_DLW={eg.get('F10_DLW')!r} != {dlw!r}")
if eg.get("F10_OUT") != f8: bad.append(f"env_given.F10_OUT={eg.get('F10_OUT')!r} != {f8!r}")
# (4) ACTUAL ARTEFACT SHAs — every declared input AND the weights, verified against the bytes on disk; an absent recorded sha is its own refusal
for k in sorted(_WANT):
    p = ins.get(k)
    if p is None: continue                                                       # already named by the key-set refusal above
    if not os.path.isfile(p): bad.append(f"input {k} missing on disk: {p}"); continue
    if _empty(shas.get(k)): bad.append(f"input {k} has NO recorded sha256 in the sidecar: its identity is unverifiable"); continue
    cur = sha(p)
    if cur != shas[k]: bad.append(f"input {k} changed since refit: {cur[:12]} != {str(shas[k])[:12]}")
pt = m.get("pt")
if pt is None: pass                                                              # already named by the key-set refusal
elif not os.path.isfile(str(pt)): bad.append(f"weights missing: {pt}")
elif _empty(m.get("pt_sha256")): bad.append("sidecar records NO pt_sha256: the weights identity is unverifiable (this used to be treated as 'nothing to check')")
else:
    cur = sha(str(pt))
    if cur != m["pt_sha256"]: bad.append(f"weights changed since refit: {cur[:12]} != {str(m['pt_sha256'])[:12]}")
# (5) WHICH PROGRAM WROTE IT — the same discipline require_gate applies to gate receipts (self_sha computed at run time from the source this chain invokes)
if not os.path.isfile(src): bad.append(f"refit source missing beside the driver: {src}")
elif not _empty(m.get("self_sha256")):
    _ss = sha(src)
    if _ss != m["self_sha256"]: bad.append(f"sidecar was written by a different program: self_sha256 {str(m['self_sha256'])[:12]} != {os.path.basename(src)} {_ss[:12]}")
if bad: print("; ".join(bad)); sys.exit(3)
print(f"ok seed {seed} fix7, {len(ins)} inputs + weights verified against the bytes on disk, written by {os.path.basename(src)} {str(m['self_sha256'])[:12]}")
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
