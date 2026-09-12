#!/usr/bin/env python3
"""r13-B core - T1 FORM B: within-half beta-gap overlay on the deployed (_ex) book.

Frozen by PREREG_r13B_withinhalf_2026-09-12.md sha256 27b0d34c5c55119ba55422a212ec340b1be1bf24af6278564796480d85cbe045
which this file ASSERTS before it will run (constraint 10).

READ-ONLY. CPU ONLY. NO GPU. Live tree never touched.
"""
import os, sys, json, time, hashlib, calendar, subprocess

# ------------------------------------------------------------------ E-0826-D env whitelist
WHITE = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else None
assert WHITE, "device must be launched with an explicit env whitelist argument"
BANNED = ('CAL','JUDGE','UPLIFT','PANEL','LOOK','WRULE','LEGS','PHI','FSEED','W3FIX','FTRIM',
          'UMASK','SLOW','FPRED','MEMBERS_TOPN','COSTB','SLEEVE','KMOD','SEAT','RNSM','LTRIM',
          'CDAMP','FUNDSCALE','FEMAT','TRADE_TOPN','REF_SKIP','PYTHON','OMP','MKL')
ENV_ACTUAL = {k: os.environ[k] for k in sorted(os.environ)}
EXTRA = sorted(k for k in os.environ if k not in WHITE)
assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
BAN = sorted(k for k in os.environ if k.startswith(BANNED))
assert BAN == [], ("CALIBER FLAG PRESENT", BAN)
ENV_REPORT = dict(env_whitelist=sorted(WHITE), env_extra=EXTRA, env_actual=ENV_ACTUAL,
                  env_banned=BAN, env_banned_prefixes=sorted(BANNED),
                  launch_cmdline=" ".join(sys.argv))

import numpy as np
ENV_REPORT.update(python=sys.version.split()[0], numpy=np.__version__)

PREREG_SHA = "27b0d34c5c55119ba55422a212ec340b1be1bf24af6278564796480d85cbe045"
AMEND1_SHA = "720fa335e62463cbe81b764285e00020c08b81d70bcbf9d5f3ab54ae5098af9d"
AMEND2_SHA = "5b8bc70485784cec3aa39363d6aef62cf7570b6703809fe65a8faa68b06ea5f8"
HERE = os.path.dirname(os.path.abspath(__file__))
PRE = os.path.join(HERE, "PREREG_r13B_withinhalf_2026-09-12.md")
AM1 = os.path.join(HERE, "PREREG_AMENDMENT_1_2026-09-12.md")
AM2 = os.path.join(HERE, "PREREG_AMENDMENT_2_2026-09-12.md")
assert hashlib.sha256(open(PRE, 'rb').read()).hexdigest() == PREREG_SHA, "PREREG HASH MISMATCH"
assert hashlib.sha256(open(AM1, 'rb').read()).hexdigest() == AMEND1_SHA, "AMENDMENT 1 HASH MISMATCH"
assert hashlib.sha256(open(AM2, 'rb').read()).hexdigest() == AMEND2_SHA, "AMENDMENT 2 HASH MISMATCH"

def sha(p, n=64):
    h = hashlib.sha256()
    with open(os.path.realpath(p), 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''): h.update(b)
    return h.hexdigest()[:n]
def gpu():
    try:
        return subprocess.check_output(["nvidia-smi","--query-gpu=utilization.gpu,memory.used",
                                        "--format=csv,noheader"], text=True).strip()
    except Exception as e:
        return "nvidia-smi unavailable: %s" % e
GPU_START = gpu()

D    = "/workspace/review_scratch/health_check/dev_v4/pod_backup_2026-08-21"
MASK = "/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz"
ARMS = "/workspace/uplift_2026-09-11/r3k/arms"
R12  = "/workspace/uplift_2026-09-11/r12_regime/causal_primitives_r12_v2.npz"
XIB  = "/workspace/uplift_2026-09-11/seatladder/dev/probe_artifacts/w10_ablation_series_LAD_XIB_dyn_s42.npz"
OUT  = "/workspace/uplift_2026-09-11/r13_B_withinhalf"
os.makedirs(OUT, exist_ok=True)
BOOKS = {"s42": f"{ARMS}/A0_PWR230k_s42.npz", "s2027": f"{ARMS}/A0_PWR230k_s2027.npz"}
INPUT_SHAS = {p: dict(realpath=os.path.realpath(p), sha256=sha(p)) for p in
              [f"{D}/wide_fea_hist_meta.npz", f"{D}/wide_panel_4h_hist_v2.npz", MASK, R12, XIB,
               BOOKS["s42"], BOOKS["s2027"], PRE, os.path.abspath(__file__)]}
assert INPUT_SHAS[BOOKS["s42"]]["sha256"] == \
    "352ac36fb319532756da71e7cc405fb0dcde6f36f6e28a57f1f681177bcfd339", "A0 s42 sha mismatch"
t0 = time.time()
def log(*a): print("[%7.1fs]" % (time.time()-t0), *a, flush=True)

# ------------------------------------------------------------------ S1 meta / panel / mask
MT = np.load(f"{D}/wide_fea_hist_meta.npz", allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); y4 = MT["y4"]; qvk = MT["qvk"]
PW = np.load(f"{D}/wide_panel_4h_hist_v2.npz", allow_pickle=True)
pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
FN = PW["f_fund_now"]; IV = PW["f_fund_iv"]
IVf = np.where(np.isfinite(IV) & (IV > 0), IV, 8.0)
UZ = np.load(MASK, allow_pickle=True)
assert [str(x) for x in UZ["symbols"]] == [str(x) for x in PW["symbols"]]
umap = {int(t): k for k, t in enumerate(UZ["ts"].astype(np.int64))}; UM = np.asarray(UZ["mask"])
T, N = y4.shape; TOPN = 829
log("meta", y4.shape, "panel", FN.shape)

MEM = np.empty(T, dtype=object)
Y  = np.full((T, N), np.nan, np.float64)
A  = np.full(T, np.nan)
for i in range(T):
    q = np.nan_to_num(qvk[i], nan=-1.0); o = np.argsort(-q); o = o[q[o] > -0.5]
    m = np.sort(o[:TOPN]).astype(np.int64)
    t = int(E_ts[i])
    if t in umap: m = m[UM[umap[t]][m]]
    MEM[i] = m
    yv32 = y4[i, m]
    Y[i, m] = yv32.astype(np.float64)
    ok = np.isfinite(yv32)
    if ok.sum() >= 30: A[i] = float(yv32[ok].mean())
P12 = np.load(R12); P12C = [str(c) for c in P12["cols"]]; P12R = P12["rec"]
p12row = {int(t): k for k, t in enumerate(P12R[:, 0].astype(np.int64))}
Aarch = np.array([P12R[p12row[int(t)], P12C.index("A_ew")] if int(t) in p12row else np.nan for t in E_ts])
both = np.isfinite(A) & np.isfinite(Aarch)
A_PARITY = float(np.abs(A[both] - Aarch[both]).max())
assert A_PARITY == 0.0, ("A_ew PARITY", A_PARITY)
log("A_ew parity vs r12 = 0.0 (bit-exact), members mean %.1f" % np.mean([len(x) for x in MEM]))

# ------------------------------------------------------------------ S2 per-name causal beta
okrow = np.isfinite(A)
Mfin  = np.isfinite(Y) & okrow[:, None]
Az    = np.where(okrow, A, 0.0)
Yz    = np.where(Mfin, Y, 0.0)
def pre(x):
    c = np.zeros((T + 1, N)); np.cumsum(x, axis=0, out=c[1:]); return c
Cn   = pre(Mfin.astype(np.float64))
Ca   = pre(Az[:, None] * Mfin)
Caa  = pre((Az * Az)[:, None] * Mfin)
Cy   = pre(Yz)
Cay  = pre(Yz * Az[:, None])
Cyy  = pre(Yz * Yz)
Crow = np.concatenate([[0.0], np.cumsum(okrow.astype(np.float64))])
del Yz

def beta_at(i, W):
    """beta_i(t;W) over meta rows [i-W, i-1], pairwise-complete, >=0.8*n_Arows finite."""
    lo, hi = i - W, i
    if lo < 0: return np.full(N, np.nan)
    nrow = Crow[hi] - Crow[lo]
    if nrow < 5: return np.full(N, np.nan)
    n   = Cn[hi] - Cn[lo]
    Sa  = Ca[hi] - Ca[lo]; Saa = Caa[hi] - Caa[lo]
    Sy  = Cy[hi] - Cy[lo]; Say = Cay[hi] - Cay[lo]; Syy = Cyy[hi] - Cyy[lo]
    with np.errstate(invalid='ignore', divide='ignore'):
        ma, my = Sa / n, Sy / n
        cov = Say / n - ma * my
        var = Saa / n - ma * ma
        b = cov / var
    bad = (n < 0.8 * nrow) | ~np.isfinite(b) | (var <= 0)
    b = np.where(bad, np.nan, b)
    return b

def beta_direct(i, W):
    """loop-form reference, verbatim algebra of r13_beta_pod.py betas()."""
    r = np.array([k for k in range(i - W, i) if np.isfinite(A[k])], int)
    if r.size < 5: return np.full(N, np.nan)
    a = A[r]; m = np.isfinite(Y[r]); yz = np.where(m, Y[r], 0.0)
    n = m.sum(0).astype(np.float64)
    Sa = (a[:, None] * m).sum(0); Saa = ((a * a)[:, None] * m).sum(0)
    Sy = yz.sum(0); Say = (yz * a[:, None]).sum(0)
    with np.errstate(invalid='ignore', divide='ignore'):
        ma, my = Sa / n, Sy / n
        cov = Say / n - ma * my; var = Saa / n - ma * ma
        b = cov / var
    bad = (n < 0.8 * r.size) | ~np.isfinite(b) | (var <= 0)
    return np.where(bad, np.nan, b)

WBETAS = (60, 120, 250)
rng_chk = np.random.default_rng([20260905, 777])
PRE_PARITY = {}
for W in WBETAS:
    ds = []
    for i in rng_chk.integers(1200, T, 25):
        b1 = beta_at(int(i), W); b2 = beta_direct(int(i), W)
        k = np.isfinite(b1) | np.isfinite(b2)
        assert np.array_equal(np.isfinite(b1), np.isfinite(b2)), ("nan pattern", i, W)
        ds.append(float(np.nanmax(np.abs(b1[k] - b2[k]))) if k.any() else 0.0)
    PRE_PARITY[W] = max(ds)
    assert PRE_PARITY[W] < 1e-9, ("prefix-sum vs direct beta", W, PRE_PARITY[W])
log("beta prefix-sum vs direct maxabs", PRE_PARITY)

BETA = {W: np.full((T, N), np.nan, np.float32) for W in WBETAS}
for W in WBETAS:
    for i in range(W, T): BETA[W][i] = beta_at(i, W)
    log("beta matrix W=%d built, finite frac %.4f" % (W, float(np.isfinite(BETA[W]).mean())))

# ------------------------------------------------------------------ S3 per-anchor static book data
UB = calendar.timegm((2026, 8, 30, 20, 0, 0))
COSTB_CACHE = {}
def load_book(tag):
    Z = np.load(BOOKS[tag], allow_pickle=True)
    C = [str(c) for c in Z['cols']]; RC = Z['rec']; cfg = json.loads(str(Z['config_json']))
    assert cfg['CAL'] == 'log' and cfg['PHI'] == 0.45 and cfg['LEGS'] == '101' and \
           cfg['WRULE'] == 'msharpe' and cfg['LOOK'] == 900 and cfg['MEMBERS_TOPN'] == 829 and \
           cfg['UMASK_SCOPE'] == 'm1' and cfg['W3FIX'] is None and cfg['FTRIM'] == 'zero', cfg
    assert cfg['UPLIFT']['self_sha256'] == \
        "b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650", "device pin"
    COSTB_CACHE[tag] = cfg['COST_B']
    col = lambda k: RC[:, C.index(k)].astype(float)
    return dict(ts=col('ts').astype(np.int64), W=Z['W'], gt=col('gross_total'),
                pnl_ex=col('pnl_ex'), carry_ex=col('carry_ex'), cost_ex=col('cost_ex'),
                net_ex=col('net_ex'), turnover=col('turnover'), cfg=cfg,
                netlong=col('netlong'), pnl=col('pnl'), carry=col('carry'))

def static_rows(bk, tag):
    """per rec-row: meta row, panel row, member set, y, funding4h, cost rate vector."""
    mrow = {int(t): i for i, t in enumerate(E_ts)}
    rows = []
    CB = COSTB_CACHE[tag]
    assert CB == COSTB_CACHE['s42'], ('COST_B differs between seeds', tag)
    rate_tier = np.array([fr * mk + (1 - fr) * tk for (mk, tk, fr) in CB])
    for k, t in enumerate(bk['ts']):
        t = int(t); i = mrow[t]; j = pw_row[t]; m = MEM[i]
        qv4h = np.expm1(np.clip(qvk[i, m], 0, 30)) * 48
        tr = np.full(len(m), 2, np.int8); tr[qv4h >= 1e6] = 1; tr[qv4h >= 5e6] = 0
        rows.append(dict(i=i, j=j, m=m,
                         yv=np.nan_to_num(y4[i, m], nan=0.0).astype(np.float64),
                         fn4=(np.nan_to_num(FN[j, m], nan=0.0) * (4.0 / IVf[j, m])).astype(np.float64),
                         rate=rate_tier[tr]))
    return rows

def reshape_ex(sm):
    """w10_sleeve.py L312-319 == dl_quant_live/signal/legs.py:124 executor semantics."""
    nz = np.abs(sm) > 1e-12
    smr = sm.copy()
    if nz.any():
        smr[nz] -= smr[nz].mean()
        g0 = np.abs(sm).sum(); g1 = np.abs(smr).sum()
        if g1 > 1e-9: smr *= g0 / g1
    return smr

# ------------------------------------------------------------------ S4 THE OVERLAY (FORM B)
THETA_MAX = 1.0; MULT_LO, MULT_HI = 0.25, 1.75
def overlay(u, m, b, kappa, rho=0.86):
    """within-half beta tilt on normalised weights u (L1=1, sum=0). Returns u', diag dict.
       Each half's dollar sum over the tilted subset is preserved EXACTLY."""
    d = dict(theta=0.0, Bhat=np.nan, Bhat_post=np.nan, bL=np.nan, bS=np.nan,
             bL_post=np.nan, bS_post=np.nan, nfin=0, clipped=0, exact=True)
    fin = np.isfinite(b[m])
    if fin.sum() < 20: return u, d
    mm = m[fin]; bb = b[mm].astype(np.float64)
    bbar_cs = bb.mean()
    bb = bbar_cs + rho * (bb - bbar_cs)            # Vasicek shrink (proved no-op below)
    s = bb.std()
    uu = u[mm]
    L = uu > 0; S = uu < 0
    d['nfin'] = int(fin.sum())
    if s <= 0 or L.sum() < 5 or S.sum() < 5: return u, d
    SL = uu[L].sum(); SS = uu[S].sum()
    bL = float((uu[L] * bb[L]).sum() / SL); bS = float((uu[S] * bb[S]).sum() / SS)
    # AMENDMENT 1 (prereg sha 720fa335…): the BOOK's ex-ante beta, which imputes the
    # cross-sectional mean beta to every name we cannot estimate. sum(u) over the whole
    # book is 0, so sum over the non-estimable complement is -Su; hence
    #   sum_all u*b  ==  sum_{m_fin} u*(b~ - bbar_cs).
    # The v1 form sum_{m_fin} u*b~ carried a spurious bbar_cs*Su term, was not the book's
    # beta, and broke the pre-registered rho-invariance.
    bb_c = bb - bbar_cs
    Bhat = float((uu * bb_c).sum())
    VL = float((uu[L] * (bb[L] - bL) ** 2).sum())
    VS = float((-uu[S] * (bb[S] - bS) ** 2).sum())
    d.update(Bhat=Bhat, bL=bL, bS=bS)
    if VL + VS <= 0: return u, d
    th = kappa * Bhat * s / (VL + VS)
    th = float(np.clip(th, -THETA_MAX, THETA_MAX))
    d['theta'] = th
    if th == 0.0:
        d.update(Bhat_post=Bhat, bL_post=bL, bS_post=bS); return u, d
    mult = np.ones(len(mm))
    mult[L] = 1.0 - th * (bb[L] - bL) / s
    mult[S] = 1.0 + th * (bb[S] - bS) / s
    cl = (mult < MULT_LO) | (mult > MULT_HI)
    d['clipped'] = int(cl.sum()); d['exact'] = bool(cl.sum() == 0)
    mult = np.clip(mult, MULT_LO, MULT_HI)
    un = uu * mult
    nl = un[L].sum(); ns = un[S].sum()
    if nl == 0 or ns == 0: return u, d
    un[L] *= SL / nl; un[S] *= SS / ns          # restore each half's dollar sum EXACTLY
    up = u.copy(); up[mm] = un
    d.update(Bhat_post=float((un * bb_c).sum()),
             bL_post=float((un[L] * bb[L]).sum() / un[L].sum()),
             bS_post=float((un[S] * bb[S]).sum() / un[S].sum()))
    return up, d

# ------------------------------------------------------------------ S5 accounting
def account(bk, rows, kappa, wbeta, mode="POST", rho=0.86, betamat=None, bshift=0, bperm=None):
    """Recompute the _ex ledger from the stored weights, with the overlay applied.
       mode POST : overlay on smr (reshape is the identity on the output)  [PRIMARY]
       mode PRE  : overlay on sm, then executor reshape                     [variant R]
       mode BAND : POST + 2.5e-4 no-trade band on the overlay delta, halves restored [variant BAND]"""
    n = len(rows); BM = betamat if betamat is not None else (BETA[wbeta] if wbeta else None)
    gt = bk['gt']; Wm = bk['W']
    out = dict((k, np.zeros(n)) for k in
               ('pnl','carry','cost','turn','theta','Bhat','Bhat_post','bL','bS','bL_post','bS_post',
                'pl','ps','cl','cs','gL','gS','l1chk','sumchk','fire','clipped','signflip','exact'))
    HR = np.zeros(N); prev = None
    for k in range(n):
        r = rows[k]; sm = Wm[k].astype(np.float64); G = gt[k]
        smr = reshape_ex(sm)
        if kappa == 0.0 and mode == "POST":
            v = smr; dg_ = dict(theta=0.0, Bhat=np.nan, Bhat_post=np.nan, bL=np.nan, bS=np.nan,
                                bL_post=np.nan, bS_post=np.nan, clipped=0, exact=True)
        else:
            base = smr if mode in ("POST", "BAND") else sm
            u = base / G
            bi = r['i'] - bshift
            b = BM[bi] if (BM is not None and 0 <= bi < T) else np.full(N, np.nan, np.float32)
            if bperm is not None:
                bp = np.full(N, np.nan, np.float32); bp[bperm] = b; b = bp
            up, dg_ = overlay(u, r['m'], b, kappa, rho)
            v = up * G
            if mode == "BAND":
                dlt = v - smr
                v = np.where(np.abs(dlt) < 2.5e-4, smr, v)
                mm = r['m']
                for sgn in (1, -1):
                    sel = (smr[mm] > 0) if sgn > 0 else (smr[mm] < 0)
                    if sel.sum() and v[mm][sel].sum() != 0:
                        tmp = v[mm]; tmp[sel] *= smr[mm][sel].sum() / tmp[sel].sum(); v[mm] = tmp
            if mode == "PRE":
                v = reshape_ex(v)
        out['l1chk'][k]  = abs(np.abs(v).sum() - G)
        out['sumchk'][k] = abs(v.sum() - smr.sum())
        out['signflip'][k] = int((np.sign(v[r['m']]) != np.sign(smr[r['m']])).sum())
        m = r['m']; vm = v[m]
        p = vm * r['yv'] * 1e4; c = vm * r['fn4'] * 1e4
        trr = v - HR
        out['pnl'][k] = p.sum(); out['carry'][k] = c.sum()
        out['cost'][k] = float((np.abs(trr[m]) * r['rate']).sum())
        out['turn'][k] = float(np.abs(trr).sum())
        Lm = vm > 0; Sm = vm < 0
        out['pl'][k] = p[Lm].sum(); out['ps'][k] = p[Sm].sum()
        out['cl'][k] = c[Lm].sum(); out['cs'][k] = c[Sm].sum()
        out['gL'][k] = np.abs(vm[Lm]).sum() / G; out['gS'][k] = np.abs(vm[Sm]).sum() / G
        for f in ('theta','Bhat','Bhat_post','bL','bS','bL_post','bS_post','clipped'):
            out[f][k] = dg_[f] if dg_[f] is not None else np.nan
        out['exact'][k] = 1.0 if dg_['exact'] else 0.0
        out['fire'][k] = 1.0 if (prev is not None or True) and np.abs(v - smr).max() > 1e-5 * G else 0.0
        HR = v; prev = v
    out['net'] = out['pnl'] - out['carry'] - out['cost']
    out['g']   = out['net'] / gt
    out['turn_matched'] = out['turn'] / gt
    return out

# ------------------------------------------------------------------ S6 statistics
NB = 2000
def blocks(mask, day):
    idx = np.nonzero(mask)[0]
    dd = {}
    for k in idx: dd.setdefault(day[k], []).append(k)
    return [np.array(v) for _, v in sorted(dd.items())]
def boot_mean(x, mask, day):
    by = blocks(mask, day)
    if len(by) < 3: return (np.nan, np.nan, np.nan)
    tot = np.array([x[b].sum() for b in by]); cnt = np.array([len(b) for b in by], float)
    nd = len(by); ms = np.empty(NB)
    for k in range(NB):
        r = np.random.default_rng([20260905, k]).integers(0, nd, nd)
        ms[k] = tot[r].sum() / cnt[r].sum()
    return float(np.percentile(ms, 2.5)), float(np.percentile(ms, 97.5)), float(ms.std(ddof=1))
def boot_ci_alpha(x, mask, day, alpha):
    by = blocks(mask, day)
    if len(by) < 3: return (np.nan, np.nan)
    tot = np.array([x[b].sum() for b in by]); cnt = np.array([len(b) for b in by], float)
    nd = len(by); ms = np.empty(NB)
    for k in range(NB):
        r = np.random.default_rng([20260905, k]).integers(0, nd, nd)
        ms[k] = tot[r].sum() / cnt[r].sum()
    return float(np.percentile(ms, 100*alpha/2)), float(np.percentile(ms, 100*(1-alpha/2)))
def ols(x, y):
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() < 30: return dict(a=np.nan, b=np.nan, se=np.nan, t=np.nan, n=int(ok.sum()))
    X = np.column_stack([np.ones(ok.sum()), x[ok]]); Y = y[ok]
    bb, *_ = np.linalg.lstsq(X, Y, rcond=None); res = Y - X @ bb
    s2 = res @ res / (len(Y) - 2); sb = np.sqrt(np.diag(s2 * np.linalg.pinv(X.T @ X)))
    return dict(a=float(bb[0]), b=float(bb[1]), se=float(sb[1]),
                t=float(bb[1]/sb[1]) if sb[1] > 0 else np.nan, n=int(ok.sum()))
def maxdd(g, L=2.0):
    eq = np.concatenate([[1.0], np.cumprod(1.0 + L * g * 1e-4)])
    return float((1 - eq / np.maximum.accumulate(eq)).max())
def daystats(g, mask, day, L=2.0):
    by = {}
    for k in np.nonzero(mask)[0]: by.setdefault(day[k], []).append(k)
    keys = sorted(by)
    dr = np.array([np.prod(1.0 + L * g[np.array(by[d])] * 1e-4) - 1.0 for d in keys])
    w = int(np.argmin(dr))
    return dict(n_days=len(keys), worst_day=keys[w], worst_day_ret=float(dr[w]),
                halt4=int((dr <= -0.04).sum()), alert268=int((dr <= -0.0268).sum()),
                halt4_per_yr=float((dr <= -0.04).sum()/(len(dr)/365.0)),
                maxDD=maxdd(g[mask], L))

# ------------------------------------------------------------------ S7 run
RES = dict(prereg_sha256=PREREG_SHA, amendment1_sha256=AMEND1_SHA, amendment2_sha256=AMEND2_SHA, device_sha256=sha(os.path.abspath(__file__)),
           inputs=INPUT_SHAS, env=ENV_REPORT, gpu_start=GPU_START,
           beta_prefix_vs_direct_maxabs={str(k): v for k, v in PRE_PARITY.items()},
           A_ew_parity_vs_r12_maxabs=A_PARITY, K_total=12,
           primary_arm=dict(KAPPA=1.00, WBETA=250, mode="POST", seed="s42"))

BK = {tg: load_book(tg) for tg in BOOKS}
ROWS = {tg: static_rows(BK[tg], tg) for tg in BOOKS}
for tg in BOOKS:
    ts = BK[tg]['ts']
    WT = ts <= UB; WA = WT.copy(); WA[:900] = False
    assert int(WT.sum()) == 10038 and int(WA.sum()) == 9138, (tg, int(WT.sum()), int(WA.sum()))
TS  = BK['s42']['ts']
WT  = TS <= UB; WA = WT.copy(); WA[:900] = False
DAY = np.array([time.strftime('%Y%m%d', time.gmtime(int(t))) for t in TS])
YEAR= np.array([time.gmtime(int(t)).tm_year for t in TS])
gA0 = BK['s42']['net_ex'] / BK['s42']['gt']
xa = gA0[WA]
SELFCHK = dict(mean_g=float(xa.mean()), sharpe=float(xa.mean()/xa.std(ddof=1)*np.sqrt(2190)),
               turn_raw=float(BK['s42']['turnover'][WA].mean()),
               turn_matched=float((BK['s42']['turnover']/BK['s42']['gt'])[WA].mean()))
assert abs(SELFCHK['mean_g'] - 0.6341957) < 5e-7 and abs(SELFCHK['sharpe'] - 1.2912234) < 5e-7, SELFCHK
assert abs(SELFCHK['turn_raw'] - 0.03032) < 5e-6 and abs(SELFCHK['turn_matched'] - 0.0540270) < 5e-7, SELFCHK
RES['selfcheck_archive'] = SELFCHK
RES['turnover_caliber'] = dict(raw=SELFCHK['turn_raw'], matched=SELFCHK['turn_matched'],
                               ratio=SELFCHK['turn_matched']/SELFCHK['turn_raw'],
                               note="matched = turnover/gross_total (mean gross_total %.4f); "
                                    "RAW/matched confusion is a x1.4375 error"
                                    % BK['s42']['gt'][WA].mean())
log("archive self-check OK", SELFCHK)

# ---- GATE P
GP = {}
rng_gp = np.random.default_rng([20260905, 13])
zz = []
for tg in BOOKS:
    for k in rng_gp.integers(1000, len(ROWS[tg]), 200):
        r = ROWS[tg][int(k)]; sm = BK[tg]['W'][int(k)].astype(np.float64)
        G = BK[tg]['gt'][int(k)]; u = reshape_ex(sm) / G
        up, _ = overlay(u, r['m'], BETA[250][r['i']], 0.0)
        zz.append(float(np.abs(up - u).max()))
GP['overlay_identity_at_kappa0_maxabs'] = max(zz)
assert max(zz) == 0.0, ("GATE P overlay identity", max(zz))
BASE = {}
for tg in BOOKS:
    b0 = account(BK[tg], ROWS[tg], 0.0, 250, "POST")
    BASE[tg] = b0
    GP[tg] = dict(
        pnl_ex_maxabs = float(np.abs(b0['pnl']   - BK[tg]['pnl_ex']).max()),
        carry_ex_maxabs= float(np.abs(b0['carry'] - BK[tg]['carry_ex']).max()),
        cost_ex_maxabs= float(np.abs(b0['cost']  - BK[tg]['cost_ex']).max()),
        net_ex_maxabs = float(np.abs(b0['net']   - BK[tg]['net_ex']).max()),
        g_maxabs      = float(np.abs(b0['g']     - BK[tg]['net_ex']/BK[tg]['gt']).max()),
        mean_g_rebuild= float(b0['g'][WA].mean()),
        mean_g_archive= float((BK[tg]['net_ex']/BK[tg]['gt'])[WA].mean()))
    log("GATE P", tg, GP[tg])
RES['GATE_P'] = GP
PASS_P = all(GP[tg]['pnl_ex_maxabs'] < 1e-3 and GP[tg]['carry_ex_maxabs'] < 1e-4
             and GP[tg]['cost_ex_maxabs'] < 1e-4 for tg in BOOKS)
RES['GATE_P_pass'] = bool(PASS_P and GP['overlay_identity_at_kappa0_maxabs'] == 0.0)
assert RES['GATE_P_pass'], GP

# ---- shrinkage invariance (prereg 3.2)
a1 = account(BK['s42'], ROWS['s42'], 1.00, 250, "POST", rho=1.00)
a2 = account(BK['s42'], ROWS['s42'], 1.00, 250, "POST", rho=0.86)
RES['shrinkage_is_noop'] = dict(
    g_maxabs=float(np.abs(a1['g'] - a2['g']).max()),
    theta_maxabs=float(np.abs(a1['theta'] - a2['theta']).max()),
    note="Vasicek rho scales Bhat, s and V so it cancels exactly in theta* = kappa*Bhat*s/(VL+VS). "
         "AMENDMENT 1 made this true by defining Bhat on DEMEANED betas; it is now ASSERTED.")
# AMENDMENT 2: round-off tolerance (rho is an actual multiply; IEEE754 cannot cancel bitwise)
assert RES['shrinkage_is_noop']['theta_maxabs'] <= 1e-12 and \
       RES['shrinkage_is_noop']['g_maxabs'] <= 1e-9, ("rho-invariance", RES['shrinkage_is_noop'])
log("shrinkage no-op ASSERTED", RES['shrinkage_is_noop'])

# ---- the grid
GRID = {}
for kap in (0.25, 0.50, 0.75, 1.00):
    for W in WBETAS:
        nm = "K%.2f_W%d" % (kap, W)
        GRID[nm] = account(BK['s42'], ROWS['s42'], kap, W, "POST")
        log("arm", nm, "done")
np.save(f"{OUT}/_grid_g.npy", np.array([GRID[k]['g'] for k in sorted(GRID)]))
json.dump(sorted(GRID), open(f"{OUT}/_grid_names.json", "w"))

def armstats(ov, bs, mask=WA):
    d = ov['g'] - bs['g']
    lo, hi, se = boot_mean(d, mask, DAY)
    blo, bhi = boot_ci_alpha(d, mask, DAY, 0.05 / 12.0)
    dcost = (ov['cost'] - bs['cost']) / BK['s42']['gt']
    dgross = ((ov['pnl'] - ov['carry']) - (bs['pnl'] - bs['carry'])) / BK['s42']['gt']
    rep = (ov['net'] - 2.2167 * ov['cost'] - (bs['net'] - 2.2167 * bs['cost'])) / BK['s42']['gt']
    return dict(dg=float(d[mask].mean()), ci95=[lo, hi], boot_se=se, bonf12=[blo, bhi],
                dg_pnl=float(((ov['pnl']-bs['pnl'])/BK['s42']['gt'])[mask].mean()),
                dg_carry=float(((ov['carry']-bs['carry'])/BK['s42']['gt'])[mask].mean()),
                dg_cost=float(dcost[mask].mean()),
                dturn_matched=float((ov['turn_matched']-bs['turn_matched'])[mask].mean()),
                turn_matched=float(ov['turn_matched'][mask].mean()),
                dturn_pct=float((ov['turn_matched']-bs['turn_matched'])[mask].mean()
                                / bs['turn_matched'][mask].mean() * 100),
                cost_survival=float(d[mask].mean()/dgross[mask].mean()) if dgross[mask].mean() else np.nan,
                dg_reprice_3p2167=float(rep[mask].mean()),
                sharpe_ov=float(ov['g'][mask].mean()/ov['g'][mask].std(ddof=1)*np.sqrt(2190)),
                sharpe_base=float(bs['g'][mask].mean()/bs['g'][mask].std(ddof=1)*np.sqrt(2190)),
                mean_theta=float(np.nanmean(ov['theta'][mask])),
                mean_abs_theta=float(np.nanmean(np.abs(ov['theta'][mask]))),
                fire_frac=float(ov['fire'][mask].mean()), fire_n=int(ov['fire'][mask].sum()),
                clipped_mean=float(ov['clipped'][mask].mean()),
                exact_frac=float(ov['exact'][mask].mean()),
                l1_maxabs=float(ov['l1chk'].max()), sum_maxabs=float(ov['sumchk'].max()),
                signflip_total=int(ov['signflip'].sum()))
RES['grid'] = {k: armstats(GRID[k], BASE['s42']) for k in sorted(GRID)}
for k in sorted(RES['grid']):
    log("ARM", k, "dg %+.4f" % RES['grid'][k]['dg'], "CI", [round(x,4) for x in RES['grid'][k]['ci95']],
        "dturn%% %+.2f" % RES['grid'][k]['dturn_pct'])
json.dump(RES, open(f"{OUT}/RECEIPT_r13B_stage1.json", "w"), indent=1, default=float)
log("stage1 receipt written")

# ------------------------------------------------------------------ S8 GATE M: did it move the beta gap?
IDX_META = np.array([r['i'] for r in ROWS['s42']])
Anow = A[IDX_META]; Abps = Anow * 1e4
GT42 = BK['s42']['gt']
def halves(o):
    gL, gS = o['gL'], o['gS']
    rL = np.where(gL > 1e-9, (o['pl']/GT42)/gL, np.nan)
    rS = np.where(gS > 1e-9, -(o['ps']/GT42)/gS, np.nan)
    EXPO = ((gL-gS)/2.0)*(rL+rS); SELE = ((rL-rS)/2.0)*(gL+gS)
    return rL, rS, EXPO, SELE
def gatem(ov, bs, tagname):
    out = dict(arm=tagname)
    gap_pre  = bs['bL'] - bs['bS']
    gap_post = ov['bL_post'] - ov['bS_post']
    gap_pre_ov = ov['bL'] - ov['bS']
    out['exante_gap_pooled'] = dict(
        base=float(np.nanmean(gap_pre_ov[WA])), overlay=float(np.nanmean(gap_post[WA])),
        abs_base=float(np.nanmean(np.abs(gap_pre_ov[WA]))),
        abs_overlay=float(np.nanmean(np.abs(gap_post[WA]))),
        pct_reduction=float(100*(1 - np.nanmean(np.abs(gap_post[WA]))/np.nanmean(np.abs(gap_pre_ov[WA])))))
    lo1, hi1, _ = boot_mean(np.nan_to_num(np.abs(gap_pre_ov)), WA, DAY)
    lo2, hi2, _ = boot_mean(np.nan_to_num(np.abs(gap_post)), WA, DAY)
    out['exante_gap_pooled']['ci_abs_base'] = [lo1, hi1]
    out['exante_gap_pooled']['ci_abs_overlay'] = [lo2, hi2]
    d = np.nan_to_num(np.abs(gap_post)) - np.nan_to_num(np.abs(gap_pre_ov))
    l, h, _ = boot_mean(d, WA, DAY); out['exante_gap_pooled']['ci_delta_abs'] = [l, h]
    out['exante_gap_by_year'] = {}
    for y in sorted(set(YEAR[WA].tolist())):
        a = WA & (YEAR == y)
        l, h, _ = boot_mean(d, a, DAY)
        out['exante_gap_by_year'][str(y)] = dict(
            n=int(a.sum()), base=float(np.nanmean(gap_pre_ov[a])), overlay=float(np.nanmean(gap_post[a])),
            abs_base=float(np.nanmean(np.abs(gap_pre_ov[a]))), abs_overlay=float(np.nanmean(np.abs(gap_post[a]))),
            ci_delta_abs=[l, h],
            Bhat_base=float(np.nanmean(ov['Bhat'][a])), Bhat_overlay=float(np.nanmean(ov['Bhat_post'][a])),
            mean_theta=float(np.nanmean(ov['theta'][a])), sign_theta=float(np.sign(np.nanmean(ov['theta'][a]))))
    rLb, rSb, EXb, SEb = halves(bs); rLo, rSo, EXo, SEo = halves(ov)
    out['realised'] = {}
    for lab, msk in [("pooled", WA)] + [(str(y), WA & (YEAR == y)) for y in sorted(set(YEAR[WA].tolist()))]:
        out['realised'][lab] = dict(
            n=int(msk.sum()),
            g_on_A_base=ols(np.where(msk, Abps, np.nan), np.where(msk, bs['g'], np.nan)),
            g_on_A_overlay=ols(np.where(msk, Abps, np.nan), np.where(msk, ov['g'], np.nan)),
            betaL_base=ols(np.where(msk, Abps, np.nan), np.where(msk, rLb, np.nan))['b'],
            betaS_base=ols(np.where(msk, Abps, np.nan), np.where(msk, rSb, np.nan))['b'],
            betaL_ov=ols(np.where(msk, Abps, np.nan), np.where(msk, rLo, np.nan))['b'],
            betaS_ov=ols(np.where(msk, Abps, np.nan), np.where(msk, rSo, np.nan))['b'],
            expo_base=float(np.nanmean(EXb[msk])), sele_base=float(np.nanmean(SEb[msk])),
            expo_ov=float(np.nanmean(EXo[msk])), sele_ov=float(np.nanmean(SEo[msk])))
        r = out['realised'][lab]
        r['realised_gap_base'] = r['betaL_base'] - r['betaS_base']
        r['realised_gap_ov']   = r['betaL_ov'] - r['betaS_ov']
    return out
PRIMARY = "K1.00_W250"
RES['GATE_M'] = {k: gatem(GRID[k], BASE['s42'], k) for k in (PRIMARY, "K0.50_W250", "K1.00_W60")}
gm = RES['GATE_M'][PRIMARY]
r23 = gm['realised'].get('2023', {}); r26 = gm['realised'].get('2026', {})
def toward_zero(a, b): return abs(b) < abs(a)
RES['GATE_M_pass'] = bool(gm['exante_gap_pooled']['pct_reduction'] >= 50.0
    and toward_zero(r23['g_on_A_base']['b'], r23['g_on_A_overlay']['b'])
    and toward_zero(r26['g_on_A_base']['b'], r26['g_on_A_overlay']['b']))
log("GATE M", json.dumps(gm['exante_gap_pooled'], default=float))
log("GATE M pass =", RES['GATE_M_pass'])

# ------------------------------------------------------------------ S9 regime cells (r12's exact 34)
P12A = dict((c, P12R[:, P12C.index(c)].astype(float)) for c in P12C)
mts12 = P12R[:, 0].astype(np.int64); m12row = {int(t): i for i, t in enumerate(mts12)}
def trail_mean(x, k):
    out = np.full(len(x), np.nan)
    cs = np.concatenate([[0.0], np.cumsum(np.nan_to_num(x))])
    cn = np.concatenate([[0.0], np.cumsum(np.isfinite(x).astype(float))])
    for i in range(k, len(x)):
        n = cn[i] - cn[i-k]
        if n >= k*0.8: out[i] = (cs[i]-cs[i-k])/n
    return out
def trail_sum(x, k):
    out = np.full(len(x), np.nan)
    cs = np.concatenate([[0.0], np.cumsum(np.nan_to_num(x))])
    cn = np.concatenate([[0.0], np.cumsum(np.isfinite(x).astype(float))])
    for i in range(k, len(x)):
        if cn[i]-cn[i-k] >= k*0.8: out[i] = cs[i]-cs[i-k]
    return out
def trail_sd(x, k):
    out = np.full(len(x), np.nan)
    for i in range(k, len(x)):
        w = x[i-k:i]; w = w[np.isfinite(w)]
        if len(w) >= k*0.8: out[i] = w.std()
    return out
Ab, Bb, Db = P12A['A_ew'], P12A['B_breadth'], P12A['D_disp_bps']
BRD6 = trail_mean(Bb,6); XSV30 = trail_mean(Db,30); MV30 = trail_sd(Ab,30)*1e4
R24 = trail_sum(Ab,6); R72 = trail_sum(Ab,18)
take = np.array([m12row[int(t)] for t in TS])
BRD6, XSV30, MV30, R24, R72 = (v[take] for v in (BRD6, XSV30, MV30, R24, R72))
SIGF, FMED, SPAY = (P12A[c][take] for c in ('SIGF','FMED','SPAY'))
def terc(v): return np.nanpercentile(v[WA], [100/3, 200/3])
def band(v, q):
    lab = np.full(len(v), -1)
    lab[np.isfinite(v) & (v <= q[0])] = 0
    lab[np.isfinite(v) & (v > q[0]) & (v <= q[1])] = 1
    lab[np.isfinite(v) & (v > q[1])] = 2
    return lab
QB, QX, QM, QS = terc(BRD6), terc(XSV30), terc(MV30), terc(SIGF)
Q_FMED_D1 = np.nanpercentile(FMED[WA], 10); Q_SPAY_D9 = np.nanpercentile(SPAY[WA], 90)
LB, LX, LM, LS = band(BRD6,QB), band(XSV30,QX), band(MV30,QM), band(SIGF,QS)
CELLS = []
for y in sorted(set(YEAR[WT].tolist())): CELLS.append(('a_YEAR', str(y), YEAR == y))
for t_, nm in [(0,'T1 narrowest'),(1,'T2'),(2,'T3 broadest')]: CELLS.append(('b_BREADTH(trail24h)', nm, LB==t_))
for t_, nm in [(0,'T1 lowest'),(1,'T2'),(2,'T3 highest')]: CELLS.append(('c_XSVOL(trail5d disp)', nm, LX==t_))
for t_, nm in [(0,'T1 lowest'),(1,'T2'),(2,'T3 highest')]: CELLS.append(('c2_MKTVOL(trail5d EW sd)', nm, LM==t_))
for t_, nm in [(0,'T1 lowest'),(1,'T2'),(2,'T3 highest')]: CELLS.append(('d_SIGF(fund disp)', nm, LS==t_))
E = {}
E['POSTCRASH R24<=-2%'] = np.isfinite(R24) & (R24 <= -0.02)
E['~POSTCRASH'] = np.isfinite(R24) & (R24 > -0.02)
E['BROADRALLY R24>=+2%&B>=.60'] = np.isfinite(R24) & np.isfinite(BRD6) & (R24>=0.02) & (BRD6>=0.60)
E['~BROADRALLY'] = np.isfinite(R24) & np.isfinite(BRD6) & ~E['BROADRALLY R24>=+2%&B>=.60']
E['ALTSURGE R72>=+8%'] = np.isfinite(R72) & (R72 >= 0.08)
E['~ALTSURGE'] = np.isfinite(R72) & (R72 < 0.08)
E['ALTSURGE_BROAD'] = E['ALTSURGE R72>=+8%'] & np.isfinite(BRD6) & (BRD6>=0.60)
E['DEEPNEG_MKT (FMED d1)'] = np.isfinite(FMED) & (FMED <= Q_FMED_D1)
E['~DEEPNEG_MKT'] = np.isfinite(FMED) & (FMED > Q_FMED_D1)
E['DEEPNEG_SHORT (SPAY d10)'] = np.isfinite(SPAY) & (SPAY >= Q_SPAY_D9)
E['~DEEPNEG_SHORT'] = np.isfinite(SPAY) & (SPAY < Q_SPAY_D9)
for k_, v_ in E.items(): CELLS.append(('e_EVENT', k_, v_))
for lo_, hi_, nm in [(-9,-0.04,'R72 < -4%'),(-0.04,0.0,'R72 -4%..0'),(0.0,0.04,'R72 0..+4%'),
                     (0.04,0.08,'R72 +4..+8%'),(0.08,0.15,'R72 +8..+15%'),(0.15,9,'R72 >= +15%')]:
    CELLS.append(('e2_R72 ladder', nm, np.isfinite(R72) & (R72>=lo_) & (R72<hi_)))
def regime_table(ov, bs):
    tab = []
    d = ov['g'] - bs['g']
    for fam, lab, mk in CELLS:
        a = mk & WA; n = int(a.sum())
        if n < 30: tab.append(dict(family=fam, cell=lab, n=n, note='too few')); continue
        xb = bs['g'][a]; xo = ov['g'][a]
        lo, hi, _ = boot_mean(d, a, DAY)
        tab.append(dict(family=fam, cell=lab, n=n,
            g_base=float(xb.mean()), g_ov=float(xo.mean()), dg=float(d[a].mean()), dg_ci=[lo, hi],
            sharpe_base=float(xb.mean()/xb.std(ddof=1)*np.sqrt(2190)),
            sharpe_ov=float(xo.mean()/xo.std(ddof=1)*np.sqrt(2190)),
            sharpe_se=float(np.sqrt(2190/n)),
            dturn=float((ov['turn_matched']-bs['turn_matched'])[a].mean()),
            mean_theta=float(np.nanmean(ov['theta'][a]))))
    return tab
RES['regime_table_primary'] = regime_table(GRID[PRIMARY], BASE['s42'])
RES['regime_cuts'] = dict(BRD6=QB.tolist(), XSV30=QX.tolist(), MV30=QM.tolist(), SIGF=QS.tolist(),
                          FMED_decile1=float(Q_FMED_D1), SPAY_decile10=float(Q_SPAY_D9),
                          note="cuts frozen on the A0 W_ALPHA distribution and applied to BOTH arms")
nn = sum(1 for r in RES['regime_table_primary'] if 'note' not in r)
RES['regime_n_cells'] = nn
RES['regime_sharpe_over3_base'] = sum(1 for r in RES['regime_table_primary']
    if 'note' not in r and r['sharpe_base'] > 3.0)
RES['regime_sharpe_over3_ov'] = sum(1 for r in RES['regime_table_primary']
    if 'note' not in r and r['sharpe_ov'] > 3.0)
RES['regime_ci_over3_ov'] = sum(1 for r in RES['regime_table_primary']
    if 'note' not in r and (r['sharpe_ov'] - 1.96*r['sharpe_se']) > 3.0)
log("regime table done, cells", nn)

# ------------------------------------------------------------------ S10 TAIL on W_TAIL
RES['tail'] = dict(
    base=daystats(BASE['s42']['g'], WT, DAY),
    overlay=daystats(GRID[PRIMARY]['g'], WT, DAY),
    archive=daystats(gA0, WT, DAY),
    window="W_TAIL n=%d (NO warm drop)" % int(WT.sum()))
log("tail", json.dumps(RES['tail'], default=float))
json.dump(RES, open(f"{OUT}/RECEIPT_r13B_stage2.json", "w"), indent=1, default=float)

# ------------------------------------------------------------------ S11 NULLS (turnover + firing matched)
tgt_turn = float((GRID[PRIMARY]['turn_matched'] - BASE['s42']['turn_matched'])[WA].mean())
tgt_fire = int(GRID[PRIMARY]['fire'][WA].sum())
def marg(o): return float((o['turn_matched'] - BASE['s42']['turn_matched'])[WA].mean())
NULLS = {}
specs = []
for k in (1, 2, 3):
    specs.append(("NULL_RELAB%d" % k, dict(bperm=np.random.default_rng([4242, k]).permutation(N), bshift=0)))
for k in (101, 503, 1009):
    specs.append(("NULL_SHIFT%d" % k, dict(bperm=None, bshift=k)))
for nm, sp in specs:
    lo_k, hi_k = 0.0, 8.0
    best = None
    for it in range(13):
        mid = 0.5 * (lo_k + hi_k)
        o = account(BK['s42'], ROWS['s42'], mid, 250, "POST", betamat=BETA[250], **sp)
        mt = marg(o)
        best = (mid, o, mt)
        if abs(mt - tgt_turn) / max(abs(tgt_turn), 1e-12) <= 0.01: break
        if mt < tgt_turn: lo_k = mid
        else: hi_k = mid
    kap, o, mt = best
    d = o['g'] - BASE['s42']['g']
    lo, hi, _ = boot_mean(d, WA, DAY)
    NULLS[nm] = dict(kappa_matched=float(kap), dg=float(d[WA].mean()), ci95=[lo, hi],
                     dturn_matched=mt, dturn_rel_err=float((mt - tgt_turn)/abs(tgt_turn)),
                     fire_n=int(o['fire'][WA].sum()), fire_target=tgt_fire,
                     mean_abs_theta=float(np.nanmean(np.abs(o['theta'][WA]))),
                     mean_abs_theta_real=float(np.nanmean(np.abs(GRID[PRIMARY]['theta'][WA]))),
                     Bhat_reduction_pct=float(100*(1 - np.nanmean(np.abs(o['Bhat_post'][WA]))
                                                     / np.nanmean(np.abs(o['Bhat'][WA])))))
    log("NULL", nm, "kappa %.4f dg %+.4f dturn %+.6f (target %+.6f) fire %d/%d"
        % (kap, NULLS[nm]['dg'], mt, tgt_turn, NULLS[nm]['fire_n'], tgt_fire))
RES['nulls'] = NULLS
RES['nulls_target'] = dict(dturn_matched=tgt_turn, fire_n=tgt_fire,
                           real_dg=RES['grid'][PRIMARY]['dg'])
RES['nulls_beaten'] = int(sum(1 for v in NULLS.values() if RES['grid'][PRIMARY]['dg'] > v['dg']))

# ------------------------------------------------------------------ S12 rho to A0 and XIB_LAG50
ZX = np.load(XIB, allow_pickle=True)
XC = [str(c) for c in ZX['cols']]; XR = ZX['d30_n2_c42_rec']
xts = XR[:, XC.index('ts')].astype(np.int64)
gX = XR[:, XC.index('net_ex')] / XR[:, XC.index('gross_total')]
xmap = {int(t): i for i, t in enumerate(xts)}
sel = np.array([xmap.get(int(t), -1) for t in TS])
okx = sel >= 0
gXal = np.full(len(TS), np.nan); gXal[okx] = gX[sel[okx]]
dov = GRID[PRIMARY]['g'] - BASE['s42']['g']
dxib = gXal - gA0
def rho(a, b, msk):
    k = msk & np.isfinite(a) & np.isfinite(b)
    return float(np.corrcoef(a[k], b[k])[0, 1]), int(k.sum())
RES['rho'] = dict(
    d_vs_gA0=rho(dov, gA0, WA), g_overlay_vs_gA0=rho(GRID[PRIMARY]['g'], gA0, WA),
    d_vs_dXIB=rho(dov, dxib, WA), gXIB_vs_gA0=rho(gXal, gA0, WA),
    d_vs_gXIB=rho(dov, gXal, WA),
    xib_file=XIB, xib_sha256=INPUT_SHAS[XIB]['sha256'],
    note="d = overlay increment. |rho(d, dXIB)| >= 0.60 would mean the overlay is the same "
         "alpha re-weighting in disguise (prereg 8).")
log("rho", json.dumps(RES['rho'], default=float))

# ------------------------------------------------------------------ S13 variants + second seed
VAR = {}
VAR['R_pre_reshape'] = account(BK['s42'], ROWS['s42'], 1.00, 250, "PRE")
VAR['BAND'] = account(BK['s42'], ROWS['s42'], 1.00, 250, "BAND")
RES['variants'] = {k: armstats(v, BASE['s42']) for k, v in VAR.items()}
o27 = account(BK['s2027'], ROWS['s2027'], 1.00, 250, "POST")
d27 = o27['g'] - BASE['s2027']['g']
lo, hi, se = boot_mean(d27, WA, DAY)
gt27 = BK['s2027']['gt']
RES['seed_s2027'] = dict(dg=float(d27[WA].mean()), ci95=[lo, hi], boot_se=se,
    dturn_matched=float((o27['turn_matched']-BASE['s2027']['turn_matched'])[WA].mean()),
    dturn_pct=float((o27['turn_matched']-BASE['s2027']['turn_matched'])[WA].mean()
                    / BASE['s2027']['turn_matched'][WA].mean()*100),
    sharpe_ov=float(o27['g'][WA].mean()/o27['g'][WA].std(ddof=1)*np.sqrt(2190)),
    sharpe_base=float(BASE['s2027']['g'][WA].mean()/BASE['s2027']['g'][WA].std(ddof=1)*np.sqrt(2190)),
    exante_gap_reduction_pct=float(100*(1 - np.nanmean(np.abs(o27['bL_post'][WA]-o27['bS_post'][WA]))
                                          / np.nanmean(np.abs(o27['bL'][WA]-o27['bS'][WA])))),
    dg_reprice_3p2167=float(((o27['net']-2.2167*o27['cost']
                              -(BASE['s2027']['net']-2.2167*BASE['s2027']['cost']))/gt27)[WA].mean()),
    tail=daystats(o27['g'], WT, DAY))
log("seed s2027", json.dumps(RES['seed_s2027'], default=float))

# ------------------------------------------------------------------ S14 identity check (r12 eq)
rLb, rSb, EXb, SEb = halves(BASE['s42'])
idn = float(np.nanmax(np.abs(EXb + SEb - BASE['s42']['pnl']/GT42)))
RES['r12_identity_maxabs_rebuilt'] = idn
BRmask = E['BROADRALLY R24>=+2%&B>=.60'] & WA
rLo, rSo, EXo, SEo = halves(GRID[PRIMARY])
RES['broad_rally_decomposition'] = dict(
    n=int(BRmask.sum()),
    base=dict(g=float(BASE['s42']['g'][BRmask].mean()), expo=float(np.nanmean(EXb[BRmask])),
              sele=float(np.nanmean(SEb[BRmask])), rL=float(np.nanmean(rLb[BRmask])),
              rS=float(np.nanmean(rSb[BRmask])), gL=float(BASE['s42']['gL'][BRmask].mean()),
              gS=float(BASE['s42']['gS'][BRmask].mean())),
    overlay=dict(g=float(GRID[PRIMARY]['g'][BRmask].mean()), expo=float(np.nanmean(EXo[BRmask])),
                 sele=float(np.nanmean(SEo[BRmask])), rL=float(np.nanmean(rLo[BRmask])),
                 rS=float(np.nanmean(rSo[BRmask])), gL=float(GRID[PRIMARY]['gL'][BRmask].mean()),
                 gS=float(GRID[PRIMARY]['gS'][BRmask].mean())))
RES['gpu_end'] = gpu()
RES['built_utc'] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
RES['wall_s'] = time.time() - t0
json.dump(RES, open(f"{OUT}/RECEIPT_r13B_full.json", "w"), indent=1, default=float)
np.savez_compressed(f"{OUT}/r13B_series.npz", ts=TS,
    g_base=BASE['s42']['g'], g_primary=GRID[PRIMARY]['g'], theta=GRID[PRIMARY]['theta'],
    Bhat=GRID[PRIMARY]['Bhat'], Bhat_post=GRID[PRIMARY]['Bhat_post'],
    bL=GRID[PRIMARY]['bL'], bS=GRID[PRIMARY]['bS'],
    bL_post=GRID[PRIMARY]['bL_post'], bS_post=GRID[PRIMARY]['bS_post'],
    turn_base=BASE['s42']['turn_matched'], turn_primary=GRID[PRIMARY]['turn_matched'],
    A_ew=Anow, WA=WA, WT=WT)
log("DONE")
print("RESULT_JSON_AT", f"{OUT}/RECEIPT_r13B_full.json")
