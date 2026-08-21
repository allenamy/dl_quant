"""W2 两书配置装置 · 宽书逐锚序列生成器 @jpline(2026-08-22, Session 6737834a-W2)。
书构造 = pod_stop_arms_v3.py(devices_2026-08-21, 权威构造 = pod_legweight_arms 逐字同构)逐字移植, 输入改指 jpline 上的 pod 备份
/mnt/storage/private/work_hsy/pod_backup_2026-08-21/(META=wide_fea_hist_meta.npz, PANEL=wide_panel_4h_hist_v2.npz(正确 carry: f_fund_iv/f_fund_ema_v1),
KING=slow_pred_hist_oos.npy 按年扩张 OOS 折 2022-26)。臂: S0 无止损 / d30_n2_c42(止损层)。
新增逐锚仪器(不改书): 毛 pnl / carry / 成本 / gross_total(|sm| 全向量合计, 与 §J-bis 口径同) / gross_member(当锚成员内) / gross_sel /
nsel / 成员数 / 当锚触发数 / 三腿贡献(LEGC 同式) / w3 腿权; 权重向量 sm(float32)供重叠名核算。
复现收据: d30_n2_c42 的 net 必须与 pod_backup/nets_histv2_-30_2_42.npy 逐元素相等(maxabs<1e-6), S0 同 nets_histv2_0_0_0.npy。
输出: probe_artifacts/w2_wide_series.npz + w2_wide_summary.json。只读数据, 不碰实盘仓。
"""
import json, time, sys, os
import numpy as np
from scipy.stats import rankdata
B = "/mnt/storage/private/work_hsy/pod_backup_2026-08-21"; PD = "/mnt/storage/private/work_hsy/probe_artifacts"
t0 = time.time()
MT = np.load(f"{B}/wide_fea_hist_meta.npz", allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; qvk = MT["qvk"]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts]); nA = len(E_ts); NW = 829
PW = np.load(f"{B}/wide_panel_4h_hist_v2.npz", allow_pickle=True)
pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
FN = PW["f_fund_now"]; IV = PW["f_fund_iv"] if "f_fund_iv" in PW else np.full_like(PW["f_fund_now"], 8.0); R24 = PW["f_rev_24h"]; FE = PW["f_fund_ema_v1"] if "f_fund_ema_v1" in PW else PW["f_fund_ema"]
WSYM = [str(s) for s in PW["symbols"]]
SLOW = np.load(f"{B}/slow_pred_hist_oos.npy")
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
    cnt = np.zeros(NW, int); su = np.full(NW, -1)
    rec = []; WS = []
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
        pnl_raw = float((sm[m] * yv).sum() * 1e4)
        legc = []
        for leg in ("king", "rev24", "fund"):
            zz = np.nan_to_num(xz(sc[leg])); gl = np.abs(zz).sum()
            legc.append(float(w3[{"king": 0, "rev24": 1, "fund": 2}[leg]] * (zz / gl * yv).sum() * 1e4) if gl > 1e-9 else 0.0)
        fires_i = 0
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
            if fr2.any(): su[fr2] = i + cool; cnt[fr2] = 0; fires_i = int(fr2.sum())
        gm = float(np.abs(sm[m]).sum()); gsel = float(np.abs(sm[m][sel]).sum()); gt = float(np.abs(sm).sum())
        rec.append((int(E_ts[i]), float(pnl_raw - car - cbps), pnl_raw, float(car), float(cbps), gt, gm, gsel, int(sel.sum()), int(len(m)), fires_i,
                    legc[0], legc[1], legc[2], float(w3[0]), float(w3[1]), float(w3[2]), float(np.abs(trade).sum())))
        WS.append(sm.astype(np.float32))
        H = sm; Pi = Pi * (1.0 + yfull)
        if i % 2000 == 0: print("run depth", depth, i, "/", nA, round(time.time() - t0, 1), "s", flush=True)
    return np.array(rec), np.stack(WS)
LRa, pos = legs(SLOW); print("legs done", round(time.time() - t0, 1), "s", flush=True)
ARMS = [("S0", None, 0, 0, "nets_histv2_0_0_0.npy"), ("d30_n2_c42", -0.30, 2, 42, "nets_histv2_-30_2_42.npy")]
COLS = ["ts", "net", "pnl", "carry", "cost", "gross_total", "gross_member", "gross_sel", "nsel", "nmember", "fires", "leg_king", "leg_rev24", "leg_fund", "w3_king", "w3_rev24", "w3_fund", "turnover"]
out = {}; save = {}
for nm, d, n_, c, reff in ARMS:
    R, WS = run(SLOW, LRa, pos, d, n_, c)
    ref = np.load(f"{B}/{reff}")
    assert ref.shape[0] == R.shape[0], f"{nm}: n {R.shape[0]} vs ref {ref.shape[0]}"
    assert np.array_equal(ref[:, 0].astype(np.int64), R[:, 0].astype(np.int64)), f"{nm}: ts mismatch"
    dmax = float(np.max(np.abs(ref[:, 1] - R[:, 1])))
    ts_ = R[:, 0].astype(np.int64); net = R[:, 1]; yy = np.array([time.gmtime(int(t)).tm_year for t in ts_]); a24 = net[yy >= 2024]
    gt = R[:, 5]; gm = R[:, 6]
    out[nm] = {"maxabs_diff_vs_pod_backup": dmax, "n": int(len(net)), "first": time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(ts_[0]))), "last": time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(ts_[-1]))),
               "net_all": round(float(net.mean()), 4), "net_2024on": round(float(a24.mean()), 4), "sharpe_2024on": round(float(a24.mean() / a24.std(ddof=1) * np.sqrt(2190)), 3),
               "by_year": {int(y): round(float(net[yy == y].mean()), 3) for y in sorted(set(yy.tolist()))},
               "carry_mean": round(float(R[:, 3].mean()), 4), "cost_mean": round(float(R[:, 4].mean()), 4), "fires_total": int(R[:, 10].sum()),
               "gross_total_by_year": {int(y): round(float(gt[yy == y].mean()), 4) for y in sorted(set(yy.tolist()))},
               "gross_member_by_year": {int(y): round(float(gm[yy == y].mean()), 4) for y in sorted(set(yy.tolist()))},
               "gross_total_last500": round(float(gt[-500:].mean()), 4), "nsel_last500": round(float(R[-500:, 8].mean()), 0), "turnover_mean": round(float(R[:, 17].mean()), 5)}
    print("RECEIPT", nm, json.dumps(out[nm]), flush=True)
    save[f"{nm}_rec"] = R
    save[f"{nm}_W"] = WS
json.dump(out, open(f"{PD}/w2_wide_summary.json", "w"), indent=1, ensure_ascii=False)
np.savez_compressed(f"{PD}/w2_wide_series.npz", cols=np.array(COLS), symbols=np.array(WSYM), **save)
print("DONE", round(time.time() - t0, 1), "s", flush=True)
