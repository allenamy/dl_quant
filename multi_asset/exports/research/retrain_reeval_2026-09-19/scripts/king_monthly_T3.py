#!/usr/bin/env python3
"""king_monthly_T3.py — PREREG_retrain_reeval_corrected_pipeline_2026-09-19 (9b403aad) §2 arm T3 "king 月度".
Rule (frozen): the model for month m is trained on anchors whose label ends STRICTLY before the first instant of m:
    label_end(anchor) = E_ts + 4h   (king label y4 = Σ 5m rows (E, E+48], pod_fea_ext_clamp_v2.py L59-60)
    train rows: E_ts[A] + 14400 < month_start(m)          test rows: calendar month of E_ts[A] == m      (20 folds 202501..202608)
"其余同 SLOW_v4 配方": the row construction (members, finite-label filter, per-anchor rank target, keep columns), the LightGBM estimator and its
parameters are copied VERBATIM from pod_export_bundle_v4.py (sha256 42555a37…, the exporter that produced the FP2 SLOW_v4 used by A1) L40-61/L67-68/L75-82,
on the SAME inputs (FP2 root king features + meta). Rows outside 202501..202608 are copied from SLOW_v4 unchanged (2024 fold rows; NaN before 2024).
MODE=check (device validation, run first): the yearly 2025 fold with the exporter's own rule (YRA < 2025) must reproduce SLOW_v4's 2025 rows; the result
(bitwise or not, max|Δ|, rank corr) is recorded. It does not change the arm.
env: KING_FEA KING_META SLOW_BASE LIVE_PINS OUT_DIR MODE=check|months [MONTHS=csv]
"""
import os, sys, json, time, calendar, hashlib
import numpy as np
from scipy.stats import rankdata, spearmanr
T0 = time.time()
def log(*a): print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()
E_ = os.environ
FEA_P, META_P, SLOW_P, PINS_P, OUT = E_["KING_FEA"], E_["KING_META"], E_["SLOW_BASE"], E_["LIVE_PINS"], E_["OUT_DIR"]; MODE = E_.get("MODE", "months")
ALL = [202501 + k for k in range(12)] + [202601 + k for k in range(8)]
MONTHS = [int(x) for x in E_["MONTHS"].split(",")] if E_.get("MONTHS") else ALL
assert all(m in ALL for m in MONTHS) and MODE in ("check", "months")
os.makedirs(OUT, exist_ok=True)
PINS = json.load(open(PINS_P))
# ── verbatim recipe: pod_export_bundle_v4.py L40-61 ──
FEA = np.load(FEA_P)
MT = np.load(META_P, allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; qvk = MT["qvk"]
names = [str(n) for n in MT["names"]]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
nA = len(E_ts); NW = 829
keep = [k for k, nm in enumerate(names) if not (nm.startswith("ret5_sum_48") or nm.startswith("ret5_sum_288"))]
assert [names[k] for k in keep] == PINS["keep_names"], "keep_names 与在役不一致"
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
del rows_X, rows_y, rows_a, FEA
YRA = yrs[A]
import lightgbm as lgb
def fit(sel):   # pod_export_bundle_v4.py L75-76 verbatim estimator
    return lgb.LGBMRegressor(n_estimators=400, learning_rate=0.05, num_leaves=63,
                             subsample=0.8, colsample_bytree=0.8, n_jobs=100, verbose=-1).fit(X[sel], Y[sel])
ym_anchor = np.array([time.gmtime(int(t)).tm_year * 100 + time.gmtime(int(t)).tm_mon for t in E_ts]); YMA = ym_anchor[A]
SLOW = np.load(SLOW_P); assert SLOW.shape == (nA, NW), SLOW.shape
rep = {"device": os.path.basename(__file__), "self_sha256": sha(os.path.abspath(__file__)), "mode": MODE, "lightgbm": lgb.__version__, "numpy": np.__version__,
       "inputs": {"KING_FEA": FEA_P, "KING_FEA_sha256": sha(FEA_P), "KING_META": META_P, "KING_META_sha256": sha(META_P), "SLOW_BASE": SLOW_P, "SLOW_BASE_sha256": sha(SLOW_P), "LIVE_PINS": PINS_P, "LIVE_PINS_sha256": sha(PINS_P)},
       "recipe": "pod_export_bundle_v4.py (42555a37) L40-61 rows, L75-76 estimator verbatim; fold rule = PREREG §2 T3 (label_end = E+4h < month start)",
       "n_rows": int(len(Y)), "n_anchors_with_rows": int(len(np.unique(A))), "folds": {}}
log(f"rows {len(Y)} anchors {len(np.unique(A))} keep {len(keep)} mode {MODE}")
if MODE == "check":
    tr_ = YRA < 2025; te_ = YRA == 2025
    g2 = fit(tr_); pv = g2.predict(X[te_]); a_te = A[te_]
    P = np.full((nA, NW), np.nan, np.float32)
    for a in np.unique(a_te):
        sel = a_te == a; m = members[a]; okm = np.isfinite(y4[a, m]); P[a, m[okm]] = pv[sel]
    rows25 = yrs == 2025; a_ = P[rows25]; b_ = SLOW[rows25]
    fin_eq = bool(np.array_equal(np.isfinite(a_), np.isfinite(b_))); both = np.isfinite(a_) & np.isfinite(b_)
    mx = float(np.max(np.abs(a_[both] - b_[both]))) if both.any() else float("nan")
    rc = [sp(P[i], SLOW[i]) for i in np.nonzero(rows25)[0] if np.isfinite(P[i]).sum() >= 30]
    rep["check_2025_yearly"] = {"rule": "YRA < 2025 (exporter's own yearly rule)", "finite_pattern_equal": fin_eq, "maxabs": mx, "bitwise": bool(fin_eq and mx == 0.0),
                                "rank_corr_mean": float(np.nanmean(rc)), "rank_corr_min": float(np.nanmin(rc)), "n_train_rows": int(tr_.sum()), "n_test_rows": int(te_.sum())}
    log("CHECK", json.dumps(rep["check_2025_yearly"]))
    json.dump(rep, open(f"{OUT}/T3_CHECK.json", "w"), indent=1); log("T3_CHECK_DONE"); sys.exit(0)
PRED = SLOW.copy()
first25 = int(np.searchsorted(E_ts, calendar.timegm((2025, 1, 1, 0, 0, 0))))
PRED[first25:] = np.nan            # every 2025+ row is re-predicted by its monthly fold (no silent carry-over of SLOW_v4 rows)
for ym in MONTHS:
    y, mo = divmod(ym, 100); ms = calendar.timegm((y, mo, 1, 0, 0, 0))
    tr_ = (E_ts[A] + 14400) < ms; te_ = YMA == ym
    tr_anchors = np.unique(A[tr_]); last_tr = int(E_ts[int(tr_anchors.max())])
    assert last_tr + 14400 < ms, (ym, last_tr, ms)                                  # CAUSALITY ASSERT: label end strictly before the month start
    assert not (tr_ & te_).any()
    t1 = time.time(); g = fit(tr_); pv = g.predict(X[te_]); a_te = A[te_]; ics = []
    for a in np.unique(a_te):
        sel = a_te == a; m = members[a]; okm = np.isfinite(y4[a, m]); PRED[a, m[okm]] = pv[sel]
        ics.append(sp(pv[sel], y4[a, m[okm]]))
    fold = {"month": ym, "n_train_rows": int(tr_.sum()), "n_train_anchors": int(len(tr_anchors)), "last_train_anchor": time.strftime("%FT%TZ", time.gmtime(last_tr)),
            "last_train_label_end": time.strftime("%FT%TZ", time.gmtime(last_tr + 14400)), "month_start": time.strftime("%FT%TZ", time.gmtime(ms)), "causality_ok": True,
            "n_test_rows": int(te_.sum()), "n_test_anchors": int(len(np.unique(a_te))), "ic_mean_info": float(np.nanmean(ics)), "fit_s": round(time.time() - t1, 1)}
    rep["folds"][str(ym)] = fold; log("FOLD", json.dumps(fold))
    np.save(f"{OUT}/SLOW_T3_partial.npy", PRED); json.dump(rep, open(f"{OUT}/T3_folds.json", "w"), indent=1)
if MONTHS == ALL:
    ymr = ym_anchor
    for ym in ALL:   # coverage: every row that SLOW_v4 predicted in 2025+ is predicted by exactly the fold of its month
        r = ymr == ym; assert np.array_equal(np.isfinite(PRED[r]), np.isfinite(SLOW[r])), f"finite pattern differs from SLOW_v4 in {ym}"
    assert np.array_equal(PRED[:first25], SLOW[:first25], equal_nan=True)
    np.save(f"{OUT}/SLOW_T3.npy", PRED); rep["out"] = f"{OUT}/SLOW_T3.npy"; rep["out_sha256"] = sha(f"{OUT}/SLOW_T3.npy")
    json.dump(rep, open(f"{OUT}/T3_folds.json", "w"), indent=1); log("T3_DONE", rep["out_sha256"][:16])
