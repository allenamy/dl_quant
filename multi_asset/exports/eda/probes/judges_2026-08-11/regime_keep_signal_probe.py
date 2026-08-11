"""两问四测 — 全部因果、全部本地、判读先写。

用户问 1: 降毛敞口 = 动态杠杆? rank-IC 后验, 如何实时?
  ★ 澄清: 在锚点 T, 上一锚(T-4h)的收益窗口【刚好闭合】 ⇒ trailing IC 以 1 锚滞后可得, 是因果的。
    弱点不是因果性, 是【反应性】(先亏后砍) + 是否有预测力。
  T1 检验: IC 序列的可预测性 — AR(1) + trailing-4 均值预测下一锚 IC。
           有预测力 ⇒ IC 门控杠杆有依据; 无 ⇒ 它只是防御(诚实说)。
  T2 检验: 延续指数 C_t = xsec-corr(ret_{t-2 窗}, ret_{t-1 窗}) — 【零滞后因果】的行情性质:
           市场此刻在延续还是反转。C_t 能否预测本锚模型 IC? 能 ⇒ 存在有原则的实时门。

用户问 2: 当前 regime 也是 pattern, 如何【保持信号】——
  T3 检验: 两代模型逐锚 IC 的相关 + 50/50 混合的假想表现(静态混合=分散倾斜,
           不是被否决过的 regime 路由 — 无切换, 常开)。
  T4 检验: 动量补臂探针 — 7d 横截面动量(因果, 与目标窗零重叠):
           全期 IC / 延续锚 IC / 反转锚 IC / 与 king IC 的逐锚相关(互补性)。
           若动量在延续锚为正而 king≈0 ⇒ 补臂存在且可收割(下一步才是门与预注册)。

样本: 旧模型 OOS 从 07-24 起(~78 锚, 训练止 06 月); 新模型 08-01 起(32 锚)。
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

gens = {}
for tag, d in (("new", os.path.join(REPO, "checkpoints")),
               ("old", os.path.join(REPO, "rollback_batch1_20260804T145921Z", "checkpoints"))):
    gens[tag], _ = INF.load(stats_path=os.path.join(d, "norm_stats.npz"), ckpt_dir=d)

FLOOR = 887
idx_all = [i for i in range(FLOOR, len(ts) - 4)
           if int(ts[i]) % (4 * 3600 * 1000) == 0]
NEW_START = 1785542400000            # 08-01 (新模型 OOS)


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


# 打分 + 目标 + 因果行情量
S = {"new": {}, "old": {}}
Y, C_t, MOM = {}, {}, {}
for i in idx_all:
    mask = member[i].astype(np.float32)
    if mask.sum() < 20:
        continue
    y = np.full(N, np.nan)
    c0, c1 = CLOSE[i], CLOSE[i + 4]
    ok = np.isfinite(c0) & np.isfinite(c1) & (c0 > 0)
    y[ok] = c1[ok] / c0[ok] - 1.0
    y[mask < 0.5] = np.nan
    Y[i] = y
    r_prev1 = CLOSE[i] / CLOSE[i - 4] - 1.0          # (t-4h, t]
    r_prev2 = CLOSE[i - 4] / CLOSE[i - 8] - 1.0      # (t-8h, t-4h]
    C_t[i] = ic(r_prev2, r_prev1)                    # 延续指数(零滞后因果)
    mom = CLOSE[i] / CLOSE[i - 168] - 1.0            # 7d 动量, 与目标窗零重叠
    mom[mask < 0.5] = np.nan
    MOM[i] = mom
    win = CH[i - INF.W + 1: i + 1].transpose(1, 0, 2)
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
A_old = anchors                                      # 旧模型全程 OOS
A_new = [i for i in anchors if int(ts[i]) >= NEW_START]
ic_old = np.array([ic(S["old"][i], Y[i]) for i in A_old])
ic_new_map = {i: ic(S["new"][i], Y[i]) for i in A_new}
ct = np.array([C_t[i] for i in A_old])
print(f"样本: 旧模型 {len(A_old)} 锚(07-24 起, 全 OOS) / 新模型 {len(A_new)} 锚(08-01 起)")

def ar1(x):
    a, b = x[:-1], x[1:]
    m = np.isfinite(a) & np.isfinite(b)
    return float(np.corrcoef(a[m], b[m])[0, 1]), int(m.sum())

print("\n[T1] IC 可预测性(旧模型 %d 锚)" % len(A_old))
r1, n1 = ar1(ic_old)
print(f"  AR(1) = {r1:+.3f}  (n={n1})")
tr4 = np.array([np.nanmean(ic_old[max(0, k - 4):k]) if k >= 2 else np.nan
                for k in range(len(ic_old))])
m = np.isfinite(tr4) & np.isfinite(ic_old)
r_tr = float(np.corrcoef(tr4[m], ic_old[m])[0, 1])
print(f"  corr(trailing-4 均值, 下一锚 IC) = {r_tr:+.3f}  (n={m.sum()})")
se = 1 / np.sqrt(max(n1, 1))
print(f"  参考 SE≈{se:.3f} ⇒ |r|<{2*se:.2f} 视为无预测力")

print("\n[T2] 延续指数 C_t(零滞后因果) 能否预测本锚 IC")
m = np.isfinite(ct) & np.isfinite(ic_old)
r_c = float(np.corrcoef(ct[m], ic_old[m])[0, 1])
print(f"  corr(C_t, 本锚旧模型 IC) = {r_c:+.3f}  (n={m.sum()})")
ic_new_arr = np.array([ic_new_map[i] for i in A_new])
ct_new = np.array([C_t[i] for i in A_new])
m2 = np.isfinite(ct_new) & np.isfinite(ic_new_arr)
r_c_new = float(np.corrcoef(ct_new[m2], ic_new_arr[m2])[0, 1])
print(f"  corr(C_t, 本锚新模型 IC) = {r_c_new:+.3f}  (n={m2.sum()})")
hi = ct > np.nanmedian(ct)
print(f"  延续锚(C_t 高半) 旧模型 IC = {np.nanmean(ic_old[hi]):+.4f} | "
      f"反转锚(低半) = {np.nanmean(ic_old[~hi]):+.4f}")

print("\n[T3] 两代混合(静态, 非路由)")
both = [(ic_new_map[i], ic(S["old"][i], Y[i])) for i in A_new]
bn = np.array([x[0] for x in both]); bo = np.array([x[1] for x in both])
m = np.isfinite(bn) & np.isfinite(bo)
r_no = float(np.corrcoef(bn[m], bo[m])[0, 1])
mix = np.array([ic(0.5 * zr(S["new"][i]) + 0.5 * zr(S["old"][i]), Y[i]) for i in A_new])
print(f"  corr(逐锚 IC_new, IC_old) = {r_no:+.3f}")
print(f"  50/50 分数混合: 全 {len(A_new)} 锚 IC {np.nanmean(mix):+.4f} "
      f"(new {np.nanmean(bn):+.4f} / old {np.nanmean(bo):+.4f})")
print(f"  最近 6 锚: 混合 {np.nanmean(mix[-6:]):+.4f}  new {np.nanmean(bn[-6:]):+.4f}  old {np.nanmean(bo[-6:]):+.4f}")
sd_mix, sd_new = np.nanstd(mix, ddof=1), np.nanstd(bn, ddof=1)
print(f"  IC 波动: 混合 {sd_mix:.4f} vs new {sd_new:.4f}  ⇒ IR/锚: 混合 "
      f"{np.nanmean(mix)/sd_mix:+.2f} vs new {np.nanmean(bn)/sd_new:+.2f}")

print("\n[T4] 动量补臂探针(7d, 因果, 零目标重叠)")
ic_mom = np.array([ic(MOM[i], Y[i]) for i in A_old])
print(f"  全期 IC = {np.nanmean(ic_mom):+.4f}  (sd {np.nanstd(ic_mom,ddof=1):.4f}, n={len(A_old)})")
print(f"  延续锚(C_t 高半) = {np.nanmean(ic_mom[hi]):+.4f} | 反转锚 = {np.nanmean(ic_mom[~hi]):+.4f}")
rec6 = [i for i in A_new][-6:]
print(f"  最近 6 锚 动量 IC = {np.nanmean([ic(MOM[i], Y[i]) for i in rec6]):+.4f}"
      f"   (对照: 新模型同期 {np.nanmean(bn[-6:]):+.4f})")
m = np.isfinite(ic_mom) & np.isfinite(ic_old)
r_mk = float(np.corrcoef(ic_mom[m], ic_old[m])[0, 1])
print(f"  corr(逐锚 动量 IC, 旧模型 IC) = {r_mk:+.3f}   (负/低 = 真互补)")
mixk = np.array([ic(zr(S["new"].get(i, np.full(N, np.nan))) + 0.5 * zr(MOM[i]), Y[i])
                 for i in A_new])
print(f"  新模型+0.5·动量 混合: 全期 {np.nanmean(mixk):+.4f}  最近 6 锚 {np.nanmean(mixk[-6:]):+.4f}")

json.dump({"t1_ar1": r1, "t1_trailing4": r_tr,
           "t2_ct_old": r_c, "t2_ct_new": r_c_new,
           "t3_corr": r_no, "t3_mix_full": float(np.nanmean(mix)),
           "t3_mix_recent6": float(np.nanmean(mix[-6:])),
           "t4_mom_full": float(np.nanmean(ic_mom)),
           "t4_mom_cont": float(np.nanmean(ic_mom[hi])),
           "t4_mom_rev": float(np.nanmean(ic_mom[~hi])),
           "t4_corr_mom_old": r_mk},
          open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "regime_probe.json"), "w"), indent=1)
print("\nwrote regime_probe.json")
