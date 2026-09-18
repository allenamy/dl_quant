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
# ★ FP2-3 (2026-09-17, PENDING_DECISIONS「月度重训启动重核上月合同」): OPTIONAL contract keys — registered (the parser accepts them) but NOT
#   required (a contract without them still loads: the frozen September contract has no previous month). The monthly driver's preflight REQUIRES
#   them for every month after 2026-09 and re-runs the roll gate live against them (see chain_v4_monthly.sh preflight).
# ★ FP2-8 (2026-09-17, DESIGN_FP2-8 AMENDMENT 1.3): BUILDER_TARGETS / BUILDER_KING_FEA select the data-stage builders BY BASENAME in D (default = the
#   frozen v1 names); MEMBER_MASK is an optional training member mask (ts, symbols, mask) passed to both builders as MEMBER_MASK_NPZ (empty ⇒ v1 behaviour).
V4_MONTH_OPTIONAL_KEYS="PREV_MONTH_ENV PREV_SHA_JSON BUILDER_TARGETS BUILDER_KING_FEA MEMBER_MASK GATE_EXPORT GATE_LIVENESS UMASK_NPZ CONTROLS_REF_KING_FEA CONTROLS_REF_KING_META CONTROLS_REF_DL_TARGETS"   # FP3 F/J (2026-09-18): liveness-gate variant basename; evaluation umask (sha bound to the contract in preflight); reference builds for the controls stage   # GATE_EXPORT (PROPOSED5): export-gate variant basename in D, default v4e_gate_export_v2.py
load_month_env(){  # load_month_env <v4_month.env> — PARSES the contract as DATA (round 4: the file is never sourced) and exports exactly the parsed pairs; rc 4 on any defect
  # ★ P2-2 (independent review round 4, 2026-09-17): an OPTIONAL key absent from the month file must be ABSENT after loading — never inherited from the
  #   parent environment (a leftover GATE_EXPORT / MEMBER_MASK in the caller's shell selected a gate / a mask the contract did not name).
  local _ok; for _ok in $V4_MONTH_OPTIONAL_KEYS; do unset "$_ok"; done
  # ★ ROUND 4 (2026-09-13, independent review REVIEW_round3_code_and_research_2026-09-13 §4 R3-D3; probes D3_bundle_continuation_A/B, D3_source_parse_error_ignored,
  #   D3_assignment_prefixed_command_marker_written, D3_parent_tilde_parent_A/B): rounds 2-3 checked PHYSICAL LINES with grep/awk and then let Bash source the file,
  #   i.e. two different grammars. A trailing backslash joined `BUNDLE_OUT=$R\` with the next line into `$RBUNDLE_TAR`, a PARENT variable, under an unchanged
  #   contract sha; an unclosed quote made the source fail while the loader still printed MONTH_ENV_OK; `SEEDS=42 : > file` ran a command; `~/king` followed the
  #   parent HOME. A longer character blacklist only moves that boundary, so there is now ONE grammar, parsed by Python and never executed:
  #     line    := blank | comment | KEY=VALUE      blank = spaces/tabs only; comment = optional spaces/tabs then #, free text
  #     KEY     := a key of V4_MONTH_KEYS, at most ONCE per file, starting in column 1
  #     VALUE   := ( LITERAL | $NAME | ${NAME} )*   LITERAL characters: A-Z a-z 0-9 _ . / , : @ % + = -   and nothing else (no quote, backslash, space, tab,
  #                                                  tilde, glob, ; & | < > parenthesis, backtick, #)
  #     NAME    := a key DEFINED EARLIER IN THIS FILE; the parser substitutes that key's already-resolved value (the parent shell never fills anything in)
  #   The parser's rc is checked, and its output is re-validated here (registered key names, each exactly once, non-empty LITERAL values) before anything is
  #   exported. Refusal names: month_env_missing / _malformed / _key_missing_<K> / _unbound_reference (the round-2/3 classes, kept) + _duplicate_key_<K> /
  #   _parser_failed_rc_<rc> / _parser_output. Interpreter = the pre-contract $PY (chain_lib default /workspace/venv/bin/python); the contract's PY takes over after.
  local f=$1 k v line out rc py=$PY got=" " first rest
  [ -n "$f" ] && [ -f "$f" ] || die "month_env_missing_${f:-<none>}" 4
  out=$(V4_MONTH_OPTIONAL_KEYS="$V4_MONTH_OPTIONAL_KEYS" "$py" - "$f" "$V4_MONTH_KEYS" <<'PYEOF'
import os, re, sys
path, keys = sys.argv[1], sys.argv[2].split()
optional = os.environ.get("V4_MONTH_OPTIONAL_KEYS", "").split()   # FP2-3: accepted if present, never required (passed by ENV so the argv shape is unchanged)
REG = set(keys) | set(optional)
LIT = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_./,:@%+=-")
NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
ASSIGN = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)=(.*)", re.S)
BLANK = re.compile(r"[ \t]*")
COMMENT = re.compile(r"[ \t]*#.*", re.S)
SAY = {chr(92): "a backslash: line continuation or escape", chr(34): "a double quote", chr(39): "a single quote", chr(32): "a space", chr(9): "a tab",
       chr(126): "a tilde: expands to the parent HOME", chr(96): "a backtick: command substitution", chr(13): "a carriage return"}
def refuse(cls, arg, why):
    print("REFUSED " + cls + ((" " + arg) if arg else ""))
    for w in why[:12]: print("  " + w)
    if len(why) > 12: print("  ... and " + str(len(why) - 12) + " more")
    sys.exit(4)
try:
    raw = open(path, "rb").read()
except OSError as e:
    refuse("malformed", "", ["unreadable: " + str(e)])
try:
    text = raw.decode("utf-8")
except UnicodeDecodeError as e:
    refuse("malformed", "", ["not UTF-8 text: " + str(e)])
lines = text.split(chr(10))
if lines and lines[-1] == "":
    lines.pop()
malformed, duplicate, unbound = [], [], []
first_line, resolved = {}, {}
for no, line in enumerate(lines, 1):
    if BLANK.fullmatch(line) or COMMENT.fullmatch(line):
        continue
    m = ASSIGN.fullmatch(line)
    if not m:
        malformed.append(f"line {no}: not KEY=VALUE, a # comment or a blank line: {line[:80]!r}")
        continue
    key, val = m.group(1), m.group(2)
    if key not in REG:
        malformed.append(f"line {no}: {key} is not a registered contract key of V4_MONTH_KEYS")
        continue
    dup = key in first_line
    if dup:
        duplicate.append((key, f"line {no}: {key} is defined a second time, first at line {first_line[key]}: a contract names each key once"))
    else:
        first_line[key] = no
    parts, i, bad = [], 0, False
    while i < len(val):
        c = val[i]
        if c in LIT:
            j = i
            while j < len(val) and val[j] in LIT:
                j += 1
            parts.append(val[i:j]); i = j
            continue
        if c == "$":
            nx = val[i + 1:i + 2]
            if nx == chr(40):
                malformed.append(f"line {no}: {key}: a command or arithmetic substitution at column {len(key) + 2 + i} is not part of the value grammar"); bad = True; break
            if nx == "{":
                mm = NAME.match(val, i + 2)
                if not (mm and val[mm.end():mm.end() + 1] == "}"):
                    unbound.append(f"{key}: malformed ${{...}} reference at column {len(key) + 2 + i}: only ${{NAME}} is allowed"); bad = True; break
                name, nxt = mm.group(0), mm.end() + 1
            else:
                mm = NAME.match(val, i + 1)
                if not mm:
                    unbound.append(f"{key}: a bare $ / command substitution is not allowed in a contract value, column {len(key) + 2 + i}"); bad = True; break
                name, nxt = mm.group(0), mm.end()
            if name not in REG:
                unbound.append(f"{key}: ${name} is not a contract key (the parent shell would fill it in)"); bad = True; break
            if name not in resolved:
                unbound.append(f"{key}: ${name} is referenced before it is defined in this file"); bad = True; break
            parts.append(resolved[name]); i = nxt
            continue
        malformed.append(f"line {no}: {key}: {SAY.get(c, repr(c))} at column {len(key) + 2 + i} is not part of the value grammar"); bad = True; break
    if not dup:
        resolved[key] = "" if bad else "".join(parts)
if malformed:
    refuse("malformed", "", malformed + [d for _, d in duplicate])
if duplicate:
    refuse("duplicate_key", duplicate[0][0], [d for _, d in duplicate])
absent = [k for k in keys if k not in first_line]
if absent:
    refuse("key_missing", absent[0], [f"key {k} is not a line of the file (an inherited environment value does not count)" for k in absent])
if unbound:
    refuse("unbound_reference", "", ["unbound reference: " + u for u in unbound])
empty = [k for k in list(keys) + [o for o in optional if o in first_line] if resolved[k] == ""]
if empty:
    refuse("key_missing", empty[0], [f"key {k} is present but EMPTY" for k in empty])
for k in list(keys) + [o for o in optional if o in first_line]:   # FP2-3: optional keys are emitted (and exported) when present
    print(k + "=" + resolved[k])
PYEOF
); rc=$?
  if [ $rc -ne 0 ]; then
    first=${out%%$'\n'*}; rest=""; [ "$first" = "$out" ] || rest=${out#*$'\n'}
    echo "month env $f: parser rc=$rc: ${first}${rest:+ | }${rest}" >&2
    case $first in
      "REFUSED malformed") die "month_env_malformed_$(basename "$f")" 4 ;;
      "REFUSED unbound_reference") die "month_env_unbound_reference_$(basename "$f")" 4 ;;
      "REFUSED key_missing "*) k=${first#REFUSED key_missing }; case " $V4_MONTH_KEYS " in *" $k "*) die "month_env_key_missing_$k" 4 ;; esac ;;
      "REFUSED duplicate_key "*) k=${first#REFUSED duplicate_key }; case " $V4_MONTH_KEYS " in *" $k "*) die "month_env_duplicate_key_$k" 4 ;; esac ;;
    esac
    die "month_env_parser_failed_rc_${rc}_$(basename "$f")" 4
  fi
  # rc 0 is not trusted on its own: every output line must be a registered KEY, once, with a non-empty value made of LITERAL characters only
  # ★ ROUND 5 (2026-09-13, FX-TRAIN TRN-19; independent review round 4 probe parser_bare_registered_key_OUTPUT_ACCEPTED): a line with NO '=' split into
  #   k == v == the whole line (`${line%%=*}` and `${line#*=}` both return it), so a bare `R` passed all four checks below and was exported as R=R.
  #   The '=' is now required BEFORE the split; the real parser always prints KEY=VALUE, so only a broken or substituted $PY reaches this refusal.
  while IFS= read -r line; do
    case $line in *=*) ;; *) echo "month env $f: parser output line has no '=' (not KEY=VALUE): ${line:0:80}" >&2; die "month_env_parser_output_$(basename "$f")" 4 ;; esac
    k=${line%%=*}; v=${line#*=}
    case $k in ""|*[!ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_]*) echo "month env $f: parser output line is not KEY=VALUE: ${line:0:80}" >&2; die "month_env_parser_output_$(basename "$f")" 4 ;; esac
    case " $V4_MONTH_KEYS $V4_MONTH_OPTIONAL_KEYS " in *" $k "*) ;; *) echo "month env $f: parser emitted an unregistered key $k" >&2; die "month_env_parser_output_$(basename "$f")" 4 ;; esac
    case $k in GATE_EXPORT|GATE_LIVENESS) case ${line#*=} in */*|.*|"") echo "month env $f: $k must be a bare basename in D (got '${line#*=}'): a path alias skipped the variant scope binding (review round 5); BUILDER_* keys are checked by the driver, STEP gates check their own basename" >&2; die "month_env_not_a_basename_${k}_$(basename "$f")" 4 ;; esac ;; esac
    case $got in *" $k "*) echo "month env $f: parser emitted $k twice" >&2; die "month_env_parser_output_$(basename "$f")" 4 ;; esac
    case $v in ""|*[!ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_./,:@%+=-]*) echo "month env $f: parser emitted a value for $k outside the LITERAL grammar" >&2; die "month_env_parser_output_$(basename "$f")" 4 ;; esac
    got="$got$k "
  done <<< "$out"
  for k in $V4_MONTH_KEYS; do case $got in *" $k "*) ;; *) echo "month env $f: parser output lacks key $k" >&2; die "month_env_parser_output_$(basename "$f")" 4 ;; esac; done
  # B-R3 (kept): nothing the caller exported survives — every contract key is UNSET, then EXACTLY the parsed pairs are exported
  # ★ R12-C3 (round 12): V4_UMASK_NPZ is NOT a contract key, so the unset list never touched it and an ambient value reached
  #   run_v4_arms.sh unchanged (the reviewer's argv spy: clean env ⇒ the wrapper's own default mask, polluted env ⇒ a foreign mask,
  #   both rc 0). It is cleared here and re-derived below from the contract-bound UMASK_NPZ, so one approved file reaches every consumer.
  unset $V4_MONTH_KEYS V4_MONTH_ENV V4_UMASK_NPZ
  while IFS= read -r line; do export "${line%%=*}=${line#*=}" || die "month_env_export_${line%%=*}" 4; done <<< "$out"
  for k in $V4_MONTH_KEYS; do [ -n "${!k:-}" ] || die "month_env_key_missing_$k" 4; done
  V4_MONTH_ENV=$f; export V4_MONTH_ENV
  # the names the child programs read (trainer whitelist, launcher, merge, arms, build_dev): derived from the contract, never from their defaults
  export V4_D="$D" V4_F8="$F8" V4_DLW_RAW="$DLW_RAW" V4_DLW_CLIP="$DLW_CLIP" V4_BASE_TRAINER="$BASE_TRAINER" V4_HC="$HC" V4_KING_DIR="$KING_DIR" V4_R="$R" \
         V4_TRAINER="$D/pod_f10_train_monthly_v4.py" V4_DLW_EXT="$DLW_EXT" V4_F8_EXT="$F8_EXT" V4_DEV_PREDS="$HC/dev_v4/f8_2026-08-22/preds" V4_PREV_BUNDLE="$PREV_BUNDLE" V4_PREV_META="$PREV_META" V4_REF_META="$REF_META"
  # ★ R12-C3: the evaluation umask the contract declares (and preflight binds to approved_baseline.umask_npz_sha256) is the ONLY one the
  #   children may see. Declared ⇒ exported as V4_UMASK_NPZ for every consumer; not declared ⇒ stays unset and each consumer refuses,
  #   instead of silently using its own default.
  [ -z "${UMASK_NPZ:-}" ] || export V4_UMASK_NPZ="$UMASK_NPZ"
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
prereq_receipt(){  # prereq_receipt <stage> <name> <receipt.json> <gate> [<profile>] [<key>=<path> ...] — receipt exists, names <gate>, PASS true; PREFLIGHT
                   # additionally bound to this contract (month_env_sha256) and root; every GOVERNED gate is re-verified through v4_gate_common.require.
                   # ★ R13-C1 (independent review round 13): every <key>=<path> the caller passes must be the artefact THIS run is using — the receipt's
                   # recorded path for that key must be the same file (realpath) and its recorded sha must equal that file's bytes now. Without it a
                   # GENUINE PASS produced from ANOTHER candidate's (healthy) data satisfies `require` — which only re-hashes what the receipt itself
                   # points at — and opens this run's stages. The reviewer transplanted exactly such a ticket into a root whose own run FAILS the gate.
  local stage=$1 name=$2 rp=$3 gate=$4 prof="" a; shift 4
  local -a want=()
  for a in "$@"; do case $a in *=*) want+=("$a") ;; *) [ -z "$prof" ] && prof=$a ;; esac; done
  local out rc
  out=$($PY - "$rp" "$gate" "${V4_MONTH_ENV:-}" "$R" "$D" "$prof" "${want[@]}" 2>&1 <<'PYEOF'
import hashlib, json, os, sys
rp, gate, envf, root, dev, prof = (sys.argv[1:7] + [""] * 6)[:6]
want = {}                                                                    # R13-C1: key -> the path THIS run expects the receipt to have consumed
for a in sys.argv[7:]:
    if "=" in a:
        k, v = a.split("=", 1)
        if v: want[k] = v
if not os.path.isfile(rp): print(f"receipt missing: {rp}"); sys.exit(3)
try: r = json.load(open(rp))
except Exception as e: print(f"receipt unreadable: {e}"); sys.exit(3)
if r.get("gate") != gate: print(f"receipt is from gate {r.get('gate')!r}, expected {gate!r}"); sys.exit(3)
if r.get("PASS") is not True: print(f"receipt says PASS={r.get('PASS')!r} ({r.get('utc')})"); sys.exit(3)
if gate == "PREFLIGHT":
    h = hashlib.sha256(open(envf, "rb").read()).hexdigest() if envf and os.path.isfile(envf) else None
    if r.get("month_env_sha256") != h: print(f"preflight receipt is bound to contract sha {str(r.get('month_env_sha256'))[:12]}, this run's contract is {str(h)[:12]}"); sys.exit(3)
    if os.path.realpath(str(r.get("root", ""))) != os.path.realpath(root): print(f"preflight receipt root {r.get('root')} != this root {root}"); sys.exit(3)
    print(f"ok {gate} {r.get('utc')}"); sys.exit(0)
# ★ R12-C2 (independent review round 12): a downstream/recovery stage used to accept a receipt on NAME + PASS alone, so the literal
#   {"gate": "MEMBER_LIVENESS", "PASS": true} opened king/legs/mwf/refit/arms/member_rule/decision with no source, no contract approval
#   and no inputs. Every GOVERNED gate is now re-verified through the SAME v4_gate_common.require the gates/export stages use: the
#   receipt's own self_sha256 must be an APPROVED source of that gate in the frozen contract, the registered input floor must be
#   declared, and EVERY input the receipt recorded is re-hashed on disk now (recorded_extras). An ungoverned gate keeps name+PASS and
#   SAYS so, instead of pretending it was verified.
sys.path.insert(0, dev)
try: import v4_gate_common as GC
except Exception as e: print(f"v4_gate_common unimportable from {dev}: {e}"); sys.exit(3)
governed = gate in GC.REQUIRED_INPUTS or any(k.startswith(gate + "@") for k in GC.REQUIRED_INPUTS)
if not governed:
    print(f"ok {gate} {r.get('utc')} (ungoverned gate: name+PASS only, no registered input floor)"); sys.exit(0)
ss = r.get("self_sha256")
if not isinstance(ss, str) or len(ss) != 64:
    print(f"receipt carries no usable self_sha256 ({ss!r}): an unidentified program's PASS is not a prerequisite"); sys.exit(3)
ip = r.get("inputs_path")
if not isinstance(ip, dict) or not ip:
    print("receipt records no inputs_path: nothing can be re-hashed, so this PASS cannot be re-verified"); sys.exit(3)
ok, why = GC.require(rp, {k: v for k, v in ip.items() if isinstance(v, str)}, expected_gate=gate,
                     expected_self_sha=ss, profile=(prof or None), recorded_extras=True)
if not ok: print(f"require refused this receipt: {why}"); sys.exit(3)
# ★ R13-C1: `require` proves the receipt is internally consistent with the files IT names. It does NOT prove those files are this run's
#   candidate. A genuine PASS written from another root's healthy data passes everything above. Bind each expected key to the artefact
#   this stage is about to consume: same file by realpath, and the sha the receipt recorded for it equal to that file's bytes now.
ish = r.get("inputs_sha256") or {}
for k, p in sorted(want.items()):
    rp_ = ip.get(k)
    if not isinstance(rp_, str) or not rp_:
        print(f"receipt records no input {k!r}: it cannot be bound to this run's {p}"); sys.exit(3)
    if os.path.realpath(rp_) != os.path.realpath(p):
        print(f"receipt's {k} is {rp_}, this run uses {p}: the PASS was produced from another candidate's artefact"); sys.exit(3)
    if not os.path.isfile(p):
        print(f"this run's {k} is missing on disk: {p}"); sys.exit(3)
    now = hashlib.sha256(open(p, "rb").read()).hexdigest()
    if ish.get(k) != now:
        print(f"receipt's {k} sha {str(ish.get(k))[:12]} != this run's file {now[:12]} ({p})"); sys.exit(3)
print(f"ok {gate} {r.get('utc')} (re-verified: source {ss[:12]} approved in the contract, {len(ip)} recorded inputs re-hashed"
      + (f", {len(want)} bound to this run's artefacts: {','.join(sorted(want))})" if want else ", no candidate binding requested)"))
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
# ★ ROUND 4 (2026-09-13, independent review REVIEW_round3_code_and_research_2026-09-13 §4 R3-D1; probes D1_changed_{targets,fea82,fea89,legs}_null_locator_ACCEPTED,
#   D1_all_four_null_locators_ACCEPTED, D1_missing_target_null_locator_ACCEPTED, all rc 0): round 3 compared the KEY SET, but a key may hold null. The path
#   comparison ran only `if p is not None`, the hash loop said `if p is None: continue`, and the helper still printed "4 inputs + weights verified". So a changed,
#   or even DELETED, input passed as soon as its locator was nulled. "The real writer never emits null" is no exemption: this gate exists to refuse damaged or
#   mismatched sidecars. Now: (i) every required locator (four inputs + pt) must be a NON-EMPTY STRING resolving to this month's expected path; (ii) INDEPENDENTLY
#   of whatever the locator says, each expected file must exist at the expected path and hash to the recorded sha256 (a 64-hex digest, as the writer's
#   hexdigest emits), unconditionally; (iii) the ok line is assembled only from checks that ran and passed, and a check that did not run is itself a refusal.
prereq_refit_sidecar(){  # prereq_refit_sidecar <stage> <name> <sidecar.json> <DLW_RAW> <F8> <expected seed> <refit source .py> — every argument is mandatory
  local stage=$1 name=$2 sc=$3 dlw=$4 f8=$5 seed=$6 src=$7 out rc
  [ -n "$seed" ] && [ -n "$src" ] || { echo "prereq $stage/$name: expected seed and refit source are MANDATORY arguments of prereq_refit_sidecar (an unbound call verifies nothing)" >&2; die "${stage}_prereq_${name}" 3; }
  out=$($PY - "$sc" "$dlw" "$f8" "$seed" "$src" 2>&1 <<'PYEOF'
import hashlib, json, os, re, sys
sc, dlw, f8, seed_s, src = sys.argv[1:6]
if not os.path.isfile(sc): print(f"refit sidecar missing: {sc}"); sys.exit(3)
try: m = json.load(open(sc))
except Exception as e: print(f"refit sidecar unreadable: {e}"); sys.exit(3)
if not isinstance(m, dict): print(f"refit sidecar is not a JSON object: {sc}"); sys.exit(3)
try: seed = int(seed_s)
except ValueError: print(f"expected seed {seed_s!r} is not an integer"); sys.exit(3)
bad = []; ran = {}                                                               # ran[check] = evidence of a check that RAN and PASSED; the ok line reads only this
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
def _empty(v): return v is None or (isinstance(v, (str, dict, list, tuple)) and len(v) == 0)
def _locator(v): return isinstance(v, str) and v != ""                        # round 4: null / non-string / empty is NOT a locator
_HEX = re.compile(r"[0-9a-f]{64}")
def _digest(v): return isinstance(v, str) and _HEX.fullmatch(v) is not None
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
# (2) EXPECTED LOCATORS — every required locator is a non-empty path STRING naming this month's artefact (round 4, R3-D1: a null locator used to skip BOTH checks)
for k in sorted(_WANT):
    p = ins.get(k)
    if not _locator(p): bad.append(f"input {k} locator is {p!r}: a required locator must be a non-empty path string naming this month's {_WANT[k]!r} (a null locator is a refusal, never a skipped check)")
    elif os.path.realpath(p) != os.path.realpath(_WANT[k]): bad.append(f"input {k} path {p!r} != this month's {_WANT[k]!r}")
    else: ran[f"locator:{k}"] = p
_ptw = f"{f8}/models/f10_live_s{seed}.pt"; _ptl = m.get("pt")
if not _locator(_ptl): bad.append(f"pt locator is {_ptl!r}: a required locator must be a non-empty path string naming this month's {_ptw!r}")
elif os.path.realpath(_ptl) != os.path.realpath(_ptw): bad.append(f"pt path {_ptl!r} != this month's {_ptw!r}")
else: ran["locator:pt"] = _ptl
# (3) EXPECTED SEED — all four seed carriers must agree with the seed the driver is verifying (researcher F-R1 (c))
_sb = len(bad)
if m.get("seed") != seed: bad.append(f"seed={m.get('seed')!r} != expected {seed}")
if str(eg.get("SEED")) != str(seed): bad.append(f"env_given.SEED={eg.get('SEED')!r} != expected {seed}")
if os.path.basename(sc) != f"f10_live_s{seed}.json": bad.append(f"sidecar file {os.path.basename(sc)!r} is not the seed-{seed} slot f10_live_s{seed}.json")
if len(bad) == _sb: ran["seed"] = seed
# recipe + month binding (round 2 checks, kept verbatim in meaning)
if m.get("best_ep_rule") != "fix7": bad.append(f"best_ep_rule={m.get('best_ep_rule')!r}")
if str(eg.get("BEST_EP_FIX")) != "7": bad.append(f"env_given.BEST_EP_FIX={eg.get('BEST_EP_FIX')!r}")
if m.get("best_ep_kept") != 7: bad.append(f"best_ep_kept={m.get('best_ep_kept')!r} != 7 (the fix7 rule keeps exactly epoch 7)")
if eg.get("F10_DLW") != dlw: bad.append(f"env_given.F10_DLW={eg.get('F10_DLW')!r} != {dlw!r}")
if eg.get("F10_OUT") != f8: bad.append(f"env_given.F10_OUT={eg.get('F10_OUT')!r} != {f8!r}")
# (4) ACTUAL ARTEFACT SHAs — hashed at THIS MONTH'S EXPECTED PATH, UNCONDITIONALLY: whatever (or whether) the locator says, the expected file must exist and match
for k in sorted(_WANT):
    rec = shas.get(k)
    if _empty(rec): bad.append(f"input {k} has NO recorded sha256 in the sidecar: its identity is unverifiable"); continue
    if not _digest(rec): bad.append(f"input {k} recorded sha256 {rec!r} is not a 64-hex digest: its identity is unverifiable"); continue
    if not os.path.isfile(_WANT[k]): bad.append(f"input {k} missing on disk at this month's path: {_WANT[k]}"); continue
    cur = sha(_WANT[k])
    if cur != rec: bad.append(f"input {k} changed since refit: {cur[:12]} != {rec[:12]} ({_WANT[k]})")
    else: ran[f"sha:{k}"] = cur
_rp = m.get("pt_sha256")
if _empty(_rp): bad.append("sidecar records NO pt_sha256: the weights identity is unverifiable (this used to be treated as 'nothing to check')")
elif not _digest(_rp): bad.append(f"pt_sha256 {_rp!r} is not a 64-hex digest: the weights identity is unverifiable")
elif not os.path.isfile(_ptw): bad.append(f"weights missing at this month's path: {_ptw}")
else:
    cur = sha(_ptw)
    if cur != _rp: bad.append(f"weights changed since refit: {cur[:12]} != {_rp[:12]} ({_ptw})")
    else: ran["sha:pt"] = cur
# (5) WHICH PROGRAM WROTE IT — the same discipline require_gate applies to gate receipts (self_sha computed at run time from the source this chain invokes)
_rs = m.get("self_sha256")
if not os.path.isfile(src): bad.append(f"refit source missing beside the driver: {src}")
elif not _digest(_rs): bad.append(f"self_sha256 {_rs!r} is not a 64-hex digest: which program wrote the sidecar is unverifiable")
else:
    _ss = sha(src)
    if _ss != _rs: bad.append(f"sidecar was written by a different program: self_sha256 {_rs[:12]} != {os.path.basename(src)} {_ss[:12]}")
    else: ran["self_sha256"] = _ss
if bad: print("; ".join(bad)); sys.exit(3)
# (6) round 4: "verified" is printed ONLY for checks that ran — a check that silently did not run is a refusal, not a pass
_NEED = {f"locator:{k}" for k in _WANT} | {f"sha:{k}" for k in _WANT} | {"locator:pt", "sha:pt", "seed", "self_sha256"}
_notrun = sorted(_NEED - set(ran))
if _notrun: print(f"refusing to report verification: check(s) {_notrun} did not run"); sys.exit(3)
_n = sum(1 for k in ran if k.startswith("sha:") and k != "sha:pt")
print(f"ok seed {seed} fix7, {_n} inputs + weights verified against the bytes on disk, written by {os.path.basename(src)} {ran['self_sha256'][:12]}")
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
