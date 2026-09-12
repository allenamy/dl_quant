#!/usr/bin/env python3
"""r15_judge.py — PREREG_r15 §5-§11 statistics for every declared arm (K=5), both seeds, against the ARCHIVED A0.
Runs only after RECEIPT_r15_drive_gateP.json (P1-P3 PASS) and RECEIPT_r15_mechgate.json (gate PASS) exist; asserts both.
g = net_ex/gross_total (bps/anchor/unit gross). W_ALPHA (n=9138) for alpha numbers, W_TAIL (n=10038) for tail numbers,
KING_LIVE (ts>=2024-01-01) sub-sample of each. Paired dg vs A0 of the same seed. UTC-day block bootstrap 2000,
default_rng([20260905,k]); CI95 and CI99-K (K=5 Bonferroni). Regime cells = r12's 34 cells, cuts asserted equal to r12's receipt.
Read-only. CPU only. Caliber is read from each artifact's config_json, never from the environment.
"""
import os, sys, json, time, hashlib, calendar
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "launch with a non-empty env whitelist as argv[1]"
BANNED = ('CAL','JUDGE','UPLIFT','PANEL','LOOK','WRULE','LEGS','PHI','FSEED','W3FIX','FTRIM','UMASK','SLOW','FPRED','MEMBERS_TOPN','COSTB','SLEEVE','KMOD','SEAT','RNSM','LTRIM','CDAMP','FUNDSCALE','FEMAT','TRADE_TOPN','REF_SKIP','PYTHON','OMP','MKL','R15','FTPOS','OUT_TAG')
EXTRA = sorted(k for k in os.environ if k not in WHITE); assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
BAN = sorted(k for k in os.environ if k.startswith(BANNED)); assert BAN == [], ("CALIBER FLAG PRESENT", BAN)
ENV = dict(env_whitelist=sorted(WHITE), env_actual={k: os.environ[k] for k in sorted(os.environ)}, launch_cmdline=" ".join(sys.argv))
import numpy as np
ENV.update(python=sys.version.split()[0], numpy=np.__version__)
R = "/workspace/uplift_2026-09-11/r15_structural"
PREREG_SHA = "097769b087fa0834fb780062bf710134d7e3a67555174de5c26c1668c455f6fc"
PRIM = "/workspace/uplift_2026-09-11/r12_regime/causal_primitives_r12_v2.npz"; PRIM_SHA = "0510f456f63f4963cae757a0fd86251477089de1d266b8b8859092f9f73cf08f"
R12RC = R + "/receipts/RECEIPT_r12_regime_table.json"
def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
assert sha(R + "/PREREG_r15_structural_2026-09-12.md") == PREREG_SHA
assert sha(PRIM) == PRIM_SHA, sha(PRIM)
G = json.load(open(R + "/receipts/RECEIPT_r15_drive_gateP.json")); assert G["gate"]["P1"]["PASS"] and G["gate"]["P2"]["PASS"] and G["gate"]["P3"]["PASS"]
MG = json.load(open(R + "/receipts/RECEIPT_r15_mechgate.json"))
# PREREG §4: STOP applies to the A0-side gate only; the ARM-F "exactly zero" sub-gate is REPORTED (PASS/FAIL), not a stop (AMENDMENT 1).
assert all(MG["gate"]["s" + s]["A0_gate_pass"] for s in ("42", "2027")), MG["gate"]
MECH_F_ZERO = {s: MG["gate"]["s" + s]["F_position_zero_pass"] for s in ("42", "2027")}
NL = json.load(open(R + "/receipts/RECEIPT_r15_nulls.json")) if os.path.exists(R + "/receipts/RECEIPT_r15_nulls.json") else None
K = 5; ALPHA_K = 0.05 / K; PCT_K = (100 * ALPHA_K / 2, 100 * (1 - ALPHA_K / 2))
NB = 2000; LAMBDAS = (1.0, 0.8096, 0.2545); RES_BPS = 0.23
UB = calendar.timegm((2026, 8, 30, 20, 0, 0)); K24 = calendar.timegm((2024, 1, 1, 0, 0, 0))
SEEDS = ("42", "2027"); ARMS = ("F", "S", "SB", "F05", "F20")
ARMFILE = {"F": "F_s%s", "S": "S_s%s", "SB": "SB_s%s", "F05": "F05_s%s", "F20": "F20_s%s"}
EXPECT = {"F": dict(FTPOS=1, SEATNET=0, FTRIM_TH=-0.001), "S": dict(FTPOS=0, SEATNET=1, FTRIM_TH=-0.001), "SB": dict(FTPOS=0, SEATNET=0, FTRIM_TH=-0.001),
          "F05": dict(FTPOS=1, SEATNET=0, FTRIM_TH=-0.0005), "F20": dict(FTPOS=1, SEATNET=0, FTRIM_TH=-0.002)}
def load(p, expect=None, sb=False):
    Z = np.load(p, allow_pickle=True); C = [str(c) for c in Z["cols"]]; rec = np.asarray(Z["d30_n2_c42_rec"] if "d30_n2_c42_rec" in Z else Z["rec"], float)
    cfg = json.loads(str(Z["config_json"]))
    assert cfg["CAL"] == "log" and cfg["PHI"] == 0.45 and cfg["LEGS"] == "101" and cfg["WRULE"] == "msharpe" and cfg["W3FIX"] is None and cfg["UMASK_SCOPE"] == "m1" and cfg["LOOK"] == 900 and cfg["FTRIM"] == "zero" and cfg["MEMBERS_TOPN"] == 829, cfg
    assert cfg["COSTB_JSON"].endswith("costb_PWR_G230k.json") and cfg["SLOW_NPY"].endswith("SLOW_v3_on_v4axis.npy"), cfg
    if expect is not None:
        for k, v in expect.items(): assert cfg[k] == v, (k, cfg[k], v)
        assert cfg.get("R15", {}).get("R15_SB", 0) == (1 if sb else 0), cfg.get("R15")
        if not sb: assert cfg.get("R15") is None or (cfg["R15"]["R15_KILL_NPZ"] is None and cfg["R15"]["R15_SEATC_NPZ"] is None and cfg["R15"]["R15_SEATC_SCALE"] == 1.0 and cfg["R15"]["R15_KILL_TH"] is None), cfg["R15"]
    col = lambda k: rec[:, C.index(k)]
    ts = col("ts").astype(np.int64); gt = col("gross_total")
    d = dict(ts=ts, gt=gt, g=col("net_ex") / gt, pnl=col("pnl_ex") / gt, car=col("carry_ex") / gt, cst=col("cost_ex") / gt, tau_raw=col("turnover"), tau=col("turnover") / gt,
             w3k=col("w3_king"), w3f=col("w3_fund"), lk=col("leg_king"), lf=col("leg_fund"), nl=col("netlong"), cfg=cfg, sha=sha(p), path=p, cols=C, rec=rec)
    assert np.allclose(d["pnl"] - d["car"] - d["cst"], d["g"], atol=1e-9)
    d["WT"] = ts <= UB; d["WA"] = d["WT"].copy(); d["WA"][:900] = False; assert d["WA"].sum() == 9138 and d["WT"].sum() == 10038
    d["KL"] = ts >= K24; assert (d["WA"] & d["KL"]).sum() == 5838
    if "legs_carry_fund" in Z: d["legs_ts"] = Z["legs_ts"].astype(np.int64); d["legs_carry"] = {l: np.asarray(Z["legs_carry_" + l], float) for l in ("king", "rev24", "fund")}; d["legs_price"] = {l: np.asarray(Z["legs_price_" + l], float) for l in ("king", "rev24", "fund")}; d["legs_used"] = {l: np.asarray(Z["legs_" + l], float) for l in ("king", "rev24", "fund")}
    return d
A0 = {s: load(G["runs"]["GP_A0_s" + s]["out"], dict(FTPOS=0, SEATNET=0, FTRIM_TH=-0.001)) for s in SEEDS}
ARCH = {"42": "352ac36fb319532756da71e7cc405fb0dcde6f36f6e28a57f1f681177bcfd339", "2027": "aa44e18fb6bcfa7ef54f1708d070b0a2a7d5333f6cea63dfca94fecf59be1c7b"}
for s in SEEDS:   # the GATE-P run is bitwise the archived arm; its rec must equal the archive's rec
    ZA = np.load("/workspace/uplift_2026-09-11/r3k/arms/A0_PWR230k_s%s.npz" % s, allow_pickle=True); assert sha("/workspace/uplift_2026-09-11/r3k/arms/A0_PWR230k_s%s.npz" % s) == ARCH[s]
    assert np.array_equal(np.asarray(ZA["rec"], float), A0[s]["rec"], equal_nan=True)
    x = A0[s]["g"][A0[s]["WA"]]
    if s == "42": assert abs(x.mean() - 0.6341957) < 5e-7 and abs(A0[s]["tau"][A0[s]["WA"]].mean() - 0.0540270) < 5e-7 and abs(A0[s]["tau_raw"][A0[s]["WA"]].mean() - 0.03032) < 5e-6
AR = {(a, s): load(R + "/arms/" + ARMFILE[a] % s + ".npz", EXPECT[a], sb=(a == "SB")) for a in ARMS for s in SEEDS}
A0I = {s: load(R + "/arms/D_A0I_s%s.npz" % s, dict(FTPOS=0, SEATNET=0, FTRIM_TH=-0.001)) for s in SEEDS}
for s in SEEDS: assert np.array_equal(A0I[s]["rec"], A0[s]["rec"], equal_nan=True)
ts = A0["42"]["ts"]; WA = A0["42"]["WA"]; WT = A0["42"]["WT"]; KL = A0["42"]["KL"]
for a in ARMS:
    for s in SEEDS: assert np.array_equal(AR[(a, s)]["ts"], ts), (a, s)
DAY = np.array([time.strftime("%Y%m%d", time.gmtime(int(t))) for t in ts]); YEAR = np.array([time.gmtime(int(t)).tm_year for t in ts])
# ------------------------------------------------------------------ bootstrap core
_DRAW = {}
def draws(nd):
    if nd not in _DRAW: _DRAW[nd] = np.stack([np.random.default_rng([20260905, k]).integers(0, nd, nd) for k in range(NB)])
    return _DRAW[nd]
def boot(d, mask):
    idx = np.nonzero(mask)[0]
    if len(idx) < 10: return dict(ci95=[np.nan, np.nan], ci99K=[np.nan, np.nan], se=np.nan, n_days=0)
    dd = {}
    for k in idx: dd.setdefault(DAY[k], []).append(k)
    keys = sorted(dd); tot = np.array([d[dd[k]].sum() for k in keys]); cnt = np.array([len(dd[k]) for k in keys], float); nd = len(keys)
    r = draws(nd); ms = tot[r].sum(1) / cnt[r].sum(1)
    return dict(ci95=[float(np.percentile(ms, 2.5)), float(np.percentile(ms, 97.5))], ci99K=[float(np.percentile(ms, PCT_K[0])), float(np.percentile(ms, PCT_K[1]))], se=float(ms.std(ddof=1)), n_days=nd)
def shp(x): return float(x.mean() / x.std(ddof=1) * np.sqrt(2190))
def block(arm, base, mask):
    d = arm["g"] - base["g"]; n = int(mask.sum()); b = boot(d, mask)
    o = dict(n=n, g_arm=float(arm["g"][mask].mean()), g_A0=float(base["g"][mask].mean()), dg=float(d[mask].mean()), **b,
             sharpe_arm=shp(arm["g"][mask]), sharpe_A0=shp(base["g"][mask]), sharpe_se=float(np.sqrt(2190 / n)),
             dpnl=float((arm["pnl"] - base["pnl"])[mask].mean()), dcarry=float((arm["car"] - base["car"])[mask].mean()), dcost=float((arm["cst"] - base["cst"])[mask].mean()),
             pnl_arm=float(arm["pnl"][mask].mean()), carry_arm=float(arm["car"][mask].mean()), cost_arm=float(arm["cst"][mask].mean()),
             pnl_A0=float(base["pnl"][mask].mean()), carry_A0=float(base["car"][mask].mean()), cost_A0=float(base["cst"][mask].mean()),
             tau_matched_arm=float(arm["tau"][mask].mean()), tau_matched_A0=float(base["tau"][mask].mean()), tau_raw_arm=float(arm["tau_raw"][mask].mean()), tau_raw_A0=float(base["tau_raw"][mask].mean()),
             tau_ratio_matched_over_raw_A0=float((base["tau"][mask] / np.where(base["tau_raw"][mask] > 0, base["tau_raw"][mask], np.nan)).mean() if np.isfinite(base["tau"][mask] / np.where(base["tau_raw"][mask] > 0, base["tau_raw"][mask], np.nan)).any() else np.nan))
    o["dtau_matched"] = o["tau_matched_arm"] - o["tau_matched_A0"]; o["dtau_pct"] = 100 * o["dtau_matched"] / o["tau_matched_A0"]
    assert abs(o["dpnl"] - o["dcarry"] - o["dcost"] - o["dg"]) < 1e-9
    o["survival"] = {}
    for lam in LAMBDAS:
        ga = (arm["pnl"] - arm["car"] - lam * arm["cst"])[mask].mean(); gb = (base["pnl"] - base["car"] - lam * base["cst"])[mask].mean()
        o["survival"]["%.4f" % lam] = dict(g_arm=float(ga), g_A0=float(gb), dg=float(ga - gb), sign=int(np.sign(ga - gb)),
                                           surv_arm=float(1 - lam * arm["cst"][mask].mean() / (arm["pnl"] - arm["car"])[mask].mean()), surv_A0=float(1 - lam * base["cst"][mask].mean() / (base["pnl"] - base["car"])[mask].mean()))
    o["dg_sign_stable_over_lambda"] = len(set(v["sign"] for v in o["survival"].values())) == 1
    o["by_year"] = {int(y): dict(n=int((mask & (YEAR == y)).sum()), g_arm=float(arm["g"][mask & (YEAR == y)].mean()), g_A0=float(base["g"][mask & (YEAR == y)].mean()), dg=float(d[mask & (YEAR == y)].mean())) for y in sorted(set(YEAR[mask].tolist()))}
    return o
# ------------------------------------------------------------------ tail
def tail(x, mask, L=2.0):
    idx = np.nonzero(mask)[0]; g = x["g"][idx]
    eq = np.concatenate([[1.0], np.cumprod(1.0 + L * g * 1e-4)]); dd = 1 - eq / np.maximum.accumulate(eq); imx = int(np.argmax(dd))
    days = {}
    for k in idx: days.setdefault(DAY[k], []).append(k)
    keys = sorted(days); dr = np.array([np.prod(1.0 + L * x["g"][np.array(days[k])] * 1e-4) - 1.0 for k in keys]); w = int(np.argmin(dr))
    return dict(n=int(len(idx)), n_days=len(keys), maxDD=float(dd.max()), maxDD_trough_utc=time.strftime("%Y-%m-%d %HZ", time.gmtime(int(ts[idx][max(imx - 1, 0)]))),
                worst_day=keys[w], worst_day_ret=float(dr[w]), halt4=int((dr <= -0.04).sum()), alert268=int((dr <= -0.0268).sum()), sd_day=float(dr.std(ddof=1)),
                halt4_per_yr=float((dr <= -0.04).sum() / (len(dr) / 365)), ann_ret_2x=float(np.prod(1 + dr) ** (365 / len(dr)) - 1))
# ------------------------------------------------------------------ regime cells (verbatim r12 construction)
P = np.load(PRIM); PC = [str(c) for c in P["cols"]]; PR = P["rec"]; pcol = lambda k: PR[:, PC.index(k)].astype(float); mts = PR[:, 0].astype(np.int64)
assert set(np.unique(np.diff(mts)).tolist()) == {14400}
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
mrow = {int(t): i for i, t in enumerate(mts)}; take = np.array([mrow[int(t)] for t in ts])
BRD6, XSV30, MV30, R24, R72, SIGF, FMED, SPAY = (v[take] for v in (BRD6, XSV30, MV30, R24, R72, SIGF, FMED, SPAY))
def terc(v): return np.nanpercentile(v[WA], [100 / 3, 200 / 3])
def band(v, q):
    lab = np.full(len(v), -1); lab[np.isfinite(v) & (v <= q[0])] = 0; lab[np.isfinite(v) & (v > q[0]) & (v <= q[1])] = 1; lab[np.isfinite(v) & (v > q[1])] = 2; return lab
QB, QX, QM, QS = terc(BRD6), terc(XSV30), terc(MV30), terc(SIGF); Q_FMED_D1 = np.nanpercentile(FMED[WA], 10); Q_SPAY_D9 = np.nanpercentile(SPAY[WA], 90)
CUTS = dict(BRD6=QB.tolist(), XSV30=QX.tolist(), MV30=QM.tolist(), SIGF=QS.tolist(), FMED_decile1=float(Q_FMED_D1), SPAY_decile10=float(Q_SPAY_D9))
R12 = json.load(open(R12RC))
for k, v in CUTS.items(): assert np.allclose(np.asarray(v), np.asarray(R12["cuts"][k]), atol=1e-9), (k, v, R12["cuts"][k])
LB, LX, LM, LS = band(BRD6, QB), band(XSV30, QX), band(MV30, QM), band(SIGF, QS)
CELLS = []
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
for lo, hi, nm in [(-9, -0.04, "R72 < -4%"), (-0.04, 0.0, "R72 -4%..0"), (0.0, 0.04, "R72 0..+4%"), (0.04, 0.08, "R72 +4..+8%"), (0.08, 0.15, "R72 +8..+15%"), (0.15, 9, "R72 >= +15%")]:
    CELLS.append(("e2_R72 ladder", nm, np.isfinite(R72) & (R72 >= lo) & (R72 < hi)))
assert len(CELLS) == 34
# r12 self-check: A0 s42 cell Sharpes must reproduce r12's receipt
_r12 = {(c["family"], c["cell"]): c for c in R12["cells"]}
for fam, lab, mk in CELLS:
    a = mk & WA; c = _r12[(fam, lab)]
    if int(a.sum()) >= 30: assert abs(shp(A0["42"]["g"][a]) - c["sharpe"]) < 1e-9 and abs(float(A0["42"]["g"][a].mean()) - c["mean_g"]) < 1e-9, (fam, lab)
def regime(arm, base):
    rows = []; n3b = n3a = l3b = l3a = 0; nt = 0; sig = 0
    for fam, lab, mk in CELLS:
        a = mk & WA; n = int(a.sum())
        if n < 30: rows.append(dict(family=fam, cell=lab, n=n, note="too few")); continue
        nt += 1; se = float(np.sqrt(2190 / n)); shA = shp(base["g"][a]); shB = shp(arm["g"][a]); b = boot(arm["g"] - base["g"], a)
        n3b += shA > 3.0; n3a += shB > 3.0; l3b += shA - 1.96 * se > 3.0; l3a += shB - 1.96 * se > 3.0; sig += (b["ci95"][0] > 0) or (b["ci95"][1] < 0)
        rows.append(dict(family=fam, cell=lab, n=n, sharpe_A0=shA, sharpe_arm=shB, sharpe_se=se, g_A0=float(base["g"][a].mean()), g_arm=float(arm["g"][a].mean()), dg=float((arm["g"] - base["g"])[a].mean()), ci95=b["ci95"],
                         dcarry=float((arm["car"] - base["car"])[a].mean()), dpnl=float((arm["pnl"] - base["pnl"])[a].mean()), dcost=float((arm["cst"] - base["cst"])[a].mean())))
    return dict(cells=rows, n_cells=nt, sharpe_gt3_before=n3b, sharpe_gt3_after=n3a, sharpe_lo_gt3_before=l3b, sharpe_lo_gt3_after=l3a, cells_dg_ci95_excl0=sig)
# ------------------------------------------------------------------ seat path (S, SB) + sigma_fund terciles + leg-vs-book carry
def seat(arm, base):
    m = WA; o = {}
    for k, nm in (("w3k", "w3_king"), ("w3f", "w3_fund")):
        o[nm] = dict(arm_mean=float(arm[k][m].mean()), A0_mean=float(base[k][m].mean()), arm_p10_p50_p90=[float(v) for v in np.percentile(arm[k][m], [10, 50, 90])], A0_p10_p50_p90=[float(v) for v in np.percentile(base[k][m], [10, 50, 90])],
                     arm_by_year={int(y): float(arm[k][m & (YEAR == y)].mean()) for y in sorted(set(YEAR[m].tolist()))}, A0_by_year={int(y): float(base[k][m & (YEAR == y)].mean()) for y in sorted(set(YEAR[m].tolist()))},
                     arm_king_live_mean=float(arm[k][m & KL].mean()), A0_king_live_mean=float(base[k][m & KL].mean()))
    o["P_w3_king_ge_085_arm"] = float((arm["w3k"][m] >= 0.85).mean()); o["P_w3_king_ge_085_A0"] = float((base["w3k"][m] >= 0.85).mean())
    o["P_w3_king_ge_085_arm_king_live"] = float((arm["w3k"][m & KL] >= 0.85).mean()); o["P_w3_king_ge_085_A0_king_live"] = float((base["w3k"][m & KL] >= 0.85).mean())
    o["mean_abs_dw3_king"] = float(np.abs(arm["w3k"] - base["w3k"])[m].mean()); o["frac_anchors_w3_changed"] = float((np.abs(arm["w3k"] - base["w3k"])[m] > 1e-9).mean())
    o["sigf_terciles"] = {}
    for t, nm in [(0, "T1 lowest"), (1, "T2"), (2, "T3 highest")]:
        a = (LS == t) & WA; b = boot(arm["g"] - base["g"], a)
        o["sigf_terciles"][nm] = dict(n=int(a.sum()), dg=float((arm["g"] - base["g"])[a].mean()), ci95=b["ci95"], w3_king_arm=float(arm["w3k"][a].mean()), w3_king_A0=float(base["w3k"][a].mean()), g_A0=float(base["g"][a].mean()), g_arm=float(arm["g"][a].mean()))
    return o
def legcarry(s):
    x = A0I[s]; lm = {int(t): i for i, t in enumerate(x["legs_ts"])}; li = np.array([lm[int(t)] for t in ts[WA]])
    bc = float(A0[s]["car"][WA].mean()); o = dict(book_carry_ex_pug_A0=bc)
    for l in ("king", "rev24", "fund"):
        c = x["legs_carry"][l][li]; o["leg_rankbook_carry_pug_" + l] = float(c.mean()); o["ratio_leg_over_book_" + l] = float(c.mean() / bc) if bc != 0 else None
        o["leg_price_LR_mean_" + l] = float(x["legs_price"][l][li].mean()); o["leg_price_LR_sharpe_" + l] = shp(x["legs_price"][l][li]); o["leg_net_LR_mean_" + l] = float((x["legs_price"][l] - x["legs_carry"][l])[li].mean()); o["leg_net_LR_sharpe_" + l] = shp((x["legs_price"][l] - x["legs_carry"][l])[li])
    o["fund_rankbook_carry_king_live"] = float(x["legs_carry"]["fund"][np.array([lm[int(t)] for t in ts[WA & KL]])].mean()); o["book_carry_ex_pug_A0_king_live"] = float(A0[s]["car"][WA & KL].mean())
    return o
def sb_seat_inputs(s):
    x = AR[("SB", s)]
    if "legs_used" not in x: return None
    lm = {int(t): i for i, t in enumerate(x["legs_ts"])}; li = np.array([lm[int(t)] for t in ts[WA]])
    return {l: dict(sb_net_mean=float(x["legs_used"][l][li].mean()), sb_net_sharpe=shp(x["legs_used"][l][li]), price_LR_mean=float(x["legs_price"][l][li].mean()), price_LR_sharpe=shp(x["legs_price"][l][li])) for l in ("king", "rev24", "fund")}
# ------------------------------------------------------------------ nulls
def nulls(a, s):
    if NL is None or a not in ("F", "S"): return None
    o = {}; relab = []
    for fam in ("RELAB1", "RELAB2", "RELAB3", "SHIFT101", "SHIFT503", "SHIFT1009"):
        n = NL["nulls"]["%s_s%s_%s" % (a, s, fam)]
        o[fam] = {k: n.get(k) for k in ("dose_matched", "dtau", "dtau_target", "dtau_rel_err", "MATCHED", "n_steps", "dg", "dg_arm", "fire_total_WA", "fire_target_WA", "fire_rel_err", "fire_S_mean_abs_dw3k", "fire_S_target", "weak_family", "out_sha256")}
        if fam.startswith("RELAB"): relab.append(n["dg"])
    relab = np.array(relab); dga = NL["nulls"]["%s_s%s_RELAB1" % (a, s)]["dg_arm"]
    o["summary"] = dict(dg_arm=dga, relab_dg=relab.tolist(), relab_max=float(relab.max()), relab_mean=float(relab.mean()), relab_sd=float(relab.std(ddof=1)), beats_all_relab=bool(dga > relab.max()),
                        rank_of_arm_among_relab=int((relab >= dga).sum()) + 1, z_vs_relab=float((dga - relab.mean()) / relab.std(ddof=1)) if relab.std(ddof=1) > 0 else None,
                        all_relab_matched=all(o[f]["MATCHED"] for f in ("RELAB1", "RELAB2", "RELAB3")), shift_dg=[o[f]["dg"] for f in ("SHIFT101", "SHIFT503", "SHIFT1009")], shift_matched=[o[f]["MATCHED"] for f in ("SHIFT101", "SHIFT503", "SHIFT1009")])
    return o
# ------------------------------------------------------------------ assemble
OUT = dict(self_sha256=sha(os.path.abspath(__file__)), prereg_sha256=PREREG_SHA, K=K, alpha_K=ALPHA_K, env=ENV, cuts=CUTS, primitives_sha256=PRIM_SHA,
           A0={s: dict(sha256=A0[s]["sha"], path=A0[s]["path"], archived_sha256=ARCH[s], g_WA=float(A0[s]["g"][WA].mean()), sharpe_WA=shp(A0[s]["g"][WA]), tau_matched_WA=float(A0[s]["tau"][WA].mean()), tau_raw_WA=float(A0[s]["tau_raw"][WA].mean()),
                       tau_ratio_matched_over_raw=float((A0[s]["tau"][WA] / A0[s]["tau_raw"][WA]).mean()), carry_WA=float(A0[s]["car"][WA].mean()), cost_WA=float(A0[s]["cst"][WA].mean()), pnl_WA=float(A0[s]["pnl"][WA].mean()),
                       g_KL=float(A0[s]["g"][WA & KL].mean()), sharpe_KL=shp(A0[s]["g"][WA & KL]), tail_WT=tail(A0[s], WT), tail_KL=tail(A0[s], WT & KL), by_year={int(y): float(A0[s]["g"][WA & (YEAR == y)].mean()) for y in sorted(set(YEAR[WA].tolist()))}) for s in SEEDS},
           leg_vs_book_carry={s: legcarry(s) for s in SEEDS}, arms={})
for a in ARMS:
    OUT["arms"][a] = {}
    for s in SEEDS:
        x = AR[(a, s)]; b = A0[s]
        o = dict(sha256=x["sha"], path=x["path"], cfg_knobs={k: x["cfg"].get(k) for k in ("FTPOS", "SEATNET", "FTRIM_TH", "FSEED", "FPRED")}, cfg_R15=x["cfg"].get("R15"), device_self_sha256=x["cfg"]["UPLIFT"]["self_sha256"],
                 W_ALPHA=block(x, b, WA), KING_LIVE=block(x, b, WA & KL), tail_WT=tail(x, WT), tail_KL=tail(x, WT & KL), regime=regime(x, b), nulls=nulls(a, s))
        if a in ("S", "SB"): o["seat"] = seat(x, b)
        if a == "SB": o["sb_seat_inputs"] = sb_seat_inputs(s)
        OUT["arms"][a][s] = o
# ------------------------------------------------------------------ verdicts (PREREG §11)
def verdict(a):
    c = {}
    for s in SEEDS:
        o = OUT["arms"][a][s]; w = o["W_ALPHA"]; tA = o["tail_WT"]; tB = OUT["A0"][s]["tail_WT"]
        c[s] = dict(ci99K_lo_gt0=w["ci99K"][0] > 0, ci99K_hi_lt0=w["ci99K"][1] < 0, dg_ge_res=w["dg"] >= RES_BPS, dtau_le_15=w["dtau_pct"] <= 15.0, dtau_gt_25=w["dtau_pct"] > 25.0,
                    maxDD_ok=tA["maxDD"] <= 1.10 * tB["maxDD"], halt_ok=tA["halt4"] <= tB["halt4"], lambda_sign_stable=w["dg_sign_stable_over_lambda"],
                    beats_relab=(o["nulls"]["summary"]["beats_all_relab"] if o["nulls"] else None))
    rej = any(c[s]["ci99K_hi_lt0"] or c[s]["dtau_gt_25"] for s in SEEDS)
    adm = all(c[s]["ci99K_lo_gt0"] and c[s]["dg_ge_res"] and c[s]["dtau_le_15"] and c[s]["maxDD_ok"] and c[s]["halt_ok"] and c[s]["lambda_sign_stable"] and (c[s]["beats_relab"] in (True, None)) for s in SEEDS)
    v = "REJECT" if rej else ("ADMIT" if adm else "UNDECIDED")
    return dict(verdict=v, conditions=c, deployability="NOT_DEPLOYABLE as-is: book-behaviour change (production FTRIM is score-level in combo_stage.py; seat rule lives in shadow_loop_v3.py); requires prereg + user ruling. MEASURED ONLY.",
                nulls_run=(a in ("F", "S")))
OUT["mechgate_F_position_zero_pass"] = MECH_F_ZERO
OUT["verdicts"] = {a: verdict(a) for a in ARMS}; OUT["built_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
json.dump(OUT, open(R + "/receipts/RECEIPT_r15_judge.json", "w"), indent=1, default=float)
# rec-only copies for the repo
os.makedirs(R + "/receipts/arms_rec", exist_ok=True); RS = {}
for a in ARMS:
    for s in SEEDS:
        x = AR[(a, s)]; p = R + "/receipts/arms_rec/%s.npz" % (ARMFILE[a] % s); np.savez_compressed(p, cols=np.array(x["cols"]), rec=x["rec"], config_json=np.array(json.dumps(x["cfg"])), source_sha256=np.array(x["sha"])); RS[os.path.basename(p)] = sha(p)
json.dump(RS, open(R + "/receipts/arms_rec/SHA256_arms_rec.json", "w"), indent=1)
# ------------------------------------------------------------------ print
print("A0", {s: dict(g=round(OUT["A0"][s]["g_WA"], 4), sh=round(OUT["A0"][s]["sharpe_WA"], 4), tau=round(OUT["A0"][s]["tau_matched_WA"], 7), maxDD=round(OUT["A0"][s]["tail_WT"]["maxDD"], 4), halt=OUT["A0"][s]["tail_WT"]["halt4"]) for s in SEEDS})
print("LEG_VS_BOOK_CARRY", json.dumps(OUT["leg_vs_book_carry"]["42"], indent=None))
for a in ARMS:
    for s in SEEDS:
        o = OUT["arms"][a][s]; w = o["W_ALPHA"]; k = o["KING_LIVE"]; t = o["tail_WT"]; tb = OUT["A0"][s]["tail_WT"]; rg = o["regime"]
        print("\n== %s s%s  WA: dg %+.4f CI95 [%+.4f,%+.4f] CI99K [%+.4f,%+.4f] | dpnl %+.4f dcarry %+.4f dcost %+.4f | tau %.5f vs %.5f (%+.2f%%) | Sh %.3f vs %.3f" % (
            a, s, w["dg"], w["ci95"][0], w["ci95"][1], w["ci99K"][0], w["ci99K"][1], w["dpnl"], w["dcarry"], w["dcost"], w["tau_matched_arm"], w["tau_matched_A0"], w["dtau_pct"], w["sharpe_arm"], w["sharpe_A0"]))
        print("   KL: dg %+.4f CI95 [%+.4f,%+.4f] CI99K [%+.4f,%+.4f] | dpnl %+.4f dcarry %+.4f dcost %+.4f | tau %+.2f%% | Sh %.3f vs %.3f" % (k["dg"], k["ci95"][0], k["ci95"][1], k["ci99K"][0], k["ci99K"][1], k["dpnl"], k["dcarry"], k["dcost"], k["dtau_pct"], k["sharpe_arm"], k["sharpe_A0"]))
        print("   lambda:", {l: round(v["dg"], 4) for l, v in w["survival"].items()}, "sign stable", w["dg_sign_stable_over_lambda"], "| by year dg:", {y: round(v["dg"], 3) for y, v in w["by_year"].items()})
        print("   TAIL WT: maxDD %.4f vs %.4f | worst %s %.4f vs %s %.4f | halt %d vs %d | alert %d vs %d" % (t["maxDD"], tb["maxDD"], t["worst_day"], t["worst_day_ret"], tb["worst_day"], tb["worst_day_ret"], t["halt4"], tb["halt4"], t["alert268"], tb["alert268"]))
        print("   REGIME: Sh>3 %d->%d ; Sh_lo>3 %d->%d ; cells dg CI95 excl 0: %d / %d" % (rg["sharpe_gt3_before"], rg["sharpe_gt3_after"], rg["sharpe_lo_gt3_before"], rg["sharpe_lo_gt3_after"], rg["cells_dg_ci95_excl0"], rg["n_cells"]))
        if o["nulls"]: print("   NULLS:", json.dumps(o["nulls"]["summary"]))
        if "seat" in o: print("   SEAT: w3_king %.3f vs %.3f (KL %.3f vs %.3f) P(>=.85) %.3f vs %.3f | sigf:" % (o["seat"]["w3_king"]["arm_mean"], o["seat"]["w3_king"]["A0_mean"], o["seat"]["w3_king"]["arm_king_live_mean"], o["seat"]["w3_king"]["A0_king_live_mean"], o["seat"]["P_w3_king_ge_085_arm"], o["seat"]["P_w3_king_ge_085_A0"]), {k2: (round(v["dg"], 3), [round(c, 3) for c in v["ci95"]]) for k2, v in o["seat"]["sigf_terciles"].items()})
        print("   VERDICT", OUT["verdicts"][a]["verdict"], OUT["verdicts"][a]["conditions"][s])
print("DONE_r15_judge")
