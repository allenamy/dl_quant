"""W2 红队追加 A · 宽书逐锚【精确可加】腿归因 @jpline(2026-08-22, Session 6737834a-W2)。
书构造 = w2_wide_replay.py(= pod_stop_arms_v3 逐字)不变; 新增: 把持仓向量 sm 精确分解为 king/rev24/fund 三个分量, Σ分量 ≡ sm(逐锚断言 <1e-9):
  z_k = w3_k·xz(sc_k) → 截面去均值(线性, 逐分量) → ÷g(标量) → cap 裁剪(逐名按 w_c/w 比例缩放各分量; 未裁名不变) → ÷g2(标量) → 止损置零(逐分量)
  → EMA α0.1(线性, 逐分量) → 带(用【总量】trade 的掩码, 同一掩码施于各分量; Σ保持)。
逐锚逐腿: 价格 pnl_k = sm_k·y; carry_k = sm_k·fund_now·4/iv(正 = 该腿【付出】funding, 负 = 收到); cost_k = Σ_名 成本_名 × |trade_k,名| / Σ_j |trade_j,名|; gross_k = |sm_k|₁。
输出: probe_artifacts/w2_wide_legattrib.npz(臂 S0 与 d30_n2_c42) + w2_wide_legattrib_summary.json(含 Σ分量 vs 书 的收据)。
"""
import json, time, sys, os
import numpy as np
from scipy.stats import rankdata
B = "/mnt/storage/private/work_hsy/pod_backup_2026-08-21"; PD = "/mnt/storage/private/work_hsy/probe_artifacts"
t0 = time.time()
MT = np.load(f"{B}/wide_fea_hist_meta.npz", allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; qvk = MT["qvk"]
nA = len(E_ts); NW = 829
PW = np.load(f"{B}/wide_panel_4h_hist_v2.npz", allow_pickle=True)
pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
FN = PW["f_fund_now"]; IV = PW["f_fund_iv"]; R24 = PW["f_rev_24h"]; FE = PW["f_fund_ema_v1"]
SLOW = np.load(f"{B}/slow_pred_hist_oos.npy")
LEGS = ("king", "rev24", "fund")
def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    if ok.sum() >= 10: out[ok] = rankdata(v[ok]) / max(ok.sum() - 1, 1) - 0.5
    return out
COST_B = [(-0.25, 5.0, 0.85), (0.5, 6.0, 0.75), (2.0, 8.0, 0.55)]
RATE = np.array([fr * mk + (1 - fr) * tk for (mk, tk, fr) in COST_B])   # per-tier bps per unit traded
def tier_of(q):
    t = np.full(len(q), 2, np.int8); t[q >= 1e6] = 1; t[q >= 5e6] = 0
    return t
def legs(SLOW):
    LR = {l: [] for l in LEGS}; idx = []
    for i in range(nA):
        j = pw_row.get(int(E_ts[i]))
        if j is None: continue
        m = members[i]
        sc = {"king": SLOW[i, m], "rev24": -R24[j, m], "fund": FE[j, m]}
        ok = np.isfinite(y4[i, m])
        for leg in LR:
            z = np.nan_to_num(xz(sc[leg])); z = np.where(ok, z, 0.0); z -= z[ok].mean() if ok.sum() else 0
            g = np.abs(z).sum()
            LR[leg].append(float((z / g * np.nan_to_num(y4[i, m], nan=0.0)).sum() * 1e4) if g > 1e-9 else 0.0)
        idx.append(i)
    return {k: np.array(v) for k, v in LR.items()}, {int(i): p for p, i in enumerate(idx)}
def run(SLOW, LRa, pos, depth, need, cool, look=900):
    def w3_at(i):
        p = pos.get(int(i), 0)
        if p < look: return np.array([1/3]*3)
        sl = slice(p - look, p)
        r = np.stack([LRa["king"][sl], LRa["rev24"][sl], LRa["fund"][sl]])
        shp = np.maximum(r.mean(1) / (r.std(1) + 1e-9), 0.0)
        return shp / shp.sum() if shp.sum() > 0 else np.array([1/3]*3)
    H = np.zeros(NW); HK = {k: np.zeros(NW) for k in LEGS}
    Pi = np.ones(NW); sh = np.zeros(NW); cb = np.zeros(NW); cnt = np.zeros(NW, int); su = np.full(NW, -1)
    rec = []; maxerr = 0.0
    for i in range(nA):
        j = pw_row.get(int(E_ts[i]))
        if j is None: continue
        m = members[i]
        sc = {"king": SLOW[i, m], "rev24": -R24[j, m], "fund": FE[j, m]}
        w3 = w3_at(i)
        zk = {k: w3[q] * np.nan_to_num(xz(sc[k])) for q, k in enumerate(LEGS)}
        z = zk["king"] + zk["rev24"] + zk["fund"]
        ok = np.isfinite(y4[i, m]); qv4h = np.expm1(np.clip(qvk[i, m], 0, 30)) * 48
        sel = ok & (qv4h >= 2.5e5)
        if sel.sum() < 80: continue
        w = np.where(sel, z, 0.0); w -= w[sel].mean()
        wk = {k: np.where(sel, zk[k], 0.0) for k in LEGS}
        for k in LEGS: wk[k] = wk[k] - wk[k][sel].mean()
        g = np.abs(w).sum()
        if g < 1e-9: continue
        w /= g
        for k in LEGS: wk[k] = wk[k] / g
        capw = 2.5 / max(int(sel.sum()), 1); wc = np.clip(w, -capw, capw)
        with np.errstate(all="ignore"):
            scale = np.where(np.abs(w) > 1e-15, wc / w, 1.0)
        for k in LEGS: wk[k] = wk[k] * scale
        g2 = np.abs(wc).sum()
        if g2 > 1e-9:
            wc = wc / g2
            for k in LEGS: wk[k] = wk[k] / g2
        tgt = np.zeros(NW); tgt[m] = wc
        tk = {k: np.zeros(NW) for k in LEGS}
        for k in LEGS: tk[k][m] = wk[k]
        if depth is not None:
            bl = su > i
            if bl.any():
                tgt[bl] = 0.0
                for k in LEGS: tk[k][bl] = 0.0
        sm = H + 0.1 * (tgt - H); trade = sm - H
        mask = np.abs(trade) < 2.5e-4
        sm = np.where(mask, H, sm); trade = sm - H
        smk = {}; trk = {}
        for k in LEGS:
            s_ = HK[k] + 0.1 * (tk[k] - HK[k]); s_ = np.where(mask, HK[k], s_); smk[k] = s_; trk[k] = s_ - HK[k]
        err = float(np.max(np.abs(smk["king"] + smk["rev24"] + smk["fund"] - sm))); maxerr = max(maxerr, err)
        tr = tier_of(qv4h); rate_m = RATE[tr]
        cost_name = np.abs(trade[m]) * rate_m                                  # per-name cost (bps)
        cbps = float(cost_name.sum())
        den = sum(np.abs(trk[k][m]) for k in LEGS)
        with np.errstate(all="ignore"):
            sharek = {k: np.where(den > 0, np.abs(trk[k][m]) / np.where(den > 0, den, 1.0), 1.0 / 3) for k in LEGS}
        yv = np.nan_to_num(y4[i, m], nan=0.0)
        fnow = np.nan_to_num(FN[j, m], nan=0.0); ivv = IV[j, m]; ivv = np.where(np.isfinite(ivv) & (ivv > 0), ivv, 8.0); fc = fnow * (4.0 / ivv)
        row = [int(E_ts[i]), float((sm[m] * yv).sum() * 1e4), float((sm[m] * fc).sum() * 1e4), cbps, float(np.abs(sm).sum()), float(np.abs(sm[m]).sum()), float(w3[0]), float(w3[1]), float(w3[2])]
        for k in LEGS:
            row += [float((smk[k][m] * yv).sum() * 1e4), float((smk[k][m] * fc).sum() * 1e4), float((cost_name * sharek[k]).sum()), float(np.abs(smk[k]).sum()), float(np.abs(smk[k][m]).sum())]
        rec.append(row)
        # 成本均价深度(全宇宙价格路径) — 与 v3 逐字
        yfull = np.zeros(NW); yfull[m] = yv
        nsh = np.where(Pi > 1e-12, sm / Pi, 0.0)
        same = np.sign(nsh) == np.sign(sh); add = same & (np.abs(nsh) > np.abs(sh))
        red = same & (~add) & (np.abs(nsh) > 1e-12); new = (~same) | (np.abs(sh) < 1e-12)
        cb = np.where(add, cb + (nsh - sh) * Pi, cb)
        with np.errstate(all="ignore"):
            ratio = np.where(np.abs(sh) > 1e-12, nsh / np.where(np.abs(sh) > 1e-12, sh, 1.0), 0.0)
        cb = np.where(red, cb * ratio, cb); cb = np.where(new, nsh * Pi, cb); cb = np.where(np.abs(nsh) < 1e-12, 0.0, cb)
        sh = nsh
        with np.errstate(all="ignore"):
            avg = np.where(np.abs(sh) > 1e-12, cb / sh, np.nan)
            dep = np.where(np.isfinite(avg) & (Pi > 0), np.sign(sh) * (1.0 - avg / Pi), 0.0)
        if depth is not None:
            cand = (np.abs(sh) > 1e-12) & (dep <= depth) & (su <= i)
            cnt = np.where(cand, cnt + 1, 0); fr2 = cnt >= need
            if fr2.any(): su[fr2] = i + cool; cnt[fr2] = 0
        H = sm; HK = smk; Pi = Pi * (1.0 + yfull)
        if i % 3000 == 0: print("depth", depth, i, "/", nA, round(time.time() - t0, 1), "s", flush=True)
    return np.array(rec), maxerr
COLS = ["ts", "pnl", "carry", "cost", "gross_total", "gross_member", "w3_king", "w3_rev24", "w3_fund"]
for k in LEGS: COLS += [f"{k}_pnl", f"{k}_carry", f"{k}_cost", f"{k}_gross", f"{k}_gross_member"]
LRa, pos = legs(SLOW); print("legs done", round(time.time() - t0, 1), flush=True)
out = {}; save = {"cols": np.array(COLS)}
for nm, d, n_, c, reff in (("S0", None, 0, 0, "nets_histv2_0_0_0.npy"), ("d30_n2_c42", -0.30, 2, 42, "nets_histv2_-30_2_42.npy")):
    R, maxerr = run(SLOW, LRa, pos, d, n_, c)
    C = {c_: q for q, c_ in enumerate(COLS)}
    ref = np.load(f"{B}/{reff}"); net_ref = ref[:, 1]; assert len(net_ref) == len(R)
    net = R[:, C["pnl"]] - R[:, C["carry"]] - R[:, C["cost"]]
    sum_pnl = sum(R[:, C[f"{k}_pnl"]] for k in LEGS); sum_car = sum(R[:, C[f"{k}_carry"]] for k in LEGS); sum_cost = sum(R[:, C[f"{k}_cost"]] for k in LEGS)
    out[nm] = {"n": int(len(R)), "maxabs_net_vs_pod_backup": float(np.max(np.abs(net - net_ref))), "max_component_sum_err_weights": maxerr,
               "maxabs_sum_pnl_vs_book": float(np.max(np.abs(sum_pnl - R[:, C["pnl"]]))), "maxabs_sum_carry_vs_book": float(np.max(np.abs(sum_car - R[:, C["carry"]]))),
               "maxabs_sum_cost_vs_book": float(np.max(np.abs(sum_cost - R[:, C["cost"]]))),
               "leg_means_bps": {k: {"pnl": round(float(R[:, C[f"{k}_pnl"]].mean()), 4), "carry_paid": round(float(R[:, C[f"{k}_carry"]].mean()), 4), "cost": round(float(R[:, C[f"{k}_cost"]].mean()), 4),
                                     "gross": round(float(R[:, C[f"{k}_gross"]].mean()), 4)} for k in LEGS},
               "book_means_bps": {"pnl": round(float(R[:, C["pnl"]].mean()), 4), "carry_paid": round(float(R[:, C["carry"]].mean()), 4), "cost": round(float(R[:, C["cost"]].mean()), 4), "net": round(float(net.mean()), 4)},
               "carry_sign_convention": "carry = Σ w·fund_now·4/iv ×1e4; 正 = 书/腿【付出】funding; net = pnl − carry − cost"}
    print("RECEIPT", nm, json.dumps(out[nm]), flush=True)
    save[nm] = R
json.dump(out, open(f"{PD}/w2_wide_legattrib_summary.json", "w"), indent=1, ensure_ascii=False)
np.savez_compressed(f"{PD}/w2_wide_legattrib.npz", **save)
print("DONE", round(time.time() - t0, 1), flush=True)
