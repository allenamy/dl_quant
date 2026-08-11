"""滚动 50 锚窗口给 M0−M3 定价: 近窗那个 +3.15 净优势在新模型自己的历史里多罕见。
同一装置(实盘 compose_book × 离线面板)内的分布, 不跨仪器; 近窗数字来自实盘面板, 跨装置引用需带声明。"""
import sys, os, json, numpy as np, pandas as pd
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset")
PD = "/mnt/storage/private/work_hsy/probe_artifacts"; sys.path.insert(0, PD)
import legs as LG
import engine.replay_fullhist as RF
W = {"king": .5952380952380952, "s2": .20238095238095238, "funding": .20238095238095238, "size": 0.}
src = RF.get_src(None, f"{PD}/king_pred_newgen.npz", f"{PD}/s2_pred_newgen.npz")
a, yr = RF._all_anchors(src)
FI, RVI = src.fund_idx, src.ch.index("rvol_24h")
def arm(al, lm):
    prev = None; net = np.zeros(len(a))
    for i, t in enumerate(a):
        ti = int(t); m = np.asarray(src.tradeable(ti))
        if m.dtype == bool: m = np.where(m)[0]
        rb = None if (al == 1. and lm == 0.) else {"alpha": al, "lambda": lm}
        r = LG.compose_book(src.king[ti, m].astype(float), src.s2[ti, m].astype(float),
                            src.CH[ti, m, FI].astype(float), np.ones(len(m)), weights=W,
                            rvol=src.CH[ti, m, RVI].astype(float) if rb else None, risk_budget=rb)
        w = np.asarray(r["target_w"], float); y = src.Y4[ti, m]; ok = np.isfinite(y)
        cur = dict(zip(m, w))
        trn = 0. if prev is None else sum(abs(cur.get(x, 0.)-prev.get(x, 0.)) for x in set(cur) | set(prev))
        net[i] = float(np.nansum(w[ok]*y[ok]))*1e4 - trn*2*3.115
        prev = cur
    return net
n0, n3 = arm(1., 0.), arm(.5, 1.)
d = n0 - n3
roll = pd.Series(d).rolling(50).mean().dropna().values
ry = np.asarray(yr)[49:]
print(f"滚动 50 锚 M0−M3 净差: 窗口数 {len(roll)}")
print(f"  M0 更好(>0)的窗口占比 = {(roll>0).mean():.4f}")
print(f"  分位 p50={np.percentile(roll,50):+.3f}  p90={np.percentile(roll,90):+.3f}  p95={np.percentile(roll,95):+.3f}  p99={np.percentile(roll,99):+.3f}  max={roll.max():+.3f}")
print(f"  ≥ +3.15 的窗口占比 = {(roll>=3.15).mean():.5f}")
print(f"  逐年 ≥+3.15 占比: ", {int(y): round(float((roll[ry==y]>=3.15).mean()),4) for y in sorted(set(ry))})
print(f"  逐年 >0 占比:     ", {int(y): round(float((roll[ry==y]>0).mean()),4) for y in sorted(set(ry))})
print("ROLLWIN_DONE")
