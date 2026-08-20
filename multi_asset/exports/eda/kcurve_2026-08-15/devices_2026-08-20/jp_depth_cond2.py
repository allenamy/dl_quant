"""v2: 度量改为 -fwd_ret(触发时名义口径, 有界) — v1 的 1/p 凸性把死币窗炸成 +144% 假均值。
条件A: 慢累积深度首穿 -X(stride5 入场模拟)。条件B: 快挤压 = 3d 价格 +8%/+15%(逆空头)。
输出: E[持有后续 1/3/7d 盈亏/名义], 中位, P(worse5/better5), p10, 逐年均值(7d), 流动性半分。
"""
import numpy as np
import json

d = np.load("/mnt/storage/private/work_hsy/w3lane/s30/daily_base.npz", allow_pickle=True)
ret = d["dret"]
qv = d["dqv"] if "dqv" in d else None
dates = d["dates"] if "dates" in d else None
D, N = ret.shape
liq_lo = (np.nanmean(qv, axis=0) < np.nanmedian(np.nanmean(qv, axis=0))) if qv is not None else np.zeros(N, bool)
years = np.array([int(str(x)[:4]) for x in dates]) if dates is not None else np.zeros(D, int)
logr = np.log1p(np.where(np.isfinite(ret), np.clip(ret, -0.95, 5.0), 0.0))
okm = np.isfinite(ret)


def fwd(j, t, h):
    if t + h >= D or not okm[t + 1:t + 1 + h, j].all():
        return None
    return float(np.expm1(logr[t + 1:t + 1 + h, j].sum()))


def stats(evs):
    if len(evs) < 30:
        return {"n": len(evs)}
    a7 = np.array([e[2] for e in evs])
    r = {"n": len(evs)}
    for h, idx in (("1d", 0), ("3d", 1), ("7d", 2)):
        a = np.array([e[idx] for e in evs])
        r[f"hold{h}"] = round(float(np.mean(-a)), 4)   # 空头持有盈亏 = -fwd_ret
    r["med7"] = round(float(np.median(-a7)), 4)
    r["p_worse5"] = round(float(np.mean(-a7 <= -0.05)), 3)
    r["p_better5"] = round(float(np.mean(-a7 >= 0.05)), 3)
    r["p10"] = round(float(np.percentile(-a7, 10)), 3)
    ys = {}
    for y in sorted(set(e[3] for e in evs)):
        a = np.array([-e[2] for e in evs if e[3] == y])
        if len(a) >= 10:
            ys[int(y)] = [len(a), round(float(np.mean(a)), 4)]
    r["by_year7"] = ys
    for tag, fl in (("lo", True), ("hi", False)):
        a = np.array([-e[2] for e in evs if e[4] == fl])
        if len(a):
            r[f"liq_{tag}7"] = [len(a), round(float(np.mean(a)), 4)]
    return r


out = {}
# 条件A: 慢累积深度
for th in (-0.15, -0.25):
    evs = []
    for j in range(N):
        for t0 in range(0, D - 9, 5):
            if not okm[t0, j]:
                continue
            lp = 0.0
            for k in range(t0, min(t0 + 60, D)):
                if not okm[k, j]:
                    break
                lp += logr[k, j]
                if np.expm1(-lp) <= th:   # depth = 1/p-1
                    f1, f3, f7 = fwd(j, k, 1), fwd(j, k, 3), fwd(j, k, 7)
                    if f7 is not None and f1 is not None and f3 is not None:
                        evs.append((f1, f3, f7, years[k], bool(liq_lo[j])))
                    break
    out[f"A_depth{th}"] = stats(evs)

# 条件B: 快挤压 3d pump(带 3d 冷却去重叠)
for pump in (0.08, 0.15):
    evs = []
    for j in range(N):
        last = -99
        for t in range(3, D - 8):
            if t - last < 3 or not okm[t - 2:t + 1, j].all():
                continue
            r3 = np.expm1(logr[t - 2:t + 1, j].sum())
            if r3 >= pump:
                f1, f3, f7 = fwd(j, t, 1), fwd(j, t, 3), fwd(j, t, 7)
                if f7 is not None and f1 is not None and f3 is not None:
                    evs.append((f1, f3, f7, years[t], bool(liq_lo[j])))
                    last = t
    out[f"B_pump{pump}"] = stats(evs)

print(json.dumps(out, indent=None, separators=(",", ":")))
