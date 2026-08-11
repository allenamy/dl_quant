"""basis 族面板: premiumIndex/markPrice/indexPrice 月度 CSV -> 7 特征, 滞后 1h。"""
import glob, os, time
import numpy as np, pandas as pd
P = np.load("/workspace/data/panel_targets.npz", allow_pickle=True)
R = np.load("/workspace/data/wide_dl_prodmask32.npz", allow_pickle=True)
TS = np.asarray(P["ts"]).astype(np.int64)
SYMS = [str(s) for s in P["symbols"]]
SI = {s: i for i, s in enumerate(SYMS)}
T, N = len(TS), len(SYMS)
ROW = {int(t): i for i, t in enumerate(TS)}
def load_fam(fam, sym, col=4):
    """月度 kline CSV -> {hour_ms: close}"""
    out = {}
    for fp in glob.glob("/workspace/data/raw/%s/%s-2*.csv" % (fam, sym)):
        try:
            with open(fp) as f:
                for ln in f:
                    p = ln.split(",", 6)
                    if not p[0].strip().isdigit(): continue
                    ms = int(p[0]);  ms = ms // 1000 if ms > 10**14 else ms
                    out[ms] = float(p[col])
        except Exception: pass
    return out
PREM = np.full((T, N), np.nan); GAP = np.full((T, N), np.nan)
t0 = time.time()
for si, s in enumerate(SYMS):
    pr = load_fam("premiumIndexKlines", s)
    mk = load_fam("markPriceKlines", s)
    ix = load_fam("indexPriceKlines", s)
    for ms, v in pr.items():
        i = ROW.get(ms + 3600_000)          # 滞后 1h: 该小时的值写到下一小时行
        if i is not None: PREM[i, si] = v
    for ms, m in mk.items():
        x = ix.get(ms)
        i = ROW.get(ms + 3600_000)
        if i is not None and x and x > 0: GAP[i, si] = m / x - 1.0
    if (si+1) % 30 == 0: print("  %d/%d %.1fmin" % (si+1, N, (time.time()-t0)/60), flush=True)
names32 = [str(x) for x in R["ch_names"]]
fund = R["CH"][:, :, names32.index("funding_ema")].astype(np.float64); fund[fund == 0] = np.nan
def roll(A, w, fn="mean"):
    return getattr(pd.DataFrame(A).rolling(w, min_periods=max(3, w//2)), fn)().values
F = {}
F["prem_ema"]   = pd.DataFrame(PREM).ewm(span=8, min_periods=4).mean().values
F["prem_mom24"] = PREM - roll(PREM, 24)
F["prem_vol24"] = roll(PREM, 24, "std")
F["prem_x_fund"]= F["prem_ema"] - fund
F["mark_idx_gap"] = roll(GAP, 8)
F["prem_rev"]   = -(PREM - roll(PREM, 168))
disp = np.nanstd(np.where(R["MEMBER110"], PREM, np.nan), axis=1)
F["prem_disp_xsec"] = np.repeat(pd.Series(disp).rolling(24, min_periods=12).mean().values[:, None], N, 1)
X = np.stack([np.asarray(v, np.float32) for v in F.values()], axis=2)
print("填充率 prem %.3f gap %.3f" % (np.isfinite(PREM).mean(), np.isfinite(GAP).mean()))
np.savez_compressed("/workspace/data/basis_hourly.npz", X=X, ts=TS,
                    symbols=np.array(SYMS, object), feats=np.array(list(F), object), lag_ms=3600000)
print("saved basis_hourly.npz", X.shape)
