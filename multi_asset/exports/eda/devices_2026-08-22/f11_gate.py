"""F-11 录取门 @jpline。预注册 PREREG_F11 §2(SHA 650f3742, +§1-bis 修正案)先于本数字。
BASE=LGBM(171) vs LOB=LGBM(171+38), 只用 59 个 LOB 币的行(同行配对), walk-forward 2023-26, embargo 60。
判据: Δ秩IC(资产内 raw y4s 与 resid YR4s 双口径, 主=raw 子截面秩) ≥ +0.005 且 ≥3/4 折同号。"""
import os, glob, json, time, hashlib
import numpy as np
from scipy.stats import spearmanr
ROOT = "/mnt/storage/private/work_hsy"
DLW = f"{ROOT}/dlw_2026-08-22"; OUT = f"{ROOT}/f8_2026-08-22"
YEARS = (2023, 2024, 2025, 2026); EMB = 60
LGB = dict(n_estimators=400, learning_rate=0.05, num_leaves=63, subsample=0.8,
           colsample_bytree=0.8, random_state=0, n_jobs=20, verbose=-1)
T0 = time.time()


def log(*a):
    print(f"[{time.time()-T0:6.1f}s]", *a, flush=True)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""):
            h.update(ch)
    return h.hexdigest()


TG = np.load(f"{DLW}/data/dlw_targets.npz", allow_pickle=True)
yrs = TG["yrs"].astype(int); y4s = TG["y4s"]; YR4s = TG["YR4s"]; YRZ = TG["YRZ"]
nA, NW = y4s.shape
FE = np.load(f"{DLW}/data/dlw_fea82.npz", allow_pickle=True)
X82 = FE["X"]; pa = FE["pair_a"].astype(np.int64); ps = FE["pair_s"].astype(np.int64)
F9 = np.load(f"{OUT}/data/f8_fea89.npz", allow_pickle=True)
X171 = np.concatenate([X82, F9["X"]], 1).astype(np.float32); del X82, F9
# LOB 特征拼装 (nA, NW, 38)
parts = sorted(glob.glob(f"{OUT}/data/f11_parts/*.npz"))
z0 = np.load(parts[0], allow_pickle=True); names38 = [str(x) for x in z0["names"]]; K = len(names38)
LOB = np.full((nA, NW, K), np.nan, np.float32)
lob_cols = set()
for p in parts:
    z = np.load(p, allow_pickle=True)
    LOB[:, int(z["scol"]), :] = z["fe"][:, :K]
    lob_cols.add(int(z["scol"]))
log(f"parts {len(parts)} K {K}")
insub = np.isin(ps, sorted(lob_cols))
XL_rows = LOB[pa[insub], ps[insub]]                        # (nrows_sub, 38)
Xb = X171[insub]; Y = YRZ[pa[insub], ps[insub]]
A = pa[insub]; S = ps[insub]; YRA = yrs[A]
okrow = np.isfinite(Y) & np.isfinite(XL_rows[:, 0])        # LOB 覆盖行(±1 带 last 有值)
Xb = Xb[okrow]; XL_rows = XL_rows[okrow]; Y = Y[okrow]; A = A[okrow]; S = S[okrow]; YRA = YRA[okrow]
log(f"sub rows {len(Y)} (59币, LOB覆盖)")
rep = {"prereg_sha": "650f3742", "self_sha256": sha(os.path.abspath(__file__)),
       "n_rows": int(len(Y)), "cols": {"base": 171, "lob": K}, "folds": {}}
import lightgbm as lgb


def spear(x, y, nmin=25):
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() < nmin:
        return np.nan
    r = spearmanr(x[ok], y[ok])
    return float(r.correlation if hasattr(r, "correlation") else r[0])


for YV in YEARS:
    te_anchor = np.where(yrs == YV)[0]
    if te_anchor.size == 0:
        continue
    first_te = int(te_anchor[0])
    tr = (YRA < YV) & (A < first_te - EMB)
    te = YRA == YV
    if tr.sum() < 30000 or te.sum() < 5000:
        rep["folds"][str(YV)] = {"skipped": f"tr {int(tr.sum())} te {int(te.sum())}"}
        log(f"[{YV}] skip 样本不足 tr {tr.sum()} te {te.sum()}")
        continue
    out = {}
    P = {}
    for arm, X in (("base", Xb), ("lob", np.concatenate([Xb, XL_rows], 1))):
        t1 = time.time()
        g = lgb.LGBMRegressor(**LGB).fit(X[tr], Y[tr])
        pv = g.predict(X[te]).astype(np.float32)
        P[arm] = pv
        icr = []; icy = []
        for a_ in np.unique(A[te]):
            m = te & (A == a_)
            icr.append(spear(pv[m[te]] if False else pv[(A[te] == a_)], YR4s[a_, S[te][A[te] == a_]]))
            icy.append(spear(pv[(A[te] == a_)], y4s[a_, S[te][A[te] == a_]]))
        out[arm] = {"ic_resid": float(np.nanmean(icr)), "ic_raw": float(np.nanmean(icy)), "sec": round(time.time() - t1, 1)}
        log(f"[{YV}] {arm} raw {out[arm]['ic_raw']:+.4f} resid {out[arm]['ic_resid']:+.4f} ({out[arm]['sec']}s)")
    out["d_raw"] = round(out["lob"]["ic_raw"] - out["base"]["ic_raw"], 5)
    out["d_resid"] = round(out["lob"]["ic_resid"] - out["base"]["ic_resid"], 5)
    rep["folds"][str(YV)] = out
    log(f"== {YV}: Δraw {out['d_raw']:+.5f} Δresid {out['d_resid']:+.5f}")
    json.dump(rep, open(f"{OUT}/results/f11_gate.json", "w"), indent=1, default=float)
ds = [v["d_raw"] for v in rep["folds"].values() if "d_raw" in v]
rep["d_raw_mean"] = round(float(np.mean(ds)), 5) if ds else None
rep["n_pos_folds"] = int(sum(d > 0 for d in ds))
rep["gate_pass"] = bool(ds and np.mean(ds) >= 0.005 and sum(d > 0 for d in ds) >= min(3, len(ds)))
json.dump(rep, open(f"{OUT}/results/f11_gate.json", "w"), indent=1, default=float)
log(f"F11_GATE_DONE Δraw均 {rep['d_raw_mean']} 同号折 {rep['n_pos_folds']}/{len(ds)} PASS={rep['gate_pass']}")
