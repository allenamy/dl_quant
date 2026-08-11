"""深挖: IC 塌陷的【原因】而非现象 — 四台仪器, 每台对应一个可证伪机制。

M1 信号时效衰减 + EMA 截面兼容性(用户假设: "调整后的截面还是模型预期的截面吗")
   fresh IC vs lag1/lag2 IC vs 0.7·lag1+0.3·fresh 混合 IC。
   若 lag1 在近期归零/转负 ⇒ EMA 书骑在过期信号上(与模型不兼容·此 regime); 若 lag 保持
   fresh 的 ~60% ⇒ 兼容, 塌陷与 EMA 无关。
M2 逐资产分解(最近 6 锚 新−旧 差距的贡献): 集中在少数名字还是普遍?
   那些名字是高波动/高 beta/新上市吗? — 分别检验 BAB 倾斜机制(已登记: 干净模型 BAB 倾斜 2.3×)
   与 训练覆盖机制(新模型见过 7 月, 旧没有)。
M3 逐特征服务审计: 当前面板在新/旧两套 mu/sd 下的 |z| 与 clip 饱和率 —
   找机械性服务缺陷(某通道在新统计下分布错位)。重点: ch31(causal 替换), funding 族, ch86(x_rvol 历史地雷)。
M4 regime 分桶: 按锚点横截面波动分半, 新旧差距在哪一半扩大。
"""
import json
import os
import sys

import numpy as np

REPO = os.path.expanduser("~/dl_quant_live")
sys.path[:0] = [os.path.join(REPO, "signal"), os.path.join(REPO, "live"), REPO]

import fapi_source as FS          # noqa: E402
import inference as INF           # noqa: E402
import live_panel as LP           # noqa: E402
import panel_build as PB          # noqa: E402

OLD = os.path.join(REPO, "rollback_batch1_20260804T145921Z", "checkpoints")
NEW = os.path.join(REPO, "checkpoints")
CUTOFF_MS = 1785542400000         # 2026-08-01T00:00Z
FLOOR = 887

src = FS.FapiSource()
built = LP.build_live_panel(src, hours=1200, refresh=False, progress=None)
CH, ts, syms = built["CH"], np.asarray(built["ts"]), built["symbols"]
CLOSE = np.asarray(built["CLOSE"], float)
N = len(syms)
tradable = None
try:
    tradable = set(src.perp_symbols())
except Exception:
    pass
member = PB.derive_member(built["DVOL30"], built["CLOSE"], symbols=syms, tradable=tradable)

gens = {}
for tag, d in (("new", NEW), ("old", OLD)):
    gens[tag], _ = INF.load(stats_path=os.path.join(d, "norm_stats.npz"), ckpt_dir=d)

idx = [i for i in range(FLOOR, len(ts) - 4)
       if int(ts[i]) % (4 * 3600 * 1000) == 0 and int(ts[i]) >= CUTOFF_MS]


def zr(x):
    m = np.isfinite(x)
    out = np.full(len(x), np.nan)
    r = np.argsort(np.argsort(x[m])).astype(float)
    r = (r - r.mean()) / (r.std() + 1e-12)
    out[m] = r
    return out


# ── 打分并缓存分数向量 ──────────────────────────────────────────────────────────
S = {"new": {}, "old": {}}                 # tag -> anchor_i -> composite z over syms
Y = {}                                     # anchor_i -> realized +4h ret (members only)
for i in idx:
    mask = member[i].astype(np.float32)
    if mask.sum() < 20:
        continue
    win = CH[i - INF.W + 1: i + 1].transpose(1, 0, 2)
    y = np.full(N, np.nan)
    c0, c1 = CLOSE[i], CLOSE[i + 4]
    ok = np.isfinite(c0) & np.isfinite(c1) & (c0 > 0)
    y[ok] = c1[ok] / c0[ok] - 1.0
    y[mask < 0.5] = np.nan
    Y[i] = y
    for tag in ("new", "old"):
        comp = np.full(N, np.nan)
        zs = []
        for leg in ("king", "s2"):
            c, base, _ = gens[tag][leg].composite(win, mask)
            v = np.full(N, np.nan)
            if c is not None:
                v[np.asarray(base)] = c
            vm = v[mask > 0.5]
            s = np.nanstd(vm)
            zs.append((vm - np.nanmean(vm)) / s if s > 0 else vm * np.nan)
        comp[mask > 0.5] = np.nansum(np.vstack(zs), axis=0)
        S[tag][i] = comp

anchors = sorted(Y.keys())
n_anch = len(anchors)


def ic(a, b):
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 10:
        return np.nan
    return float(np.nanmean(zr(np.where(m, a, np.nan)) * zr(np.where(m, b, np.nan))))


# ── M1: 时效衰减 ────────────────────────────────────────────────────────────────
print("=" * 78)
print("[M1] 信号时效衰减 — EMA 截面兼容性")
rows = []
for k, i in enumerate(anchors):
    fresh = ic(S["new"][i], Y[i])
    l1 = ic(S["new"][anchors[k - 1]], Y[i]) if k >= 1 else np.nan
    l2 = ic(S["new"][anchors[k - 2]], Y[i]) if k >= 2 else np.nan
    blend = (ic(0.7 * S["new"][anchors[k - 1]] + 0.3 * S["new"][i], Y[i])
             if k >= 1 else np.nan)
    rows.append((i, fresh, l1, l2, blend))
A = np.array([[r[1], r[2], r[3], r[4]] for r in rows], float)
lab = ["fresh", "lag1(4h 前的分数)", "lag2(8h 前)", "0.7·lag1+0.3·fresh(≈EMA 书)"]
for j, L in enumerate(lab):
    col = A[:, j]
    full = np.nanmean(col)
    rec = np.nanmean(col[-6:])
    print(f"  {L:28s} 全 {n_anch} 锚 {full:+.4f}   最近 6 锚 {rec:+.4f}")
print("  ⇒ 判读: lag1/fresh 比值 = 信号 4h 后还剩多少;"
      f"  全期 {np.nanmean(A[:,1])/np.nanmean(A[:,0]):+.0%}, "
      f"最近 6 锚 {'N/A' if abs(np.nanmean(A[-6:,0]))<1e-4 else f'{np.nanmean(A[-6:,1])/np.nanmean(A[-6:,0]):+.0%}'}")

# ── M2: 逐资产分解(最近 6 锚 新−旧) ────────────────────────────────────────────
print("\n" + "=" * 78)
print("[M2] 逐资产: 最近 6 锚, 新−旧 IC 差距由谁贡献")
recent = anchors[-6:]
contrib = np.zeros(N)
cnt = np.zeros(N)
for i in recent:
    zy = zr(Y[i])
    for tag, sgn in (("new", +1), ("old", -1)):
        zs_ = zr(S[tag][i])
        c = zs_ * zy
        m = np.isfinite(c)
        contrib[m] += sgn * c[m] / m.sum()
        cnt[m] += 0.5
# 资产特征: 波动/beta/上市时点
ret4 = CLOSE[4:] / CLOSE[:-4] - 1.0
mkt = np.nanmean(ret4, axis=1)
vol = np.nanstd(ret4, axis=0)
beta = np.full(N, np.nan)
for j in range(N):
    a_ = ret4[:, j]
    m = np.isfinite(a_) & np.isfinite(mkt)
    if m.sum() > 50:
        beta[j] = float(np.cov(a_[m], mkt[m])[0, 1] / (np.var(mkt[m]) + 1e-12))
first_seen = np.array([int(np.argmax(np.isfinite(CLOSE[:, j]))) if np.isfinite(CLOSE[:, j]).any()
                       else 10**9 for j in range(N)])
is_new_listing = first_seen > 24            # 面板开头(≈06-17)之后才出现

order = np.argsort(contrib)
print("  新模型输给旧模型最多的 10 名(6 锚合计贡献):")
print("  名字            贡献差    波动分位  beta   新上市?")
vq = np.argsort(np.argsort(np.where(np.isfinite(vol), vol, -1))) / max(N - 1, 1)
for j in order[:10]:
    if cnt[j] == 0:
        continue
    print(f"  {syms[j]:14s} {contrib[j]:+.4f}   {vq[j]:.0%}       "
          f"{beta[j]:+.2f}  {'是' if is_new_listing[j] else ''}")
print("  新模型赢最多的 5 名:")
for j in order[::-1][:5]:
    if cnt[j] == 0:
        continue
    print(f"  {syms[j]:14s} {contrib[j]:+.4f}   {vq[j]:.0%}       {beta[j]:+.2f}"
          f"  {'是' if is_new_listing[j] else ''}")
neg_share = float(-contrib[order[:10]].sum() / max(-contrib[contrib < 0].sum(), 1e-9))
print(f"  集中度: 最差 10 名占全部负贡献的 {neg_share:.0%}"
      f"  (高⇒个别名字问题, 低⇒普遍性)")

# 分桶: 波动 tercile × 新旧差距
print("\n  按波动 tercile 的 新−旧 差距(最近 6 锚, 每桶平均逐名贡献×N):")
tq = np.digitize(vq, [1 / 3, 2 / 3])
for b, nm in ((0, "低波动"), (1, "中"), (2, "高波动")):
    m = (tq == b) & (cnt > 0)
    print(f"    {nm:6s} n={m.sum():3d}  合计贡献差 {contrib[m].sum():+.4f}")
bm = np.digitize(np.argsort(np.argsort(np.where(np.isfinite(beta), beta, 0))) / max(N - 1, 1),
                 [1 / 3, 2 / 3])
print("  按 beta tercile:")
for b, nm in ((0, "低β"), (1, "中"), (2, "高β")):
    m = (bm == b) & (cnt > 0)
    print(f"    {nm:6s} n={m.sum():3d}  合计贡献差 {contrib[m].sum():+.4f}")

# ── M3: 逐特征服务审计 ─────────────────────────────────────────────────────────
print("\n" + "=" * 78)
print("[M3] 逐特征: 当前窗口在两套 norm_stats 下的分布 — 找机械性错位")
zs_stats = {}
i_last = anchors[-1]
win = CH[i_last - INF.W + 1: i_last + 1]          # (W, N, C)
for tag, d in (("new", NEW), ("old", OLD)):
    z = np.load(os.path.join(d, "norm_stats.npz"), allow_pickle=True)
    mu, sd = z["king_mu"], z["king_sd"]
    X = (np.nan_to_num(win) - mu[None, None, :]) / sd[None, None, :]
    zs_stats[tag] = {"mean_abs": np.nanmean(np.abs(X), axis=(0, 1)),
                     "sat": np.mean(np.abs(X) >= 10.0, axis=(0, 1)),
                     "mu": mu, "sd": sd}
d_mu = np.abs(zs_stats["new"]["mu"] - zs_stats["old"]["mu"]) / (np.abs(zs_stats["old"]["sd"]) + 1e-12)
print("  ch  new|z|均值  new饱和%   old|z|均值  old饱和%   |Δmu|/sd_old")
worst = np.argsort(-(zs_stats["new"]["sat"] - zs_stats["old"]["sat"]))[:8]
for c in worst:
    print(f"  {c:3d}   {zs_stats['new']['mean_abs'][c]:7.2f}  {zs_stats['new']['sat'][c]:7.2%}"
          f"   {zs_stats['old']['mean_abs'][c]:7.2f}  {zs_stats['old']['sat'][c]:7.2%}"
          f"   {d_mu[c]:8.2f}")
flag = [int(c) for c in range(win.shape[2])
        if zs_stats["new"]["sat"][c] > 0.02 and zs_stats["new"]["sat"][c] > 3 * zs_stats["old"]["sat"][c]]
print(f"  ★ 新统计下饱和>2% 且 ≥3× 旧统计的通道: {flag or '无'}")
big_shift = [int(c) for c in np.argsort(-d_mu)[:5]]
print(f"  mu 位移最大的 5 通道(|Δmu|/sd_old): "
      f"{[(c, round(float(d_mu[c]),2)) for c in big_shift]}")

# ── M4: regime 分桶 ────────────────────────────────────────────────────────────
print("\n" + "=" * 78)
print("[M4] regime: 按锚点横截面波动分半")
xvol = []
for i in anchors:
    r = CLOSE[i] / CLOSE[i - 6] - 1.0
    xvol.append(float(np.nanstd(r)))
med = np.median(xvol)
for nm, msk in (("低波动半", np.array(xvol) <= med), ("高波动半", np.array(xvol) > med)):
    ii = [anchors[k] for k in range(n_anch) if msk[k]]
    dn = np.nanmean([ic(S["new"][i], Y[i]) for i in ii])
    do = np.nanmean([ic(S["old"][i], Y[i]) for i in ii])
    print(f"  {nm}: n={len(ii):2d}  新 {dn:+.4f}  旧 {do:+.4f}  Δ {dn-do:+.4f}")

out = {"m1": {"labels": lab, "full": [float(np.nanmean(A[:, j])) for j in range(4)],
              "recent6": [float(np.nanmean(A[-6:, j])) for j in range(4)]},
       "m2_worst": [{"sym": syms[j], "contrib": float(contrib[j]), "vol_q": float(vq[j]),
                     "beta": None if not np.isfinite(beta[j]) else float(beta[j]),
                     "new_listing": bool(is_new_listing[j])} for j in order[:10]],
       "m3_flag_channels": flag,
       "m4": {"xvol_median": float(med)}}
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "deep_forensics.json"), "w"), indent=1)
print("\nwrote deep_forensics.json")
