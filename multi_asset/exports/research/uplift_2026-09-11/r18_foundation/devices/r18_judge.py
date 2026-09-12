#!/usr/bin/env python3
"""r18_judge.py — PREREG_r18 §4/§5 statistics for the 12 arms (6 families x 2 seeds), read-only, CPU.
Runs only after RECEIPT_r18_drive_gateP.json (GATE P PASS) and RECEIPT_r18_gates.json exist; asserts both.
g = net_ex/gross_total (bps/anchor/unit gross). W_FULL n=10038, W_ALPHA n=9138, KING_LIVE (ts>=2024-01-01).
Paired dg vs C0 of the same seed; UTC-day block bootstrap 2000, default_rng([20260905,k]); CI95 and CI99K (K=8).
Tail table at L in {1,1.25,1.4,1.5,2,2.5} x M in {1.0,1.4042} with TRUE peak-to-trough maxDD (§4/§6).
Published-verdict re-check on the ARCHIVED r15 / r16 arms (§5.4). Caliber read from each artifact's config_json.
"""
import os, sys, json, time, hashlib, calendar
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "launch with a non-empty env whitelist as argv[1]"
BANNED = ('CAL', 'JUDGE', 'UPLIFT', 'PANEL', 'LOOK', 'WRULE', 'LEGS', 'PHI', 'FSEED', 'W3FIX', 'FTRIM', 'UMASK', 'SLOW', 'FPRED', 'MEMBERS_TOPN', 'COSTB', 'SLEEVE', 'KMOD', 'SEAT', 'RNSM', 'LTRIM', 'CDAMP', 'FUNDSCALE', 'FEMAT', 'TRADE_TOPN', 'REF_SKIP', 'PYTHON', 'OMP', 'MKL', 'R18', 'SMA', 'SBAND', 'FTPOS', 'OUT_TAG')
EXTRA = sorted(k for k in os.environ if k not in WHITE); assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
BAN = sorted(k for k in os.environ if k.startswith(BANNED)); assert BAN == [], ("CALIBER FLAG PRESENT", BAN)
ENV = dict(env_whitelist=sorted(WHITE), env_actual={k: os.environ[k] for k in sorted(os.environ)}, launch_cmdline=" ".join(sys.argv))
import numpy as np
ENV.update(python=sys.version.split()[0], numpy=np.__version__)
R = "/workspace/uplift_2026-09-11/r18_foundation"; UP = "/workspace/uplift_2026-09-11"
PREREG_SHA = "51120518b72f70ce3f78c4ef1e68b0ec655c76eb385692befcf904d0d2883f6c"
DER_SHA = "9b8a6323e8f0ac31ecb4046f6759dce09ba89645cbfc356db71f51c662b2c5c4"
def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
assert sha(R + "/PREREG_r18_foundation_2026-09-12.md") == PREREG_SHA
G = json.load(open(R + "/receipts/RECEIPT_r18_drive_gateP.json")); assert G["gate"]["P"]["PASS"], G["gate"]
assert G["derived_device_sha256"] == DER_SHA
AMEND_SHA = "f8c23823259ee542c29672958ee1f53e066f50022843e9b14e77f88b32994025"; assert sha(R + "/PREREG_AMENDMENT_1_r18_2026-09-12.md") == AMEND_SHA
GT = json.load(open(R + "/receipts/RECEIPT_r18_gates.json")); assert GT["GATE_Y2"]["window_PASS"], GT["GATE_Y2"]; assert GT["GATE_R"]["PASS"], GT["GATE_R"]; assert GT["amendment_sha256"] == AMEND_SHA
K = 8; ALPHA_K = 0.05 / K; PCT_K = (100 * ALPHA_K / 2, 100 * (1 - ALPHA_K / 2)); NB = 2000; RES_BPS = 0.23
UB = calendar.timegm((2026, 8, 30, 20, 0, 0)); K24 = calendar.timegm((2024, 1, 1, 0, 0, 0)); T0607 = calendar.timegm((2022, 6, 7, 20, 0, 0))
SEEDS = ("42", "2027"); FAM = ("C0", "N2", "WU", "NW", "NW_S05", "NW_B50")
EXPECT = {"C0": dict(R18_ELIG=0, R18_WARM=0, SMA=0.1, SBAND=2.5e-4), "N2": dict(R18_ELIG=1, R18_WARM=0, SMA=0.1, SBAND=2.5e-4), "WU": dict(R18_ELIG=0, R18_WARM=1, SMA=0.1, SBAND=2.5e-4),
          "NW": dict(R18_ELIG=1, R18_WARM=1, SMA=0.1, SBAND=2.5e-4), "NW_S05": dict(R18_ELIG=1, R18_WARM=1, SMA=0.05, SBAND=2.5e-4), "NW_B50": dict(R18_ELIG=1, R18_WARM=1, SMA=0.10, SBAND=5.0e-4)}
LEVS = (1.0, 1.25, 1.4, 1.5, 2.0, 2.5); MULTS = (1.0, 1.4042); HALT = -0.04; ALERT = -0.0268; DDLIM = -0.25
def load(p, expect=None, r18=True):
    Z = np.load(p, allow_pickle=True); C = [str(c) for c in Z["cols"]]; rec = np.asarray(Z["d30_n2_c42_rec"] if "d30_n2_c42_rec" in Z else Z["rec"], float)
    cfg = json.loads(str(Z["config_json"]))
    assert cfg["CAL"] == "log" and cfg["PHI"] == 0.45 and cfg["LEGS"] == "101" and cfg["WRULE"] == "msharpe" and cfg["W3FIX"] is None and cfg["UMASK_SCOPE"] == "m1" and cfg["LOOK"] == 900 and cfg["FTRIM"] == "zero" and cfg["MEMBERS_TOPN"] == 829, cfg
    assert cfg["COSTB_JSON"].endswith("costb_PWR_G230k.json") and cfg["SLOW_NPY"].endswith("SLOW_v3_on_v4axis.npy"), cfg
    if r18:
        assert cfg["UPLIFT"]["self_sha256"] == DER_SHA and cfg["R18"]["prereg_sha256"] == PREREG_SHA, cfg["R18"]
        for k, v in expect.items(): assert cfg["R18"][k] == v, (k, cfg["R18"][k], v)
    col = lambda k: rec[:, C.index(k)]
    ts = col("ts").astype(np.int64); gt = col("gross_total")
    d = dict(ts=ts, gt=gt, g=col("net_ex") / gt, pnl=col("pnl_ex") / gt, car=col("carry_ex") / gt, cst=col("cost_ex") / gt, tau_raw=col("turnover"), tau=col("turnover") / gt,
             w3k=col("w3_king"), w3r=col("w3_rev24"), w3f=col("w3_fund"), lk=col("leg_king"), lr=col("leg_rev24"), lf=col("leg_fund"), nl=col("netlong"), cfg=cfg, sha=sha(p), path=p, cols=C, rec=rec)
    assert np.allclose(d["pnl"] - d["car"] - d["cst"], d["g"], atol=1e-9)
    d["WT"] = ts <= UB; d["WA"] = d["WT"].copy(); d["WA"][:900] = False; assert d["WA"].sum() == 9138 and d["WT"].sum() == 10038, (d["WA"].sum(), d["WT"].sum())
    d["KL"] = ts >= K24; assert (d["WA"] & d["KL"]).sum() == 5838
    if "d30_n2_c42_R18A" in Z: d["aux"] = np.asarray(Z["d30_n2_c42_R18A"], float); d["aux_cols"] = [str(c) for c in Z["d30_n2_c42_R18A_cols"]]; assert np.array_equal(d["aux"][:, 0].astype(np.int64), ts)
    if "d30_n2_c42_W" in Z: d["W"] = np.asarray(Z["d30_n2_c42_W"], np.float32)
    return d
AR = {(f, s): load(R + "/arms/%s_s%s.npz" % (f, s), EXPECT[f]) for f in FAM for s in SEEDS}
ts = AR[("C0", "42")]["ts"]; WA = AR[("C0", "42")]["WA"]; WT = AR[("C0", "42")]["WT"]; KL = AR[("C0", "42")]["KL"]
for k, x in AR.items(): assert np.array_equal(x["ts"], ts), k
for s in SEEDS:   # C0 is bitwise the archived A0 (GATE P); re-assert the published anchors on s42
    x = AR[("C0", s)]["g"][WA]
    if s == "42": assert abs(x.mean() - 0.6341957) < 5e-7 and abs(AR[("C0", s)]["tau"][WA].mean() - 0.0540270) < 5e-7
DAY = np.array([time.strftime("%Y%m%d", time.gmtime(int(t))) for t in ts]); YEAR = np.array([time.gmtime(int(t)).tm_year for t in ts]); DAYS = (ts // 86400) * 86400
# ------------------------------------------------------------------ bootstrap
_DRAW = {}
def draws(nd):
    if nd not in _DRAW: _DRAW[nd] = np.stack([np.random.default_rng([20260905, k]).integers(0, nd, nd) for k in range(NB)])
    return _DRAW[nd]
def boot(d, mask, k9=False):
    idx = np.nonzero(mask)[0]; dd = {}
    for k in idx: dd.setdefault(DAY[k], []).append(k)
    keys = sorted(dd); tot = np.array([d[dd[k]].sum() for k in keys]); cnt = np.array([len(dd[k]) for k in keys], float); nd = len(keys)
    r = draws(nd); ms = tot[r].sum(1) / cnt[r].sum(1)
    o = dict(ci95=[float(np.percentile(ms, 2.5)), float(np.percentile(ms, 97.5))], ci99K=[float(np.percentile(ms, PCT_K[0])), float(np.percentile(ms, PCT_K[1]))], se=float(ms.std(ddof=1)), n_days=nd)
    if k9:
        r9 = np.stack([np.random.default_rng([20260905, 9 * NB + k]).integers(0, nd, nd) for k in range(NB)]); m9 = tot[r9].sum(1) / cnt[r9].sum(1)
        o["ci95_k9"] = [float(np.percentile(m9, 2.5)), float(np.percentile(m9, 97.5))]
    return o
def shp(x): return float(x.mean() / x.std(ddof=1) * np.sqrt(2190))
def level(x, mask):
    g = x["g"][mask]; n = int(mask.sum()); b = boot(x["g"], mask)
    return dict(n=n, g=float(g.mean()), ci95=b["ci95"], se_boot=b["se"], sharpe=shp(g), sharpe_se=float(np.sqrt(2190 / n)), tau_matched=float(x["tau"][mask].mean()), tau_raw=float(x["tau_raw"][mask].mean()),
                pnl=float(x["pnl"][mask].mean()), carry=float(x["car"][mask].mean()), cost=float(x["cst"][mask].mean()), gross_total=float(x["gt"][mask].mean()), netlong=float(x["nl"][mask].mean()),
                by_year={int(y): dict(n=int((mask & (YEAR == y)).sum()), g=float(x["g"][mask & (YEAR == y)].mean()), sharpe=shp(x["g"][mask & (YEAR == y)]) if (mask & (YEAR == y)).sum() > 30 else None) for y in sorted(set(YEAR[mask].tolist()))})
def block(arm, base, mask):
    d = arm["g"] - base["g"]; n = int(mask.sum()); b = boot(d, mask, k9=True)
    o = dict(n=n, g_arm=float(arm["g"][mask].mean()), g_base=float(base["g"][mask].mean()), dg=float(d[mask].mean()), **b, sharpe_arm=shp(arm["g"][mask]), sharpe_base=shp(base["g"][mask]), sharpe_se=float(np.sqrt(2190 / n)),
             dpnl=float((arm["pnl"] - base["pnl"])[mask].mean()), dcarry=float((arm["car"] - base["car"])[mask].mean()), dcost=float((arm["cst"] - base["cst"])[mask].mean()),
             tau_matched_arm=float(arm["tau"][mask].mean()), tau_matched_base=float(base["tau"][mask].mean()), n_anchors_g_differs=int((np.abs(d[mask]) > 1e-12).sum()),
             first_anchor_g_differs=(time.strftime("%Y-%m-%d %HZ", time.gmtime(int(ts[mask][np.nonzero(np.abs(d[mask]) > 1e-12)[0][0]]))) if (np.abs(d[mask]) > 1e-12).any() else None),
             last_anchor_g_differs=(time.strftime("%Y-%m-%d %HZ", time.gmtime(int(ts[mask][np.nonzero(np.abs(d[mask]) > 1e-12)[0][-1]]))) if (np.abs(d[mask]) > 1e-12).any() else None))
    o["dtau_matched"] = o["tau_matched_arm"] - o["tau_matched_base"]; o["dtau_pct"] = 100 * o["dtau_matched"] / o["tau_matched_base"]
    assert abs(o["dpnl"] - o["dcarry"] - o["dcost"] - o["dg"]) < 1e-9
    o["ci95_excl0"] = bool(o["ci95"][0] > 0 or o["ci95"][1] < 0); o["ci99K_excl0"] = bool(o["ci99K"][0] > 0 or o["ci99K"][1] < 0); o["abs_dg_ge_resolution"] = bool(abs(o["dg"]) >= RES_BPS)
    o["by_year"] = {int(y): dict(n=int((mask & (YEAR == y)).sum()), g_arm=float(arm["g"][mask & (YEAR == y)].mean()), g_base=float(base["g"][mask & (YEAR == y)].mean()), dg=float(d[mask & (YEAR == y)].mean())) for y in sorted(set(YEAR[mask].tolist()))}
    return o
# ------------------------------------------------------------------ tail (PREREG §4 / §6)
def dayret(g, mask, L):
    idx = np.nonzero(mask)[0]; ud, inv = np.unique(DAYS[idx], return_inverse=True); out = np.ones(len(ud))
    np.multiply.at(out, inv, 1.0 + L * g[idx] * 1e-4); return ud, out - 1.0
def roll1y(ud, rs):
    tdd, sl, cg = [], [], []
    for s in range(len(ud)):
        e = np.searchsorted(ud, ud[s] + 365 * 86400, side="right")
        if e - s < 300 or ud[e - 1] - ud[s] < 350 * 86400: continue
        nav = np.concatenate([[1.0], np.cumprod(1.0 + rs[s:e])]); tdd.append(float((nav / np.maximum.accumulate(nav) - 1.0).min())); sl.append(float(nav[1:].min() - 1.0)); cg.append(float(nav[-1] - 1.0))
    return np.array(tdd), np.array(sl), np.array(cg)
def tailrow(g, mask, L, M):
    ud, rd = dayret(g, mask, L); mu = rd.mean(); rs = mu + M * (rd - mu)
    nav = np.concatenate([[1.0], np.cumprod(1.0 + rs)]); dd = nav / np.maximum.accumulate(nav) - 1.0; it = int(np.argmin(dd)); ip = int(np.argmax(nav[:it + 1]))
    tdd, sl, cg = roll1y(ud, rs); yrs = (ud[-1] - ud[0]) / (365.25 * 86400); w = int(np.argmin(rs))
    return dict(L=L, M=M, n_days=int(len(ud)), maxdd=float(dd.min()), maxdd_peak=time.strftime("%Y-%m-%d", time.gmtime(int(ud[ip - 1]))) if ip > 0 else "start", maxdd_trough=time.strftime("%Y-%m-%d", time.gmtime(int(ud[it - 1]))),
                worst_day=time.strftime("%Y-%m-%d", time.gmtime(int(ud[w]))), worst_day_ret=float(rs[w]), halt=int((rs <= HALT).sum()), alert=int((rs <= ALERT).sum()), halt_per_yr=float((rs <= HALT).sum() / yrs),
                p_true_maxDD25=float((tdd <= DDLIM).mean()), p_start_loss25=float((sl <= DDLIM).mean()), median_1y_ret=float(np.median(cg)), n_windows=int(len(cg)), ann_ret=float(nav[-1] ** (365.25 * 86400 / (ud[-1] - ud[0] + 86400)) - 1.0), sd_day=float(rs.std(ddof=1)))
def tail(x, mask): return {"L%.2f_M%.4f" % (L, M): tailrow(x["g"], mask, L, M) for L in LEVS for M in MULTS}
# ------------------------------------------------------------------ N2 readouts (§5.1)
def n2(s):
    a, c = AR[("N2", s)], AR[("C0", s)]; A = a["aux"]; ac = a["aux_cols"]; ci = lambda k: A[:, ac.index(k)]
    o = dict(aux_full=dict(n_elig_changed=int(ci("n_elig_changed")[WT].sum()), n_new_only=int(ci("n_elig_new_only")[WT].sum()), n_old_only=int(ci("n_elig_old_only")[WT].sum()), anchors_changed=int((ci("n_elig_changed")[WT] > 0).sum())),
             aux_WA=dict(n_elig_changed=int(ci("n_elig_changed")[WA].sum()), n_new_only=int(ci("n_elig_new_only")[WA].sum()), n_old_only=int(ci("n_elig_old_only")[WA].sum()), anchors_changed=int((ci("n_elig_changed")[WA] > 0).sum())),
             unknown_return_exposure=dict(WT=dict(cells=int(ci("n_sel_y4nan")[WT].sum()), anchors=int((ci("n_sel_y4nan")[WT] > 0).sum()), sum_abs_sm=float(ci("gross_y4nan")[WT].sum()), max_abs_sm_anchor=float(ci("gross_y4nan")[WT].max())),
                                          WA=dict(cells=int(ci("n_sel_y4nan")[WA].sum()), anchors=int((ci("n_sel_y4nan")[WA] > 0).sum()), sum_abs_sm=float(ci("gross_y4nan")[WA].sum()), max_abs_sm_anchor=float(ci("gross_y4nan")[WA].max()))),
             c0_unknown_return_cells_WT=int(c["aux"][:, c["aux_cols"].index("n_sel_y4nan")][WT].sum()),
             input_side_counts=GT["ELIG_DIFF"], W_FULL=block(a, c, WT), W_ALPHA=block(a, c, WA), KING_LIVE=block(a, c, WA & KL), tail=tail(a, WT))
    cells = []
    for h in GT["GATE_R"]["held_cells"]:
        r_, c_ = h["row"], h["col"]
        cells.append(dict(iso=h["iso"], symbol=h["symbol"], C0_W_prev=float(c["W"][r_ - 1, c_]), C0_W=float(c["W"][r_, c_]), C0_W_next=float(c["W"][r_ + 1, c_]), N2_W_prev=float(a["W"][r_ - 1, c_]), N2_W=float(a["W"][r_, c_]), N2_W_next=float(a["W"][r_ + 1, c_]),
                          N2_position_kept_at_i=bool(abs(a["W"][r_, c_]) > 1e-9), N2_exit_at_i_plus_1=bool(abs(a["W"][r_ + 1, c_]) <= 1e-9)))
    o["reviewer_cells"] = cells; o["reviewer_cells_all_kept"] = all(c_["N2_position_kept_at_i"] for c_ in cells)
    fut = np.zeros(a["W"].shape, bool)   # under N2, |W| on the reviewer's fut cells (old rule): max abs
    return o
# ------------------------------------------------------------------ WU readouts (§5.2)
def wu(s):
    a, c = AR[("WU", s)], AR[("C0", s)]; warm = np.arange(len(ts)) < 900
    o = dict(warm_rows=dict(n=900, first=time.strftime("%Y-%m-%d %HZ", time.gmtime(int(ts[0]))), last=time.strftime("%Y-%m-%d %HZ", time.gmtime(int(ts[899])))),
             w3_before=dict(king=float(c["w3k"][warm].mean()), rev24=float(c["w3r"][warm].mean()), fund=float(c["w3f"][warm].mean()), rev24_max=float(c["w3r"][warm].max()), unique_triples=[list(map(float, t)) for t in sorted(set(zip(c["w3k"][warm].round(6), c["w3r"][warm].round(6), c["w3f"][warm].round(6))))]),
             w3_after=dict(king=float(a["w3k"][warm].mean()), rev24=float(a["w3r"][warm].mean()), fund=float(a["w3f"][warm].mean()), rev24_max=float(a["w3r"][warm].max()), unique_triples=[list(map(float, t)) for t in sorted(set(zip(a["w3k"][warm].round(6), a["w3r"][warm].round(6), a["w3f"][warm].round(6))))]),
             rev24_weight_zero_on_all_warm_rows_after=bool((a["w3r"][warm] == 0.0).all()), rev24_weight_after_row900_C0_max=float(np.abs(c["w3r"][~warm]).max()), rev24_weight_after_row900_WU_max=float(np.abs(a["w3r"][~warm]).max()),
             leg_rev24_nonzero_rows_before=int((c["lr"] != 0).sum()), leg_rev24_nonzero_rows_after=int((a["lr"] != 0).sum()))
    i7 = int(np.nonzero(ts == T0607)[0][0]); r7 = ts // 86400 == T0607 // 86400
    def anchor(x, i): return dict(iso=time.strftime("%Y-%m-%d %HZ", time.gmtime(int(ts[i]))), g=float(x["g"][i]), gross_total=float(x["gt"][i]), net_ex_bps=float(x["g"][i] * x["gt"][i]), leg_king=float(x["lk"][i]), leg_rev24=float(x["lr"][i]), leg_fund=float(x["lf"][i]), w3=[float(x["w3k"][i]), float(x["w3r"][i]), float(x["w3f"][i])], pnl=float(x["pnl"][i]), carry=float(x["car"][i]), cost=float(x["cst"][i]))
    def day(x, mask_day): return dict(anchors=int(mask_day.sum()), sum_g=float(x["g"][mask_day].sum()), day_ret_L2=float(np.prod(1 + 2.0 * x["g"][mask_day] * 1e-4) - 1), sum_leg_king=float(x["lk"][mask_day].sum()), sum_leg_rev24=float(x["lr"][mask_day].sum()), sum_leg_fund=float(x["lf"][mask_day].sum()), per_anchor_g=[float(v) for v in x["g"][mask_day]])
    o["anchor_2022_06_07_20Z"] = dict(before=anchor(c, i7), after=anchor(a, i7)); o["day_2022_06_07"] = dict(before=day(c, r7), after=day(a, r7))
    for nm, x in (("before", c), ("after", a)):
        t = tailrow(x["g"], WT, 2.0, 1.0); wd = calendar.timegm(time.strptime(t["worst_day"], "%Y-%m-%d")); md = ts // 86400 * 86400 == wd
        o["worst_day_L2_M1_" + nm] = dict(worst_day=t["worst_day"], day_ret=t["worst_day_ret"], decomposition=day(x, md))
    o["W_FULL"] = block(a, c, WT); o["W_ALPHA"] = block(a, c, WA); o["KING_LIVE"] = block(a, c, WA & KL); o["tail"] = tail(a, WT); o["tail_C0"] = tail(c, WT)
    return o
# ------------------------------------------------------------------ NW readouts (§5.3)
A1X = dict(g=0.6602, sharpe=1.2857, n=9199, ci95=[0.1673, 1.1472], source="RESULT_r11_cost_tail_income_2026-09-12.md L84 / CLOSEOUT §… (A1x_ext_s42: v4-native legs, upper bound 2026-09-10 00Z, post-warm drop 900); s2027 +0.6828 / 1.3288", label="INFERRED (quoted; different axis and model legs; unpaired)")
def nw(s):
    a, c = AR[("NW", s)], AR[("C0", s)]
    o = dict(level_W_FULL=level(a, WT), level_W_ALPHA=level(a, WA), level_KING_LIVE=level(a, WA & KL), C0_level_W_FULL=level(c, WT), C0_level_W_ALPHA=level(c, WA),
             vs_C0=dict(W_FULL=block(a, c, WT), W_ALPHA=block(a, c, WA), KING_LIVE=block(a, c, WA & KL)), tail=tail(a, WT), tail_C0=tail(c, WT), A1x_reference=A1X,
             vs_A1x_unpaired=dict(dg_WA=float(a["g"][WA].mean() - A1X["g"]), dsharpe_WA=shp(a["g"][WA]) - A1X["sharpe"], note="unpaired, different axis (n 9138 vs 9199) and different model legs; INFERRED"))
    for f in ("NW_S05", "NW_B50"):
        x = AR[(f, s)]; o["smoothing_" + f] = dict(W_ALPHA=block(x, a, WA), W_FULL=block(x, a, WT), level_W_ALPHA=level(x, WA), tail=tail(x, WT))
    return o
# ------------------------------------------------------------------ published verdicts (§5.4), archived arms, no re-runs
PUB = {"r15": {"F": "F_s%s", "S": "S_s%s", "SB": "SB_s%s", "F05": "F05_s%s", "F20": "F20_s%s"}, "r16": {"X%d" % k: "A_X%d_s%%s" % k for k in range(6)}}
PUBDIR = {"r15": UP + "/r15_structural/arms/", "r16": UP + "/r16_asym_band/arms/"}
def published():
    out = {}
    for rnd, arms in PUB.items():
        for a, pat in arms.items():
            for s in SEEDS:
                p = PUBDIR[rnd] + (pat % s) + ".npz"
                if not os.path.exists(p): out["%s/%s/s%s" % (rnd, a, s)] = dict(missing=True, path=p); continue
                x = load(p, r18=False); assert np.array_equal(x["ts"], ts), p
                c, n_ = AR[("C0", s)], AR[("NW", s)]
                vA = {w: block(x, c, m) for w, m in (("W_ALPHA", WA), ("KING_LIVE", WA & KL))}; vN = {w: block(x, n_, m) for w, m in (("W_ALPHA", WA), ("KING_LIVE", WA & KL))}
                out["%s/%s/s%s" % (rnd, a, s)] = dict(path=p, sha256=x["sha"], vs_A0={w: {k: v[k] for k in ("dg", "ci95", "ci95_excl0", "dtau_pct", "n")} for w, v in vA.items()}, vs_NW={w: {k: v[k] for k in ("dg", "ci95", "ci95_excl0", "dtau_pct")} for w, v in vN.items()},
                                                   sign_change_W_ALPHA=bool(np.sign(vA["W_ALPHA"]["dg"]) != np.sign(vN["W_ALPHA"]["dg"])), ci_status_change_W_ALPHA=bool(vA["W_ALPHA"]["ci95_excl0"] != vN["W_ALPHA"]["ci95_excl0"]),
                                                   sign_change_KING_LIVE=bool(np.sign(vA["KING_LIVE"]["dg"]) != np.sign(vN["KING_LIVE"]["dg"])), ci_status_change_KING_LIVE=bool(vA["KING_LIVE"]["ci95_excl0"] != vN["KING_LIVE"]["ci95_excl0"]),
                                                   NW_minus_A0_W_ALPHA=float((n_["g"] - c["g"])[WA].mean()), confound_note="arm was run with N2/WU defects ON; dg_vs_NW = dg_vs_A0 - (NW - A0). Not a clean re-test.")
    return out
# ------------------------------------------------------------------ assemble
OUT = dict(self_sha256=sha(os.path.abspath(__file__)), prereg_sha256=PREREG_SHA, derived_device_sha256=DER_SHA, K=K, alpha_K=ALPHA_K, env=ENV, windows=dict(W_FULL=int(WT.sum()), W_ALPHA=int(WA.sum()), KING_LIVE_in_W_ALPHA=int((WA & KL).sum()), UB_utc="2026-08-30 20Z"),
           arms={"%s_s%s" % k: dict(path=v["path"], sha256=v["sha"], R18=v["cfg"]["R18"]) for k, v in AR.items()},
           C0={s: dict(level_W_FULL=level(AR[("C0", s)], WT), level_W_ALPHA=level(AR[("C0", s)], WA), level_KING_LIVE=level(AR[("C0", s)], WA & KL), tail=tail(AR[("C0", s)], WT)) for s in SEEDS},
           N2={s: n2(s) for s in SEEDS}, WU={s: wu(s) for s in SEEDS}, NW={s: nw(s) for s in SEEDS}, published=published(), built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
json.dump(OUT, open(R + "/receipts/RECEIPT_r18_judge.json", "w"), indent=1, default=float)
os.makedirs(R + "/receipts/arms_rec", exist_ok=True); RS = {}
for (f, s), x in AR.items():
    p = R + "/receipts/arms_rec/%s_s%s.npz" % (f, s); kw = dict(cols=np.array(x["cols"]), rec=x["rec"], config_json=np.array(json.dumps(x["cfg"])), source_sha256=np.array(x["sha"]))
    if "aux" in x: kw["R18A"] = x["aux"]; kw["R18A_cols"] = np.array(x["aux_cols"])
    np.savez_compressed(p, **kw); RS[os.path.basename(p)] = sha(p)
json.dump(RS, open(R + "/receipts/arms_rec/SHA256_arms_rec.json", "w"), indent=1)
for s in SEEDS:
    print("\n== seed", s)
    print("C0  WA g %.4f sh %.4f | WT g %.4f sh %.4f" % (OUT["C0"][s]["level_W_ALPHA"]["g"], OUT["C0"][s]["level_W_ALPHA"]["sharpe"], OUT["C0"][s]["level_W_FULL"]["g"], OUT["C0"][s]["level_W_FULL"]["sharpe"]))
    for f, key in (("N2", "N2"), ("WU", "WU")):
        o = OUT[key][s]
        for w in ("W_FULL", "W_ALPHA"): print("%s %s dg %+.4f CI95 [%+.4f,%+.4f] n_differs %d first %s" % (f, w, o[w]["dg"], o[w]["ci95"][0], o[w]["ci95"][1], o[w]["n_anchors_g_differs"], o[w]["first_anchor_g_differs"]))
    o = OUT["NW"][s]
    for w in ("W_FULL", "W_ALPHA"): print("NW %s g %.4f CI95 [%.4f,%.4f] sh %.4f tau %.5f | dg vs C0 %+.4f [%+.4f,%+.4f]" % (w, o["level_" + w]["g"], o["level_" + w]["ci95"][0], o["level_" + w]["ci95"][1], o["level_" + w]["sharpe"], o["level_" + w]["tau_matched"], o["vs_C0"][w]["dg"], o["vs_C0"][w]["ci95"][0], o["vs_C0"][w]["ci95"][1]))
    print("N2 reviewer cells", json.dumps(OUT["N2"][s]["reviewer_cells"])); print("N2 aux", json.dumps(OUT["N2"][s]["aux_full"]), json.dumps(OUT["N2"][s]["unknown_return_exposure"]))
    print("WU w3 before", OUT["WU"][s]["w3_before"]["unique_triples"], "after", OUT["WU"][s]["w3_after"]["unique_triples"], "rev24 zero", OUT["WU"][s]["rev24_weight_zero_on_all_warm_rows_after"])
    print("WU 2022-06-07 20Z", json.dumps(OUT["WU"][s]["anchor_2022_06_07_20Z"])); print("WU worst day", json.dumps({k: v for k, v in OUT["WU"][s]["worst_day_L2_M1_before"].items() if k != "decomposition"}), json.dumps({k: v for k, v in OUT["WU"][s]["worst_day_L2_M1_after"].items() if k != "decomposition"}))
    for f in ("C0", "NW"):
        t = OUT[f][s]["tail"] if f == "C0" else OUT["NW"][s]["tail"]
        for k in ("L1.00_M1.0000", "L2.00_M1.0000", "L1.00_M1.4042", "L2.00_M1.4042"): print(f, k, json.dumps({kk: t[k][kk] for kk in ("maxdd", "worst_day", "worst_day_ret", "halt", "alert", "p_true_maxDD25", "p_start_loss25", "median_1y_ret")}))
print("\nPUBLISHED sign/CI changes:", [(k, v["sign_change_W_ALPHA"], v["ci_status_change_W_ALPHA"]) for k, v in OUT["published"].items() if not v.get("missing") and (v["sign_change_W_ALPHA"] or v["ci_status_change_W_ALPHA"])])
print("DONE_r18_judge")
