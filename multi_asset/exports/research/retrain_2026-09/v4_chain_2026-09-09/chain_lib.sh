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
PY=${PY:-/workspace/venv/bin/python}; R=${R:-/workspace/review_scratch}; L=${L:-$R/v4_commands.txt}
say(){ echo "[$(date -u +%FT%TZ)] $*" >> "$L"; }
die(){ say "FAIL_$1"; echo "FAIL_$1" >&2; exit "${2:-1}"; }
gate_sha(){  # gate_sha <gate script> — sha256 of the gate source THIS chain trusts, from the file on disk at run time; non-zero rc if unreadable
  local out; out=$($PY "$R/v4_gate_common.py" sha "$1" 2>/dev/null) || return 3; [ -n "$out" ] || return 3; echo "${out%% *}"
}
require_gate(){  # require_gate <receipt.json> gate=<expected> self_sha=<sha of the gate source, mandatory> name=path ...
  local out; out=$($PY "$R/v4_gate_common.py" require "$@" 2>&1); local rc=$?
  say "require $1: $out"; [ $rc -eq 0 ] || die "gate_require_$(basename "$1" .json)" 3
}
pin_deps(){  # pin_deps <name> path... — provenance receipt of every consumed file; any missing file is fatal (exit 3)
  local name=$1; shift; local out="$R/v4_gates/deps_${name}.json"; mkdir -p "$R/v4_gates"
  $PY "$R/v4_gate_common.py" sha "$@" > "$out.txt" 2>&1 || die "deps_${name}_unreadable_file" 3
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
run_shards(){  # run_shards <launcher.sh> <TARGET> <SEED> ; uses SH0..SH3; sets RCS (space-separated) and returns non-zero if any shard failed
  local launcher=$1 T=$2 SD=$3; local pids=() rcs=() k
  for k in 0 1 2 3; do local -n M="SH$k"; bash "$R/$launcher" "$T" "$SD" "$k" "$M" & pids+=($!); done
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
