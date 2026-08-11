"""32ch 自建 · 第二步: OHLCV 网格 -> 32 通道(与生产面板逐位同构)。

★ 零转写原则: 因子公式直接 `from wide_factory import build_factors, _shift, _roll`
  —— 20 个 zoo 因子一行不抄。只有通道 20-31 的装配按 build_wide_dl L98-129 镜像,
  其中 betaadj_ret24 用【因果】窗 np.convolve(...,"full")[:T] (build_wide_dl_causal 的修法),
  绝不用 "same"(中心窗, 含 11h 未来 —— ch31 泄漏的原形)。
★ funding 维度修正(0B/0C 实测过的坑): 4h/8h 结算币共存, rank-centring 消不掉群体位移
  ⇒ 逐行 rate*(8/ivh) 先归一再 EMA(span=24h 等效)。列缺失时用相邻结算间隔推 ivh
  (原版回退 8.0 平坦值; 但 ~29 币中途迁移 4h↔8h, 间隔推导更忠于修正意图 —— 差异已记录)。
★ 校验: baseline8.npz(生产面板原件)在场时, 8 列逐列 corr(MEMBER∩finite), ≥0.999 判 PASS。
"""
import sys, os, glob
import numpy as np
import pandas as pd
sys.path.insert(0, "/workspace/code")
from multi_asset.data.wide_factory import build_factors, _shift, _roll  # 原版, 零转写

G = np.load("/workspace/data/ohlcv_grid.npz", allow_pickle=True)
P = np.load("/workspace/data/panel_targets.npz", allow_pickle=True)
TS = np.asarray(G["ts"]).astype(np.int64)
SYMS = [str(s) for s in G["symbols"]]
T, N = len(TS), len(SYMS)
C, H, L = G["CLOSE"].astype(np.float64), G["HIGH"].astype(np.float64), G["LOW"].astype(np.float64)
V, QV = G["VOL"].astype(np.float64), G["QVOL"].astype(np.float64)

# ---- DVOL30 (build_wide_panel L102 原式) ----
DV = pd.DataFrame(QV).rolling(24 * 30, min_periods=24 * 5).mean().values

# ---- FUND_EMA (build_wide_panel L57-92 原配方) ----
FUND = np.full((T, N), np.nan)
n_col = n_gap = 0
for si, s in enumerate(SYMS):
    rows = []
    for fp in sorted(glob.glob(f"/workspace/data/raw/fundingRate/{s}-2*.csv")):
        try:
            with open(fp) as f:
                first = f.readline()
                hdr = None if first.split(",")[0].strip().isdigit() else 0
            df = pd.read_csv(fp, header=hdr)
            rows.append(df)
        except Exception:
            continue
    if not rows:
        continue
    fd = pd.concat(rows, ignore_index=True)
    cols = [str(c).lower() for c in fd.columns]
    def _find(*keys, default=None):
        for i, c in enumerate(cols):
            if any(k in c for k in keys):
                return i
        return default
    it = _find("calc_time", "funding_time", "time", default=0)
    ir = _find("last_funding_rate", "funding_rate", "rate", default=len(cols) - 1)
    ii = _find("interval")
    fts = pd.to_numeric(fd.iloc[:, it], errors="coerce").values.astype(np.float64)
    rate = pd.to_numeric(fd.iloc[:, ir], errors="coerce").values.astype(np.float64)
    ok = np.isfinite(fts) & np.isfinite(rate)
    fts, rate = fts[ok], rate[ok]
    if len(fts) < 3:
        continue
    o = np.argsort(fts); fts, rate = fts[o], rate[o]
    fts = np.where(fts > 1e14, fts / 1000, fts).astype(np.int64)   # us -> ms
    if ii is not None:
        ivh = pd.to_numeric(fd.iloc[:, ii], errors="coerce").values.astype(np.float64)[ok][o]
        ivh = np.where(np.isfinite(ivh) & (ivh > 0), ivh, 8.0); n_col += 1
    else:  # 间隔推导: 相邻结算差, 就近取 {1,2,4,8}
        gap = np.diff(fts) / 3600000.0
        gap = np.concatenate([[gap[0] if len(gap) else 8.0], gap])
        grid_iv = np.array([1.0, 2.0, 4.0, 8.0])
        ivh = grid_iv[np.abs(gap[:, None] - grid_iv[None, :]).argmin(1)]; n_gap += 1
    ih = float(np.median(ivh))
    span = max(2, int(round(24.0 / max(ih, 1.0))))
    ema = pd.Series(rate * (8.0 / ivh)).ewm(span=span, adjust=False).mean().values
    idx = np.searchsorted(fts, TS, side="right") - 1          # 因果 ffill: 最后一个 ≤t
    okk = idx >= 0
    FUND[okk, si] = ema[idx[okk]]
print(f"FUND_EMA: interval 列可用 {n_col} 币 / 间隔推导 {n_gap} 币; 填充 {np.isfinite(FUND).mean():.3f}")

# ---- 20 个 zoo 因子: 原版函数 ----
z = {"CLOSE": C, "HIGH": H, "LOW": L, "VOL": V, "QVOL": QV, "FUND_EMA": FUND, "DVOL30": DV}
F = build_factors(z)
ch_names = list(F.keys())
chans = [F[k][0] for k in ch_names]

# ---- 通道 20-31: build_wide_dl L98-129 镜像(唯一改动 = 因果 mkt24) ----
logc = np.log(np.where(C > 0, C, np.nan))
ret1 = logc - _shift(logc, 1)
for n in (1, 4, 12, 24):
    chans.append(logc - _shift(logc, n)); ch_names.append(f"ret_{n}h")
chans.append(_roll(ret1, 6, "std")); ch_names.append("rvol_6h")
chans.append(np.log(np.where(QV > 0, QV, np.nan))); ch_names.append("logqvol")
def _xsr(A):
    R = np.full_like(A, np.nan, np.float32)
    for t in range(A.shape[0]):
        v = np.isfinite(A[t])
        if v.sum() >= 8:
            r = np.argsort(np.argsort(A[t, v])).astype(np.float32)
            R[t, v] = r / (v.sum() - 1) - 0.5
    return R
market = np.nanmean(np.where(np.isfinite(ret1), ret1, np.nan), axis=1)
for nm, A in {"xsr_rvol": F["rvol_24h"][0], "xsr_ret24": logc - _shift(logc, 24),
              "xsr_fund": F["funding_ema"][0], "xsr_turn": F["lturnover_24h"][0],
              "xsr_mom72": F["mom_72h"][0]}.items():
    chans.append(_xsr(A)); ch_names.append(nm)
mkt24 = np.convolve(np.nan_to_num(market), np.ones(24), "full")[:T]   # ★ 因果尾窗
chans.append((logc - _shift(logc, 24)) - F["beta_24h"][0] * mkt24[:, None])
ch_names.append("betaadj_ret24")
CH = np.nan_to_num(np.stack(chans, axis=2).astype(np.float32), nan=0.0, posinf=0.0, neginf=0.0)
print(f"CH {CH.shape}  通道: {ch_names}")

# ---- 与生产面板 ch_names 顺序断言 ----
EXPECT = ['funding_ema','mom_4h','mom_8h','mom_24h','mom_72h','mom_168h','rev_1h','rev_3h',
          'rvol_24h','dvol_24h','rvol_72h','dvol_72h','beta_24h','beta_72h','lturnover_24h',
          'illiq_72h','size_dvol','max_ret_24h','gtja_046','a101_044','ret_1h','ret_4h',
          'ret_12h','ret_24h','rvol_6h','logqvol','xsr_rvol','xsr_ret24','xsr_fund',
          'xsr_turn','xsr_mom72','betaadj_ret24']
assert ch_names == EXPECT, f"通道顺序漂移: {[(i,a,b) for i,(a,b) in enumerate(zip(ch_names,EXPECT)) if a!=b]}"
print("通道顺序与生产面板逐位一致 ✓")

# ---- baseline8 校验(在场才跑) ----
b8p = "/workspace/data/baseline8.npz"
MEM = P["MEMBER110"]
if os.path.exists(b8p) and os.path.getsize(b8p) > 120e6:
    B8 = np.load(b8p, allow_pickle=True)
    ref, cols = B8["B"], [str(c) for c in B8["cols"]]
    print("\nbaseline8 逐列校验 (corr over MEMBER∩finite):")
    allpass = True
    for k, cname in enumerate(cols):
        j = ch_names.index(cname)
        a, b = CH[:, :, j], ref[:, :, k]
        m = MEM & np.isfinite(a) & np.isfinite(b) & (a != 0) & (b != 0)
        r = np.corrcoef(a[m], b[m])[0, 1] if m.sum() > 1000 else np.nan
        ok = r > 0.999
        allpass &= bool(ok)
        print(f"  {cname:ville16s}" if False else f"  {cname:16s} corr={r:.6f}  n={m.sum():,}  {'PASS' if ok else '★FAIL'}")
    print(f"⇒ 校验 {'全部 PASS' if allpass else '有 FAIL — 53ch 判决前必须解释'}")
else:
    print("\nbaseline8 未到齐 — 校验推迟(不阻塞装配, 但 53ch 判决前必须补跑)")

out = {"CH": CH, "ch_names": np.array(ch_names, object),
       "baseline_cols": np.array(['funding_ema','mom_24h','mom_72h','rev_1h','rvol_24h',
                                  'size_dvol','max_ret_24h','beta_24h'], object)}
for k in ("ts","symbols","MEMBER110","Y1","YR1","CL1","Y4","YR4","CL4","Y24","YR24","CL24"):
    out[k] = P[k]
np.savez("/workspace/data/wide_dl_rebuilt32.npz", **out)
print("saved wide_dl_rebuilt32.npz")
