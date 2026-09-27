#!/bin/bash
# kf_manifest_ic.sh -- process executor (§10-f) of the step "training done -> manifest in the IC device's format" (fresh2 2026-09-27).
# Waits bound to the training run's identity: the training PGID must stay alive until a line-anchored terminal line appears in
# kingfam.log (STOP / KF_TRAIN_DONE); PGID gone without one => KF_MANIFEST_IC STOP. On KF_TRAIN_DONE: MANIFEST_IC.json in dlarch's
# format (7e2ebafc7): {"arms": {"KN": [{"path","sha256"} x8], "A1": [...]}, "dups": {...}} with every sha re-hashed now and checked
# against MANIFEST_KN_A1.json, then the line "KF_MANIFEST_IC_DONE path sha" in kingfam.log.
set -uo pipefail
K=/workspace/kingfam_2026-09-27; LG=$K/logs/kingfam.log
say() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" | tee -a $LG; }
G=$(python3 -c "import json;print(json.load(open('$K/logs/PGID_train.json'))['pgid'])")
T0=$(date -u +%Y-%m-%dT%H:%M:%SZ)
while :; do
  L=$(grep -E "^\S+ (STOP|KF_TRAIN_DONE)" $LG | awk -v t=$T0 '$1 >= "2026-09-27T02:39"' | tail -1)
  [ -n "$L" ] && break
  ps -o pid= -g $G > /dev/null 2>&1 || { sleep 5; L=$(grep -E "^\S+ (STOP|KF_TRAIN_DONE)" $LG | awk '$1 >= "2026-09-27T02:39"' | tail -1); [ -n "$L" ] && break; say "KF_MANIFEST_IC STOP: training PGID $G gone without a terminal line"; exit 1; }
  sleep 30
done
echo "$L" | grep -q "KF_TRAIN_DONE" || { say "KF_MANIFEST_IC STOP: training ended with [$L]"; exit 1; }
python3 - $K <<'PY' || { say "KF_MANIFEST_IC STOP: manifest conversion failed"; exit 1; }
import sys, json, hashlib, os
K = sys.argv[1]; src = f"{K}/MANIFEST_KN_A1.json"; man = json.load(open(src))
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
out = {"arms": {}, "dups": {}, "source_manifest": {"path": src, "sha256": sha(src)}, "writer": "kf_manifest_ic.sh (fresh2)"}
for arm in ("KN", "A1"):
    out["arms"][arm] = []
    for m in range(8):
        e = man[f"{arm}_m{m}"]; h = sha(e["oof"]); assert h == e["oof_sha256"], (arm, m); out["arms"][arm].append({"path": e["oof"], "sha256": h})
    d = man[f"{arm}_m0_dup"]; h = sha(d["oof"]); assert h == d["oof_sha256"]
    out["dups"][arm] = {"path": d["oof"], "sha256": h, "check": f"{K}/arms/{arm}_m0_dup/DUP_CHECK.json", "note": "determinism only (revision 1), checked by fresh2's driver; not a member"}
p = f"{K}/MANIFEST_IC.json"; json.dump(out, open(p + ".tmp", "w"), indent=1); os.replace(p + ".tmp", p); print(p, sha(p))
PY
say "KF_MANIFEST_IC_DONE $K/MANIFEST_IC.json sha=$(sha256sum $K/MANIFEST_IC.json | cut -c1-64)"
