"""PH · 相位审计的 regime/最坏五分位附读 @jpline(2026-08-22, Session 6737834a-PH)。
读 ph_series_2026-08-22.npz(两相位 S0/S1 逐锚净额)与 w2_live_series.npz(btc4/mkt_ew, 相位 0 锚), 按【日】对齐:
  regime 变量 = 该日 |BTC 4h 收益| 之和(日内绝对波动代理)与 日等权市场收益(方向); 五分位按全史日分位; 报每分位 Δ(相位3−相位0_mine) 日均(÷6 折 bps/锚)与 两相位各自日夏普; Q4=最坏(最高波动 / 最低市场收益)分位。
另给: 逐名义钟点(00/04/…/20Z)两相位的净额均值(相位敏感性与 STATE §2 "00/08/16Z 比 04/12/20Z 好" 的对照), 以及 2026 单年的 Δ CI。
输出 probe_artifacts/phase_alignment_regime_2026-08-22.json。
"""
import json, numpy as np, pandas as pd
PD = "/mnt/storage/private/work_hsy/probe_artifacts"
S = np.load(f"{PD}/ph_series_2026-08-22.npz", allow_pickle=True); L = np.load(f"{PD}/w2_live_series.npz", allow_pickle=True)
ANN6 = np.sqrt(6 * 365)


def daily(x, ats):
    d = (np.asarray(ats) // 86400).astype(np.int64); u, inv = np.unique(d, return_inverse=True)
    s = np.zeros(len(u)); np.add.at(s, inv, np.nan_to_num(x)); return u, s


def sh(v): return float(np.mean(v) / (np.std(v, ddof=1) + 1e-12) * np.sqrt(365.0))


out = {}
# regime variables on phase-0 (W2 live series) anchors, aggregated by day of nominal (= row ts + 1h)
ats0 = L["ts"].astype(np.int64) + 3600
ud, btc_abs = daily(np.abs(np.nan_to_num(L["btc4"])), ats0); _, mkt = daily(np.nan_to_num(L["mkt_ew"]), ats0)
for arm in ("S0", "S1"):
    u3, s3 = daily(S[f"mine_p3_{arm}_net"], S["mine_p3_ats"]); u0, s0 = daily(S[f"mine_p0_{arm}_net"], S["mine_p0_ats"])
    com = np.intersect1d(np.intersect1d(u3, u0), ud)
    i3 = np.searchsorted(u3, com); i0 = np.searchsorted(u0, com); ir = np.searchsorted(ud, com)
    A, B, V, M = s3[i3], s0[i0], btc_abs[ir], mkt[ir]
    res = {"n_days": int(len(com))}
    for nm, var, worst in (("btc_abs_vol", V, "Q4=highest"), ("mkt_ew_dir", M, "Q0=lowest")):
        q = np.searchsorted(np.quantile(var, [0.2, 0.4, 0.6, 0.8]), var, side="right")
        tab = {}
        for k in range(5):
            m = q == k
            tab[f"Q{k}"] = {"n": int(m.sum()), "delta_mean_bps_per_anchor": round(float((A[m] - B[m]).mean() / 6), 4), "sharpe_p3": round(sh(A[m]), 3), "sharpe_p0": round(sh(B[m]), 3),
                            "mean_p3_bps": round(float(A[m].mean() / 6), 4), "mean_p0_bps": round(float(B[m].mean() / 6), 4)}
        res[nm] = {"worst_is": worst, "quintiles": tab}
    # 2026 only
    yrs = pd.to_datetime(com * 86400, unit="s", utc=True).year.to_numpy()
    rng = np.random.default_rng(1); m26 = yrs == 2026
    if m26.sum() > 30:
        ds = [];
        for _ in range(2000):
            idx = rng.choice(np.where(m26)[0], m26.sum(), replace=True); ds.append(sh(A[idx]) - sh(B[idx]))
        res["y2026"] = {"n_days": int(m26.sum()), "delta_daily_sharpe": round(sh(A[m26]) - sh(B[m26]), 3), "ci95": [round(float(np.percentile(ds, 2.5)), 3), round(float(np.percentile(ds, 97.5)), 3)],
                        "delta_mean_bps_per_anchor": round(float((A[m26] - B[m26]).mean() / 6), 4)}
    out[arm] = res
# per nominal hour
hr = {}
for nm in ("mine_p0", "mine_p3", "newgen_p0"):
    ats = S[f"{nm}_ats"].astype(np.int64); h = (ats // 3600) % 24
    hr[nm] = {int(k): {"n": int((h == k).sum()), "S1_mean_bps": round(float(S[f"{nm}_S1_net"][h == k].mean()), 4), "S0_mean_bps": round(float(S[f"{nm}_S0_net"][h == k].mean()), 4)} for k in sorted(set(h.tolist()))}
out["by_nominal_hour"] = hr
json.dump(out, open(f"{PD}/phase_alignment_regime_2026-08-22.json", "w"), indent=1)
print(json.dumps(out, indent=1))
