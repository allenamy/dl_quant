"""r16 analysis. Windows, statistic, partition, nulls, tail and verdict rule all per PREREG_r16 (frozen, sha asserted).
Bootstrap = closed-form UTC-day block (r8_inbook/fastboot.py, as in analyze12.py). Regime labels = analyze12.build_labels
verbatim, on the v2 primitives (sha asserted)."""
import numpy as np, json, os, glob, calendar, time, hashlib
R = "/workspace/uplift_2026-09-11/r16_asym_band"
PREREG = R + "/PREREG_r16_asym_band_2026-09-12.md"
PRIM = "/workspace/uplift_2026-09-11/r12_regime/causal_primitives_r12_v2.npz"
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
assert sha(PREREG) == "68bc4fdb7f619dbb9ca10fc868f86b1f31f227029f7b58aead309f4620ab2b0c"
assert sha(PRIM) == "0510f456f63f4963cae757a0fd86251477089de1d266b8b8859092f9f73cf08f"
assert sha(R + "/w10_r16.py") == "caf7ffdb3bde581bc34438d5e9df695546564c0669bbaa5812e5c9b62e4a87a0"
APY = 2190; B = 2000; K = 6
TS_MAX = calendar.timegm((2026, 8, 30, 20, 0, 0)); WARM = 900
KING_TS = calendar.timegm((2024, 1, 1, 0, 0, 0))
LEV = 2.0; MULT = 1.4042; HALT = -0.04; ALERT = -0.0268; DDLIM = -0.25
LAMBDAS = [1.0, 0.8096, 0.2545]
ARMS = ["X0", "X1", "X2", "X3", "X4", "X5"]; SEEDS = [42, 2027]
# ---------- bootstrap ----------
def prep(x, days):
    ud, inv = np.unique(days, return_inverse=True); nd = len(ud)
    return nd, np.bincount(inv, minlength=nd).astype(float), np.bincount(inv, weights=x, minlength=nd), np.bincount(inv, weights=x * x, minlength=nd)
def draws(nd, k): return np.random.default_rng([20260905, k]).integers(0, nd, size=(B, nd))
def boot_mean(x, days, k):
    nd, n, s, q = prep(x, days); idx = draws(nd, k); return s[idx].sum(1) / n[idx].sum(1)
def boot_dmean(x, y, days, k):
    nd, n, sx, qx = prep(x, days); _, _, sy, qy = prep(y, days); idx = draws(nd, k); N = n[idx].sum(1)
    return sx[idx].sum(1) / N - sy[idx].sum(1) / N
def ci(v, a=0.025): return [float(np.quantile(v, a)), float(np.quantile(v, 1 - a))]
A_BONF = 0.05 / (2 * K)
# ---------- regime labels (analyze12.build_labels verbatim, v2 primitives) ----------
P = np.load(PRIM, allow_pickle=True); pc = {str(c): i for i, c in enumerate(P["cols"])}; pr = P["rec"]
pts = pr[:, pc["ts"]].astype(np.int64)
A_ew = pr[:, pc["A_ew"]]; B_br = pr[:, pc["B_breadth"]]; D_dis = pr[:, pc["D_disp_bps"]]
SIGF = pr[:, pc["SIGF"]]; FMED = pr[:, pc["FMED"]]; SPAY = pr[:, pc["SPAY"]]; n = len(pts)
def trail_mean(x, w):
    out = np.full(n, np.nan)
    for i in range(w, n):
        s = x[i - w:i]
        if np.isfinite(s).all(): out[i] = s.mean()
    return out
def trail_sum(x, w):
    out = np.full(n, np.nan)
    for i in range(w, n):
        s = x[i - w:i]
        if np.isfinite(s).all(): out[i] = s.sum()
    return out
BRD6 = trail_mean(B_br, 6); XSV30 = trail_mean(D_dis, 30); R24 = trail_sum(A_ew, 6); R72 = trail_sum(A_ew, 18)
MV30 = np.full(n, np.nan)
for i in range(30, n):
    s = A_ew[i - 30:i]
    if np.isfinite(s).all(): MV30[i] = 1e4 * s.std()
PRIMD = {"ts": pts, "BRD6": BRD6, "XSV30": XSV30, "MV30": MV30, "SIGF": SIGF, "FMED": FMED, "SPAY": SPAY, "R24": R24, "R72": R72}
def build_labels(ts):
    idx = {int(t): i for i, t in enumerate(pts)}; sel = np.array([idx[int(t)] for t in ts])
    g = {k: v[sel] for k, v in PRIMD.items() if k != "ts"}; L = {}
    L["YEAR"] = np.array(["Y%d" % time.gmtime(int(t)).tm_year for t in ts], object)
    def tert(x, nm):
        f = np.isfinite(x); q1, q2 = np.nanquantile(x[f], [1/3, 2/3]); o = np.full(len(x), nm + "_NA", object)
        o[f & (x <= q1)] = nm + "_T1"; o[f & (x > q1) & (x <= q2)] = nm + "_T2"; o[f & (x > q2)] = nm + "_T3"; return o
    L["BREADTH"] = tert(g["BRD6"], "BRD"); L["XSVOL"] = tert(g["XSV30"], "XSV"); L["MKTVOL"] = tert(g["MV30"], "MV"); L["SIGFT"] = tert(g["SIGF"], "SIGF")
    ev = {}
    ev["POSTCRASH"] = np.isfinite(g["R24"]) & (g["R24"] <= -0.02)
    ev["BROADRALLY"] = np.isfinite(g["R24"]) & np.isfinite(g["BRD6"]) & (g["R24"] >= 0.02) & (g["BRD6"] >= 0.60)
    ev["ALTSURGE"] = np.isfinite(g["R72"]) & (g["R72"] >= 0.08)
    ev["ALTSURGE_BROAD"] = ev["ALTSURGE"] & np.isfinite(g["BRD6"]) & (g["BRD6"] >= 0.60)
    f = np.isfinite(g["FMED"]); d1 = np.nanquantile(g["FMED"][f], 0.10); ev["DEEPNEG_MKT"] = f & (g["FMED"] <= d1)
    f2 = np.isfinite(g["SPAY"]); d9 = np.nanquantile(g["SPAY"][f2], 0.90); ev["DEEPNEG_SHORT"] = f2 & (g["SPAY"] >= d9)
    f3 = np.isfinite(g["R72"]); qs = np.nanquantile(g["R72"][f3], [.2, .4, .6, .8]); o = np.full(len(ts), "R72_NA", object)
    o[f3] = np.array(["R72_Q%d" % (np.searchsorted(qs, v) + 1) for v in g["R72"][f3]], object); L["R72LADDER"] = o
    return L, ev
# ---------- tail helpers ----------
def dayret(g_bps, days):
    ud = np.unique(days); out = np.zeros(len(ud))
    for i, d in enumerate(ud): out[i] = np.prod(1.0 + LEV * g_bps[days == d] * 1e-4) - 1.0
    return ud, out
def maxdd(r):
    eq = np.concatenate([[1.0], np.cumprod(1.0 + r)]); return float((eq / np.maximum.accumulate(eq) - 1.0).min())
def roll1y(ud, r):
    cg, dd = [], []
    for s in range(len(ud)):
        e = np.searchsorted(ud, ud[s] + 365 * 86400, side="right")
        if e - s < 300 or ud[e - 1] - ud[s] < 350 * 86400: continue
        cum = np.cumprod(1.0 + r[s:e]) - 1.0; cg.append(float(cum[-1])); dd.append(float(cum.min()))
    return np.array(cg), np.array(dd)
def tail(rd, ud):
    yrs = (ud[-1] - ud[0]) / (365.25 * 86400); cg, dd = roll1y(ud, rd)
    return {"day_sigma_pct": float(rd.std(ddof=1) * 100), "worst_day_pct": float(rd.min() * 100),
            "worst_day_utc": time.strftime("%Y-%m-%d", time.gmtime(int(ud[int(np.argmin(rd))]))), "maxdd_pct": maxdd(rd) * 100,
            "n_halt": int((rd <= HALT).sum()), "n_alert": int((rd <= ALERT).sum()), "halt_per_yr": float((rd <= HALT).sum() / yrs),
            "alert_per_yr": float((rd <= ALERT).sum() / yrs), "median_1y_cagr_pct": float(np.median(cg) * 100),
            "p_1y_dd_ge25": float((dd <= DDLIM).mean()), "n_1y_windows": int(len(cg)), "years": float(yrs)}
# ---------- load ----------
def load(tag):
    Z = np.load(R + "/arms/%s.npz" % tag, allow_pickle=True); cfg = json.loads(str(Z["config_json"]))
    rec = Z["rec"]; aux = Z["R16A"]; ac = {str(c): i for i, c in enumerate(Z["R16A_cols"])}
    assert np.abs(rec[:, 18] - (rec[:, 19] - rec[:, 20] - rec[:, 21])).max() < 1e-9, "net_ex identity " + tag
    return {"cfg": cfg, "rec": rec, "aux": aux, "ac": ac, "ts": rec[:, 0].astype(np.int64)}
OUT = {"_meta": {"prereg_sha256": sha(PREREG), "device_sha256": sha(R + "/w10_r16.py"), "primitives": PRIM, "primitives_sha256": sha(PRIM),
                 "TS_MAX": TS_MAX, "WARM": WARM, "KING_LIVE_FROM": KING_TS, "LEV": LEV, "LIVE_SIGMA_MULT": MULT, "B": B, "K": K, "lambdas": LAMBDAS,
                 "bonferroni_ci_level": 1 - 0.05 / K}}
def alpha_stats(a, mask, days, ref=None):
    rec, aux, ac = a["rec"], a["aux"], a["ac"]; gt = rec[:, 5]; g = rec[:, 18] / gt
    x = g[mask]; d = days[mask]; sd = float(x.std(ddof=1))
    o = {"n": int(mask.sum()), "mean_g": float(x.mean()), "ci95_k0": ci(boot_mean(x, d, 0)), "sharpe": float(x.mean() / sd * np.sqrt(APY)),
         "se_sharpe": float(np.sqrt(APY / mask.sum())), "sd_g": sd,
         "pnl_over_gross": float((rec[mask, 19] / gt[mask]).mean()), "carry_over_gross": float((rec[mask, 20] / gt[mask]).mean()),
         "cost_over_gross": float((rec[mask, 21] / gt[mask]).mean()),
         "turn_matched_file": float((rec[mask, 17] / gt[mask]).mean()), "turn_matched_exec": float((aux[mask, ac["turn_ex_all"]] / gt[mask]).mean()),
         "turn_raw_file": float(rec[mask, 17].mean()), "gross_total_mean": float(gt[mask].mean())}
    o["cost_rate_bps_per_unit_turn_exec"] = o["cost_over_gross"] / o["turn_matched_exec"]
    o["survival_lambda"] = {str(l): 1.0 - l * o["cost_over_gross"] for l in LAMBDAS}
    if ref is not None:
        gr = (ref["rec"][:, 18] / ref["rec"][:, 5])[mask]
        dv0 = boot_dmean(x, gr, d, 0); dv9 = boot_dmean(x, gr, d, 9)
        dpnl = o["pnl_over_gross"] - float((ref["rec"][mask, 19] / ref["rec"][mask, 5]).mean())
        dcar = o["carry_over_gross"] - float((ref["rec"][mask, 20] / ref["rec"][mask, 5]).mean())
        dcost = o["cost_over_gross"] - float((ref["rec"][mask, 21] / ref["rec"][mask, 5]).mean())
        dg = float(x.mean() - gr.mean()); assert abs(dg - (dpnl - dcar - dcost)) < 1e-9
        o["dg"] = dg; o["dg_ci95_k0"] = ci(dv0); o["dg_ci95_k9"] = ci(dv9); o["dg_ci_bonf6"] = ci(dv0, A_BONF); o["dg_p_le0_k0"] = float((dv0 <= 0).mean())
        o["dpnl"] = dpnl; o["dcarry"] = dcar; o["dcost"] = dcost
        o["dg_lambda"] = {str(l): dpnl - dcar - l * dcost for l in LAMBDAS}
        o["dturn_matched_file"] = o["turn_matched_file"] - float((ref["rec"][mask, 17] / ref["rec"][mask, 5]).mean())
        o["dturn_matched_exec"] = o["turn_matched_exec"] - float((ref["aux"][mask, ref["ac"]["turn_ex_all"]] / ref["rec"][mask, 5]).mean())
        o["dsharpe"] = o["sharpe"] - float(gr.mean() / gr.std(ddof=1) * np.sqrt(APY))
        o["abs_dg_ge_0p23"] = bool(abs(dg) >= 0.23)
    return o
def mech(a, mask):
    aux, ac = a["aux"], a["ac"]; o = {}
    for ch in ("k", "f"):
        c = lambda nm: aux[mask, ac[ch + "_" + nm]]
        nzt = c("n_zt").sum(); nztm = c("n_zt_m").sum()
        o[ch] = {"mean_resid_after_zero_target": float(c("sum_abs_sm_zt").sum() / nzt) if nzt > 0 else None,
                 "mean_resid_after_zero_target_members": float(c("sum_abs_sm_zt_m").sum() / nztm) if nztm > 0 else None,
                 "zt_names_per_anchor": float(c("n_zt").mean()), "zt_member_names_per_anchor": float(c("n_zt_m").mean()),
                 "zt_stalled_share": float(c("n_zt_stalled").sum() / nzt) if nzt > 0 else None,
                 "n_gap_per_anchor": float(c("n_gap").mean()), "n_DR_per_anchor": float(c("n_DR").mean()),
                 "n_DR_banded_per_anchor": float(c("n_DR_banded").mean()), "n_RI_banded_per_anchor": float(c("n_RI_banded").mean()),
                 "n_flip_per_anchor": float(c("n_flip").mean()), "n_flip_banded_per_anchor": float(c("n_flip_banded").mean()),
                 "n_exempt_per_anchor": float(c("n_exempt").mean()), "n_exempt_moved_per_anchor": float(c("n_exempt_moved").mean()),
                 "anchors_with_exempt_moved": int((c("n_exempt_moved") > 0).sum()), "exempt_abs_dw_per_anchor": float(c("exempt_abs_dw").mean())}
    o["anchors_with_exempt_moved_any_chain"] = int(((aux[mask, ac["k_n_exempt_moved"]] + aux[mask, ac["f_n_exempt_moved"]]) > 0).sum())
    o["total_exempted_names"] = float((aux[mask, ac["k_n_exempt"]] + aux[mask, ac["f_n_exempt"]]).sum())
    return o
for sd in SEEDS:
    A0 = load("GP_s%d_aux1" % sd); ts0 = A0["ts"]
    mT = ts0 <= TS_MAX; mA = mT.copy(); mA[:WARM] = False; mK = mA & (ts0 >= KING_TS)
    assert mA.sum() == 9138 and mT.sum() == 10038, (mA.sum(), mT.sum())
    days = (ts0 // 86400) * 86400; LAB, EV = build_labels(ts0)
    S = {"n_W_ALPHA": int(mA.sum()), "n_W_TAIL": int(mT.sum()), "n_KING_LIVE": int(mK.sum()),
         "n_W_ALPHA_before_2024": int((mA & (ts0 < KING_TS)).sum()),
         "n_W_ALPHA_leg_king_exactly_zero_before_2024": int((mA & (ts0 < KING_TS) & (A0["rec"][:, 11] == 0.0)).sum())}
    # F10 prefix: first rec anchor with any finite F10 pred (device L120-135 alignment)
    TG = np.load("/workspace/dlw_v4raw/data/dlw_targets.npz", allow_pickle=True); dts = TG["E_ts"].astype(np.int64)
    pd_ = np.load("/workspace/review_scratch/health_check/dev_v4/f8_2026-08-22/preds/f10_A0_s%d.npy" % sd, mmap_mode="r")
    rmap = {int(t): k for k, t in enumerate(dts)}; fin = np.array([bool(np.isfinite(pd_[rmap[int(t)]]).any()) if int(t) in rmap else False for t in ts0])
    first = int(np.argmax(fin)) if fin.any() else -1
    S["f10_first_finite_anchor_index"] = first; S["f10_first_finite_ts"] = time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(ts0[first]))) if first >= 0 else None
    S["n_W_ALPHA_before_f10_first_finite"] = int((mA & (np.arange(len(ts0)) < first)).sum()) if first >= 0 else None
    arms = {}
    S["A0"] = {"alpha": alpha_stats(A0, mA, days), "king_live": alpha_stats(A0, mK, days), "mech": mech(A0, mA)}
    ud, rd = dayret((A0["rec"][:, 18] / A0["rec"][:, 5])[mT], days[mT]); mu = rd.mean()
    S["A0"]["tail"] = {"replay": tail(rd, ud), "live_vol": tail(mu + MULT * (rd - mu), ud)}
    S["A0"]["regime"] = {}
    g0 = A0["rec"][:, 18] / A0["rec"][:, 5]
    for fam, lab in LAB.items():
        for u in sorted(set(lab[mA])):
            k = mA & (lab == u)
            if k.sum() >= 30: S["A0"]["regime"][u] = {"n": int(k.sum()), "mean_g": float(g0[k].mean()), "sharpe": float(g0[k].mean() / g0[k].std(ddof=1) * np.sqrt(APY))}
    for nm, msk in EV.items():
        for side, k in (("", mA & msk), ("_NOT", mA & ~msk)):
            if k.sum() >= 30: S["A0"]["regime"][nm + side] = {"n": int(k.sum()), "mean_g": float(g0[k].mean()), "sharpe": float(g0[k].mean() / g0[k].std(ddof=1) * np.sqrt(APY))}
    assert len(S["A0"]["regime"]) == 34, len(S["A0"]["regime"])
    for xm in ARMS:
        a = load("A_%s_s%d" % (xm, sd)); assert np.array_equal(a["ts"], ts0), xm
        assert a["cfg"]["R16"]["XMODE"] == xm and a["cfg"]["R16"]["XNULL"] == 0
        o = {"alpha": alpha_stats(a, mA, days, A0), "king_live": alpha_stats(a, mK, days, A0), "mech": mech(a, mA)}
        g = a["rec"][:, 18] / a["rec"][:, 5]
        ud, rd = dayret(g[mT], days[mT]); mu = rd.mean()
        o["tail"] = {"replay": tail(rd, ud), "live_vol": tail(mu + MULT * (rd - mu), ud)}
        reg = {}
        for u in S["A0"]["regime"]:
            if u in EV or u.endswith("_NOT"):
                base = u[:-4] if u.endswith("_NOT") else u; k = mA & (~EV[base] if u.endswith("_NOT") else EV[base])
            else:
                k = np.zeros(len(ts0), bool)
                for fam, lab in LAB.items(): k |= (lab == u)
                k &= mA
            x = g[k]; dd = boot_dmean(x, g0[k], days[k], 0)
            reg[u] = {"n": int(k.sum()), "mean_g": float(x.mean()), "sharpe": float(x.mean() / x.std(ddof=1) * np.sqrt(APY)), "se_sharpe": float(np.sqrt(APY / k.sum())),
                      "dg": float(x.mean() - g0[k].mean()), "dg_ci95": ci(dd), "dcost": float((a["rec"][k, 21] / a["rec"][k, 5]).mean() - (A0["rec"][k, 21] / A0["rec"][k, 5]).mean()),
                      "dpnl": float((a["rec"][k, 19] / a["rec"][k, 5]).mean() - (A0["rec"][k, 19] / A0["rec"][k, 5]).mean())}
        o["regime"] = reg
        nulls = {}
        for d in (1, 2, 3):
            nz_ = load("N_%s_d%d_s%d" % (xm, d, sd)); assert np.array_equal(nz_["ts"], ts0)
            assert nz_["cfg"]["R16"]["XMODE"] == xm and nz_["cfg"]["R16"]["XNULL"] == d
            gn = nz_["rec"][:, 18] / nz_["rec"][:, 5]
            st = alpha_stats(nz_, mA, days, A0)
            tv = boot_dmean(g[mA], gn[mA], days[mA], 0)
            nulls["d%d" % d] = {"dg_vs_A0": st["dg"], "dg_ci95": st["dg_ci95_k0"], "dturn_matched_file": st["dturn_matched_file"],
                                "dturn_matched_exec": st["dturn_matched_exec"], "dcost": st["dcost"], "dpnl": st["dpnl"],
                                "treat_minus_null": float(g[mA].mean() - gn[mA].mean()), "treat_minus_null_ci95": ci(tv),
                                "n_exempt_per_anchor": mech(nz_, mA)["k"]["n_exempt_per_anchor"] + mech(nz_, mA)["f"]["n_exempt_per_anchor"]}
        o["nulls"] = nulls
        o["nulls_beaten"] = int(sum(o["alpha"]["dg"] > v["dg_vs_A0"] for v in nulls.values()))
        arms[xm] = o
        print("s%d %-3s dg=%+.4f ci95=[%+.3f,%+.3f] bonf=[%+.3f,%+.3f] dpnl=%+.4f dcarry=%+.4f dcost=%+.4f dturn=%+.5f nulls_beaten=%d/3 | tail wd=%.2f%% halt/yr=%.2f mDD=%.1f%%" %
              (sd, xm, o["alpha"]["dg"], *o["alpha"]["dg_ci95_k0"], *o["alpha"]["dg_ci_bonf6"], o["alpha"]["dpnl"], o["alpha"]["dcarry"], o["alpha"]["dcost"],
               o["alpha"]["dturn_matched_file"], o["nulls_beaten"], o["tail"]["live_vol"]["worst_day_pct"], o["tail"]["live_vol"]["halt_per_yr"], o["tail"]["live_vol"]["maxdd_pct"]), flush=True)
    S["arms"] = arms; OUT["s%d" % sd] = S
# ---------- verdict per PREREG §9 ----------
V = {}
constr = all(OUT["s%d" % sd]["arms"]["X4"]["alpha"]["dg"] < OUT["s%d" % sd]["arms"]["X0"]["alpha"]["dg"] for sd in SEEDS)
for xm in ARMS:
    a42 = OUT["s42"]["arms"][xm]; a27 = OUT["s2027"]["arms"][xm]
    ca = a42["alpha"]["dg"] > 0 and a27["alpha"]["dg"] > 0
    cb = a42["alpha"]["dg_ci_bonf6"][0] > 0 and a27["alpha"]["dg_ci95_k0"][0] > 0
    cc = a42["nulls_beaten"] == 3 and a27["nulls_beaten"] == 3
    cd = all(OUT["s%d" % sd]["arms"][xm]["tail"]["live_vol"]["worst_day_pct"] >= OUT["s%d" % sd]["A0"]["tail"]["live_vol"]["worst_day_pct"] - 0.5 and
             OUT["s%d" % sd]["arms"][xm]["tail"]["live_vol"]["halt_per_yr"] <= OUT["s%d" % sd]["A0"]["tail"]["live_vol"]["halt_per_yr"] for sd in SEEDS)
    ce = all(len(set(np.sign(v) for v in OUT["s%d" % sd]["arms"][xm]["alpha"]["dg_lambda"].values())) == 1 for sd in SEEDS)
    rej = (a42["alpha"]["dg"] < 0 and a27["alpha"]["dg"] < 0) or a42["alpha"]["dg_ci95_k0"][1] < 0 or a27["alpha"]["dg_ci95_k0"][1] < 0
    verdict = "ADMIT" if (ca and cb and cc and cd and ce and constr) else ("REJECT" if rej else "UNDECIDED")
    V[xm] = {"a_dg_pos_both": ca, "b_bonf_s42_and_ci_s2027": cb, "c_beats_3_nulls_both": cc, "d_tail_not_worse": cd, "e_lambda_sign_stable": ce, "f_construction_X4_lt_X0": constr, "verdict": verdict}
    print(xm, V[xm], flush=True)
OUT["verdict"] = V; OUT["construction_check_pass"] = constr
json.dump(OUT, open(R + "/receipts/RESULT_R16.json", "w"), indent=1); print("ANALYZE_DONE")
