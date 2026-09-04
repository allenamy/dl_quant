"""pod_king_rolling_monthly.py — PREREG_rolling_king_monthly_2026-09-05 STEP 1 (pod, read-only inputs).
Rolling walk-forward king predictions with the PRODUCTION recipe:
  data preparation = /workspace/pod_export_bundle_v3.py L26-48 verbatim (FEA/meta/keep 78 cols/rows over members with
  finite y4, skip anchors <50, label rr = rankdata(y4[ok])/max(n-1,1)-0.5),
  LGBMRegressor(n_estimators=400, learning_rate=0.05, num_leaves=63, subsample=0.8, colsample_bytree=0.8, verbose=-1)
  with n_jobs=NJOBS (48) and random_state = 20260905 + fold_index (production: n_jobs=100, random_state unset).
Folds (UTC by E_ts): MODE=monthly  -> test = calendar month M in 2024-01..2026-08
                     MODE=quarterly-> test = calendar quarter in 2024Q1..2026Q3 (shape check only)
  train = all rows whose anchor label window ends strictly before the embargo boundary:
          E_ts + 48*300 < (first test E_ts - 60*14400 s)
          [D1 device note, decided before any number was seen: the spec's "E_ts < first_test - 60*14400" makes the last training
           label end EXACTLY at the boundary, so the strict causal ASSERT below fails with gap 0 (first launch 17:18Z, log kept in
           logs/rollm_attempt1_assertfail.log). Kept the ASSERT strict as the guard and dropped one more anchor per fold (effective
           embargo = 60 anchors + one 4h step between label end and first test anchor). Numerically ~330 rows of 1.2-2.7M per fold.]
  ASSERT per fold: max(train E_ts) + 48*300 < min(test E_ts) - 60*14400 (printed).
Output: /workspace/review_scratch/rolling_king/slow_pred_{rollm|rollq}.npy  (float32, shape == meta anchors x 829,
        aligned to meta E_ts, NaN outside test folds -> 2022-23 NaN exactly like slow_pred_pinned.npy) + folds JSON.
"""
import os, sys, json, time, hashlib
import numpy as np
sys.path.insert(0, "/workspace")
from scipy.stats import rankdata, spearmanr
import lightgbm as lgb

OUT = "/workspace/review_scratch/rolling_king"
os.makedirs(OUT, exist_ok=True)
MODE = os.environ.get("MODE", "monthly"); assert MODE in ("monthly", "quarterly"), MODE
NJOBS = int(os.environ.get("NJOBS", "48"))
EMB = 60; EMB_S = EMB * 14400; LABEL_S = 48 * 300
SEED0 = 20260905
TAG = {"monthly": "rollm", "quarterly": "rollq"}[MODE]
_CFG = {"MODE": MODE, "TAG": TAG, "NJOBS": NJOBS, "EMB_anchors": EMB, "EMB_s": EMB_S, "LABEL_s": LABEL_S, "SEED0": SEED0,
        "train_rule": "E_ts + 48*300 < first_test_E_ts - 60*14400 (D1: one 4h step stricter than 'E_ts < first_test - 60*14400' so the strict causal ASSERT holds)",
        "lightgbm": lgb.__version__, "numpy": np.__version__, "python": sys.version.split()[0],
        "self_sha256": hashlib.sha256(open(__file__, "rb").read()).hexdigest(),
        "FEA": "/workspace/data/wide_fea_v2ext.npy", "META": "/workspace/data/wide_fea_v2ext_meta.npz",
        "lgbm_params": {"n_estimators": 400, "learning_rate": 0.05, "num_leaves": 63, "subsample": 0.8, "colsample_bytree": 0.8, "verbose": -1}}
print("CONFIG " + json.dumps(_CFG), flush=True)
t00 = time.time()

# ── production data preparation: /workspace/pod_export_bundle_v3.py L22, L26-47 verbatim ──
PINS = json.load(open("/workspace/live_pins.json"))          # Δ4/Δ5
FEA = np.load("/workspace/data/wide_fea_v2ext.npy")
MT = np.load("/workspace/data/wide_fea_v2ext_meta.npz", allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; qvk = MT["qvk"]
names = [str(n) for n in MT["names"]]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
nA = len(E_ts); NW = 829
keep = [k for k, nm in enumerate(names) if not (nm.startswith("ret5_sum_48") or nm.startswith("ret5_sum_288"))]
assert [names[k] for k in keep] == PINS["keep_names"], "keep_names 与在役不一致"  # Δ5
def sp(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 30: return np.nan
    r = spearmanr(a[ok], b[ok]); return r.correlation if hasattr(r, "correlation") else r[0]
rows_X, rows_y, rows_a = [], [], []
for i in range(nA):
    m = members[i]
    yv = y4[i, m]; ok = np.isfinite(yv)
    if ok.sum() < 50: continue
    rr = rankdata(yv[ok]) / max(ok.sum() - 1, 1) - 0.5
    rows_X.append(FEA[i, m[ok]][:, keep].astype(np.float32))
    rows_y.append(rr.astype(np.float32)); rows_a.append(np.full(ok.sum(), i, np.int32))
X = np.concatenate(rows_X); Y = np.concatenate(rows_y); A = np.concatenate(rows_a)
YRA = yrs[A]
# ── end verbatim block ──
del rows_X, rows_y, rows_a, FEA
A_ts = E_ts[A]
print(f"PREP X {X.shape} {X.dtype} Y {Y.shape} rows_anchors {len(np.unique(A))}/{nA} keep {len(keep)} "
      f"E_ts[0] {time.strftime('%Y-%m-%d %H:%M', time.gmtime(int(E_ts[0])))} E_ts[-1] {time.strftime('%Y-%m-%d %H:%M', time.gmtime(int(E_ts[-1])))} "
      f"prep_s {time.time()-t00:.1f}", flush=True)

gm = [time.gmtime(int(t)) for t in E_ts]
if MODE == "monthly":
    keys = np.array([g.tm_year * 100 + g.tm_mon for g in gm])
    fold_keys = [y * 100 + m for y in (2024, 2025, 2026) for m in range(1, 13) if (y, m) <= (2026, 8)]
else:
    keys = np.array([g.tm_year * 10 + (g.tm_mon - 1) // 3 + 1 for g in gm])
    fold_keys = [y * 10 + q for y in (2024, 2025, 2026) for q in range(1, 5) if (y, q) <= (2026, 3)]
keysA = keys[A]
PRED = np.full((nA, NW), np.nan, np.float32)
folds = []
for fi, fk in enumerate(fold_keys):
    te_anchor = np.where(keys == fk)[0]
    assert len(te_anchor) > 0, f"empty fold {fk}"
    t_first = int(E_ts[te_anchor].min()); t_last = int(E_ts[te_anchor].max())
    cut = t_first - EMB_S
    tr = (A_ts + LABEL_S) < cut     # D1: label window end strictly before the embargo boundary (see docstring)
    te = keysA == fk
    tr_max = int(A_ts[tr].max()); tr_min = int(A_ts[tr].min())
    lhs = tr_max + LABEL_S; rhs = t_first - EMB_S
    ok_assert = lhs < rhs
    print(f"ASSERT fold {fi} key {fk}: max(train E_ts)+48*300 = {lhs} ({time.strftime('%Y-%m-%d %H:%M', time.gmtime(lhs))}) "
          f"< min(test E_ts)-60*14400 = {rhs} ({time.strftime('%Y-%m-%d %H:%M', time.gmtime(rhs))}) -> {ok_assert} "
          f"gap {rhs - lhs}s = {(rhs - lhs) / 14400:.2f} anchors; train_span {time.strftime('%Y-%m-%d %H:%M', time.gmtime(tr_min))}..{time.strftime('%Y-%m-%d %H:%M', time.gmtime(tr_max))} "
          f"test_span {time.strftime('%Y-%m-%d %H:%M', time.gmtime(t_first))}..{time.strftime('%Y-%m-%d %H:%M', time.gmtime(t_last))}", flush=True)
    assert ok_assert, f"CAUSALITY ASSERT FAILED fold {fi} {fk}: {lhs} >= {rhs}"
    assert not np.any(tr & te), "train/test row overlap"
    seed = SEED0 + fi
    t0 = time.time()
    gbm = lgb.LGBMRegressor(n_estimators=400, learning_rate=0.05, num_leaves=63,
                            subsample=0.8, colsample_bytree=0.8, n_jobs=NJOBS, verbose=-1, random_state=seed).fit(X[tr], Y[tr])
    fit_s = time.time() - t0
    pv = gbm.predict(X[te]); a_te = A[te]
    ics = []
    for a in np.unique(a_te):
        sel = a_te == a; m = members[a]; okm = np.isfinite(y4[a, m])
        PRED[a, m[okm]] = pv[sel]
        ics.append(sp(pv[sel], y4[a, m[okm]]))
    rec = {"fold": fi, "key": int(fk), "seed": seed, "train_rows": int(tr.sum()), "train_anchors": int(len(np.unique(A[tr]))),
           "test_anchors_in_month": int(len(te_anchor)), "test_anchors_with_rows": int(len(np.unique(a_te))), "test_rows": int(te.sum()),
           "fit_s": round(fit_s, 1), "rankIC_raw_y4": round(float(np.nanmean(ics)), 5), "assert_lhs": lhs, "assert_rhs": rhs,
           "train_first": tr_min, "train_last": tr_max, "test_first": t_first, "test_last": t_last,
           "booster_sha256": hashlib.sha256(gbm.booster_.model_to_string().encode()).hexdigest()[:16]}
    folds.append(rec)
    print(f"FOLD {fi} key {fk} seed {seed} train_rows {rec['train_rows']} train_anchors {rec['train_anchors']} "
          f"test_anchors {rec['test_anchors_with_rows']}/{rec['test_anchors_in_month']} test_rows {rec['test_rows']} "
          f"fit_s {fit_s:.1f} rankIC {rec['rankIC_raw_y4']:+.4f} booster {rec['booster_sha256']} elapsed {time.time()-t00:.0f}s", flush=True)

path = f"{OUT}/slow_pred_{TAG}.npy"
np.save(path, PRED.astype(np.float32))
sha = hashlib.sha256(open(path, "rb").read()).hexdigest()
fin = np.isfinite(PRED)
fin_anchor = fin.any(1)
first_fin = int(np.where(fin_anchor)[0][0]); last_fin = int(np.where(fin_anchor)[0][-1])
pin = np.load("/workspace/shadow_bundle_v3/slow_pred_pinned.npy")
mask_equal = bool(np.array_equal(np.isfinite(pin), fin))
print(f"SAVED {path} shape {PRED.shape} dtype {PRED.dtype} sha256 {sha} finite_anchors {int(fin_anchor.sum())} "
      f"first_finite {time.strftime('%Y-%m-%d %H:%M', time.gmtime(int(E_ts[first_fin])))} last_finite {time.strftime('%Y-%m-%d %H:%M', time.gmtime(int(E_ts[last_fin])))} "
      f"pre2024_all_nan {bool(not fin[yrs < 2024].any())} finite_mask_equal_pinned {mask_equal}", flush=True)
json.dump({"config": _CFG, "folds": folds, "output": path, "sha256": sha, "finite_mask_equal_pinned": mask_equal},
          open(f"{OUT}/folds_{TAG}.json", "w"), indent=1)
print(f"DONE {MODE} {time.time()-t00:.0f}s", flush=True)
