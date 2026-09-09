"""PREREG_caliber_program §2 — king window-clamp ablation. Training path copied from pod_export_bundle_v3.py L28-L96 (same as
king_clip_ablation.py, gate-checked there). Arms: OLD (deployed features) / CLAMP (E-0909-A clamped features, same meta) /
DROP138 (deployed features, the 138 wrap-affected anchors removed from TRAINING rows). Seeds: default (gate C2) + 42 + 2027."""
import os, sys, json, time, hashlib
import numpy as np
from scipy.stats import rankdata, spearmanr
import lightgbm as lgb
OUT = "/workspace/review_scratch/king_clamp_ablation"; os.makedirs(OUT, exist_ok=True)
PINS = json.load(open("/workspace/live_pins.json")); BASE = json.load(open("/workspace/slow_scorer_v3base.json"))
FEAS = {"OLD": "/workspace/data/wide_fea_v2ext.npy", "CLAMP": "/workspace/data/wide_fea_v2ext_clamp.npy", "DROP138": "/workspace/data/wide_fea_v2ext.npy"}
MT = np.load("/workspace/data/wide_fea_v2ext_meta.npz", allow_pickle=True)          # identical across arms (gate C1)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; names = [str(n) for n in MT["names"]]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts]); nA = len(E_ts); NW = 829
keep = [k for k, nm in enumerate(names) if not (nm.startswith("ret5_sum_48") or nm.startswith("ret5_sum_288"))]
assert [names[k] for k in keep] == PINS["keep_names"]
FIRST_CLEAN = 1643587200   # 2022-01-31 00:00Z: first anchor with E_row >= 8640 (cache starts 2022-01-01 00:00)
DROP = E_ts < FIRST_CLEAN; assert int(DROP.sum()) == 138, int(DROP.sum())
def sp(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 30: return np.nan
    r = spearmanr(a[ok], b[ok]); return r.correlation if hasattr(r, "correlation") else r[0]
def build_rows(arm):
    FEA = np.load(FEAS[arm], mmap_mode="r"); rX, rY, rA, rJ = [], [], [], []; dropped = 0
    for i in range(nA):
        if arm == "DROP138" and DROP[i]: dropped += 1; continue
        m = members[i]; yv = y4[i, m].astype(np.float64); ok = np.isfinite(yv)
        if ok.sum() < 50: continue
        mm = m[ok]; n = int(ok.sum()); rr = rankdata(yv[ok]) / max(n - 1, 1) - 0.5
        rX.append(np.asarray(FEA[i, mm])[:, keep].astype(np.float32)); rY.append(rr.astype(np.float32)); rA.append(np.full(n, i, np.int32)); rJ.append(mm.astype(np.int32))
    return np.concatenate(rX), np.concatenate(rY), np.concatenate(rA), np.concatenate(rJ), dropped
def fit_arm(arm, seed):
    X, Y, A, J, dropped = build_rows(arm); YRA = yrs[A]; tr = YRA < 2026; te = YRA == 2026
    kw = dict(n_estimators=400, learning_rate=0.05, num_leaves=63, subsample=0.8, colsample_bytree=0.8, n_jobs=60, verbose=-1)
    if seed is not None: kw["random_state"] = seed
    PRED = np.full((nA, NW), np.nan, np.float32); fold_ic = {}
    for YV in (2024, 2025):
        g2 = lgb.LGBMRegressor(**kw).fit(X[YRA < YV], Y[YRA < YV]); msk = YRA == YV; pv = g2.predict(X[msk]); a_te = A[msk]; j_te = J[msk]; ics_ = []
        for a in np.unique(a_te):
            sel = a_te == a; PRED[a, j_te[sel]] = pv[sel]; ics_.append(sp(pv[sel], y4[a, j_te[sel]]))
        fold_ic[YV] = float(np.nanmean(ics_))
    gbm = lgb.LGBMRegressor(**kw).fit(X[tr], Y[tr]); pv = gbm.predict(X[te]); a_te = A[te]; j_te = J[te]; ics = []
    for a in np.unique(a_te):
        sel = a_te == a; PRED[a, j_te[sel]] = pv[sel]; ics.append(sp(pv[sel], y4[a, j_te[sel]]))
    tag = "%s_s%s" % (arm, "def" if seed is None else seed); np.save("%s/slow_pred_%s.npy" % (OUT, tag), PRED)
    res = {"arm": arm, "seed": seed, "n_rows": int(len(Y)), "dropped_anchors": dropped, "n_train_rows": int(tr.sum()), "ic2024": fold_ic[2024], "ic2025": fold_ic[2025], "ic26": float(np.nanmean(ics)),
           "pred_sha16": hashlib.sha256(open("%s/slow_pred_%s.npy" % (OUT, tag), "rb").read()).hexdigest()[:16]}
    print(json.dumps(res), flush=True); return res
if __name__ == "__main__":
    allres = []
    print("=== GATE C2: K_OLD default seed must reproduce the deployed v3 gate readings ===", flush=True)
    r = fit_arm("OLD", None); allres.append(r)
    for k, base, gate in (("ic2024", "2024", 0.004), ("ic2025", "2025", 0.004), ("ic26", "2026", 0.006)):
        d = abs(r[k] - float(BASE["ic"][base])); print("  %s %+.5f vs base %+.5f (|d|=%.5f, gate %.3f) -> %s" % (k, r[k], float(BASE["ic"][base]), d, gate, "OK" if d <= gate else "FAIL"), flush=True)
    for arm in ("OLD", "CLAMP", "DROP138"):
        for seed in (42, 2027): allres.append(fit_arm(arm, seed))
    json.dump(allres, open("%s/RESULTS.json" % OUT, "w"), indent=1); print("KCLAMP_DONE", flush=True)
