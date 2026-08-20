"""簇风险测量仪 P1a(2026-08-20 用户七点裁定): 名字集中度之外的【风险集中度】四读数.
① 空腿相关簇: 与空腿等权篮子残差相关>0.6 的空头名集合 → 簇敞口 %NAV;
② 簇已实现损失: 该簇近 1/3 日按当前持仓名义的实现移动(断路器 P1b 的标定原料);
③ 书 N_eff: 持仓加权残差相关阵参与率(独立赌注实数);
④ 低流通代理敞口: 观察清单惯犯 + 低成交额四分位空头占比。
仪表, 零书改动; 输出一行入 daily_notes; P1b 阈值由本仪器历史+压力受据标定后另行预注册。
"""
import json, time, urllib.request, datetime, glob
import numpy as np
P = sorted(glob.glob("/Users/haosiyu/dl_quant_live/state/live/pilot_log/*/position_readback.jsonl"))[-1]
rows = [json.loads(l) for l in open(P)]
last_anchor = max(r["anchor_ts"] for r in rows)
pos = {r["symbol"]: r["venue_position_notional"] for r in rows
       if r["anchor_ts"] == last_anchor and r.get("held") and abs(r.get("venue_position_notional", 0)) > 5}
NAV = 16100.0
try:
    nv = [json.loads(l) for l in open(sorted(glob.glob("/Users/haosiyu/dl_quant_live/state/live/pilot_log/*/daily_nav.jsonl"))[-1])]
    NAV = float(nv[-1]["nav"])
except Exception: pass
syms = sorted(pos)
def kl(sym, n=61):
    url = f"https://fapi.binance.com/fapi/v1/klines?symbol={sym}&interval=1d&limit={n}"
    k = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "M"}), timeout=15))
    return {int(r[0] // 86400000): (float(r[4]), float(r[7])) for r in k}
data = {}
for i, s in enumerate(syms):
    try: data[s] = kl(s)
    except Exception: pass
    if i % 50 == 0: time.sleep(0.8)
btc = kl("BTCUSDT")
days = sorted(set(btc))[-60:-1]  # 丢当日残缺 bar
def rets(c):
    return np.array([(c[b][0] / c[a][0] - 1) if (a in c and b in c) else np.nan for a, b in zip(days, days[1:])])
rb = rets(btc)
R, adv = {}, {}
for s in syms:
    if s in data and len(data[s]) > 40:
        r = rets(data[s])
        ok = np.isfinite(r) & np.isfinite(rb)
        beta = (r[ok] * rb[ok]).sum() / max((rb[ok] ** 2).sum(), 1e-12)
        R[s] = np.where(np.isfinite(r), r - beta * np.nan_to_num(rb), np.nan)
        adv[s] = np.nanmedian([data[s][d][1] for d in days if d in data[s]])
shorts = [s for s in syms if pos[s] < 0 and s in R]
if shorts:
    Sb = np.nanmean([R[s] for s in shorts], axis=0)
    corr2b = {}
    for s in shorts:
        ok = np.isfinite(R[s]) & np.isfinite(Sb)
        corr2b[s] = float(np.corrcoef(R[s][ok], Sb[ok])[0, 1]) if ok.sum() > 20 else 0.0
    cluster = [s for s in shorts if corr2b[s] > 0.6]
    cl_expo = sum(abs(pos[s]) for s in cluster) / NAV * 100
    m1 = sum(pos[s] * (data[s][days[-1]][0] / data[s][days[-2]][0] - 1) for s in cluster
             if days[-1] in data.get(s, {}) and days[-2] in data.get(s, {})) / NAV * 1e4
    d3a, d3b = days[-4], days[-1]
    m3 = sum(pos[s] * (data[s][d3b][0] / data[s][d3a][0] - 1) for s in cluster
             if d3b in data.get(s, {}) and d3a in data.get(s, {})) / NAV * 1e4
else:
    cluster, cl_expo, m1, m3 = [], 0, 0, 0
W = np.array([abs(pos[s]) for s in syms if s in R]); W = W / W.sum()
M = np.vstack([R[s] for s in syms if s in R])
Mw = M * np.sqrt(W)[:, None]
Mw = np.where(np.isfinite(Mw), Mw, 0)
C = np.nan_to_num(np.corrcoef(Mw), nan=0.0); np.fill_diagonal(C, 1.0)
ev = np.linalg.eigvalsh(C); ev = ev[ev > 1e-10]
neff = float(ev.sum() ** 2 / (ev ** 2).sum())
WATCH = {"RATSUSDT", "ETHFIUSDT", "CRVUSDT"}
qadv = np.percentile([adv[s] for s in adv], 25)
lf = [s for s in shorts if s in WATCH or adv.get(s, 9e9) < qadv]
lf_expo = sum(abs(pos[s]) for s in lf) / NAV * 100
today = datetime.datetime.now(datetime.timezone.utc).strftime("%m-%d")
line = (f"- {today} 簇风险仪P1a: 空腿相关簇 {len(cluster)}名/敞口{cl_expo:.1f}%NAV | "
        f"簇实现移动 1d{m1:+.0f}/3d{m3:+.0f}bps | 书N_eff {neff:.1f} | 低流通空头敞口{lf_expo:.1f}%NAV")
print(line)
print("  簇成员:", cluster[:12])
open("/Users/haosiyu/wide_shadow/daily_notes.md", "a").write(line + "\n")
