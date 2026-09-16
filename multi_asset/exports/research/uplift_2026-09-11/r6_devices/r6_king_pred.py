"""R6 EXTEND step 5: king predictions on the NEW anchors, from the PINNED v4 booster. No retraining (PREREG §8.1).

Legitimacy, stated before the numbers:
  * pod_export_bundle_v4.py L48-52 trains slow2026.txt on `tr = YRA < 2026`, i.e. TRAINING CUTOFF = 2025-12-31 23:59Z.
    Every new anchor is 2026-09-01..2026-09-10, so NO new anchor is inside the training window.
  * This is exactly what production does: ~/wide_shadow/shadow_loop_v3.py L147 loads
    `lgb.Booster(model_file=f"{BUNDLE}/slow2026.txt")` and scores each live anchor forward with it (VERIFIED read-only).
  * PARITY GATE X-KING: re-score the EXISTING 2026 anchors with the same booster and compare against
    slow_pred_pinned.npy. If the re-scored values do not reproduce the pinned array, the forward scores are not
    the same object and the extension is void.
Output SLOW_v4_x0910.npy: prefix rows bitwise identical to slow_pred_pinned.npy, new rows scored forward.
"""
import os, json, time, hashlib, sys
import numpy as np
import lightgbm as lgb

ENV_WL = ["R6_FEA", "R6_META", "R6_BOOSTER", "R6_PINNED", "R6_PRED_OUT", "R6_PINS"]
ENV_EFF = {k: os.environ.get(k) for k in ENV_WL}
FEA_P  = os.environ.get("R6_FEA", "/workspace/uplift_2026-09-11/r6/out/wide_fea_v4_x0910.npy")
META_P = os.environ.get("R6_META", "/workspace/uplift_2026-09-11/r6/out/wide_fea_v4_meta_x0910.npz")
BOOST  = os.environ.get("R6_BOOSTER", "/workspace/shadow_bundle_v4/slow2026.txt")
PINNED = os.environ.get("R6_PINNED", "/workspace/shadow_bundle_v4/slow_pred_pinned.npy")
OUTP   = os.environ.get("R6_PRED_OUT", "/workspace/uplift_2026-09-11/r6/out/SLOW_v4_x0910.npy")
PINS_P = os.environ.get("R6_PINS", "/workspace/live_pins.json")
RPT    = "/workspace/uplift_2026-09-11/r6/RECEIPT_king_pred.json"

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
def U(t): return time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t)))

MT = np.load(META_P, allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]
names = [str(n) for n in MT["names"]]
PINS = json.load(open(PINS_P))
keep = [k for k, nm in enumerate(names) if not (nm.startswith("ret5_sum_48") or nm.startswith("ret5_sum_288"))]
assert [names[k] for k in keep] == PINS["keep_names"], "keep_names != live pins (Delta5 assertion, pod_export_bundle_v4 L34)"
FEA = np.load(FEA_P, mmap_mode="r")
P0 = np.load(PINNED)
nA, NW = len(E_ts), 829
assert FEA.shape == (nA, NW, len(names)), (FEA.shape, nA, NW, len(names))
n_old = P0.shape[0]
assert P0.shape[1] == NW
print(f"extended king axis n={nA} {U(E_ts[0])}..{U(E_ts[-1])} | pinned n={n_old} | keep cols {len(keep)}", flush=True)

bst = lgb.Booster(model_file=BOOST)
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
PRED = np.full((nA, NW), np.nan, np.float32)
PRED[:n_old] = P0                                        # prefix VERBATIM
t0 = time.time()
new_idx = list(range(n_old, nA))
scored = 0
for i in new_idx:
    m = members[i]; ok = np.isfinite(y4[i, m])
    if ok.sum() < 50: continue
    X = np.asarray(FEA[i, m[ok]][:, keep], dtype=np.float32)
    PRED[i, m[ok]] = bst.predict(X).astype(np.float32)
    scored += 1
print(f"forward-scored {scored}/{len(new_idx)} new anchors ({time.time()-t0:.0f}s)", flush=True)

# ---- X-KING parity: re-score EXISTING 2026 anchors, compare to the pinned array ----
old26 = [i for i in range(n_old) if yrs[i] == 2026]
chk_idx = old26[-200:] if len(old26) > 200 else old26
maxabs = 0.0; n_cells = 0; n_bitwise = 0; n_finite_pat = 0
for i in chk_idx:
    m = members[i]; ok = np.isfinite(y4[i, m])
    if ok.sum() < 50: continue
    X = np.asarray(FEA[i, m[ok]][:, keep], dtype=np.float32)
    p = bst.predict(X).astype(np.float32)
    q = P0[i, m[ok]]
    fin = np.isfinite(q)
    n_finite_pat += int((np.isfinite(p) == fin).sum()); n_cells += len(p)
    n_bitwise += int((p[fin].view(np.uint32) == q[fin].view(np.uint32)).sum())
    if fin.any(): maxabs = max(maxabs, float(np.abs(p[fin] - q[fin]).max()))
xk = {"anchors_checked": len(chk_idx), "cells": n_cells, "bitwise_equal": n_bitwise,
      "bitwise_equal_rate": round(n_bitwise / max(n_cells, 1), 8), "maxabs": maxabs,
      "finite_pattern_equal_rate": round(n_finite_pat / max(n_cells, 1), 8)}
print("X-KING re-score parity vs slow_pred_pinned:", json.dumps(xk), flush=True)

np.save(OUTP, PRED)
Q = np.load(OUTP)
bw_prefix = bool(np.array_equal(Q[:n_old], P0, equal_nan=True))
rep = {"self_sha256": sha(os.path.abspath(__file__)), "env_effective": ENV_EFF,
       "booster": BOOST, "booster_sha256": sha(BOOST),
       "booster_training_cutoff": "2025-12-31 23:59Z (pod_export_bundle_v4.py L48 `tr = YRA < 2026`)",
       "new_anchors_all_after_cutoff": bool(min(E_ts[n_old:]) > 1767225600),
       "pinned": PINNED, "pinned_sha256": sha(PINNED), "pinned_n": int(n_old),
       "fea": FEA_P, "meta": META_P, "meta_sha256": sha(META_P),
       "out": OUTP, "out_sha256": sha(OUTP), "out_n": int(nA),
       "new_anchors": len(new_idx), "new_anchors_scored": scored,
       "new_first": U(E_ts[n_old]) if nA > n_old else None, "new_last": U(E_ts[-1]),
       "X_KING_rescore_parity": xk, "BW5_prefix_bitwise_equal_readback": bw_prefix,
       "production_equivalence": "~/wide_shadow/shadow_loop_v3.py L147 loads lgb.Booster(slow2026.txt) and scores live anchors forward (READ-ONLY verified)",
       "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
json.dump(rep, open(RPT, "w"), indent=1)
print(f"R6_KING_PRED_DONE prefix_bitwise={bw_prefix} sha={rep['out_sha256'][:16]}", flush=True)
