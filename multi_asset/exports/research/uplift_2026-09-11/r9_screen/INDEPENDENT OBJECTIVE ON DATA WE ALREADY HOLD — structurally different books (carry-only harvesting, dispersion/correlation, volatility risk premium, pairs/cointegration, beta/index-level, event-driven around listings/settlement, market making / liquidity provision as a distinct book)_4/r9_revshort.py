"""R9 SCREEN -- REV_SHORT (short-horizon cross-sectional reversal) as a STANDALONE book.
INDEPENDENT RE-MEASUREMENT. Not a judge verdict, not a candidate, no deployment claim.
ENV WHITELIST (E-0826-D) = EMPTY SET -- this device reads NO environment variable.

Caliber pin v4 (2026-09-09):
  accounting matrix : /workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz  (RAW y4)
  A0 reference      : /workspace/uplift_2026-09-11/r3k/arms/A0_PWR230k_s42.npz          (the arm that
                      produces the brief's +0.6342 / SR 1.2912 planning number; fitted PWR cost)
  cost              : /workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json (tiered, per-name)
  CAL=log  => y4 used RAW, NO expm1 (E-0904-F).  Eligibility gate copied from w10_universe.py L198-199.
  window            : drop first 900 device anchors (E-0911-A); ts <= 2026-08-30 20:00Z (E-0911-D).
  statistic         : g = net / gross, bps per 4h anchor per unit gross.  Book has sum|w| = 1 so
                      gross_total == 1 by construction and g == net bps directly.
  bootstrap         : UTC-day block, B=2000, numpy.default_rng([20260905, k]).
Carry (funding) is EXCLUDED from the candidate: y4 is price only.  Stated, not hidden.
"""
import os, sys, json, hashlib, time, calendar
ENV_SEEN = sorted(os.environ.keys())
_FORBID = ("LEGS","CAL","WRULE","LOOK","PHI","UMASK_NPZ","UMASK_SCOPE","FSEED","FPRED","COSTB_JSON",
           "MEMBERS_TOPN","FTRIM","SLOW_NPY","W3FIX","FEMAT_NPZ","OUT_TAG","TRADE_TOPN","TILT",
           "KMOD","KMOD_F10","KMOD_AGREE","KTAIL","SEATF10","SEATNET","FUNDSCALE","REF_SKIP")
_viol = [k for k in _FORBID if k in os.environ]
assert not _viol, "E-0826-D env violation: %r" % _viol
import numpy as np
from scipy.stats import rankdata, spearmanr

def T(*a): return calendar.timegm(a + (0,)*(6-len(a)))
def sha(p):
    h = hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda: f.read(1<<22), b""): h.update(b)
    return h.hexdigest()

U    = "/workspace/uplift_2026-09-11"
META = "/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz"
A0P  = U + "/r3k/arms/A0_PWR230k_s42.npz"
CBJ  = U + "/r3k/costb_PWR_G230k.json"
CUT  = T(2026,8,30,20); WARM = 900; B = 2000; APY = 2190.0
assert CUT == 1788120000, CUT

R = {"device": os.path.abspath(__file__), "self_sha256": sha(os.path.abspath(__file__)),
     "env_whitelist": [], "env_seen_at_runtime": ENV_SEEN,
     "numpy": np.__version__, "python": sys.version.split()[0],
     "inputs": {k: {"path": p, "sha256": sha(p)} for k,p in
                (("meta_newprod_v4",META),("A0_PWR230k_s42",A0P),("costb_PWR_G230k",CBJ))},
     "cut_epoch": CUT, "warm_drop": WARM, "B": B}

# ---------------------------------------------------------------- cost model (pinned, tiered)
CB = json.load(open(CBJ))
RATE = np.array(CB["blended_bps_per_unit_turnover"], float)     # [tier0, tier1, tier2]
BOOKAVG = float(CB["book_avg_bps_per_unit_turnover"])
R["cost"] = {"blended_bps_per_unit_turnover": RATE.tolist(), "book_avg": BOOKAVG,
             "tier_edges_qv4h": [5e6, 1e6], "model": CB["model"]}

# ---------------------------------------------------------------- load accounting matrix
m = np.load(META, allow_pickle=True)
E_ts = m["E_ts"].astype(np.int64); Y = m["y4"].astype(np.float64)
QV = m["qvk"].astype(np.float64); members = m["members"]
Tn, N = Y.shape
R["meta"] = {"shape_y4": [int(Tn), int(N)], "E_ts_first": int(E_ts[0]), "E_ts_last": int(E_ts[-1]),
             "axis_len": int(Tn), "monotone_4h": bool(np.all(np.diff(E_ts) == 14400))}

# ---------------------------------------------------------------- A0 reference series
a = np.load(A0P, allow_pickle=True)
cols = [str(c) for c in a["cols"]]; ci = {c:i for i,c in enumerate(cols)}
KEY = "rec" if "rec" in a.files else "d30_n2_c42_rec"
rec = np.asarray(a[KEY], float)[WARM:]
a_ts = np.round(rec[:, ci["ts"]]).astype(np.int64)
msk = a_ts <= CUT
a_ts = a_ts[msk]
gA0 = rec[msk, ci["net_ex"]] / rec[msk, ci["gross_total"]]
NW = len(gA0)
def ann(x):
    s = np.std(x, ddof=1); return float(np.mean(x)/s*np.sqrt(APY)) if s > 0 else float("nan")
R["A0"] = {"key": KEY, "n": int(NW), "mean_g": round(float(gA0.mean()),4), "SR": round(ann(gA0),4),
           "span": [time.strftime("%Y-%m-%d %HZ", time.gmtime(int(a_ts[0]))),
                    time.strftime("%Y-%m-%d %HZ", time.gmtime(int(a_ts[-1])))]}
print("A0  n=%d  mean_g=%+.4f  SR=%+.4f" % (NW, gA0.mean(), ann(gA0)), flush=True)

pos = {int(t): i for i, t in enumerate(E_ts)}
IDX = np.array([pos[int(t)] for t in a_ts])
assert np.array_equal(E_ts[IDX], a_ts), "anchor axis mismatch"
R["axis_alignment"] = "E_ts[IDX] == A0 ts, bitwise"

# ---------------------------------------------------------------- eligibility (w10_universe L198-199)
MEMB = np.zeros((Tn, N), bool)
for t in range(Tn):
    mm = members[t]
    if mm is not None and len(mm): MEMB[t, np.asarray(mm, dtype=int)] = True
QV4H = np.expm1(np.clip(QV, 0, 30)) * 48.0        # verbatim w10_universe.py L198
ELIG = MEMB & np.isfinite(Y) & (QV4H >= 2.5e5)
TIER = np.where(QV4H >= 5e6, 0, np.where(QV4H >= 1e6, 1, 2)).astype(np.int8)
R["eligibility"] = {"rule": "member AND isfinite(y4) AND qv4h>=2.5e5 ; qv4h=expm1(clip(qvk,0,30))*48 "
                            "(verbatim w10_universe.py L198-199)",
                    "mean_eligible_names_per_anchor": round(float(ELIG[IDX].sum(1).mean()), 2)}
print("eligible names/anchor:", R["eligibility"]["mean_eligible_names_per_anchor"], flush=True)

# ---------------------------------------------------------------- STEP 1  causality
Yz = np.where(np.isfinite(Y), Y, 0.0); FIN = np.isfinite(Y)
def make_score(Ysrc, FINsrc):
    """score[t] = -y4[t-1].  Row t reads ONLY row t-1.  Rank book => subtracting any per-anchor
    scalar (market mean) is a no-op on ranks, so it is omitted and that is asserted below."""
    S = np.full((Tn, N), np.nan)
    S[1:] = -Ysrc[:Tn-1]
    V = np.zeros((Tn, N), bool); V[1:] = FINsrc[:Tn-1]
    return S, V
SCORE, VALID = make_score(Y, FIN)

# (1a) INTERVENTIONAL leak test: blank every row >= c, rebuild, require bitwise-identical scores at t<=c
rng0 = np.random.default_rng([20260905, 777])
cuts = sorted(rng0.choice(np.arange(1200, Tn-5), size=24, replace=False).tolist())
bad = []
for c in cuts:
    Yc = Y.copy(); Yc[c:] = np.nan
    Fc = np.isfinite(Yc); Yzc = np.where(Fc, Yc, 0.0)
    Sc, Vc = make_score(Yc, Fc)
    A = SCORE[:c+1]; Bm = Sc[:c+1]
    same = np.array_equal(np.nan_to_num(A, nan=-9e99), np.nan_to_num(Bm, nan=-9e99))
    if not same: bad.append(int(c))
R["leak_interventional"] = {"cuts_tested": len(cuts), "cuts_failing": bad,
    "rule": "blank all rows >= c, rebuild score, require bitwise-identical score rows 0..c",
    "PASS": len(bad) == 0}
print("interventional leak test: %d cuts, %d failures" % (len(cuts), len(bad)), flush=True)

# (1b) offset spectrum (secondary; k=-1 is -1.0 by construction = alignment self-check)
OFF = {}
for k in range(-3, 4):
    ics = []
    for ii in range(0, NW, 3):
        t = IDX[ii]; tt = t + k
        if tt < 0 or tt >= Tn: continue
        e = ELIG[t] & VALID[t] & np.isfinite(SCORE[t]) & np.isfinite(Y[tt])
        if e.sum() < 20: continue
        ics.append(spearmanr(SCORE[t, e], Y[tt, e]).statistic)
    ics = np.array(ics); ics = ics[np.isfinite(ics)]
    OFF["k%+d" % k] = {"IC": round(float(ics.mean()), 5),
                       "t": round(float(ics.mean()/ics.std(ddof=1)*np.sqrt(len(ics))), 2),
                       "n": int(len(ics))}
R["leak_offset_spectrum"] = OFF
print("offset spectrum:", json.dumps(OFF), flush=True)

# ---------------------------------------------------------------- book construction
def targets(tier_max=None):
    W = np.zeros((NW, N))
    for ii in range(NW):
        t = IDX[ii]
        e = ELIG[t] & VALID[t] & np.isfinite(SCORE[t])
        if tier_max is not None: e = e & (TIER[t] <= tier_max)
        n = int(e.sum())
        if n < 20: continue
        r = rankdata(SCORE[t, e])/(n+1.0) - 0.5
        w = r - r.mean()
        s = np.abs(w).sum()
        if s > 0: W[ii, e] = w/s
    return W

def run(Wt, alpha=1.0, band=0.0, cap=None):
    """alpha=1,band=0 -> jump to target. alpha=0.1,band=2.5e-4,cap=2.5/n = the LIVE book chain."""
    gg = np.zeros(NW); tn = np.zeros(NW); cc = np.zeros(NW); held = np.zeros(N)
    for ii in range(NW):
        t = IDX[ii]; tgt = Wt[ii].copy()
        if cap is not None:
            nz = np.abs(tgt) > 0
            k = int(nz.sum())
            if k: 
                tgt = np.clip(tgt, -cap/k, cap/k)
                s = np.abs(tgt).sum()
                if s > 0: tgt = tgt/s
        if alpha >= 1.0 and band <= 0: new = tgt
        else:
            sm = held + alpha*(tgt - held)
            tr = sm - held
            sm = np.where(np.abs(tr) < band, held, sm)
            new = sm
        s = np.abs(new).sum()
        if s > 0: new = new/s
        d = np.abs(new - held)
        tn[ii] = d.sum()
        cc[ii] = float((d * RATE[TIER[t]]).sum())
        gg[ii] = 1e4*float(np.nansum(new * np.where(np.isfinite(Y[t]), Y[t], 0.0)))
        held = new
    return gg, tn, cc

# ---------------------------------------------------------------- bootstrap machinery
DAY = a_ts // 86400
ud, inv = np.unique(DAY, return_inverse=True); nd = len(ud)
order = np.argsort(inv, kind="stable")
st = np.searchsorted(inv[order], np.arange(nd)); en = np.append(st[1:], len(order))
def boot(fn, seed):
    rng = np.random.default_rng([20260905, seed])
    pick = rng.integers(0, nd, size=(B, nd)); out = np.empty(B)
    for b in range(B):
        ii = np.concatenate([order[st[j]:en[j]] for j in pick[b]])
        out[b] = fn(ii)
    return out
def ci(v):
    v = v[np.isfinite(v)]
    return [round(float(np.percentile(v,2.5)),4), round(float(np.percentile(v,97.5)),4)]

# ---------------------------------------------------------------- STEP 2/3  main arm + shapes
def report(tag, gg, tn, cc, do_boot=True, seed=1):
    net = gg - cc
    out = {"gross_bps": round(float(gg.mean()),4), "turnover": round(float(tn.mean()),4),
           "cost_bps": round(float(cc.mean()),4), "net_bps": round(float(net.mean()),4),
           "breakeven_bps_per_unit_turnover": round(float(gg.mean()/tn.mean()),4) if tn.mean()>0 else None,
           "eff_cost_rate_bps_per_unit_turnover": round(float(cc.mean()/tn.mean()),4) if tn.mean()>0 else None,
           "SR_gross": round(ann(gg),4), "SR_net": round(ann(net),4),
           "rho_net_A0": round(float(np.corrcoef(net, gA0)[0,1]),4),
           "rho_gross_A0": round(float(np.corrcoef(gg, gA0)[0,1]),4)}
    if do_boot:
        out["net_CI95"] = ci(boot(lambda ii: net[ii].mean(), seed))
        out["rho_net_A0_CI95"] = ci(boot(lambda ii: np.corrcoef(net[ii], gA0[ii])[0,1], seed+100))
    print("%-26s gross %+8.4f  turn %7.4f  cost %7.4f  net %+8.4f  SRnet %+7.3f  rho %+7.4f  BE %7.4f"
          % (tag, gg.mean(), tn.mean(), cc.mean(), net.mean(), ann(net),
             out["rho_net_A0"], out["breakeven_bps_per_unit_turnover"] or float("nan")), flush=True)
    return out, net

WtA = targets(None)
ARMS = {}
gg, tn, cc = run(WtA, 1.0, 0.0)
ARMS["RAW_jump"], NET_MAIN = report("RAW_jump a=1", gg, tn, cc, True, 1)
GG_MAIN, TN_MAIN, CC_MAIN = gg, tn, cc

for al, bd, cp, lbl in [(0.5,0.0,None,"EMA a=0.5"), (0.25,0.0,None,"EMA a=0.25"),
                        (0.1,0.0,None,"EMA a=0.1"),
                        (0.1,2.5e-4,2.5,"LIVE chain a=0.1 cap2.5"),
                        (0.5,2.5e-4,2.5,"LIVE chain a=0.5 cap2.5"),
                        (1.0,0.0,2.5,"jump cap2.5")]:
    g2,t2,c2 = run(WtA, al, bd, cp)
    ARMS[lbl],_ = report(lbl, g2, t2, c2, False)

for tm, lbl in [(0,"tier0 only"), (1,"tier0+1 only")]:
    Wt = targets(tm); g2,t2,c2 = run(Wt, 1.0, 0.0)
    ARMS[lbl],_ = report(lbl, g2, t2, c2, False)
R["arms"] = ARMS

# ---------------------------------------------------------------- STEP 2  conditional rho
CONDS = {}
q20 = float(np.quantile(gA0, 0.20)); q10 = float(np.quantile(gA0, 0.10))
dmean = np.array([gA0[DAY==d].mean() for d in ud]); dq20 = float(np.quantile(dmean, 0.20))
dbad = np.isin(DAY, ud[dmean <= dq20])
for lbl, sel, sd in (("A0_bottom_quintile_anchors", gA0 <= q20, 11),
                     ("A0_bottom_decile_anchors",   gA0 <= q10, 12),
                     ("A0_negative_anchors",        gA0 < 0,    13),
                     ("A0_worst_quintile_UTCdays",  dbad,       14),
                     ("A0_top_quintile_anchors",    gA0 >= float(np.quantile(gA0,0.80)), 15)):
    x = NET_MAIN[sel]; y = gA0[sel]
    idxs = np.where(sel)[0]
    # day-block bootstrap restricted to the conditioning subset
    d2 = a_ts[sel]//86400; u2, i2 = np.unique(d2, return_inverse=True); n2 = len(u2)
    o2 = np.argsort(i2, kind="stable"); s2 = np.searchsorted(i2[o2], np.arange(n2)); e2 = np.append(s2[1:], len(o2))
    rng = np.random.default_rng([20260905, sd]); pk = rng.integers(0, n2, size=(B, n2)); bb = np.empty(B)
    for b in range(B):
        jj = np.concatenate([o2[s2[j]:e2[j]] for j in pk[b]])
        bb[b] = np.corrcoef(x[jj], y[jj])[0,1] if np.std(x[jj])>0 and np.std(y[jj])>0 else np.nan
    CONDS[lbl] = {"n": int(sel.sum()), "rho": round(float(np.corrcoef(x,y)[0,1]),4), "rho_CI95": ci(bb),
                  "cand_mean_net": round(float(x.mean()),4), "A0_mean_g": round(float(y.mean()),4)}
    print("%-30s n=%5d rho=%+7.4f CI %s  cand_net=%+8.4f  A0=%+8.4f"
          % (lbl, sel.sum(), CONDS[lbl]["rho"], CONDS[lbl]["rho_CI95"],
             CONDS[lbl]["cand_mean_net"], CONDS[lbl]["A0_mean_g"]), flush=True)
R["conditional_rho"] = CONDS

# ---------------------------------------------------------------- STEP 3  turnover-matched nulls
NULLS = {}
for d in (1,2,3):
    rng = np.random.default_rng([4242, d]); pi = rng.permutation(N)
    Sp = SCORE[:, pi]; Vp = VALID[:, pi]
    Wn = np.zeros((NW, N))
    for ii in range(NW):
        t = IDX[ii]
        e = ELIG[t] & Vp[t] & np.isfinite(Sp[t]); n = int(e.sum())
        if n < 20: continue
        r = rankdata(Sp[t, e])/(n+1.0) - 0.5; w = r - r.mean(); s = np.abs(w).sum()
        if s > 0: Wn[ii, e] = w/s
    g2,t2,c2 = run(Wn, 1.0, 0.0)
    NULLS["RELAB%d" % d], _ = report("NULL RELAB%d" % d, g2, t2, c2, False)
for k in (101, 503, 1009):
    Sp = np.full_like(SCORE, np.nan); Sp[k:] = SCORE[:-k]
    Vp = np.zeros_like(VALID); Vp[k:] = VALID[:-k]
    Wn = np.zeros((NW, N))
    for ii in range(NW):
        t = IDX[ii]
        e = ELIG[t] & Vp[t] & np.isfinite(Sp[t]); n = int(e.sum())
        if n < 20: continue
        r = rankdata(Sp[t, e])/(n+1.0) - 0.5; w = r - r.mean(); s = np.abs(w).sum()
        if s > 0: Wn[ii, e] = w/s
    g2,t2,c2 = run(Wn, 1.0, 0.0)
    NULLS["SHIFT%d" % k], _ = report("NULL SHIFT%d" % k, g2, t2, c2, False)
R["nulls_turnover_matched"] = NULLS

# ---------------------------------------------------------------- per-year
yr = np.array([time.gmtime(int(t)).tm_year for t in a_ts])
NETM = GG_MAIN - CC_MAIN
R["per_year"] = {int(y): {"n": int((yr==y).sum()),
                          "gross": round(float(GG_MAIN[yr==y].mean()),4),
                          "turn": round(float(TN_MAIN[yr==y].mean()),4),
                          "net": round(float(NETM[yr==y].mean()),4),
                          "breakeven": round(float(GG_MAIN[yr==y].mean()/TN_MAIN[yr==y].mean()),4),
                          "rho_A0": round(float(np.corrcoef(NETM[yr==y], gA0[yr==y])[0,1]),4)}
                 for y in sorted(set(yr.tolist()))}
print("per_year:", json.dumps(R["per_year"]), flush=True)

# ---------------------------------------------------------------- STEP 4  combination arithmetic
sA = ann(gA0); COMB = {"A0_SR": round(sA,4), "SE_SR": round(float(np.sqrt(APY/NW)),4), "target_SR": 3.966}
for lbl, arm_net in (("RAW_jump", NETM),):
    sC = ann(arm_net); rho = float(np.corrcoef(arm_net, gA0)[0,1])
    # max-Sharpe two-asset combination
    den = 1.0 - rho*rho
    smax = float(np.sqrt(max((sA*sA + sC*sC - 2*rho*sA*sC)/den, 0.0))) if den > 1e-12 else float("nan")
    grid = {}
    for w in (0.1,0.2,0.3,0.5):
        sd = np.sqrt((1-w)**2*np.var(gA0,ddof=1) + w**2*np.var(arm_net,ddof=1)
                     + 2*w*(1-w)*rho*np.std(gA0,ddof=1)*np.std(arm_net,ddof=1))
        mu = (1-w)*gA0.mean() + w*arm_net.mean()
        grid["w=%.1f" % w] = round(float(mu/sd*np.sqrt(APY)),4)
    COMB[lbl] = {"cand_SR_net": round(sC,4), "rho": round(rho,4), "max_SR_combined": round(smax,4),
                 "SR_at_weights": grid,
                 "SR_needed_standalone_uncorrelated_to_hit_3.966":
                     round(float(np.sqrt(max(3.966**2 - sA*sA, 0.0))),4)}
R["combination"] = COMB
print("combination:", json.dumps(COMB), flush=True)

OUTP = U + "/r9_revshort/R9_REVSHORT.json"
os.makedirs(os.path.dirname(OUTP), exist_ok=True)
json.dump(R, open(OUTP, "w"), indent=1)
print("wrote", OUTP)
print("R9_DONE")
