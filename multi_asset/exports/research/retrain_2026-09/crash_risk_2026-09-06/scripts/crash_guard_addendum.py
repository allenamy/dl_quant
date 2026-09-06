"""crash_guard_addendum.py — team-lead question on the shuffle-future guard (RESULT_crash_risk_long_end §4): is the residual null AUC anchor-level base-rate
prediction by the cohort-level F6 columns? Controls for T1, seed 42, per fold (same folds/embargo/LGBM as crash_model.py):
  pooled AUC          : AUC over all test rows (mixes between-anchor and within-anchor discrimination)
  within-anchor AUC   : AUC after replacing p̂ by its rank within the anchor's cohort (rankdata/(n−1)) — removes anchor-level differences
  anchor-mean AUC     : AUC using only the anchor-mean of p̂ for every row (pure between-anchor component)
for three label conditions: TRUE labels (saved preds of crash_model.py), WITHIN-anchor shuffle (labels permuted inside each training anchor, retrain),
GLOBAL shuffle (labels permuted across all training rows, retrain). Also the within-anchor top-10% lift. Output results/guard_addendum.json."""
import os, json, time, calendar, hashlib
import numpy as np
from scipy.stats import rankdata
import lightgbm as lgb
ROOT = "/workspace/review_scratch/crash_risk"; SELF = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()
def T(s): return int(calendar.timegm(time.strptime(s, "%Y-%m-%d")))
CUT = T("2026-08-10") + 20 * 3600; FOLDS = [2024, 2025, 2026]
F = np.load(f"{ROOT}/data/features.npz", allow_pickle=True); PI = F["PI"]; X = np.asarray(F["X"], np.float32)
P0 = np.load(f"{ROOT}/data/phase0.npz", allow_pickle=True); E_ts = P0["E_ts"].astype(np.int64); T2 = P0["T2"]; T1 = P0["T1"]; PJ = F["PJ"]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts]); ET = E_ts[PI]; YR = yrs[PI]; ok2 = np.isfinite(T2[PI, PJ]); y1 = T1[PI, PJ].astype(int)
LGB = dict(n_estimators=400, learning_rate=0.05, num_leaves=63, subsample=0.8, subsample_freq=1, colsample_bytree=0.8, n_jobs=12, verbose=-1)
def auc(s, y):
    s = np.asarray(s, float); f = np.isfinite(s); s, y = s[f], np.asarray(y)[f]; npos = int(y.sum()); nneg = len(y) - npos
    if npos == 0 or nneg == 0: return float("nan")
    r = rankdata(s); return float((r[y == 1].sum() - npos * (npos + 1) / 2) / (npos * nneg))
def groups(rows):
    pi = PI[rows]; order = np.argsort(pi, kind="stable"); starts = np.searchsorted(pi[order], np.unique(pi)); ends = np.append(starts[1:], len(rows)); return [order[a:b] for a, b in zip(starts, ends)]
def within_rank(p, rows):
    r = np.full(len(rows), np.nan); mu = np.full(len(rows), np.nan)
    for idx in groups(rows):
        v = p[idx]; f = np.isfinite(v)
        if f.sum() > 1: r[idx[f]] = rankdata(v[f]) / (f.sum() - 1)
        mu[idx] = np.nanmean(v) if f.any() else np.nan
    return r, mu
def top10(p, rows):
    top = np.zeros(len(rows), bool)
    for idx in groups(rows):
        v = p[idx]; f = np.isfinite(v)
        if f.sum() == 0: continue
        k = int(np.ceil(0.10 * f.sum())); top[idx[f][np.argsort(-v[f])[:k]]] = True
    return top
def evaluate(p, rows, y):
    r, mu = within_rank(p, rows); top = top10(p, rows); base = y.mean()
    return {"auc_pooled": round(auc(p, y), 4), "auc_within_anchor_rank": round(auc(r, y), 4), "auc_anchor_mean_only": round(auc(mu, y), 4), "lift_top10_within_anchor": round(float(y[top].mean() / base), 3) if base > 0 else None}
pred_true = np.load(f"{ROOT}/data/preds_T1_s42.npz")["pred"]; rng = np.random.default_rng(20260905); res = {"self_sha256": SELF, "folds": {}}
for YV in FOLDS:
    te = (YR == YV) & ok2 & (ET <= CUT if YV == 2026 else True); first = ET[te].min(); tr = (YR < YV) & ok2 & (ET + 14400 <= first); rows = np.where(te)[0]; yt = y1[te]
    out = {"n_test": int(te.sum()), "test_events": int(yt.sum()), "TRUE": evaluate(pred_true[rows], rows, yt)}
    ys = y1.copy()
    for idx in groups(np.where(tr)[0]): ys[np.where(tr)[0][idx]] = ys[np.where(tr)[0][idx]][rng.permutation(len(idx))]
    p = lgb.LGBMClassifier(objective="binary", random_state=42, **LGB).fit(X[tr], ys[tr]).predict_proba(X[te])[:, 1]; out["SHUFFLE_within_anchor"] = evaluate(p, rows, yt)
    yg = y1.copy(); trr = np.where(tr)[0]; yg[trr] = yg[trr][rng.permutation(len(trr))]
    p = lgb.LGBMClassifier(objective="binary", random_state=42, **LGB).fit(X[tr], yg[tr]).predict_proba(X[te])[:, 1]; out["SHUFFLE_global"] = evaluate(p, rows, yt)
    res["folds"][str(YV)] = out; print(f"[{YV}] " + json.dumps(out), flush=True)
json.dump(res, open(f"{ROOT}/results/guard_addendum.json", "w"), indent=1); print("GUARD_ADDENDUM_DONE", flush=True)
