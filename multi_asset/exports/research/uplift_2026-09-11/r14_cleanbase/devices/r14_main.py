"""r14 MAIN device — rebuild the baseline without the dead-leg prefix and measure what it changes.

STEP 1 reproduce the defect (source instrument from pod2 + archived-arm instrument here)
STEP 2 define CLEAN = king-live anchors; report the baseline on it
STEP 3 rho to baseline on FULL vs CLEAN for every archived candidate, with block-bootstrap CIs
STEP 4 the Amihud sleeve's +0.2458 delta-Sharpe, recomputed on CLEAN
STEP 5 the distribution of rho on both samples -> does "they were all re-weightings" survive

PREREG 89ba6e7d87d79866d78f7a95400ee13b21b7d0d511dfc82f6ce7b509ca956fe7 (asserted below).
Caliber pin v4.  g = net_ex/gross_total, bps / 4h anchor / unit gross.
W_ALPHA = rec[900:] then ts <= 2026-08-30 20Z => n 9138.  W_TAIL = no warm drop, same ceiling => 10038.
ENV WHITELIST (E-0826-D) = EMPTY SET, asserted in-file.
LIVE ZERO-TOUCH: no path under ~/dl_quant_live or ~/wide_shadow is opened.
"""
import os, sys, json, hashlib, calendar, time
_FORBID = ("LEGS","CAL","WRULE","LOOK","PHI","UMASK_NPZ","UMASK_SCOPE","FSEED","FPRED","COSTB_JSON",
           "MEMBERS_TOPN","FTRIM","SLOW_NPY","W3FIX","FEMAT_NPZ","OUT_TAG","TRADE_TOPN","TILT",
           "TILT_TAU","TILT_K","KMOD","KMOD_F10","KMOD_L","KMOD_AGREE","KTAIL","SEATF10","SEATNET",
           "FUNDSCALE","REF_SKIP","SLEEVE","CDAMP","LTRIM_TH","FTRIM_TH","RNSM","FTPOS","PANEL",
           "PANEL_IN","EXPORT_PANEL","EMA_STATE_JSON","JUDGE_HC","JUDGE_REQUIRE_W")
_v = [k for k in _FORBID if k in os.environ]
assert not _v, "E-0826-D env violation: %r" % _v
ENV_SEEN = sorted(os.environ.keys()); ENV_WHITELIST = []
assert ENV_WHITELIST == []
import numpy as np
from scipy.stats import spearmanr

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def T(*a): return calendar.timegm(a + (0,)*(6-len(a)))

ROOT = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11"
OUT  = ROOT + "/r14_cleanbase"
SCR  = "/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/scratchpad/r10c"
PREREG = OUT + "/PREREG_r14_clean_baseline_2026-09-12.md"
PREREG_SHA = "89ba6e7d87d79866d78f7a95400ee13b21b7d0d511dfc82f6ce7b509ca956fe7"
assert sha(PREREG) == PREREG_SHA, "PREREG sha mismatch -> device refuses to run"
AMD1 = OUT + "/PREREG_AMENDMENT_1_2026-09-12.md"
AMD1_SHA = "e1caddf028b5148403da28527b6cb27ab152652d413c5f8bdf4bd04e4b74012f"
assert sha(AMD1) == AMD1_SHA, "AMENDMENT 1 sha mismatch -> device refuses to run"
# LIVE ZERO-TOUCH is enforced structurally: every path this device opens is registered in IN and
# printed in the receipt; none of them is under the live producer or executor trees.

CUT = T(2026, 8, 30, 20); WARM = 900; B = 2000; APY = 2190.0
DEV_SHA = "b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650"
R = {"step": "R14_MAIN", "self_sha256": sha(os.path.abspath(__file__)),
     "prereg_sha256": PREREG_SHA, "prereg_amendment_1_sha256": AMD1_SHA, "env_whitelist": ENV_WHITELIST, "env_seen_at_runtime": ENV_SEEN,
     "numpy": np.__version__, "scipy": __import__("scipy").__version__,
     "python": sys.version.split()[0], "B": B, "APY": APY,
     "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
IN = {}
def reg(tag, p):
    IN[tag] = {"path": p, "sha256": sha(p)}; return p

# ===================================================================== STEP 1a: G1 source gate
DEVP = reg("w10_sleeve_device", ROOT + "/trackA/w10_sleeve.py")
src = open(DEVP).read().split("\n")
L219 = src[218]; L267 = src[266]
G1 = {"device_sha256": sha(DEVP), "device_sha_matches_pin": sha(DEVP) == DEV_SHA,
      "L219": L219.strip(), "L267": L267.strip(),
      "L219_has_nan_to_num_on_king": 'np.nan_to_num(xz(sc["king"]))' in L219,
      "L267_has_nan_to_num_on_f10": 'np.nan_to_num(xz(F10P[i, m]))' in L267,
      "xz_gate_lines_138_141": [src[i].strip() for i in (137, 138, 139, 140)]}
G1["PASS"] = bool(G1["device_sha_matches_pin"] and G1["L219_has_nan_to_num_on_king"] and G1["L267_has_nan_to_num_on_f10"])
R["GATE_G1_source"] = G1
print("G1 device sha match=%s  L219=%s  L267=%s  PASS=%s" % (G1["device_sha_matches_pin"],
      G1["L219_has_nan_to_num_on_king"], G1["L267_has_nan_to_num_on_f10"], G1["PASS"]))
assert G1["PASS"], "G1 FAIL"

# ===================================================================== STEP 1b: axis + A0
A0P = reg("A0_PWR230k_s42", ROOT + "/r10_screen/CMUM_CARRY/pin/A0_PWR230k_s42.npz")
a = np.load(A0P, allow_pickle=True)
cols = [str(c) for c in a["cols"]]; ix = {c: i for i, c in enumerate(cols)}
rec = np.asarray(a["rec"], float)
ts_all = np.round(rec[:, ix["ts"]]).astype(np.int64)
ALPHA = np.arange(len(ts_all))[WARM:]; ALPHA = ALPHA[ts_all[ALPHA] <= CUT]
TAIL  = np.arange(len(ts_all)); TAIL = TAIL[ts_all[TAIL] <= CUT]
TS = ts_all[ALPHA]; n = len(TS)
TS_T = ts_all[TAIL]; nT = len(TS_T)
gA0   = (rec[:, ix["net_ex"]] / rec[:, ix["gross_total"]])[ALPHA]
gA0_T = (rec[:, ix["net_ex"]] / rec[:, ix["gross_total"]])[TAIL]
turn_raw   = rec[:, ix["turnover"]][ALPHA]
turn_match = (rec[:, ix["turnover"]] / rec[:, ix["gross_total"]])[ALPHA]
legk = rec[:, ix["leg_king"]][ALPHA]; w3k = rec[:, ix["w3_king"]][ALPHA]
gross = rec[:, ix["gross_total"]][ALPHA]
ident = np.max(np.abs(rec[:, ix["net_ex"]] - (rec[:, ix["pnl_ex"]] - rec[:, ix["carry_ex"]] - rec[:, ix["cost_ex"]])))
G5 = {"n_W_ALPHA": int(n), "n_W_TAIL": int(nT), "monotone_4h": bool(np.all(np.diff(TS) == 14400)),
      "span": [time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(TS[0]))),
               time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(TS[-1])))],
      "identity_net_ex_maxabs": float(ident), "arm_config": json.loads(str(a["config_json"]))}
G5["PASS"] = bool(n == 9138 and nT == 10038 and G5["monotone_4h"] and ident < 1e-9)
R["GATE_G5_axis"] = G5
print("G5 n_ALPHA=%d n_TAIL=%d monotone=%s identity_maxabs=%.3e PASS=%s" % (n, nT, G5["monotone_4h"], ident, G5["PASS"]))
assert G5["PASS"], "G5 FAIL"

def ann(x, s=None):
    x = np.asarray(x); sd = np.std(x, ddof=1)
    return float(np.mean(x)/sd*np.sqrt(APY)) if sd > 0 else float("nan")
def mdd(x):
    c = np.concatenate([[0.0], np.cumsum(x)]); return float(np.max(np.maximum.accumulate(c) - c))
def worstday(x, ts):
    d = ts // 86400; ud_, inv_ = np.unique(d, return_inverse=True)
    s = np.bincount(inv_, weights=x, minlength=len(ud_)); i = int(np.argmin(s))
    return float(s[i]), time.strftime("%Y-%m-%d", time.gmtime(int(ud_[i])*86400))
G6 = {"mean_g": float(gA0.mean()), "sharpe": ann(gA0),
      "expect_mean_g": 0.6341957, "expect_sharpe": 1.2912234}
G6["PASS"] = bool(abs(G6["mean_g"]-0.6341957) < 5e-6 and abs(G6["sharpe"]-1.2912234) < 5e-5)
R["GATE_G6_A0_level"] = G6
print("G6 A0 mean_g %.7f (expect 0.6341957)  SR %.7f (expect 1.2912234)  PASS=%s" % (G6["mean_g"], G6["sharpe"], G6["PASS"]))
assert G6["PASS"], "G6 FAIL"

# ===================================================================== STEP 1c: dead masks
DM = reg("r14_deadmask_from_pod2", OUT + "/receipts/r14_deadmask.npz")
d = np.load(DM)
pos = {int(t): i for i, t in enumerate(d["ts"])}
sel = np.array([pos[int(t)] for t in TS])
assert np.array_equal(d["ts"][sel], TS)
nk3 = d["n_finite_king_v3"][sel]; nk4 = d["n_finite_king_v4"][sel]; nf10 = d["n_finite_f10"][sel]
KING_DEAD = nk3 < 10; F10_DEAD = nf10 < 10; BOTH_DEAD = KING_DEAD & F10_DEAD
CLEAN = ~KING_DEAD
selT = np.array([pos[int(t)] for t in TS_T])
KING_DEAD_T = d["n_finite_king_v3"][selT] < 10; CLEAN_T = ~KING_DEAD_T

def rng_of(m, ts):
    if m.sum() == 0: return [None, None]
    return [time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(ts[m][0]))),
            time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(ts[m][-1])))]
def contiguous(m):
    idxs = np.nonzero(m)[0]
    return bool(len(idxs) == 0 or np.all(np.diff(idxs) == 1))
G3 = {"king_dead": int(KING_DEAD.sum()), "king_dead_pct": round(100*KING_DEAD.mean(), 4),
      "f10_dead": int(F10_DEAD.sum()), "f10_dead_pct": round(100*F10_DEAD.mean(), 4),
      "both_dead": int(BOTH_DEAD.sum()), "clean": int(CLEAN.sum()),
      "king_dead_range": rng_of(KING_DEAD, TS), "f10_dead_range": rng_of(F10_DEAD, TS),
      "clean_range": rng_of(CLEAN, TS),
      "king_dead_is_contiguous_prefix": contiguous(KING_DEAD) and bool(KING_DEAD[0]),
      "f10_dead_is_contiguous_prefix": contiguous(F10_DEAD) and bool(F10_DEAD[0]),
      "f10_dead_subset_of_king_dead": bool(np.all(F10_DEAD <= KING_DEAD)),
      "expect": {"king_dead": 3300, "f10_dead": 1110, "both_dead": 1110}}
G3["PASS"] = bool(G3["king_dead"] == 3300 and G3["f10_dead"] == 1110 and G3["both_dead"] == 1110)
R["GATE_G3_counts"] = G3
print("G3 king_dead=%d f10_dead=%d both=%d clean=%d PASS=%s" % (G3["king_dead"], G3["f10_dead"], G3["both_dead"], G3["clean"], G3["PASS"]))

# GATE D: two instruments
wpos = w3k > 0
agree = (legk == 0.0) == KING_DEAD
GD = {"n_anchors_w3king_gt0": int(wpos.sum()),
      "disagreements_where_w3king_gt0": int((~agree & wpos).sum()),
      "disagreements_all": int((~agree).sum()),
      "n_leg_king_exactly_zero": int((legk == 0.0).sum()),
      "n_w3king_zero": int((w3k == 0.0).sum()),
      "note": "instrument 1 = isfinite(SLOW[i,m]).sum()<10 from source on pod2; instrument 2 = leg_king==0.0 exactly in the archived arm rec"}
GD["PASS"] = bool(GD["disagreements_where_w3king_gt0"] == 0)
R["GATE_D_two_instruments"] = GD
print("GATE D: leg_king==0 vs source-dead  disagreements(w3k>0)=%d  all=%d  PASS=%s" %
      (GD["disagreements_where_w3king_gt0"], GD["disagreements_all"], GD["PASS"]))

# G2 (from the pod receipt, re-asserted here)
POD = json.load(open(OUT + "/receipts/RECEIPT_r14_pod_deadmask.json"))
R["pod_receipt"] = {"self_sha256": POD["self_sha256"], "row_coverage": POD["row_coverage"],
                    "inputs": {k: v["sha256"] for k, v in POD["inputs"].items()}}
G2 = {"SLOW_v3_first_finite_ts": POD["row_coverage"]["SLOW_v3_on_v4axis"]["first_finite_ts_utc"],
      "SLOW_v4_first_finite_ts": POD["row_coverage"]["SLOW_v4"]["first_finite_ts_utc"],
      "f10_first_finite_ts": POD["row_coverage"]["f10_A0_s42_on_axis"]["first_finite_ts_utc"],
      "n_king_dead_anchors_before_2024_in_ALPHA": int((KING_DEAD & (TS < T(2024,1,1))).sum()),
      "n_king_live_anchors_before_2024_in_ALPHA": int((CLEAN & (TS < T(2024,1,1))).sum())}
G2["PASS"] = bool(G2["SLOW_v3_first_finite_ts"] == "2024-01-01T00:00:00Z" and G2["n_king_live_anchors_before_2024_in_ALPHA"] == 0)
R["GATE_G2_source_coverage"] = G2
print("G2 SLOW_v3 first finite %s ; king-live before 2024 = %d ; PASS=%s" %
      (G2["SLOW_v3_first_finite_ts"], G2["n_king_live_anchors_before_2024_in_ALPHA"], G2["PASS"]))

# G4 conditional
G4 = {"king_dead_mean_g": round(float(gA0[KING_DEAD].mean()), 4), "king_dead_sharpe": round(ann(gA0[KING_DEAD]), 4),
      "king_live_mean_g": round(float(gA0[CLEAN].mean()), 4), "king_live_sharpe": round(ann(gA0[CLEAN]), 4),
      "both_dead_mean_g": round(float(gA0[BOTH_DEAD].mean()), 4), "both_dead_sharpe": round(ann(gA0[BOTH_DEAD]), 4),
      "f10dead_kinglive_n": int((F10_DEAD & CLEAN).sum()),
      "expect": {"king_dead_mean_g": -0.3770, "king_dead_sharpe": -1.1302,
                 "king_live_mean_g": 1.2058, "king_live_sharpe": 2.1508}}
G4["PASS"] = bool(abs(G4["king_dead_mean_g"]+0.3770) <= 0.0010 and abs(G4["king_dead_sharpe"]+1.1302) <= 0.005
                  and abs(G4["king_live_mean_g"]-1.2058) <= 0.0010 and abs(G4["king_live_sharpe"]-2.1508) <= 0.005)
R["GATE_G4_conditional"] = G4
print("G4 dead %+0.4f/%+0.4f  live %+0.4f/%+0.4f  PASS=%s" % (G4["king_dead_mean_g"], G4["king_dead_sharpe"],
      G4["king_live_mean_g"], G4["king_live_sharpe"], G4["PASS"]))
R["STEP1_ALL_GATES_PASS"] = bool(G1["PASS"] and G2["PASS"] and G3["PASS"] and G4["PASS"] and G5["PASS"] and G6["PASS"] and GD["PASS"])
assert R["STEP1_ALL_GATES_PASS"], "STEP 1 reproduction FAILED -> round stops (see receipt)"

# ===================================================================== bootstrap machinery
DAY = TS // 86400
ud, inv = np.unique(DAY, return_inverse=True); nd = len(ud)
order = np.argsort(inv, kind="stable")
st = np.searchsorted(inv[order], np.arange(nd)); en = np.append(st[1:], len(order))
def boot_idx(k, days_universe=None, B_=B):
    rng = np.random.default_rng([20260905, k])
    if days_universe is None:
        picks = rng.integers(0, nd, size=(B_, nd))
        return [np.concatenate([order[st[j]:en[j]] for j in picks[b]]) for b in range(B_)]
    dsel = np.nonzero(days_universe)[0]; m_ = len(dsel)
    picks = rng.integers(0, m_, size=(B_, m_))
    return [np.concatenate([order[st[dsel[j]]:en[dsel[j]]] for j in picks[b]]) for b in range(B_)]
day_is_clean = np.zeros(nd, bool)
np.logical_or.at(day_is_clean, inv[CLEAN], True)
day_all_clean = np.ones(nd, bool)
np.logical_and.at(day_all_clean, inv, CLEAN)
BOOT_FULL  = boot_idx(1)
BOOT_CLEAN = boot_idx(1, days_universe=day_all_clean)
BOOT_PAIR  = boot_idx(2)
BOOT_AM    = boot_idx(3)
R["bootstrap"] = {"B": B, "rng": "numpy.default_rng([20260905,k])",
                  "k_full": 1, "k_clean": 1, "k_paired_drho": 2, "k_amihud": 3,
                  "utc_days_full": int(nd), "utc_days_all_clean": int(day_all_clean.sum()),
                  "note": "CLEAN day universe = UTC days every anchor of which is king-live (no mixed day enters the CLEAN resample)"}
def ci(v, r_=4):
    v = np.asarray(v, float); v = v[np.isfinite(v)]
    return [round(float(np.percentile(v, 2.5)), r_), round(float(np.percentile(v, 97.5)), r_)]
def rho(x, y):
    if np.std(x) == 0 or np.std(y) == 0: return float("nan")
    return float(np.corrcoef(x, y)[0, 1])

# ===================================================================== STEP 2: baseline on CLEAN
def describe(g, ts, tr_raw=None, tr_match=None, boot=None, tag=""):
    nn = len(g); se = float(np.sqrt(APY/nn))
    wd, wdd = worstday(g, ts)
    o = {"n": nn, "range": [time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(ts[0]))),
                            time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(ts[-1])))],
         "mean_g_bps": round(float(g.mean()), 4), "sd_bps": round(float(np.std(g, ddof=1)), 4),
         "ann_sharpe": round(ann(g), 4), "SE_ann_sharpe": round(se, 4),
         "sharpe_analytic_CI95": [round(ann(g)-1.96*se, 4), round(ann(g)+1.96*se, 4)],
         "maxDD_bps_of_gross": round(mdd(g), 1), "worst_UTC_day_bps": round(wd, 1), "worst_UTC_day": wdd,
         "NAV_pct_per_yr_at_2x_gross": round(float(g.mean())*APY*2.0/100.0, 2)}
    if tr_raw is not None:
        o["turnover_RAW_sum_abs_dw"] = round(float(tr_raw.mean()), 6)
        o["turnover_MATCHED_mean_ratio"] = round(float(tr_match.mean()), 6)
        o["turnover_ratio_matched_over_raw"] = round(float(tr_match.mean()/tr_raw.mean()), 5)
    if boot is not None:
        o["mean_g_CI95"] = ci([g[i].mean() if len(i) else np.nan for i in boot])
        o["ann_sharpe_CI95_bootstrap"] = ci([ann(g[i]) if len(i) > 2 else np.nan for i in boot])
    return o
S2 = {}
S2["A0_FULL_W_ALPHA"] = describe(gA0, TS, turn_raw, turn_match, BOOT_FULL)
_remap = np.full(n, -1, np.int64); _remap[np.nonzero(CLEAN)[0]] = np.arange(int(CLEAN.sum()))
BOOT_CLEAN_LOCAL = [_remap[i[CLEAN[i]]] for i in BOOT_CLEAN]
assert all((x >= 0).all() for x in BOOT_CLEAN_LOCAL), "clean bootstrap remap"
S2["A0_CLEAN_king_live"] = describe(gA0[CLEAN], TS[CLEAN], turn_raw[CLEAN], turn_match[CLEAN],
                                    BOOT_CLEAN_LOCAL)
S2["A0_KINGDEAD"] = describe(gA0[KING_DEAD], TS[KING_DEAD], turn_raw[KING_DEAD], turn_match[KING_DEAD])
S2["A0_BOTHDEAD_fund_only_book"] = describe(gA0[BOTH_DEAD], TS[BOTH_DEAD], turn_raw[BOTH_DEAD], turn_match[BOTH_DEAD])
# W_TAIL convention for the tail numbers
S2["A0_FULL_W_TAIL"] = describe(gA0_T, TS_T)
S2["A0_CLEAN_on_W_TAIL"] = describe(gA0_T[CLEAN_T], TS_T[CLEAN_T])
S2["CLEAN_window_equivalence"] = {
    "n_clean_in_W_ALPHA": int(CLEAN.sum()), "n_clean_in_W_TAIL": int(CLEAN_T.sum()),
    "identical_set": bool(np.array_equal(TS[CLEAN], TS_T[CLEAN_T])),
    "why": "all 900 warm-drop anchors are king-dead, so W_ALPHA and W_TAIL give the SAME clean subsample"}
S2["by_year_A0"] = {}
for y in range(2022, 2027):
    m_ = (TS >= T(y,1,1)) & (TS < T(y+1,1,1))
    if m_.sum() == 0: continue
    S2["by_year_A0"][str(y)] = {"n": int(m_.sum()), "king_live_frac": round(float(CLEAN[m_].mean()), 4),
                                "mean_g": round(float(gA0[m_].mean()), 4), "sharpe": round(ann(gA0[m_]), 4)}
R["STEP2_baseline"] = S2
print("\nSTEP2  A0 FULL  n=%d mean_g %+0.4f SR %+0.4f | CLEAN n=%d mean_g %+0.4f SR %+0.4f (SE %0.4f)" %
      (S2["A0_FULL_W_ALPHA"]["n"], S2["A0_FULL_W_ALPHA"]["mean_g_bps"], S2["A0_FULL_W_ALPHA"]["ann_sharpe"],
       S2["A0_CLEAN_king_live"]["n"], S2["A0_CLEAN_king_live"]["mean_g_bps"], S2["A0_CLEAN_king_live"]["ann_sharpe"],
       S2["A0_CLEAN_king_live"]["SE_ann_sharpe"]))

# ===================================================================== candidates
BOOKS = {}; PLANE = {}; NOTE = {}
BP = reg("books_on_pinned_axis", ROOT + "/r10_combine/series/books_on_pinned_axis.npz")
zb = np.load(BP, allow_pickle=True)
assert np.array_equal(zb["ts"].astype(np.int64), TS), "books_on_pinned_axis ts != W_ALPHA"
bn = [str(x) for x in zb["names"]]; Gm = zb["G"]
gateB = {"A0_column_maxabs_vs_recomputed": float(np.max(np.abs(Gm[:, bn.index("A0")] - gA0)))}
gateB["PASS_bitwise"] = bool(gateB["A0_column_maxabs_vs_recomputed"] == 0.0)
R["GATE_books_axis"] = gateB
print("GATE books_on_pinned_axis A0 column maxabs vs recomputed = %.3e (bitwise=%s)" %
      (gateB["A0_column_maxabs_vs_recomputed"], gateB["PASS_bitwise"]))
for k in bn:
    if k == "A0": continue
    BOOKS[k] = Gm[:, bn.index(k)].astype(float); PLANE[k] = "fitted PWR_G230k (r10 screens)"; NOTE[k] = "r10_combine books_on_pinned_axis"

def from_rec(path, tag, plane, note, key=None):
    p = reg(tag, path); z = np.load(p, allow_pickle=True)
    c = [str(x) for x in z["cols"]]; jx = {x: i for i, x in enumerate(c)}
    kk = key or ("rec" if "rec" in z.files else "d30_n2_c42_rec")
    A = np.asarray(z[kk], float)
    tt = np.round(A[:, jx["ts"]]).astype(np.int64)
    assert np.array_equal(tt, ts_all), tag + ": ts axis mismatch"
    g = (A[:, jx["net_ex"]] / A[:, jx["gross_total"]])[ALPHA]
    BOOKS[tag] = g; PLANE[tag] = plane; NOTE[tag] = note
    return json.loads(str(z["config_json"])) if "config_json" in z.files else None
# AMENDMENT 1: A12 = the r3 XIB SCREEN's own arm (the one the archived rho 0.8891 is about).
cfgX = from_rec(OUT + "/receipts/r14_XIB_r3screen_s42.npz", "XIB_LAG50",
                "DEPLOYED fee-only (costb_fee_steady)",
                "r3_xib/arms/w10_ablation_series_R3_XIBLAG50_dyn_s42 (FEMAT r3_xib/dev/sig/XIBLAG50.npz) -- AMENDMENT 1")
cfgXd = from_rec(ROOT + "/r13_A_halfscale/receipts/XIB_LAG50_s42__REAL.npz", "XIB_LAG50_placeboREAL",
                 "DEPLOYED fee-only (costb_fee_steady)",
                 "DISCLOSURE ROW, outside SET A: the placebo-family REAL arm I first mis-picked (AMENDMENT 1)")
cfgA0f = from_rec(OUT + "/receipts/r14_A0_fee_s42.npz", "A0_feeplane",
                  "DEPLOYED fee-only (costb_fee_steady)",
                  "DISCLOSURE ROW, outside SET A: the SAME book A0 on the deployed cost plane -- a plane-sensitivity control for every rho below")
AMP = reg("r14_amihud_arms", OUT + "/receipts/r14_amihud_arms.npz")
za = np.load(AMP, allow_pickle=True)
AM_G = {}
for seed in ("42", "2027"):
    c = [str(x) for x in za["AMIHUD_s%s_cols" % seed]]; jx = {x: i for i, x in enumerate(c)}
    A = np.asarray(za["AMIHUD_s%s_rec" % seed], float)
    tt = np.round(A[:, jx["ts"]]).astype(np.int64); assert np.array_equal(tt, ts_all)
    AM_G[seed] = (A[:, jx["net_ex"]] / A[:, jx["gross_total"]])[ALPHA]
BOOKS["AMIHUD_SLEEVE"] = AM_G["42"]; PLANE["AMIHUD_SLEEVE"] = "fitted PWR_G230k"
NOTE["AMIHUD_SLEEVE"] = "p6 arm w10_ablation_series_P6_AMQ64_PWR_s42 (the sleeve as a STANDALONE book)"
BP2 = reg("r13B_series", ROOT + "/r13_B_withinhalf/receipts/r13B_series.npz")
zr = np.load(BP2, allow_pickle=True)
assert np.array_equal(zr["ts"].astype(np.int64), ts_all)
WA = zr["WA"].astype(bool)
gateWA = {"WA_matches_W_ALPHA": bool(np.array_equal(np.nonzero(WA)[0], ALPHA)), "n_WA": int(WA.sum())}
R["GATE_r13B_WA"] = gateWA
BOOKS["T1_FORMB"] = zr["g_primary"][ALPHA].astype(float); PLANE["T1_FORMB"] = "r13B internal (see its receipt)"
NOTE["T1_FORMB"] = "r13B g_primary = the within-half beta-overlay book (an OVERLAY ON A0, not a standalone bet)"
R["r13B_g_base_vs_A0_maxabs"] = float(np.max(np.abs(zr["g_base"][ALPHA] - gA0)))

SETA = ["TSMOM","VRP","CMUM","SLOW","COINT","REVS","TSMOM_best","CMUM_static","CMUM_best",
        "SLOW_best","REVS_best","XIB_LAG50","AMIHUD_SLEEVE","T1_FORMB"]
assert all(k in BOOKS for k in SETA), [k for k in SETA if k not in BOOKS]
# SET B: the 13 SLOW_CLOCK component arms
SIGN = {"A_QVS1H":"__m","A_REV1H":"__m","A_TBF1H":"__m","A_VOL1H":"__p","B_REV12H":"__m",
        "B_TBF12H":"__p","C_TBF3D":"__p","C_TBF7D":"__p","C_TBF14D":"__p","C_TBF30D":"__p",
        "D_FCHG12H":"__m","D_FCHG3D":"__m","D_FSLOPE":"__p"}
SETB = []
for f, s_ in SIGN.items():
    p = SCR + "/slowarms/PWR_%s%s.npz" % (f, s_)
    if not os.path.exists(p): continue
    from_rec(p, "SLOWARM_" + f, "fitted PWR_G230k", "SLOW_CLOCK component arm (SET B, distribution only)")
    SETB.append("SLOWARM_" + f)
R["arms"] = {"SET_A": SETA, "SET_B": SETB, "K_declared": 41,
             "DISCLOSURE_outside_SET_A": ["XIB_LAG50_placeboREAL", "A0_feeplane"],
             "K_actual": len(SETA) + len(SETB) + 14,
             "amendment_1": "A12 identity corrected to the r3-screen XIB arm; K unchanged"}
R["book_meta"] = {k: {"cost_plane": PLANE[k], "note": NOTE[k],
                      "mean_g_FULL": round(float(BOOKS[k].mean()), 4),
                      "ann_sharpe_FULL": round(ann(BOOKS[k]), 4)}
                  for k in SETA + SETB + ["XIB_LAG50_placeboREAL", "A0_feeplane"]}

# ===================================================================== STEP 3: rho FULL vs CLEAN
def band(r_):
    ar = abs(r_)
    return "REWEIGHTING" if ar >= 0.60 else ("PARTIAL" if ar >= 0.30 else "INDEPENDENT")
ROWS = {}
cl_idx = np.nonzero(CLEAN)[0]
DISCLOSE = ["XIB_LAG50_placeboREAL", "A0_feeplane"]
for k in SETA + SETB + DISCLOSE:
    y = BOOKS[k]
    rf = rho(y, gA0); rc = rho(y[CLEAN], gA0[CLEAN]); rd = rho(y[KING_DEAD], gA0[KING_DEAD])
    sf = float(spearmanr(y, gA0).statistic); sc = float(spearmanr(y[CLEAN], gA0[CLEAN]).statistic)
    cif = ci([rho(y[i], gA0[i]) for i in BOOT_FULL])
    cic = ci([rho(y[i][CLEAN[i]], gA0[i][CLEAN[i]]) for i in BOOT_CLEAN])
    dboot = np.array([rho(y[i][CLEAN[i]], gA0[i][CLEAN[i]]) - rho(y[i], gA0[i]) for i in BOOT_PAIR])
    cid = ci(dboot)
    ROWS[k] = {"set": ("A" if k in SETA else ("B" if k in SETB else "DISCLOSURE")), "cost_plane": PLANE[k],
               "rho_FULL": round(rf, 4), "rho_FULL_CI95": cif,
               "rho_CLEAN": round(rc, 4), "rho_CLEAN_CI95": cic,
               "rho_KINGDEAD": round(rd, 4),
               "d_rho": round(rc - rf, 4), "d_rho_CI95_paired": cid,
               "d_rho_CI_excludes_0": bool(cid[0] > 0 or cid[1] < 0),
               "material_move": bool(abs(rc - rf) >= 0.10 and (cid[0] > 0 or cid[1] < 0)),
               "band_FULL": band(rf), "band_CLEAN": band(rc),
               "classification_changes": bool(band(rf) != band(rc)),
               "spearman_FULL": round(sf, 4), "spearman_CLEAN": round(sc, 4),
               "mean_g_FULL": round(float(y.mean()), 4), "mean_g_CLEAN": round(float(y[CLEAN].mean()), 4),
               "sharpe_FULL": round(ann(y), 4), "sharpe_CLEAN": round(ann(y[CLEAN]), 4)}
    print("  rho %-18s FULL %+0.4f %s  CLEAN %+0.4f %s  d %+0.4f %s  %s%s" %
          (k, rf, cif, rc, cic, rc-rf, cid, ROWS[k]["band_FULL"],
           (" -> " + ROWS[k]["band_CLEAN"]) if ROWS[k]["classification_changes"] else ""), flush=True)
R["STEP3_rho"] = ROWS

# ===================================================================== STEP 4: Amihud
S4 = {"archived": {"source": "p6_receipts/P6_COMBO.json s42 alloc 0.20 SR_gain_vs_A0",
                   "value": 0.24579898267356137, "window": "p6 own: rec[900:] and ts <= 2026-08-10 20Z, n=9018",
                   "by_year_A0": {"2022":0.48,"2023":-1.936,"2024":1.088,"2025":1.187,"2026":5.433},
                   "by_year_sleeve": {"2022":0.168,"2023":1.861,"2024":1.197,"2025":1.379,"2026":2.407}},
      "PRIMARY_cell": "a=0.20 seed 42", "threshold_survives": 0.1229, "alloc": {}}
for seed in ("42", "2027"):
    S = AM_G[seed]
    for aa in (0.10, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50):
        C = (1-aa)*gA0 + aa*S
        dF = ann(C) - ann(gA0); dC = ann(C[CLEAN]) - ann(gA0[CLEAN])
        ciF = ci([ann(C[i]) - ann(gA0[i]) for i in BOOT_AM])
        ciC = ci([ann(C[i][CLEAN[i]]) - ann(gA0[i][CLEAN[i]]) for i in BOOT_AM])
        verdict = ("REVERSES" if dC <= 0 else
                   ("SURVIVES" if (dC >= 0.1229 and ciC[0] > 0) else "COLLAPSES"))
        S4["alloc"]["s%s_a%.2f" % (seed, aa)] = {
            "seed": seed, "a": aa,
            "SR_A0_FULL": round(ann(gA0), 4), "SR_comb_FULL": round(ann(C), 4),
            "dSharpe_FULL": round(dF, 4), "dSharpe_FULL_CI95": ciF,
            "SR_A0_CLEAN": round(ann(gA0[CLEAN]), 4), "SR_comb_CLEAN": round(ann(C[CLEAN]), 4),
            "dSharpe_CLEAN": round(dC, 4), "dSharpe_CLEAN_CI95": ciC,
            "dSharpe_CLEAN_CI_lower_gt_0": bool(ciC[0] > 0),
            "verdict": verdict}
for seed in ("42", "2027"):
    S = AM_G[seed]
    S4["sleeve_standalone_s" + seed] = {
        "SR_FULL": round(ann(S), 4), "SR_CLEAN": round(ann(S[CLEAN]), 4),
        "SR_KINGDEAD": round(ann(S[KING_DEAD]), 4),
        "mean_g_FULL": round(float(S.mean()), 4), "mean_g_CLEAN": round(float(S[CLEAN].mean()), 4),
        "mean_g_KINGDEAD": round(float(S[KING_DEAD].mean()), 4),
        "rho_to_A0_FULL": round(rho(S, gA0), 4), "rho_to_A0_CLEAN": round(rho(S[CLEAN], gA0[CLEAN]), 4),
        "by_year": {str(y): {"A0": round(ann(gA0[(TS>=T(y,1,1))&(TS<T(y+1,1,1))]), 3),
                             "sleeve": round(ann(S[(TS>=T(y,1,1))&(TS<T(y+1,1,1))]), 3),
                             "n": int(((TS>=T(y,1,1))&(TS<T(y+1,1,1))).sum())}
                    for y in range(2022, 2027)}}
R["STEP4_amihud"] = S4
p = S4["alloc"]["s42_a0.20"]
print("\nSTEP4 PRIMARY a=0.20 s42:  FULL d %+0.4f %s | CLEAN d %+0.4f %s -> %s" %
      (p["dSharpe_FULL"], p["dSharpe_FULL_CI95"], p["dSharpe_CLEAN"], p["dSharpe_CLEAN_CI95"], p["verdict"]))

# ===================================================================== STEP 5: the central claim
absA_F = np.array([abs(ROWS[k]["rho_FULL"]) for k in SETA])
absA_C = np.array([abs(ROWS[k]["rho_CLEAN"]) for k in SETA])
absAll_F = np.array([abs(ROWS[k]["rho_FULL"]) for k in SETA + SETB])
absAll_C = np.array([abs(ROWS[k]["rho_CLEAN"]) for k in SETA + SETB])
def dist(v):
    return {"n": int(len(v)), "min": round(float(v.min()), 4), "p25": round(float(np.percentile(v, 25)), 4),
            "median": round(float(np.median(v)), 4), "p75": round(float(np.percentile(v, 75)), 4),
            "max": round(float(v.max()), 4), "mean": round(float(v.mean()), 4),
            "n_REWEIGHTING_ge_0.60": int((v >= 0.60).sum()),
            "n_PARTIAL_0.30_0.60": int(((v >= 0.30) & (v < 0.60)).sum()),
            "n_INDEPENDENT_lt_0.30": int((v < 0.30).sum())}
S5 = {"SET_A_FULL": dist(absA_F), "SET_A_CLEAN": dist(absA_C),
      "SET_A_plus_B_FULL": dist(absAll_F), "SET_A_plus_B_CLEAN": dist(absAll_C),
      "classification_changes": [k for k in SETA + SETB if ROWS[k]["classification_changes"]],
      "material_moves": sorted([k for k in SETA + SETB if ROWS[k]["material_move"]],
                               key=lambda k: -abs(ROWS[k]["d_rho"]))}
R_F = S5["SET_A_FULL"]["n_REWEIGHTING_ge_0.60"]; R_C = S5["SET_A_CLEAN"]["n_REWEIGHTING_ge_0.60"]
medF = S5["SET_A_FULL"]["median"]; medC = S5["SET_A_CLEAN"]["median"]
S5["R_FULL"] = R_F; S5["R_CLEAN"] = R_C
if R_F <= 3:
    S5["verdict"] = "CLAIM NEVER HELD"
elif R_C >= R_F and medC >= medF - 0.10:
    S5["verdict"] = "CLAIM SURVIVES"
else:
    S5["verdict"] = "CLAIM WEAKENS"
S5["verdict_rule"] = "prereg §6 STEP 5"
R["STEP5_central_claim"] = S5
print("\nSTEP5 SET A |rho|: FULL median %.4f (REWEIGHT %d/14) | CLEAN median %.4f (REWEIGHT %d/14) -> %s"
      % (medF, R_F, medC, R_C, S5["verdict"]))

R["inputs"] = IN
SAVE_NAMES = SETA + SETB + DISCLOSE
np.savez_compressed(OUT + "/series/r14_clean_series.npz", ts=TS, g_A0=gA0, king_dead=KING_DEAD,
                    f10_dead=F10_DEAD, both_dead=BOTH_DEAD, clean=CLEAN,
                    n_finite_king_v3=nk3, n_finite_king_v4=nk4, n_finite_f10=nf10,
                    turn_raw=turn_raw, turn_matched=turn_match,
                    names=np.array(SAVE_NAMES), G=np.column_stack([BOOKS[k] for k in SAVE_NAMES]),
                    amihud_s42=AM_G["42"], amihud_s2027=AM_G["2027"])
R["out_series_sha256"] = sha(OUT + "/series/r14_clean_series.npz")
json.dump(R, open(OUT + "/receipts/RECEIPT_r14_main.json", "w"), indent=1)
print("\nR14_MAIN_DONE")
