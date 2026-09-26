"""mr_shuffle_king.py — red control of DECISION_RULE_king_monthly_retrain §0.4: King SCORES shuffled across names within each
anchor (finite cells only, fixed seed), everything else identical to the source OOF. Expected: book worse than A0 in both segments.
usage: python mr_shuffle_king.py <src KING_OOF.npz> <out dir>"""
import os, sys, json, hashlib, time
import numpy as np
SEED = 20260926


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=False)
z = np.load(src); P = z["P"].copy(); rng = np.random.default_rng(SEED); moved = 0
for i in range(P.shape[0]):
    f = np.flatnonzero(np.isfinite(P[i]))
    if len(f) > 1:
        perm = rng.permutation(len(f)); P[i, f] = P[i, f[perm]]; moved += int((perm != np.arange(len(f))).sum())
p = os.path.join(out, "KING_OOF.npz")
np.savez(p, P=P, E_ts=z["E_ts"], symbols=z["symbols"], model_sha256=z["model_sha256"])
same_finite = bool(np.array_equal(np.isfinite(P), np.isfinite(z["P"])))
rec = {"status": "RED_CONTROL_SHUFFLED_KING_SCORES", "source": src, "source_sha256": sha(src), "seed": SEED, "cells_moved": moved,
       "finite_pattern_identical": same_finite, "predictions_sha256": sha(p), "self_sha256": sha(os.path.abspath(__file__)),
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
assert same_finite and moved > 0
json.dump(rec, open(os.path.join(out, "TRAIN_RECEIPT.json"), "w"), indent=1)
print("MR_SHUFFLE_DONE", json.dumps(rec)[:300], flush=True)
