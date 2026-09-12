"""r14 STEP 4 detail — the Amihud sleeve's +0.2458, taken apart.

Reproduces the archived 4/4 cells (2 arm seeds x 2 bootstrap seeds, P6_COMBO_PAIRED.json) on p6's own
window, then re-runs them on W_ALPHA and on CLEAN (king-live).  Also: per-year, the 2023-excluded test
(the audit's specific suspicion), the KING-DEAD half, and the mean-g vs sd decomposition -- because the
archived receipt's own dg_point is -0.0025 bps/anchor, i.e. the combination earns LESS, not more.

PREREG 89ba6e7d87d79866d78f7a95400ee13b21b7d0d511dfc82f6ce7b509ca956fe7 + AMENDMENT 1 (asserted).
ENV WHITELIST (E-0826-D) = EMPTY SET, asserted in-file.
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
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def T(*a): return calendar.timegm(a + (0,)*(6-len(a)))
ROOT = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11"
OUT = ROOT + "/r14_cleanbase"
PREREG_SHA = "89ba6e7d87d79866d78f7a95400ee13b21b7d0d511dfc82f6ce7b509ca956fe7"
AMD1_SHA = "e1caddf028b5148403da28527b6cb27ab152652d413c5f8bdf4bd04e4b74012f"
assert sha(OUT + "/PREREG_r14_clean_baseline_2026-09-12.md") == PREREG_SHA
assert sha(OUT + "/PREREG_AMENDMENT_1_2026-09-12.md") == AMD1_SHA
APY = 2190.0; WARM = 900; B = 2000
R = {"step": "R14_AMIHUD_DETAIL", "self_sha256": sha(os.path.abspath(__file__)),
     "prereg_sha256": PREREG_SHA, "prereg_amendment_1_sha256": AMD1_SHA,
     "env_whitelist": ENV_WHITELIST, "env_seen_at_runtime": ENV_SEEN,
     "numpy": np.__version__, "B": B, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
def g_of(p):
    z = np.load(p, allow_pickle=True); c = [str(x) for x in z["cols"]]; jx = {x: i for i, x in enumerate(c)}
    k = "rec" if "rec" in z.files else "d30_n2_c42_rec"; A = np.asarray(z[k], float)
    return np.round(A[:, jx["ts"]]).astype(np.int64), A[:, jx["net_ex"]]/A[:, jx["gross_total"]]
P = {"A0_s42": ROOT + "/r10_screen/CMUM_CARRY/pin/A0_PWR230k_s42.npz",
     "A0_s2027": OUT + "/receipts/r14_A0_PWR230k_s2027.npz",
     "AMIHUD": OUT + "/receipts/r14_amihud_arms.npz",
     "deadmask": OUT + "/receipts/r14_deadmask.npz"}
R["inputs"] = {k: {"path": v, "sha256": sha(v)} for k, v in P.items()}
ts, A42 = g_of(P["A0_s42"]); ts2, A27 = g_of(P["A0_s2027"]); assert np.array_equal(ts, ts2)
za = np.load(P["AMIHUD"], allow_pickle=True)
S = {}
for s_ in ("42", "2027"):
    c = [str(x) for x in za["AMIHUD_s%s_cols" % s_]]; jx = {x: i for i, x in enumerate(c)}
    M = np.asarray(za["AMIHUD_s%s_rec" % s_], float)
    assert np.array_equal(np.round(M[:, jx["ts"]]).astype(np.int64), ts)
    S[s_] = M[:, jx["net_ex"]]/M[:, jx["gross_total"]]
R["sleeve_seed_identity"] = {"s42_vs_s2027_maxabs_dg": float(np.max(np.abs(S["42"]-S["2027"]))),
    "bitwise_identical": bool(np.array_equal(S["42"], S["2027"])),
    "meaning": "the Amihud sleeve arm carries NO DL seed; the archived 2-seed spread comes entirely from the A0 side"}
print("sleeve seed identity maxabs dg =", R["sleeve_seed_identity"]["s42_vs_s2027_maxabs_dg"])
dm = np.load(P["deadmask"]); pos = {int(t): i for i, t in enumerate(dm["ts"])}
KD = np.array([dm["n_finite_king_v3"][pos[int(t)]] < 10 for t in ts])
WIN = {"P6_n9018": (np.arange(len(ts)) >= WARM) & (ts <= T(2026,8,10,20)),
       "W_ALPHA_n9138": (np.arange(len(ts)) >= WARM) & (ts <= T(2026,8,30,20))}
WIN["W_ALPHA_CLEAN"] = WIN["W_ALPHA_n9138"] & ~KD
WIN["W_ALPHA_KINGDEAD"] = WIN["W_ALPHA_n9138"] & KD
WIN["W_ALPHA_ex2023"] = WIN["W_ALPHA_n9138"] & ~((ts >= T(2023,1,1)) & (ts < T(2024,1,1)))
WIN["W_ALPHA_2023only"] = WIN["W_ALPHA_n9138"] & ((ts >= T(2023,1,1)) & (ts < T(2024,1,1)))
def ann(x):
    sd = np.std(x, ddof=1); return float(np.mean(x)/sd*np.sqrt(APY)) if sd > 0 else float("nan")
def blocks(mask, k):
    t = ts[mask]; day = t // 86400; ud, inv = np.unique(day, return_inverse=True); nd = len(ud)
    order = np.argsort(inv, kind="stable"); st = np.searchsorted(inv[order], np.arange(nd)); en = np.append(st[1:], len(order))
    rng = np.random.default_rng([20260905, k]); picks = rng.integers(0, nd, size=(B, nd))
    return [np.concatenate([order[st[j]:en[j]] for j in picks[b]]) for b in range(B)]
def ci(v): v = np.asarray(v, float); v = v[np.isfinite(v)]; return [round(float(np.percentile(v,2.5)),4), round(float(np.percentile(v,97.5)),4)]
CELLS = {}
for wn, m in WIN.items():
    for s_ in ("42", "2027"):
        A = (A42 if s_ == "42" else A27)[m]; Sl = S[s_][m]
        for aa in (0.10, 0.20, 0.30, 0.40, 0.50):
            C = (1-aa)*A + aa*Sl
            row = {"n": int(m.sum()), "SR_A0": round(ann(A), 4), "SR_sleeve": round(ann(Sl), 4),
                   "SR_comb": round(ann(C), 4), "dSR_point": round(ann(C)-ann(A), 4),
                   "mean_g_A0": round(float(A.mean()), 4), "mean_g_comb": round(float(C.mean()), 4),
                   "dg_point": round(float(C.mean()-A.mean()), 5),
                   "sd_A0": round(float(np.std(A, ddof=1)), 4), "sd_comb": round(float(np.std(C, ddof=1)), 4),
                   "sd_reduction_pct": round(100*(1-np.std(C, ddof=1)/np.std(A, ddof=1)), 3)}
            if aa == 0.20:
                for k in (0, 9, 3):
                    BK = blocks(m, k)
                    row["dSR_ci95_k%d" % k] = ci([ann(C[i])-ann(A[i]) for i in BK])
                    row["P_dSR_gt0_k%d" % k] = round(float(np.mean([ (ann(C[i])-ann(A[i])) > 0 for i in BK])), 4)
                    row["dg_ci95_k%d" % k] = ci([C[i].mean()-A[i].mean() for i in BK])
            CELLS["%s|s%s|a%.2f" % (wn, s_, aa)] = row
R["cells"] = CELLS
print("\n%-24s %-6s %-6s %8s %8s %8s %-22s %10s %-22s %8s"%("window","seed","a","SR_A0","SR_comb","dSR","dSR_CI95_k0","dg","dg_CI95_k0","sd-%"))
for kk in sorted(CELLS):
    v = CELLS[kk]
    if not kk.endswith("a0.20"): continue
    wn, s_, aa = kk.split("|")
    print("%-24s %-6s %-6s %8.4f %8.4f %+8.4f %-22s %+10.5f %-22s %8.3f" %
          (wn, s_, aa, v["SR_A0"], v["SR_comb"], v["dSR_point"], str(v.get("dSR_ci95_k0")),
           v["dg_point"], str(v.get("dg_ci95_k0")), v["sd_reduction_pct"]), flush=True)
R["archived_4of4_reproduction"] = {
  "archived": {"s42_k0_dSR_ci95": [0.033640892958924314, 0.4586626276072951],
               "s42_k9_dSR_ci95": [0.03147445768736703, 0.4718962756713162],
               "s2027_k0_dSR_ci95": [0.031902571636209624, 0.4553064915118186],
               "s2027_k9_dSR_ci95": [0.030514800689848555, 0.4638355310432292],
               "s42_dSR_point": 0.24579898267356137, "s42_dg_point": -0.0025163156917981603,
               "source": "p6_receipts/P6_COMBO_PAIRED.json"},
  "mine_on_P6_window": {"s42_k0": CELLS["P6_n9018|s42|a0.20"]["dSR_ci95_k0"],
                        "s42_k9": CELLS["P6_n9018|s42|a0.20"]["dSR_ci95_k9"],
                        "s2027_k0": CELLS["P6_n9018|s2027|a0.20"]["dSR_ci95_k0"],
                        "s2027_k9": CELLS["P6_n9018|s2027|a0.20"]["dSR_ci95_k9"],
                        "s42_dSR_point": CELLS["P6_n9018|s42|a0.20"]["dSR_point"],
                        "s42_dg_point": CELLS["P6_n9018|s42|a0.20"]["dg_point"]},
  "mine_on_CLEAN": {"s42_k0": CELLS["W_ALPHA_CLEAN|s42|a0.20"]["dSR_ci95_k0"],
                    "s42_k9": CELLS["W_ALPHA_CLEAN|s42|a0.20"]["dSR_ci95_k9"],
                    "s2027_k0": CELLS["W_ALPHA_CLEAN|s2027|a0.20"]["dSR_ci95_k0"],
                    "s2027_k9": CELLS["W_ALPHA_CLEAN|s2027|a0.20"]["dSR_ci95_k9"],
                    "s42_dSR_point": CELLS["W_ALPHA_CLEAN|s42|a0.20"]["dSR_point"],
                    "s42_dg_point": CELLS["W_ALPHA_CLEAN|s42|a0.20"]["dg_point"]}}
n_pos_arch = 4
n_pos_mine_p6 = sum(1 for k in ("s42_k0","s42_k9","s2027_k0","s2027_k9") if R["archived_4of4_reproduction"]["mine_on_P6_window"][k][0] > 0)
n_pos_mine_cl = sum(1 for k in ("s42_k0","s42_k9","s2027_k0","s2027_k9") if R["archived_4of4_reproduction"]["mine_on_CLEAN"][k][0] > 0)
R["archived_4of4_reproduction"]["cells_with_CI_lower_bound_gt_0"] = {
    "archived_on_P6_window": n_pos_arch, "mine_on_P6_window": n_pos_mine_p6, "mine_on_CLEAN": n_pos_mine_cl}
print("\n4/4 cells with CI lower bound > 0:  archived(P6 window) 4/4  |  mine(P6 window) %d/4  |  mine(CLEAN) %d/4"
      % (n_pos_mine_p6, n_pos_mine_cl))
# per year at a=0.20, seed 42
PY = {}
for y in range(2022, 2027):
    m = WIN["W_ALPHA_n9138"] & (ts >= T(y,1,1)) & (ts < T(y+1,1,1))
    A = A42[m]; Sl = S["42"][m]; C = 0.8*A + 0.2*Sl
    PY[str(y)] = {"n": int(m.sum()), "king_live_frac": round(float((~KD)[m].mean()), 4),
                  "SR_A0": round(ann(A), 3), "SR_sleeve": round(ann(Sl), 3), "SR_comb": round(ann(C), 3),
                  "dSR": round(ann(C)-ann(A), 4), "dg": round(float(C.mean()-A.mean()), 5)}
R["per_year_a020_s42"] = PY
print("\nper year a=0.20 s42:")
for y, v in PY.items():
    print("  %s n%5d kinglive %.2f  A0 %+7.3f sleeve %+7.3f comb %+7.3f  dSR %+0.4f  dg %+0.5f" %
          (y, v["n"], v["king_live_frac"], v["SR_A0"], v["SR_sleeve"], v["SR_comb"], v["dSR"], v["dg"]))
R["audit_suspicion_test"] = {
  "claim": "the +0.2458 is entirely a 2023 fix, and 2023 is a dead-king year",
  "dSR_on_W_ALPHA": CELLS["W_ALPHA_n9138|s42|a0.20"]["dSR_point"],
  "dSR_excluding_2023": CELLS["W_ALPHA_ex2023|s42|a0.20"]["dSR_point"],
  "dSR_2023_only": CELLS["W_ALPHA_2023only|s42|a0.20"]["dSR_point"],
  "dSR_on_CLEAN_2024on": CELLS["W_ALPHA_CLEAN|s42|a0.20"]["dSR_point"],
  "dSR_on_KINGDEAD": CELLS["W_ALPHA_KINGDEAD|s42|a0.20"]["dSR_point"],
  "retention_CLEAN_over_FULL": round(CELLS["W_ALPHA_CLEAN|s42|a0.20"]["dSR_point"] /
                                     CELLS["W_ALPHA_n9138|s42|a0.20"]["dSR_point"], 4)}
print("\naudit suspicion:", json.dumps(R["audit_suspicion_test"], indent=1))
json.dump(R, open(OUT + "/receipts/RECEIPT_r14_amihud_detail.json", "w"), indent=1)
print("AMIHUD_DETAIL_DONE")
