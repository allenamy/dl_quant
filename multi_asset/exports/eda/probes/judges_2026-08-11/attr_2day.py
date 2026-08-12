"""两日收益四项归因: β/市场 | 模型选择(β调整) | 持仓年龄拆分 | 运气分位。
原料: position_readback(逐锚逐名 notional+mid, 12天) + ic_monitor + daily_nav。
代数: pnl_i,t = notional_{i,t-1} × (mid_t/mid_{t-1} − 1); 逐名 β 用 12 天锚收益回归;
book_pnl_t = Σ = [mkt_t × Σ(w_iβ_i)]（β项） + [Σ w_i ε_i]（选择项）。"""
import json, glob, os
import numpy as np
from collections import defaultdict
RB = defaultdict(dict)  # anchor_ts -> sym -> (notional, mid)
for f in sorted(glob.glob(os.path.expanduser("~/dl_quant_live/state/live/pilot_log/*/position_readback.jsonl"))):
    for l in open(f):
        try: r = json.loads(l)
        except Exception: continue
        sym = r["symbol"]; no = r.get("venue_position_notional"); q = r.get("venue_position_qty")
        if no is None or not q: continue
        mid = abs(no/q) if q else None
        RB[round(r["anchor_ts"])][sym] = (no, mid)
anchors = sorted(RB)
print(f"readback 锚数 {len(anchors)}, 跨 {(anchors[-1]-anchors[0])/86400:.1f} 天")
# 逐锚逐名收益与 pnl
def rets_between(a0, a1):
    out = {}
    for s, (n0, m0) in RB[a0].items():
        if s in RB[a1] and m0 and RB[a1][s][1]:
            out[s] = (RB[a1][s][1]/m0 - 1, n0)
    return out
# 全史逐名 β(vs 等权市场)
sym_rets = defaultdict(list); mkt_series = []
for i in range(1, len(anchors)):
    rr = rets_between(anchors[i-1], anchors[i])
    if len(rr) < 30: mkt_series.append(np.nan); continue
    mkt = np.mean([v[0] for v in rr.values()]); mkt_series.append(mkt)
    for s, (ret, _) in rr.items(): sym_rets[s].append((i, ret, mkt))
beta = {}
for s, xs in sym_rets.items():
    if len(xs) >= 30:
        r_ = np.array([x[1] for x in xs]); m_ = np.array([x[2] for x in xs])
        beta[s] = float(np.cov(r_, m_)[0,1]/max(np.var(m_), 1e-12))
# 两日窗 = 最近 12 个锚间隔
W = 12
win = range(len(anchors)-W, len(anchors))
tot = bterm = sel = 0.0
name_pnl = defaultdict(float)
per_anchor = []
for i in win:
    a0, a1 = anchors[i-1], anchors[i]
    rr = rets_between(a0, a1)
    if len(rr) < 30: continue
    mkt = np.mean([v[0] for v in rr.values()])
    pa = pb = ps = 0.0
    for s, (ret, n0) in rr.items():
        pnl = n0*ret; b = beta.get(s, 1.0)
        pa += pnl; pb += n0*b*mkt; ps += n0*(ret - b*mkt)
        name_pnl[s] += pnl
    tot += pa; bterm += pb; sel += ps
    per_anchor.append((a1, pa, pb, ps, mkt))
import datetime as dt
print(f"\n== 窗口(近{W}锚 ≈2天) 四项归因 ==")
print(f"书 P&L 合计 {tot:+.1f} USDT = β/市场项 {bterm:+.1f} + 选择项(β调整) {sel:+.1f}")
print("逐锚:")
for a, pa, pb, ps, mkt in per_anchor:
    t = dt.datetime.utcfromtimestamp(a).strftime("%m-%d %H:%M")
    print(f"  {t}Z 书 {pa:+7.2f} = β {pb:+7.2f} + 选 {ps:+7.2f}  (市场 {mkt*100:+.2f}%)")
# 逐名贡献 + 年龄拆分(08-04 前已持有=legacy)
first_seen = {}
for a in anchors:
    for s in RB[a]:
        first_seen.setdefault(s, a)
cut = anchors[0] + 5*86400
top = sorted(name_pnl.items(), key=lambda x: -abs(x[1]))[:10]
print("\n窗口逐名 top10(±):")
leg = rec = 0.0
for s, v in sorted(name_pnl.items(), key=lambda x: x[1]):
    if first_seen.get(s, 0) <= cut: leg += v
    else: rec += v
for s, v in top:
    side = "空" if RB[anchors[-1]].get(s, (0,0))[0] < 0 else "多"
    age = "老仓" if first_seen.get(s, 0) <= cut else "新仓"
    print(f"  {s:14s} {side} {age} {v:+7.2f}")
print(f"年龄拆分: 老仓(≤08-09 已持) {leg:+.1f} vs 新仓 {rec:+.1f}")
# ic_monitor β-resid 窗口 vs 历史
ic = [json.loads(l) for l in open(os.path.expanduser("~/dl_quant_live/state/live/ic_monitor.jsonl"))]
br = [r["rank_ic_beta_resid"] for r in ic if r.get("rank_ic_beta_resid") is not None]
brw = br[-10:] if len(br) >= 10 else br
print(f"\nic_monitor β-resid: 窗口近10锚均值 {np.mean(brw):+.4f} vs 全史 {np.mean(br):+.4f}")
# 运气分位: 12锚合计 vs 离线分布(per-anchor sd≈37bps gross, 由夏普1.46反推)
gross = sum(abs(v[0]) for v in RB[anchors[-1]].values())
sd12 = 37e-4*gross*np.sqrt(12); mu12 = 1.154e-4*gross*12
z = (tot - mu12)/sd12
print(f"运气分位: 12锚合计 {tot:+.1f} vs 离线期望 {mu12:+.1f}±{sd12:.0f} ⇒ z={z:+.2f}")
# funding/fee 成分(daily_nav)
fund = fees = 0.0
for f in sorted(glob.glob(os.path.expanduser("~/dl_quant_live/state/live/pilot_log/*/daily_nav.jsonl")))[-3:]:
    rows = [json.loads(l) for l in open(f)]
    if rows:
        r = rows[-1].get("realised_by_type", {})
        fund += r.get("FUNDING_FEE", 0); fees += r.get("COMMISSION", 0)
print(f"近3日 funding {fund:+.2f} / 手续费 {fees:+.2f}")
print("ATTR_DONE")
