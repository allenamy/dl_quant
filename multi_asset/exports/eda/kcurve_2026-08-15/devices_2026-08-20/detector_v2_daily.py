"""残差相关探测器 v2 日更仪表(压力战役 §9 接线件; 预警用途, 无任何交易行为).
拉 449 名 90d 日线 → β_BTC 残差 → 顶/底篮子残差相关(15d) + 截面离散度 + momLS 5d — 各带 90d 分位.
输出一行追加 daily_notes.md; 读数=仪表, 非触发器(尾部失明受据在案).
"""
import json, time, urllib.request, datetime
import numpy as np
SY = [s.strip() for s in open("/Users/haosiyu/wide_shadow/syms450.txt") if s.strip()]
def kl(sym):
    url = f"https://fapi.binance.com/fapi/v1/klines?symbol={sym}&interval=1d&limit=91"
    req = urllib.request.Request(url, headers={"User-Agent": "M"})
    k = json.load(urllib.request.urlopen(req, timeout=15))
    return {int(r[0] // 86400000): float(r[4]) for r in k}
allc = {}
for n, s in enumerate(SY):
    try: allc[s] = kl(s)
    except Exception: pass
    if n % 60 == 0: time.sleep(1.0)
days_all = sorted(set().union(*[set(c) for c in allc.values()]))
days = days_all[-91:-1]  # 丢当日未收盘残缺 bar(首读教训 08-20)
M = np.full((len(days), len(SY)), np.nan)
di = {d: i for i, d in enumerate(days)}
for j, s in enumerate(SY):
    c = allc.get(s, {})
    for a, b in zip(days, days[1:]):
        if a in c and b in c: M[di[b], j] = c[b] / c[a] - 1
iB = SY.index("BTCUSDT"); btc = np.nan_to_num(M[:, iB])
X = np.where(np.isfinite(M), M, 0.0)
beta = (X * btc[:, None]).sum(0) / max((btc ** 2).sum(), 1e-12)
Rr = np.where(np.isfinite(M), M - btc[:, None] * beta[None, :], np.nan)
mom = np.full_like(M, np.nan)
for i in range(32, len(days)):
    mom[i] = np.nansum(np.where(np.isfinite(M[i-32:i-2]), M[i-32:i-2], 0), 0)
topb, botb, ls = [np.full(len(days), np.nan) for _ in range(3)]
for i in range(33, len(days)):
    f, r = mom[i], Rr[i]
    ok = np.isfinite(f) & np.isfinite(r) & (np.abs(f) > 0)
    if ok.sum() < 60: continue
    q = np.nanpercentile(f[ok], [10, 90])
    topb[i] = np.nanmean(r[(f >= q[1]) & ok]); botb[i] = np.nanmean(r[(f <= q[0]) & ok])
    ls[i] = topb[i] - botb[i]
def roll_corr(a, b, w=15):
    out = np.full(len(a), np.nan)
    for i in range(w, len(a)):
        sa, sb = a[i-w:i], b[i-w:i]
        ok = np.isfinite(sa) & np.isfinite(sb)
        if ok.sum() >= 10: out[i] = np.corrcoef(sa[ok], sb[ok])[0, 1]
    return out
rc = roll_corr(topb, botb)
disp = np.nanstd(np.where(np.isfinite(Rr), Rr, np.nan), axis=1)
def pct(series, v):
    s = series[np.isfinite(series)]
    return round(float((s < v).mean() * 100)) if len(s) and np.isfinite(v) else None
today = datetime.datetime.now(datetime.timezone.utc).strftime("%m-%d")
bvol = np.full(len(days), np.nan)
ab = np.abs(np.nan_to_num(M[:, iB]))
for i in range(3, len(days)):
    w = ab[max(0, i-5):i+1]; bvol[i] = w.mean()
line = (f"- {today} 探测器v2: 残差顶底相关15d {rc[-1]:+.2f}(90d分位{pct(rc, rc[-1])}%) | "
        f"离散度 {disp[-1]*1e4:.0f}bps(分位{pct(disp, disp[-1])}%) | momLS 5d {np.nansum(ls[-5:])*1e4:+.0f}bps | "
        f"BTC波动分位 {pct(bvol, bvol[-1])}%(弱参考: OOS AUC~0.51, 全样本2.1×未迁移) | 覆盖 {sum(1 for c in allc.values() if len(c) > 60)} 名")
print(line)
open("/Users/haosiyu/wide_shadow/daily_notes.md", "a").write(line + "\n")
