"""杠杆 → 触 −25% 停机线概率(缺口 E, 08-24 杠杆门第四输入)。
输入: 逐锚净额序列(bps/锚, gross≈1 书口径); 杠杆 L ⇒ NAV 逐锚收益 ≈ L×net/1e4(线性近似, 忽略复利内差异); 块自助(42 锚块)×2000 条 1 年路径;
输出: 各 L 下 P(年内从峰值回撤触及 −25%) / P(触 −15%) / 年化中位与 p5。判据: 不设, 纯度量供 08-24 门。"""
import sys, json, numpy as np
src = sys.argv[1]; tag = sys.argv[2]; out = sys.argv[3]
MINY = int(sys.argv[4]) if len(sys.argv) > 4 else 0
LEVS = [float(x) for x in sys.argv[5].split(",")] if len(sys.argv) > 5 else [1.0, 2.0, 3.0, 3.5, 4.0]
import time
arr = np.load(src)
if arr.ndim == 2:
    yrs = np.array([time.gmtime(int(t)).tm_year for t in arr[:, 0]]); net = arr[:, 1][yrs >= MINY]
else:
    net = arr
net = net[np.isfinite(net)]
SHR = float(sys.argv[6]) if len(sys.argv) > 6 else 1.0
net = net - net.mean() * (1.0 - SHR)   # 均值折让(方差不变): 回放乐观度校正
rng = np.random.RandomState(11)
L_ = int(sys.argv[7]) if len(sys.argv) > 7 else 42; nb = len(net) // L_; NY = 2190; nblocks = NY // L_ + 1
res = {"block": L_, "mean_shrink": SHR, "min_year": MINY, "n_anchor": int(len(net)), "mean_bps": round(float(net.mean()), 3), "sd_bps": round(float(net.std()), 2)}
for lev in LEVS:
    hit25 = 0; hit15 = 0; ann = []
    for _ in range(2000):
        idx = rng.randint(0, nb, nblocks)
        path = np.concatenate([net[i*L_:(i+1)*L_] for i in idx])[:NY] * lev / 1e4
        cum = np.cumprod(1 + path); dd = cum / np.maximum.accumulate(cum) - 1
        hit25 += dd.min() <= -0.25; hit15 += dd.min() <= -0.15; ann.append(cum[-1] - 1)
    ann = np.array(ann)
    res[f"L{lev}"] = {"P_hit_-25%": round(hit25/2000, 3), "P_hit_-15%": round(hit15/2000, 3),
                      "ann_median": round(float(np.median(ann)), 3), "ann_p5": round(float(np.percentile(ann, 5)), 3), "ann_p95": round(float(np.percentile(ann, 95)), 3)}
print(tag, json.dumps(res))
json.dump(res, open(out, "w"), indent=1)
