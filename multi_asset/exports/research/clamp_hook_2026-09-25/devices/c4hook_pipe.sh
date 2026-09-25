#!/bin/bash
# One READ-ONLY hooked engine cell (baseline NC s42X, seed 0 of 32, full X axis) under the team run gate; dlarch's book-layer cells first
# (this cell starts only when at most ONE other engine group runs, i.e. it never takes the last slot). Outputs under /dev/shm/c4hook_2026-09-25.
set -u
NC=/dev/shm/news2_2026-09-23; ME=/dev/shm/c4hook_2026-09-25; DEV=$ME/devices; FA=/dev/shm/fanom_2026-09-24; GATE=/dev/shm/fresh_2026-09-23/devices/memgate.sh
TAG="NEWS2_s42X|scaled|rule|raw|UAFE"; mkdir -p $ME/logs $ME/hook $ME/cfg
/workspace/venv/bin/python - "$NC" "$ME" <<'PY'
import json, hashlib, sys, copy
nc, me = sys.argv[1:3]
def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda: f.read(1<<22), b""): h.update(b)
    return h.hexdigest()
cfgp = f"{nc}/configs/RUN_CONFIG_NEWS2_s42X_2026-09-23.json"; c = json.load(open(cfgp))
want = "NEWS2_s42X|scaled|rule|raw|UAFE"; runs = [r for r in c["runs"] if r["tag"] == want]; assert len(runs) == 1
c["runs"] = [copy.deepcopy(runs[0])]; c["paths"] = dict(c["paths"]); c["paths"]["pod_root"] = me
c["_diagnostic_note"] = {"purpose": "C-4 read-only clamp hook cell (lead approval 2026-09-25); zero-impact control vs SER_EXT_NEWS2_s42X",
                         "derived_from": cfgp, "derived_from_sha256": sha(cfgp), "changed": ["paths.pod_root -> " + me],
                         "deliberately_unchanged": ["runs[0].arm", "runs[0].tag", "runs[0].targets"]}
json.dump(c, open(f"{me}/cfg/RUN_CONFIG.json", "w"), indent=1); print("DERIVED", want, "pod_root ->", me)
PY
while true; do
  OTHERS=$(ps -eo pgid=,args= | grep -E "bt_launch.py" | grep -v grep | grep -v "$ME" | awk '{print $1}' | sort -u | wc -l)
  G=$(bash $GATE 2>&1); GR=$?
  echo "$(date -u +%FT%TZ) others=$OTHERS memgate_rc=$GR $(echo "$G" | tail -1)" >> $ME/logs/gate.log
  if [ "$GR" -eq 0 ] && [ "$OTHERS" -le 1 ]; then break; fi
  sleep 60
done
env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B /dev/shm/fresh_2026-09-23/devices/fa_launch_guard.py PATH,HOME,LC_CTYPE $ME/cfg/RUN_CONFIG.json >> $ME/logs/guard.log 2>&1; echo "guard rc=$?" >> $ME/logs/gate.log
cd $NC/engine
env -i PATH=/usr/bin:/bin HOME=/root nice -n 12 /workspace/venv/bin/python -B $DEV/hook_prelude.py $ME/hook $NC/engine/bt_launch.py PATH,HOME,LC_CTYPE \
  $ME/cfg/RUN_CONFIG.json --smoke 2022-06-30T00:00:00Z 9252 0 "$TAG" c4hook > $ME/logs/engine.log 2>&1
echo "engine rc=$? $(date -u +%FT%TZ)" >> $ME/logs/gate.log
CELL=$ME/runs_smoke/c4hook/NEWS2_s42X_scaled_rule_raw_UAFE
env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B $DEV/c4hook_read.py $CELL $ME/hook $FA/receipts/SER_EXT_NEWS2_s42X.npz $ME/C4HOOK_READ.json > $ME/logs/read.log 2>&1
echo "read rc=$? $(date -u +%FT%TZ)" >> $ME/logs/gate.log
