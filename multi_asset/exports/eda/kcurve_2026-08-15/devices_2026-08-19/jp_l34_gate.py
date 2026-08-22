"""L3+L4 定向改造重测(判据封于跑前, 各计 1 测):
L3: #48 门A 幸存 2 列(cumdep_far_asym, spread_bps)作【部分覆盖树特征】(14 大币行, 其余 NaN→秩中位).
    判折=覆盖率≥60% 的年折(预期 2024/2025); 判据: 判折均 Δ≥+0.003 双跑且末判折≥0.
L4: BTC 书状态 3 量(spread/ldepth/far_asym)24h 均值的【30d 自 z 归一】全局状态列(P1 改造 vs L2 原始水平).
    覆盖锚(2023+), 折 2024/25/26; 判据同族门.
env: FEA_IN META_IN BS_IN LOB_IN OUT_JSON
"""
import json, time, os
import numpy as np
from scipy.stats import rankdata, spearmanr
import lightgbm as lgb
FEA = np.load(os.environ["FEA_IN"], mmap_mode="r")
MT = np.load(os.environ["META_IN"], allow_pickle=True)
BS = np.load(os.environ["BS_IN"], allow_pickle=True)
L = np.load(os.environ["LOB_IN"])
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]
names = [str(n) for n in MT["names"]]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
slow_keep = [k for k, nm in enumerate(names) if not (nm.startswith("ret5_sum_48") or nm.startswith("ret5_sum_288"))]
C450 = np.load(os.environ["FEA_IN"].replace("fea450.npy", "cache450.npz"), mmap_mode="r")
syms450 = [str(s) for s in C450["symbols"]]
# ---- L3 特征: 对齐 bookstate14 ----
bts = BS["ts"].astype(np.int64); bsym = [str(s) for s in BS["symbols"]]
fnames = [str(s) for s in BS["feat_names"]]
i_far, i_spr = fnames.index("cumdep_far_asym"), fnames.index("spread_bps")
Fraw = BS["F_raw"][:, :, [i_far, i_spr]]
pos = np.searchsorted(bts, E_ts * 1000)
pos = np.clip(pos, 0, len(bts) - 1)
exact = bts[pos] == E_ts * 1000
smap = [syms450.index(s) if s in syms450 else -1 for s in bsym]
X3 = np.full((len(E_ts), len(syms450), 2), np.nan, np.float32)
for i in range(len(E_ts)):
    if not exact[i]: continue
    for j, si in enumerate(smap):
        if si >= 0: X3[i, si] = Fraw[pos[i], j]
cov3 = np.isfinite(X3[:, :, 0]).sum(1) >= 10
print(f"L3 覆盖锚 {cov3.sum()}/{len(E_ts)}; 按年:", {y: int((cov3 & (yrs == y)).sum()) for y in (2024, 2025, 2026)}, flush=True)
# ---- L4 特征: BTC 全局 z 状态 ----
lts = L["ts_min"].astype(np.int64); lf = L["feat"].astype(np.float64)
o = np.argsort(lts); lts, lf = lts[o], lf[o]
sel9 = [0, 1, 5]  # spread_bps, ldepth5, far_asym
lcum = np.vstack([np.zeros((1, len(sel9))), np.nancumsum(np.where(np.isfinite(lf[:, sel9]), lf[:, sel9], 0), 0)])
lcnt = np.vstack([np.zeros((1, len(sel9))), np.cumsum(np.isfinite(lf[:, sel9]), 0)])
amin = E_ts // 60
hi = np.searchsorted(lts, amin, side="right"); lo = np.searchsorted(lts, amin - 1440, side="right")
s = lcum[hi] - lcum[lo]; n = lcnt[hi] - lcnt[lo]
M24 = np.where(n >= 720, s / np.maximum(n, 1), np.nan)  # (nA, 3)
cov4 = np.isfinite(M24[:, 0])
import pandas as pd
M = pd.DataFrame(M24)
Z = ((M - M.rolling(180, min_periods=90).mean()) / (M.rolling(180, min_periods=90).std() + 1e-12)).clip(-5, 5).values.astype(np.float32)
def sp(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 30: return np.nan
    r = spearmanr(a[ok], b[ok]); return r.correlation if hasattr(r, "correlation") else r[0]
def xrank(v):
    out = np.zeros(len(v), np.float32); ok = np.isfinite(v)
    if ok.sum() > 1: out[ok] = rankdata(v[ok]) / (ok.sum() - 1) - 0.5
    return out
BASE = {"2024": 0.0530, "2025": 0.0550, "2026": 0.0545}
def build_and_run(mask, extra_fn, judge_years, label):
    rows_X, rows_E, rows_y, rows_a = [], [], [], []
    for i in range(len(E_ts)):
        if not mask[i]: continue
        m = members[i]; yv = y4[i, m]; ok = np.isfinite(yv)
        if ok.sum() < 50: continue
        rr = rankdata(yv[ok]) / max(ok.sum() - 1, 1) - 0.5
        rows_X.append(np.asarray(FEA[i, m[ok]][:, slow_keep], dtype=np.float32))
        rows_E.append(extra_fn(i, m[ok]))
        rows_y.append(rr.astype(np.float32)); rows_a.append(np.full(ok.sum(), i, np.int32))
    XB = np.concatenate(rows_X); XE = np.concatenate(rows_E)
    Y = np.concatenate(rows_y); A = np.concatenate(rows_a); YRA = yrs[A]
    print(f"[{label}] rows {len(Y)} extra {XE.shape[1]}", flush=True)
    out = {}
    for arm, X in (("base", XB), ("arm", np.column_stack([XB, XE]))):
        out[arm] = {}
        for seed in (0, 1):
            r = {}
            for YV in judge_years:
                tr = YRA < YV; te = YRA == YV
                if te.sum() < 1000: continue
                g = lgb.LGBMRegressor(n_estimators=400, learning_rate=0.05, num_leaves=63, subsample=0.8,
                                      colsample_bytree=0.8, n_jobs=20, verbose=-1, random_state=seed).fit(X[tr], Y[tr])
                pv = g.predict(X[te]); a_te = A[te]; ics = []
                for a in np.unique(a_te):
                    s_ = a_te == a; mm = members[a]; okm = np.isfinite(y4[a, mm])
                    ics.append(sp(pv[s_], y4[a, mm][okm]))
                r[str(YV)] = round(float(np.nanmean(ics)), 4)
            out[arm][f"s{seed}"] = r
            print(f"  [{label} {arm} s{seed}] {r}", flush=True)
    verd = []
    for seed in (0, 1):
        b, a = out["base"][f"s{seed}"], out["arm"][f"s{seed}"]
        d = {y: round(a[y] - b[y], 4) for y in b}
        avg = round(float(np.mean(list(d.values()))), 4)
        last = d[max(d)]
        verd.append({"delta": d, "avg": avg, "last": last})
        print(f"  [{label} Δ s{seed}] {d} avg {avg:+.4f}", flush=True)
    ok = all(v["avg"] >= 0.003 and v["last"] >= 0 for v in verd)
    return {"runs": verd, "verdict": "PASS" if ok else "KILLED", "arms": out}
res = {}
res["L3_bookstate14_partial"] = build_and_run(
    cov3, lambda i, mi: np.column_stack([xrank(X3[i, mi, 0]), xrank(X3[i, mi, 1])]),
    (2024, 2025, 2026), "L3")
print("L3 VERDICT", res["L3_bookstate14_partial"]["verdict"], flush=True)
res["L4_global_zstate"] = build_and_run(
    cov4, lambda i, mi: np.repeat(np.nan_to_num(Z[i])[None, :], len(mi), 0),
    (2024, 2025, 2026), "L4")
print("L4 VERDICT", res["L4_global_zstate"]["verdict"], flush=True)
json.dump(res, open(os.environ.get("OUT_JSON", "l34_gate.json"), "w"), indent=1, default=str)
print("L34_GATE_DONE", flush=True)
