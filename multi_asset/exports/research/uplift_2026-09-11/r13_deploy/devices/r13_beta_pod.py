#!/usr/bin/env python3
"""r13 · IS PER-NAME BETA ESTIMABLE AT 4h ON THIS UNIVERSE?  READ-ONLY. CPU ONLY. NO GPU.

Benchmark A_ew = equal-weight mean of finite y4 over the book's member set, rebuilt exactly as
w10_sleeve.py L31-37 (MEMBERS_TOPN=829 by qvk) then narrowed by UMASK m1 (CRYPTO) — the same
construction as pod_causal_regime_r12_v2.py L50-55, whose output column A_ew this device
RE-DERIVES and ASSERTS against, so the benchmark is not a second caliber.

y4 caliber: pod 5m lineage, Sum of 5-minute SIMPLE returns. NO expm1 (E-0904-F).
Window: W_ALPHA only (book ts axis, drop first 900, ts <= 2026-08-30 20Z) => n must be 9138.
"""
import os, sys, json, time, hashlib, calendar
WHITE = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else None
BANNED = ('CAL','JUDGE','UPLIFT','PANEL','LOOK','WRULE','LEGS','PHI','FSEED','W3FIX','FTRIM',
          'UMASK','SLOW','FPRED','MEMBERS_TOPN','COSTB','SLEEVE','KMOD','SEAT','RNSM','LTRIM',
          'CDAMP','FUNDSCALE','FEMAT','TRADE_TOPN','REF_SKIP','PYTHON','OMP','MKL')
ENV_ACTUAL = {k: os.environ[k] for k in sorted(os.environ)}
EXTRA = sorted(k for k in os.environ if WHITE is not None and k not in WHITE)
assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
BAN = sorted(k for k in os.environ if k.startswith(BANNED))
assert BAN == [], ("CALIBER FLAG PRESENT", BAN)
import numpy as np

PREREG_SHA = "fcbedd4aae571dcbe8c550348981e08baf594dc2d270aaefb41c72b43c96c8a4"
_p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "PREREG_r13.md")
assert hashlib.sha256(open(_p, 'rb').read()).hexdigest() == PREREG_SHA, "PREREG HASH MISMATCH"

D = "/workspace/review_scratch/health_check/dev_v4/pod_backup_2026-08-21"
MASK = "/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz"
PIN = "/workspace/uplift_2026-09-11/r3k/arms/A0_PWR230k_s42.npz"   # sha256 352ac36f… == the repo-archived pin
R12 = "/workspace/uplift_2026-09-11/r12_regime/causal_primitives_r12_v2.npz"
OUT = "/workspace/uplift_2026-09-11/r13_deploy"
os.makedirs(OUT, exist_ok=True)
def sha16(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''): h.update(b)
    return h.hexdigest()[:16]

MT = np.load(f"{D}/wide_fea_hist_meta.npz", allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); y4 = MT["y4"]; qvk = MT["qvk"]
UZ = np.load(MASK, allow_pickle=True)
umap = {int(t): k for k, t in enumerate(UZ["ts"].astype(np.int64))}; UM = np.asarray(UZ["mask"])
TOPN = 829
T, N = y4.shape
Y = np.full((T, N), np.nan, np.float64)
A = np.full(T, np.nan)
NMEM = np.zeros(T, int)
for i in range(T):
    q = np.nan_to_num(qvk[i], nan=-1.0); o = np.argsort(-q); o = o[q[o] > -0.5]
    m = np.sort(o[:TOPN]).astype(np.int64)
    t = int(E_ts[i])
    if t in umap: m = m[UM[umap[t]][m]]
    yv32 = y4[i, m]                      # keep the float32 caliber for A_ew (r12 L53 does)
    Y[i, m] = yv32.astype(np.float64)
    ok = np.isfinite(yv32); NMEM[i] = int(m.size)
    if ok.sum() >= 30: A[i] = float(yv32[ok].mean())
# PARITY: re-derived A_ew must equal the archived r12 column
P = np.load(R12); PC = [str(c) for c in P["cols"]]; PR = P["rec"]
prow = {int(t): k for k, t in enumerate(PR[:, 0].astype(np.int64))}
Aarch = np.array([PR[prow[int(t)], PC.index("A_ew")] if int(t) in prow else np.nan for t in E_ts])
both = np.isfinite(A) & np.isfinite(Aarch)
PARITY = float(np.abs(A[both] - Aarch[both]).max()); assert PARITY == 0.0, ("A_ew PARITY", PARITY)

bts = np.load(PIN, allow_pickle=True)["rec"][:, [str(c) for c in np.load(PIN, allow_pickle=True)["cols"]].index("ts")].astype(np.int64)
UB = calendar.timegm((2026, 8, 30, 20, 0, 0))
WT = bts <= UB; WA = WT.copy(); WA[:900] = False
assert int(WT.sum()) == 10038 and int(WA.sum()) == 9138, (int(WT.sum()), int(WA.sum()))
ALPHA_TS = set(bts[WA].tolist())
mrow = {int(t): i for i, t in enumerate(E_ts)}
IDX = np.array([mrow[int(t)] for t in bts[WA] if int(t) in mrow])
assert len(IDX) == 9138, len(IDX)
lo, hi = int(IDX.min()), int(IDX.max())

M = np.isfinite(Y)
Yz = np.where(M, Y, 0.0)

def betas(rows):
    """pairwise-complete beta_i = cov(y_i, A)/var(A) over `rows`; returns beta, se, n_i."""
    r = np.array([k for k in rows if np.isfinite(A[k])], int)
    if r.size < 5: return None
    a = A[r]
    m = M[r]; yz = Yz[r]
    n = m.sum(0).astype(np.float64)
    Sa = (a[:, None] * m).sum(0); Saa = ((a * a)[:, None] * m).sum(0)
    Sy = yz.sum(0); Say = (yz * a[:, None]).sum(0); Syy = (yz * yz).sum(0)
    with np.errstate(invalid='ignore', divide='ignore'):
        ma, my = Sa / n, Sy / n
        cov = Say / n - ma * my
        var = Saa / n - ma * ma
        vy = Syy / n - my * my
        b = cov / var
        resv = np.maximum(vy - cov * cov / var, 0.0)
        se = np.sqrt(resv / np.maximum(n - 2, 1) / var)
    bad = (n < 0.8 * r.size) | ~np.isfinite(b) | (var <= 0)
    b[bad] = np.nan; se[bad] = np.nan
    return b, se, n

def spear(x, y):
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() < 20: return np.nan, int(ok.sum())
    def rk(v):
        o = np.argsort(v, kind='mergesort'); r = np.empty(len(v)); r[o] = np.arange(len(v))
        # average ties
        s = v[o]; i = 0
        while i < len(s):
            j = i
            while j + 1 < len(s) and s[j + 1] == s[i]: j += 1
            if j > i: r[o[i:j + 1]] = (i + j) / 2.0
            i = j + 1
        return r
    a, b = rk(x[ok]), rk(y[ok])
    return float(np.corrcoef(a, b)[0, 1]), int(ok.sum())

RES = {}
for W in (30, 60, 120, 250):
    pts = list(range(max(lo, lo + W), hi - W + 1, W))
    rowsout = []
    for t0 in pts:
        tr = list(range(t0 - W, t0)); nx = list(range(t0, t0 + W))
        bt = betas(tr); bn = betas(nx)
        if bt is None or bn is None: continue
        b, se, n = bt; bnext, _, _ = bn
        oddb = betas(tr[0::2]); evnb = betas(tr[1::2])
        rho_sh = np.nan
        if oddb is not None and evnb is not None:
            rho_sh, _ = spear(oddb[0], evnb[0])
        rho_sb = (2 * rho_sh / (1 + rho_sh)) if np.isfinite(rho_sh) and rho_sh > -1 else np.nan
        rho_oos, n_oos = spear(b, bnext)
        ok = np.isfinite(b) & np.isfinite(bnext)
        q_ratio = np.nan; ex_spread = re_spread = np.nan
        if ok.sum() >= 50:
            bb, nn = b[ok], bnext[ok]
            o = np.argsort(bb); k = max(1, len(o) // 5)
            ex_spread = float(bb[o[-k:]].mean() - bb[o[:k]].mean())
            re_spread = float(nn[o[-k:]].mean() - nn[o[:k]].mean())
            q_ratio = re_spread / ex_spread if ex_spread != 0 else np.nan
        tst = np.abs(b / se); tst = tst[np.isfinite(tst)]
        rowsout.append(dict(ts=int(E_ts[t0]), n_names=int(np.isfinite(b).sum()),
                            sd_cs=float(np.nanstd(b)), iqr=float(np.nanpercentile(b, 75) - np.nanpercentile(b, 25)),
                            med_abs_t=float(np.median(tst)) if tst.size else np.nan,
                            frac_t_gt2=float((tst > 2).mean()) if tst.size else np.nan,
                            med_se=float(np.nanmedian(se)),
                            rho_splithalf=rho_sh, rho_SB=rho_sb, rho_OOS=rho_oos, n_oos=n_oos,
                            ex_spread=ex_spread, re_spread=re_spread, q_ratio=q_ratio))
    # adjacent-anchor rank autocorr (overlapping windows, MECHANICAL) and lag-W (informative)
    adj = []
    for t0 in range(hi - 200, hi - 200 + 40):
        b1 = betas(range(t0 - W, t0)); b2 = betas(range(t0 - W + 1, t0 + 1))
        if b1 and b2: adj.append(spear(b1[0], b2[0])[0])
    lagW = [r for r in rowsout]
    lw = []
    for i in range(len(rowsout) - 1):
        pass
    # lag-W rank autocorr = corr of beta_hat at consecutive non-overlapping eval points
    bs = []
    for t0 in pts:
        bb = betas(range(t0 - W, t0))
        bs.append(bb[0] if bb else None)
    for i in range(len(bs) - 1):
        if bs[i] is not None and bs[i + 1] is not None:
            lw.append(spear(bs[i], bs[i + 1])[0])
    def agg(k):
        v = np.array([r[k] for r in rowsout], float); v = v[np.isfinite(v)]
        if not v.size: return None
        rng = np.random.default_rng([20260905, W])
        bo = np.array([v[rng.integers(0, v.size, v.size)].mean() for _ in range(2000)])
        return dict(n=int(v.size), mean=float(v.mean()), median=float(np.median(v)),
                    p05=float(np.percentile(v, 5)), p95=float(np.percentile(v, 95)),
                    ci95=[float(np.percentile(bo, 2.5)), float(np.percentile(bo, 97.5))])
    RES[f"W={W}"] = dict(n_eval_points=len(rowsout), eval_stride_anchors=W,
                         rho_SB=agg("rho_SB"), rho_OOS=agg("rho_OOS"), q_ratio=agg("q_ratio"),
                         ex_spread=agg("ex_spread"), re_spread=agg("re_spread"),
                         sd_cs=agg("sd_cs"), iqr=agg("iqr"), med_abs_t=agg("med_abs_t"),
                         frac_t_gt2=agg("frac_t_gt2"), med_se=agg("med_se"),
                         n_names=agg("n_names"),
                         rank_autocorr_lag1_mechanical=(float(np.nanmedian(adj)) if adj else None),
                         rank_autocorr_lagW=(float(np.nanmedian(lw)) if lw else None),
                         rows=rowsout)
    print("done W=", W, flush=True)

# ══ E3 · DOES THE EX-ANTE BOOK BETA PREDICT THE REALISED ONE? ════════════════════════════════
# beta_ante_t = sum_i w_ex,i(t) * betahat_i(t; W) on the DEPLOYED (_ex) book; realised sensitivity
# from g = net_ex/gross_total regressed on the contemporaneous A. If the interaction coefficient
# on A x (beta_ante - mean) is ~0, per-name beta has NO grip on the book's realised exposure and
# FORM B is expressible but INERT.
E3 = {}
try:
    BK = np.load("/workspace/uplift_2026-09-11/r12_regime/A0_book_for_halves_ex.npz", allow_pickle=True)
    bkts = BK["ts"].astype(np.int64); WMAT = BK["W"]; GT = BK["gross_total"]
    PINZ = np.load(PIN, allow_pickle=True); PCOL = [str(c) for c in PINZ["cols"]]; PREC = PINZ["rec"]
    pts_ = PREC[:, PCOL.index("ts")].astype(np.int64)
    gser = PREC[:, PCOL.index("net_ex")].astype(float) / PREC[:, PCOL.index("gross_total")].astype(float)
    grow = {int(t): k for k, t in enumerate(pts_)}
    bkrow = {int(t): k for k, t in enumerate(bkts)}
    for W in (60, 120, 250):
        # rolling pairwise-complete betas, updated one anchor at a time
        n = np.zeros(N); Sa = np.zeros(N); Saa = np.zeros(N); Sy = np.zeros(N); Say = np.zeros(N)
        rowsE = []
        I0 = lo - W if lo - W >= 0 else 0
        for i in range(I0, hi + 1):
            # ★ BUG FOUND AND FIXED BEFORE THE FIRST REPORTED NUMBER: the first draft removed row
            #   i-W unconditionally, so during warm-up it subtracted W rows that had never been
            #   added and every accumulator was wrong. Remove only rows this loop actually added.
            if i - W >= I0:
                k0 = i - W
                if np.isfinite(A[k0]):
                    mk = M[k0]; n -= mk; Sa -= A[k0] * mk; Saa -= A[k0] * A[k0] * mk
                    Sy -= Yz[k0]; Say -= Yz[k0] * A[k0]
            # beta from the window [i-W, i)  (strictly before i)
            t = int(E_ts[i])
            if t in ALPHA_TS and t in bkrow and t in grow:
                with np.errstate(invalid='ignore', divide='ignore'):
                    ma = Sa / n; my = Sy / n
                    cov = Say / n - ma * my; var = Saa / n - ma * ma
                    bb = cov / var
                good = (n >= 0.8 * W) & np.isfinite(bb) & (var > 0)
                bb = np.where(good, bb, np.nan)
                if np.isfinite(bb).sum() >= 100:
                    sm = WMAT[bkrow[t]].astype(np.float64)
                    nzm = np.abs(sm) > 1e-12
                    smr = sm.copy()
                    if nzm.any():
                        smr[nzm] -= smr[nzm].mean()
                        g0 = np.abs(sm).sum(); g1 = np.abs(smr).sum()
                        if g1 > 1e-9: smr *= g0 / g1
                    smr = smr / float(GT[bkrow[t]])
                    okb = np.isfinite(bb) & (np.abs(smr) > 0)
                    if okb.sum() >= 50:
                        rowsE.append((t, float((smr[okb] * bb[okb]).sum()),
                                      float(A[i]) * 1e4, float(gser[grow[t]])))
            if np.isfinite(A[i]):
                mi = M[i]; n += mi; Sa += A[i] * mi; Saa += A[i] * A[i] * mi
                Sy += Yz[i]; Say += Yz[i] * A[i]
        if len(rowsE) > 500:
            E = np.array(rowsE, float)
            ba, Ab, gg = E[:, 1], E[:, 2], E[:, 3]
            okE = np.isfinite(ba) & np.isfinite(Ab) & np.isfinite(gg)
            ba, Ab, gg = ba[okE], Ab[okE], gg[okE]
            bc = ba - ba.mean()
            X = np.column_stack([np.ones(len(gg)), Ab, Ab * bc])
            cf, *_ = np.linalg.lstsq(X, gg, rcond=None)
            res = gg - X @ cf; s2 = res @ res / (len(gg) - 3)
            se = np.sqrt(np.diag(s2 * np.linalg.pinv(X.T @ X)))
            qs = np.quantile(ba, [0, .2, .4, .6, .8, 1.0])
            qq = []
            for k in range(5):
                sel = (ba >= qs[k]) & (ba <= qs[k + 1]) if k == 4 else (ba >= qs[k]) & (ba < qs[k + 1])
                if sel.sum() > 50:
                    Xq = np.column_stack([np.ones(int(sel.sum())), Ab[sel]])
                    c2, *_ = np.linalg.lstsq(Xq, gg[sel], rcond=None)
                    qq.append(dict(q=k + 1, n=int(sel.sum()), beta_ante_mean=float(ba[sel].mean()),
                                   beta_realised=float(c2[1])))
            sl = np.nan
            if len(qq) == 5:
                xa = np.array([r["beta_ante_mean"] for r in qq]); ya = np.array([r["beta_realised"] for r in qq])
                sl = float(np.polyfit(xa, ya, 1)[0])
            E3[f"W={W}"] = dict(n=int(len(gg)), beta_ante_mean=float(ba.mean()), beta_ante_sd=float(ba.std()),
                                pooled_beta=float(cf[1]), pooled_beta_se=float(se[1]),
                                interaction_coef=float(cf[2]), interaction_se=float(se[2]),
                                interaction_t=float(cf[2] / se[2]) if se[2] > 0 else None,
                                quintiles=qq, quintile_slope=sl,
                                A_mean_bps=float(Ab.mean()), cov_A_betaante=float(np.cov(Ab, ba)[0, 1]),
                                warmup_fix="rolling accumulator removes only rows it added (I0 guard)",
                                note="interaction_coef = d(realised book beta)/d(ex-ante book beta). "
                                     "1.0 = ex-ante beta IS the realised exposure; 0.0 = no grip.")
        print("E3 done W=", W, flush=True)
except Exception as _e:
    E3 = {"error": f"{type(_e).__name__}: {str(_e)[:300]}"}

best = max((k for k in RES), key=lambda k: (RES[k]["rho_OOS"] or {}).get("median", -9))
bm = RES[best]
VERD = dict(best_window=best,
            rho_SB=(bm["rho_SB"] or {}).get("median"), rho_OOS=(bm["rho_OOS"] or {}).get("median"),
            q_ratio=(bm["q_ratio"] or {}).get("median"),
            lagW=bm["rank_autocorr_lagW"])
def _v(x, d=-9): return d if x is None else x
VERD["verdict"] = ("KILL" if (_v(VERD["rho_SB"]) < 0.30 or _v(VERD["rho_OOS"]) < 0.30
                              or _v(VERD["q_ratio"]) < 0.20)
                   else "GO" if (_v(VERD["rho_OOS"]) >= 0.30 and _v(VERD["q_ratio"]) >= 0.40
                                 and _v(VERD["rho_SB"]) >= 0.30)
                   else "USABLE_WITH_SHRINKAGE")
RCP = dict(device=os.path.basename(__file__),
           device_sha256=hashlib.sha256(open(os.path.abspath(__file__), 'rb').read()).hexdigest(),
           prereg_sha256=PREREG_SHA, prereg_asserted=True,
           window="W_ALPHA", n_W_ALPHA=int(WA.sum()), n_W_TAIL=int(WT.sum()),
           A_ew_parity_vs_r12_maxabs=PARITY,
           members_rule="MEMBERS_TOPN=829 qvk rebuild (w10_sleeve.py L31-37) then UMASK m1",
           mean_n_members=float(NMEM[IDX].mean()), min_n_members=int(NMEM[IDX].min()),
           max_n_members=int(NMEM[IDX].max()),
           y4_caliber="pod 5m lineage: SUM of 5-minute SIMPLE returns; NO expm1 (E-0904-F)",
           inputs={p: dict(realpath=os.path.realpath(p), sha16=sha16(p))
                   for p in [f"{D}/wide_fea_hist_meta.npz", MASK, PIN, R12]},
           env_whitelist=sorted(WHITE) if WHITE else None, env_extra=EXTRA, env_banned=BAN,
           env_banned_prefixes=sorted(BANNED), env_actual=ENV_ACTUAL,
           python=sys.version.split()[0], numpy=np.__version__,
           E3_portfolio_level=E3,
           results={k: {kk: vv for kk, vv in v.items() if kk != "rows"} for k, v in RES.items()},
           VERDICT=VERD,
           built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
json.dump(RCP, open(f"{OUT}/RECEIPT_r13_beta.json", "w"), indent=1, default=float)
json.dump({k: v["rows"] for k, v in RES.items()}, open(f"{OUT}/r13_beta_rows.json", "w"), indent=0, default=float)
print(json.dumps({k: v for k, v in RCP.items() if k not in ("env_actual", "inputs")}, indent=1, default=float))
