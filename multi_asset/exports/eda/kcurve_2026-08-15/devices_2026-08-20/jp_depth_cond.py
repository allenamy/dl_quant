"""条件路径判官: E[空头持仓后续7d盈亏 | 已深 -X%] — 渐进式挤压响应的地基曲线。

数据: daily_base.npz dret (BTC残差化日收益, 2022-26, D x N)。
空头深度: 入场日 t0, depth_k = p0/p_k - 1 (p=cumprod(1+r))。入场 stride 5d 半重叠。
事件: 首穿 -X 档(10/15/20/25/30)。度量: 之后 7d 的深度变化(=持有该仓后续盈亏/名义)。
幸存者声明: 下架截断删掉的是空头【盈利】路径(归零币), 对 hold 偏悲观 = 对止损有利的保守向。
分层: 逐年 + 流动性半分(dqv 中位), 触发档内报 n/均值/中位/P(再恶化5pp)/P(回弹5pp)/p10尾。
"""
import numpy as np
import json

d = np.load("/mnt/storage/private/work_hsy/w3lane/s30/daily_base.npz", allow_pickle=True)
ret = d["dret"]            # (D, N)
qv = d["dqv"] if "dqv" in d else None
dates = d["dates"] if "dates" in d else None
D, N = ret.shape
liq_lo = None
if qv is not None:
    med = np.nanmedian(np.nanmean(qv, axis=0))
    liq_lo = np.nanmean(qv, axis=0) < med   # 低流动半区

years = None
if dates is not None:
    years = np.array([int(str(x)[:4]) for x in dates])

TH = [-0.10, -0.15, -0.20, -0.25, -0.30]
H = 7          # 后续观察 7d
MAXHOLD = 60   # 每段最长模拟持仓
STRIDE = 5

out = {}
for th in TH:
    rows = []  # (year, is_lo, delta7, depth0)
    for j in range(N):
        r = ret[:, j]
        ok = np.isfinite(r)
        for t0 in range(0, D - H - 2, STRIDE):
            if not ok[t0]:
                continue
            p = 1.0
            hit = -1
            for k in range(t0, min(t0 + MAXHOLD, D)):
                if not ok[k]:
                    break
                p *= (1.0 + r[k])
                dep = 1.0 / p - 1.0
                if dep <= th:
                    hit = k
                    d0 = dep
                    break
            if hit < 0 or hit + H >= D:
                continue
            p2 = p
            fin = True
            for k in range(hit + 1, hit + 1 + H):
                if not ok[k]:
                    fin = False
                    break
                p2 *= (1.0 + r[k])
            if not fin:
                continue
            d7 = 1.0 / p2 - 1.0
            rows.append(((years[hit] if years is not None else 0),
                         (bool(liq_lo[j]) if liq_lo is not None else False),
                         d7 - d0, d0))
    if not rows:
        out[str(th)] = {"n": 0}
        continue
    arr = np.array([x[2] for x in rows])
    res = {"n": len(rows), "mean7": float(np.mean(arr)), "med7": float(np.median(arr)),
           "p_worse5": float(np.mean(arr <= -0.05)), "p_better5": float(np.mean(arr >= 0.05)),
           "p10": float(np.percentile(arr, 10)), "p90": float(np.percentile(arr, 90))}
    # 逐年均值
    if years is not None:
        ys = {}
        for y in sorted(set(x[0] for x in rows)):
            a = np.array([x[2] for x in rows if x[0] == y])
            ys[int(y)] = [len(a), float(np.mean(a))]
        res["by_year"] = ys
    if liq_lo is not None:
        for tag, flag in (("lo_liq", True), ("hi_liq", False)):
            a = np.array([x[2] for x in rows if x[1] == flag])
            res[tag] = [len(a), float(np.mean(a)) if len(a) else None]
    out[str(th)] = res

print(json.dumps(out, indent=1))
