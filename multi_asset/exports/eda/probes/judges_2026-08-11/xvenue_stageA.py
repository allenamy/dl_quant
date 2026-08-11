"""跨场所族 · 阶段 A(本机, 不依赖 jpline)
预注册 PREREG_crossvenue_2026-08-09  FROZEN 0b9f3e186aad7390... @ 10:37:03Z

★ 逐笔间隔归一(预注册 §1, 不可省): per_hour = fundingRate / interval_h,
  interval_h 由相邻结算时间戳间距逐笔算出。实测 4h=138005 / 8h=128941 笔, 各占一半。
A1 独立 IC · A2 换手 · A3 与 Binance funding 水平的相关(P1 前哨) · A4 与 size 的相关(P3)
门: A1 全期 rank-IC 的 day-block CI 下界 > 0  且  A4 |ρ| < 0.3  ⇒ 才进阶段 B
"""
import numpy as np, pandas as pd, datetime as dt, json
E = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/eda"

hl = np.load(f"{E}/hl_funding_hourly.npz", allow_pickle=True)
bn = np.load(f"{E}/bn_funding_settlements.npz", allow_pickle=True)
kl = np.load(f"{E}/bn_klines_1h.npz", allow_pickle=True)
bs = np.load(f"{E}/basis_premium_1h.npz", allow_pickle=True)
sz = np.load(f"{E}/bn_size_snapshot.npz", allow_pickle=True)

SYM = [str(s) for s in bn["symbols"]]                 # 81 个
COIN = {s: s[:-4] for s in SYM}
hl_c = {str(c): j for j, c in enumerate(hl["coins"])}
kl_s = {str(s): j for j, s in enumerate(kl["symbols"])}
bs_s = {str(s): j for j, s in enumerate(bs["symbols"])}
print(f"symbols {len(SYM)}")

# ── 统一到 klines 的逐小时网格 ──────────────────────────────────────────────
TS = kl["ts"].astype(np.int64)
T, N = len(TS), len(SYM)
tix = {int(t): i for i, t in enumerate(TS)}
CLOSE = np.full((T, N), np.nan)
for j, s in enumerate(SYM):
    CLOSE[:, j] = kl["CLOSE"][:, kl_s[s]]

def to_grid(src_ts, src_mat, colmap, how="ffill"):
    out = np.full((T, N), np.nan)
    st = src_ts.astype(np.int64)
    pos = np.searchsorted(TS, st)
    for j, s in enumerate(SYM):
        c = colmap.get(s if s in colmap else COIN[s])
        if c is None: continue
        v = src_mat[:, c].astype(np.float64)
        ok = np.isfinite(v) & (pos >= 0) & (pos < T)
        col = np.full(T, np.nan)
        col[pos[ok]] = v[ok]
        if how == "ffill":
            idx = np.where(np.isfinite(col), np.arange(T), 0)
            np.maximum.accumulate(idx, out=idx)
            col = col[idx]
        out[:, j] = col
    return out

HL_F = to_grid(hl["ts"], hl["FUNDING"], hl_c, "ffill")
HL_P = to_grid(hl["ts"], hl["PREMIUM"], hl_c, "ffill")
BN_PH = to_grid(bn["ts"], (bn["RATE"] / np.where(np.isfinite(bn["INTERVAL_H"]) & (bn["INTERVAL_H"] > 0),
                                                 bn["INTERVAL_H"], np.nan)),
                {s: j for j, s in enumerate([str(x) for x in bn["symbols"]])}, "ffill")
BN_PR = to_grid(bs["ts_hour"], bs["PREM"], bs_s, "ffill")
print(f"网格对齐 ✓  HL_F {np.isfinite(HL_F).mean():.3f}  BN_PH {np.isfinite(BN_PH).mean():.3f}  "
      f"BN_PR {np.isfinite(BN_PR).mean():.3f}  CLOSE {np.isfinite(CLOSE).mean():.3f}")

# ── 4h 锚点 ────────────────────────────────────────────────────────────────
hrs = pd.to_datetime(TS, unit="ms", utc=True)
AN = np.where((hrs.hour % 4 == 0))[0]
AN = AN[(AN + 4) < T]
print(f"4h 锚 {len(AN)}  {hrs[AN[0]]:%Y-%m-%d} → {hrs[AN[-1]]:%Y-%m-%d}")

def rc(x):
    o = np.full_like(x, np.nan); m = np.isfinite(x)
    if m.sum() < 5: return o
    r = pd.Series(x[m]).rank().values
    o[m] = 2*(r-1)/max(len(r)-1, 1) - 1.0
    o[m] -= o[m].mean()
    return o

def l1(x):
    s = np.nansum(np.abs(x)); return x/s if s > 1e-12 else x

SIZE = -np.log(np.where(np.isfinite(sz["quote_vol"]) & (sz["quote_vol"] > 0), sz["quote_vol"], np.nan))
rows = []
for i in AN:
    f = HL_F[i] - BN_PH[i]
    p = HL_P[i] - BN_PR[i]
    ret = CLOSE[i+4]/CLOSE[i] - 1.0
    ok = np.isfinite(ret)
    h1 = -1.0*rc(np.where(ok, f, np.nan)); h2 = -1.0*rc(np.where(ok, p, np.nan))
    m1 = np.isfinite(h1) & ok; m2 = np.isfinite(h2) & ok
    if m1.sum() < 20: continue
    def ic(w, m):
        return float(pd.Series(w[m]).corr(pd.Series(ret[m]), method="spearman")) if m.sum() >= 20 else np.nan
    rows.append({"i": int(i), "ts": int(TS[i]), "yr": hrs[i].year,
                 "n": int(m1.sum()), "ic_h1": ic(h1, m1), "ic_h2": ic(h2, m2),
                 "w1": l1(np.where(m1, h1, 0.0)), "w2": l1(np.where(m2, h2, 0.0)),
                 "corr_bnlevel": float(pd.Series(h1[m1]).corr(pd.Series(rc(np.where(m1, BN_PH[i], np.nan))[m1]), method="spearman")),
                 "corr_size": float(pd.Series(h1[m1]).corr(pd.Series(SIZE[m1]), method="spearman"))})
df = pd.DataFrame(rows)
print(f"\n可评锚 {len(df)}  名字/锚 {df.n.mean():.0f}")

def boot(v, nb=4000, bl=5):
    v = v[np.isfinite(v)]; rng = np.random.default_rng(2026); n = len(v); nb_ = int(np.ceil(n/bl))
    o = np.empty(nb)
    for k in range(nb):
        st = rng.integers(0, max(n-bl, 1), size=nb_)
        ix = (st[:, None]+np.arange(bl)[None, :]).ravel()[:n]; ix = ix[ix < n]
        o[k] = np.nanmean(v[ix])
    return float(np.percentile(o, 2.5)), float(np.percentile(o, 97.5))

print("\n===== A1 独立 rank-IC =====")
for k, nm in [("ic_h1", "H1 funding背离"), ("ic_h2", "H2 premium背离")]:
    v = df[k].values; lo, hi = boot(v)
    print(f"  {nm}: 全期 {np.nanmean(v):+.5f}  CI95 [{lo:+.5f},{hi:+.5f}]  "
          f"正号 {100*np.nanmean(v>0):.0f}%")
    for y, s in df.groupby("yr")[k]:
        print(f"      {y}: {s.mean():+.5f} (n={len(s)})")

print("\n===== A2 换手(8h cadence) =====")
for k in ("w1", "w2"):
    W = np.stack(df[k].values); tn = []
    for a in range(2, len(W), 2):
        tn.append(np.abs(W[a]-W[a-2]).sum()/2)
    print(f"  {k}: 换手/8h {np.mean(tn):.4f}")

print("\n===== A3 与 Binance funding 水平的相关(P1 前哨) =====")
print(f"  逐锚均值 ρ = {df.corr_bnlevel.mean():+.4f}  (预言: 差应抵消水平 ⇒ 低)")
print("\n===== A4 与 size 的相关(P3 专属门) =====")
print(f"  逐锚均值 ρ = {df.corr_size.mean():+.4f}  ⇒ "
      f"{'PASS (<0.3)' if abs(df.corr_size.mean()) < 0.3 else '★ FAIL —— 是 size 代理不是宽度'}")

lo1, hi1 = boot(df.ic_h1.values)
g1 = lo1 > 0; g4 = abs(df.corr_size.mean()) < 0.3
print(f"\n===== 阶段 A 门 =====\n  A1 CI 下界>0: {g1}   A4 |ρ|<0.3: {g4}   "
      f"⇒ {'进阶段 B' if (g1 and g4) else '★ 当场关闭, 不占 jpline 窗口'}")
json.dump({"n_anchors": int(len(df)), "ic_h1": float(df.ic_h1.mean()), "ic_h2": float(df.ic_h2.mean()),
           "ci_h1": [lo1, hi1], "corr_bnlevel": float(df.corr_bnlevel.mean()),
           "corr_size": float(df.corr_size.mean()), "gate_A1": bool(g1), "gate_A4": bool(g4)},
          open(f"{E}/xvenue_stageA.json", "w"), indent=1)
print("XVENUE_A_DONE")
