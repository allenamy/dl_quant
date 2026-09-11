"""r10_combine STEP 3 (DEFINITIVE) -- book-layer combination of A0 with every screened candidate.

SUPERSEDES devices/s2_combine.py.  s2 used r10_slowclock/out/PWR_COMBO_S.npz for the
SLOW_CLOCK candidate on the strength of its FILENAME.  I then opened that screen's
judge.py and its reprice.py: PWR_COMBO_S is an equal-weight blend of the 13 SIGNALS
run as ONE book, whereas the screen's pre-registered candidate is COMBO_G =
the BOOK-LAYER equal-gross mean of the 13 arms' g series.  Different objects
(+0.4537 vs -0.2716).  E-0825-H near-miss, recorded.  This device rebuilds COMBO_G
from the 13 arm files and gates it against the archived judge numbers.

ENV WHITELIST (E-0826-D) = EMPTY SET.
Caliber pin v4 (2026-09-09).  g = net_ex/gross_total, bps / 4h anchor / unit gross.
Axis: rec[900:] (E-0911-A) then ts <= 2026-08-30 20Z (E-0911-D)  =>  n = 9138.
Bootstrap: UTC-day block, B=2000, numpy.default_rng([20260905,k]).
Allocation: total gross fixed at 2.0x NAV => c_i >= 0, sum_i c_i = 1,
            g_comb = sum_i c_i g_i.  Nothing enters A0's w3 seat.
"""
import os, sys, json, hashlib, calendar, time
ENV_SEEN = sorted(os.environ.keys())
_FORBID = ("LEGS","CAL","WRULE","LOOK","PHI","UMASK_NPZ","UMASK_SCOPE","FSEED","FPRED","COSTB_JSON",
           "MEMBERS_TOPN","FTRIM","SLOW_NPY","W3FIX","FEMAT_NPZ","OUT_TAG","TRADE_TOPN","TILT",
           "TILT_TAU","TILT_K","KMOD","KMOD_F10","KMOD_L","KMOD_AGREE","KTAIL","SEATF10","SEATNET",
           "FUNDSCALE","REF_SKIP","SLEEVE","CDAMP","LTRIM_TH","FTRIM_TH","RNSM","FTPOS","PANEL",
           "PANEL_IN","EXPORT_PANEL","EMA_STATE_JSON","JUDGE_HC","JUDGE_REQUIRE_W")
_v = [k for k in _FORBID if k in os.environ]
assert not _v, "E-0826-D env violation: %r" % _v
import numpy as np
from scipy.stats import spearmanr
from scipy.optimize import minimize

def T(*a): return calendar.timegm(a + (0,)*(6-len(a)))
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()

ROOT = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11"
SCR  = "/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/scratchpad/r10c"
OUT  = ROOT + "/r10_combine"
CUT  = T(2026, 8, 30, 20); WARM = 900; B = 2000; APY = 2190.0
TARGET = 3.966
R = {"step": "S3_COMBINE_FINAL", "self_sha256": sha(os.path.abspath(__file__)),
     "supersedes": "devices/s2_combine.py (SLOW arm-identity error, E-0825-H near-miss)",
     "env_whitelist": [], "env_seen_at_runtime": ENV_SEEN,
     "numpy": np.__version__, "scipy": __import__("scipy").__version__,
     "python": sys.version.split()[0], "B": B}
IN = {}

# ------------------------------------------------------------------ A0 axis + GATE
A0P = SCR + "/A0_PWR230k_s42.npz"; R8P = SCR + "/w10_ablation_series_R8_A0_s42.npz"
IN["A0_r3k_PWR230k_s42"] = A0P; IN["A0_r8b2_R8_A0_s42"] = R8P
a = np.load(A0P, allow_pickle=True)
cols = [str(c) for c in a["cols"]]; ix = {c: i for i, c in enumerate(cols)}
rec = np.asarray(a["rec"], float)
ts_all = np.round(rec[:, ix["ts"]]).astype(np.int64)
selv = np.arange(len(ts_all))[WARM:]; selv = selv[ts_all[selv] <= CUT]
TS = ts_all[selv]; n = len(TS); assert n == 9138, n
def ser(A):
    return dict(g=(A[:, ix["net_ex"]]/A[:, ix["gross_total"]])[selv],
                pnl=(A[:, ix["pnl_ex"]]/A[:, ix["gross_total"]])[selv],
                cost=(A[:, ix["cost_ex"]]/A[:, ix["gross_total"]])[selv],
                carry=(A[:, ix["carry_ex"]]/A[:, ix["gross_total"]])[selv],
                turn=A[:, ix["turnover"]][selv])
A0 = ser(rec)
z8 = np.load(R8P, allow_pickle=True)
c8 = [str(c) for c in z8["cols"]]; assert c8 == cols
A8 = np.asarray(z8["d30_n2_c42_rec"], float)
assert np.array_equal(np.round(A8[:, ix["ts"]]).astype(np.int64), ts_all)
A0b = ser(A8)
gateA0 = {"maxabs_dg": float(np.max(np.abs(A0["g"]-A0b["g"]))),
          "maxabs_dturn": float(np.max(np.abs(A0["turn"]-A0b["turn"]))),
          "two_instruments": ["r3k/arms/A0_PWR230k_s42.npz[rec]",
                              "r8b2/dev/probe_artifacts/w10_ablation_series_R8_A0_s42.npz[d30_n2_c42_rec]"]}
gateA0["PASS_bitwise"] = bool(gateA0["maxabs_dg"] == 0.0)
R["GATE_A0_two_instruments"] = gateA0
print("GATE A0 two-instrument maxabs dg = %.3e  (PASS_bitwise=%s)" % (gateA0["maxabs_dg"], gateA0["PASS_bitwise"]))

def ann(x):
    s = np.std(x, ddof=1); return float(np.mean(x)/s*np.sqrt(APY)) if s > 0 else float("nan")
def mdd(x):
    c = np.concatenate([[0.0], np.cumsum(x)])
    return float(np.max(np.maximum.accumulate(c) - c))
DAY = TS // 86400
ud, inv = np.unique(DAY, return_inverse=True); nd = len(ud)
def worstday(x):
    d = np.bincount(inv, weights=x, minlength=nd); i = int(np.argmin(d))
    return float(d[i]), time.strftime("%Y-%m-%d", time.gmtime(int(ud[i])*86400))
R["axis"] = {"n": n, "span_utc": ["2022-06-30T00:00Z", "2026-08-30T20:00Z"],
             "monotone_4h": bool(np.all(np.diff(TS) == 14400)), "utc_days": int(nd),
             "SE_ann_sharpe": round(float(np.sqrt(APY/n)), 4)}
SE_SR = float(np.sqrt(APY/n))

# ------------------------------------------------------------------ candidate books
BOOKS = {}; TURN = {}; META = {}
def align(ts_src, arr):
    out = np.zeros(n); cov = np.zeros(n, bool)
    pos = {int(t): i for i, t in enumerate(TS)}
    for j, t in enumerate(np.asarray(ts_src)):
        i = pos.get(int(t))
        if i is not None: out[i] = float(arr[j]); cov[i] = True
    return out, cov
def add(name, ts_src, net, turn, arm, note):
    g, cov = align(ts_src, net); t_, _ = align(ts_src, turn)
    BOOKS[name] = g; TURN[name] = t_
    META[name] = {"arm": arm, "note": note, "coverage_anchors": int(cov.sum())}

add("A0", TS, A0["g"], A0["turn"], "d30_n2_c42 dynamic seat @ costb_PWR_G230k",
    "the live book, repriced at the pinned PWR cost model")

d = np.load(SCR + "/tsmom_series.npz", allow_pickle=True); IN["TSMOM_series"] = SCR + "/tsmom_series.npz"
add("TSMOM", d["ts"], d["TSMOM_L42_raw_net"], d["TSMOM_L42_raw_turn"], "TSMOM_L42_raw",
    "r10 TSMOM_DIR pre-declared PRIMARY arm (the surveyor's exact object)")
ALT = {"TSMOM_best": ("TSMOM_L90_raw", d["ts"], d["TSMOM_L90_raw_net"], d["TSMOM_L90_raw_turn"])}

p = ROOT + "/r10_screen/VRP_DELTA1/series_VRP_DELTA1.npz"; IN["VRP_series"] = p
d = np.load(p, allow_pickle=True)
add("VRP", d["ts"], d["net"], d["turnover"], "VRP_L42", "r10 VRP_DELTA1 primary lookback L=42")

p = ROOT + "/r10_screen/CMUM_CARRY/final_series.npz"; IN["CMUM_series"] = p
d = np.load(p, allow_pickle=True)
add("CMUM", d["TS"], d["A_last_net"], d["A_last_turn"], "A_last",
    "r10 CMUM_CARRY pre-registered PRIMARY arm; covers 8738/9138 anchors, 0 (flat) elsewhere")
ALT["CMUM_static"] = ("E_static_shortCM", d["TS"],
                      -(d["D_static_longCM_gross"]) - d["D_static_longCM_cost"], d["D_static_longCM_turn"])
p2 = ROOT + "/r10_screen/CMUM_CARRY/best_series.npz"; IN["CMUM_best"] = p2
db = np.load(p2, allow_pickle=True)
ALT["CMUM_best"] = (str(db["tag"]), db["TS"], db["net"], db["turn"])

# --- SLOW: rebuild COMBO_G = book-layer equal-gross mean of the 13 arms (NOT PWR_COMBO_S)
SIGN = {"A_QVS1H":"__m","A_REV1H":"__m","A_TBF1H":"__m","A_VOL1H":"__p","B_REV12H":"__m",
        "B_TBF12H":"__p","C_TBF3D":"__p","C_TBF7D":"__p","C_TBF14D":"__p","C_TBF30D":"__p",
        "D_FCHG12H":"__m","D_FCHG3D":"__m","D_FSLOPE":"__p"}
Q = ["A_QVS1H","A_REV1H","A_TBF1H","A_VOL1H","B_REV12H","B_TBF12H","C_TBF3D","C_TBF7D",
     "C_TBF14D","C_TBF30D","D_FCHG12H","D_FCHG3D","D_FSLOPE"]
ARMS = {}; armsha = {}
for f in Q:
    pp = SCR + "/slowarms/PWR_%s%s.npz" % (f, SIGN[f]); IN["SLOW_"+f] = pp
    zz = np.load(pp, allow_pickle=True); assert [str(c) for c in zz["cols"]] == cols, f
    A = np.asarray(zz["rec"] if "rec" in zz.files else zz["d30_n2_c42_rec"], float)
    assert np.array_equal(np.round(A[:, ix["ts"]]).astype(np.int64), ts_all), f
    ARMS[f] = ser(A); armsha[f] = sha(pp)[:16]
CG = {k: np.mean([ARMS[f][k] for f in Q], axis=0) for k in ("g","pnl","cost","carry","turn")}
gateSLOW = {"rebuilt_mean_g": round(float(CG["g"].mean()), 4), "archived_mean_g": -0.2716,
            "rebuilt_ann_sharpe": round(ann(CG["g"]), 4), "archived_ann_sharpe": -1.5666,
            "rebuilt_turnover": round(float(CG["turn"].mean()), 5), "archived_turnover": 0.05911,
            "rebuilt_cost_ex": round(float(CG["cost"].mean()), 4), "archived_cost_ex": 0.6375,
            "arm_sha16": armsha,
            "arm_sha16_matches_screen_receipt": True}
gateSLOW["PASS"] = (abs(gateSLOW["rebuilt_mean_g"]+0.2716) <= 5e-4 and
                    abs(gateSLOW["rebuilt_ann_sharpe"]+1.5666) <= 5e-3)
R["GATE_SLOW_rebuild_COMBO_G"] = gateSLOW
print("GATE SLOW COMBO_G rebuilt mean_g %+.4f (archived -0.2716)  SR %+.4f (archived -1.5666)  PASS=%s"
      % (gateSLOW["rebuilt_mean_g"], gateSLOW["rebuilt_ann_sharpe"], gateSLOW["PASS"]))
assert gateSLOW["PASS"]
add("SLOW", TS, CG["g"], CG["turn"], "COMBO_G = book-layer equal-gross mean of 13 rho-selected arms",
    "r10 SLOW_CLOCK pre-registered candidate (zero arm-pick freedom)")
ALT["SLOW_best"] = ("C_TBF3D__p (screen-declared CONTAMINATED full-sample ceiling)", TS,
                    ARMS["C_TBF3D"]["g"], ARMS["C_TBF3D"]["turn"])

p = SCR + "/coint_main_series.npz"; IN["COINT_series"] = p
d = np.load(p, allow_pickle=True)
add("COINT", d["ts"], d["g_alloc"], d["turn"], "MAIN, per unit ALLOCATED gross",
    "r10 COINT_PAIR main arm; mean utilisation of allocated gross 0.335")

p = OUT + "/series/REV_SHORT_rebuilt.npz"; IN["REVS_series"] = p
d = np.load(p, allow_pickle=True)
add("REVS", d["ts"], d["RAW_jump_net"], d["RAW_jump_turn"], "RAW_jump",
    "r9 REV_SHORT pre-declared PRIMARY arm; rebuilt this session, gated in S1 receipt")
ALT["REVS_best"] = ("EMA_a0.50", d["ts"], d["EMA_a0.50_net"], d["EMA_a0.50_turn"])

for k, (arm, ts_, net_, tu_) in ALT.items():
    add(k, ts_, net_, tu_, arm, "alternative arm, used ONLY for the selection-premium ladder")
R["inputs"] = {k: {"path": v, "sha256": sha(v)} for k, v in IN.items()}
R["books"] = {k: META[k] for k in META}

# ------------------------------------------------------------------ bootstrap
order = np.argsort(inv, kind="stable")
st = np.searchsorted(inv[order], np.arange(nd)); en = np.append(st[1:], len(order))
rng = np.random.default_rng([20260905, 1]); picks = rng.integers(0, nd, size=(B, nd))
BOOT = [np.concatenate([order[st[j]:en[j]] for j in picks[b]]) for b in range(B)]
def ci(v):
    v = np.asarray(v); v = v[np.isfinite(v)]
    return [round(float(np.percentile(v, 2.5)), 4), round(float(np.percentile(v, 97.5)), 4)]
def bstat(x, f): return np.array([f(x[ii]) for ii in BOOT])
SRB = lambda z: np.mean(z)/np.std(z, ddof=1)*np.sqrt(APY)

# ------------------------------------------------------------------ per-book table
def describe(g, turn):
    wd, wdd = worstday(g)
    return {"mean_g_bps": round(float(g.mean()), 4), "mean_g_CI95": ci(bstat(g, np.mean)),
            "ann_sharpe": round(ann(g), 4), "ann_sharpe_CI95": ci(bstat(g, SRB)),
            "SE_ann_sharpe": round(SE_SR, 4), "sd_per_anchor_bps": round(float(np.std(g, ddof=1)), 4),
            "turnover_per_anchor": round(float(turn.mean()), 5),
            "maxDD_bps_of_gross": round(mdd(g), 1),
            "worst_UTC_day_bps": round(wd, 1), "worst_UTC_day": wdd,
            "NAV_pct_per_yr_at_2x_gross": round(float(g.mean())*APY*2.0/100.0, 2)}
PRIMARY = ["A0","TSMOM","VRP","CMUM","SLOW","COINT","REVS"]
TBL = {k: describe(BOOKS[k], TURN[k]) for k in BOOKS}
R["per_book"] = TBL
print("\n%-12s %9s %24s %9s %8s %9s %9s %10s %12s" % ("book","mean_g","CI95","SR","sd","turn","maxDD","worstday","arm"))
for k in PRIMARY + [x for x in BOOKS if x not in PRIMARY]:
    t_ = TBL[k]
    print("%-12s %+9.4f [%+9.4f,%+9.4f] %+9.4f %8.2f %9.5f %9.1f %+10.1f  %s"
          % (k, t_["mean_g_bps"], t_["mean_g_CI95"][0], t_["mean_g_CI95"][1], t_["ann_sharpe"],
             t_["sd_per_anchor_bps"], t_["turnover_per_anchor"], t_["maxDD_bps_of_gross"],
             t_["worst_UTC_day_bps"], META[k]["arm"]), flush=True)

# ------------------------------------------------------------------ correlation matrix
NM = PRIMARY
G = np.column_stack([BOOKS[k] for k in NM]); K = len(NM)
P = np.corrcoef(G.T); S = np.eye(K)
for i in range(K):
    for j in range(i+1, K):
        S[i, j] = S[j, i] = spearmanr(G[:, i], G[:, j]).statistic
BS = np.array([np.corrcoef(G[ii].T)[np.triu_indices(K, 1)] for ii in BOOT])
tri = list(zip(*np.triu_indices(K, 1)))
R["corr_pearson"] = {"names": NM, "M": [[round(float(P[i,j]),4) for j in range(K)] for i in range(K)]}
R["corr_spearman"] = {"names": NM, "M": [[round(float(S[i,j]),4) for j in range(K)] for i in range(K)]}
R["corr_pairs_CI95"] = {"%s~%s" % (NM[i], NM[j]): {"pearson": round(float(P[i,j]),4),
                        "CI95": ci(BS[:, q]), "spearman": round(float(S[i,j]),4)}
                        for q, (i, j) in enumerate(tri)}
print("\nPEARSON (recomputed from the series)\n%-8s" % "" + " ".join("%8s" % x for x in NM))
for i in range(K):
    print("%-8s" % NM[i] + " ".join("%+8.4f" % P[i, j] for j in range(K)), flush=True)

thr = np.percentile(BOOKS["A0"], 20.0); low = BOOKS["A0"] <= thr
R["A0_bottom_quintile"] = {"threshold_g_bps": round(float(thr), 4), "n": int(low.sum()),
                           "A0_mean_there_bps": round(float(BOOKS["A0"][low].mean()), 4)}
R["conditional_in_A0_loss_cells"] = {
    k: {"rho_uncond": round(float(np.corrcoef(BOOKS[k], BOOKS["A0"])[0,1]), 4),
        "rho_in_bottom_quintile": round(float(np.corrcoef(BOOKS[k][low], BOOKS["A0"][low])[0,1]), 4),
        "cand_mean_g_there_bps": round(float(BOOKS[k][low].mean()), 4),
        "cand_mean_g_there_CI95": ci(np.array([BOOKS[k][ii][BOOKS["A0"][ii] <= thr].mean() for ii in BOOT]))}
    for k in NM[1:]}

# ------------------------------------------------------------------ allocation engine
def alloc_stats(keys, c, tag, do_boot=True):
    Gk = np.column_stack([BOOKS[k] for k in keys]); Tk = np.column_stack([TURN[k] for k in keys])
    g = Gk @ c; turn = float((Tk @ c).mean())
    Ck = np.cov(Gk.T, ddof=1) if len(keys) > 1 else np.array([[np.var(Gk[:,0], ddof=1)]])
    rc = c*(Ck @ c); rc = rc/rc.sum() if rc.sum() != 0 else rc
    wd, wdd = worstday(g); gA = BOOKS["A0"]
    srb = bstat(g, SRB) if do_boot else np.array([np.nan])
    o = {"tag": tag, "books": list(keys), "gross_share": [round(float(x), 5) for x in c],
         "risk_share": [round(float(x), 5) for x in rc],
         "mean_g_bps": round(float(g.mean()), 4),
         "mean_g_CI95": ci(bstat(g, np.mean)) if do_boot else None,
         "ann_sharpe": round(ann(g), 4), "ann_sharpe_CI95": ci(srb) if do_boot else None,
         "SE_ann_sharpe": round(SE_SR, 4),
         "sd_per_anchor_bps": round(float(np.std(g, ddof=1)), 4),
         "turnover_per_anchor": round(turn, 5),
         "maxDD_bps_of_gross": round(mdd(g), 1),
         "worst_UTC_day_bps": round(wd, 1), "worst_UTC_day": wdd,
         "NAV_pct_per_yr_at_2x_gross": round(float(g.mean())*APY*2.0/100.0, 2),
         "vs_A0_alone": {"d_mean_g": round(float(g.mean()-gA.mean()), 4),
                         "d_mean_g_paired_CI95": ci(bstat(g-gA, np.mean)) if do_boot else None,
                         "d_ann_sharpe": round(ann(g)-ann(gA), 4),
                         "d_ann_sharpe_in_SE": round((ann(g)-ann(gA))/SE_SR, 3),
                         "d_maxDD_bps": round(mdd(g)-mdd(gA), 1),
                         "d_worst_UTC_day_bps": round(wd-worstday(gA)[0], 1),
                         "d_turnover": round(turn-float(TURN["A0"].mean()), 5)},
         "distance_to_goal": {"target_point_estimate": TARGET,
                              "gap_sharpe": round(TARGET-ann(g), 4),
                              "gap_in_SE": round((TARGET-ann(g))/SE_SR, 2),
                              "CI95_lower_bound": ci(srb)[0] if do_boot else None,
                              "CI95_lower_clears_3.0": bool(do_boot and ci(srb)[0] > 3.0)}}
    if do_boot:
        print("%-44s SR %+7.4f [%+6.3f,%+6.3f]  g %+7.4f  turn %7.5f  mDD %8.1f  wday %+8.1f  gapSE %6.2f"
              % (tag, o["ann_sharpe"], o["ann_sharpe_CI95"][0], o["ann_sharpe_CI95"][1],
                 o["mean_g_bps"], turn, o["maxDD_bps_of_gross"], o["worst_UTC_day_bps"],
                 o["distance_to_goal"]["gap_in_SE"]), flush=True)
    return o, g
def equalrisk(keys):
    sd = np.array([np.std(BOOKS[k], ddof=1) for k in keys]); w = 1.0/sd; return w/w.sum()
def maxsharpe(keys, Gm=None):
    Gk = Gm if Gm is not None else np.column_stack([BOOKS[k] for k in keys])
    m_ = Gk.mean(0); C_ = np.cov(Gk.T, ddof=1); k = len(keys)
    def neg(c):
        v = float(c @ C_ @ c); return 1e6 if v <= 0 else -float((c @ m_)/np.sqrt(v))
    best = None
    for s0 in [np.ones(k)/k] + [np.eye(k)[i]*0.9 + 0.1/k for i in range(k)]:
        try:
            r_ = minimize(neg, s0, method="SLSQP", bounds=[(0,1)]*k,
                          constraints=[{"type":"eq","fun":lambda c: c.sum()-1.0}],
                          options={"maxiter":800,"ftol":1e-12})
            if r_.success and (best is None or r_.fun < best.fun): best = r_
        except Exception: pass
    c = np.clip(best.x, 0, 1); return c/c.sum()

POOLS = {
 "A0_alone":               ["A0"],
 "POOL_A_all_primary":     ["A0","TSMOM","VRP","CMUM","SLOW","COINT","REVS"],
 "POOL_B_survivors":       ["A0","TSMOM","VRP"],
 "POOL_C_survivors_bestarm":["A0","TSMOM_best","VRP","CMUM_best","SLOW_best"],
 "POOL_A2_all_zeroselect": ["A0","TSMOM","VRP","CMUM_static","SLOW","COINT","REVS"],
}
R["pool_definitions"] = {
 "POOL_A_all_primary": "EVERY candidate that reached a book-layer screen this round, each at its OWN pre-registered primary arm. No arm chosen by me. 6 candidates + A0.",
 "POOL_B_survivors": "mechanical filter on POOL_A: keep a candidate iff its standalone net mean g point estimate is > 0. Nothing else. -> TSMOM, VRP.",
 "POOL_C_survivors_bestarm": "maximum-selection pool: for each candidate whose BEST reported arm has a positive net point estimate, take that best arm. Includes SLOW's own screen-declared CONTAMINATED ceiling. This pool is NOT a result; it is the upper rail of the selection ladder.",
 "POOL_A2_all_zeroselect": "POOL_A with CMUM at its screen-declared ZERO-SELECTION arm (E_static_shortCM) instead of its prereg primary, to show how much of POOL_A's equal-risk collapse is that one arm.",
}
print("\n--- ALLOCATIONS (gross shares sum to 1; total gross fixed at 2.0x NAV) ---", flush=True)
ALLOC = {}
for pn, keys in POOLS.items():
    ALLOC[pn] = {}
    if len(keys) == 1:
        ALLOC[pn]["single"], _ = alloc_stats(keys, np.array([1.0]), pn); continue
    ALLOC[pn]["equal_risk"], _ = alloc_stats(keys, equalrisk(keys), pn + " | equal-risk")
    c = maxsharpe(keys)
    o, gopt = alloc_stats(keys, c, pn + " | max-Sharpe IN-SAMPLE (long-only)")
    o["WARNING"] = ("FITTED IN SAMPLE on the same 9138 anchors it is scored on. "
                    "Upper bound only; see optimism_penalty.")
    ALLOC[pn]["max_sharpe_longonly_INSAMPLE"] = o
    for cc in (0.02, 0.05, 0.10, 0.20):
        cv = np.zeros(len(keys)); cv[0] = 1.0-cc; cv[1:] = cc/(len(keys)-1)
        ALLOC[pn]["A0_%.0fpct_rest_equal" % ((1-cc)*100)], _ = alloc_stats(
            keys, cv, pn + " | A0 %.0f%% + rest equal" % ((1-cc)*100))
R["allocations"] = ALLOC
json.dump(R, open(OUT + "/receipts/S3_COMBINE_FINAL.json", "w"), indent=1)
np.savez_compressed(OUT + "/series/books_on_pinned_axis.npz", ts=TS,
                    names=np.array(list(BOOKS.keys())),
                    G=np.column_stack([BOOKS[k] for k in BOOKS]),
                    TU=np.column_stack([TURN[k] for k in BOOKS]))
print("\nwrote", OUT + "/receipts/S3_COMBINE_FINAL.json", flush=True)
