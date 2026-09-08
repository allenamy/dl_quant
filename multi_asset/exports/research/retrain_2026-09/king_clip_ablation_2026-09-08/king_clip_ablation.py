"""PREREG_king_clip_label_ablation_2026-09-08 (+AMENDMENT 1). Three label arms x seeds, king refit.
Training/prediction path copied verbatim from pod_export_bundle_v3.py L28-L96; ONLY the label matrix differs.
Arms: OLD (as deployed) / WORST (adversarial worst-case relabel of clip-affected cells) / DROP (those cells -> NaN)."""
import os, sys, json, time, hashlib
import numpy as np
from scipy.stats import rankdata, spearmanr
sys.path.insert(0, "/workspace")
from zload import zload
import lightgbm as lgb

OUT = "/workspace/review_scratch/king_clip_ablation"
os.makedirs(OUT, exist_ok=True)
PINS = json.load(open("/workspace/live_pins.json"))
BASE = json.load(open("/workspace/slow_scorer_v3base.json"))
FEA = np.load("/workspace/data/wide_fea_v2ext.npy", mmap_mode="r")
MT = np.load("/workspace/data/wide_fea_v2ext_meta.npz", allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; names = [str(n) for n in MT["names"]]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts]); nA = len(E_ts); NW = 829
keep = [k for k, nm in enumerate(names) if not (nm.startswith("ret5_sum_48") or nm.startswith("ret5_sum_288"))]
assert [names[k] for k in keep] == PINS["keep_names"], "keep_names mismatch"

# ---- clip-affected mask on the KING window rows [E, E+47] ----
Z = zload("/workspace/data/dlnative_5m_wide829_f16_ext.npz", allow_pickle=True)
CTS = Z["ts"].astype(np.int64); r5 = Z["data"][:, :, 0].astype(np.float32); fin5 = np.isfinite(r5)
HI = np.float32(np.float16(0.3)); LO = np.float32(np.float16(-0.3))
CSlo = np.concatenate([np.zeros((1, NW), np.int32), np.cumsum((r5 == LO) & fin5, 0, dtype=np.int32)])
CShi = np.concatenate([np.zeros((1, NW), np.int32), np.cumsum((r5 == HI) & fin5, 0, dtype=np.int32)])
cidx = {int(t): i for i, t in enumerate(CTS)}
del r5, fin5, Z

def sp(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 30: return np.nan
    r = spearmanr(a[ok], b[ok]); return r.correlation if hasattr(r, "correlation") else r[0]

def build_rows(arm):
    """Returns X, Y, A exactly as the deployed script, with the arm's label transform."""
    rows_X, rows_y, rows_a = [], [], []
    n_aff = 0; n_anch = 0
    for i in range(nA):
        m = members[i]; yv = y4[i, m].astype(np.float64); ok = np.isfinite(yv)
        if ok.sum() < 50: continue
        mm = m[ok]; yy = yv[ok].copy()
        E = cidx.get(int(E_ts[i]))
        aff = np.zeros(len(mm), bool)
        if E is not None and E + 48 < CSlo.shape[0]:
            aff = ((CSlo[E + 48, mm] - CSlo[E, mm]) + (CShi[E + 48, mm] - CShi[E, mm])) > 0
        if aff.any():
            n_anch += 1; n_aff += int(aff.sum())
            if arm == "WORST":
                lo = aff & ((CSlo[E + 48, mm] - CSlo[E, mm]) > 0)
                hi = aff & ((CShi[E + 48, mm] - CShi[E, mm]) > 0)
                if lo.any(): yy[lo] = np.nanmin(yv[ok]) - 1.0 - np.arange(int(lo.sum()))
                if hi.any(): yy[hi] = np.nanmax(yv[ok]) + 1.0 + np.arange(int(hi.sum()))
            elif arm == "DROP":
                yy[aff] = np.nan
        good = np.isfinite(yy)
        if good.sum() < 50: continue
        n = int(good.sum())
        rr = rankdata(yy[good]) / max(n - 1, 1) - 0.5
        rows_X.append(np.asarray(FEA[i, mm[good]])[:, keep].astype(np.float32))
        rows_y.append(rr.astype(np.float32)); rows_a.append(np.full(n, i, np.int32))
    return (np.concatenate(rows_X), np.concatenate(rows_y), np.concatenate(rows_a), n_aff, n_anch)

def fit_arm(arm, seed):
    X, Y, A, n_aff, n_anch = build_rows(arm)
    YRA = yrs[A]; tr = YRA < 2026; te = YRA == 2026
    kw = dict(n_estimators=400, learning_rate=0.05, num_leaves=63, subsample=0.8,
              colsample_bytree=0.8, n_jobs=60, verbose=-1)
    if seed is not None: kw["random_state"] = seed
    PRED = np.full((nA, NW), np.nan, np.float32); fold_ic = {}
    for YV in (2024, 2025):
        g2 = lgb.LGBMRegressor(**kw).fit(X[YRA < YV], Y[YRA < YV])
        pv = g2.predict(X[YRA == YV]); a_te = A[YRA == YV]; ics_ = []
        for a in np.unique(a_te):
            sel = a_te == a; m = members[a]; okm = np.isfinite(y4[a, m])
            PRED[a, m[okm]] = pv[sel]; ics_.append(sp(pv[sel], y4[a, m[okm]]))
        fold_ic[YV] = float(np.nanmean(ics_))
    gbm = lgb.LGBMRegressor(**kw).fit(X[tr], Y[tr])
    pv = gbm.predict(X[te]); a_te = A[te]; ics = []
    for a in np.unique(a_te):
        sel = a_te == a; m = members[a]; okm = np.isfinite(y4[a, m])
        PRED[a, m[okm]] = pv[sel]; ics.append(sp(pv[sel], y4[a, m[okm]]))
    ic26 = float(np.nanmean(ics))
    tag = "%s_s%s" % (arm, "def" if seed is None else seed)
    np.save("%s/slow_pred_%s.npy" % (OUT, tag), PRED)
    res = {"arm": arm, "seed": seed, "n_rows": int(len(Y)), "n_affected_rows": n_aff,
           "n_anchors_touched": n_anch, "ic2024": fold_ic[2024], "ic2025": fold_ic[2025], "ic26": ic26,
           "base_ic": {k: float(v) for k, v in BASE["ic"].items()},
           "pred_sha16": hashlib.sha256(open("%s/slow_pred_%s.npy" % (OUT, tag), "rb").read()).hexdigest()[:16]}
    print(json.dumps(res), flush=True)
    return res

if __name__ == "__main__":
    allres = []
    print("=== SELF-CHECK 1: K_OLD at the deployed (default) seed must reproduce the deployed gate readings ===", flush=True)
    r = fit_arm("OLD", None); allres.append(r)
    print("  ic2024 %+.5f vs base %+.5f (|d|=%.5f, gate 0.004)" % (r["ic2024"], r["base_ic"]["2024"], abs(r["ic2024"] - r["base_ic"]["2024"])), flush=True)
    print("  ic2025 %+.5f vs base %+.5f (|d|=%.5f, gate 0.004)" % (r["ic2025"], r["base_ic"]["2025"], abs(r["ic2025"] - r["base_ic"]["2025"])), flush=True)
    print("  ic26   %+.5f vs base %+.5f (|d|=%.5f, gate 0.006)" % (r["ic26"], r["base_ic"]["2026"], abs(r["ic26"] - r["base_ic"]["2026"])), flush=True)
    for arm in ("OLD", "WORST", "DROP"):
        for seed in (42, 2027):
            allres.append(fit_arm(arm, seed))
    json.dump(allres, open("%s/RESULTS.json" % OUT, "w"), indent=1)
    print("DONE", flush=True)
