"""FIX for the DROP arm + a bitwise re-derivation check of the already-saved OLD s42 arm.
BUG (mine): PRED[a, m[okm]] = pv[sel] assumed the training rows for an anchor are exactly m[okm],
which holds for OLD/WORST but NOT for DROP (it removes cells -> fewer rows). Now the member index
of every training row is carried explicitly and PRED is written at those indices.
★ CHECK: re-run OLD seed 42 through the FIXED path; its PRED must be bitwise identical to the saved one."""
import os, sys, json, time, hashlib
import numpy as np
from scipy.stats import rankdata, spearmanr
sys.path.insert(0, "/workspace")
from zload import zload
import lightgbm as lgb
OUT = "/workspace/review_scratch/king_clip_ablation"
PINS = json.load(open("/workspace/live_pins.json")); BASE = json.load(open("/workspace/slow_scorer_v3base.json"))
FEA = np.load("/workspace/data/wide_fea_v2ext.npy", mmap_mode="r")
MT = np.load("/workspace/data/wide_fea_v2ext_meta.npz", allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; names = [str(n) for n in MT["names"]]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts]); nA = len(E_ts); NW = 829
keep = [k for k, nm in enumerate(names) if not (nm.startswith("ret5_sum_48") or nm.startswith("ret5_sum_288"))]
assert [names[k] for k in keep] == PINS["keep_names"]
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
    rX, rY, rA, rJ = [], [], [], []          # rJ = member column index of each row  <-- the fix
    n_aff = 0; n_anch = 0
    for i in range(nA):
        m = members[i]; yv = y4[i, m].astype(np.float64); ok = np.isfinite(yv)
        if ok.sum() < 50: continue
        mm = m[ok]; yy = yv[ok].copy()
        E = cidx.get(int(E_ts[i])); aff = np.zeros(len(mm), bool)
        if E is not None and E + 48 < CSlo.shape[0]:
            aff = ((CSlo[E + 48, mm] - CSlo[E, mm]) + (CShi[E + 48, mm] - CShi[E, mm])) > 0
        if aff.any():
            n_anch += 1; n_aff += int(aff.sum())
            if arm == "WORST":
                lo = aff & ((CSlo[E + 48, mm] - CSlo[E, mm]) > 0); hi = aff & ((CShi[E + 48, mm] - CShi[E, mm]) > 0)
                if lo.any(): yy[lo] = np.nanmin(yv[ok]) - 1.0 - np.arange(int(lo.sum()))
                if hi.any(): yy[hi] = np.nanmax(yv[ok]) + 1.0 + np.arange(int(hi.sum()))
            elif arm == "DROP":
                yy[aff] = np.nan
        good = np.isfinite(yy)
        if good.sum() < 50: continue
        n = int(good.sum())
        rr = rankdata(yy[good]) / max(n - 1, 1) - 0.5
        rX.append(np.asarray(FEA[i, mm[good]])[:, keep].astype(np.float32))
        rY.append(rr.astype(np.float32)); rA.append(np.full(n, i, np.int32)); rJ.append(mm[good].astype(np.int32))
    return np.concatenate(rX), np.concatenate(rY), np.concatenate(rA), np.concatenate(rJ), n_aff, n_anch
def fit_arm(arm, seed, save=True):
    X, Y, A, J, n_aff, n_anch = build_rows(arm)
    YRA = yrs[A]; tr = YRA < 2026; te = YRA == 2026
    kw = dict(n_estimators=400, learning_rate=0.05, num_leaves=63, subsample=0.8,
              colsample_bytree=0.8, n_jobs=60, verbose=-1)
    if seed is not None: kw["random_state"] = seed
    PRED = np.full((nA, NW), np.nan, np.float32); fold_ic = {}
    for YV in (2024, 2025):
        g2 = lgb.LGBMRegressor(**kw).fit(X[YRA < YV], Y[YRA < YV])
        msk = YRA == YV; pv = g2.predict(X[msk]); a_te = A[msk]; j_te = J[msk]; ics_ = []
        for a in np.unique(a_te):
            sel = a_te == a
            PRED[a, j_te[sel]] = pv[sel]                       # <-- fixed indexing
            ics_.append(sp(pv[sel], y4[a, j_te[sel]]))
        fold_ic[YV] = float(np.nanmean(ics_))
    gbm = lgb.LGBMRegressor(**kw).fit(X[tr], Y[tr])
    pv = gbm.predict(X[te]); a_te = A[te]; j_te = J[te]; ics = []
    for a in np.unique(a_te):
        sel = a_te == a
        PRED[a, j_te[sel]] = pv[sel]
        ics.append(sp(pv[sel], y4[a, j_te[sel]]))
    ic26 = float(np.nanmean(ics))
    tag = "%s_s%s" % (arm, "def" if seed is None else seed)
    res = {"arm": arm, "seed": seed, "n_rows": int(len(Y)), "n_affected_rows": n_aff,
           "n_anchors_touched": n_anch, "ic2024": fold_ic[2024], "ic2025": fold_ic[2025], "ic26": ic26}
    if save:
        np.save("%s/slow_pred_%s.npy" % (OUT, tag), PRED)
        res["pred_sha16"] = hashlib.sha256(open("%s/slow_pred_%s.npy" % (OUT, tag), "rb").read()).hexdigest()[:16]
    print(json.dumps(res), flush=True)
    return res, PRED
if __name__ == "__main__":
    print("=== FIX CHECK: OLD seed 42 through the fixed path must reproduce the saved arm bitwise ===", flush=True)
    r, P = fit_arm("OLD", 42, save=False)
    old = np.load("%s/slow_pred_OLD_s42.npy" % OUT)
    same = np.array_equal(np.nan_to_num(P, nan=-9e9), np.nan_to_num(old, nan=-9e9))
    print("  bitwise identical to saved OLD_s42: %s ; max|diff| %.3e" % (same, np.nanmax(np.abs(P - old)) if not same else 0.0), flush=True)
    assert same, "fixed indexing changed a non-DROP arm -> STOP"
    for seed in (42, 2027):
        fit_arm("DROP", seed)
    print("DROP_DONE", flush=True)
