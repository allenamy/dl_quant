#!/bin/bash
# P4 item 1 -- cost of GUARANTEED determinism, measured SOLO (no GPU contention) so the times compare.
# S1 = in-service regime (nothing changed)        -- timing reference
# S3, S4 = torch.use_deterministic_algorithms(True) + cudnn.deterministic + TF32 off
#          + CUBLAS_WORKSPACE_CONFIG=:4096:8      -- S3 vs S4 bitwise = the guarantee actually holds
# EPOCHS=1 (a mechanism probe, not a book-layer recipe): divergence, if any, starts at the first optimiser
# step, and per-epoch seconds is the cost metric.  V2=1 is NOT set here on purpose: these three runs are
# compared only with each other, and the V2=0 chain is the cheaper one to run three times.
set -u
R=/workspace/uplift_2026-09-11/r4_nondet
cd $R
while ! grep -q CHAIN_P4_DONE logs/chain.log 2>/dev/null; do sleep 30; done
echo "=== PROBE2 start $(date -u +%FT%TZ)" >> logs/probe_drive.log
for J in "S1 off" "S3 full" "S4 full"; do
  set -- $J
  T0=$(date +%s)
  ./train_probe.sh $1 $2 1
  echo "$1 mode=$2 wall=$(( $(date +%s) - T0 ))s $(date -u +%FT%TZ)" >> logs/probe_drive.log
done
/workspace/venv/bin/python - >> logs/probe_drive.log 2>&1 <<'PYEOF'
import hashlib, os, json, re
R = "/workspace/uplift_2026-09-11/r4_nondet"
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
out = {}
for L in ("S1", "S3", "S4"):
    p = "%s/f8_%s/preds/f10_V2MAIN_s42.npy" % (R, L)
    lg = "%s/logs/probe_%s.log" % (R, L)
    eps = [float(x) for x in re.findall(r"\((\d+)s\)", open(lg).read())] if os.path.exists(lg) else []
    env = re.findall(r"DET_ENV (\{.*\})", open(lg).read())
    out[L] = {"preds_sha256": sha(p) if os.path.exists(p) else None,
              "epoch_seconds": eps, "epoch_sec_total": sum(eps), "det_env": env[0] if env else None}
out["S3_eq_S4_bitwise"] = (out["S3"]["preds_sha256"] == out["S4"]["preds_sha256"]) if out["S3"]["preds_sha256"] else None
out["S1_eq_S3"] = (out["S1"]["preds_sha256"] == out["S3"]["preds_sha256"]) if out["S3"]["preds_sha256"] else None
if out["S1"]["epoch_sec_total"] and out["S3"]["epoch_sec_total"]:
    out["determinism_time_cost_ratio_S3_over_S1"] = round(out["S3"]["epoch_sec_total"] / out["S1"]["epoch_sec_total"], 4)
json.dump(out, open(R + "/receipts/RESULT_P4_determinism_cost.json", "w"), indent=1)
print(json.dumps(out, indent=1))
PYEOF
echo "PROBE2_DONE $(date -u +%FT%TZ)" >> logs/probe_drive.log
