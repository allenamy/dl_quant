"""#72 翻译测试 · 2×2 析因 —— 腿级 IC 能不能兑现成书级净夏普?

设计: {y4, y8} × {cad4, cad8}。这样【模型效应】与【节奏效应】及其交互各自可分,
      而不是把两者混在一次 y8@8h vs y4@4h 的比较里。
两侧同协议: 都从 harness 冠军臂组装(y4 三种子 / y8 五种子), 不与生产折 newgen 混。
★ 共同锚: 只在 y4 与 y8 都有 ≥5 个有限预测的锚上评估 —— y8 的 OOS 锚比 y4 少 39%(CL8 更严),
  不做交集就会把【覆盖】混进【质量】(W4 的共同锚教训 + 今日"部分臂压塌交集"的教训)。
口径: 实盘同构 cap99+demean → risk_budget(α.5 λ1.0) → l1 单位 gross; 成本 3.115(实测) 与 5.8 双报。
★ 归因纪律(今日已触发三次): 若增益来自 Δ换手 而非 Δ毛额 ⇒ 记在换手线, 不记在模型线。
"""
import sys, json, time, numpy as np, pandas as pd
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset")
import engine.replay_fullhist as RF
from engine.signal_chain import SignalChain, _z, _l1, _rank_centered
from engine.funding_risk import FundingLegRiskControl
from engine.vol_gate import VolGate

PD = "/mnt/storage/private/work_hsy/probe_artifacts"
S2 = f"{PD}/s2_pred_newgen.npz"
LIVE3 = {"king": 0.5952380952380952, "s2": 0.20238095238095238, "funding": 0.20238095238095238, "size": 0.0}
COSTS = [3.115, 5.80]
RB = {"alpha": 0.5, "lambda": 1.0}
OUT = f"{PD}/translate_2x2.json"

t0 = time.time()
# ★ 引擎面板与 harness 训练面板【不是同一个时间网格】(48168 vs 48912) —— 必须按 ts+symbol 显式对齐。
#   若两边碰巧同长, 直接用会变成静默的错行对齐。这里先对齐再喂给 get_src。
src = RF.get_src()                       # 默认面板, 只为拿到 ts/symbols/N
N = src.N; RVOL_I = src.ch.index("rvol_24h")
eng_ts = {int(t): i for i, t in enumerate(src.ts)}
eng_sym = {s: j for j, s in enumerate(src.symbols)}


def align(path):
    z = np.load(path, allow_pickle=True)
    A = z["king_pred"].astype(np.float64)
    hts = z["ts"].astype(np.int64); hsym = [str(x) for x in z["symbols"]]
    out = np.full((src.T, N), np.nan)
    rows = np.array([eng_ts.get(int(t), -1) for t in hts])
    cols = np.array([eng_sym.get(s, -1) for s in hsym])
    rm = rows >= 0; cm = cols >= 0
    out[np.ix_(rows[rm], cols[cm])] = A[np.ix_(np.where(rm)[0], np.where(cm)[0])]
    print(f"    {path.split('/')[-1]}: 时间命中 {rm.mean():.3f} 符号命中 {cm.mean():.3f} "
          f"有限格 {np.isfinite(out).mean():.4f}", flush=True)
    return out


print(f"[A] 引擎 T={src.T} N={N}; 对齐 harness 面板:", flush=True)
K = {"y4": align(f"{PD}/harness_y4_pred_panel.npz"),
     "y8": align(f"{PD}/harness_y8_pred_panel.npz")}
# 用 y4 的对齐结果替换引擎的 king, 以便 _all_anchors 的掩码正确
src.king = K["y4"]
anchors, yr = RF._all_anchors(src)

disp_ref = FundingLegRiskControl.calibrate_dispersion(src, anchors)
frc = FundingLegRiskControl(winsor_z=4.0, name_cap=0.15, disp_gate_z=4.0, disp_shrink=0.3, disp_ref=disp_ref)
chain = SignalChain(src, weights=LIVE3, funding_mode="rank", vol_gate=VolGate(src),
                    funding_risk=frc, pos_cap_pct=99.0)
chain.calibrator = None

# ── 共同锚 ──────────────────────────────────────────────────────────────────
keep = []
for t in anchors:
    ti = int(t); m = np.where(src.member[ti])[0]
    if m.size < 5:
        continue
    if all(np.isfinite(K[h][ti, m]).sum() >= 5 for h in K):
        keep.append(ti)
keep = np.array(keep)
print(f"[A] 全锚 {len(anchors)} → 共同锚 {len(keep)}  "
      f"(y4 单独 {sum(1 for t in anchors if np.isfinite(K['y4'][int(t)]).sum()>=5)}, "
      f"y8 单独 {sum(1 for t in anchors if np.isfinite(K['y8'][int(t)]).sum()>=5)})", flush=True)
yrk = pd.to_datetime(src.ts[keep], unit="ms", utc=True).year.to_numpy()
DAY = (src.ts[keep] // (1000*3600*24)).astype(np.int64)

M, RET, RVOL, FUND, S2L = [], [], [], [], []
for ti in keep:
    legs, m = src.legs_raw(int(ti))
    M.append(m); RET.append(src.Y4[int(ti), m])
    RVOL.append(src.CH[int(ti), m, RVOL_I].astype(np.float64))
    FUND.append(legs["funding"]); S2L.append(legs["s2"])
print(f"[A] done {time.time()-t0:.0f}s", flush=True)


def rb(s_, rvol):
    a, l = RB["alpha"], RB["lambda"]
    v = np.asarray(rvol, float); fin = np.isfinite(v) & (v > 0)
    if not fin.any(): return s_
    med = float(np.median(v[fin]))
    if med <= 0: return s_
    v = np.where(fin, v, med)
    w = np.sign(s_) * np.abs(s_)**a / np.power(v/med, l)
    return w - w.mean()


def run(hz, cad_king):
    held = {"king": np.zeros(N), "s2": np.zeros(N), "funding": np.zeros(N)}
    cad = {"king": cad_king, "s2": 24, "funding": 8}
    prev = np.zeros(N); pnl = np.zeros(len(keep)); turn = np.zeros(len(keep)); ric = np.full(len(keep), np.nan)
    T_ = {k: 0.0 for k in held}
    for i, ti in enumerate(keep):
        m = M[i]
        raw = {"king": _z(np.nan_to_num(K[hz][int(ti), m])),
               "s2": _z(S2L[i]),
               "funding": -1.0 * _rank_centered(FUND[i])}
        rc, _ = frc.apply(raw["funding"], funding_raw=FUND[i])
        raw["funding"] = rc
        for k in held:
            if i == 0 or (int(ti) % cad[k] == 0):
                new = np.zeros(N); new[m] = _l1(raw[k])
                T_[k] += float(np.abs(new - held[k]).sum()); held[k] = new
        combo = sum(LIVE3[k] * held[k] for k in held)
        shaped = rb(chain.shape_position(combo[m]), RVOL[i])
        g = float(np.abs(shaped).sum())
        if g > 1e-12: shaped = shaped / g
        net = np.zeros(N); net[m] = shaped
        r = RET[i]; ok = np.isfinite(r)
        pnl[i] = float(np.nansum(shaped[ok]*r[ok]))
        turn[i] = 0.0 if i == 0 else float(np.abs(net-prev).sum())
        if ok.sum() >= 5:
            ric[i] = float(np.corrcoef(pd.Series(shaped[ok]).rank(), pd.Series(r[ok]).rank())[0, 1])
        prev = net
    yrs = (int(src.ts[keep[-1]]) - int(src.ts[keep[0]])) / (1000*3600*24*365.25)
    gt = sum(LIVE3[k]*T_[k] for k in T_) / max(yrs, 1e-9)
    return pnl, turn, ric, gt


def sh(p, t, c):
    return RF._dsharpe(pd.DataFrame({"day": DAY, "n": p - t*c*1e-4}).groupby("day").n.sum().values)


R = {"common_anchors": int(len(keep)), "costs": COSTS, "cells": {}}
print("\n格           毛额累计    年化换手   rank-IC   " + "   ".join(f"Sh@{c}" for c in COSTS))
print("-"*74)
base = None
for hz in ["y4", "y8"]:
    for cd in [4, 8]:
        p, t, ric, gt = run(hz, cd)
        row = {"cum_gross": round(float(p.sum()), 5), "gross_turn_ann": round(gt, 1),
               "rank_ic": round(float(np.nanmean(ric)), 5),
               **{f"Sh@{c}": round(sh(p, t, c), 4) for c in COSTS}}
        R["cells"][f"{hz}_cad{cd}"] = row
        if hz == "y4" and cd == 4: base = row
        print(f"{hz}_cad{cd:<4s} {p.sum():+11.5f} {gt:10.1f} {np.nanmean(ric):+9.5f}   " +
              "   ".join(f"{sh(p,t,c):+8.4f}" for c in COSTS), flush=True)

b = R["cells"]["y4_cad4"]
print("\n===== 相对 y4_cad4(在役形态) =====")
for k, v in R["cells"].items():
    if k == "y4_cad4": continue
    print(f"  {k:10s} Δ毛额 {v['cum_gross']-b['cum_gross']:+.5f}  Δ换手 {v['gross_turn_ann']-b['gross_turn_ann']:+8.1f}  "
          f"ΔrankIC {v['rank_ic']-b['rank_ic']:+.5f}  " +
          "  ".join(f"ΔSh@{c} {v[f'Sh@{c}']-b[f'Sh@{c}']:+.4f}" for c in COSTS))
print("\n★ 归因: 若 ΔSh 主要由 Δ换手(负)驱动而非 Δ毛额(正) ⇒ 记在换手线, 不记在模型线。")
json.dump(R, open(OUT, "w"), indent=1)
print(f"\n[done] {time.time()-t0:.0f}s -> {OUT}\nTRANSLATE_DONE")
