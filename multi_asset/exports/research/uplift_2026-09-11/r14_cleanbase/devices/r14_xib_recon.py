"""r14 SUPPLEMENT — reconcile MY rho(XIB_LAG50, A0) = +0.8555 against the archived +0.8891.

Two instruments disagree -> reconcile before either is quoted (desk rule).
The archived XIB arm is priced on the DEPLOYED fee-only plane (costb_fee_steady); the pinned A0 I
correlated it against is on the FITTED plane (costb_PWR_G230k).  This device pairs XIB with the
fee-plane A0 that the r3 XIB screen itself used (R3_A0_dyn_s42) and walks the window as well, so the
0.0336 gap is attributed to plane and/or window rather than left as an unexplained disagreement.

PREREG 89ba6e7d87d79866d78f7a95400ee13b21b7d0d511dfc82f6ce7b509ca956fe7 (asserted).
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
assert sha(OUT + "/PREREG_r14_clean_baseline_2026-09-12.md") == PREREG_SHA
APY = 2190.0; WARM = 900; B = 2000
R = {"step": "R14_XIB_RECON", "self_sha256": sha(os.path.abspath(__file__)),
     "prereg_sha256": PREREG_SHA, "env_whitelist": ENV_WHITELIST, "env_seen_at_runtime": ENV_SEEN,
     "numpy": np.__version__, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
def g_of(p, key=None):
    z = np.load(p, allow_pickle=True)
    c = [str(x) for x in z["cols"]]; jx = {x: i for i, x in enumerate(c)}
    k = key or ("rec" if "rec" in z.files else "d30_n2_c42_rec")
    A = np.asarray(z[k], float)
    ts = np.round(A[:, jx["ts"]]).astype(np.int64)
    return ts, A[:, jx["net_ex"]]/A[:, jx["gross_total"]], json.loads(str(z["config_json"])), k
P_XIB  = ROOT + "/r13_A_halfscale/receipts/XIB_LAG50_s42__REAL.npz"
P_A0FE = OUT + "/receipts/r14_A0_fee_s42.npz"
P_A0PW = ROOT + "/r10_screen/CMUM_CARRY/pin/A0_PWR230k_s42.npz"
P_DM   = OUT + "/receipts/r14_deadmask.npz"
R["inputs"] = {k: {"path": v, "sha256": sha(v)} for k, v in
               {"XIB_LAG50": P_XIB, "A0_fee_steady_R3_A0_dyn_s42": P_A0FE, "A0_fitted_PWR230k": P_A0PW,
                "deadmask": P_DM}.items()}
zf = np.load(P_A0FE, allow_pickle=True)
R["A0_fee_source"] = {"pod2_path": str(zf["src_path"]), "pod2_sha256": str(zf["src_sha256"]),
                      "rec_key": str(zf["rec_key"])}
tsX, gX, cX, kX = g_of(P_XIB)
tsF, gF, cF, kF = g_of(P_A0FE)
tsP, gP, cP, kP = g_of(P_A0PW)
assert np.array_equal(tsX, tsF) and np.array_equal(tsX, tsP)
R["cost_planes"] = {"XIB_LAG50": cX["COSTB_JSON"], "A0_fee": cF["COSTB_JSON"], "A0_fitted": cP["COSTB_JSON"],
                    "XIB_FEMAT": cX["FEMAT_NPZ"], "A0_fee_FEMAT": cF["FEMAT_NPZ"],
                    "A0_fee_COST_B": cF["COST_B"], "XIB_COST_B": cX["COST_B"]}
dm = np.load(P_DM); pos = {int(t): i for i, t in enumerate(dm["ts"])}
KD_all = np.array([dm["n_finite_king_v3"][pos[int(t)]] < 10 for t in tsX])
WINDOWS = {
 "W_ALPHA_n9138 (E-0911-A + E-0911-D)": (np.arange(len(tsX)) >= WARM) & (tsX <= T(2026,8,30,20)),
 "p6/r3 window n9018 (warm900, ceiling 2026-08-10 20Z)": (np.arange(len(tsX)) >= WARM) & (tsX <= T(2026,8,10,20)),
 "warm900 to axis end n9139": (np.arange(len(tsX)) >= WARM),
 "full axis n10039 (no warm drop)": np.ones(len(tsX), bool),
 "frozen 2025-03-01..2026-08-10 20Z": (tsX >= T(2025,3,1)) & (tsX <= T(2026,8,10,20)),
}
def rho(a, b): return float(np.corrcoef(a, b)[0, 1])
TAB = {}
for wn, m in WINDOWS.items():
    cl = m & ~KD_all
    TAB[wn] = {"n": int(m.sum()), "n_clean": int(cl.sum()),
               "rho_XIBfee_vs_A0fee_MATCHED_PLANE": round(rho(gX[m], gF[m]), 4),
               "rho_XIBfee_vs_A0fitted_MIXED_PLANE": round(rho(gX[m], gP[m]), 4),
               "rho_A0fee_vs_A0fitted": round(rho(gF[m], gP[m]), 4),
               "rho_clean_XIBfee_vs_A0fee": (round(rho(gX[cl], gF[cl]), 4) if cl.sum() > 10 else None),
               "rho_clean_XIBfee_vs_A0fitted": (round(rho(gX[cl], gP[cl]), 4) if cl.sum() > 10 else None)}
    print("%-52s n %5d  matched %+0.4f  mixed %+0.4f  (clean matched %s)" %
          (wn, m.sum(), TAB[wn]["rho_XIBfee_vs_A0fee_MATCHED_PLANE"],
           TAB[wn]["rho_XIBfee_vs_A0fitted_MIXED_PLANE"], TAB[wn]["rho_clean_XIBfee_vs_A0fee"]), flush=True)
R["window_x_plane_table"] = TAB
# block bootstrap on W_ALPHA for the matched-plane pair
m = WINDOWS["W_ALPHA_n9138 (E-0911-A + E-0911-D)"]; ts = tsX[m]
day = ts // 86400; ud, inv = np.unique(day, return_inverse=True); nd = len(ud)
order = np.argsort(inv, kind="stable"); st = np.searchsorted(inv[order], np.arange(nd)); en = np.append(st[1:], len(order))
rng = np.random.default_rng([20260905, 1]); picks = rng.integers(0, nd, size=(B, nd))
BOOT = [np.concatenate([order[st[j]:en[j]] for j in picks[b]]) for b in range(B)]
x = gX[m]; y = gF[m]; cl = (~KD_all)[m]
def ci(v): v = np.asarray(v, float); v = v[np.isfinite(v)]; return [round(float(np.percentile(v,2.5)),4), round(float(np.percentile(v,97.5)),4)]
R["W_ALPHA_matched_plane"] = {
  "rho_FULL": round(rho(x, y), 4), "rho_FULL_CI95": ci([rho(x[i], y[i]) for i in BOOT]),
  "rho_CLEAN": round(rho(x[cl], y[cl]), 4),
  "rho_CLEAN_CI95": ci([rho(x[i][cl[i]], y[i][cl[i]]) for i in BOOT]),
  "d_rho": round(rho(x[cl], y[cl]) - rho(x, y), 4),
  "band_FULL": "REWEIGHTING" if abs(rho(x, y)) >= 0.60 else "PARTIAL/INDEPENDENT",
  "band_CLEAN": "REWEIGHTING" if abs(rho(x[cl], y[cl])) >= 0.60 else "PARTIAL/INDEPENDENT"}
R["archived_claim"] = {"value": 0.8891, "where": "PREREG_r3_xib_lag50_fundleg_promotion L19 / RESULT_r6_judge2 L20 (prose only; no JSON receipt in the repo carries it)",
                       "reconciled": None}
best = None
for wn, v in TAB.items():
    for lab in ("rho_XIBfee_vs_A0fee_MATCHED_PLANE", "rho_XIBfee_vs_A0fitted_MIXED_PLANE"):
        d = abs(v[lab] - 0.8891)
        if best is None or d < best[0]: best = (d, wn, lab, v[lab])
R["archived_claim"]["reconciled"] = {"closest_cell_gap": round(best[0], 4), "window": best[1],
                                     "pairing": best[2], "value": best[3]}
print("\nclosest cell to the archived 0.8891: %s / %s = %+0.4f (gap %0.4f)" % (best[1], best[2], best[3], best[0]))
json.dump(R, open(OUT + "/receipts/RECEIPT_r14_xib_recon.json", "w"), indent=1)
print("XIB_RECON_DONE")
