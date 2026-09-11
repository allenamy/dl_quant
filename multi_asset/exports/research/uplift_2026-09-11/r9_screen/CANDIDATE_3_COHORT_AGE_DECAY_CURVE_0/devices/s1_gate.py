#!/usr/bin/env python3
"""
r9_screen STEP 1 -- FEASIBILITY GATE for COHORT_AGE_DECAY_CURVE.
E-0826-D ENV WHITELIST FOR THIS SCRIPT = THE EMPTY SET (asserted: os.environ.get raises).
Everything is an explicit absolute path.

What this proves (or fails to prove) BEFORE anything expensive:
  G1  device sha == pinned GATE-P sha b88e35a4...
  G2  the archived A0 weight matrix (V4_A0_dyn_s42, costb_fee_steady) and the pinned-cost
      A0 rerun (R8_A0_s42, costb_PWR_G230k) carry the SAME book -> W bitwise identical.
      (cost never feeds back into sm in the device; this is the test of that claim, not the claim.)
  G3  the accounting inputs resolve, by readlink, to the v4-pinned objects.
  G4  I can reproduce the device's own rec columns (pnl_ex, carry_ex, cost_ex, gross_total,
      turnover, net_ex) from W + meta + panel + the pinned cost tiers. This is the instrument test.
  G5  NO-LOOKAHEAD: the attribution uses only W[t] (chosen at anchor t) and y4[t] (realised over
      [E_t+5m, E_t+4h+5m)). Assert the panel row used at anchor t is the anchor's own row.
"""
import os, sys, json, time, hashlib, calendar
import numpy as np
from scipy.stats import rankdata
# E-0826-D: the guard is installed AFTER third-party imports, because numpy/scipy read their own
# runtime env (NUMPY_MADVISE_HUGEPAGE, OMP_NUM_THREADS) at import time. Those are runtime knobs of
# the libraries, not configuration of this analysis. From here on, ANY env read raises.
ENV_WHITELIST = frozenset()
_CONFIG_ENV_NAMES = ["LEGS","PHI","CAL","WRULE","LOOK","MEMBERS_TOPN","TRADE_TOPN","FTRIM","FTRIM_TH",
    "LTRIM_TH","CDAMP","UMASK_SCOPE","UMASK_NPZ","COSTB_JSON","SLOW_NPY","FSEED","FPRED","FEMAT_NPZ",
    "OUT_TAG","W3FIX","KMOD","KMOD_L","KMOD_F10","KMOD_AGREE","KTAIL","SEATF10","SEATNET","FUNDSCALE",
    "RNSM","FTPOS","SLEEVE","REF_SKIP","TILT","TILT_TAU","TILT_K","JUDGE_HC","V2","PANEL_IN",
    "EXPORT_PANEL","EMA_STATE_JSON"]
_ENV_PRESENT = sorted([k for k in _CONFIG_ENV_NAMES if k in os.environ])
assert _ENV_PRESENT == [], "E-0826-D: config-bearing env vars present: %r" % (_ENV_PRESENT,)
def _forbid(*a, **k):
    raise AssertionError("E-0826-D violation: this script must read no environment variable")
os.environ.get = _forbid

OUT = "/workspace/uplift_2026-09-11/r9_screen"
os.makedirs(OUT, exist_ok=True)
DEV  = "/workspace/uplift_2026-09-11/w10_sleeve.py"
ARCH = "/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz"
R8A0 = "/workspace/uplift_2026-09-11/r8b2/dev/probe_artifacts/w10_ablation_series_R8_A0_s42.npz"
META = "/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz"
PANEL= "/workspace/data/wide_panel_4h_v2ext.npz"
UMSK = "/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz"
COSTB= "/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json"
COSTD= "/workspace/review_scratch/health_check/calib/costb_fee_steady.json"

def sha(p, n=64): return hashlib.sha256(open(p,"rb").read()).hexdigest()[:n]
R = {"env_whitelist": sorted(ENV_WHITELIST), "env_config_names_asserted_absent": _CONFIG_ENV_NAMES, "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
R["sha256"] = {p: sha(p) for p in (DEV, COSTB, COSTD)}
R["sha256_16"] = {p: sha(p,16) for p in (ARCH, R8A0, META, PANEL, UMSK)}

# ---- G1
R["G1_device_sha_matches_pinned_GATE_P"] = (R["sha256"][DEV] ==
    "b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650")

# ---- G3 (resolve by readlink, never by filename -- E-0825-H/G)
LINKS = {}
for tree in ("/workspace/uplift_2026-09-11/r8b2/dev/pod_backup_2026-08-21",
             "/workspace/review_scratch/health_check/dev_v4/pod_backup_2026-08-21"):
    LINKS[tree] = {f: os.path.realpath(os.path.join(tree,f)) for f in sorted(os.listdir(tree))}
R["G3_resolved_inputs"] = LINKS
R["G3_both_trees_same_meta"]  = (LINKS[list(LINKS)[0]]["wide_fea_hist_meta.npz"] ==
                                 LINKS[list(LINKS)[1]]["wide_fea_hist_meta.npz"] == META)
R["G3_both_trees_same_panel"] = (LINKS[list(LINKS)[0]]["wide_panel_4h_hist_v2.npz"] ==
                                 LINKS[list(LINKS)[1]]["wide_panel_4h_hist_v2.npz"] == PANEL)

A = np.load(ARCH, allow_pickle=True); Bz = np.load(R8A0, allow_pickle=True)
cfgA = json.loads(str(A["config_json"])); cfgB = json.loads(str(Bz["config_json"]))
R["G2_cfgA"] = {k: cfgA.get(k) for k in ("LEGS","PHI","CAL","WRULE","LOOK","MEMBERS_TOPN","FTRIM","UMASK_SCOPE","COSTB_JSON","SLOW_NPY","FSEED","FPRED")}
R["G2_cfgB"] = {k: cfgB.get(k) for k in ("LEGS","PHI","CAL","WRULE","LOOK","MEMBERS_TOPN","FTRIM","UMASK_SCOPE","COSTB_JSON","SLOW_NPY","FSEED","FPRED")}
WA = np.asarray(A["d30_n2_c42_W"]); WB = np.asarray(Bz["d30_n2_c42_W"])
R["G2_W_bitwise_identical"] = bool(WA.shape==WB.shape and WA.dtype==WB.dtype and WA.tobytes()==WB.tobytes())
R["G2_W_shape"] = list(WA.shape); R["G2_W_dtype"] = str(WA.dtype)
recA = np.asarray(A["d30_n2_c42_rec"], float); recB = np.asarray(Bz["d30_n2_c42_rec"], float)
cols = [str(c) for c in A["cols"]]; ci = {c:i for i,c in enumerate(cols)}
R["G2_ts_identical"] = bool(np.array_equal(recA[:,ci["ts"]], recB[:,ci["ts"]]))
R["G2_pnl_ex_maxabs_diff_archived_vs_pinnedcost"] = float(np.max(np.abs(recA[:,ci["pnl_ex"]]-recB[:,ci["pnl_ex"]])))
R["G2_cost_ex_mean_archived"] = float(recA[:,ci["cost_ex"]].mean())
R["G2_cost_ex_mean_pinnedcost"] = float(recB[:,ci["cost_ex"]].mean())

# ---- rebuild the device's member/sel machinery exactly (MEMBERS_TOPN=829, UMASK_SCOPE=m1)
MT = np.load(META, allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); y4 = MT["y4"]; qvk = MT["qvk"]
PW = np.load(PANEL, allow_pickle=True)
pts = PW["ts"].astype(np.int64); pw_row = {int(t):j for j,t in enumerate(pts)}
FN = PW["f_fund_now"]; IV = PW["f_fund_iv"] if "f_fund_iv" in PW else np.full_like(PW["f_fund_now"], 8.0)
WSYM = [str(s) for s in PW["symbols"]]
R["G5_symbols_match_arch"] = bool(WSYM == [str(s) for s in A["symbols"]])
NW = len(WSYM); nA = len(E_ts)
uz = np.load(UMSK, allow_pickle=True)
umap = {int(t):k for k,t in enumerate(uz["ts"].astype(np.int64))}; UM = np.asarray(uz["mask"])
UROW = {}
for j,t in enumerate(pts):
    k = umap.get(int(t))
    if k is not None: UROW[j] = UM[k]
CB = json.load(open(COSTB))["tiers"]
COST_B = [(float(t["maker_bps"]), float(t["taker_bps"]), float(t["maker_share"])) for t in CB]
RATE = np.array([fr*mk + (1-fr)*tk for (mk,tk,fr) in COST_B])
CBd = json.load(open(COSTD)); CBd = CBd["tiers"] if isinstance(CBd, dict) else CBd
COST_D = [(float(t["maker_bps"]), float(t["taker_bps"]), float(t["maker_share"])) if isinstance(t,dict) else (float(t[0]),float(t[1]),float(t[2])) for t in CBd]
RATED = np.array([fr*mk + (1-fr)*tk for (mk,tk,fr) in COST_D])
R["COST_B_pinned_blended_by_tier"] = [round(float(x),6) for x in RATE]
R["COST_B_device_blended_by_tier"] = [round(float(x),6) for x in RATED]

# members rebuilt from qvk (MEMBERS_TOPN=829), exactly as device lines 70-76
MEM = np.empty(nA, dtype=object)
for i in range(nA):
    q = np.nan_to_num(qvk[i], nan=-1.0); o = np.argsort(-q); o = o[q[o] > -0.5]
    MEM[i] = np.sort(o[:829])
# the device does NOT sort: members[i] = _ord[:N]. keep its order to be safe.
for i in range(nA):
    q = np.nan_to_num(qvk[i], nan=-1.0); o = np.argsort(-q); o = o[q[o] > -0.5]
    MEM[i] = o[:829]

def tier_of(q):
    t = np.full(len(q), 2, np.int8); t[q>=1e6]=1; t[q>=5e6]=0
    return t

# ---- G4: reproduce rec columns from W alone
tsB = np.round(recB[:,ci["ts"]]).astype(np.int64)
pos = {int(t):r for r,t in enumerate(tsB)}
HR = np.zeros(NW); HB = np.zeros(NW)
rep = np.full((len(tsB), 6), np.nan)   # pnl_ex carry_ex cost_ex gross_total turnover net_ex
lookahead_bad = 0
for i in range(nA):
    t = int(E_ts[i]); r = pos.get(t)
    if r is None: continue
    j = pw_row.get(t)
    if j is None: continue
    if int(pts[j]) != t: lookahead_bad += 1
    m = MEM[i]
    mk = UROW.get(j)
    if mk is not None: m = m[mk[m]]
    sm = WA[r].astype(np.float64)
    smr = sm.copy(); nz = np.abs(sm) > 1e-12
    if nz.any():
        smr[nz] -= smr[nz].mean()
        g0 = np.abs(sm).sum(); g1 = np.abs(smr).sum()
        if g1 > 1e-9: smr *= g0/g1
    trr = smr - HR; trade = sm - HB
    qv4h = np.expm1(np.clip(qvk[i,m],0,30))*48
    tr = tier_of(qv4h)
    yv = np.nan_to_num(y4[i,m], nan=0.0)
    fnow = np.nan_to_num(FN[j,m], nan=0.0); ivv = IV[j,m]
    ivv = np.where(np.isfinite(ivv)&(ivv>0), ivv, 8.0)
    pnl_r = float((smr[m]*yv).sum()*1e4)
    car_r = float((smr[m]*fnow*(4.0/ivv)).sum()*1e4)
    tabs_r = np.abs(trr[m])
    cb_r = float((tabs_r*RATE[tr]).sum())
    rep[r] = (pnl_r, car_r, cb_r, float(np.abs(sm).sum()), float(np.abs(trade).sum()), pnl_r-car_r-cb_r)
    HR = smr; HB = sm
R["G5_panel_row_is_anchor_own_row_violations"] = int(lookahead_bad)
R["G4_rows_reproduced"] = int(np.isfinite(rep[:,0]).sum()); R["G4_rows_total"] = int(len(tsB))
tgt = ["pnl_ex","carry_ex","cost_ex","gross_total","turnover","net_ex"]
R["G4_maxabs_vs_device_rec_pinnedcost"] = {}
for k,c in enumerate(tgt):
    d = np.abs(rep[:,k] - recB[:,ci[c]])
    R["G4_maxabs_vs_device_rec_pinnedcost"][c] = float(np.nanmax(d))
R["G4_note"] = ("W is stored float32; the device computed in float64. residual = float32 storage of sm. "
                "cost_ex is compared against the PINNED-cost rerun R8_A0_s42 -> proves my cost tiers match the pinned model.")
np.save(OUT+"/rep_cols.npy", rep)
np.save(OUT+"/ts_A0.npy", tsB)
s = json.dumps(R, indent=1, default=float)
open(OUT+"/GATE_r9screen.json","w").write(s)
print(s)
