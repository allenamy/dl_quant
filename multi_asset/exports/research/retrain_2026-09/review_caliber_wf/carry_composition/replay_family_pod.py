"""carry_composition (pod, READ-ONLY on /workspace/port_w10, /workspace/data): carry exposure of every replay-family arm
(a) on the 28 live-overlap anchors 08-26 04Z..08-30 20Z (excl. 08-29 20Z) and (b) by year 2022..2026, from the stored
W (blended book, file caliber) x v2ext panel rates f_fund_now*(4/f_fund_iv), device caliber (smr: demean non-zero set,
rescale to gross). + = book pays; all per unit gross. Also: band-short (rn8<=-10bp/8h) gross share and payment,
LP/SN gross shares, stored carry_ex vs recompute sanity, hist_v2 (replay input) vs v2ext panel fund equality at the 28 anchors,
and the scaled-carry net_ex bound. Usage: python replay_family_pod.py <npz path> [<npz path> ...]"""
import sys, os, json, time, numpy as np
def f(t): return time.strftime("%m-%d %HZ", time.gmtime(int(t)))
PW = np.load("/workspace/data/wide_panel_4h_v2ext.npz", allow_pickle=True); pts = PW["ts"].astype(np.int64); prow = {int(t): i for i, t in enumerate(pts)}
FN = np.asarray(PW["f_fund_now"], np.float64); IV = np.asarray(PW["f_fund_iv"], np.float64); psym = [str(s) for s in PW["symbols"]]; NW = len(psym)
IVf = np.where(np.isfinite(IV) & (IV > 0), IV, 8.0); R4 = np.nan_to_num(FN) * (4.0 / IVf); RN8 = np.where(np.isfinite(FN), FN * (8.0 / IVf), np.nan); BAND = np.isfinite(RN8) & (RN8 <= -0.0010)
OV = [N for N in range(1787716800, 1788120000 + 1, 14400) if N != 1788033600]; assert len(OV) == 28
yr = np.array([time.gmtime(int(t)).tm_year for t in pts])
# hist_v2 (replay input) vs v2ext at the 28 anchors
if "--panelcheck" in sys.argv:
    H2 = np.load("/workspace/port_w10/pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz", allow_pickle=True); h2row = {int(t): i for i, t in enumerate(H2["ts"].astype(np.int64))}
    assert [str(s) for s in H2["symbols"]] == psym
    d = []; dfe = []; nn = 0
    for N in OV:
        i, k = prow[N], h2row[N]
        a, b = np.nan_to_num(FN[i]), np.nan_to_num(np.asarray(H2["f_fund_now"][k], np.float64)); d.append(np.abs(a - b).max())
        a2, b2 = np.nan_to_num(np.asarray(PW["f_fund_ema_v1"][i], np.float64)), np.nan_to_num(np.asarray(H2["f_fund_ema_v1"][k], np.float64)); dfe.append(np.abs(a2 - b2).max())
        nn += int((np.isfinite(FN[i]) != np.isfinite(np.asarray(H2["f_fund_now"][k], np.float64))).sum())
    print(f"PANELCHECK hist_v2 vs v2ext on 28 anchors: max|f_fund_now diff| {max(d):.2e}, max|f_fund_ema_v1 diff| {max(dfe):.2e}, finite-mask mismatches {nn}; hist_v2 ts range {f(H2['ts'][0])}..{f(H2['ts'][-1])} n {len(H2['ts'])}")
def dm(w):
    nz = np.abs(w) > 1e-12; o = w.copy()
    if nz.any():
        o[nz] -= o[nz].mean(); g0 = np.abs(w).sum(); g1 = np.abs(o).sum()
        if g1 > 1e-9: o *= g0 / g1
    return o
def measure(W, ts):
    out = np.full((len(ts), 9), np.nan)   # carry_dm, carry_raw, pay_SN, pay_LP, LP, SN, band_g, band_pay, netlong
    for k, N in enumerate(ts):
        i = prow.get(int(N))
        if i is None: continue
        w = W[k].astype(np.float64); g = np.abs(w).sum()
        if g < 1e-9: continue
        r = R4[i]; s = dm(w); b = BAND[i]
        out[k] = [(s * r).sum() / g * 1e4, (w * r).sum() / g * 1e4, (s * r)[(s < 0) & (r < 0)].sum() / g * 1e4, (s * r)[(s > 0) & (r > 0)].sum() / g * 1e4,
                  np.abs(s[(s > 0) & (r > 0)]).sum() / g, np.abs(s[(s < 0) & (r < 0)]).sum() / g, np.abs(s[(s < 0) & b]).sum() / g, (s * r)[(s < 0) & b].sum() / g * 1e4, w.sum() / g]
    return out
LAB = ["carry_dm", "carry_raw", "pay_SN", "pay_LP", "LP", "SN", "band_g", "band_pay", "netlong"]
res = {}
for p in [a for a in sys.argv[1:] if a.endswith(".npz")]:
    tag = os.path.basename(p).replace("w10_ablation_series_", "").replace(".npz", "")
    z = np.load(p, allow_pickle=True); cols = [str(c) for c in z["cols"]]; Rc = z["d30_n2_c42_rec"]; W = z["d30_n2_c42_W"]; ts = Rc[:, cols.index("ts")].astype(np.int64)
    assert [str(s) for s in z["symbols"]] == psym
    cfgj = json.loads(str(z["config_json"])); M = measure(W, ts)
    ce = Rc[:, cols.index("carry_ex")]; gt = Rc[:, cols.index("gross_total")]; nx = Rc[:, cols.index("net_ex")]; px = Rc[:, cols.index("pnl_ex")]; cx = Rc[:, cols.index("cost_ex")]
    okm = np.isfinite(M[:, 0]); ovm = np.isin(ts, OV); yy = np.array([time.gmtime(int(t)).tm_year for t in ts])
    san = np.abs(ce[okm] - M[okm, 0] * gt[okm]).max()
    r = {"config": {k: cfgj[k] for k in ("W3FIX", "MEMBERS_TOPN", "TRADE_TOPN", "FTRIM", "CAL", "LEGS", "PHI", "FSEED")}, "n": int(len(ts)), "sanity_max|carry_ex - carry_dm*gross|": float(san),
         "overlap28": {"n": int((ovm & okm).sum()), **{l: float(np.nanmean(M[ovm, j])) for j, l in enumerate(LAB)}, "carry_dm_se": float(np.nanstd(M[ovm, 0], ddof=1) / np.sqrt((ovm & okm).sum())), "gross": float(gt[ovm].mean())},
         "by_year": {}}
    for y in sorted(set(yy.tolist())):
        m = (yy == y) & okm
        r["by_year"][int(y)] = {"n": int(m.sum()), **{l: float(np.nanmean(M[m, j])) for j, l in enumerate(LAB)}, "gross": float(gt[m].mean()),
                                "carry_ex_perNAV": float(ce[m].mean()), "net_ex_perNAV": float(nx[m].mean()), "pnl_ex_perNAV": float(px[m].mean()), "cost_ex_perNAV": float(cx[m].mean()),
                                "p10": float(np.nanpercentile(M[m, 0], 10)), "p50": float(np.nanpercentile(M[m, 0], 50)), "p90": float(np.nanpercentile(M[m, 0], 90)),
                                "frac_anchors_ge_2.0": float((M[m, 0] >= 2.0).mean()),
                                "roll28_max": float(np.nanmax(np.convolve(np.nan_to_num(M[m, 0]), np.ones(28) / 28, "valid"))) if m.sum() >= 28 else float("nan"),
                                "roll28_p90": float(np.nanpercentile(np.convolve(np.nan_to_num(M[m, 0]), np.ones(28) / 28, "valid"), 90)) if m.sum() >= 28 else float("nan")}
    m24 = (yy >= 2024) & okm
    r["2024on"] = {"n": int(m24.sum()), "net_ex_perNAV": float(nx[m24].mean()), "carry_ex_perNAV": float(ce[m24].mean()), "carry_dm_pergross": float(np.nanmean(M[m24, 0])), "gross": float(gt[m24].mean()),
                   "sharpe_ex": float(nx[m24].mean() / nx[m24].std(ddof=1) * np.sqrt(2190)), "pay_SN": float(np.nanmean(M[m24, 2])), "band_pay": float(np.nanmean(M[m24, 7])), "band_g": float(np.nanmean(M[m24, 6]))}
    res[tag] = r
    print(f"\n### {tag}  cfg W3FIX={cfgj['W3FIX']} MEMBERS_TOPN={cfgj['MEMBERS_TOPN']} TRADE_TOPN={cfgj['TRADE_TOPN']} FTRIM={cfgj['FTRIM']} CAL={cfgj['CAL']} FSEED={cfgj['FSEED']} | n {len(ts)} | sanity max|carry_ex - dm*gross| {san:.2e}")
    o = r["overlap28"]; print(f"  overlap28 (n {o['n']}): carry_dm {o['carry_dm']:+.3f} (se {o['carry_dm_se']:.3f}) raw {o['carry_raw']:+.3f} | pay_SN {o['pay_SN']:+.3f} pay_LP {o['pay_LP']:+.3f} | LP {o['LP']:.3f} SN {o['SN']:.3f} | band shorts g {o['band_g']:.3f} pay {o['band_pay']:+.3f} | netlong {o['netlong']:+.3f} gross {o['gross']:.3f}")
    print("  year    n  carry_dm   p10   p50   p90  roll28max roll28p90 frac>=2 | pay_SN pay_LP |   LP    SN | band_g band_pay | netlong gross | carry_ex/NAV net_ex/NAV pnl_ex cost_ex")
    for y, v in r["by_year"].items():
        print(f"  {y} {v['n']:5d} {v['carry_dm']:+8.3f} {v['p10']:+5.2f} {v['p50']:+5.2f} {v['p90']:+5.2f} {v['roll28_max']:+8.3f} {v['roll28_p90']:+8.3f} {v['frac_anchors_ge_2.0']:6.3f} | {v['pay_SN']:+6.3f} {v['pay_LP']:+6.3f} | {v['LP']:.3f} {v['SN']:.3f} | {v['band_g']:.3f} {v['band_pay']:+6.3f} | {v['netlong']:+.3f} {v['gross']:.3f} | {v['carry_ex_perNAV']:+.3f} {v['net_ex_perNAV']:+.3f} {v['pnl_ex_perNAV']:+.3f} {v['cost_ex_perNAV']:.3f}")
    a = r["2024on"]; print(f"  2024on: net_ex/NAV {a['net_ex_perNAV']:+.4f} sharpe {a['sharpe_ex']:.2f} carry_ex/NAV {a['carry_ex_perNAV']:+.4f} (per gross {a['carry_dm_pergross']:+.3f}, gross {a['gross']:.3f}) pay_SN {a['pay_SN']:+.3f} band_g {a['band_g']:.3f} band_pay {a['band_pay']:+.3f}")
json.dump(res, open("/workspace/review_scratch/carry_composition/replay_family.json", "a"), indent=1); print("\nsaved (appended) replay_family.json")
