#!/bin/bash
# replay_check.sh — dl_monthly_wf RNG-replay receipt: after the restarted E60 process ends (so at most two of my trainings run at once), re-fit the
# finished fold 2025-01 (E60) in a FRESH process into replay_check/ and compare with the original fold artifacts (written 07:27Z before the quota incident):
# per-fold seeding (torch & numpy SEED+YM) ⇒ the re-run must reproduce the original scores/weights up to GPU kernel nondeterminism (reported as max|Δ|).
R=/workspace/review_scratch/dl_monthly_wf; PY=/workspace/venv/bin/python; cd $R || exit 2
while ! grep -q "END\[E60-restart\]" logs/commands.txt; do sleep 30; done
mkdir -p replay_check
CMD="env ARM=V2MAIN V2=1 SEED=42 F10_DLW=/workspace/dlw_ext F10_OUT=/workspace/f8_ext MWF_OUT=$R/replay_check EMBARGO=60 MONTHS=202501 $PY $R/pod_f10_train_monthly.py"
T0=$(date +%s); echo "CMD[replay-check E60 202501] $(date -u +%FT%TZ): $CMD" >> logs/commands.txt
$CMD > logs/replay_check_mE60_202501.log 2>&1; rc=$?
echo "END[replay-check] rc=$rc $(date -u +%FT%TZ) wall $(( $(date +%s) - T0 )) s" >> logs/commands.txt
$PY - <<'EOF' > logs/replay_check_compare.log 2>&1
import numpy as np, torch, json, hashlib
R = "/workspace/review_scratch/dl_monthly_wf"
a = np.load(f"{R}/preds_fold/mE60_202501.npz"); b = np.load(f"{R}/replay_check/preds_fold/mE60_202501.npz")
Pa, Pb = a["P"], b["P"]; ok = np.isfinite(Pa) & np.isfinite(Pb)
print("first_te equal", int(a["first_te"]) == int(b["first_te"]), "finite masks equal", bool(np.array_equal(np.isfinite(Pa), np.isfinite(Pb))))
print("scores: bitwise equal", bool(np.array_equal(Pa, Pb, equal_nan=True)), "max|Δ|", float(np.max(np.abs(Pa[ok] - Pb[ok]))), "share exactly equal", float((Pa[ok] == Pb[ok]).mean()), "n cells", int(ok.sum()))
sa = torch.load(f"{R}/models/mE60_202501.pt", map_location="cpu"); sb = torch.load(f"{R}/replay_check/models/mE60_202501.pt", map_location="cpu")
print("weights: bitwise equal", all(torch.equal(sa[k], sb[k]) for k in sa), "max|Δ|", max(float((sa[k] - sb[k]).abs().max()) for k in sa))
ca = json.load(open(f"{R}/models/mE60_202501_config.json")); cb = json.load(open(f"{R}/replay_check/models/mE60_202501_config.json"))
print("config: self_sha equal", ca["self_sha256"] == cb["self_sha256"], "best_epoch", ca["best_epoch"], cb["best_epoch"], "best_va", ca["best_va"], cb["best_va"], "va_curve equal", ca["va_curve"] == cb["va_curve"], "seed_fold", ca["seed_fold"], cb["seed_fold"])
print("file sha256 original/replay npz:", hashlib.sha256(open(f"{R}/preds_fold/mE60_202501.npz","rb").read()).hexdigest()[:16], hashlib.sha256(open(f"{R}/replay_check/preds_fold/mE60_202501.npz","rb").read()).hexdigest()[:16])
print("REPLAY_CHECK_DONE")
EOF
echo "REPLAY_CHECK $(date -u +%FT%TZ): $(grep -E 'scores:|weights:' logs/replay_check_compare.log | tr '\n' ' ')" >> logs/commands.txt
