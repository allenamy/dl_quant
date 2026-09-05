"""gate_G4a.py — PREREG §2 G4 items that need no retraining, on the REBUILT king (stage 5) and meta/cache:
 (i)  per-fold CAUSALITY ASSERT: folds YV in 2022..2026 with train = years < YV, test = years == YV (pod_slow_hist_folds.py L27-28):
      max(train E_ts) + 48*300 <= min(test E_ts) and train ∩ test = ∅ ; must be 5/5 True.
 (ii) fold-out leakage: pre-2022 rows all NaN; for every anchor with >=50 finite-y4 members the finite mask of PRED equals the finite
      mask of y4 over its members (the only cells the fold model of that anchor's year writes, L31-34); no finite cell outside members.
 (vi) feature window: 3 features x 100 random anchors recomputed from the cache over rows [E-w, E-1] must equal the stored FEA cell
      bitwise (after the float16 store), and the shifted window [E-w+1, E] must differ in at least one cell => max row used == E-1.
Writes results/G4a.json with pass flags. Exit 0 always (verdict consumed by stage 10)."""
import os, sys, json, time, hashlib
import numpy as np
ROOT = os.environ.get("JR_ROOT", "/workspace/review_scratch/jpline_rebuild")   # JR_ROOT only for the dry-test harness
sys.path.insert(0, f"{ROOT}/src"); from zload import zload
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
def iso(t): return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(t)))
MT = np.load(f"{ROOT}/data/wide_fea_hist_meta_rebuilt.npz", allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; names = [str(n) for n in MT["names"]]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts]); nA = len(E_ts)
PRED = np.load(f"{ROOT}/data/slow_pred_hist_oos_rebuilt.npy", mmap_mode="r")
out = {"self_sha256": sha(os.path.abspath(__file__)), "king": sha(f"{ROOT}/data/slow_pred_hist_oos_rebuilt.npy"), "meta": sha(f"{ROOT}/data/wide_fea_hist_meta_rebuilt.npz")}
# (i)
used = np.array([np.isfinite(y4[i, members[i]]).sum() >= 50 for i in range(nA)])   # anchors that enter X (L19-20)
folds = []; ok_i = True
for YV in (2022, 2023, 2024, 2025, 2026):
    tr = used & (yrs < YV); te = used & (yrs == YV)
    if tr.sum() == 0 or te.sum() == 0:
        ok_i = False; folds.append({"YV": YV, "n_train_anchors": int(tr.sum()), "n_test_anchors": int(te.sum()), "pass": False, "note": "empty train or test set"}); print(f"  (i) fold {YV}: EMPTY train/test set -> FAIL", flush=True); continue
    lhs = int(E_ts[tr].max()) + 48 * 300; rhs = int(E_ts[te].min()); ov = bool(np.any(tr & te))
    ok = (lhs <= rhs) and not ov; ok_i &= ok
    folds.append({"YV": YV, "n_train_anchors": int(tr.sum()), "n_test_anchors": int(te.sum()), "max_train_Ets_plus_label": iso(lhs), "min_test_Ets": iso(rhs), "gap_s": rhs - lhs, "overlap": ov, "pass": bool(ok)})
    print(f"  (i) fold {YV}: train {tr.sum()} anchors ..{iso(int(E_ts[tr].max()))} (+4h label = {iso(lhs)}) <= test first {iso(rhs)} : {lhs <= rhs}; overlap {ov} -> {'PASS' if ok else 'FAIL'}", flush=True)
out["i_causality"] = {"folds": folds, "pass": bool(ok_i)}
# (ii)
pre = yrs < 2022
n_pre_finite = int(np.isfinite(np.asarray(PRED[pre])).sum())
bad_mask = 0; bad_outside = 0; n_checked = 0
for i in range(nA):
    if yrs[i] < 2022: continue
    row = np.asarray(PRED[i]); f = np.isfinite(row); m = members[i]
    inside = np.zeros(len(row), bool); inside[m] = np.isfinite(y4[i, m])
    if used[i]:
        n_checked += 1
        if not np.array_equal(f, inside): bad_mask += 1
    else:
        if f.any(): bad_outside += 1
ok_ii = (n_pre_finite == 0) and bad_mask == 0 and bad_outside == 0
out["ii_foldout"] = {"n_pre2022_anchors": int(pre.sum()), "n_pre2022_finite_cells": n_pre_finite, "n_anchors_checked": n_checked, "n_mask_mismatch": bad_mask, "n_unused_anchors_with_values": bad_outside, "pass": bool(ok_ii)}
print(f"  (ii) pre-2022 finite cells {n_pre_finite}; finite mask == member∧finite(y4) for {n_checked - bad_mask}/{n_checked} used anchors; unused anchors with values {bad_outside} -> {'PASS' if ok_ii else 'FAIL'}", flush=True)
# (vi)
Z = zload(f"{ROOT}/data/dlnative_5m_wide829_f16_hist.npz", allow_pickle=True); CTS = Z["ts"].astype(np.int64); CD = Z["data"]
FEA = np.load(f"{ROOT}/data/wide_fea_hist_rebuilt.npy", mmap_mode="r")
row = {int(t): k for k, t in enumerate(CTS)}
rng = np.random.default_rng(20260905); picks = rng.choice(np.where(used)[0], size=100, replace=False)
tests = [("ret5_sum_48_v", 0, 48, "sum"), ("range_mean_288_v", 1, 288, "mean"), ("vol_2016_v", 0, 2016, "vol")]
def feat(x, kind):   # x: rows of one symbol's channel, float32 -> same recipe as pod_fea_wide_hist.py L16-20, L53-62 (float64 accumulation)
    fin = np.isfinite(x); xz = np.where(fin, x, 0).astype(np.float64); nf = max(int(fin.sum()), 1)
    if kind == "sum": v = xz.sum()
    elif kind == "mean": v = xz.sum() / nf
    else:
        mm = xz.sum() / nf; v = np.sqrt(max((xz ** 2).sum() / nf - mm ** 2, 0.0))
    return np.float16(np.clip(np.nan_to_num(np.float32(v), nan=0), -1e4, 1e4))
res_vi = {}; ok_vi = True
for nm, ch, w, kind in tests:
    col = names.index(nm); eq_true = 0; neq_shift = 0; n = 0
    for i in picks:
        E = row[int(E_ts[i])]; m = members[i]; j = int(rng.choice(m))
        stored = np.float16(FEA[i, j, col])
        v_true = feat(CD[E - w:E, j, ch].astype(np.float32), kind)          # rows [E-w, E-1]
        v_shift = feat(CD[E - w + 1:E + 1, j, ch].astype(np.float32), kind)  # rows [E-w+1, E]  (would include the bar closing at N)
        n += 1; eq_true += int(v_true == stored); neq_shift += int(v_shift != stored)
    res_vi[nm] = {"n": n, "bitwise_equal_window_[E-w,E-1]": eq_true, "differs_window_[E-w+1,E]": neq_shift}
    ok_vi &= (eq_true == n) and (neq_shift >= 1)
    print(f"  (vi) {nm}: window [E-w,E-1] bitwise {eq_true}/{n}; shifted [E-w+1,E] differs in {neq_shift}/{n}", flush=True)
out["vi_feature_window"] = {"features": res_vi, "pass": bool(ok_vi)}
out["G4a_PASS"] = bool(ok_i and ok_ii and ok_vi)
print(f"G4a (i) {'PASS' if ok_i else 'FAIL'} (ii) {'PASS' if ok_ii else 'FAIL'} (vi) {'PASS' if ok_vi else 'FAIL'} => {'PASS' if out['G4a_PASS'] else 'FAIL'}", flush=True)
json.dump(out, open(f"{ROOT}/results/G4a.json", "w"), indent=1); print("wrote results/G4a.json")
