"""r10_combine STEP 2 -- BOOK-LAYER COMBINATION of A0 with every r9/r10 screen candidate.

Each candidate is a SEPARATE BOOK with its OWN gross.  Total gross is held at
2.0x NAV, so an allocation is a vector c over books with c_i >= 0, sum c_i = 1,
and the combined per-unit-gross return is g_comb = sum_i c_i * g_i.  Nothing is
put into A0's w3 seat.

ENV WHITELIST (E-0826-D) = EMPTY SET.
Caliber pin v4 (2026-09-09).  g = net_ex/gross_total, bps per 4h anchor per unit
gross.  n = 9138 (post-warm drop 900, E-0911-A; cap 2026-08-30 20Z, E-0911-D).
Bootstrap: UTC-day block, B=2000, numpy.default_rng([20260905,k]).
"""
import os, sys, json, hashlib, calendar, itertools
ENV_SEEN = sorted(os.environ.keys())
_FORBID = ("LEGS","CAL","WRULE","LOOK","PHI","UMASK_NPZ","UMASK_SCOPE","FSEED","FPRED","COSTB_JSON",
           "MEMBERS_TOPN","FTRIM","SLOW_NPY","W3FIX","FEMAT_NPZ","OUT_TAG","TRADE_TOPN","TILT",
           "KMOD","KMOD_F10","KMOD_L","KMOD_AGREE","KTAIL","SEATF10","SEATNET","FUNDSCALE","REF_SKIP",
           "SLEEVE","CDAMP","LTRIM_TH","FTRIM_TH","RNSM","FTPOS","PANEL","PANEL_IN","EXPORT_PANEL",
           "EMA_STATE_JSON","JUDGE_HC","JUDGE_REQUIRE_W")
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
SE_SR = float(np.sqrt(APY/9138.0))
TARGET = 3.966

R = {"step": "S2_COMBINE", "self_sha256": sha(os.path.abspath(__file__)),
     "env_whitelist": [], "env_seen_at_runtime": ENV_SEEN,
     "numpy": np.__version__, "scipy": __import__("scipy").__version__,
     "python": sys.version.split()[0], "B": B, "SE_ann_sharpe": round(SE_SR, 4),
     "target_point_estimate": TARGET}

SRC = {
 "A0"        : SCR + "/A0_PWR230k_s42.npz",
 "TSMOM"     : SCR + "/tsmom_series.npz",
 "VRP"       : ROOT + "/r10_screen/VRP_DELTA1/series_VRP_DELTA1.npz",
 "CMUM"      : ROOT + "/r10_screen/CMUM_CARRY/final_series.npz",
 "CMUM_best" : ROOT + "/r10_screen/CMUM_CARRY/best_series.npz",
 "SLOW"      : SCR + "/slow_PWR_COMBO_S.npz",
 "SLOW_tbf"  : SCR + "/slow_PWR_C_TBF3D_p.npz",
 "COINT"     : SCR + "/coint_main_series.npz",
 "REVS"      : OUT + "/series/REV_SHORT_rebuilt.npz",
}
R["inputs"] = {k: {"path": p, "sha256": sha(p)} for k, p in SRC.items()}

# ------------------------------------------------------------------ A0 (the axis)
a = np.load(SRC["A0"], allow_pickle=True)
cols = [str(c) for c in a["cols"]]; ci_ = {c: i for i, c in enumerate(cols)}
rec = np.asarray(a["rec"], float)[WARM:]
ts_all = np.round(rec[:, ci_["ts"]]).astype(np.int64)
msk = ts_all <= CUT
TS = ts_all[msk]; rw = rec[msk]
gA0   = rw[:, ci_["net_ex"]] / rw[:, ci_["gross_total"]]
A0turn = rw[:, ci_["turnover"]]
A0pnl  = rw[:, ci_["pnl_ex"]]  / rw[:, ci_["gross_total"]]
A0cost = rw[:, ci_["cost_ex"]] / rw[:, ci_["gross_total"]]
A0carry= rw[:, ci_["carry_ex"]]/ rw[:, ci_["gross_total"]]
n = len(TS); assert n == 9138, n
R["axis"] = {"n": int(n), "t0": TS[0].item(), "t1": TS[-1].item(),
             "span_utc": ["2022-06-30T00:00Z", "2026-08-30T20:00Z"],
             "monotone_4h": bool(np.all(np.diff(TS) == 14400))}

def ann(x):
    s = np.std(x, ddof=1); return float(np.mean(x)/s*np.sqrt(APY)) if s > 0 else float("nan")
def mdd(x):
    c = np.cumsum(x); return float(np.max(np.maximum.accumulate(c) - c))
DAY = TS // 86400
ud, inv = np.unique(DAY, return_inverse=True); nd = len(ud)
def dayagg(x): return np.bincount(inv, weights=x, minlength=nd)
def worstday(x):
    d = dayagg(x); i = int(np.argmin(d)); return float(d[i]), int(ud[i])
def dstr(e): return __import__("time").strftime("%Y-%m-%d", __import__("time").gmtime(int(e)*86400))

# ------------------------------------------------------------------ candidates
def align(ts_src, arr):
    """map a candidate series onto the A0 axis; 0 where the book has no coverage."""
    out = np.zeros(n); cov = np.zeros(n, bool)
    pos = {int(t): i for i, t in enumerate(TS)}
    for j, t in enumerate(ts_src):
        i = pos.get(int(t))
        if i is not None: out[i] = arr[j]; cov[i] = True
    return out, cov

BOOKS = {}; META = {}
def add(name, ts_src, net, turn=None, gross=None, cost=None, note="", arm=""):
    g, cov = align(np.asarray(ts_src), np.asarray(net, float))
    t_, _ = align(np.asarray(ts_src), np.asarray(turn, float)) if turn is not None else (np.zeros(n), None)
    gr, _ = align(np.asarray(ts_src), np.asarray(gross, float)) if gross is not None else (np.full(n, np.nan), None)
    co, _ = align(np.asarray(ts_src), np.asarray(cost, float)) if cost is not None else (np.full(n, np.nan), None)
    BOOKS[name] = g
    META[name] = {"arm": arm, "note": note, "coverage_anchors": int(cov.sum()),
                  "turn": t_, "gross": gr, "cost": co}

add("A0", TS, gA0, A0turn, A0pnl + A0carry, A0cost,
    "live book, PWR_G230k repricing", "d30_n2_c42 dynamic seat")

d = np.load(SRC["TSMOM"], allow_pickle=True)
add("TSMOM", d["ts"], d["TSMOM_L42_raw_net"], d["TSMOM_L42_raw_turn"],
    d["TSMOM_L42_raw_pnl"] + d["TSMOM_L42_raw_carry"], d["TSMOM_L42_raw_cost"],
    "r10 TSMOM_DIR declared PRIMARY arm", "TSMOM_L42_raw")
TSMOM_BEST = ("TSMOM_L90_raw", d["ts"], d["TSMOM_L90_raw_net"], d["TSMOM_L90_raw_turn"])

d = np.load(SRC["VRP"], allow_pickle=True)
add("VRP", d["ts"], d["net"], d["turnover"], d["gross"], d["cost"],
    "r10 VRP_DELTA1 primary L=42", "VRP_L42")

d = np.load(SRC["CMUM"], allow_pickle=True)
cm_net_prim = d["A_last_net"]
# E_static_shortCM = -(D_static_longCM book) : weights flip sign, |dw| (hence cost) unchanged
cm_static_net = -(d["D_static_longCM_gross"]) - d["D_static_longCM_cost"]
add("CMUM", d["TS"], cm_net_prim, d["A_last_turn"], d["A_last_gross"], d["A_last_cost"],
    "r10 CMUM_CARRY declared PRIMARY (prereg) arm; 8738/9138 covered, 0 elsewhere", "A_last")
CMUM_STATIC = ("E_static_shortCM", d["TS"], cm_static_net, d["D_static_longCM_turn"])
db = np.load(SRC["CMUM_best"], allow_pickle=True)
CMUM_BEST = (str(db["tag"]), db["TS"], db["net"], db["turn"])

def rec_g(path):
    z = np.load(path, allow_pickle=True)
    cc = [str(x) for x in z["cols"]]; k = {c: i for i, c in enumerate(cc)}
    r = np.asarray(z["rec"], float)[WARM:]
    t = np.round(r[:, k["ts"]]).astype(np.int64); m = t <= CUT
    r = r[m]; t = t[m]
    return t, r[:, k["net_ex"]]/r[:, k["gross_total"]], r[:, k["turnover"]], \
           (r[:, k["pnl_ex"]]+r[:, k["carry_ex"]])/r[:, k["gross_total"]], r[:, k["cost_ex"]]/r[:, k["gross_total"]]
t, g, tu, gr, co = rec_g(SRC["SLOW"])
add("SLOW", t, g, tu, gr, co, "r10 SLOW_CLOCK pre-registered rho-only equal-gross combination of all 13 arms", "PWR_COMBO_S")
SLOW_TBF = ("C_TBF3D__p (screen-declared CONTAMINATED ceiling)",) + rec_g(SRC["SLOW_tbf"])[:3]

d = np.load(SRC["COINT"], allow_pickle=True)
add("COINT", d["ts"], d["g_alloc"], d["turn"], d["P"] + d["C"], d["K"],
    "r10 COINT_PAIR main arm, per unit ALLOCATED gross (util 0.335)", "MAIN g_alloc")

d = np.load(SRC["REVS"], allow_pickle=True)
add("REVS", d["ts"], d["RAW_jump_net"], d["RAW_jump_turn"], d["RAW_jump_gross"], d["RAW_jump_cost"],
    "r9 REV_SHORT declared PRIMARY arm, rebuilt this session (GATE in S1 receipt)", "RAW_jump")

NAMES = list(BOOKS.keys())
G = np.column_stack([BOOKS[k] for k in NAMES])
TU = np.column_stack([META[k]["turn"] for k in NAMES])
R["books"] = {k: {"arm": META[k]["arm"], "note": META[k]["note"],
                  "coverage_anchors": META[k]["coverage_anchors"]} for k in NAMES}

# ------------------------------------------------------------------ bootstrap machinery
order = np.argsort(inv, kind="stable")
st = np.searchsorted(inv[order], np.arange(nd)); en = np.append(st[1:], len(order))
BOOT_IDX = []
rng = np.random.default_rng([20260905, 1])
picks = rng.integers(0, nd, size=(B, nd))
for b in range(B):
    BOOT_IDX.append(np.concatenate([order[st[j]:en[j]] for j in picks[b]]))
def ci(v):
    v = np.asarray(v); v = v[np.isfinite(v)]
    return [round(float(np.percentile(v, 2.5)), 4), round(float(np.percentile(v, 97.5)), 4)]
def boot_stat(x, f):
    return np.array([f(x[ii]) for ii in BOOT_IDX])

# ------------------------------------------------------------------ per-book table
def describe(name, g, turn):
    wd, wdd = worstday(g)
    out = {"mean_g_bps": round(float(g.mean()), 4),
           "mean_g_CI95": ci(boot_stat(g, np.mean)),
           "ann_sharpe": round(ann(g), 4),
           "ann_sharpe_CI95": ci(boot_stat(g, lambda z: np.mean(z)/np.std(z, ddof=1)*np.sqrt(APY))),
           "sd_per_anchor_bps": round(float(np.std(g, ddof=1)), 4),
           "turnover_per_anchor": round(float(np.mean(turn)), 5),
           "maxDD_bps_of_gross": round(mdd(g), 2),
           "worst_UTC_day_bps": round(wd, 2), "worst_UTC_day": dstr(wdd),
           "NAV_pct_per_yr_at_2x": round(float(g.mean())*APY*2.0/100.0, 2)}
    return out
TBL = {k: describe(k, BOOKS[k], META[k]["turn"]) for k in NAMES}
R["per_book"] = TBL
print("%-7s %9s %22s %8s %9s %9s %9s %10s" % ("book","mean_g","CI95","SR","sd","turn","maxDD","worstday"))
for k in NAMES:
    t_ = TBL[k]
    print("%-7s %+9.4f [%+8.4f,%+8.4f] %+8.4f %9.3f %9.5f %9.1f %+10.1f"
          % (k, t_["mean_g_bps"], t_["mean_g_CI95"][0], t_["mean_g_CI95"][1], t_["ann_sharpe"],
             t_["sd_per_anchor_bps"], t_["turnover_per_anchor"], t_["maxDD_bps_of_gross"],
             t_["worst_UTC_day_bps"]), flush=True)

# ------------------------------------------------------------------ correlation matrix (RECOMPUTED)
K = len(NAMES)
P = np.corrcoef(G.T)
S = np.zeros((K, K))
for i in range(K):
    for j in range(K):
        S[i, j] = 1.0 if i == j else spearmanr(G[:, i], G[:, j]).statistic
RHO_CI = {}
BS = np.array([np.corrcoef(G[ii].T)[np.triu_indices(K, 1)] for ii in BOOT_IDX])
tri = list(zip(*np.triu_indices(K, 1)))
for q, (i, j) in enumerate(tri):
    RHO_CI["%s~%s" % (NAMES[i], NAMES[j])] = {"pearson": round(float(P[i, j]), 4),
                                              "CI95": ci(BS[:, q]),
                                              "spearman": round(float(S[i, j]), 4)}
R["corr_matrix_pearson"] = {"names": NAMES, "M": [[round(float(P[i, j]), 4) for j in range(K)] for i in range(K)]}
R["corr_matrix_spearman"] = {"names": NAMES, "M": [[round(float(S[i, j]), 4) for j in range(K)] for i in range(K)]}
R["corr_pairs_CI95"] = RHO_CI
print("\nPEARSON  " + " ".join("%8s" % x for x in NAMES))
for i in range(K):
    print("%-8s " % NAMES[i] + " ".join("%+8.4f" % P[i, j] for j in range(K)), flush=True)

# conditional on A0 bottom quintile
thr = np.percentile(gA0, 20.0); sel = gA0 <= thr
R["A0_bottom_quintile"] = {"threshold_g": round(float(thr), 4), "n": int(sel.sum()),
                           "A0_mean_there": round(float(gA0[sel].mean()), 4)}
CONDR = {}
for k in NAMES[1:]:
    x = BOOKS[k]
    CONDR[k] = {"rho_uncond": round(float(np.corrcoef(x, gA0)[0, 1]), 4),
                "rho_in_A0_bottom_quintile": round(float(np.corrcoef(x[sel], gA0[sel])[0, 1]), 4),
                "cand_mean_g_there_bps": round(float(x[sel].mean()), 4),
                "cand_mean_g_there_CI95": ci(np.array([x[ii][gA0[ii] <= thr].mean() for ii in BOOT_IDX]))}
R["conditional_in_A0_loss_cells"] = CONDR

# ------------------------------------------------------------------ allocation machinery
mu = G.mean(0); COV = np.cov(G.T, ddof=1); sd = np.sqrt(np.diag(COV))
def sr_of(c): 
    v = float(c @ COV @ c)
    return float((c @ mu)/np.sqrt(v)*np.sqrt(APY)) if v > 0 else float("nan")
def maxsharpe(idx, longonly=True):
    m_ = mu[idx]; C_ = COV[np.ix_(idx, idx)]
    k = len(idx)
    def neg(c):
        v = float(c @ C_ @ c)
        return 1e6 if v <= 0 else -float((c @ m_)/np.sqrt(v))
    best = None
    starts = [np.ones(k)/k] + [np.eye(k)[i]*0.9 + 0.1/k for i in range(k)]
    bnds = [(0, 1)]*k if longonly else [(-1, 1)]*k
    for s0 in starts:
        try:
            r_ = minimize(neg, s0, method="SLSQP", bounds=bnds,
                          constraints=[{"type": "eq", "fun": lambda c: c.sum()-1.0}],
                          options={"maxiter": 500, "ftol": 1e-12})
            if r_.success and (best is None or r_.fun < best.fun): best = r_
        except Exception: pass
    c = np.clip(best.x, 0 if longonly else -1, 1); c = c/np.abs(c).sum() if not longonly else c/c.sum()
    return c
def equalrisk(idx):
    w = 1.0/sd[idx]; return w/w.sum()

def report_alloc(tag, idx, c):
    g = G[:, idx] @ c
    turn = float((TU[:, idx] @ c).mean())
    wd, wdd = worstday(g)
    srb = boot_stat(g, lambda z: np.mean(z)/np.std(z, ddof=1)*np.sqrt(APY))
    rc = c*(COV[np.ix_(idx, idx)] @ c); rc = rc/rc.sum()
    out = {"books": [NAMES[i] for i in idx], "gross_share": [round(float(x), 5) for x in c],
           "risk_share": [round(float(x), 5) for x in rc],
           "mean_g_bps": round(float(g.mean()), 4), "mean_g_CI95": ci(boot_stat(g, np.mean)),
           "ann_sharpe": round(ann(g), 4), "ann_sharpe_CI95": ci(srb),
           "SE_ann_sharpe": round(SE_SR, 4),
           "sd_per_anchor_bps": round(float(np.std(g, ddof=1)), 4),
           "turnover_per_anchor": round(turn, 5),
           "maxDD_bps_of_gross": round(mdd(g), 2),
           "worst_UTC_day_bps": round(wd, 2), "worst_UTC_day": dstr(wdd),
           "NAV_pct_per_yr_at_2x": round(float(g.mean())*APY*2.0/100.0, 2),
           "vs_A0": {"d_mean_g": round(float(g.mean()-gA0.mean()), 4),
                     "d_ann_sharpe": round(ann(g)-ann(gA0), 4),
                     "d_ann_sharpe_in_SE": round((ann(g)-ann(gA0))/SE_SR, 3),
                     "d_maxDD": round(mdd(g)-mdd(gA0), 2),
                     "d_worst_day": round(wd-worstday(gA0)[0], 2),
                     "d_turnover": round(turn-float(A0turn.mean()), 5)},
           "distance_to_target": {"target_point_estimate": TARGET,
                                  "gap_sharpe": round(TARGET-ann(g), 4),
                                  "gap_in_SE": round((TARGET-ann(g))/SE_SR, 3),
                                  "CI95_lower": ci(srb)[0],
                                  "CI95_lower_clears_3.0": bool(ci(srb)[0] > 3.0)},
           "paired_delta_vs_A0_CI95": ci(boot_stat(g-gA0, np.mean))}
    print("%-34s SR %+7.4f [%+6.3f,%+6.3f]  g %+7.4f  turn %7.5f  mDD %8.1f  wday %+8.1f  gapSE %6.2f"
          % (tag, out["ann_sharpe"], out["ann_sharpe_CI95"][0], out["ann_sharpe_CI95"][1],
             out["mean_g_bps"], turn, out["maxDD_bps_of_gross"], out["worst_UTC_day_bps"],
             out["distance_to_target"]["gap_in_SE"]), flush=True)
    return out, g

IX = {k: i for i, k in enumerate(NAMES)}
POOLS = {
 "A0_alone":            ["A0"],
 "POOL_A_all_primary":  ["A0","TSMOM","VRP","CMUM","SLOW","COINT","REVS"],
 "POOL_B_survivors":    ["A0","TSMOM","VRP"],
}
R["pool_definitions"] = {
 "POOL_A_all_primary": "every candidate that reached a book-layer screen, each at its OWN pre-registered primary arm. No arm chosen by me.",
 "POOL_B_survivors": "mechanical rule applied to POOL_A: keep the candidate iff its standalone net mean g point estimate > 0 on the pinned axis. No other filter.",
}
print("\n--- allocations ---", flush=True)
ALLOC = {}
for pname, keys in POOLS.items():
    idx = [IX[k] for k in keys]
    ALLOC[pname] = {}
    if len(idx) == 1:
        ALLOC[pname]["single"], _ = report_alloc(pname+" / A0 only", idx, np.array([1.0]))
        continue
    ALLOC[pname]["equal_risk"], _ = report_alloc(pname+" / equal-risk", idx, equalrisk(idx))
    c = maxsharpe(idx, True)
    ALLOC[pname]["max_sharpe_longonly_INSAMPLE"], gopt = report_alloc(pname+" / max-Sharpe (IS, long-only)", idx, c)
    ALLOC[pname]["max_sharpe_longonly_INSAMPLE"]["WARNING"] = "FITTED IN SAMPLE on the same 9138 anchors it is scored on. Upper bound, not an expectation."
    for cc_ in (0.02, 0.05, 0.10, 0.20):
        cv = np.zeros(len(idx)); cv[0] = 1.0-cc_
        cv[1:] = cc_/max(1, len(idx)-1)
        ALLOC[pname]["fixed_c%.2f_split_equally" % cc_], _ = report_alloc(
            pname+" / A0 %.0f%% + rest equal" % ((1-cc_)*100), idx, cv)
R["allocations"] = ALLOC
json.dump(R, open(OUT + "/receipts/S2_COMBINE.json", "w"), indent=1)
np.savez_compressed(OUT + "/series/books_on_pinned_axis.npz", ts=TS,
                    names=np.array(NAMES), G=G, TU=TU)
print("\nwrote", OUT + "/receipts/S2_COMBINE.json", flush=True)
