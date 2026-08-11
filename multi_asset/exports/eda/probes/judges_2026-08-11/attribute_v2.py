"""归因 v2 — 回答三个 v1 回答不了的问题, 每个都配一个能分辨的检验。

v1 的 L3(-0.634) 【不可用】: king/s2 是残差反转信号, 一个名字【因为刚跌】才被打高分,
而 ret 正是造成它的那段收益 ⇒ 负相关由构造保证。佐证: funding 腿(非反转)同数据下 +0.284。
⇒ 本文改用三个各自可分辨的量:

Q1 持仓拿了多久      —— EMA 上线后是否真在变长(降速的直接后果)
Q2 反转失效 vs beta  —— 两侧都逆行 = 反转失效签名; 单侧 = beta/单侧问题
Q3 ★ EMA 是否留住输家 —— 按持仓时长看每单位亏损。老仓更亏 ⇒ 降速锁住输家(真风险)
"""
import json
import os
import sys
import time

import numpy as np

R = os.path.expanduser("~/dl_quant_live")
sys.path.insert(0, os.path.join(R, "live"))
import binance_broker as BB  # noqa: E402

b = BB.BinanceBroker(mode="LIVE")
pr = [p for p in (b._request("GET", "/fapi/v3/positionRisk", signed=True) or [])
      if abs(float(p.get("notional") or 0)) > 1e-9]
now_ms = time.time() * 1000

rows = []
for p in pr:
    nt = float(p.get("notional") or 0)
    ep, mp = float(p.get("entryPrice") or 0), float(p.get("markPrice") or 0)
    up = float(p.get("unRealizedProfit") or 0)
    age_h = (now_ms - float(p.get("updateTime") or now_ms)) / 3.6e6
    rows.append({"sym": p["symbol"], "nt": nt, "up": up,
                 "ret": (mp / ep - 1.0) if ep > 0 else np.nan,
                 "age_h": age_h,
                 "unit": up / abs(nt) * 1e4 if nt else np.nan})

tot = sum(r["up"] for r in rows)
print(f"逐仓 {len(rows)} 名  总未实现 {tot:+.2f}")

ages = np.array([r["age_h"] for r in rows])
print("\n[Q1] 持仓时长(距该仓位最后一次变动)")
for lo, hi, lab in ((0, 1, "<1h(本锚刚动)"), (1, 4, "1-4h(上一锚)"),
                    (4, 12, "4-12h"), (12, 1e9, ">12h(老仓)")):
    m = (ages >= lo) & (ages < hi)
    if m.sum():
        u = np.array([r["up"] for r in rows])[m]
        g = np.array([abs(r["nt"]) for r in rows])[m]
        print(f"  {lab:16s} n={m.sum():3d}  毛 {g.sum():7,.0f}  未实现 {u.sum():+7.2f}  "
              f"= {u.sum()/g.sum()*1e4:+7.1f} bps/单位")

print("\n[Q2] 反转失效检验 —— 我方持仓方向下的收益(负=价格朝反方向走)")
sr = np.array([np.sign(r["nt"]) * r["ret"] * 1e4 for r in rows])
lon = np.array([r["nt"] > 0 for r in rows])
print(f"  全体  : 中位 {np.nanmedian(sr):+7.1f} bps  平均 {np.nanmean(sr):+7.1f}  逆行 {np.mean(sr < 0):.0%}")
print(f"  多头侧: 中位 {np.nanmedian(sr[lon]):+7.1f} bps  逆行 {np.mean(sr[lon] < 0):.0%}")
print(f"  空头侧: 中位 {np.nanmedian(sr[~lon]):+7.1f} bps  逆行 {np.mean(sr[~lon] < 0):.0%}")

print("\n[Q3] ★ EMA 是否留住输家 —— 每单位收益 vs 持仓时长")
u = np.array([r["unit"] for r in rows])
m = np.isfinite(u) & np.isfinite(ages)
if m.sum() > 20:
    ra = np.argsort(np.argsort(ages[m])).astype(float)
    ru = np.argsort(np.argsort(u[m])).astype(float)
    ra -= ra.mean(); ru -= ru.mean()
    d = np.sqrt((ra * ra).sum() * (ru * ru).sum())
    sp = float((ra * ru).sum() / d) if d > 0 else np.nan
    print(f"  Spearman(持仓时长, 每单位收益) = {sp:+.3f}   n={int(m.sum())}")
    verdict = ("★★ 显著负 ⇒ 老仓位亏更多 = 降速把输家锁住(真风险, 需处置)" if sp < -0.2
               else "≈0 ⇒ 亏损与持仓时长无关 ⇒ 不是 EMA 造成的" if abs(sp) <= 0.2
               else "正 ⇒ 老仓位反而更好")
    print(f"  {verdict}")

print("\n[Q4] 参考")
print(f"  若现在全平: 未实现 {tot:+.2f} 再扣单边成本 ~{4300*3.63/1e4:.2f} ⇒ 约 {tot - 4300*3.63/1e4:+.2f}")
json.dump({"n": len(rows), "total": tot,
           "median_signed_ret_bps": float(np.nanmedian(sr)),
           "adverse_frac": float(np.mean(sr < 0)),
           "adverse_long": float(np.mean(sr[lon] < 0)),
           "adverse_short": float(np.mean(sr[~lon] < 0))},
          open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "attribution_v2.json"), "w"), indent=1)
