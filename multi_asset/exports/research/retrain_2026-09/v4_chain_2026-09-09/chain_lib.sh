#!/bin/bash
# chain_lib.sh — shared discipline for the v4 chain drivers (review b0a573a1 P1-PIPE, 2026-09-09).
#   · a stage may dispatch only on a FRESH PASS receipt (v4_gate_common.py require <json> name=path ...)
#   · every child is waited on BY PID and its rc collected; ANY non-zero rc aborts the driver (no merge, no DONE)
#   · merges must exit 0 AND print their completion marker
#   · the DONE line is written only on success and carries the rc list; failures write FAIL_<stage> and exit non-zero
# Source it: . chain_lib.sh ; then: require_gate <json> name=path ... ; run_shards <launcher> <T> <SD> ; check_marker <log> <marker>
PY=${PY:-/workspace/venv/bin/python}; R=${R:-/workspace/review_scratch}; L=${L:-$R/v4_commands.txt}
say(){ echo "[$(date -u +%FT%TZ)] $*" >> "$L"; }
die(){ say "FAIL_$1"; echo "FAIL_$1" >&2; exit "${2:-1}"; }
require_gate(){  # require_gate <receipt.json> [name=path ...]
  local out; out=$($PY "$R/v4_gate_common.py" require "$@" 2>&1); local rc=$?
  say "require $1: $out"; [ $rc -eq 0 ] || die "gate_require_$(basename "$1" .json)" 3
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
