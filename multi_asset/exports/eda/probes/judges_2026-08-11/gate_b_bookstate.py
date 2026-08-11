"""#48 门 B —— PREREG_bookstate_pregate_2026-08-05.md (v2 修订 sha 66089f6875a11a6c) 逐字执行。

★ 本文件是 `b4_breadth_gates12.py` 的【变体】(sleeve 在独立文件、只覆盖 14/110 名, 通道名取不到),
  因此按预注册 §9-② 强制自校: **先用本脚本自己的代码路径复算 #21 记录过的 rev_1h(dIC +0.0023,
  置换臂 ≈−0.0006)**; 复算不落在记录值附近 ⇒ 变体作废, 不出 sleeve 结论。
★ 双速: 主判 a=1.0(书当前速度, 原始冻结口径), 次判 a=0.03(预先声明), 两档都报。
"""
import json, sys
import numpy as np
import pandas as pd
from scipy.stats import rankdata

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA + "/engine/live")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
import torch; torch.backends.mkldnn.enabled = False
from engine.panel_source import PanelSource
from engine.signal_chain import SignalChain
from engine.netting import CrossLegNetting

PANEL = MA + "/exports/wide_dl_full_corrfund_causal_v1.npz"     # 与 #21 同一面板
FEAT = MA + "/exports/eda/bookstate14_features.npz"
KW, WEIGHTS, NBOOT = 0.5952380952380952, [0.05, 0.10], 400
SURV = ["cumdep_far_asym", "spread_bps"]
RNG = np.random.default_rng(0)

src = PanelSource(panel=PANEL, king=MA + "/exports/eda/king_pred_panel.npz",
                  s2=MA + "/exports/eda/s2_pred_panel_cl4.npz")
src.king = np.load("/tmp/vs5_pred_s1f_SERVE.npz")["pred"].astype(np.float64)
src.s2 = np.load("/tmp/vs5_pred_s2c10_SERVE.npz")["pred"].astype(np.float64)
z = np.load(PANEL, allow_pickle=True)
chn = [str(c) for c in z["ch_names"]]; CH = z["CH"]
A_ALL = np.sort(np.where((src.member & src.CL4 & np.isfinite(src.king)
                          & np.isfinite(src.s2)).any(1))[0])

f = np.load(FEAT, allow_pickle=True)
fts = {int(t): i for i, t in enumerate(f["ts"])}
fsy = [str(x) for x in f["symbols"]]
psy = [str(x) for x in z["symbols"]]
fcol = np.array([psy.index(s) for s in fsy])
Fz = f["F_z"]; fnames = [str(x) for x in f["feat_names"]]
SIDX = [fnames.index(s) for s in SURV]
# sleeve = 等权 z 合成(预注册钉死, 不得改为拟合权重); 其余 96 名 = 0(v2 §8 第四条口径)
SLEEVE = np.nanmean(Fz[:, :, SIDX], axis=2)                      # (Tf, 14)


class AsymCap(SignalChain):
    def shape_position(self, combo):
        mag = np.nan_to_num(np.asarray(combo, float))
        if mag.size >= 10 and np.isfinite(mag).any():
            mag = np.clip(mag, np.nanpercentile(mag, 1.0), np.nanpercentile(mag, 99.0))
        return mag - mag.mean()


def w_from_vals(ti, m, v, permute):
    if permute:
        v = RNG.permutation(v)
    r = rankdata(v); r = r - r.mean()
    s = float(np.abs(r).sum())
    if s < 1e-12:
        return None
    w = np.zeros(src.N); w[m] = r / s
    return w


def factor_channel(name, A, permute=False):
    """#21 口径: 面板通道 → 逐锚 L1 归一的横截面 rank 书。用于自校。"""
    j = chn.index(name); out = {}
    for t in A:
        ti = int(t)
        m = np.where(src.member[ti] & src.CL4[ti] & np.isfinite(CH[ti, :, j]))[0]
        if m.size < 5:
            continue
        w = w_from_vals(ti, m, CH[ti, m, j].astype(np.float64), permute)
        if w is not None:
            out[ti] = w
    return out


def factor_sleeve(A, permute=False):
    """本轨: sleeve 只在 14 名上有值, 其余为 0(合成内中性)。"""
    out = {}
    for t in A:
        ti = int(t); fi = fts.get(int(src.ts[ti]))
        if fi is None:
            continue
        v_all = SLEEVE[fi]
        ok = np.isfinite(v_all)
        if ok.sum() < 5:
            continue
        m = fcol[ok]
        keep = src.member[ti][m] & src.CL4[ti][m]
        if keep.sum() < 5:
            continue
        w = w_from_vals(ti, m[keep], v_all[ok][keep].astype(np.float64), permute)
        if w is not None:
            out[ti] = w
    return out


def book(A, YR, add=None, w_add=0.0, smooth_a=1.0):
    r = (1.0 - KW) / 2.0
    W = {"king": KW, "s2": r, "funding": r, "size": 0.0}
    ch = AsymCap(src, weights=W, funding_mode="rank", pos_cap_pct=99.0)
    res = CrossLegNetting(ch, W, cost_bps=1.9).run(A, src.ts, year_of=YR)
    bk = {int(t): (m, p / max(float(np.abs(p).sum()), 1e-12)) for (t, m, p) in res["net_positions"]}
    prev = np.zeros(src.N); ema = np.zeros(src.N)
    pnl = np.zeros(len(A)); turn = np.zeros(len(A)); ics = []
    for i, t in enumerate(A):
        ti = int(t); ret = src.Y4[ti]
        if ti not in bk or not np.isfinite(ret).any():
            turn[i] = float(np.abs(-prev).sum()); prev = np.zeros(src.N); continue
        m, p = bk[ti]
        w = np.zeros(src.N); w[m] = p
        if add is not None and ti in add:
            w = (1.0 - w_add) * w + w_add * add[ti]
        s = float(np.abs(w).sum())
        if s > 1e-12:
            w = w / s
        ema = (1.0 - smooth_a) * ema + smooth_a * w          # a=1 ⇒ 逐位等于 w(有效性)
        s2_ = float(np.abs(ema).sum())
        wt = ema / s2_ if s2_ > 1e-12 else ema
        good = np.isfinite(ret) & (wt != 0)
        if good.sum() >= 5:
            pnl[i] = float(np.sum(wt[good] * ret[good]))
            ics.append(np.corrcoef(rankdata(wt[good]), rankdata(ret[good]))[0, 1])
        turn[i] = float(np.abs(wt - prev).sum()); prev = wt
    return pnl, turn, np.array([x for x in ics if np.isfinite(x)])


def metrics(pnl, turn, cost_bps, days, ny):
    net = pnl - turn * cost_bps * 1e-4
    dfp = pd.DataFrame({"d": days, "p": net}).groupby("d")["p"].sum()
    mu, sd = dfp.mean(), dfp.std(ddof=1)
    return float(mu / sd * np.sqrt(365.25)) if sd > 1e-12 else 0.0


def boot_ci(delta_by_day, nboot=NBOOT):
    ud = np.array(sorted(delta_by_day.keys())); v = np.array([delta_by_day[d] for d in ud])
    bs = [np.mean(RNG.choice(v, size=len(v), replace=True)) for _ in range(nboot)]
    return float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def run_case(label, mk, A, YR, DAY, ny, smooth_a):
    base_p, base_t, base_ic = book(A, YR, smooth_a=smooth_a)
    out = {}
    for w_add in WEIGHTS:
        add = mk(A, permute=False)
        p, t, ic = book(A, YR, add=add, w_add=w_add, smooth_a=smooth_a)
        addp = mk(A, permute=True)
        pp, tp, icp = book(A, YR, add=addp, w_add=w_add, smooth_a=smooth_a)
        dic = float(np.mean(ic) - np.mean(base_ic))
        dic_perm = float(np.mean(icp) - np.mean(base_ic))
        dnet = {c: metrics(p, t, c, DAY, ny) - metrics(base_p, base_t, c, DAY, ny)
                for c in (3.63, 5.8)}
        dbd = {}
        for d in np.unique(DAY):
            msk = DAY == d
            dbd[int(d)] = float(np.sum((p - t * 3.63e-4)[msk]) - np.sum((base_p - base_t * 3.63e-4)[msk]))
        lo, hi = boot_ci(dbd)
        out[w_add] = {"dIC": round(dic, 5), "dIC_permuted_ruler": round(dic_perm, 5),
                      "dSh@3.63": round(dnet[3.63], 4), "dSh@5.8": round(dnet[5.8], 4),
                      "dailyPnL_CI95": [round(lo, 4), round(hi, 4)],
                      "gate1_pass": bool(dic > 0 and lo > 0),
                      "gate2_pass": bool(lo > 0 and dnet[5.8] > 0)}
        print(f"  [{label} a={smooth_a} w={w_add}] {out[w_add]}", flush=True)
    return out


def main():
    # ── 自校: 用本脚本的代码路径复算 #21 的 rev_1h ──
    YR_ALL = pd.to_datetime(src.ts[A_ALL], unit="ms", utc=True).year.to_numpy()
    DAY_ALL = (src.ts[A_ALL] // (1000 * 3600 * 24)).astype(np.int64)
    NY_ALL = (int(src.ts[A_ALL[-1]]) - int(src.ts[A_ALL[0]])) / (1000 * 3600 * 24 * 365.25)
    print(f"[self-check] 复算 #21 的 rev_1h (记录: dIC +0.0023, 置换臂 ≈−0.0006)", flush=True)
    sc = run_case("rev_1h", lambda A, permute: factor_channel("rev_1h", A, permute),
                  A_ALL, YR_ALL, DAY_ALL, NY_ALL, 1.0)
    d5 = sc[0.05]["dIC"]
    ok = abs(d5 - 0.0023) < 0.0015 and abs(sc[0.05]["dIC_permuted_ruler"]) < 0.0015
    print(f"[self-check] {'PASS' if ok else '★★ FAIL — 变体作废, 不出 sleeve 结论'} "
          f"(dIC={d5}, perm={sc[0.05]['dIC_permuted_ruler']})", flush=True)
    res = {"prereg": "PREREG_bookstate_pregate_2026-08-05.md (v2 66089f6875a11a6c)",
           "self_check": {"factor": "rev_1h", "recorded_dIC": 0.0023, "recomputed": sc,
                          "pass": ok}}
    if not ok:
        json.dump(res, open(MA + "/exports/eda/RESULT_bookstate14_gateB.json", "w"), indent=1)
        print("变体自校未过 —— 按预注册停止。"); return
    # ── sleeve: 只在有特征覆盖的锚上判(v2 §6 第一条口径) ──
    A = np.array([t for t in A_ALL if int(src.ts[t]) in fts])
    A = np.array([t for t in A if np.isfinite(SLEEVE[fts[int(src.ts[t])]]).sum() >= 5])
    YR = pd.to_datetime(src.ts[A], unit="ms", utc=True).year.to_numpy()
    DAY = (src.ts[A] // (1000 * 3600 * 24)).astype(np.int64)
    NY = (int(src.ts[A[-1]]) - int(src.ts[A[0]])) / (1000 * 3600 * 24 * 365.25)
    print(f"[sleeve] 覆盖锚 {len(A)}/{len(A_ALL)} = {len(A)/len(A_ALL):.3f}, "
          f"跨度 {pd.to_datetime(int(src.ts[A[0]]),unit='ms')} → "
          f"{pd.to_datetime(int(src.ts[A[-1]]),unit='ms')}, {NY:.2f} 年", flush=True)
    res["coverage"] = {"n_anchors": int(len(A)), "frac_of_all": round(len(A)/len(A_ALL), 4),
                       "years": round(NY, 2)}
    for a in (1.0, 0.03):
        res[f"sleeve_a{a}"] = run_case("sleeve", lambda A, permute: factor_sleeve(A, permute),
                                       A, YR, DAY, NY, a)
    json.dump(res, open(MA + "/exports/eda/RESULT_bookstate14_gateB.json", "w"),
              indent=1, ensure_ascii=False)
    print("\n=== 判决 ===")
    for a in (1.0, 0.03):
        for w in WEIGHTS:
            r = res[f"sleeve_a{a}"][w]
            print(f"  a={a} w={w}: 关一{'过' if r['gate1_pass'] else '挂'} "
                  f"关二{'过' if r['gate2_pass'] else '挂'}  dIC={r['dIC']} "
                  f"(置换尺 {r['dIC_permuted_ruler']}) dSh {r['dSh@3.63']}/{r['dSh@5.8']}")
    print("saved -> exports/eda/RESULT_bookstate14_gateB.json")


if __name__ == "__main__":
    main()
