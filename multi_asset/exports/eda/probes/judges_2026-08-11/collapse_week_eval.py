"""y24 部署四关之② — 塌陷周实测 + perhead 分头保护终判。同一装置一次判两个候选。

★ 判读先于数字 (2026-08-06 16:4xZ 写):
  候选在役对照(同窗已测): 在役模型 fresh IC 全期 +0.085 / 最近 6 锚 +0.009; 残差 IC 最近 6 = −0.008。
  【关② 过线】h24_C fold_4 在最近 6 锚(塌陷窗)的 fresh IC ≥ +0.03 且比在役同窗高 ≥ +0.02
     ⇒ y24 在本周也活, 部署价值 = 常态增益 + 塌陷韧性, 进关③。
  【关② 不过但全期好】若塌陷窗 ≈0/负 而全 33 锚 ≥ 在役 ⇒ y24 不解决本周问题,
     部署价值降级为"常态增益"(仍可观, 判据回到 5 年 replay), 照进关③但预注册措辞降级。
  【perhead 分头保护判定】perhead fold_4 逐头: 塌陷窗残差 IC > +0.02 的活头 ≥1 ⇒ 目标分头保护成立
     (E1 是它的推广); 零活头 ⇒ 分头保护不成立, E1 的风格正交化目标升级为必需。
  n=6 的功率警告适用于一切"塌陷窗"读数 — 差值 < 0.05 均报"方向性", 不下断言。
装置: 与 paired_gen_backfill 同(本地实况面板 hours=1200, FLOOR=887, 4h 锚 ≥08-01, 成员掩码同产线)。
模型: fold_4 checkpoints + 训练器同路径导出的 fold_4 mu/sd (非在役 norm_stats — 面板同但折训练窗不同)。
"""
import os
import sys

import numpy as np

REPO = os.path.expanduser("~/dl_quant_live")
sys.path[:0] = [os.path.join(REPO, "signal"), os.path.join(REPO, "live"), REPO]
import fapi_source as FS          # noqa: E402
import inference as INF           # noqa: E402
import live_panel as LP           # noqa: E402
import panel_build as PB          # noqa: E402

S = os.path.dirname(os.path.abspath(__file__))
Z = np.load(os.path.join(S, "norm_stats_fold4.npz"))
MU, SD = Z["mu"], Z["sd"]

src = FS.FapiSource()
built = LP.build_live_panel(src, hours=1200, refresh=False)
CH, ts, syms = built["CH"], np.asarray(built["ts"]), built["symbols"]
CLOSE = np.asarray(built["CLOSE"], float)
N = len(syms)
try:
    tradable = set(src.perp_symbols())
except Exception:
    tradable = None
member = PB.derive_member(built["DVOL30"], built["CLOSE"], symbols=syms, tradable=tradable)

cands = {"h24_C": INF.FrozenModel("h24_C", os.path.join(S, "h24C_fold4.pt"), MU, SD),
         "h24_C_s2": INF.FrozenModel("h24_C_s2", os.path.join(S, "h24Cs2_fold4.pt"), MU, SD),
         "perhead": INF.FrozenModel("perhead", os.path.join(S, "perhead_fold4.pt"), MU, SD)}
deployed, _ = INF.load()

idx = [i for i in range(887, len(ts) - 4)
       if int(ts[i]) % (4 * 3600 * 1000) == 0 and int(ts[i]) >= 1785542400000]


def zr(x):
    m = np.isfinite(x)
    out = np.full(len(x), np.nan)
    if m.sum() < 3:
        return out
    r = np.argsort(np.argsort(x[m])).astype(float)
    out[m] = (r - r.mean()) / (r.std() + 1e-12)
    return out


def ic(a, b):
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 10:
        return np.nan
    return float(np.nanmean(zr(np.where(m, a, np.nan)) * zr(np.where(m, b, np.nan))))


res = {k: {"fresh": [], "proj": [], "resid": []} for k in list(cands) + ["deployed"]}
per_head = {k: {} for k in cands}
for i in idx:
    mask = member[i].astype(np.float32)
    if mask.sum() < 20:
        continue
    win = CH[i - INF.W + 1: i + 1].transpose(1, 0, 2)
    y = np.where(np.isfinite(CLOSE[i]) & np.isfinite(CLOSE[i + 4]) & (CLOSE[i] > 0),
                 CLOSE[i + 4] / CLOSE[i] - 1, np.nan)
    y[mask < 0.5] = np.nan
    style = -(CLOSE[i] / CLOSE[i - 168] - 1.0)
    style[mask < 0.5] = np.nan
    zs = zr(style)

    def comp_of(model):
        c, base, _ = model.composite(win, mask)
        v = np.full(N, np.nan)
        if c is not None:
            v[np.asarray(base)] = c
        return v

    for k, m_ in cands.items():
        v = comp_of(m_)
        zh = zr(v)
        mm = np.isfinite(zh) & np.isfinite(zs)
        beta = float(np.nanmean(zh[mm] * zs[mm]))
        res[k]["fresh"].append(ic(v, y))
        res[k]["proj"].append(ic(beta * zs, y))
        res[k]["resid"].append(ic(np.where(mm, zh - beta * zs, np.nan), y))
        sc = np.asarray(m_.factor_scores(win, mask))
        for h in range(sc.shape[1]):
            vv = sc[:, h].astype(float).copy()
            vv[mask < 0.5] = np.nan
            zhh = zr(vv)
            b2 = float(np.nanmean(zhh[mm] * zs[mm]))
            per_head[k].setdefault(h, []).append(
                ic(np.where(mm, zhh - b2 * zs, np.nan), y))
    # 在役合成(king+s2 等权 z), 与既有口径一致
    vk = comp_of(deployed["king"]); vs = comp_of(deployed["s2"])
    zc = np.nansum(np.vstack([zr(vk), zr(vs)]), axis=0)
    zc[mask < 0.5] = np.nan
    res["deployed"]["fresh"].append(ic(zc, y))

n = len(res["deployed"]["fresh"])
print(f"n_anchors={n}  (最近 6 = 塌陷窗)")
print(f"{'模型':12s} {'fresh全期':>9s} {'fresh近6':>9s} {'proj近6':>8s} {'resid近6':>9s}")
for k in ("deployed", "h24_C", "h24_C_s2", "perhead"):
    F = np.array(res[k]["fresh"], float)
    line = f"{k:12s} {np.nanmean(F):>+9.4f} {np.nanmean(F[-6:]):>+9.4f}"
    if res[k]["proj"]:
        line += (f" {np.nanmean(np.array(res[k]['proj'],float)[-6:]):>+8.4f}"
                 f" {np.nanmean(np.array(res[k]['resid'],float)[-6:]):>+9.4f}")
    print(line)
print("\nperhead 逐头塌陷窗残差 IC(分头保护判定, 活头线 +0.02):")
for k in ("perhead", "h24_C"):
    hs = {h: float(np.nanmean(np.array(v, float)[-6:])) for h, v in per_head[k].items()}
    alive = [h for h, x in hs.items() if x > 0.02]
    print(f"  {k}: {[round(x,4) for _,x in sorted(hs.items())]}  活头={alive or '无'}")
