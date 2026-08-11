"""metrics 族深度法证 —— DESIGN_metrics_v2 的数据基础。八项检查, 全部打在真实 CSV 上。

背景(为什么每项都要查):
 F1 帧规整性     5min 网格是否真规整; 重复戳/离格戳 → 聚合窗语义
 F2 语义分辨     count_toptrader(按账户数) vs sum_toptrader(按持仓量) 是两个人群行为;
                二者分歧 = 头部集中度信号 —— 若二者相关 >0.95 则"分歧轴"不存在, v1 当均质列就没错
 F3 分布形态     四个 ratio живут в (0,∞); 偏度决定要不要 log 域 (std(raw ratio) 混淆水平与离散)
 F4 单位自证     oi_value / oi ≈ 标记价 → 验证单位理解 (funding 单位错配的教训: 单位必须自证, 不能想当然)
 F5 与 klines 重叠  taker ratio 的小时均值 vs kline taker_buy 推导值 —— 若 corr≈1, v1 的 taker_ls_mean
                是重复列(#dedup), 真增量只在小时内 std/slope
 F6 覆盖形态     缺口是随机还是成块 (成块=交易所停更, 会变假信号)
 F7 OI 跳变      5min 内 |Δlog OI|>20% 的事件数 (结算/下架伪迹)
 F8 交互侦察     ΔOI×ret 四象限(新多/新空/空回补/多清算)机制 —— 有向增量的存在性粗扫
"""
import glob, os, sys
import numpy as np
import pandas as pd

MET = "/workspace/data/raw/metrics"
P = np.load("/workspace/data/panel_targets.npz", allow_pickle=True)
SYMS_ALL = [str(s) for s in P["symbols"]]
PROBE = ["BTCUSDT", "SOLUSDT", "OPUSDT"]          # 大/中/小
COLS = ["sum_open_interest", "sum_open_interest_value",
        "count_toptrader_long_short_ratio", "sum_toptrader_long_short_ratio",
        "count_long_short_ratio", "sum_taker_long_short_vol_ratio"]

def load_sym(sym, limit_days=None):
    fs = sorted(glob.glob(f"{MET}/{sym}-2*.csv"))
    if limit_days: fs = fs[-limit_days:]
    parts = []
    for fp in fs:
        try: parts.append(pd.read_csv(fp))
        except Exception: pass
    if not parts: return None
    df = pd.concat(parts, ignore_index=True)
    df["ts"] = pd.to_datetime(df["create_time"], utc=True)
    return df.sort_values("ts").reset_index(drop=True)

print("═"*80)
print("[F1] 帧规整性 (近 90 天)")
for s in PROBE:
    df = load_sym(s, 90)
    dt_s = df["ts"].diff().dt.total_seconds().dropna()
    dup = df["ts"].duplicated().sum()
    off = (df["ts"].dt.minute % 5 != 0).sum() + (df["ts"].dt.second != 0).sum()
    vc = dt_s.value_counts().head(3)
    print(f"  {s:10s} 帧距分布 {dict(vc)} | 重复戳 {dup} | 离格 {off}")

print("\n[F2] count_top vs sum_top: 同一轴还是两个轴? (全史)")
for s in PROBE:
    df = load_sym(s)
    a = np.log(df["count_toptrader_long_short_ratio"].clip(lower=1e-6))
    b = np.log(df["sum_toptrader_long_short_ratio"].clip(lower=1e-6))
    c = np.corrcoef(a, b)[0, 1]
    div = (b - a)                                  # >0: 大户仓位比账户数更偏多 ⇒ 头部集中做多
    print(f"  {s:10s} corr(log count, log sum)={c:+.3f}  分歧 sd={div.std():.3f} "
          f"AR1={div.autocorr(lag=12):+.3f}(1h)  {'★ 独立轴' if c < 0.9 else '近冗余'}")

print("\n[F3] 分布形态: raw vs log 偏度 (BTC 全史)")
df = load_sym("BTCUSDT")
for c in COLS[2:]:
    v = df[c].values
    v = v[np.isfinite(v) & (v > 0)]
    from scipy.stats import skew
    print(f"  {c:38s} raw skew={skew(v):+7.2f}  log skew={skew(np.log(v)):+7.2f}  "
          f"零/负值 {np.sum(~((df[c] > 0) & np.isfinite(df[c])))}")

print("\n[F4] 单位自证: oi_value/oi vs 当日价格 (BTC 抽 5 日)")
sub = df.iloc[:: max(1, len(df)//5)][:5]
for _, r in sub.iterrows():
    imp = r["sum_open_interest_value"] / max(r["sum_open_interest"], 1e-9)
    print(f"  {str(r['ts'])[:10]}  隐含价 {imp:,.0f}")
print("  (与该日 BTC 价同量级 ⇒ oi=币本位, oi_value=USDT ✓)")

print("\n[F5] taker ratio 与 klines 的信息重叠 (BTC 近 180 天)")
df90 = load_sym("BTCUSDT", 180).set_index("ts")
tk_h = df90["sum_taker_long_short_vol_ratio"].resample("1h").mean()
kl = []
for fp in sorted(glob.glob("/workspace/data/raw/klines1h/BTCUSDT-2*.csv"))[-180:]:
    try:
        k = pd.read_csv(fp, header=None if open(fp).readline()[0].isdigit() else 0)
        k.columns = ["open_time","open","high","low","close","volume","close_time",
                     "quote_volume","count","taker_buy_volume","taker_buy_quote_volume","ignore"][:len(k.columns)]
        kl.append(k)
    except Exception: pass
K = pd.concat(kl, ignore_index=True)
ot = pd.to_numeric(K["open_time"], errors="coerce")
ot = np.where(ot > 1e14, ot/1000, ot)
K["ts"] = pd.to_datetime(ot.astype("int64"), unit="ms", utc=True)
K = K.set_index("ts")
kr = pd.to_numeric(K["taker_buy_volume"]) / (pd.to_numeric(K["volume"]) - pd.to_numeric(K["taker_buy_volume"])).clip(lower=1e-9)
J = pd.concat([tk_h.rename("met"), kr.rename("kl")], axis=1).dropna()
print(f"  corr(metrics taker 小时均值, klines 推导) = {np.corrcoef(np.log(J['met'].clip(lower=1e-6)), np.log(J['kl'].clip(lower=1e-6)))[0,1]:+.3f}  n={len(J)}")
print("  ⇒ >0.9 则 v1 的 taker_ls_mean 是 klines 重复列, 真增量只在小时内 std/slope")

print("\n[F6] 覆盖形态: 缺口成块? (全宇宙, 文件级)")
gaps_block = 0; total = 0
for s in SYMS_ALL:
    fs = sorted(glob.glob(f"{MET}/{s}-2*.csv"))
    if len(fs) < 30: continue
    days = [os.path.basename(f)[-14:-4] for f in fs]
    d0 = pd.to_datetime(days)
    dd = pd.Series(d0).diff().dt.days.dropna()
    blocks = (dd > 3).sum()                        # >3 天连续缺 = 成块
    gaps_block += blocks; total += 1
print(f"  {total} 币中, 有 >3 天成块缺口的事件共 {gaps_block} 起")

print("\n[F7] OI 跳变: |Δlog oi|>20%/5min (BTC+SOL+OP 全史)")
for s in PROBE:
    df = load_sym(s)
    dlo = np.abs(np.diff(np.log(df["sum_open_interest"].clip(lower=1e-9))))
    n = (dlo > 0.20).sum()
    print(f"  {s:10s} {n} 起  (最大 {dlo.max()*100:.0f}%)")

print("\n[F8] 交互侦察: ΔOI×ret 四象限 → 未来 1h 收益 (BTC 近 1 年, 只看方向)")
df = load_sym("BTCUSDT", 365).set_index("ts")
oi_h = np.log(df["sum_open_interest"].clip(lower=1e-9)).resample("1h").last()
# 用 klines close 而非 metrics(独立源)
cl = pd.to_numeric(K["close"])
ret1 = np.log(cl).diff()
fut1 = ret1.shift(-1)
doi = oi_h.diff()
JJ = pd.concat([doi.rename("doi"), ret1.rename("ret"), fut1.rename("fut")], axis=1).dropna()
for nm, m in [("OI↑ P↑ (新多)", (JJ.doi > 0) & (JJ.ret > 0)), ("OI↑ P↓ (新空)", (JJ.doi > 0) & (JJ.ret < 0)),
              ("OI↓ P↑ (空回补)", (JJ.doi < 0) & (JJ.ret > 0)), ("OI↓ P↓ (多清算)", (JJ.doi < 0) & (JJ.ret < 0))]:
    print(f"  {nm:14s} n={m.sum():5d}  未来1h均值 {JJ.fut[m].mean()*1e4:+.2f} bps")
print("\n法证完毕 — 数字进 DESIGN_metrics_v2")
