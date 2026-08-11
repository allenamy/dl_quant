"""造 taker flow 五因子 — PREREG_takerflow_family FROZEN 43a76ddb, 形态一字未改。
F1 tbr_24h · F2 tbr_dev(24h−168h) · F3 tbr_rev(−(4h−24h)) · F4 avg_dev · F5 cnt_dev
全部只用 ≤t 信息(尾随窗口, 右闭)。落盘含 ts/symbols 供服务器按名对齐。
"""
import numpy as np, json
E = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/eda"
z = np.load(f"{E}/bn_takerflow_1h.npz", allow_pickle=True)
ts = z["ts"]; syms = [str(s) for s in z["symbols"]]
QV, TB, CN = z["QVOL"].astype(np.float64), z["TAKER_BUY_QUOTE"].astype(np.float64), z["TRADE_COUNT"].astype(np.float64)
T, N = QV.shape
print(f"原始 {T} 小时 × {N} 币")

def roll_sum(a, w):
    """尾随 w 小时求和, 右闭(第 t 行含 t)。NaN 视作缺失, 不补零。"""
    b = np.where(np.isfinite(a), a, 0.0); m = np.isfinite(a).astype(np.float64)
    cs = np.cumsum(np.vstack([np.zeros((1, a.shape[1])), b]), axis=0)
    cm = np.cumsum(np.vstack([np.zeros((1, a.shape[1])), m]), axis=0)
    s = cs[w:] - cs[:-w]; n = cm[w:] - cm[:-w]
    out = np.full_like(a, np.nan); cnt = np.full_like(a, np.nan)
    out[w-1:] = s; cnt[w-1:] = n
    return np.where(cnt >= w*0.5, out, np.nan), cnt

def tbr(w):
    tb, _ = roll_sum(TB, w); qv, _ = roll_sum(QV, w)
    return np.where(qv > 0, tb/qv, np.nan)

def logavg(w):
    qv, _ = roll_sum(QV, w); cn, _ = roll_sum(CN, w)
    r = np.where((cn > 0) & (qv > 0), qv/np.where(cn > 0, cn, np.nan), np.nan)
    return np.log(r)

def logcnt(w):
    cn, _ = roll_sum(CN, w)
    return np.log(np.where(cn > 0, cn, np.nan))

t4, t24, t168 = tbr(4), tbr(24), tbr(168)
F = {
    "F1_tbr_24h":  t24,
    "F2_tbr_dev":  t24 - t168,
    "F3_tbr_rev": -(t4 - t24),
    "F4_avg_dev":  logavg(24) - logavg(168),
    "F5_cnt_dev":  logcnt(24) - logcnt(168),
}
print("\n因子覆盖与分布(全期):")
for k, v in F.items():
    f = v[np.isfinite(v)]
    print(f"  {k:12s} 有限占比 {np.isfinite(v).mean():.4f}  分位[1,50,99] "
          f"{np.percentile(f,[1,50,99]).round(5).tolist()}  sd {f.std():.5f}")
print("\n因子两两相关(全期展平, 只看结构不作判据):")
ks = list(F)
for i in range(len(ks)):
    row = "  " + ks[i][:12].ljust(12)
    for j in range(len(ks)):
        a, b = F[ks[i]].ravel(), F[ks[j]].ravel()
        m = np.isfinite(a) & np.isfinite(b)
        row += f"{np.corrcoef(a[m], b[m])[0,1]:+7.3f}"
    print(row)
np.savez_compressed(f"{E}/takerflow_factors.npz", ts=ts, symbols=np.array(syms, dtype=object),
                    **F, prereg="PREREG_takerflow_family_2026-08-09 43a76ddb")
print(f"\n落盘 {E}/takerflow_factors.npz")
