"""未实现盈亏的逐名归因 — 拆到"是模型错了还是市场动了"。

口径:
  · 逐仓 unrealizedProfit 来自 /fapi/v3/account 的 positions 数组(场所真值, 非我方重建)。
  · 分数来自 state/live/preds_latest.json(产出 12:00Z 锚那一份, 与当前持仓同源)。
  · 权重来自 state/live/harvest_ema.json 的 EMA 后状态(= 书真正想持有的)。
分解四层:
  L1 多空两侧    —— 中性书两侧应大致相抵; 单侧主导 = beta 泄漏或单侧选股失败
  L2 beta 成分   —— 净敞口 × 市场平均涨跌; 这部分不是 alpha 的锅
  L3 分数一致性  —— 未实现与【我们自己的分数】的秩相关。负 = 模型指反了(真 alpha 失败);
                    ≈0 = 与模型无关(市场/特异噪声)
  L4 集中度      —— 前 N 名占多少; 若少数名字主导, 就不是"整体信号失效"
"""
import json
import os
import sys

import numpy as np

R = os.path.expanduser("~/dl_quant_live")
sys.path.insert(0, os.path.join(R, "live"))
import binance_broker as BB  # noqa: E402

b = BB.BinanceBroker(mode="LIVE")
acct = b._request("GET", "/fapi/v3/account", signed=True)
# ★ /fapi/v3/account 的 positions 数组【不带】 entryPrice/markPrice ⇒ 无法算逐名收益。
#   positionRisk 才带(entryPrice/markPrice/breakEvenPrice), 且 unRealizedProfit 大小写不同。
pos = [p for p in (b._request("GET", "/fapi/v3/positionRisk", signed=True) or [])
       if abs(float(p.get("notional") or 0)) > 1e-9]
print(f"逐仓 {len(pos)} 名   总未实现 = {float(acct.get('totalUnrealizedProfit',0)):+.2f} USDT"
      f"   钱包 {float(acct.get('totalWalletBalance',0)):,.2f}")

P = json.load(open(os.path.join(R, "state", "live", "preds_latest.json")))
king, s2, fund = P.get("king") or {}, P.get("s2") or {}, P.get("funding_ema") or {}
HZ = (json.load(open(os.path.join(R, "state", "live", "harvest_ema.json"))) or {}).get("state") or {}

rows = []
for p in pos:
    s = p["symbol"]
    nt = float(p.get("notional") or 0.0)
    up = float(p.get("unRealizedProfit") or p.get("unrealizedProfit") or 0.0)
    ep, mp = float(p.get("entryPrice") or 0), float(p.get("markPrice") or 0)
    ret = (mp / ep - 1.0) if ep > 0 else np.nan          # 持仓期价格变动
    bev = float(p.get("breakEvenPrice") or 0)
    rows.append({"sym": s, "notional": nt, "upnl": up, "ret": ret,
                 "entry": ep, "mark": mp, "bev": bev,
                 "king": king.get(s), "s2": s2.get(s), "fund": fund.get(s),
                 "w": HZ.get(s)})

tot = sum(r["upnl"] for r in rows)
lon = [r for r in rows if r["notional"] > 0]
sho = [r for r in rows if r["notional"] < 0]
gl, gs = sum(r["notional"] for r in lon), sum(-r["notional"] for r in sho)
pl, ps = sum(r["upnl"] for r in lon), sum(r["upnl"] for r in sho)

print(f"\n[L1] 多空两侧")
print(f"  多头 {len(lon):3d} 名  毛 {gl:8,.0f}  未实现 {pl:+8.2f}  = 该侧毛的 {pl/gl*1e4:+7.1f} bps")
print(f"  空头 {len(sho):3d} 名  毛 {gs:8,.0f}  未实现 {ps:+8.2f}  = 该侧毛的 {ps/gs*1e4:+7.1f} bps")
print(f"  合计 {tot:+.2f}   净敞口 {gl-gs:+,.0f} ({(gl-gs)/(gl+gs)*100:+.2f}% of gross)")

# L2: beta 成分 = 净敞口 × 平均持仓期收益(等权市场代理)
mkt = float(np.nanmean([r["ret"] for r in rows]))
beta_pnl = (gl - gs) * mkt
print(f"\n[L2] beta 成分")
print(f"  持仓期市场平均收益(等权 {len(rows)} 名) = {mkt*1e4:+.1f} bps")
print(f"  净敞口 × 市场 = {beta_pnl:+.2f} USDT  ⇒ 占总未实现的 {beta_pnl/tot*100 if tot else 0:.0f}%")
print(f"  ⇒ 剩余(非 beta) = {tot-beta_pnl:+.2f}")


def spearman(a, b_):
    a, b_ = np.asarray(a, float), np.asarray(b_, float)
    m = np.isfinite(a) & np.isfinite(b_)
    if m.sum() < 10:
        return np.nan
    ra = np.argsort(np.argsort(a[m])).astype(float)
    rb = np.argsort(np.argsort(b_[m])).astype(float)
    ra -= ra.mean(); rb -= rb.mean()
    d = np.sqrt((ra * ra).sum() * (rb * rb).sum())
    return float((ra * rb).sum() / d) if d > 0 else np.nan


# L3: 未实现 与 我们自己的分数/权重 的一致性
# 每单位敞口的收益 = upnl / |notional| —— 去掉仓位大小, 只看方向对不对
per_unit = [r["upnl"] / abs(r["notional"]) * 1e4 if r["notional"] else np.nan for r in rows]
signed_ret = [np.sign(r["notional"]) * r["ret"] * 1e4 for r in rows]   # 我方持仓方向下的收益
print(f"\n[L3] 与我们自己分数的一致性  (per-unit 收益 bps: "
      f"mean {np.nanmean(per_unit):+.1f}, 中位 {np.nanmedian(per_unit):+.1f})")
for nm, key in (("king", "king"), ("s2", "s2"), ("funding", "fund"), ("最终权重 w", "w")):
    sc = [r[key] for r in rows]
    if sum(1 for x in sc if x is not None) < 10:
        print(f"  {nm:10s} (分数缺失, 跳过)"); continue
    sp = spearman(sc, [r["ret"] for r in rows])
    print(f"  {nm:10s} Spearman(分数, 持仓期收益) = {sp:+.3f}   "
          f"{'← 指反了' if sp<-0.05 else '← 指对了' if sp>0.05 else '← 与收益无关'}")

# L4: 集中度
rows.sort(key=lambda r: r["upnl"])
w5 = sum(r["upnl"] for r in rows[:5])
b5 = sum(r["upnl"] for r in rows[-5:])
neg = [r for r in rows if r["upnl"] < 0]
print(f"\n[L4] 集中度")
print(f"  亏损名 {len(neg)}/{len(rows)}   最亏 5 名合计 {w5:+.2f} = 总额的 {w5/tot*100 if tot else 0:.0f}%")
print(f"  最赚 5 名合计 {b5:+.2f}")
print(f"  最亏 8:")
for r in rows[:8]:
    side = "多" if r["notional"] > 0 else "空"
    print(f"    {r['sym']:14s} {side} 名义{abs(r['notional']):6,.0f}  未实现{r['upnl']:+7.2f}  "
          f"价格变动{r['ret']*1e4:+7.1f}bps  king={r['king'] if r['king'] is None else round(r['king'],3)}")
print(f"  最赚 5:")
for r in rows[-5:]:
    side = "多" if r["notional"] > 0 else "空"
    print(f"    {r['sym']:14s} {side} 名义{abs(r['notional']):6,.0f}  未实现{r['upnl']:+7.2f}  "
          f"价格变动{r['ret']*1e4:+7.1f}bps")

json.dump({"total": tot, "long": {"n": len(lon), "gross": gl, "upnl": pl},
           "short": {"n": len(sho), "gross": gs, "upnl": ps},
           "mkt_ret_bps": mkt * 1e4, "beta_pnl": beta_pnl,
           "rows": [{k: (None if isinstance(v, float) and not np.isfinite(v) else v)
                     for k, v in r.items()} for r in rows]},
          open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "unrealized_attribution.json"), "w"), indent=1)
