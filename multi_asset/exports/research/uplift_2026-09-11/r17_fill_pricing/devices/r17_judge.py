#!/usr/bin/env python3
"""r17_judge.py — PREREG_r17 §6-§7 statistics: A0 under partial fills (DET + 5 STOCH seeds) vs archived 100%-fill A0, two
cost planes (lambda 0.8096 primary / 1.0 secondary), residual and turnover statistics from the R17 instrument, W_TAIL tail,
KING_LIVE, r12's 34 regime cells (verbatim r15 construction, cuts asserted), r6 BOOK-gap term before/after (exact reproduction
of j1_decomp's bootstrap first), and the re-based arms X1 / F / S. Runs only after RECEIPT_r17_drive_gateP.json says P1-P4 PASS.
Read-only. CPU only. Caliber is read from each artifact's config_json, never from the environment.
"""
import os, sys, json, time, hashlib, calendar
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "launch with a non-empty env whitelist as argv[1]"
BANNED = ('CAL','JUDGE','UPLIFT','PANEL','LOOK','WRULE','LEGS','PHI','FSEED','W3FIX','FTRIM','UMASK','SLOW','FPRED','MEMBERS_TOPN','COSTB','SLEEVE','KMOD','SEAT','RNSM','LTRIM','CDAMP','FUNDSCALE','FEMAT','TRADE_TOPN','REF_SKIP','PYTHON','OMP','MKL','R15','R16','R17','XMODE','XNULL','AUX16','FTPOS','OUT_TAG')
EXTRA = sorted(k for k in os.environ if k not in WHITE); assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
BAN = sorted(k for k in os.environ if k.startswith(BANNED)); assert BAN == [], ("CALIBER FLAG PRESENT", BAN)
ENV = dict(env_whitelist=sorted(WHITE), env_actual={k: os.environ[k] for k in sorted(os.environ)}, launch_cmdline=" ".join(sys.argv))
import numpy as np
ENV.update(python=sys.version.split()[0], numpy=np.__version__)
U = "/workspace/uplift_2026-09-11"; R = U + "/r17_fill_pricing"
PREREG_SHA = "a7533b922c68e6dc575b1eadd3d19f62d4d271393ec5d58621c31aa65f5ae272"; AMEND1_SHA = "70c8142ac4595fb4e83659daaa83cd3a68ba1284f103fd77ba3a14ba3f3269bd"
PRIM = U + "/r12_regime/causal_primitives_r12_v2.npz"; PRIM_SHA = "0510f456f63f4963cae757a0fd86251477089de1d266b8b8859092f9f73cf08f"
R12RC = U + "/r15_structural/receipts/RECEIPT_r12_regime_table.json"
def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
assert sha(R + "/PREREG_r17_fill_pricing_2026-09-12.md") == PREREG_SHA; assert sha(R + "/PREREG_AMENDMENT_1_r17_2026-09-12.md") == AMEND1_SHA
assert sha(PRIM) == PRIM_SHA, sha(PRIM)
G = json.load(open(R + "/receipts/RECEIPT_r17_drive_gateP.json")); assert all(G["gate"][p]["PASS"] for p in ("P1", "P2", "P3", "P4")), G["gate"]; assert G["fails"] == [], G["fails"]
FM = json.load(open(R + "/receipts/RECEIPT_r17_fillmodel_2026-09-12.json")); assert FM["table"]["sha256"] == G["fill_table_sha256"]
LIVE_GROSS_RATIO = FM["live_gross_ratio"]["median_excl_lt_0p8"]
K = 4; ALPHA_K = 0.05 / K; PCT_K = (100 * ALPHA_K / 2, 100 * (1 - ALPHA_K / 2)); NB = 2000; LAM_P, LAM_S = 0.8096, 1.0; RES_BPS = 0.23
UB = calendar.timegm((2026, 8, 30, 20, 0, 0)); K24 = calendar.timegm((2024, 1, 1, 0, 0, 0)); SEEDS = ("42", "2027"); STO = [1, 2, 3, 4, 5]
ARCH = {"42": "352ac36fb319532756da71e7cc405fb0dcde6f36f6e28a57f1f681177bcfd339", "2027": "aa44e18fb6bcfa7ef54f1708d070b0a2a7d5333f6cea63dfca94fecf59be1c7b"}
def load(p, key_rec="d30_n2_c42_rec", expect=None, r17=None):
    Z = np.load(p, allow_pickle=True); C = [str(c) for c in Z["cols"]]; rec = np.asarray(Z[key_rec], float); cfg = json.loads(str(Z["config_json"]))
    assert cfg["CAL"] == "log" and cfg["PHI"] == 0.45 and cfg["LEGS"] == "101" and cfg["WRULE"] == "msharpe" and cfg["W3FIX"] is None and cfg["UMASK_SCOPE"] == "m1" and cfg["LOOK"] == 900 and cfg["FTRIM"] == "zero" and cfg["MEMBERS_TOPN"] == 829, cfg
    assert cfg["COSTB_JSON"].endswith("costb_PWR_G230k.json") and cfg["SLOW_NPY"].endswith("SLOW_v3_on_v4axis.npy"), cfg
    if expect:
        for k, v in expect.items(): assert cfg[k] == v, (k, cfg[k], v)
    if r17 is not None:
        for k, v in r17.items(): assert cfg["R17"][k] == v, (k, cfg["R17"][k], v)
        assert cfg["R17"]["R17_TABLE_SHA256"] == G["fill_table_sha256"] and cfg["R17"]["R17_GROSS_USDT"] == 232000.0, cfg["R17"]
    col = lambda k: rec[:, C.index(k)]; ts = col("ts").astype(np.int64); gt = col("gross_total")
    d = dict(ts=ts, gt=gt, g=col("net_ex") / gt, pnl=col("pnl_ex") / gt, car=col("carry_ex") / gt, cst=col("cost_ex") / gt, tau_raw=col("turnover"), tau=col("turnover") / gt, w3k=col("w3_king"), w3f=col("w3_fund"), nl=col("netlong"), cfg=cfg, sha=sha(p), path=p, cols=C, rec=rec)
    assert np.allclose(d["pnl"] - d["car"] - d["cst"], d["g"], atol=1e-9)
    d["WT"] = ts <= UB; d["WA"] = d["WT"].copy(); d["WA"][:900] = False; assert d["WA"].sum() == 9138 and d["WT"].sum() == 10038; d["KL"] = ts >= K24; assert (d["WA"] & d["KL"]).sum() == 5838
    if "d30_n2_c42_R17" in Z:
        IC = [str(c) for c in Z["d30_n2_c42_R17_cols"]]; I = np.asarray(Z["d30_n2_c42_R17"], float); assert I.shape[0] == len(ts), (I.shape, len(ts))
        d["I"] = {c: I[:, IC.index(c)] for c in IC}
    return d
A0 = {s: load(U + "/r3k/arms/A0_PWR230k_s%s.npz" % s, "rec", dict(FTPOS=0, SEATNET=0)) for s in SEEDS}
for s in SEEDS: assert A0[s]["sha"] == ARCH[s]
assert abs(A0["42"]["g"][A0["42"]["WA"]].mean() - 0.6341957) < 5e-7 and abs(A0["42"]["tau"][A0["42"]["WA"]].mean() - 0.0540270) < 5e-7 and abs(A0["42"]["tau_raw"][A0["42"]["WA"]].mean() - 0.03032) < 5e-6
DET = {s: load(R + "/arms/A0DET_s%s.npz" % s, expect=dict(FTPOS=0, SEATNET=0), r17=dict(R17_FILL=1, R17_MODE="det", R17_X1=0)) for s in SEEDS}
STOC = {(k, s): load(R + "/arms/A0STO%d_s%s.npz" % (k, s), expect=dict(FTPOS=0, SEATNET=0), r17=dict(R17_FILL=1, R17_MODE="stoch", R17_SEED=k, R17_X1=0)) for k in STO for s in SEEDS}
ARM100 = {("X1", s): load(U + "/r16_asym_band/arms/A_X1_s%s.npz" % s, "rec", dict(FTPOS=0, SEATNET=0)) for s in SEEDS}
ARM100.update({("F", s): load(U + "/r15_structural/arms/F_s%s.npz" % s, expect=dict(FTPOS=1, SEATNET=0)) for s in SEEDS}); ARM100.update({("S", s): load(U + "/r15_structural/arms/S_s%s.npz" % s, expect=dict(FTPOS=0, SEATNET=1)) for s in SEEDS})
ARMPF = {("X1", s): load(R + "/arms/X1DET_s%s.npz" % s, expect=dict(FTPOS=0, SEATNET=0), r17=dict(R17_FILL=1, R17_MODE="det", R17_X1=1)) for s in SEEDS}
ARMPF.update({("F", s): load(R + "/arms/FDET_s%s.npz" % s, expect=dict(FTPOS=1, SEATNET=0), r17=dict(R17_FILL=1, R17_MODE="det", R17_X1=0)) for s in SEEDS}); ARMPF.update({("S", s): load(R + "/arms/SDET_s%s.npz" % s, expect=dict(FTPOS=0, SEATNET=1), r17=dict(R17_FILL=1, R17_MODE="det", R17_X1=0)) for s in SEEDS})
ts = A0["42"]["ts"]; WA = A0["42"]["WA"]; WT = A0["42"]["WT"]; KL = A0["42"]["KL"]
for x in list(DET.values()) + list(STOC.values()) + list(ARM100.values()) + list(ARMPF.values()): assert np.array_equal(x["ts"], ts)
DAY = np.array([time.strftime("%Y%m%d", time.gmtime(int(t))) for t in ts]); YEAR = np.array([time.gmtime(int(t)).tm_year for t in ts])
def glam(x, lam): return x["pnl"] - x["car"] - lam * x["cst"]
# ------------------------------------------------------------------ bootstrap core (UTC-day blocks)
_DRAW = {}
def draws(nd):
    if nd not in _DRAW: _DRAW[nd] = np.stack([np.random.default_rng([20260905, k]).integers(0, nd, nd) for k in range(NB)])
    return _DRAW[nd]
def boot(d, mask):
    idx = np.nonzero(mask)[0]
    if len(idx) < 10: return dict(ci95=[np.nan, np.nan], ci99K=[np.nan, np.nan], se=np.nan, n_days=0)
    dd = {}
    for k in idx: dd.setdefault(DAY[k], []).append(k)
    keys = sorted(dd); tot = np.array([d[dd[k]].sum() for k in keys]); cnt = np.array([len(dd[k]) for k in keys], float); r = draws(len(keys)); ms = tot[r].sum(1) / cnt[r].sum(1)
    return dict(ci95=[float(np.percentile(ms, 2.5)), float(np.percentile(ms, 97.5))], ci99K=[float(np.percentile(ms, PCT_K[0])), float(np.percentile(ms, PCT_K[1]))], se=float(ms.std(ddof=1)), n_days=len(keys))
def shp(x): return float(x.mean() / x.std(ddof=1) * np.sqrt(2190))
def block(arm, lam_arm, base, lam_base, mask):
    ga = glam(arm, lam_arm); gb = glam(base, lam_base); d = ga - gb; n = int(mask.sum()); b = boot(d, mask)
    o = dict(n=n, lam_arm=lam_arm, lam_base=lam_base, g_arm=float(ga[mask].mean()), g_base=float(gb[mask].mean()), dg=float(d[mask].mean()), **b, sharpe_arm=shp(ga[mask]), sharpe_base=shp(gb[mask]), sharpe_se=float(np.sqrt(2190 / n)),
             dpnl=float((arm["pnl"] - base["pnl"])[mask].mean()), dcarry=float((arm["car"] - base["car"])[mask].mean()), dcost=float((lam_arm * arm["cst"] - lam_base * base["cst"])[mask].mean()),
             pnl_arm=float(arm["pnl"][mask].mean()), carry_arm=float(arm["car"][mask].mean()), cost_arm_lam=float(lam_arm * arm["cst"][mask].mean()), cost_arm_raw=float(arm["cst"][mask].mean()),
             pnl_base=float(base["pnl"][mask].mean()), carry_base=float(base["car"][mask].mean()), cost_base_lam=float(lam_base * base["cst"][mask].mean()),
             tau_exec_matched_arm=float(arm["tau"][mask].mean()), tau_matched_base=float(base["tau"][mask].mean()), tau_raw_arm=float(arm["tau_raw"][mask].mean()), tau_raw_base=float(base["tau_raw"][mask].mean()))
    if "I" in arm: o["tau_intent_matched_arm"] = float((arm["I"]["tau_intent"] / arm["gt"])[mask].mean())
    assert abs(o["dpnl"] - o["dcarry"] - o["dcost"] - o["dg"]) < 1e-9
    o["by_year"] = {int(y): dict(n=int((mask & (YEAR == y)).sum()), g_arm=float(ga[mask & (YEAR == y)].mean()), g_base=float(gb[mask & (YEAR == y)].mean()), dg=float(d[mask & (YEAR == y)].mean())) for y in sorted(set(YEAR[mask].tolist()))}
    o["abs_dg_ge_res"] = bool(abs(o["dg"]) >= RES_BPS); o["ci95_excl0"] = bool(o["ci95"][0] > 0 or o["ci95"][1] < 0)
    return o
# ------------------------------------------------------------------ tail
def tail(x, lam, mask, L=2.0):
    idx = np.nonzero(mask)[0]; g = glam(x, lam)[idx]
    eq = np.concatenate([[1.0], np.cumprod(1.0 + L * g * 1e-4)]); dd = 1 - eq / np.maximum.accumulate(eq); imx = int(np.argmax(dd))
    days = {}
    for k in idx: days.setdefault(DAY[k], []).append(k)
    keys = sorted(days); gl = glam(x, lam); dr = np.array([np.prod(1.0 + L * gl[np.array(days[k])] * 1e-4) - 1.0 for k in keys]); w = int(np.argmin(dr))
    return dict(n=int(len(idx)), n_days=len(keys), lam=lam, maxDD=float(dd.max()), maxDD_trough_utc=time.strftime("%Y-%m-%d %HZ", time.gmtime(int(ts[idx][max(imx - 1, 0)]))), worst_day=keys[w], worst_day_ret=float(dr[w]),
                halt4=int((dr <= -0.04).sum()), alert268=int((dr <= -0.0268).sum()), sd_day=float(dr.std(ddof=1)), halt4_per_yr=float((dr <= -0.04).sum() / (len(dr) / 365)), ann_ret_2x=float(np.prod(1 + dr) ** (365 / len(dr)) - 1))
# ------------------------------------------------------------------ regime cells (verbatim r15/r12 construction)
P = np.load(PRIM); PC = [str(c) for c in P["cols"]]; PR = P["rec"]; pcol = lambda k: PR[:, PC.index(k)].astype(float); mts = PR[:, 0].astype(np.int64); assert set(np.unique(np.diff(mts)).tolist()) == {14400}
A_, B_, D_ = pcol("A_ew"), pcol("B_breadth"), pcol("D_disp_bps"); SIGF, FMED, SPAY = pcol("SIGF"), pcol("FMED"), pcol("SPAY")
def trail_mean(x, k):
    out = np.full(len(x), np.nan); cs = np.concatenate([[0.0], np.cumsum(np.nan_to_num(x))]); cn = np.concatenate([[0.0], np.cumsum(np.isfinite(x).astype(float))])
    for i in range(k, len(x)):
        n = cn[i] - cn[i - k]
        if n >= k * 0.8: out[i] = (cs[i] - cs[i - k]) / n
    return out
def trail_sum(x, k):
    out = np.full(len(x), np.nan); cs = np.concatenate([[0.0], np.cumsum(np.nan_to_num(x))]); cn = np.concatenate([[0.0], np.cumsum(np.isfinite(x).astype(float))])
    for i in range(k, len(x)):
        if cn[i] - cn[i - k] >= k * 0.8: out[i] = cs[i] - cs[i - k]
    return out
def trail_sd(x, k):
    out = np.full(len(x), np.nan)
    for i in range(k, len(x)):
        w = x[i - k:i]; w = w[np.isfinite(w)]
        if len(w) >= k * 0.8: out[i] = w.std()
    return out
BRD6 = trail_mean(B_, 6); XSV30 = trail_mean(D_, 30); MV30 = trail_sd(A_, 30) * 1e4; R24 = trail_sum(A_, 6); R72 = trail_sum(A_, 18)
mrow = {int(t): i for i, t in enumerate(mts)}; take = np.array([mrow[int(t)] for t in ts]); BRD6, XSV30, MV30, R24, R72, SIGF, FMED, SPAY = (v[take] for v in (BRD6, XSV30, MV30, R24, R72, SIGF, FMED, SPAY))
def terc(v): return np.nanpercentile(v[WA], [100 / 3, 200 / 3])
def band(v, q):
    lab = np.full(len(v), -1); lab[np.isfinite(v) & (v <= q[0])] = 0; lab[np.isfinite(v) & (v > q[0]) & (v <= q[1])] = 1; lab[np.isfinite(v) & (v > q[1])] = 2; return lab
QB, QX, QM, QS = terc(BRD6), terc(XSV30), terc(MV30), terc(SIGF); Q_FMED_D1 = np.nanpercentile(FMED[WA], 10); Q_SPAY_D9 = np.nanpercentile(SPAY[WA], 90)
CUTS = dict(BRD6=QB.tolist(), XSV30=QX.tolist(), MV30=QM.tolist(), SIGF=QS.tolist(), FMED_decile1=float(Q_FMED_D1), SPAY_decile10=float(Q_SPAY_D9)); R12 = json.load(open(R12RC))
for k, v in CUTS.items(): assert np.allclose(np.asarray(v), np.asarray(R12["cuts"][k]), atol=1e-9), (k, v, R12["cuts"][k])
LB, LX, LM, LS = band(BRD6, QB), band(XSV30, QX), band(MV30, QM), band(SIGF, QS); CELLS = []
for y in sorted(set(YEAR[WT].tolist())): CELLS.append(("a_YEAR", str(y), YEAR == y))
for t, nm in [(0, "T1 narrowest"), (1, "T2"), (2, "T3 broadest")]: CELLS.append(("b_BREADTH(trail24h)", nm, LB == t))
for t, nm in [(0, "T1 lowest"), (1, "T2"), (2, "T3 highest")]: CELLS.append(("c_XSVOL(trail5d disp)", nm, LX == t))
for t, nm in [(0, "T1 lowest"), (1, "T2"), (2, "T3 highest")]: CELLS.append(("c2_MKTVOL(trail5d EW sd)", nm, LM == t))
for t, nm in [(0, "T1 lowest"), (1, "T2"), (2, "T3 highest")]: CELLS.append(("d_SIGF(fund disp)", nm, LS == t))
E = {}
E["POSTCRASH R24<=-2%"] = np.isfinite(R24) & (R24 <= -0.02); E["~POSTCRASH"] = np.isfinite(R24) & (R24 > -0.02)
E["BROADRALLY R24>=+2%&B>=.60"] = np.isfinite(R24) & np.isfinite(BRD6) & (R24 >= 0.02) & (BRD6 >= 0.60); E["~BROADRALLY"] = np.isfinite(R24) & np.isfinite(BRD6) & ~E["BROADRALLY R24>=+2%&B>=.60"]
E["ALTSURGE R72>=+8%"] = np.isfinite(R72) & (R72 >= 0.08); E["~ALTSURGE"] = np.isfinite(R72) & (R72 < 0.08); E["ALTSURGE_BROAD"] = E["ALTSURGE R72>=+8%"] & np.isfinite(BRD6) & (BRD6 >= 0.60)
E["DEEPNEG_MKT (FMED d1)"] = np.isfinite(FMED) & (FMED <= Q_FMED_D1); E["~DEEPNEG_MKT"] = np.isfinite(FMED) & (FMED > Q_FMED_D1)
E["DEEPNEG_SHORT (SPAY d10)"] = np.isfinite(SPAY) & (SPAY >= Q_SPAY_D9); E["~DEEPNEG_SHORT"] = np.isfinite(SPAY) & (SPAY < Q_SPAY_D9)
for k, v in E.items(): CELLS.append(("e_EVENT", k, v))
for lo, hi, nm in [(-9, -0.04, "R72 < -4%"), (-0.04, 0.0, "R72 -4%..0"), (0.0, 0.04, "R72 0..+4%"), (0.04, 0.08, "R72 +4..+8%"), (0.08, 0.15, "R72 +8..+15%"), (0.15, 9, "R72 >= +15%")]: CELLS.append(("e2_R72 ladder", nm, np.isfinite(R72) & (R72 >= lo) & (R72 < hi)))
assert len(CELLS) == 34
_r12 = {(c["family"], c["cell"]): c for c in R12["cells"]}
for fam, lab, mk in CELLS:
    a = mk & WA; c = _r12[(fam, lab)]
    if int(a.sum()) >= 30: assert abs(shp(A0["42"]["g"][a]) - c["sharpe"]) < 1e-9 and abs(float(A0["42"]["g"][a].mean()) - c["mean_g"]) < 1e-9, (fam, lab)
def regime(arm, lam_arm, base, lam_base):
    rows = []; n3b = n3a = l3b = l3a = 0; nt = 0; sig = 0; ga = glam(arm, lam_arm); gb = glam(base, lam_base)
    for fam, lab, mk in CELLS:
        a = mk & WA; n = int(a.sum())
        if n < 30: rows.append(dict(family=fam, cell=lab, n=n, note="too few")); continue
        nt += 1; se = float(np.sqrt(2190 / n)); shA = shp(gb[a]); shB = shp(ga[a]); b = boot(ga - gb, a)
        n3b += shA > 3.0; n3a += shB > 3.0; l3b += shA - 1.96 * se > 3.0; l3a += shB - 1.96 * se > 3.0; sig += (b["ci95"][0] > 0) or (b["ci95"][1] < 0)
        rows.append(dict(family=fam, cell=lab, n=n, sharpe_base=shA, sharpe_arm=shB, sharpe_se=se, g_base=float(gb[a].mean()), g_arm=float(ga[a].mean()), dg=float((ga - gb)[a].mean()), ci95=b["ci95"]))
    return dict(cells=rows, n_cells=nt, sharpe_gt3_before=n3b, sharpe_gt3_after=n3a, sharpe_lo_gt3_before=l3b, sharpe_lo_gt3_after=l3a, cells_dg_ci95_excl0=sig)
# ------------------------------------------------------------------ residual / turnover / dust / class instrument
def instr(x, mask):
    I = x["I"]; gt = x["gt"]; o = dict(n=int(mask.sum()))
    o["tau_intent_matched"] = float((I["tau_intent"] / gt)[mask].mean()); o["tau_exec_matched"] = float((I["tau_exec"] / gt)[mask].mean()); o["tau_exec_rec_check"] = float(x["tau"][mask].mean())
    o["exec_over_intent_turnover"] = float(I["tau_exec"][mask].sum() / I["tau_intent"][mask].sum())
    o["resid_over_gross_target_mean"] = float((I["resid"] / np.where(I["gross_target"] > 0, I["gross_target"], np.nan))[mask].mean()); o["n_resid_m_mean"] = float(I["n_resid_m"][mask].mean()); o["n_intent_m_mean"] = float(I["n_intent_m"][mask].mean())
    r = I["gross_prev_held"] / np.where(I["gross_target"] > 0, I["gross_target"], np.nan); o["held_over_target_gross_median"] = float(np.nanmedian(r[mask])); o["held_over_target_gross_p10_p90"] = [float(np.nanpercentile(r[mask], 10)), float(np.nanpercentile(r[mask], 90))]
    o["held_over_target_by_year_median"] = {int(y): float(np.nanmedian(r[mask & (YEAR == y)])) for y in sorted(set(YEAR[mask].tolist()))}
    o["n_dust_mean"] = float(I["n_dust"][mask].mean()); o["dust_notional_over_intent"] = float(I["dust_notional"][mask].sum() / I["tau_intent"][mask].sum())
    o["class_fill_realised"] = {c: dict(intent_share=float(I["int_" + c][mask].sum() / I["tau_intent"][mask].sum()), exec_over_intent=float(I["exec_" + c][mask].sum() / max(I["int_" + c][mask].sum(), 1e-12))) for c in ("ADD", "DERISK", "FLIP", "ZT")}
    ages = {k: float(I[k][mask].sum()) for k in ("age1", "age2", "age3_5", "age6_12", "age_gt12")}; tot = sum(ages.values()); o["resid_age_hist_counts"] = ages; o["resid_age_hist_share"] = {k: v / tot for k, v in ages.items()} if tot > 0 else None
    o["resid_names_per_anchor_gt5e-5"] = float(sum(I[k][mask] for k in ("age1", "age2", "age3_5", "age6_12", "age_gt12")).mean())
    return o
# ------------------------------------------------------------------ r6 BOOK gap (exact reproduction of j1_decomp, then the partial-fill replacement)
J1 = json.load(open(R + "/receipts/j1_recon_rows.json")); rows = J1["rows"]; W5 = (1787716800, 1788998400)
def dayblk(A): return time.strftime("%Y%m%d", time.gmtime(A))
def bootci_j1(x, days, k):
    rng = np.random.default_rng([20260911, k]); ud = sorted(set(days)); idx = {d: np.where(np.array(days) == d)[0] for d in ud}; o = np.empty(NB)
    for b in range(NB):
        p = rng.integers(0, len(ud), len(ud)); o[b] = x[np.concatenate([idx[ud[q]] for q in p])].mean()
    return float(x.mean()), float(o.std(ddof=1)), [float(np.percentile(o, 2.5)), float(np.percentile(o, 97.5))]
def book_gap(pf_arm, s):
    arm = "A0_PWR230k_s%s" % s; S = [r for r in rows if W5[0] <= r["A"] <= W5[1] and r.get("realized") and "D2" in r and "HELD" in r and arm in r]
    da = [dayblk(r["A"]) for r in S]; gD = np.array([r["D2"]["price_y4s"] for r in S]); gR = np.array([r[arm]["price_bps"] for r in S])
    kk = {"42": 107, "2027": 110}[s]; m0, se0, ci0 = bootci_j1(gD - gR, da, kk)
    tpos = {int(t): i for i, t in enumerate(ts)}; ix = np.array([tpos[int(r["A"])] for r in S])
    for r, i in zip(S, ix): assert abs(A0[s]["pnl"][i] * 1.0 - r[arm]["price_bps"]) < 1e-9, (r["A"], A0[s]["pnl"][i], r[arm]["price_bps"])   # the archived arm's rows ARE the j1 rows
    out = dict(n=len(S), window="W5 2026-08-26 04Z..09-10 00Z ∩ archived arm has value (=> 08-26 04Z..08-30 20Z)", book_100=dict(mean=m0, boot_se=se0, ci95=ci0, j1_seed_k=kk, reproduces_r6=bool(abs(m0 - {"42": 2.6981652055987984, "2027": 2.8709079038664203}[s]) < 1e-9)))
    def after(x, tag):
        gP = x["pnl"][ix]; m1, se1, ci1 = bootci_j1(gD - gP, da, kk); d = (gD - gR) - (gD - gP)
        b = boot_local(d, da); return dict(tag=tag, mean=m1, boot_se=se1, ci95=ci1, explained_by_fills=dict(mean=float(d.mean()), ci95=b))
    def boot_local(d, days):
        rng = np.random.default_rng([20260905, 777]); ud = sorted(set(days)); idx = {dd: np.where(np.array(days) == dd)[0] for dd in ud}; o = np.empty(NB)
        for b in range(NB):
            p = rng.integers(0, len(ud), len(ud)); o[b] = d[np.concatenate([idx[ud[q]] for q in p])].mean()
        return [float(np.percentile(o, 2.5)), float(np.percentile(o, 97.5))]
    out["book_pf_det"] = after(pf_arm, "A0DET"); out["book_pf_stoch"] = [after(STOC[(k, s)], "A0STO%d" % k) for k in STO]
    out["book_pf_stoch_mean_range"] = [min(v["mean"] for v in out["book_pf_stoch"]), max(v["mean"] for v in out["book_pf_stoch"])]
    return out
# ------------------------------------------------------------------ assemble
OUT = dict(self_sha256=sha(os.path.abspath(__file__)), prereg_sha256=PREREG_SHA, amendment1_sha256=AMEND1_SHA, K=K, alpha_K=ALPHA_K, lambda_primary=LAM_P, lambda_secondary=LAM_S, env=ENV, cuts=CUTS, primitives_sha256=PRIM_SHA,
           fill_table_sha256=G["fill_table_sha256"], derived_device_sha256=G["derived_device_sha256"], live_gross_ratio_median=LIVE_GROSS_RATIO, A0={}, A0DET={}, STOCH={}, rebased={}, book_gap={}, gates={})
for s in SEEDS:
    a = A0[s]; OUT["A0"][s] = dict(sha256=a["sha"], g_WA=float(a["g"][WA].mean()), sharpe_WA=shp(a["g"][WA]), tau_matched=float(a["tau"][WA].mean()), tau_raw=float(a["tau_raw"][WA].mean()), carry=float(a["car"][WA].mean()), cost=float(a["cst"][WA].mean()), pnl=float(a["pnl"][WA].mean()),
                                   g_KL=float(a["g"][WA & KL].mean()), sharpe_KL=shp(a["g"][WA & KL]), tail_WT=tail(a, 1.0, WT), tail_KL=tail(a, 1.0, WT & KL), by_year={int(y): float(a["g"][WA & (YEAR == y)].mean()) for y in sorted(set(YEAR[WA].tolist()))})
    d = DET[s]
    OUT["A0DET"][s] = dict(sha256=d["sha"], path=d["path"], cfg_R17=d["cfg"]["R17"], device_self_sha256=d["cfg"]["UPLIFT"]["self_sha256"],
                           primary_WA=block(d, LAM_P, a, 1.0, WA), secondary_WA=block(d, LAM_S, a, 1.0, WA), primary_KL=block(d, LAM_P, a, 1.0, WA & KL), secondary_KL=block(d, LAM_S, a, 1.0, WA & KL),
                           g_WA_lam={"%.4f" % l: float(glam(d, l)[WA].mean()) for l in (LAM_P, LAM_S)}, sharpe_WA_lam={"%.4f" % l: shp(glam(d, l)[WA]) for l in (LAM_P, LAM_S)},
                           tail_WT={"%.4f" % l: tail(d, l, WT) for l in (LAM_P, LAM_S)}, tail_KL={"%.4f" % l: tail(d, l, WT & KL) for l in (LAM_P, LAM_S)},
                           instr_WA=instr(d, WA), instr_2026=instr(d, WA & (YEAR == 2026)), instr_KL=instr(d, WA & KL),
                           regime_primary=regime(d, LAM_P, a, 1.0), regime_secondary=regime(d, LAM_S, a, 1.0))
    OUT["gates"]["F_ii_s" + s] = dict(replay_held_over_target_2026_median=OUT["A0DET"][s]["instr_2026"]["held_over_target_gross_median"], live_median=LIVE_GROSS_RATIO, PASS=bool(abs(OUT["A0DET"][s]["instr_2026"]["held_over_target_gross_median"] - LIVE_GROSS_RATIO) <= 0.05))
    st = {}
    for k in STO:
        x = STOC[(k, s)]; st[k] = dict(sha256=x["sha"], g_WA_lam={"%.4f" % l: float(glam(x, l)[WA].mean()) for l in (LAM_P, LAM_S)}, sharpe_WA_lam={"%.4f" % l: shp(glam(x, l)[WA]) for l in (LAM_P, LAM_S)},
                                      primary_WA=block(x, LAM_P, a, 1.0, WA), tail_WT={"%.4f" % l: tail(x, l, WT) for l in (LAM_P, LAM_S)}, instr_WA=instr(x, WA), g_KL_primary=float(glam(x, LAM_P)[WA & KL].mean()))
    gs = {"%.4f" % l: [st[k]["g_WA_lam"]["%.4f" % l] for k in STO] for l in (LAM_P, LAM_S)}
    OUT["STOCH"][s] = dict(seeds=st, g_WA_mean={l: float(np.mean(v)) for l, v in gs.items()}, g_WA_sd_across_seeds={l: float(np.std(v, ddof=1)) for l, v in gs.items()}, g_WA_min_max={l: [float(min(v)), float(max(v))] for l, v in gs.items()},
                          det_inside_envelope={l: bool(min(v) <= OUT["A0DET"][s]["g_WA_lam"][l] <= max(v)) for l, v in gs.items()}, halt4_range={"%.4f" % l: [min(st[k]["tail_WT"]["%.4f" % l]["halt4"] for k in STO), max(st[k]["tail_WT"]["%.4f" % l]["halt4"] for k in STO)] for l in (LAM_P, LAM_S)},
                          maxDD_range={"%.4f" % l: [min(st[k]["tail_WT"]["%.4f" % l]["maxDD"] for k in STO), max(st[k]["tail_WT"]["%.4f" % l]["maxDD"] for k in STO)] for l in (LAM_P, LAM_S)})
    OUT["book_gap"][s] = book_gap(d, s)
    for arm in ("X1", "F", "S"):
        a100 = ARM100[(arm, s)]; apf = ARMPF[(arm, s)]
        o = dict(sha256_100=a100["sha"], sha256_pf=apf["sha"], dg_100=block(a100, 1.0, a, 1.0, WA), dg_pf_primary=block(apf, LAM_P, d, LAM_P, WA), dg_pf_secondary=block(apf, LAM_S, d, LAM_S, WA), dg_pf_primary_KL=block(apf, LAM_P, d, LAM_P, WA & KL),
                 tail_WT_100=tail(a100, 1.0, WT), tail_WT_pf={"%.4f" % l: tail(apf, l, WT) for l in (LAM_P, LAM_S)}, instr_WA=instr(apf, WA))
        ti_arm = (apf["I"]["tau_intent"] / apf["gt"])[WA].mean(); ti_a0 = (d["I"]["tau_intent"] / d["gt"])[WA].mean(); te_arm = apf["tau"][WA].mean(); te_a0 = d["tau"][WA].mean()
        o["turnover"] = dict(dtau_intent_matched=float(ti_arm - ti_a0), dtau_intent_pct=float(100 * (ti_arm - ti_a0) / ti_a0), dtau_exec_matched=float(te_arm - te_a0), dtau_exec_pct=float(100 * (te_arm - te_a0) / te_a0),
                             fill_rate_of_incremental_intent=float((te_arm - te_a0) / (ti_arm - ti_a0)) if abs(ti_arm - ti_a0) > 1e-9 else None, dtau_100_pct=float(100 * (a100["tau"][WA].mean() - a["tau"][WA].mean()) / a["tau"][WA].mean()))
        o["sign_flip_primary"] = bool(np.sign(o["dg_100"]["dg"]) != np.sign(o["dg_pf_primary"]["dg"])); o["sign_flip_secondary"] = bool(np.sign(o["dg_100"]["dg"]) != np.sign(o["dg_pf_secondary"]["dg"]))
        OUT["rebased"]["%s_s%s" % (arm, s)] = o
# ------------------------------------------------------------------ verdict (PREREG §7 reading rule (b))
def rule(key):
    c = {s: OUT["A0DET"][s][key] for s in SEEDS}
    if all(abs(c[s]["dg"]) >= RES_BPS and c[s]["ci95_excl0"] for s in SEEDS): v = "MOVES_" + ("UP" if all(c[s]["dg"] > 0 for s in SEEDS) else ("DOWN" if all(c[s]["dg"] < 0 for s in SEEDS) else "MIXED"))
    elif all(abs(c[s]["dg"]) < RES_BPS for s in SEEDS): v = "CLOSES"
    else: v = "UNDECIDED"
    return dict(verdict=v, dg={s: c[s]["dg"] for s in SEEDS}, ci95={s: c[s]["ci95"] for s in SEEDS}, ci99K={s: c[s]["ci99K"] for s in SEEDS})
OUT["verdict_b"] = dict(primary_lam_0p8096=rule("primary_WA"), secondary_lam_1p0=rule("secondary_WA"))
OUT["built_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
json.dump(OUT, open(R + "/receipts/RECEIPT_r17_judge.json", "w"), indent=1, default=float)
os.makedirs(R + "/receipts/arms_rec", exist_ok=True); RS = {}
for tag, x in [("A0DET_s%s" % s, DET[s]) for s in SEEDS] + [("A0STO%d_s%s" % (k, s), STOC[(k, s)]) for k in STO for s in SEEDS] + [("%sDET_s%s" % (arm, s), ARMPF[(arm, s)]) for arm in ("X1", "F", "S") for s in SEEDS]:
    p = R + "/receipts/arms_rec/%s.npz" % tag; ex = {"R17_" + c: v for c, v in x["I"].items()} if "I" in x else {}
    np.savez_compressed(p, cols=np.array(x["cols"]), rec=x["rec"], config_json=np.array(json.dumps(x["cfg"])), source_sha256=np.array(x["sha"]), **ex); RS[os.path.basename(p)] = sha(p)
json.dump(RS, open(R + "/receipts/arms_rec/SHA256_arms_rec.json", "w"), indent=1)
# ------------------------------------------------------------------ print
for s in SEEDS:
    a = OUT["A0"][s]; d = OUT["A0DET"][s]; p = d["primary_WA"]; q = d["secondary_WA"]; st = OUT["STOCH"][s]; ii = d["instr_WA"]
    print("\n=== seed %s  A0(100%%, lam1): g %.4f Sh %.3f tau %.6f carry %.4f cost %.4f | A0DET lam.8096: g %.4f Sh %.3f | lam1: g %.4f Sh %.3f" % (s, a["g_WA"], a["sharpe_WA"], a["tau_matched"], a["carry"], a["cost"], d["g_WA_lam"]["0.8096"], d["sharpe_WA_lam"]["0.8096"], d["g_WA_lam"]["1.0000"], d["sharpe_WA_lam"]["1.0000"]))
    print("  PRIMARY  d_fill %+.4f CI95 [%+.4f,%+.4f] CI99K [%+.4f,%+.4f] | dpnl %+.4f dcarry %+.4f dcost %+.4f | Sh %.3f vs %.3f" % (p["dg"], p["ci95"][0], p["ci95"][1], p["ci99K"][0], p["ci99K"][1], p["dpnl"], p["dcarry"], p["dcost"], p["sharpe_arm"], p["sharpe_base"]))
    print("  SECONDARY d_fill %+.4f CI95 [%+.4f,%+.4f] | dpnl %+.4f dcarry %+.4f dcost %+.4f" % (q["dg"], q["ci95"][0], q["ci95"][1], q["dpnl"], q["dcarry"], q["dcost"]))
    print("  KL primary d %+.4f CI95 [%+.4f,%+.4f] g_pf %.4f vs %.4f" % (d["primary_KL"]["dg"], d["primary_KL"]["ci95"][0], d["primary_KL"]["ci95"][1], d["primary_KL"]["g_arm"], d["primary_KL"]["g_base"]))
    print("  TURNOVER matched: intent %.6f exec %.6f (exec/intent %.4f) vs A0 %.6f | resid/gross %.4f n_resid %.1f held/target med %.4f (2026 %.4f; live %.4f GATE F-ii %s) | dust %.2f names/anchor %.5f of intent" % (ii["tau_intent_matched"], ii["tau_exec_matched"], ii["exec_over_intent_turnover"], a["tau_matched"], ii["resid_over_gross_target_mean"], ii["n_resid_m_mean"], ii["held_over_target_gross_median"], d["instr_2026"]["held_over_target_gross_median"], LIVE_GROSS_RATIO, OUT["gates"]["F_ii_s" + s]["PASS"], ii["n_dust_mean"], ii["dust_notional_over_intent"]))
    print("  CLASS realised fill:", {c: (round(v["intent_share"], 3), round(v["exec_over_intent"], 4)) for c, v in ii["class_fill_realised"].items()}, "| ages share", {k: round(v, 3) for k, v in (ii["resid_age_hist_share"] or {}).items()})
    print("  STOCH g(.8096) mean %.4f sd %.4f range [%.4f,%.4f] det inside %s | halt range %s maxDD range %s" % (st["g_WA_mean"]["0.8096"], st["g_WA_sd_across_seeds"]["0.8096"], *st["g_WA_min_max"]["0.8096"], st["det_inside_envelope"]["0.8096"], st["halt4_range"]["0.8096"], [round(v, 4) for v in st["maxDD_range"]["0.8096"]]))
    t0 = a["tail_WT"]; t1 = d["tail_WT"]["0.8096"]; t2 = d["tail_WT"]["1.0000"]
    print("  TAIL WT: A0 maxDD %.4f worst %s %.4f halt %d alert %d | DET(.8096) maxDD %.4f worst %s %.4f halt %d alert %d | DET(1.0) maxDD %.4f halt %d" % (t0["maxDD"], t0["worst_day"], t0["worst_day_ret"], t0["halt4"], t0["alert268"], t1["maxDD"], t1["worst_day"], t1["worst_day_ret"], t1["halt4"], t1["alert268"], t2["maxDD"], t2["halt4"]))
    rg = d["regime_primary"]; print("  REGIME(primary): Sh>3 %d->%d ; Sh_lo>3 %d->%d ; cells dg CI95 excl 0: %d/%d" % (rg["sharpe_gt3_before"], rg["sharpe_gt3_after"], rg["sharpe_lo_gt3_before"], rg["sharpe_lo_gt3_after"], rg["cells_dg_ci95_excl0"], rg["n_cells"]))
    bg = OUT["book_gap"][s]; print("  BOOK gap n=%d: 100%% %.4f [%.4f,%.4f] reproduces_r6=%s -> DET %.4f [%.4f,%.4f]; explained by fills %+.4f CI %s; stoch range %s" % (bg["n"], bg["book_100"]["mean"], *bg["book_100"]["ci95"], bg["book_100"]["reproduces_r6"], bg["book_pf_det"]["mean"], *bg["book_pf_det"]["ci95"], bg["book_pf_det"]["explained_by_fills"]["mean"], [round(v, 4) for v in bg["book_pf_det"]["explained_by_fills"]["ci95"]], [round(v, 4) for v in bg["book_pf_stoch_mean_range"]]))
    for arm in ("X1", "F", "S"):
        o = OUT["rebased"]["%s_s%s" % (arm, s)]; t = o["turnover"]
        print("  REBASE %s: dg_100 %+.4f [%+.4f,%+.4f] -> dg_pf(.8096) %+.4f [%+.4f,%+.4f] | dg_pf(1.0) %+.4f | dtau intent %+.1f%% exec %+.1f%% (100%%-fill %+.1f%%) fill of incremental %s | flip %s/%s" % (arm, o["dg_100"]["dg"], *o["dg_100"]["ci95"], o["dg_pf_primary"]["dg"], *o["dg_pf_primary"]["ci95"], o["dg_pf_secondary"]["dg"], t["dtau_intent_pct"], t["dtau_exec_pct"], t["dtau_100_pct"], None if t["fill_rate_of_incremental_intent"] is None else round(t["fill_rate_of_incremental_intent"], 3), o["sign_flip_primary"], o["sign_flip_secondary"]))
print("\nVERDICT (b)", json.dumps(OUT["verdict_b"]))
print("DONE_r17_judge")
