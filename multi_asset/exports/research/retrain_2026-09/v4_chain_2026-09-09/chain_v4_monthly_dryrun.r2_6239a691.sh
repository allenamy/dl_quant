#!/bin/bash
# chain_v4_monthly_dryrun.sh — NEGATIVE CONTROL of the monthly driver (RUNBOOK_2026-10 §0★ 修订 2 (c)): run chain_v4_monthly.sh against an EMPTY
# month root and prove it stops at the FIRST gate (preflight) with rc≠0 and that nothing was launched (no producer, no shard, no training).
# usage: bash chain_v4_monthly_dryrun.sh <source month env or template> [scratch parent dir]
#   · a fresh scratch dir <parent>/v4_dryrun_XXXXXX is created; <scratch>/root is the EMPTY month root;
#   · a derived env <scratch>/v4_month_dryrun.env is written: labels/lists copied from the source (V4_MONTH, MONTHS_ALL, SEEDS, MWF_ROOT,
#     BUNDLE_GENERATION, EXPORT_ARM, GATE_STEP1/2), PY = the interpreter running this script (or $PY), EVERY other key = a path UNDER the empty root
#     (so no real input is reachable, whatever the source env says);
#   · the driver runs with V4_DRYRUN=1 (belt and braces: even if a gate were passed, every later stage dies before launching);
#   · receipt <scratch>/dryrun_receipt.json: rc, the first FAIL_ line, training_launched (CMD[ lines under the root: must be 0), GPU state if
#     nvidia-smi exists; PASS iff rc == 3 AND a preflight receipt with PASS=false and named failures exists AND stopped_at starts with FAIL_preflight
#     AND training_launched == 0 (a crashed preflight, rc 1 and no receipt, is NOT a passed control). Exit 0 iff PASS (the CONTROL passed,
#     i.e. the driver refused), else 1.
set -o pipefail
D=$(cd "$(dirname "$0")" && pwd -P); SRC=$1; PARENT=${2:-${TMPDIR:-/tmp}}
[ -n "$SRC" ] && [ -f "$SRC" ] || { echo "usage: chain_v4_monthly_dryrun.sh <month env> [scratch parent]" >&2; exit 2; }
PYX=${PY:-$(command -v python3)}; [ -x "$PYX" ] || { echo "no python interpreter (set PY)" >&2; exit 2; }
ROOT=$(mktemp -d "$PARENT/v4_dryrun_XXXXXX") || exit 2; mkdir -p "$ROOT/root" || exit 2
# derive the dryrun env in a subshell (sourcing the source env must not leak into this shell)
( set -a; . "$SRC"; set +a; L=/dev/null; R=$ROOT/root; . "$D/chain_lib.sh"
  "$PYX" - "$ROOT" "$V4_MONTH_KEYS" "$PYX" > "$ROOT/v4_month_dryrun.env" <<'PYEOF'
import os, sys
root, keys, py = sys.argv[1], sys.argv[2].split(), sys.argv[3]
COPY = {"V4_MONTH", "MONTHS_ALL", "SEEDS", "MWF_ROOT", "BUNDLE_GENERATION", "EXPORT_ARM", "GATE_STEP1", "GATE_STEP2"}
print(f"# derived by chain_v4_monthly_dryrun.sh: every path under the EMPTY root {root}/root; labels copied from the source env")
for k in keys:
    v = os.environ.get(k, "")
    if k == "PY": v = py
    elif k == "R": v = f"{root}/root"
    elif k not in COPY: v = f"{root}/root/{os.path.basename(v.rstrip('/')) or k.lower()}"
    print(f"{k}={v}")
PYEOF
) || { echo "dryrun env derivation failed" >&2; exit 2; }
T0=$(date -u +%FT%TZ)
V4_DRYRUN=1 V4_STAGES=all PY=$PYX bash "$D/chain_v4_monthly.sh" "$ROOT/v4_month_dryrun.env" > "$ROOT/driver.out" 2>&1; rc=$?
"$PYX" - "$ROOT" "$rc" "$T0" "$D" "$SRC" <<'PYEOF'; ok=$?
import glob, hashlib, json, os, shutil, subprocess, sys, time
root, rc, t0, D, src = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5]
def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()
cmds = f"{root}/root/v4_commands.txt"; lines = open(cmds).read().splitlines() if os.path.exists(cmds) else []
fails = [l for l in lines if "FAIL_" in l]; stopped = fails[0].split("] ", 1)[-1] if fails else None
launched = 0
for p in glob.glob(f"{root}/root/**/commands.txt", recursive=True): launched += sum(1 for l in open(p) if l.startswith("CMD[") or l.startswith("PID["))
launched += sum(1 for l in lines if "F10 chain" in l and "start" in l)
gpu = None
if shutil.which("nvidia-smi"):
    r = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu,memory.used", "--format=csv,noheader"], capture_output=True, text=True); gpu = (r.stdout or r.stderr).strip()
entries = sorted(os.listdir(f"{root}/root"))
pf = f"{root}/root/v4_gates/preflight.json"; pfr = json.load(open(pf)) if os.path.exists(pf) else None
# PASS needs the HONEST refusal: rc 3 (preflight verdict FAIL), a preflight receipt that says PASS=false with named failures (a crashed preflight writes no
# receipt and exits 1 — that is not a passed control), the first FAIL_ line at preflight, and nothing launched
PASS = (rc == 3) and bool(stopped) and stopped.startswith("FAIL_preflight") and launched == 0 and pfr is not None and pfr.get("PASS") is False and bool(pfr.get("fails"))
rec = {"control": "chain_v4_monthly_dryrun (NEGATIVE: empty month root must stop at preflight, launch nothing)", "PASS": PASS, "driver_rc": rc, "stopped_at": stopped,
       "fail_lines": fails, "training_launched": launched, "gpu": gpu, "root_entries_after": entries, "preflight_fails": (pfr or {}).get("fails"), "preflight_PASS": (pfr or {}).get("PASS"),
       "driver_sha256": sha(f"{D}/chain_v4_monthly.sh"), "chain_lib_sha256": sha(f"{D}/chain_lib.sh"), "source_env": src, "source_env_sha256": sha(src), "dryrun_env_sha256": sha(f"{root}/v4_month_dryrun.env"),
       "driver_out_tail": open(f"{root}/driver.out").read()[-1500:], "started_utc": t0, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "scratch": root}
json.dump(rec, open(f"{root}/dryrun_receipt.json", "w"), indent=1)
print(f"DRYRUN_{'PASS' if PASS else 'FAIL'} driver_rc={rc} stopped_at={stopped} training_launched={launched} gpu={gpu} receipt={root}/dryrun_receipt.json")
sys.exit(0 if PASS else 1)
PYEOF
exit $ok
