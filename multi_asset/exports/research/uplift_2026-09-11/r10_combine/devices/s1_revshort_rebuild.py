"""r10_combine STEP 1 -- rebuild the REV_SHORT net-g series.

Why: the r9 REV_SHORT screen archived JSON only, no per-anchor series, and the
combination stage needs the SERIES (constraint: recompute correlations from the
series, do not trust reported rhos).  This device re-implements the arm exactly
as r9_revshort.py defined it (score[t] = -y4[t-1]; centred-rank book, sum|w|=1;
tiered cost on |dw|), and ASSERTS that the rebuilt arm reproduces the archived
numbers before saving anything.

ENV WHITELIST (E-0826-D) = EMPTY SET.  This device reads no environment variable
and asserts that no book-control variable is present.
Caliber pin v4 (2026-09-09): RAW y4 from meta_newprod_v4.npz, no expm1 on y4
(E-0904-F), no _ext lineage (E-0909-A), no clipped-compound accounting
(E-0908-B), no panel_source.py default panel (this device reads no panel).
"""
import os, sys, json, hashlib, calendar
ENV_SEEN = sorted(os.environ.keys())
_FORBID = ("LEGS","CAL","WRULE","LOOK","PHI","UMASK_NPZ","UMASK_SCOPE","FSEED","FPRED","COSTB_JSON",
           "MEMBERS_TOPN","FTRIM","SLOW_NPY","W3FIX","FEMAT_NPZ","OUT_TAG","TRADE_TOPN","TILT",
           "KMOD","KMOD_F10","KMOD_L","KMOD_AGREE","KTAIL","SEATF10","SEATNET","FUNDSCALE","REF_SKIP",
           "SLEEVE","CDAMP","LTRIM_TH","FTRIM_TH","RNSM","FTPOS","PANEL","PANEL_IN","EXPORT_PANEL",
           "EMA_STATE_JSON","JUDGE_HC","JUDGE_REQUIRE_W")
_v = [k for k in _FORBID if k in os.environ]
assert not _v, "E-0826-D env violation: %r" % _v
import numpy as np
from scipy.stats import rankdata

def T(*a): return calendar.timegm(a + (0,)*(6-len(a)))
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()

SCR  = "/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/scratchpad/r10c"
OUT  = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11/r10_combine"
META = SCR + "/meta_newprod_v4.npz"
A0P  = SCR + "/A0_PWR230k_s42.npz"
CBJ  = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11/r3k_impact/costb_PWR_G230k.json"
CUT  = T(2026, 8, 30, 20); WARM = 900; APY = 2190.0
assert CUT == 1788120000, CUT

R = {"step": "S1_REVSHORT_REBUILD", "self_sha256": sha(os.path.abspath(__file__)),
     "env_whitelist": [], "env_seen_at_runtime": ENV_SEEN,
     "numpy": np.__version__, "python": sys.version.split()[0],
     "inputs": {k: {"path": p, "sha256": sha(p)} for k, p in
                (("meta_newprod_v4", META), ("A0_PWR230k_s42", A0P), ("costb_PWR_G230k", CBJ))}}

CB = json.load(open(CBJ))
RATE = np.array(CB["blended_bps_per_unit_turnover"], float)

m = np.load(META, allow_pickle=True)
E_ts = m["E_ts"].astype(np.int64); Y = m["y4"].astype(np.float64)
QV = m["qvk"].astype(np.float64); members = m["members"]
Tn, N = Y.shape
R["meta"] = {"shape_y4": [int(Tn), int(N)], "monotone_4h": bool(np.all(np.diff(E_ts) == 14400))}

a = np.load(A0P, allow_pickle=True)
cols = [str(c) for c in a["cols"]]; ci_ = {c: i for i, c in enumerate(cols)}
rec = np.asarray(a["rec"], float)[WARM:]
a_ts = np.round(rec[:, ci_["ts"]]).astype(np.int64)
msk = a_ts <= CUT
a_ts = a_ts[msk]; recw = rec[msk]
gA0 = recw[:, ci_["net_ex"]] / recw[:, ci_["gross_total"]]
NW = len(gA0)
def ann(x):
    s = np.std(x, ddof=1); return float(np.mean(x)/s*np.sqrt(APY)) if s > 0 else float("nan")
R["A0"] = {"n": int(NW), "mean_g": round(float(gA0.mean()), 4), "SR": round(ann(gA0), 4)}
print("A0 n=%d mean_g=%+.4f SR=%+.4f" % (NW, gA0.mean(), ann(gA0)), flush=True)
assert NW == 9138, NW

pos = {int(t): i for i, t in enumerate(E_ts)}
IDX = np.array([pos[int(t)] for t in a_ts])
assert np.array_equal(E_ts[IDX], a_ts)

MEMB = np.zeros((Tn, N), bool)
for t in range(Tn):
    mm = members[t]
    if mm is not None and len(mm): MEMB[t, np.asarray(mm, dtype=int)] = True
QV4H = np.expm1(np.clip(QV, 0, 30)) * 48.0
ELIG = MEMB & np.isfinite(Y) & (QV4H >= 2.5e5)
TIER = np.where(QV4H >= 5e6, 0, np.where(QV4H >= 1e6, 1, 2)).astype(np.int8)
R["eligibility"] = {"rule": "member & isfinite(y4) & qv4h>=2.5e5 ; qv4h=expm1(clip(qvk,0,30))*48",
                    "mean_eligible_names_per_anchor": round(float(ELIG[IDX].sum(1).mean()), 2)}

FIN = np.isfinite(Y)
SCORE = np.full((Tn, N), np.nan); SCORE[1:] = -Y[:Tn-1]
VALID = np.zeros((Tn, N), bool); VALID[1:] = FIN[:Tn-1]

# interventional leak re-test (24 cuts, same rule/seed as r9_revshort.py)
rng0 = np.random.default_rng([20260905, 777])
cuts = sorted(rng0.choice(np.arange(1200, Tn-5), size=24, replace=False).tolist())
bad = []
for c in cuts:
    Yc = Y.copy(); Yc[c:] = np.nan
    Sc = np.full((Tn, N), np.nan); Sc[1:] = -Yc[:Tn-1]
    if not np.array_equal(np.nan_to_num(SCORE[:c+1], nan=-9e99), np.nan_to_num(Sc[:c+1], nan=-9e99)):
        bad.append(int(c))
R["leak_interventional"] = {"cuts": len(cuts), "failures": bad, "PASS": len(bad) == 0}
print("interventional leak: %d cuts, %d fail" % (len(cuts), len(bad)), flush=True)

W = np.zeros((NW, N))
for ii in range(NW):
    t = IDX[ii]
    e = ELIG[t] & VALID[t] & np.isfinite(SCORE[t])
    n = int(e.sum())
    if n < 20: continue
    r = rankdata(SCORE[t, e]) / (n + 1.0) - 0.5
    w = r - r.mean(); s = np.abs(w).sum()
    if s > 0: W[ii, e] = w / s

def run(alpha=1.0, band=0.0, cap=None):
    gg = np.zeros(NW); tn = np.zeros(NW); cc = np.zeros(NW); held = np.zeros(N)
    for ii in range(NW):
        t = IDX[ii]; tgt = W[ii].copy()
        if cap is not None:
            nz = np.abs(tgt) > 0; k = int(nz.sum())
            if k:
                tgt = np.clip(tgt, -cap/k, cap/k); s = np.abs(tgt).sum()
                if s > 0: tgt = tgt/s
        if alpha >= 1.0 and band <= 0: new = tgt
        else:
            sm = held + alpha*(tgt - held); tr = sm - held
            new = np.where(np.abs(tr) < band, held, sm)
        s = np.abs(new).sum()
        if s > 0: new = new/s
        d = np.abs(new - held)
        tn[ii] = d.sum(); cc[ii] = float((d * RATE[TIER[t]]).sum())
        gg[ii] = 1e4*float(np.nansum(new * np.where(np.isfinite(Y[t]), Y[t], 0.0)))
        held = new
    return gg, tn, cc

ARCH = {"RAW_jump":  dict(gross=1.1585, turn=1.3178, cost=3.8683, net=-2.7097, SRnet=-4.1986, rho=0.0186),
        "EMA_a0.50": dict(gross=1.2710, turn=0.7926, cost=2.3246, net=-1.0536, SRnet=-1.3986, rho=-0.0211)}
SER = {}; GATE = {}
for tag, (al, bd, cp) in (("RAW_jump", (1.0, 0.0, None)), ("EMA_a0.50", (0.5, 0.0, None))):
    gg, tn, cc = run(al, bd, cp); net = gg - cc
    got = dict(gross=float(gg.mean()), turn=float(tn.mean()), cost=float(cc.mean()),
               net=float(net.mean()), SRnet=ann(net), rho=float(np.corrcoef(net, gA0)[0, 1]))
    dd = {k: round(got[k]-ARCH[tag][k], 6) for k in ARCH[tag]}
    GATE[tag] = {"rebuilt": {k: round(v, 4) for k, v in got.items()},
                 "archived_r9": ARCH[tag], "delta": dd,
                 "PASS": all(abs(got[k]-ARCH[tag][k]) <= 5e-4 for k in ARCH[tag])}
    print("%-10s rebuilt net %+8.4f  archived %+8.4f  dmax %.2e  PASS=%s"
          % (tag, got["net"], ARCH[tag]["net"], max(abs(v) for v in dd.values()), GATE[tag]["PASS"]), flush=True)
    SER[tag] = dict(net=net, gross=gg, turn=tn, cost=cc)
R["GATE_reproduce_r9"] = GATE
assert all(v["PASS"] for v in GATE.values()), "REV_SHORT rebuild does not reproduce r9"

np.savez_compressed(OUT + "/series/REV_SHORT_rebuilt.npz", ts=a_ts, gA0=gA0,
                    **{("%s_%s" % (t, k)): v for t, d in SER.items() for k, v in d.items()})
R["saved"] = OUT + "/series/REV_SHORT_rebuilt.npz"
json.dump(R, open(OUT + "/receipts/S1_REVSHORT_REBUILD.json", "w"), indent=1)
print("OK ->", R["saved"], flush=True)
