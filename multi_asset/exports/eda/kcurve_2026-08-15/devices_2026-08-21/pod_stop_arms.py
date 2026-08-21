"""宽书止损臂 @pod(权威书构造 = pod_legweight_arms.py 逐字同构, base look900 无帽) + 逐名成本均价深度止损。
king 源双跑: pinned(影子平价, 可能含样本内) / slow_ext(按年扩张 OOS 2024-26 折)。
臂: S0 无 / d25_n2_c42(在役参数) / d30_n2_c42(jpline 网格最优) / d25_n1_c42。
自校验: gross_pos≈1.378 / turnover≈0.0075 / sel≈216(影子实测)。
判据(决策用权衡表, 兑换率 = maxDD 降幅 / 净额代价; 逐年不作否决项)。
"""
import json, time, sys
import numpy as np
sys.path.insert(0, "/workspace")
from scipy.stats import rankdata
MT = np.load("/workspace/data/wide_fea_v2ext_meta.npz", allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; qvk = MT["qvk"]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts]); nA = len(E_ts); NW = 829
PW = np.load("/workspace/data/wide_panel_4h_v2ext.npz", allow_pickle=True)
pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
FN = PW["f_fund_now"]; IV = PW["f_fund_iv"]; R24 = PW["f_rev_24h"]; FE = PW["f_fund_ema_v1"]
KSRC = {"pinned": np.load("/workspace/shadow_bundle/slow_pred_pinned.npy"),
        "slow_ext": np.load("/workspace/exports_train/slow_lgbm_pred_ext.npy")}
def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    if ok.sum() >= 10: out[ok] = rankdata(v[ok]) / max(ok.sum() - 1, 1) - 0.5
    return out
COST_B = [(-0.25, 5.0, 0.85), (0.5, 6.0, 0.75), (2.0, 8.0, 0.55)]
def tier_of(q):
    t = np.full(len(q), 2, np.int8); t[q >= 1e6] = 1; t[q >= 5e6] = 0
    return t
def legs(SLOW):
    LR = {l: [] for l in ("king", "rev24", "fund")}; idx = []
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
    H = np.zeros(NW); Pi = np.ones(NW); sh = np.zeros(NW); cb = np.zeros(NW)
    cnt = np.zeros(NW, int); su = np.full(NW, -1); fires = 0
    rec = []; sels = []; gps = []; trn = []
    for i in range(nA):
        j = pw_row.get(int(E_ts[i]))
        if j is None: continue
        m = members[i]
        sc = {"king": SLOW[i, m], "rev24": -R24[j, m], "fund": FE[j, m]}
        w3 = w3_at(i)
        z = w3[0]*np.nan_to_num(xz(sc["king"])) + w3[1]*np.nan_to_num(xz(sc["rev24"])) + w3[2]*np.nan_to_num(xz(sc["fund"]))
        ok = np.isfinite(y4[i, m]); qv4h = np.expm1(np.clip(qvk[i, m], 0, 30)) * 48
        sel = ok & (qv4h >= 2.5e5)
        if sel.sum() < 80: continue
        w = np.where(sel, z, 0.0); w -= w[sel].mean()
        g = np.abs(w).sum()
        if g < 1e-9: continue
        w /= g; capw = 2.5 / max(int(sel.sum()), 1); w = np.clip(w, -capw, capw)
        g2 = np.abs(w).sum()
        if g2 > 1e-9: w /= g2
        tgt = np.zeros(NW); tgt[m] = w
        if depth is not None:
            bl = su > i
            if bl.any(): tgt[bl] = 0.0
        sm = H + 0.1 * (tgt - H); trade = sm - H
        sm = np.where(np.abs(trade) < 2.5e-4, H, sm); trade = sm - H
        tr = tier_of(qv4h); tabs = np.abs(trade[m])
        cbps = sum(tabs[tr == tt].sum() * (fr * mk + (1 - fr) * tk) for tt, (mk, tk, fr) in enumerate(COST_B))
        yv = np.nan_to_num(y4[i, m], nan=0.0)
        fnow = np.nan_to_num(FN[j, m], nan=0.0); ivv = IV[j, m]; ivv = np.where(np.isfinite(ivv) & (ivv > 0), ivv, 8.0)
        car = (sm[m] * fnow * (4.0 / ivv)).sum() * 1e4
        rec.append((int(E_ts[i]), float((sm[m] * yv).sum() * 1e4 - car - cbps)))
        sels.append(int(sel.sum())); gps.append(float(np.abs(sm).sum())); trn.append(float(np.abs(trade).sum()))
        # 成本均价深度(全宇宙价格路径)
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
            if fr2.any(): su[fr2] = i + cool; cnt[fr2] = 0; fires += int(fr2.sum())
        H = sm; Pi = Pi * (1.0 + yfull)
    nets = np.array([nn for _, nn in rec]); ts_ = np.array([t for t, _ in rec])
    yy = np.array([time.gmtime(int(t)).tm_year for t in ts_])
    cum = np.cumsum(nets); dd = cum - np.maximum.accumulate(cum)
    a24 = nets[yy >= 2024]
    return {"net_all": round(float(nets.mean()), 3), "net_2024on": round(float(a24.mean()), 3),
            "sharpe_2024on": round(float(a24.mean() / (a24.std() + 1e-12) * np.sqrt(6 * 365)), 2),
            "maxDD": round(float(-dd.min()), 0), "ES5": round(float(np.sort(nets)[:len(nets) // 20].mean()), 1),
            "by_year": {int(y): round(float(nets[yy == y].mean()), 3) for y in sorted(set(yy.tolist()))},
            "turnover": round(float(np.mean(trn)), 5), "fires": fires,
            "selftest": {"sel": round(float(np.mean(sels[-500:])), 0), "gross_pos": round(float(np.mean(gps[-500:])), 4)}}
ARMS = [("S0", None, 0, 0), ("d25_n2_c42", -0.25, 2, 42), ("d30_n2_c42", -0.30, 2, 42), ("d25_n1_c42", -0.25, 1, 42)]
out = {}
for ks, SLOW in KSRC.items():
    LRa, pos = legs(SLOW)
    out[ks] = {}
    for nm, d, n_, c in ARMS:
        out[ks][nm] = run(SLOW, LRa, pos, d, n_, c)
        print(ks, nm, json.dumps(out[ks][nm]), flush=True)
    S0 = out[ks]["S0"]
    for nm in ("d25_n2_c42", "d30_n2_c42", "d25_n1_c42"):
        r = out[ks][nm]
        cut = 1 - r["maxDD"] / max(S0["maxDD"], 1e-9); cost = 1 - r["net_all"] / max(S0["net_all"], 1e-9)
        out[ks][nm]["tradeoff"] = {"maxDD_cut": round(cut, 3), "net_cost": round(cost, 3), "ratio": round(cut / max(cost, 1e-6), 1)}
        print(ks, nm, "tradeoff", out[ks][nm]["tradeoff"], flush=True)
json.dump(out, open("/workspace/stop_arms_pod.json", "w"), indent=1)
print("STOP_ARMS_DONE", flush=True)
