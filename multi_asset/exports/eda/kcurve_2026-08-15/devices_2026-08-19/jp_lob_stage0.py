"""L0 阶段0 判官(#29 冻结判据 + 设计稿 §2.3 装置补钉; 与结论同寿命当日入库):
BTC 时序: base78 vs base78+LOB慢聚合(9列×{1h,24h}=18列), 按年扩张三折双种子, y4 BTC 时序 rank-IC.
判: min Δavg ≥ +0.01 ⇒ CONTINUE(采购询价); max Δavg < +0.005 ⇒ LOB_ALPHA_CLOSED; 其间 GRAY_ZONE.
安慰剂臂(装置自检, 非判据): LOB 特征滞后 7 天注入, Δ 应≈0.
env: FEA_IN META_IN CACHE_IN LOB_IN OUT_JSON
"""
import json, time, os
import numpy as np
from scipy.stats import spearmanr
import lightgbm as lgb

MT = np.load(os.environ["META_IN"], allow_pickle=True)
FEA = np.load(os.environ["FEA_IN"], mmap_mode="r")
C = np.load(os.environ["CACHE_IN"], mmap_mode="r")
L = np.load(os.environ["LOB_IN"])
E_ts = MT["E_ts"].astype(np.int64); y4 = MT["y4"]
names = [str(n) for n in MT["names"]]
syms = [str(s) for s in C["symbols"]]; iBTC = syms.index("BTCUSDT")
slow_keep = [k for k, nm in enumerate(names) if not (nm.startswith("ret5_sum_48") or nm.startswith("ret5_sum_288"))]
lts = L["ts_min"].astype(np.int64); lf = L["feat"].astype(np.float64)  # (n, 9)
order = np.argsort(lts); lts, lf = lts[order], lf[order]
lcum = np.vstack([np.zeros((1, lf.shape[1])), np.nancumsum(np.where(np.isfinite(lf), lf, 0), 0)])
lcnt = np.vstack([np.zeros((1, lf.shape[1])), np.cumsum(np.isfinite(lf), 0)])
def wmean(a_min, W):
    hi = np.searchsorted(lts, a_min, side="right")
    lo = np.searchsorted(lts, a_min - W, side="right")
    s = lcum[hi] - lcum[lo]; n = lcnt[hi] - lcnt[lo]
    out = np.where(n >= W * 0.5, s / np.maximum(n, 1), np.nan)
    return out, n
amin = E_ts // 60
X18 = np.full((len(E_ts), 18), np.nan, np.float32)
cov_ok = np.zeros(len(E_ts), bool)
for j, W in enumerate((60, 1440)):
    m, n = wmean(amin, W)
    X18[:, j * 9:(j + 1) * 9] = m
    if W == 1440: cov_ok = n[:, 0] >= 720
XB = np.asarray(FEA[:, iBTC, :], dtype=np.float32)[:, slow_keep]
Y = y4[:, iBTC]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
valid = cov_ok & np.isfinite(Y) & (np.isfinite(XB).sum(1) > 40)
print(f"锚 {valid.sum()}/{len(E_ts)} 有 LOB 覆盖+标签", flush=True)
XBv, X18v, Yv, yv, Ev = XB[valid], X18[valid], Y[valid], yrs[valid], E_ts[valid]
# 安慰剂: LOB 特征取 7 天前锚的值(42 步)
X18p = np.full_like(X18v, np.nan); X18p[42:] = X18v[:-42]
def ts_ic(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 100: return np.nan
    r = spearmanr(a[ok], b[ok]); return r.correlation if hasattr(r, "correlation") else r[0]
def run(Xarm, seed):
    out = {}
    for YV in (2024, 2025, 2026):
        tr = yv < YV; te = yv == YV
        if te.sum() < 100: continue
        g = lgb.LGBMRegressor(n_estimators=300, learning_rate=0.05, num_leaves=31, subsample=0.8,
                              colsample_bytree=0.8, min_child_samples=20, n_jobs=16, verbose=-1,
                              random_state=seed).fit(Xarm[tr], Yv[tr])
        out[str(YV)] = round(float(ts_ic(g.predict(Xarm[te]), Yv[te])), 4)
    return out
res = {"n_anchors": int(valid.sum()), "arms": {}}
for arm, X in (("base", XBv), ("lob", np.column_stack([XBv, X18v])), ("placebo", np.column_stack([XBv, X18p]))):
    res["arms"][arm] = {}
    for seed in (0, 1):
        ic = run(X, seed)
        res["arms"][arm][f"seed{seed}"] = ic
        print(f"[{arm} s{seed}] {ic}", flush=True)
dvals = []
for seed in (0, 1):
    b, a = res["arms"]["base"][f"seed{seed}"], res["arms"]["lob"][f"seed{seed}"]
    d = {y: round(a[y] - b[y], 4) for y in b}
    avg = round(float(np.mean(list(d.values()))), 4)
    res[f"delta_seed{seed}"] = {"per_fold": d, "avg": avg}; dvals.append(avg)
    p = res["arms"]["placebo"][f"seed{seed}"]
    res[f"placebo_delta_seed{seed}"] = round(float(np.mean([p[y] - b[y] for y in b])), 4)
    print(f"[Δ s{seed}] {d} avg {avg:+.4f} | placebo {res[f'placebo_delta_seed{seed}']:+.4f}", flush=True)
res["VERDICT"] = ("CONTINUE_PURCHASE_QUOTE" if min(dvals) >= 0.01 else
                  "LOB_ALPHA_CLOSED" if max(dvals) < 0.005 else "GRAY_ZONE_OBSERVE")
print(f"VERDICT {res['VERDICT']}", flush=True)
json.dump(res, open(os.environ.get("OUT_JSON", "lob_stage0.json"), "w"), indent=1)
print("LOB_STAGE0_DONE", flush=True)
