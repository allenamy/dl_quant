"""R10 SCREEN -- TSMOM_DIR: per-name time-series trend as a DIRECTIONAL book, merged at the BOOK layer.
SCREEN ONLY. No judge verdict. No deployment claim. ZERO live touch.

ENV WHITELIST (E-0826-D) = EMPTY SET.  This is an analysis script: it reads pinned artifacts and
computes.  It asserts that NONE of the device env knobs is present, so no knob can silently change
what it measures.

PINS (v4 chain 2026-09-09, per CALIBER_PIN_v4_2026-09-11.md):
  META  /workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz     (RAW accounting y4, axis 10182)
  A0    /workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz
  PANEL /workspace/data/wide_panel_4h_v2ext.npz                              (f_fund_now, f_fund_iv -> CARRY)
  COSTB /workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json                (fitted, G=$230k)
FORBIDDEN and not touched: any _ext 5m cache, pod_fea_ext.py, clipped-compound accounting,
pod_legs_ext.py, shadow_bundle_v3, wide_fea_v2ext_meta, expm1 on the pod 5m lineage.
NOTE: y4 here is SUM of 5-minute SIMPLE returns (E-0904-F). No expm1 is applied anywhere below.
"""
import os, json, hashlib, time, sys
_F = ("LEGS","CAL","WRULE","LOOK","PHI","UMASK_NPZ","UMASK_SCOPE","FSEED","FPRED","COSTB_JSON",
      "MEMBERS_TOPN","FTRIM","SLOW_NPY","W3FIX","FEMAT_NPZ","OUT_TAG","SLEEVE","SEATNET","CDAMP",
      "KMOD","KMOD_F10","KMOD_L","KMOD_AGREE","SEATF10","KTAIL","FUNDSCALE","TRADE_TOPN","RNSM",
      "FTPOS","LTRIM_TH","FTRIM_TH","REF_SKIP","PANEL","EXPORT_PANEL","EMA_STATE_JSON")
_bad = [k for k in _F if k in os.environ]
assert not _bad, "E-0826-D env violation: %r" % _bad
import numpy as np
from scipy.stats import spearmanr

OUT = "/workspace/uplift_2026-09-11/r10_tsmom"
os.makedirs(OUT, exist_ok=True)
META  = "/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz"
A0P   = "/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz"
PANEL = "/workspace/data/wide_panel_4h_v2ext.npz"
COSTB = "/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json"
CAP   = 1788120000      # 2026-08-30 20:00Z (E-0911-D)
WARM  = 900             # drop first 900 device anchors (E-0911-A)
QVMIN = 250000.0        # live gate, ~/wide_shadow/shadow_bundle/config.json L1449 "qv4h_min"

def sha(p):
    h = hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda: f.read(1<<22), b""): h.update(b)
    return h.hexdigest()
SHAS = {k: sha(v) for k,v in dict(META=META, A0=A0P, PANEL=PANEL, COSTB=COSTB).items()}
for k,v in SHAS.items(): print("SHA256 %-6s %s" % (k, v), flush=True)

# ---------------------------------------------------------------- load pins
m = np.load(META, allow_pickle=True)
E_ts = m["E_ts"].astype(np.int64); Y = m["y4"].astype(np.float64); QV = m["qvk"].astype(np.float64)
members = m["members"]; T, N = Y.shape
assert T == 10182, T
PW = np.load(PANEL, allow_pickle=True)
pts = PW["ts"].astype(np.int64); FN = PW["f_fund_now"].astype(np.float64); IVr = PW["f_fund_iv"].astype(np.float64)
assert FN.shape[1] == N
pw_row = {int(t): j for j, t in enumerate(pts)}
CB = json.load(open(COSTB))
RATE = np.array([t["maker_share"]*t["maker_bps"] + (1-t["maker_share"])*t["taker_bps"] for t in CB["tiers"]])
print("COSTB blended bps/unit turnover per tier (recomputed by me):", np.round(RATE,4),
      " file says:", CB["blended_bps_per_unit_turnover"], flush=True)

A = np.load(A0P, allow_pickle=True); cols = [str(c) for c in A["cols"]]; ci = {c:i for i,c in enumerate(cols)}
REC = {"d30": np.asarray(A["d30_n2_c42_rec"], float), "S0": np.asarray(A["S0_rec"], float)}
WMAT = np.asarray(A["d30_n2_c42_W"], float)
a_ts = REC["d30"][:, ci["ts"]].astype(np.int64)
keep = (np.arange(len(a_ts)) >= WARM) & (a_ts <= CAP)
ts_k = a_ts[keep]; NW = int(keep.sum())
print("window n =", NW, flush=True)
assert NW == 9138, NW
pos = {int(t): i for i, t in enumerate(E_ts)}
IDX = np.array([pos[int(t)] for t in ts_k])
JDX = np.array([pw_row[int(t)] for t in ts_k])
A0 = {k: REC[k][keep, ci["net_ex"]]/REC[k][keep, ci["gross_total"]] for k in REC}
A0NL = REC["d30"][keep, ci["netlong"]]

def ann(x):
    s = float(np.std(x, ddof=1))
    return float(np.mean(x)/s*np.sqrt(2190)) if s > 0 else float("nan")

# ------------------------------------------- GATE A: second-instrument alignment / no-lookahead
# The device computes pnl_raw = 1e4 * sum(sm[m] * y4[i,m]).  If I can reproduce rec["pnl"] from the
# SAVED weight matrix and the SAME y4 rows, then y4[t] is unambiguously the FORWARD return earned by
# weights decided at E_t -- which is the alignment every arm below relies on.
pnl_dev = REC["d30"][keep, ci["pnl"]]
Yz_all = np.where(np.isfinite(Y), Y, 0.0)
pnl_me = 1e4*np.einsum("ij,ij->i", WMAT[keep], Yz_all[IDX])
GATEA = float(np.max(np.abs(pnl_me - pnl_dev)))
print("GATE A  max|pnl_me - pnl_device| = %.3e bps  (n=%d)" % (GATEA, NW), flush=True)
# and the same for carry, which also pins the panel row mapping
IVf = np.where(np.isfinite(IVr) & (IVr > 0), IVr, 8.0)
FNz = np.nan_to_num(FN, nan=0.0)
MEMB = np.zeros((T, N), bool)
for t in range(T):
    mm = members[t]
    if mm is not None and len(mm): MEMB[t, np.asarray(mm, dtype=int)] = True
car_dev = REC["d30"][keep, ci["carry"]]
car_me = 1e4*np.array([float((WMAT[keep][i][MEMB[IDX[i]]] * FNz[JDX[i]][MEMB[IDX[i]]]
                              * (4.0/IVf[JDX[i]][MEMB[IDX[i]]])).sum()) for i in range(NW)])
GATEA2 = float(np.max(np.abs(car_me - car_dev)))
print("GATE A2 max|carry_me - carry_device| = %.3e bps" % GATEA2, flush=True)

# ---------------------------------------------------------------- eligibility
QV4H = np.expm1(np.clip(QV, 0, 30))*48.0     # qvk is a log quote-volume; this is the device's own
                                             # transform (w10 L473-474 / shadow_loop_v3 L473) -- NOT
                                             # the E-0904-F forbidden expm1, which is about y4.
FIN = np.isfinite(Y)
ELIG = MEMB & FIN & (QV4H >= QVMIN)
print("mean eligible names/anchor:", round(float(ELIG[IDX].sum(1).mean()),1), flush=True)

def trail_sum(k):
    S = np.zeros((T,N)); C = np.zeros((T,N))
    for j in range(1, k+1):
        S[j:] += Yz_all[:T-j]; C[j:] += FIN[:T-j]
    return S, C

# ---------------------------------------------------------------- the book
TIER = np.full((T,N), 2, np.int8); TIER[QV4H >= 1e6] = 1; TIER[QV4H >= 5e6] = 0
MKT = np.array([float(np.nanmean(np.where(ELIG[t], Y[t], np.nan))) if ELIG[t].any() else 0.0 for t in range(T)])

def build(score, valid, ema=1.0, minn=20):
    """w_t = ema*w_raw + (1-ema)*w_{t-1}, renormalised to sum|w|=1.  Directional: no demean."""
    Wb = np.zeros((NW, N)); prev = np.zeros(N)
    for ii in range(NW):
        t = IDX[ii]
        e = ELIG[t] & valid[t] & np.isfinite(score[t])
        n = int(e.sum())
        if n < minn:
            Wb[ii] = prev; continue
        raw = np.zeros(N); raw[e] = score[t, e]
        aw = np.abs(raw).sum()
        if aw <= 0: Wb[ii] = prev; continue
        raw = raw/aw
        w = ema*raw + (1.0-ema)*prev
        aw2 = np.abs(w).sum()
        if aw2 > 0: w = w/aw2
        Wb[ii] = w; prev = w
    return Wb

def account(Wb):
    """Returns per-anchor bps per unit gross.  gross_total = sum|w| = 1 by construction."""
    pnl = 1e4*np.einsum("ij,ij->i", Wb, Yz_all[IDX])
    car = 1e4*np.array([float((Wb[i]*FNz[JDX[i]]*(4.0/IVf[JDX[i]])).sum()) for i in range(NW)])
    dW = np.abs(np.diff(Wb, axis=0, prepend=np.zeros((1,N))))
    cst = np.array([float((dW[i]*RATE[TIER[IDX[i]]]).sum()) for i in range(NW)])
    tno = dW.sum(1)
    netlong = Wb.sum(1)/np.maximum(np.abs(Wb).sum(1), 1e-12)
    return dict(pnl=pnl, carry=car, cost=cst, net=pnl-car-cst, turn=tno, netlong=netlong)

# ---------------------------------------------------------------- bootstrap machinery
DAY = (ts_k//86400).astype(np.int64)
UD  = np.unique(DAY); DIDX = [np.where(DAY==d)[0] for d in UD]
def boot(fn, B=2000, base=20260905):
    out = np.empty(B)
    for b in range(B):
        rng = np.random.default_rng([base, b])
        pick = rng.integers(0, len(UD), len(UD))
        sel = np.concatenate([DIDX[p] for p in pick])
        out[b] = fn(sel)
    return out
def ci(v): return [float(np.percentile(v,2.5)), float(np.percentile(v,97.5))]

# ---------------------------------------------------------------- arms (declared before any number)
ARMS = []
for L in (12, 42, 90):
    S, C = trail_sum(L)
    sc = np.sign(S); val = C >= max(int(0.7*L), 8)
    for a, an in ((1.0,"raw"), (0.1,"ema10")):
        ARMS.append(("TSMOM_L%d_%s" % (L, an), sc, val, a))
PRIMARY = "TSMOM_L42_raw"       # the surveyor's exact object
K_DECLARED = len(ARMS)
print("K declared =", K_DECLARED, "primary =", PRIMARY, flush=True)

RES = {}
CACHE = {}
for nm, sc, val, a in ARMS:
    Wb = build(sc, val, ema=a); R = account(Wb); CACHE[nm] = (Wb, R)
    g = R["net"]
    mb = boot(lambda s: float(g[s].mean()))
    RES[nm] = dict(
        gross_price_g=float(R["pnl"].mean()), carry_g=float(R["carry"].mean()),
        cost_g=float(R["cost"].mean()), net_g=float(g.mean()),
        net_CI95=ci(mb), SR_net=ann(g), SR_gross_price=ann(R["pnl"]),
        SR_before_cost=ann(R["pnl"]-R["carry"]),
        turnover=float(R["turn"].mean()),
        cost_survival_pct=float(100.0*g.mean()/R["pnl"].mean()) if R["pnl"].mean()!=0 else float("nan"),
        netlong_mean=float(R["netlong"].mean()), netlong_absmean=float(np.abs(R["netlong"]).mean()),
        rho_A0=float(np.corrcoef(g, A0["d30"])[0,1]),
        spearman_A0=float(spearmanr(g, A0["d30"]).statistic))
    print("%-18s netg %+8.4f CI[%+7.4f,%+7.4f] SRnet %+6.3f | price %+7.4f carry %+7.4f cost %7.4f turn %6.4f | rho %+6.3f netlong %+6.3f"
          % (nm, RES[nm]["net_g"], RES[nm]["net_CI95"][0], RES[nm]["net_CI95"][1], RES[nm]["SR_net"],
             RES[nm]["gross_price_g"], RES[nm]["carry_g"], RES[nm]["cost_g"], RES[nm]["turnover"],
             RES[nm]["rho_A0"], RES[nm]["netlong_mean"]), flush=True)

json.dump(dict(shas=SHAS, window_n=NW, K_declared=K_DECLARED, primary=PRIMARY,
               GATE_A_pnl_maxabs=GATEA, GATE_A2_carry_maxabs=GATEA2,
               costb_rates_recomputed=list(np.round(RATE,6)),
               A0=dict(d30_mean_g=float(A0["d30"].mean()), d30_SR=ann(A0["d30"]),
                       S0_mean_g=float(A0["S0"].mean()), S0_SR=ann(A0["S0"]),
                       netlong_mean=float(A0NL.mean())),
               arms=RES, env_whitelist=[]),
          open(OUT+"/STEP13.json","w"), indent=1)
print("wrote", OUT+"/STEP13.json", flush=True)
np.savez_compressed(OUT+"/series.npz", ts=ts_k, a0_d30=A0["d30"], a0_S0=A0["S0"], a0_netlong=A0NL,
                    mkt=MKT[IDX],
                    **{("%s_%s"%(nm,k)): v for nm,(Wb,R) in CACHE.items() for k,v in R.items()})
print("wrote", OUT+"/series.npz", flush=True)
