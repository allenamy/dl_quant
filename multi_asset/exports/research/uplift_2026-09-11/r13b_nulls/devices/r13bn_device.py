#!/usr/bin/env python3
"""r13b-nulls: the six turnover-matched nulls (and the real arm, and BASE) scored on sd / tail,
in ONE run on the SAME device code (r13b_core.py head, exec'd verbatim), plus the de-levering
control, year fixed effects, the C1 vol-costume arm and the leverage-headroom uncertainty.

Frozen by PREREG_r13b_nulls_on_sd_2026-09-12.md (sha asserted below). READ-ONLY. CPU ONLY.
Live tree never touched. Writes only under /workspace/uplift_2026-09-11/r13b_nulls/receipts/.
"""
import os, sys, json, time, hashlib, subprocess, math

# ------------------------------------------------------------------ E-0826-D env whitelist (argv[1])
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "device must be launched with an explicit, non-empty env whitelist as argv[1]"
BANNED = ('CAL','JUDGE','UPLIFT','PANEL','LOOK','WRULE','LEGS','PHI','FSEED','W3FIX','FTRIM',
          'UMASK','SLOW','FPRED','MEMBERS_TOPN','COSTB','SLEEVE','KMOD','SEAT','RNSM','LTRIM',
          'CDAMP','FUNDSCALE','FEMAT','TRADE_TOPN','REF_SKIP','PYTHON','OMP','MKL')
EXTRA = sorted(k for k in os.environ if k not in WHITE); assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
BAN = sorted(k for k in os.environ if k.startswith(BANNED)); assert BAN == [], ("CALIBER FLAG PRESENT", BAN)
ENV = dict(env_whitelist=sorted(WHITE), env_whitelist_n=len(WHITE), env_extra=EXTRA, env_banned=BAN,
           env_actual={k: os.environ[k] for k in sorted(os.environ)},
           env_banned_prefixes=sorted(BANNED), launch_cmdline=" ".join(sys.argv))
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
ENV.update(python=sys.version.split()[0], numpy=np.__version__)

def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''): h.update(b)
    return h.hexdigest()
def gpu():
    try:
        return subprocess.check_output(["nvidia-smi","--query-gpu=utilization.gpu,memory.used",
                                        "--format=csv,noheader"], text=True).strip()
    except Exception as e:
        return "nvidia-smi unavailable: %s" % e
GPU_START = gpu()
t0 = time.time()
HERE = os.path.dirname(os.path.abspath(__file__)); R = os.path.abspath(os.path.join(HERE, '..'))
OUTD = os.path.join(R, "receipts"); os.makedirs(OUTD, exist_ok=True)
LOGF = open(os.path.join(OUTD, "r13bn_run.log"), "a")
def log(*a):
    s = "[%7.1fs] " % (time.time()-t0) + " ".join(str(x) for x in a)
    print(s, flush=True); LOGF.write(s + "\n"); LOGF.flush()

# ------------------------------------------------------------------ frozen hashes
PREREG = os.path.join(R, "PREREG_r13b_nulls_on_sd_2026-09-12.md")
PREREG_SHA = "de9d981465ff93b874cc49c924997e2c3132a8e6d401a9e36df5aa46a7f8395f"
CORE = "/workspace/uplift_2026-09-11/r13_B_withinhalf/devices/r13b_core.py"
CORE_SHA = "54d98f8cf2ac16493387d767a1f614e9507cf09b5cf58fa9535ac95879b5a375"
SER = "/workspace/uplift_2026-09-11/r13_B_withinhalf/r13B_series.npz"
SER_SHA = "f1b84e2796cf59d7036f229d6a9ba432daec53632f1b1570814391259bd68aa1"
FULL = "/workspace/uplift_2026-09-11/r13_B_withinhalf/RECEIPT_r13B_full.json"
FULL_SHA = "c8614f7a45ad9dd9eb702fe310f1b373e93a2239a6aab0f068995194fa6f24f8"
assert sha(PREREG) == PREREG_SHA, ("PREREG HASH MISMATCH", sha(PREREG))
assert sha(CORE) == CORE_SHA, ("r13b_core.py HASH MISMATCH", sha(CORE))
assert sha(SER) == SER_SHA, ("r13B_series.npz HASH MISMATCH", sha(SER))
assert sha(FULL) == FULL_SHA, ("RECEIPT_r13B_full.json HASH MISMATCH", sha(FULL))
log("hashes OK: prereg", PREREG_SHA[:16], "core", CORE_SHA[:16], "series", SER_SHA[:16])

# ------------------------------------------------------------------ exec the archived core head (S1..S5)
src = open(CORE).read()
cut = src.index("# ------------------------------------------------------------------ S6 statistics")
ns = {'__file__': CORE, '__name__': 'r13b_core_head'}
_argv_saved = list(sys.argv); sys.argv = [CORE, _argv_saved[1]]
exec(compile(src[:cut], "r13b_core_head", "exec"), ns)
sys.argv = _argv_saved
load_book, static_rows, reshape_ex, overlay, account = (ns[k] for k in
    ('load_book','static_rows','reshape_ex','overlay','account'))
BETA = ns['BETA']; A = ns['A']; T = ns['T']; N = ns['N']; E_ts = ns['E_ts']
Cn, Cy, Cyy, Crow = ns['Cn'], ns['Cy'], ns['Cyy'], ns['Crow']
UB = ns['UB']; BOOKS = ns['BOOKS']
log("core head exec'd; T,N =", T, N, "; A_ew parity", ns['A_PARITY'], "; beta prefix parity", ns['PRE_PARITY'])

# ------------------------------------------------------------------ book, rows, windows
BK = load_book('s42'); ROWS = static_rows(BK, 's42')
TS = BK['ts']; WT = TS <= UB; WA = WT.copy(); WA[:900] = False
assert int(WT.sum()) == 10038 and int(WA.sum()) == 9138, (int(WT.sum()), int(WA.sum()))
DAY = np.array([time.strftime('%Y%m%d', time.gmtime(int(t))) for t in TS])
YEAR = np.array([time.gmtime(int(t)).tm_year for t in TS])
YM = np.array([time.strftime('%Y%m', time.gmtime(int(t))) for t in TS])
GT = BK['gt']
IDX_META = np.array([r['i'] for r in ROWS]); Anow = A[IDX_META]; Abps = Anow * 1e4

# ------------------------------------------------------------------ BASE + REAL, bitwise parity gate
BASE = account(BK, ROWS, 0.0, 250, "POST")
REAL = account(BK, ROWS, 1.00, 250, "POST")
Z = np.load(SER)
assert np.array_equal(Z['ts'].astype(np.int64), TS)
PAR = dict(g_base_bitwise=bool(np.array_equal(BASE['g'], Z['g_base'])),
           g_primary_bitwise=bool(np.array_equal(REAL['g'], Z['g_primary'])),
           g_base_maxabs=float(np.abs(BASE['g'] - Z['g_base']).max()),
           g_primary_maxabs=float(np.abs(REAL['g'] - Z['g_primary']).max()),
           theta_primary_maxabs=float(np.nanmax(np.abs(REAL['theta'] - Z['theta']))),
           WA_equal=bool(np.array_equal(WA, Z['WA'].astype(bool))), WT_equal=bool(np.array_equal(WT, Z['WT'].astype(bool))),
           A_ew_equal=bool(np.array_equal(Anow, Z['A_ew'])))
log("PARITY GATE", PAR)
assert PAR['g_base_bitwise'] and PAR['g_primary_bitwise'] and PAR['WA_equal'] and PAR['WT_equal'] and PAR['A_ew_equal'], PAR
gB, gR = BASE['g'], REAL['g']

# ------------------------------------------------------------------ nulls: verbatim S11 bisection
FULLR = json.load(open(FULL))
tgt_turn = float((REAL['turn_matched'] - BASE['turn_matched'])[WA].mean())
tgt_fire = int(REAL['fire'][WA].sum())
assert abs(tgt_turn - FULLR['nulls_target']['dturn_matched']) < 1e-15 and tgt_fire == FULLR['nulls_target']['fire_n']
def marg(o): return float((o['turn_matched'] - BASE['turn_matched'])[WA].mean())
def bisect_kappa(sp, betamat):
    lo_k, hi_k = 0.0, 8.0
    best = None; trace = []
    for it in range(13):
        mid = 0.5 * (lo_k + hi_k)
        o = account(BK, ROWS, mid, 250, "POST", betamat=betamat, **sp)
        mt = marg(o)
        best = (mid, o, mt); trace.append([mid, mt])
        if abs(mt - tgt_turn) / max(abs(tgt_turn), 1e-12) <= 0.01: break
        if mt < tgt_turn: lo_k = mid
        else: hi_k = mid
    return best, trace
ARMS = {"BASE": BASE, "REAL": REAL}
KAPPA = {"BASE": 0.0, "REAL": 1.00}
MATCH = {}
specs = []
for k in (1, 2, 3):
    specs.append(("NULL_RELAB%d" % k, dict(bperm=np.random.default_rng([4242, k]).permutation(N), bshift=0)))
for k in (101, 503, 1009):
    specs.append(("NULL_SHIFT%d" % k, dict(bperm=None, bshift=k)))
for nm, sp in specs:
    (kap, o, mt), tr = bisect_kappa(sp, BETA[250])
    ARMS[nm] = o; KAPPA[nm] = float(kap)
    arch = FULLR['nulls'][nm]
    MATCH[nm] = dict(kappa_matched=float(kap), kappa_archived=arch['kappa_matched'],
                     kappa_equal_archived=bool(kap == arch['kappa_matched']),
                     dturn_matched=mt, dturn_target=tgt_turn, dturn_rel_err=float((mt - tgt_turn)/abs(tgt_turn)),
                     fire_n=int(o['fire'][WA].sum()), fire_target=tgt_fire,
                     fire_rel_err=float(int(o['fire'][WA].sum())/tgt_fire - 1),
                     dg=float((o['g'] - gB)[WA].mean()), dg_archived=arch['dg'],
                     mean_abs_theta=float(np.nanmean(np.abs(o['theta'][WA]))), mean_abs_theta_archived=arch['mean_abs_theta'],
                     clipped_mean=float(o['clipped'][WA].mean()), exact_frac=float(o['exact'][WA].mean()),
                     Bhat_reduction_pct=float(100*(1 - np.nanmean(np.abs(o['Bhat_post'][WA]))/np.nanmean(np.abs(o['Bhat'][WA])))),
                     Bhat_reduction_pct_archived=arch['Bhat_reduction_pct'],
                     bisection_trace=tr, n_bisection_calls=len(tr))
    log("NULL", nm, "kappa %.6f (archived %.6f, equal=%s) dturn rel err %+.4f fire %d/%d dg %+.4f"
        % (kap, arch['kappa_matched'], MATCH[nm]['kappa_equal_archived'], MATCH[nm]['dturn_rel_err'],
           MATCH[nm]['fire_n'], tgt_fire, MATCH[nm]['dg']))
assert all(MATCH[n]['kappa_equal_archived'] for n in MATCH), "null kappa differs from archived build -> not the same run"
assert all(abs(MATCH[n]['dturn_rel_err']) <= 0.01 for n in MATCH)

# ------------------------------------------------------------------ C1 vol-costume arm (additional; separate)
def vol_at(i, W):
    lo, hi = i - W, i
    if lo < 0: return np.full(N, np.nan)
    nrow = Crow[hi] - Crow[lo]
    if nrow < 5: return np.full(N, np.nan)
    n = Cn[hi] - Cn[lo]; Sy = Cy[hi] - Cy[lo]; Syy = Cyy[hi] - Cyy[lo]
    with np.errstate(invalid='ignore', divide='ignore'):
        my = Sy / n; var = Syy / n - my * my
    bad = (n < 0.8 * nrow) | ~np.isfinite(var) | (var <= 0)
    return np.where(bad, np.nan, np.sqrt(np.where(bad, 1.0, var)))
VOL = np.full((T, N), np.nan, np.float32)
for i in range(250, T): VOL[i] = vol_at(i, 250)
log("VOL matrix built, finite frac %.4f (beta finite frac %.4f)" % (float(np.isfinite(VOL).mean()), float(np.isfinite(BETA[250]).mean())))
(kapC, oC, mtC), trC = bisect_kappa(dict(bperm=None, bshift=0), VOL)
ARMS["C1_VOL"] = oC; KAPPA["C1_VOL"] = float(kapC)
MATCH["C1_VOL"] = dict(kappa_matched=float(kapC), dturn_matched=mtC, dturn_target=tgt_turn,
                       dturn_rel_err=float((mtC - tgt_turn)/abs(tgt_turn)), fire_n=int(oC['fire'][WA].sum()), fire_target=tgt_fire,
                       fire_rel_err=float(int(oC['fire'][WA].sum())/tgt_fire - 1), dg=float((oC['g'] - gB)[WA].mean()),
                       mean_abs_theta=float(np.nanmean(np.abs(oC['theta'][WA]))), mean_theta=float(np.nanmean(oC['theta'][WA])),
                       clipped_mean=float(oC['clipped'][WA].mean()), exact_frac=float(oC['exact'][WA].mean()),
                       volgap_reduction_pct=float(100*(1 - np.nanmean(np.abs(oC['Bhat_post'][WA]))/np.nanmean(np.abs(oC['Bhat'][WA])))),
                       bisection_trace=trC, n_bisection_calls=len(trC),
                       note="Bhat here is the book's ex-ante long-minus-short VOL exposure (sigma in place of beta)")
log("C1_VOL kappa %.6f dturn rel err %+.4f fire %d/%d dg %+.4f" % (kapC, MATCH['C1_VOL']['dturn_rel_err'], MATCH['C1_VOL']['fire_n'], tgt_fire, MATCH['C1_VOL']['dg']))
ARM_ORDER = ["BASE", "REAL"] + [s[0] for s in specs] + ["C1_VOL"]
NULL_NAMES = [s[0] for s in specs]

# ------------------------------------------------------------------ statistics helpers (mirroring r13b_tail / r13v_judge)
NB = 2000
def days_of(mask):
    dd = {}
    for k in np.nonzero(mask)[0]: dd.setdefault(DAY[k], []).append(k)
    return [np.array(v) for _, v in sorted(dd.items())]
BY_WA = days_of(WA)
def boot_stat(fn, by):
    nd = len(by); out = np.empty(NB)
    for k in range(NB):
        r = np.random.default_rng([20260905, k]).integers(0, nd, nd)
        idx = np.concatenate([by[i] for i in r])
        out[k] = fn(idx)
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5)), float(out.std(ddof=1))
def maxdd_anchor(g, L):
    eq = np.concatenate([[1.0], np.cumprod(1.0 + L * g * 1e-4)])
    return float((1 - eq / np.maximum.accumulate(eq)).max())
def maxdd_from_daily(dr):
    eq = np.concatenate([[1.0], np.cumprod(1.0 + dr)])
    return float((1 - eq / np.maximum.accumulate(eq)).max())
def rolling_maxdd(dr, W=365):
    eq = np.concatenate([[1.0], np.cumprod(1.0 + dr)])
    win = sliding_window_view(eq, W + 1)
    rel = win / win[:, :1]
    return (1 - rel / np.maximum.accumulate(rel, axis=1)).max(axis=1)
def daymat(g, mask):
    """(n_days, kmax) zero-padded matrix of anchor g's per UTC day, in day order."""
    by = days_of(mask); kmax = max(len(b) for b in by)
    M = np.zeros((len(by), kmax))
    for j, b in enumerate(by): M[j, :len(b)] = g[b]
    return [DAY[b[0]] for b in by], M
def dayret_from_mat(M, L): return np.prod(1.0 + L * M * 1e-4, axis=1) - 1.0
def risk_block(keys, M, g_anchor_masked, L):
    dr = dayret_from_mat(M, L); nd = len(dr); yrs = nd / 365.0
    halt = int((dr <= -0.04).sum()); alert = int((dr <= -0.0268).sum())
    dds = rolling_maxdd(dr) if nd >= 365 else np.array([maxdd_from_daily(dr)])
    w = int(np.argmin(dr))
    return dict(lev=float(L), n_days=nd, halt=halt, halt_per_yr=halt/yrs, alert=alert, alert_per_yr=alert/yrs,
                worst_day=keys[w], worst_day_ret=float(dr[w]), maxDD_daily=maxdd_from_daily(dr),
                maxDD_anchor=maxdd_anchor(g_anchor_masked, L) if g_anchor_masked is not None else None,
                n_1y_windows=int(len(dds)), P_1y_maxDD_ge_25=float((dds >= 0.25).mean()),
                median_1y_maxDD=float(np.median(dds)), p90_1y_maxDD=float(np.percentile(dds, 90)),
                sd_day=float(dr.std(ddof=1)), p01_day=float(np.percentile(dr, 1)), p05_day=float(np.percentile(dr, 5)),
                crit_halt_le_1=bool(halt/yrs <= 1.0), crit_P25_le_10pct=bool((dds >= 0.25).mean() <= 0.10),
                CRITERION_PASS=bool(halt/yrs <= 1.0 and (dds >= 0.25).mean() <= 0.10))
def vardec(g, mk):
    a = Abps[mk]; y = g[mk]; ok = np.isfinite(a)
    X = np.column_stack([np.ones(ok.sum()), a[ok]]); b, *_ = np.linalg.lstsq(X, y[ok], rcond=None)
    res = y[ok] - X @ b
    return dict(n=int(ok.sum()), beta=float(b[1]), var_total=float(y[ok].var(ddof=1)),
                var_explained_by_A=float(b[1]**2 * a[ok].var(ddof=1)), var_resid=float(res.var(ddof=1)))
def fe_resid(g, keys, mask):
    out = np.full(len(g), np.nan)
    for kk in set(keys[mask].tolist()):
        m = mask & (keys == kk); out[m] = g[m] - g[m].mean()
    return out
def shrp(x): return float(x.mean()/x.std(ddof=1)*np.sqrt(2190))
def annual_from_mat(MA, nWA, L): return float(np.prod(dayret_from_mat(MA, L) + 1.0) ** (2190.0/nWA) - 1.0)

# parity of the vectorised tail machinery against the verdict device's loop forms
KEYS_T, MB = daymat(gB, WT); _, MR = daymat(gR, WT)
_dr_loop = np.array([np.prod(1.0 + 2.0*gB[np.array(b)]*1e-4) - 1.0 for b in days_of(WT)])
assert np.abs(dayret_from_mat(MB, 2.0) - _dr_loop).max() < 1e-15
_dd_loop = np.array([maxdd_from_daily(_dr_loop[i:i+365]) for i in range(0, 40)])
assert np.abs(rolling_maxdd(_dr_loop)[:40] - _dd_loop).max() < 1e-14
rbB = risk_block(KEYS_T, MB, gB[WT], 2.0); rbR = risk_block(KEYS_T, MR, gR[WT], 2.0)
VER = dict(base_halt=rbB['halt'], base_maxDD_anchor=rbB['maxDD_anchor'], base_P25=rbB['P_1y_maxDD_ge_25'],
           real_halt=rbR['halt'], real_maxDD_anchor=rbR['maxDD_anchor'], real_P25=rbR['P_1y_maxDD_ge_25'])
assert rbB['halt'] == 6 and rbR['halt'] == 2 and abs(rbB['maxDD_anchor'] - 0.46417931631583276) < 1e-12 \
    and abs(rbR['maxDD_anchor'] - 0.37429278944720323) < 1e-12 and abs(rbB['P_1y_maxDD_ge_25'] - 0.2696715049656226) < 1e-12 \
    and abs(rbR['P_1y_maxDD_ge_25'] - 0.2077922077922078) < 1e-12 and abs(rbB['maxDD_daily'] - 0.45985804439548505) < 1e-12, VER
log("tail machinery parity vs archived build/verdict OK", VER)

# ------------------------------------------------------------------ per-arm W_ALPHA sd block + W_TAIL tail block
sdB = float(gB[WA].std(ddof=1)); dREAL = 1.0 - float(gR[WA].std(ddof=1))/sdB
YEARS = sorted(set(YEAR[WT].tolist()))
gB_FEy = fe_resid(gB, YEAR, WA); gB_FEm = fe_resid(gB, YM, WA)
STATS = {}; SERIES = {}
for nm in ARM_ORDER:
    g = ARMS[nm]['g']; x = g[WA]
    sd = float(x.std(ddof=1)); d = 1.0 - sd/sdB
    lo, hi, se = boot_stat(lambda i: 1.0 - g[i].std(ddof=1)/gB[i].std(ddof=1), BY_WA) if nm != "BASE" else (0.0, 0.0, 0.0)
    gFEy = fe_resid(g, YEAR, WA); gFEm = fe_resid(g, YM, WA)
    sdFEy = float(np.nanstd(gFEy[WA], ddof=1)); sdFEm = float(np.nanstd(gFEm[WA], ddof=1))
    loF, hiF, _ = boot_stat(lambda i: 1.0 - np.nanstd(gFEy[i], ddof=1)/np.nanstd(gB_FEy[i], ddof=1), BY_WA) if nm != "BASE" else (0.0, 0.0, 0.0)
    keys, M = daymat(g, WT)
    rb = risk_block(keys, M, g[WT], 2.0)
    by_year = {}
    for y in YEARS:
        mA = WA & (YEAR == y); mT = WT & (YEAR == y)
        ky, My = daymat(g, mT); ry = risk_block(ky, My, g[mT], 2.0)
        by_year[str(y)] = dict(n_alpha=int(mA.sum()), n_tail_days=ry['n_days'],
            sd=float(g[mA].std(ddof=1)), sd_base=float(gB[mA].std(ddof=1)),
            sd_rel_change_pct=float(100*(g[mA].std(ddof=1)/gB[mA].std(ddof=1) - 1)),
            mean=float(g[mA].mean()), mean_base=float(gB[mA].mean()), dg=float((g - gB)[mA].mean()),
            sharpe=shrp(g[mA]), sharpe_base=shrp(gB[mA]),
            halt=ry['halt'], alert=ry['alert'], worst_day=ry['worst_day'], worst_day_ret=ry['worst_day_ret'],
            maxDD_anchor_within_year=ry['maxDD_anchor'], sd_day=ry['sd_day'],
            vardec=vardec(g, mA), vardec_base=vardec(gB, mA))
    STATS[nm] = dict(kappa=KAPPA[nm],
        W_ALPHA=dict(n=int(WA.sum()), mean_g=float(x.mean()), dg=float((g - gB)[WA].mean()), sharpe=shrp(x),
                     sd=sd, sd_base=sdB, sd_reduction=d, sd_reduction_pct=100*d,
                     sd_reduction_over_REAL=(d/dREAL if dREAL else np.nan),
                     sd_reduction_ci95=[lo, hi], sd_reduction_boot_se=se,
                     sd_yearFE=sdFEy, sd_yearFE_base=float(np.nanstd(gB_FEy[WA], ddof=1)),
                     sd_yearFE_reduction=1.0 - sdFEy/float(np.nanstd(gB_FEy[WA], ddof=1)),
                     sd_yearFE_reduction_ci95=[loF, hiF],
                     sd_monthFE=sdFEm, sd_monthFE_base=float(np.nanstd(gB_FEm[WA], ddof=1)),
                     sd_monthFE_reduction=1.0 - sdFEm/float(np.nanstd(gB_FEm[WA], ddof=1)),
                     turn_matched=float(ARMS[nm]['turn_matched'][WA].mean()),
                     dturn_matched=float((ARMS[nm]['turn_matched'] - BASE['turn_matched'])[WA].mean()),
                     vardec_pooled=vardec(g, WA)),
        W_TAIL_at_2p00=rb, by_year=by_year)
    SERIES[nm] = g
    log("ARM %-14s kappa %.4f | sd %.4f (%+.2f%%, CI [%+.2f%%,%+.2f%%]) yearFE %+.2f%% | halt %d worst %s %.3f%% maxDD %.4f P25 %.2f%%"
        % (nm, KAPPA[nm], sd, 100*d, 100*lo, 100*hi, 100*STATS[nm]['W_ALPHA']['sd_yearFE_reduction'],
           rb['halt'], rb['worst_day'], 100*rb['worst_day_ret'], rb['maxDD_anchor'], 100*rb['P_1y_maxDD_ge_25']))

# ------------------------------------------------------------------ variance-reduction attribution (A-explained vs residual) per year
VR = {}
for nm in ARM_ORDER:
    if nm == "BASE": continue
    rows = {}
    for lab in ["W_ALPHA"] + [str(y) for y in YEARS]:
        vb = STATS['BASE']['by_year'][lab]['vardec'] if lab != "W_ALPHA" else STATS['BASE']['W_ALPHA']['vardec_pooled']
        va = STATS[nm]['by_year'][lab]['vardec'] if lab != "W_ALPHA" else STATS[nm]['W_ALPHA']['vardec_pooled']
        dtot = vb['var_total'] - va['var_total']; dA = vb['var_explained_by_A'] - va['var_explained_by_A']
        rows[lab] = dict(d_var_total=dtot, d_var_A_explained=dA, d_var_resid=vb['var_resid'] - va['var_resid'],
                         share_A_explained=(dA/dtot if dtot else np.nan))
    sy = sum(rows[str(y)]['d_var_total'] for y in YEARS); sA = sum(rows[str(y)]['d_var_A_explained'] for y in YEARS)
    rows['sum_of_years'] = dict(d_var_total=sy, d_var_A_explained=sA, d_var_resid=sy - sA, share_A_explained=(sA/sy if sy else np.nan))
    VR[nm] = rows

# ------------------------------------------------------------------ mechanism diagnostics: HHI, sigma-weighted gross, beta staleness
rng_d = np.random.default_rng([20260905, 31]); SAMP = sorted(set(int(k) for k in rng_d.integers(1000, len(ROWS), 300)))
def weights_for(nm, k):
    r = ROWS[k]; sm = BK['W'][k].astype(np.float64); G = GT[k]; smr = reshape_ex(sm)
    if nm == "BASE": return smr, r
    u = smr / G
    if nm == "C1_VOL": BM, bshift, bperm = VOL, 0, None
    else:
        sp = dict(specs).get(nm, dict(bperm=None, bshift=0)); BM, bshift, bperm = BETA[250], sp['bshift'], sp['bperm']
    bi = r['i'] - bshift
    b = BM[bi] if 0 <= bi < T else np.full(N, np.nan, np.float32)
    if bperm is not None:
        bp = np.full(N, np.nan, np.float32); bp[bperm] = b; b = bp
    up, _ = overlay(u, r['m'], b, KAPPA[nm]); return up * G, r
DIAG = {}
for nm in ARM_ORDER:
    hhi, volw, cov, pchk = [], [], [], []
    for k in SAMP:
        v, r = weights_for(nm, k); m = r['m']; G = GT[k]; u = v[m] / G
        sg = VOL[r['i']][m].astype(np.float64); fin = np.isfinite(sg)
        hhi.append(float((u**2).sum())); volw.append(float((np.abs(u[fin]) * sg[fin]).sum() / max(np.abs(u[fin]).sum(), 1e-12)))
        cov.append(float(np.abs(u[fin]).sum()))
        pchk.append(abs(float((v[m] * r['yv'] * 1e4).sum()) - ARMS[nm]['pnl'][k]))
    DIAG[nm] = dict(n_sample=len(SAMP), HHI_mean=float(np.mean(hhi)), eff_names=float(1.0/np.mean(hhi)),
                    gross_weighted_mean_sigma=float(np.mean(volw)), sigma_coverage_of_gross=float(np.mean(cov)),
                    pnl_parity_maxabs=float(max(pchk)))
    assert DIAG[nm]['pnl_parity_maxabs'] < 1e-9, (nm, DIAG[nm])
for nm in ARM_ORDER:
    DIAG[nm]['HHI_rel_to_BASE_pct'] = 100*(DIAG[nm]['HHI_mean']/DIAG['BASE']['HHI_mean'] - 1)
    DIAG[nm]['gross_weighted_mean_sigma_rel_to_BASE_pct'] = 100*(DIAG[nm]['gross_weighted_mean_sigma']/DIAG['BASE']['gross_weighted_mean_sigma'] - 1)
log("DIAG", json.dumps({k: {kk: round(vv, 5) if isinstance(vv, float) else vv for kk, vv in v.items()} for k, v in DIAG.items()}))
def rank(a):
    o = np.argsort(a); r = np.empty(len(a)); r[o] = np.arange(len(a)); return r
STALE = {}
for k in (101, 503, 1009):
    cs, cover = [], []
    for i in range(1300, T, 10):
        b1 = BETA[250][i].astype(np.float64); b0 = BETA[250][i - k].astype(np.float64)
        f = np.isfinite(b1) & np.isfinite(b0)
        cover.append(float(f.sum()/max(np.isfinite(b1).sum(), 1)))
        if f.sum() >= 30: cs.append(float(np.corrcoef(rank(b1[f]), rank(b0[f]))[0, 1]))
    STALE["SHIFT%d" % k] = dict(lag_anchors=k, lag_days=k/6.0, mean_spearman=float(np.mean(cs)), median_spearman=float(np.median(cs)),
                                 n_anchors=len(cs), mean_name_coverage=float(np.mean(cover)))
# beta-vs-sigma cross-sectional relation (is beta a vol proxy?)
_cs = []
for i in range(1300, T, 10):
    b1 = BETA[250][i].astype(np.float64); s1 = VOL[i].astype(np.float64); f = np.isfinite(b1) & np.isfinite(s1)
    if f.sum() >= 30: _cs.append(float(np.corrcoef(rank(b1[f]), rank(s1[f]))[0, 1]))
STALE['beta_vs_sigma_spearman_mean'] = float(np.mean(_cs)); STALE['beta_vs_sigma_spearman_median'] = float(np.median(_cs))
log("STALENESS", json.dumps(STALE))

# ------------------------------------------------------------------ R3: de-levering control
sdR = float(gR[WA].std(ddof=1)); L_sd = 2.0 * sdR / sdB
L_sd_day = 2.0 * rbR['sd_day'] / rbB['sd_day']
keysA, MBA = daymat(np.where(WA, gB, 0.0), WT); _, MRA = daymat(np.where(WA, gR, 0.0), WT); nWA = int(WA.sum())
_, MWA = daymat(WA.astype(np.float64), WT); assert int(MWA.sum()) == nWA
def r3_compare(rb_ctrl, rb_t1):
    comp = dict(halt=dict(ctrl=rb_ctrl['halt'], T1=rb_t1['halt'], ctrl_no_worse=bool(rb_ctrl['halt'] <= rb_t1['halt']), T1_strictly_better=bool(rb_t1['halt'] < rb_ctrl['halt'])),
                worst_day_ret=dict(ctrl=rb_ctrl['worst_day_ret'], T1=rb_t1['worst_day_ret'], ctrl_no_worse=bool(rb_ctrl['worst_day_ret'] >= rb_t1['worst_day_ret']), T1_strictly_better=bool(rb_t1['worst_day_ret'] > rb_ctrl['worst_day_ret'])),
                maxDD_anchor=dict(ctrl=rb_ctrl['maxDD_anchor'], T1=rb_t1['maxDD_anchor'], ctrl_no_worse=bool(rb_ctrl['maxDD_anchor'] <= rb_t1['maxDD_anchor']), T1_strictly_better=bool(rb_t1['maxDD_anchor'] < rb_ctrl['maxDD_anchor'])),
                P25=dict(ctrl=rb_ctrl['P_1y_maxDD_ge_25'], T1=rb_t1['P_1y_maxDD_ge_25'], ctrl_no_worse=bool(rb_ctrl['P_1y_maxDD_ge_25'] <= rb_t1['P_1y_maxDD_ge_25']), T1_strictly_better=bool(rb_t1['P_1y_maxDD_ge_25'] < rb_ctrl['P_1y_maxDD_ge_25'])))
    n_ctrl = sum(int(v['ctrl_no_worse']) for v in comp.values()); n_t1 = sum(int(v['T1_strictly_better']) for v in comp.values())
    verdict = "CLOSED_dominated_by_delever" if n_ctrl >= 3 else ("OPEN_T1_beyond_delever" if n_t1 >= 3 else "INDETERMINATE")
    return dict(metrics=comp, n_ctrl_no_worse_of_4=n_ctrl, n_T1_strictly_better_of_4=n_t1, R3=verdict)
rb_ctrl = risk_block(KEYS_T, MB, gB[WT], L_sd); rb_ctrl_day = risk_block(KEYS_T, MB, gB[WT], L_sd_day)
lo_m, hi_m, _ = boot_stat(lambda i: 2.0*gR[i].mean() - L_sd*gB[i].mean(), BY_WA)
R3 = dict(L_sd=L_sd, L_sd_day=L_sd_day,
          sd_check=dict(sd_base_at_L_sd=L_sd*sdB, sd_T1_at_2=2.0*sdR, sd_day_base_at_L_sd=rb_ctrl['sd_day'], sd_day_T1_at_2=rbR['sd_day']),
          T1_at_2p00=rbR, BASE_at_L_sd=rb_ctrl, BASE_at_L_sd_day=rb_ctrl_day,
          compare_anchor_sd_match=r3_compare(rb_ctrl, rbR), compare_daily_sd_match=r3_compare(rb_ctrl_day, rbR),
          return_side=dict(mean_T1_at_2=2.0*float(gR[WA].mean()), mean_BASE_at_L_sd=L_sd*float(gB[WA].mean()),
                           diff_bps_per_anchor_NAV=2.0*float(gR[WA].mean()) - L_sd*float(gB[WA].mean()), diff_ci95=[lo_m, hi_m],
                           ann_T1_at_2=annual_from_mat(MRA, nWA, 2.0), ann_BASE_at_L_sd=annual_from_mat(MBA, nWA, L_sd),
                           note="reported only; alpha was already rejected and does not enter R3"))
log("R3", json.dumps(dict(L_sd=L_sd, anchor=R3['compare_anchor_sd_match']['R3'], daily=R3['compare_daily_sd_match']['R3'],
                          n_ctrl=R3['compare_anchor_sd_match']['n_ctrl_no_worse_of_4'], n_t1=R3['compare_anchor_sd_match']['n_T1_strictly_better_of_4'])))

# ------------------------------------------------------------------ H: leverage headroom and its uncertainty
def crit_ok_mat(M, L):
    dr = dayret_from_mat(M, L); nd = len(dr)
    if (dr <= -0.04).sum() / (nd/365.0) > 1.0: return False
    dds = rolling_maxdd(dr) if nd >= 365 else np.array([maxdd_from_daily(dr)])
    return bool((dds >= 0.25).mean() <= 0.10)
def max_L_crit_mat(M, steps=30):
    if not crit_ok_mat(M, 0.25): return None
    lo2, hi2 = 0.25, 6.0
    for _ in range(steps):
        m = 0.5*(lo2+hi2)
        if crit_ok_mat(M, m): lo2 = m
        else: hi2 = m
    return lo2
LcB = max_L_crit_mat(MB); LcR = max_L_crit_mat(MR)
assert abs(LcB - 1.6072065117768943) < 1e-9 and abs(LcR - 1.6909867729991674) < 1e-9, (LcB, LcR)
H = dict(point=dict(L_crit_BASE=LcB, L_crit_REAL=LcR, ratio_minus_1=LcR/LcB - 1,
                    ann_BASE_at_Lcrit=annual_from_mat(MBA, nWA, LcB), ann_REAL_at_Lcrit=annual_from_mat(MRA, nWA, LcR),
                    ann_gain_pp=100*(annual_from_mat(MRA, nWA, LcR) - annual_from_mat(MBA, nWA, LcB)),
                    verdict_archived=dict(base=1.6072065117768943, overlay=1.6909867729991674, gain_pp=1.96)))
# (a) paired circular block bootstrap on UTC days (block 30)
nd = MB.shape[0]; BL = 30; nblk = int(math.ceil(nd / BL))
ratios = np.full(NB, np.nan); LB_ = np.full(NB, np.nan); LR_ = np.full(NB, np.nan); GAIN = np.full(NB, np.nan)
nWA_day = MWA.sum(axis=1)
tH = time.time()
for k in range(NB):
    r = np.random.default_rng([20260905, k])
    starts = r.integers(0, nd, nblk)
    idx = np.concatenate([(s + np.arange(BL)) % nd for s in starts])[:nd]
    lb = max_L_crit_mat(MB[idx], steps=30); lr = max_L_crit_mat(MR[idx], steps=30)
    LB_[k] = np.nan if lb is None else lb; LR_[k] = np.nan if lr is None else lr
    if lb is not None and lr is not None:
        ratios[k] = lr/lb - 1
        nw = int(nWA_day[idx].sum())
        if nw > 0: GAIN[k] = 100*(annual_from_mat(MRA[idx], nw, lr) - annual_from_mat(MBA[idx], nw, lb))
    if k % 400 == 0: log("headroom bootstrap rep", k, "elapsed %.0fs" % (time.time()-tH))
ok = np.isfinite(ratios)
H['bootstrap'] = dict(method="paired circular block bootstrap of UTC days, block=30, NB=2000, rng default_rng([20260905,k]); "
                             "L_crit re-solved per rep on both arms with the same day blocks (30-step bisection [0.25,6])",
                      n_valid=int(ok.sum()), n_none=int((~ok).sum()),
                      ratio_minus_1_ci95=[float(np.percentile(ratios[ok], 2.5)), float(np.percentile(ratios[ok], 97.5))],
                      ratio_minus_1_median=float(np.median(ratios[ok])), ratio_minus_1_mean=float(ratios[ok].mean()),
                      P_ratio_gt_0=float((ratios[ok] > 0).mean()), P_ratio_lt_0=float((ratios[ok] < 0).mean()), P_ratio_eq_0=float((ratios[ok] == 0).mean()),
                      L_crit_BASE_ci95=[float(np.nanpercentile(LB_, 2.5)), float(np.nanpercentile(LB_, 97.5))],
                      L_crit_REAL_ci95=[float(np.nanpercentile(LR_, 2.5)), float(np.nanpercentile(LR_, 97.5))],
                      ann_gain_pp_ci95=[float(np.nanpercentile(GAIN, 2.5)), float(np.nanpercentile(GAIN, 97.5))],
                      ann_gain_pp_median=float(np.nanmedian(GAIN)))
log("H bootstrap", json.dumps(H['bootstrap']))
# (b) split-half holdout
yr_day = np.array([int(k[:4]) for k in KEYS_T])
H1 = yr_day <= 2023; H2 = yr_day >= 2024
def half_block(name, fit, ev):
    lb = max_L_crit_mat(MB[fit]); lr = max_L_crit_mat(MR[fit])
    out = dict(fit_days=int(fit.sum()), eval_days=int(ev.sum()), L_crit_BASE_fit=lb, L_crit_REAL_fit=lr,
               headroom_fit=(lr/lb - 1) if (lb and lr) else None)
    for tag, M, L in (("BASE", MB, lb), ("REAL", MR, lr)):
        if L is None: out[tag + "_eval"] = None; continue
        keys_ev = [KEYS_T[i] for i in np.nonzero(ev)[0]]
        out[tag + "_eval_at_fit_L"] = {k: v for k, v in risk_block(keys_ev, M[ev], None, L).items()
                                       if k in ('lev','n_days','halt','halt_per_yr','worst_day','worst_day_ret','maxDD_daily','P_1y_maxDD_ge_25','CRITERION_PASS')}
    lb2 = max_L_crit_mat(MB[ev]); lr2 = max_L_crit_mat(MR[ev])
    out['L_crit_BASE_on_eval'] = lb2; out['L_crit_REAL_on_eval'] = lr2; out['headroom_on_eval'] = (lr2/lb2 - 1) if (lb2 and lr2) else None
    return out
H['split_half'] = {"fit_2022-23_eval_2024-26": half_block("A", H1, H2), "fit_2024-26_eval_2022-23": half_block("B", H2, H1)}
log("H split-half", json.dumps(H['split_half'], default=str))
# (c) leave-one-year-out
H['loyo'] = {}
for y in YEARS:
    fit = yr_day != y; ev = yr_day == y
    lb = max_L_crit_mat(MB[fit]); lr = max_L_crit_mat(MR[fit])
    row = dict(fit_days=int(fit.sum()), eval_days=int(ev.sum()), L_crit_BASE_fit=lb, L_crit_REAL_fit=lr, headroom_fit=(lr/lb - 1) if (lb and lr) else None)
    for tag, M, L in (("BASE", MB, lb), ("REAL", MR, lr)):
        if L is None: continue
        dr = dayret_from_mat(M[ev], L)
        row[tag + "_heldout"] = dict(halt=int((dr <= -0.04).sum()), halt_per_yr=float((dr <= -0.04).sum()/(ev.sum()/365.0)),
                                     maxDD_daily=maxdd_from_daily(dr), worst_day_ret=float(dr.min()))
    H['loyo'][str(y)] = row
H['rule'] = dict(withdraw_if_ci_includes_0=bool(H['bootstrap']['ratio_minus_1_ci95'][0] <= 0.0 <= H['bootstrap']['ratio_minus_1_ci95'][1]),
                 split_half_sign_flip=bool(any((v['headroom_on_eval'] is not None and v['headroom_on_eval'] < 0) or
                                               (v['headroom_fit'] is not None and v['headroom_fit'] < 0) for v in H['split_half'].values())))
H['rule']['WITHDRAWN'] = bool(H['rule']['withdraw_if_ci_includes_0'] or H['rule']['split_half_sign_flip'])

# ------------------------------------------------------------------ frozen reading rules
RULES = dict(dREAL=dREAL, threshold_70pct=0.70*dREAL)
R1 = {nm: dict(sd_reduction=STATS[nm]['W_ALPHA']['sd_reduction'], ratio_to_REAL=STATS[nm]['W_ALPHA']['sd_reduction_over_REAL'],
               fires=bool(STATS[nm]['W_ALPHA']['sd_reduction'] >= 0.70*dREAL)) for nm in NULL_NAMES}
RULES['R1'] = dict(per_null=R1, max_null_sd_reduction=max(v['sd_reduction'] for v in R1.values()),
                   max_null_name=max(R1, key=lambda n: R1[n]['sd_reduction']), FIRES=bool(any(v['fires'] for v in R1.values())))
real_tail = STATS['REAL']['W_TAIL_at_2p00']; base_tail = STATS['BASE']['W_TAIL_at_2p00']
imp_halt = base_tail['halt'] - real_tail['halt']; imp_dd = base_tail['maxDD_anchor'] - real_tail['maxDD_anchor']; imp_p25 = base_tail['P_1y_maxDD_ge_25'] - real_tail['P_1y_maxDD_ge_25']
R2 = {}
for nm in NULL_NAMES + ["C1_VOL"]:
    tb = STATS[nm]['W_TAIL_at_2p00']
    h = (base_tail['halt'] - tb['halt']) >= 0.70*imp_halt; dd = (base_tail['maxDD_anchor'] - tb['maxDD_anchor']) >= 0.70*imp_dd
    p = (base_tail['P_1y_maxDD_ge_25'] - tb['P_1y_maxDD_ge_25']) >= 0.70*imp_p25
    R2[nm] = dict(halts_removed=base_tail['halt'] - tb['halt'], maxDD_anchor_reduction=base_tail['maxDD_anchor'] - tb['maxDD_anchor'],
                  P25_reduction_pp=100*(base_tail['P_1y_maxDD_ge_25'] - tb['P_1y_maxDD_ge_25']),
                  hits=dict(halt=bool(h), maxDD=bool(dd), P25=bool(p)), n_hits=int(h) + int(dd) + int(p), fires=bool(int(h) + int(dd) + int(p) >= 2))
RULES['R2'] = dict(REAL_improvements=dict(halts_removed=imp_halt, maxDD_anchor_reduction=imp_dd, P25_reduction_pp=100*imp_p25),
                   thresholds=dict(null_halt_le=base_tail['halt'] - 0.70*imp_halt, null_maxDD_le=base_tail['maxDD_anchor'] - 0.70*imp_dd,
                                   null_P25_le_pct=100*(base_tail['P_1y_maxDD_ge_25'] - 0.70*imp_p25)),
                   per_null=R2, FIRES=bool(any(R2[n]['fires'] for n in NULL_NAMES)), C1_would_fire=R2['C1_VOL']['fires'])
RULES['R3'] = dict(verdict_anchor_sd_match=R3['compare_anchor_sd_match']['R3'], verdict_daily_sd_match=R3['compare_daily_sd_match']['R3'],
                   FIRES=bool(R3['compare_anchor_sd_match']['R3'] == "CLOSED_dominated_by_delever"))
RULES['C1'] = dict(sd_reduction=STATS['C1_VOL']['W_ALPHA']['sd_reduction'], ratio_to_REAL=STATS['C1_VOL']['W_ALPHA']['sd_reduction_over_REAL'],
                   FIRES=bool(STATS['C1_VOL']['W_ALPHA']['sd_reduction'] >= 0.70*dREAL))
RULES['R4_descriptive'] = dict(y2026=dict(base={k: STATS['BASE']['by_year']['2026'][k] for k in ('halt','worst_day','worst_day_ret','maxDD_anchor_within_year','sd','mean')},
                                          real={k: STATS['REAL']['by_year']['2026'][k] for k in ('halt','worst_day','worst_day_ret','maxDD_anchor_within_year','sd','mean')}),
                               real_2026_tail_not_better=bool(STATS['REAL']['by_year']['2026']['halt'] >= STATS['BASE']['by_year']['2026']['halt']
                                                              and STATS['REAL']['by_year']['2026']['worst_day_ret'] <= STATS['BASE']['by_year']['2026']['worst_day_ret']
                                                              and STATS['REAL']['by_year']['2026']['maxDD_anchor_within_year'] >= STATS['BASE']['by_year']['2026']['maxDD_anchor_within_year']))
RULES['H_WITHDRAWN'] = H['rule']['WITHDRAWN']
RULES['LIVE_WIRE'] = "CLOSED" if (RULES['R1']['FIRES'] or RULES['R2']['FIRES'] or RULES['R3']['FIRES'] or RULES['C1']['FIRES']) else "ESTABLISHED"
RULES['closed_by'] = [k for k in ('R1','R2','R3','C1') if RULES[k]['FIRES']]
log("RULES", json.dumps(dict(R1=RULES['R1']['FIRES'], R2=RULES['R2']['FIRES'], R3=RULES['R3']['FIRES'], C1=RULES['C1']['FIRES'],
                             H_WITHDRAWN=RULES['H_WITHDRAWN'], LIVE_WIRE=RULES['LIVE_WIRE'], closed_by=RULES['closed_by'])))

# ------------------------------------------------------------------ write
GPU_END = gpu()
OUT = dict(prereg_sha256=PREREG_SHA, device_sha256=sha(os.path.abspath(__file__)),
           reused_device=dict(path=CORE, sha256=CORE_SHA, exec_head_up_to="S6 statistics"),
           inputs=dict(series=dict(path=SER, sha256=SER_SHA), receipt_full=dict(path=FULL, sha256=FULL_SHA),
                       core_head_inputs={p: v['sha256'] for p, v in ns['INPUT_SHAS'].items()}),
           env=ENV, gpu_start=GPU_START, gpu_end=GPU_END, parity_gate=PAR, tail_machinery_parity=VER,
           matching=MATCH, match_target=dict(dturn_matched=tgt_turn, fire_n=tgt_fire, base_turn_matched=float(BASE['turn_matched'][WA].mean())),
           stats=STATS, variance_reduction_attribution=VR, mechanism_diag=DIAG, beta_staleness=STALE,
           R3_delever=R3, H_headroom=H, RULES=RULES, arm_order=ARM_ORDER, null_names=NULL_NAMES,
           windows=dict(W_ALPHA=int(WA.sum()), W_TAIL=int(WT.sum())),
           built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), wall_s=time.time() - t0)
json.dump(OUT, open(os.path.join(OUTD, "RECEIPT_r13bn_nulls_on_sd.json"), "w"), indent=1, default=float)
np.savez_compressed(os.path.join(OUTD, "r13bn_series.npz"), ts=TS, WA=WA, WT=WT, A_ew=Anow, arm_order=np.array(ARM_ORDER),
                    **{"g_" + nm: SERIES[nm] for nm in ARM_ORDER}, **{"theta_" + nm: ARMS[nm]['theta'] for nm in ARM_ORDER},
                    **{"turn_" + nm: ARMS[nm]['turn_matched'] for nm in ARM_ORDER}, kappa=np.array([KAPPA[nm] for nm in ARM_ORDER]))
log("DONE; gpu_end", GPU_END, "wall %.0fs" % OUT['wall_s'])
print("RESULT_JSON_AT", os.path.join(OUTD, "RECEIPT_r13bn_nulls_on_sd.json"))
