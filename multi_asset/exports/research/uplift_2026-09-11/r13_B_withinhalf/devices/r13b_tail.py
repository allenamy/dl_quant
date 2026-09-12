#!/usr/bin/env python3
"""r13-B follow-up - is the TAIL/VOL gain real, or a warm-up artifact?
Consumes ONLY r13B_series.npz written by r13b_core.py (sha asserted below). READ-ONLY.
Frozen by the same prereg + amendments; this file adds NO new arm (K stays 12) - it only
re-reads the PRIMARY arm's own series under the W_TAIL / W_ALPHA split the prereg already fixed."""
import os, sys, json, time, hashlib, calendar
WHITE = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else None
assert WHITE, "explicit env whitelist required"
BANNED = ('CAL','JUDGE','UPLIFT','PANEL','LOOK','WRULE','LEGS','PHI','FSEED','W3FIX','FTRIM',
          'UMASK','SLOW','FPRED','MEMBERS_TOPN','COSTB','SLEEVE','KMOD','SEAT','RNSM','LTRIM',
          'CDAMP','FUNDSCALE','FEMAT','TRADE_TOPN','REF_SKIP','PYTHON','OMP','MKL')
EXTRA = sorted(k for k in os.environ if k not in WHITE); assert EXTRA == [], ("ENV", EXTRA)
BAN = sorted(k for k in os.environ if k.startswith(BANNED)); assert BAN == [], ("FLAG", BAN)
ENV = dict(env_whitelist=sorted(WHITE), env_extra=EXTRA, env_banned=BAN,
           env_actual={k: os.environ[k] for k in sorted(os.environ)},
           env_banned_prefixes=sorted(BANNED), launch_cmdline=" ".join(sys.argv))
import numpy as np
ENV.update(python=sys.version.split()[0], numpy=np.__version__)
H = os.path.dirname(os.path.abspath(__file__)); R = os.path.abspath(os.path.join(H, '..'))
def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''): h.update(b)
    return h.hexdigest()
for f, s in [("PREREG_r13B_withinhalf_2026-09-12.md", "27b0d34c5c55119ba55422a212ec340b1be1bf24af6278564796480d85cbe045"),
             ("PREREG_AMENDMENT_1_2026-09-12.md", "720fa335e62463cbe81b764285e00020c08b81d70bcbf9d5f3ab54ae5098af9d"),
             ("PREREG_AMENDMENT_2_2026-09-12.md", "5b8bc70485784cec3aa39363d6aef62cf7570b6703809fe65a8faa68b06ea5f8")]:
    assert sha(os.path.join(R, f)) == s, ("PREREG HASH", f)
SER = os.path.join(R, "receipts", "r13B_series.npz")
Z = np.load(SER)
ts = Z['ts'].astype(np.int64); gb = Z['g_base']; go = Z['g_primary']
WA = Z['WA'].astype(bool); WT = Z['WT'].astype(bool); Aew = Z['A_ew']
th = Z['theta']; Bh = Z['Bhat']; Bp = Z['Bhat_post']
assert WA.sum() == 9138 and WT.sum() == 10038
DAY = np.array([time.strftime('%Y%m%d', time.gmtime(int(t))) for t in ts])
YR  = np.array([time.gmtime(int(t)).tm_year for t in ts])
NB = 2000
def days_of(mask):
    dd = {}
    for k in np.nonzero(mask)[0]: dd.setdefault(DAY[k], []).append(k)
    return [np.array(v) for _, v in sorted(dd.items())]
def boot_stat(fn, mask, paired=None):
    by = days_of(mask); nd = len(by); out = np.empty(NB)
    for k in range(NB):
        r = np.random.default_rng([20260905, k]).integers(0, nd, nd)
        idx = np.concatenate([by[i] for i in r])
        out[k] = fn(idx)
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5)), float(out.std(ddof=1))
def maxdd(g, L=2.0):
    eq = np.concatenate([[1.0], np.cumprod(1.0 + L * g * 1e-4)])
    return float((1 - eq / np.maximum.accumulate(eq)).max())
def dayret(g, mask, L=2.0):
    by = {}
    for k in np.nonzero(mask)[0]: by.setdefault(DAY[k], []).append(k)
    ks = sorted(by)
    return ks, np.array([np.prod(1.0 + L * g[np.array(by[d])] * 1e-4) - 1.0 for d in ks])
def tailblock(g, mask, lab, L=2.0):
    ks, dr = dayret(g, mask, L)
    w = int(np.argmin(dr))
    return dict(window=lab, n_days=len(ks), lev=L, worst_day=ks[w], worst_day_ret=float(dr[w]),
                halt4=int((dr <= -0.04).sum()), alert268=int((dr <= -0.0268).sum()),
                halt4_per_yr=float((dr <= -0.04).sum()/(len(dr)/365.0)),
                maxDD=maxdd(g[mask], L), sd_day=float(dr.std(ddof=1)),
                p01_day=float(np.percentile(dr, 1)), p05_day=float(np.percentile(dr, 5)))
OUT = dict(series_sha256=sha(SER), env=ENV, prereg_sha256="27b0d34c5c55119ba55422a212ec340b1be1bf24af6278564796480d85cbe045",
           amendment1_sha256="720fa335e62463cbe81b764285e00020c08b81d70bcbf9d5f3ab54ae5098af9d",
           amendment2_sha256="5b8bc70485784cec3aa39363d6aef62cf7570b6703809fe65a8faa68b06ea5f8",
           device_sha256=sha(os.path.abspath(__file__)), K_total_unchanged=12,
           note="no new arm; re-reads the PRIMARY arm only")

# ---- 1. tail on both windows and on 2024+ (the regime closest to live)
W24 = WT & (YR >= 2024)
OUT['tail'] = {}
for lab, mk in [("W_TAIL n=10038", WT), ("W_ALPHA n=9138 (warm-up dropped)", WA), ("2024on", W24)]:
    OUT['tail'][lab] = dict(base=tailblock(gb, mk, lab), overlay=tailblock(go, mk, lab))
OUT['tail_by_year'] = {}
for y in sorted(set(YR[WT].tolist())):
    mk = WT & (YR == y)
    OUT['tail_by_year'][str(y)] = dict(base=tailblock(gb, mk, str(y)), overlay=tailblock(go, mk, str(y)))

# ---- 2. Sharpe / sd difference with CI (block bootstrap, PAIRED)
def shrp(g, idx): 
    x = g[idx]; return float(x.mean()/x.std(ddof=1)*np.sqrt(2190))
for lab, mk in [("W_ALPHA", WA)]:
    lo, hi, se = boot_stat(lambda i: shrp(go, i) - shrp(gb, i), mk)
    lo2, hi2, se2 = boot_stat(lambda i: float(go[i].std(ddof=1) - gb[i].std(ddof=1)), mk)
    lo3, hi3, _ = boot_stat(lambda i: float(go[i].std(ddof=1)/gb[i].std(ddof=1) - 1.0), mk)
    OUT['sharpe_delta'] = dict(window=lab,
        base=float(gb[mk].mean()/gb[mk].std(ddof=1)*np.sqrt(2190)),
        overlay=float(go[mk].mean()/go[mk].std(ddof=1)*np.sqrt(2190)),
        d_sharpe=float(shrp(go, np.nonzero(mk)[0]) - shrp(gb, np.nonzero(mk)[0])),
        d_sharpe_ci95=[lo, hi], d_sharpe_boot_se=se,
        sd_base=float(gb[mk].std(ddof=1)), sd_overlay=float(go[mk].std(ddof=1)),
        d_sd_ci95=[lo2, hi2], d_sd_rel_ci95=[lo3, hi3],
        sd_rel_change_pct=float(100*(go[mk].std(ddof=1)/gb[mk].std(ddof=1) - 1)))

# ---- 3. variance decomposition: how much of the vol drop is the beta removal?
def vardec(g, mk):
    a = Aew[mk]*1e4; y = g[mk]; ok = np.isfinite(a)
    X = np.column_stack([np.ones(ok.sum()), a[ok]]); b, *_ = np.linalg.lstsq(X, y[ok], rcond=None)
    res = y[ok] - X@b
    return dict(beta=float(b[1]), var_total=float(y[ok].var(ddof=1)),
                var_explained_by_A=float(b[1]**2 * a[ok].var(ddof=1)),
                var_resid=float(res.var(ddof=1)))
OUT['variance_decomposition'] = {}
for lab, mk in [("W_ALPHA", WA)] + [(str(y), WA & (YR == y)) for y in sorted(set(YR[WA].tolist()))]:
    OUT['variance_decomposition'][lab] = dict(base=vardec(gb, mk), overlay=vardec(go, mk))

# ---- 4. r12's CONTEMPORANEOUS six-bucket dose response, base vs overlay
BUCK = [("A <= -150bp", Aew <= -0.015), ("-150..-50bp", (Aew > -0.015) & (Aew <= -0.005)),
        ("-50..0bp", (Aew > -0.005) & (Aew <= 0)), ("0..+50bp", (Aew > 0) & (Aew < 0.005)),
        ("+50..+150bp", (Aew >= 0.005) & (Aew < 0.015)), ("A >= +150bp", Aew >= 0.015)]
OUT['contemporaneous_buckets'] = []
for nm, mk in BUCK:
    a = mk & WA; n = int(a.sum())
    if n < 30: continue
    by = days_of(a); tot = np.array([(go-gb)[b].sum() for b in by]); cnt = np.array([len(b) for b in by], float)
    ms = np.empty(NB)
    for k in range(NB):
        r = np.random.default_rng([20260905, k]).integers(0, len(by), len(by))
        ms[k] = tot[r].sum()/cnt[r].sum()
    OUT['contemporaneous_buckets'].append(dict(bucket=nm, n=n, A_mean_bps=float(np.nanmean(Aew[a])*1e4),
        g_base=float(gb[a].mean()), g_ov=float(go[a].mean()), dg=float((go-gb)[a].mean()),
        dg_ci=[float(np.percentile(ms,2.5)), float(np.percentile(ms,97.5))],
        sharpe_base=float(gb[a].mean()/gb[a].std(ddof=1)*np.sqrt(2190)),
        sharpe_ov=float(go[a].mean()/go[a].std(ddof=1)*np.sqrt(2190)),
        sharpe_se=float(np.sqrt(2190/n)), mean_theta=float(np.nanmean(th[a]))))

# ---- 5. leverage equivalence: run the overlay at the leverage that reproduces A0's maxDD
tgt = maxdd(gb[WT], 2.0)
lo_, hi_ = 0.5, 12.0
for _ in range(50):
    mid = 0.5*(lo_+hi_)
    if maxdd(go[WT], mid) < tgt: lo_ = mid
    else: hi_ = mid
Lstar = 0.5*(lo_+hi_)
def annual(g, L): return float((np.prod(1.0 + L*g[WA]*1e-4)**(2190/WA.sum()) - 1.0))
ks_b, dr_b = dayret(gb, WT, 2.0); ks_o, dr_o = dayret(go, WT, Lstar)
OUT['leverage_equivalence'] = dict(
    target_maxDD_base_at_2p0=tgt, L_star=Lstar, overlay_maxDD_at_Lstar=maxdd(go[WT], Lstar),
    ann_ret_base_2p0_W_ALPHA=annual(gb, 2.0), ann_ret_overlay_Lstar_W_ALPHA=annual(go, Lstar),
    ann_ret_overlay_2p0_W_ALPHA=annual(go, 2.0),
    halts_base_2p0=int((dr_b <= -0.04).sum()), halts_overlay_Lstar=int((dr_o <= -0.04).sum()),
    worst_day_base_2p0=float(dr_b.min()), worst_day_overlay_Lstar=float(dr_o.min()),
    note="W_TAIL for maxDD/halts, W_ALPHA for the annualised return. Not a deployment "
         "recommendation: leverage is a separate ruling and the cost model is not re-fitted at higher gross.")

# ---- 6. is the tail gain concentrated in the warm-up?
ksW, drW = dayret(gb, WT, 2.0); ksO, drO = dayret(go, WT, 2.0)
ord_ = np.argsort(drW)[:15]
OUT['worst_15_days_W_TAIL'] = [dict(day=ksW[i], base=float(drW[i]), overlay=float(drO[i]),
                                    delta=float(drO[i]-drW[i]),
                                    in_W_ALPHA=bool(WA[np.array([k for k in range(len(ts)) if DAY[k]==ksW[i]])].all()))
                               for i in ord_]
json.dump(OUT, open(os.path.join(R, "receipts", "RECEIPT_r13B_tail.json"), 'w'), indent=1, default=float)
print(json.dumps({k: OUT[k] for k in ('sharpe_delta','leverage_equivalence')}, indent=1, default=float))
print("DONE_tail")
