#!/usr/bin/env python3
"""t2_kappa.py — PREREG_T2 §2 estimator of kappa* (uncompensated fraction of carry), walk-forward MONTHLY refit on an
EXPANDING window, anchor fixed effects, pooled OLS  y_w = a_i + lam*FZ + b*c + e ; kappa*_raw = 1 - b ; kappa* = clip(0,1) ;
lam+ = max(lam, 0). Writes the per-anchor path read by w10_sleeve_t2.py, the C1 future-invariance gate, and the
pre-registered diagnostics d1 (unwinsorised), d2 (per-side slopes), d3 (yearly refit), d4 (live window on the r6 extension).
CPU only; reads data read-only; writes only under /workspace/uplift_r2_2026-09-13/T2/.
Launch:  env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root /workspace/venv/bin/python t2_kappa.py PATH,HOME,LC_CTYPE main|garbled
"""
import os, sys, json, time, hashlib, calendar
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "launch with a non-empty env whitelist as argv[1]"
MODE = sys.argv[2] if len(sys.argv) > 2 else None; assert MODE in ("main", "garbled"), MODE
BANNED = ('CAL', 'JUDGE', 'UPLIFT', 'PANEL', 'LOOK', 'WRULE', 'LEGS', 'PHI', 'FSEED', 'W3FIX', 'FTRIM', 'UMASK', 'SLOW', 'FPRED', 'MEMBERS_TOPN', 'COSTB', 'SLEEVE', 'KMOD', 'SEAT', 'RNSM', 'LTRIM', 'CDAMP', 'FUNDSCALE', 'FEMAT', 'TRADE_TOPN', 'REF_SKIP', 'PYTHON', 'OMP', 'MKL', 'R15', 'R18', 'SMA', 'SBAND', 'FTPOS', 'OUT_TAG', 'T2')
EXTRA = sorted(k for k in os.environ if k not in WHITE); assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
BAN = sorted(k for k in os.environ if k.startswith(BANNED)); assert BAN == [], ("CALIBER FLAG PRESENT", BAN)
ENV = dict(env_whitelist=sorted(WHITE), env_actual={k: os.environ[k] for k in sorted(os.environ)}, launch_cmdline=" ".join(sys.argv))
import numpy as np
from scipy.stats import rankdata
import scipy
ENV.update(python=sys.version.split()[0], numpy=np.__version__, scipy=scipy.__version__)
T0 = time.time()
T2 = "/workspace/uplift_r2_2026-09-13/T2"
PREREG = T2 + "/PREREG_T2_carry_net_sizing_2026-09-13.md"; PREREG_SHA = "981293b02b2ddae6574fa6dcf8db9b09a65cfa9f122a8b72d7e604ad5ec87eca"
def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def sh(cmd):
    import subprocess
    try: return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.STDOUT).strip()
    except Exception as e: return "ERR %s" % e
assert sha(PREREG) == PREREG_SHA, ("PREREG SHA", sha(PREREG))
GPU0 = sh("nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader"); PID0 = sh("ps -o pid,stat -p 333197,339489 | tail -n +2"); LOAD0 = open("/proc/loadavg").read().split()[:3]
UMASK = "/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz"; UMASK_SHA = "47d87b5165b695a7d9b340134a189dd6a2165c837bab35808b699ffac3f7f1b5"
if MODE == "main":
    META = "/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz"; META_SHA = "0e3c09ac86c727ac1a7893889918e3b367463fd059a154f5e320eed47f5725c3"
    PANEL = "/workspace/data/wide_panel_4h_v2ext.npz"; PANEL_SHA = "5e67c0559daa904d8f0526b6e268e93dcb45aab89d82646cf79a794445481116"
    assert sha(META) == META_SHA and sha(PANEL) == PANEL_SHA, "main input sha"
else:
    META = T2 + "/dev_garbled/pod_backup_2026-08-21/wide_fea_hist_meta.npz"; PANEL = T2 + "/dev_garbled/pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz"
    META_SHA = sha(META); PANEL_SHA = sha(PANEL)
assert sha(UMASK) == UMASK_SHA
X_META = "/workspace/uplift_2026-09-11/r6/out/meta_newprod_v4_x0910.npz"; X_META_SHA = "a8eb359701c71acfe853a295eb055bdbb04e1c29b6534ccdf23aeaff69907245"
X_PANEL = "/workspace/uplift_2026-09-11/r6/out/wide_panel_4h_v2ext_x0910.npz"; X_PANEL_SHA = "042478f7d8e9f9476341a2acb310828fcf1f5d4a855c2ad0105a08e78f604549"
OUTD = T2 + "/kpath"; RCD = T2 + "/receipts"; os.makedirs(OUTD, exist_ok=True); os.makedirs(RCD, exist_ok=True)
UB = calendar.timegm((2026, 8, 30, 20, 0, 0)); EMB = 8 * 3600; MIN_ANCH = 540; MIN_BIN = 180; WINS = 0.20; NMIN = 80
LIVE_LO = calendar.timegm((2026, 8, 26, 0, 0, 0)); LIVE_HI = calendar.timegm((2026, 9, 10, 0, 0, 0))

def xz(v):   # device xz verbatim
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    if ok.sum() >= 10: out[ok] = rankdata(v[ok]) / max(ok.sum() - 1, 1) - 0.5
    return out

def load_tree(meta_p, panel_p, carry_forward_umask=False):
    MT = np.load(meta_p, allow_pickle=True); E = MT["E_ts"].astype(np.int64); Y = MT["y4"]; Q = MT["qvk"]
    nA = len(E); mem = np.empty(nA, dtype=object)
    for i in range(nA):   # MEMBERS_TOPN=829 rebuild, device L70-76 verbatim
        q = np.nan_to_num(Q[i], nan=-1.0); o = np.argsort(-q); o = o[q[o] > -0.5]; mem[i] = np.sort(o[:829]).astype(np.int64)
    PW = np.load(panel_p, allow_pickle=True); pts = PW["ts"].astype(np.int64); prow = {int(t): j for j, t in enumerate(pts)}
    FN = PW["f_fund_now"]; IV = PW["f_fund_iv"]; FE = PW["f_fund_ema_v1"]; syms = [str(s) for s in PW["symbols"]]
    UZ = np.load(UMASK, allow_pickle=True); assert [str(s) for s in UZ["symbols"]] == syms, "umask symbols"
    umap = {int(t): k for k, t in enumerate(UZ["ts"].astype(np.int64))}; UM = np.asarray(UZ["mask"]); ulast = int(UZ["ts"].astype(np.int64).max())
    urow = {}; ucf = 0
    for j, t in enumerate(pts):
        k = umap.get(int(t))
        if k is not None: urow[j] = UM[k]
        elif carry_forward_umask and int(t) > ulast: urow[j] = UM[umap[ulast]]; ucf += 1
    return dict(E=E, Y=Y, Q=Q, mem=mem, pts=pts, prow=prow, FN=FN, IV=IV, FE=FE, urow=urow, syms=syms, umask_carry_forward_rows=ucf, MT=MT, PW=PW)

def sigma_rows(FN, IV):   # device FUNDSCALE dispersion definition (829 base, 8h-equivalent, bps)
    IVf = np.where(np.isfinite(IV) & (IV > 0), IV, 8.0); RN8 = np.nan_to_num(FN, nan=0.0) * (8.0 / IVf)
    out = np.full(FN.shape[0], np.nan)
    for j in range(FN.shape[0]):
        f = np.isfinite(FN[j])
        if f.sum() > 50: out[j] = float(np.std(RN8[j][f])) * 1e4
    return out

def aggregates(tr, Y=None, FN=None, FE=None, IV=None, anchors=None):
    Y = tr["Y"] if Y is None else Y; FN = tr["FN"] if FN is None else FN; FE = tr["FE"] if FE is None else FE; IV = tr["IV"] if IV is None else IV
    IVf = np.where(np.isfinite(IV) & (IV > 0), IV, 8.0)
    E = tr["E"]; nA = len(E); idx = range(nA) if anchors is None else anchors
    A = dict(valid=np.zeros(nA, bool), n=np.zeros(nA, np.int64), Sxx=np.zeros((nA, 2, 2)), Sxy=np.zeros((nA, 2)), Sxy_raw=np.zeros((nA, 2)), S3xx=np.zeros((nA, 3, 3)), S3xy=np.zeros((nA, 3)), j=np.full(nA, -1, np.int64))
    for i in idx:
        j = tr["prow"].get(int(E[i]))
        if j is None: continue
        A["j"][i] = j
        m = tr["mem"][i]; mk = tr["urow"].get(j)
        if mk is not None: m = m[mk[m]]
        fz = xz(FE[j, :])[m]
        qv = np.expm1(np.clip(tr["Q"][i, m], 0, 30)) * 48
        fn = FN[j, m]; y = Y[i, m]
        ok = np.isfinite(y) & (qv >= 2.5e5) & np.isfinite(fz) & np.isfinite(fn)
        n = int(ok.sum())
        if n < NMIN: continue
        c = (np.nan_to_num(fn, nan=0.0) * (4.0 / IVf[j, m]))[ok].astype(np.float64)   # device carry expression (float32), per unit long, per 4h
        z = fz[ok]; yr = y[ok].astype(np.float64); yw = np.clip(yr, -WINS, WINS)
        z = z - z.mean(); cd = c - c.mean(); ywd = yw - yw.mean(); yrd = yr - yr.mean()
        cp = np.maximum(c, 0.0); cm = np.minimum(c, 0.0); cpd = cp - cp.mean(); cmd = cm - cm.mean()
        A["valid"][i] = True; A["n"][i] = n
        A["Sxx"][i], A["Sxy"][i] = mom([z, cd], ywd); A["Sxy_raw"][i] = mom([z, cd], yrd)[1]; A["S3xx"][i], A["S3xy"][i] = mom([z, cpd, cmd], ywd)
    return A

def mom(cols, y):   # moments by explicit numpy sums (no BLAS: bitwise-reproducible across processes and allocations)
    k = len(cols); Sxx = np.empty((k, k)); Sxy = np.empty(k)
    for a in range(k):
        Sxy[a] = np.sum(cols[a] * y)
        for b in range(a, k):
            Sxx[a, b] = Sxx[b, a] = np.sum(cols[a] * cols[b])
    return Sxx, Sxy

def inv_small(M):   # closed-form inverse of a 2x2 / 3x3 (no LAPACK)
    if M.shape[0] == 2:
        a, b, c, d = M[0, 0], M[0, 1], M[1, 0], M[1, 1]; det = a * d - b * c
        return np.array([[d, -b], [-c, a]]) / det
    a, b, c = M[0]; d, e, f = M[1]; g, h, i = M[2]
    A_ = e * i - f * h; B_ = -(d * i - f * g); C_ = d * h - e * g; D_ = -(b * i - c * h); E_ = a * i - c * g; F_ = -(a * h - b * g); G_ = b * f - c * e; H_ = -(a * f - c * d); I_ = a * e - b * d
    det = a * A_ + b * B_ + c * C_
    return np.array([[A_, D_, G_], [B_, E_, H_], [C_, F_, I_]]) / det

def cluster_fit(Sxx, Sxy, clus):
    """pooled OLS from per-anchor moment matrices; sandwich SE clustered on `clus` (G/(G-1) correction); explicit arithmetic only."""
    k = Sxy.shape[1]; Ax = np.zeros((k, k)); s = np.zeros(k)
    for r in range(Sxx.shape[0]): Ax += Sxx[r]; s += Sxy[r]   # sequential, fixed order
    with np.errstate(all="ignore"): Ai = inv_small(Ax)
    if not np.all(np.isfinite(Ai)): return None
    th = np.zeros(k)
    for b in range(k): th += Ai[:, b] * s[b]
    u, inv = np.unique(clus, return_inverse=True); G = len(u)
    Gxx = np.zeros((G, k, k)); Gxy = np.zeros((G, k))
    for r in range(Sxx.shape[0]): Gxx[inv[r]] += Sxx[r]; Gxy[inv[r]] += Sxy[r]
    gd = Gxy.copy()
    for b in range(k): gd -= Gxx[:, :, b] * th[b]
    meat = np.empty((k, k))
    for a in range(k):
        for b in range(k): meat[a, b] = np.sum(gd[:, a] * gd[:, b])
    V = np.zeros((k, k))
    for a in range(k):
        for d in range(k):
            for b in range(k):
                for c in range(k): V[a, d] += Ai[a, b] * meat[b, c] * Ai[c, d]
    V *= G / max(G - 1, 1)
    return th, np.sqrt(np.maximum(np.diag(V), 0.0)), G

def estimate(A, E, sel_idx, day, week):
    """the §2.2 estimate on anchors sel_idx (ascending)."""
    o = dict(n_anchors=int(len(sel_idx)), n_obs=int(A["n"][sel_idx].sum()))
    if len(sel_idx) < 3: o.update(ok=False); return o
    fd = cluster_fit(A["Sxx"][sel_idx], A["Sxy"][sel_idx], day[sel_idx]); fw = cluster_fit(A["Sxx"][sel_idx], A["Sxy"][sel_idx], week[sel_idx])
    if fd is None: o.update(ok=False); return o
    th, se_d, Gd = fd; se_w = fw[1]
    lam, b = float(th[0]), float(th[1]); kraw = 1.0 - b
    o.update(ok=True, lam=lam, b=b, kappa_raw=kraw, kappa=float(min(max(kraw, 0.0), 1.0)), lam_plus=float(max(lam, 0.0)),
             se_day_lam=float(se_d[0]), se_day_b=float(se_d[1]), se_week_b=float(se_w[1]), n_days=int(Gd),
             kappa_raw_ci95_day=[kraw - 1.96 * float(se_d[1]), kraw + 1.96 * float(se_d[1])],
             guard_kappa_clip_lo=bool(kraw < 0.0), guard_kappa_clip_hi=bool(kraw > 1.0), guard_lam_floor=bool(lam < 0.0))
    return o

def refit_schedule(E, prow):
    rec_ts = np.array([t for t in E if int(t) in prow], np.int64)
    y0, m0 = time.gmtime(int(rec_ts[0]))[:2]; y1, m1 = time.gmtime(int(rec_ts[-1]))[:2]
    Ts = []; y, mth = y0, m0
    while (y, mth) <= ((y1 + (m1 == 12)), (m1 % 12) + 1):
        Ts.append(calendar.timegm((y, mth, 1, 0, 0, 0))); mth += 1
        if mth == 13: y, mth = y + 1, 1
    return np.array([t for t in Ts if t > rec_ts[0]], np.int64)

def fit_all(tr, A, sig_row, refits):
    E = tr["E"]; day = (E // 86400).astype(np.int64); week = ((E // 86400 + 3) // 7).astype(np.int64)
    sig_anchor = np.array([sig_row[A["j"][i]] if A["j"][i] >= 0 else np.nan for i in range(len(E))])
    valid_idx = np.nonzero(A["valid"])[0]
    R = []
    for T in refits:
        w = valid_idx[E[valid_idx] <= T - EMB]
        sc = estimate(A, E, w, day, week); sc["T"] = int(T); sc["T_iso"] = time.strftime("%Y-%m-%d", time.gmtime(int(T)))
        sc["active"] = bool(sc.get("ok") and sc["n_anchors"] >= MIN_ANCH and not (sc["lam_plus"] == 0.0 and sc["kappa"] == 0.0))
        # d1 unwinsorised
        if len(w) >= 3:
            f1 = cluster_fit(A["Sxx"][w], A["Sxy_raw"][w], day[w]); sc["d1_raw"] = dict(lam=float(f1[0][0]), b=float(f1[0][1]), kappa_raw=1.0 - float(f1[0][1]), se_day_b=float(f1[1][1])) if f1 else None
            f2 = cluster_fit(A["S3xx"][w], A["S3xy"][w], day[w])
            sc["d2_side"] = dict(lam=float(f2[0][0]), b_plus=float(f2[0][1]), b_minus=float(f2[0][2]), kappa_plus_raw=1.0 - float(f2[0][1]), kappa_minus_raw=1.0 - float(f2[0][2]), se_day_b_plus=float(f2[1][1]), se_day_b_minus=float(f2[1][2])) if f2 else None
        # sigma terciles on the estimation window (causal)
        wf = w[np.isfinite(sig_anchor[w])]
        sg = dict(ok=False)
        if len(wf) >= 3 * MIN_BIN:
            q1, q2 = np.quantile(sig_anchor[wf], [1.0 / 3.0, 2.0 / 3.0]); sg = dict(ok=True, q1=float(q1), q2=float(q2), bins=[])
            bn = np.where(sig_anchor[wf] <= q1, 0, np.where(sig_anchor[wf] <= q2, 1, 2))
            for b_ in range(3):
                e_ = estimate(A, E, wf[bn == b_], day, week); e_["active_bin"] = bool(e_.get("ok") and e_["n_anchors"] >= MIN_BIN and not (e_["lam_plus"] == 0.0 and e_["kappa"] == 0.0)); sg["bins"].append(e_)
            sg["all_bins_ge_min"] = bool(all(e_["n_anchors"] >= MIN_BIN and e_.get("ok") for e_ in sg["bins"]))
        sc["sigma"] = sg
        R.append(sc)
    return R, sig_anchor

def path_from(E, R, sig_anchor, refits, shift=0):
    """per-anchor path; shift=-1 look-ahead (month M uses refit of M+1), +1 stale (uses M-1)."""
    nA = len(E); r = np.searchsorted(refits, E, side="right") - 1
    if shift == -1: r = np.where(r >= 0, r + 1, -1)
    if shift == +1: r = r - 1
    P = {k: np.full(nA, np.nan) for k in ("kappa_scalar", "lam_scalar", "kappa_raw_scalar", "kappa_sigma", "lam_sigma", "kappa_raw_sigma", "refit_ts", "bin_sigma", "q1", "q2")}
    P["active_scalar"] = np.zeros(nA, bool); P["active_sigma"] = np.zeros(nA, bool)
    for i in range(nA):
        k = int(r[i])
        if k < 0 or k >= len(R): continue
        e = R[k]; P["refit_ts"][i] = e["T"]
        if e["active"]:
            P["active_scalar"][i] = True; P["kappa_scalar"][i] = e["kappa"]; P["lam_scalar"][i] = e["lam_plus"]; P["kappa_raw_scalar"][i] = e["kappa_raw"]
        sg = e["sigma"]
        if sg.get("ok") and sg.get("all_bins_ge_min") and np.isfinite(sig_anchor[i]):
            b_ = 0 if sig_anchor[i] <= sg["q1"] else (1 if sig_anchor[i] <= sg["q2"] else 2); eb = sg["bins"][b_]
            P["bin_sigma"][i] = b_; P["q1"][i] = sg["q1"]; P["q2"][i] = sg["q2"]
            if eb["active_bin"]:
                P["active_sigma"][i] = True; P["kappa_sigma"][i] = eb["kappa"]; P["lam_sigma"][i] = eb["lam_plus"]; P["kappa_raw_sigma"][i] = eb["kappa_raw"]
    return P

# ------------------------------------------------------------------ main estimate
tr = load_tree(META, PANEL)
E = tr["E"]; nA = len(E)
t1 = time.time(); A = aggregates(tr); T_AGG = round(time.time() - t1, 1)
sig_row = sigma_rows(tr["FN"], tr["IV"])
refits = refit_schedule(E, tr["prow"])
R, sig_anchor = fit_all(tr, A, sig_row, refits)
P0 = path_from(E, R, sig_anchor, refits, 0)
def savepath(P, name):
    p = OUTD + "/KPATH_T2_%s.npz" % name
    np.savez(p, E_ts=E, **P, meta_json=np.array(json.dumps(dict(prereg_sha256=PREREG_SHA, mode=MODE, name=name, meta=META, meta_sha256=META_SHA, panel=PANEL, panel_sha256=PANEL_SHA, umask_sha256=UMASK_SHA))))
    return p, sha(p)
OUTS = {}
OUTS["main" if MODE == "main" else "garbled"] = savepath(P0, "main" if MODE == "main" else "garbled")

# rec axis and windows (rec row r <-> r-th anchor with a panel row; the device books all 10039)
rec_idx = np.array([i for i in range(nA) if int(E[i]) in tr["prow"]], np.int64)
WA = np.zeros(nA, bool); WA[rec_idx[900:]] = True; WA &= E <= UB
def path_summary(P, mask):
    act = P["active_scalar"] & mask; acts = P["active_sigma"] & mask
    kr = P["kappa_raw_scalar"][act]; ref_ts = np.unique(P["refit_ts"][act])
    half = np.nonzero(mask)[0]; mid = half[len(half) // 2] if len(half) else 0
    o = dict(n_mask=int(mask.sum()), scalar_active=int(act.sum()), sigma_active=int(acts.sum()),
             scalar_kappa_mean=float(np.mean(P["kappa_scalar"][act])) if act.any() else None, scalar_lam_mean=float(np.mean(P["lam_scalar"][act])) if act.any() else None,
             scalar_kappa_min=float(np.min(P["kappa_scalar"][act])) if act.any() else None, scalar_kappa_max=float(np.max(P["kappa_scalar"][act])) if act.any() else None,
             scalar_kappa_mean_first_half=float(np.mean(P["kappa_scalar"][act & (np.arange(nA) < mid)])) if (act & (np.arange(nA) < mid)).any() else None,
             scalar_kappa_mean_second_half=float(np.mean(P["kappa_scalar"][act & (np.arange(nA) >= mid)])) if (act & (np.arange(nA) >= mid)).any() else None,
             anchors_clip_lo=int((kr < 0).sum()), anchors_clip_hi=int((kr > 1).sum()), anchors_lam_floor=int((P["lam_scalar"][act] == 0).sum()), n_refits_used=int(len(ref_ts)),
             sigma_kappa_mean_by_bin={int(b): float(np.mean(P["kappa_sigma"][acts & (P["bin_sigma"] == b)])) for b in (0, 1, 2) if (acts & (P["bin_sigma"] == b)).any()},
             sigma_anchors_by_bin={int(b): int((acts & (P["bin_sigma"] == b)).sum()) for b in (0, 1, 2)})
    return o

RC = dict(self_sha256=sha(os.path.abspath(__file__)), prereg_sha256=PREREG_SHA, mode=MODE, env=ENV, inputs=dict(meta=dict(path=META, realpath=os.path.realpath(META), sha256=META_SHA), panel=dict(path=PANEL, realpath=os.path.realpath(PANEL), sha256=PANEL_SHA), umask=dict(path=UMASK, sha256=UMASK_SHA)),
          constants=dict(embargo_s=EMB, min_anchors=MIN_ANCH, min_bin=MIN_BIN, winsor=WINS, nmin_names=NMIN, UB="2026-08-30 20Z"),
          axis=dict(n_meta=int(nA), n_rec=int(len(rec_idx)), n_valid_xsec=int(A["valid"].sum()), n_W_ALPHA=int(WA.sum()), aggregates_s=T_AGG),
          refits=R, path_outputs={k: dict(path=v[0], sha256=v[1]) for k, v in OUTS.items()}, W_ALPHA_summary=path_summary(P0, WA))
assert RC["axis"]["n_rec"] == 10039 and RC["axis"]["n_W_ALPHA"] == 9138, RC["axis"]

if MODE == "main":
    # §7 shifted paths (only read if the ceiling tripwire fires)
    RC["path_outputs"]["lookahead1"] = dict(zip(("path", "sha256"), savepath(path_from(E, R, sig_anchor, refits, -1), "lookahead1")))
    RC["path_outputs"]["stale1"] = dict(zip(("path", "sha256"), savepath(path_from(E, R, sig_anchor, refits, +1), "stale1")))
    # d3 yearly refit (diagnostic)
    day = (E // 86400).astype(np.int64); week = ((E // 86400 + 3) // 7).astype(np.int64); valid_idx = np.nonzero(A["valid"])[0]
    yearly = []
    for y in (2023, 2024, 2025, 2026):
        T = calendar.timegm((y, 1, 1, 0, 0, 0)); w = valid_idx[E[valid_idx] <= T - EMB]; e = estimate(A, E, w, day, week); e["T_iso"] = "%d-01-01" % y; yearly.append(e)
    RC["d3_yearly"] = yearly
    yk = np.full(nA, np.nan)
    for e in yearly:
        if e.get("ok") and e["n_anchors"] >= MIN_ANCH: yk[E >= calendar.timegm(time.strptime(e["T_iso"], "%Y-%m-%d"))] = e["kappa"]
    RC["d3_yearly_W_ALPHA"] = dict(kappa_mean=float(np.nanmean(yk[WA])), anchors_without_yearly_estimate=int(np.isnan(yk[WA]).sum()))
    # M1 at the final refit used in W_ALPHA
    last_used = int(np.nanmax(P0["refit_ts"][WA])); fin = next(e for e in R if e["T"] == last_used)
    ci = fin["kappa_raw_ci95_day"]; RC["M1_final_refit"] = dict(T_iso=fin["T_iso"], kappa_raw=fin["kappa_raw"], kappa=fin["kappa"], ci95_day=ci, se_day_b=fin["se_day_b"], se_week_b=fin["se_week_b"], lam=fin["lam"], se_day_lam=fin["se_day_lam"],
                                    ci_inside_0_1=bool(ci[0] > 0.0 and ci[1] < 1.0), ci_excludes_0=bool(ci[0] > 0.0), ci_excludes_1=bool(ci[1] < 1.0), d2_side=fin.get("d2_side"), d1_raw=fin.get("d1_raw"))
    # ------------------------------------------------------------------ C1 future-invariance gate
    act_idx = [k for k, e in enumerate(R) if e["active"]]
    pick = sorted(set(int(round(x)) for x in np.linspace(0, len(act_idx) - 1, 12))); pick = [act_idx[k] for k in pick]
    C1 = []
    for k in pick:
        T = int(refits[k]); rng = np.random.default_rng([20260913, T])
        Yg = tr["Y"].copy(); fut = E > T - EMB; Yg[fut] = rng.normal(0.0, 0.05, size=(int(fut.sum()), Yg.shape[1])).astype(Yg.dtype)
        pf = tr["pts"] > T - EMB
        FNg = tr["FN"].copy(); FEg = tr["FE"].copy(); IVg = tr["IV"].copy()
        FNg[pf] = rng.normal(0.0, 1e-3, size=(int(pf.sum()), FNg.shape[1])).astype(FNg.dtype); FEg[pf] = rng.normal(0.0, 1e-3, size=(int(pf.sum()), FEg.shape[1])).astype(FEg.dtype); IVg[pf] = rng.choice(np.array([1.0, 4.0, 8.0], np.float32), size=(int(pf.sum()), IVg.shape[1]))
        Ag = aggregates(tr, Y=Yg, FN=FNg, FE=FEg, IV=IVg); sg_row = sigma_rows(FNg, IVg)
        Rg, _ = fit_all(tr, Ag, sg_row, refits[k:k + 1])
        a, g_ = R[k], Rg[0]
        keys = ("lam", "b", "kappa_raw", "kappa", "lam_plus", "se_day_b", "se_week_b", "n_anchors", "n_obs", "active")
        same_scalar = all((a.get(q) == g_.get(q)) for q in keys)
        same_sigma = (a["sigma"].get("ok") == g_["sigma"].get("ok")) and (not a["sigma"].get("ok") or (a["sigma"]["q1"] == g_["sigma"]["q1"] and a["sigma"]["q2"] == g_["sigma"]["q2"] and all(all(ba.get(q) == bg.get(q) for q in keys[:-1]) for ba, bg in zip(a["sigma"]["bins"], g_["sigma"]["bins"]))))
        same_diag = (a.get("d1_raw") == g_.get("d1_raw")) and (a.get("d2_side") == g_.get("d2_side"))
        garbled_rows_y4 = int(fut.sum()); garbled_rows_panel = int(pf.sum())
        C1.append(dict(T_iso=a["T_iso"], garbled_y4_rows=garbled_rows_y4, garbled_panel_rows=garbled_rows_panel, bitwise_scalar=bool(same_scalar), bitwise_sigma=bool(same_sigma), bitwise_diagnostics=bool(same_diag),
                       lam=a["lam"], lam_garbled=g_["lam"], b=a["b"], b_garbled=g_["b"]))
        print("C1", a["T_iso"], same_scalar, same_sigma, same_diag, flush=True)
    RC["C1"] = dict(checks=C1, PASS=bool(all(c["bitwise_scalar"] and c["bitwise_sigma"] and c["bitwise_diagnostics"] for c in C1) and len(C1) == 12))
    # ------------------------------------------------------------------ d4 live window on the r6 extension tree
    assert sha(X_META) == X_META_SHA and sha(X_PANEL) == X_PANEL_SHA, "x0910 sha"
    tx = load_tree(X_META, X_PANEL, carry_forward_umask=True)
    n0, p0 = nA, len(tr["pts"])
    pref = dict(E_ts=bool(np.array_equal(tx["E"][:n0], E)), y4=bool(np.array_equal(tx["Y"][:n0], tr["Y"], equal_nan=True)), qvk=bool(np.array_equal(tx["Q"][:n0], tr["Q"], equal_nan=True)),
                panel_ts=bool(np.array_equal(tx["pts"][:p0], tr["pts"])), f_fund_now=bool(np.array_equal(tx["FN"][:p0], tr["FN"], equal_nan=True)), f_fund_iv=bool(np.array_equal(tx["IV"][:p0], tr["IV"], equal_nan=True)),
                f_fund_ema_v1=bool(np.array_equal(tx["FE"][:p0], tr["FE"], equal_nan=True)), symbols=bool(tx["syms"] == tr["syms"]))
    live = [i for i in range(len(tx["E"])) if LIVE_LO <= int(tx["E"][i]) <= LIVE_HI and int(tx["E"][i]) in tx["prow"]]
    Ax = aggregates(tx, anchors=live); li = np.array([i for i in live if Ax["valid"][i]], np.int64)
    dayx = (tx["E"] // 86400).astype(np.int64); weekx = ((tx["E"] // 86400 + 3) // 7).astype(np.int64)
    el = estimate(Ax, tx["E"], li, dayx, weekx)
    f2 = cluster_fit(Ax["S3xx"][li], Ax["S3xy"][li], dayx[li]) if len(li) >= 3 else None
    el["d2_side"] = dict(b_plus=float(f2[0][1]), b_minus=float(f2[0][2]), kappa_plus_raw=1.0 - float(f2[0][1]), kappa_minus_raw=1.0 - float(f2[0][2]), se_day_b_plus=float(f2[1][1]), se_day_b_minus=float(f2[1][2])) if f2 else None
    RC["d4_live_window"] = dict(window="2026-08-26 00Z .. 2026-09-10 00Z", tree=dict(meta=X_META, meta_sha256=X_META_SHA, panel=X_PANEL, panel_sha256=X_PANEL_SHA), prefix_bitwise=pref, prefix_all_equal=bool(all(pref.values())),
                                umask_carry_forward_panel_rows=int(tx["umask_carry_forward_rows"]), n_anchors_in_window=len(live), n_anchors_valid=int(len(li)),
                                first=time.strftime("%Y-%m-%d %HZ", time.gmtime(int(tx["E"][li[0]]))) if len(li) else None, last=time.strftime("%Y-%m-%d %HZ", time.gmtime(int(tx["E"][li[-1]]))) if len(li) else None,
                                estimate=el, caveat="16 day-clusters: the clustered SE is unreliable; September umask rows are the 2026-08-31 00Z row carried forward; descriptive only")
GPU1 = sh("nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader"); PID1 = sh("ps -o pid,stat -p 333197,339489 | tail -n +2")
RC.update(gpu_before=GPU0, gpu_after=GPU1, protected_pids_before=PID0, protected_pids_after=PID1, loadavg_before=LOAD0, wall_s=round(time.time() - T0, 1), built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
json.dump(RC, open(RCD + "/RECEIPT_T2_kappa_%s.json" % MODE, "w"), indent=1, default=float)
S = RC["W_ALPHA_summary"]
print("KAPPA_%s W_ALPHA scalar active %d kappa mean %s [min %s max %s] half1 %s half2 %s | sigma active %d by bin %s" % (MODE, S["scalar_active"], S["scalar_kappa_mean"], S["scalar_kappa_min"], S["scalar_kappa_max"], S["scalar_kappa_mean_first_half"], S["scalar_kappa_mean_second_half"], S["sigma_active"], S["sigma_kappa_mean_by_bin"]), flush=True)
if MODE == "main": print("M1", json.dumps(RC["M1_final_refit"]), "| C1 PASS", RC["C1"]["PASS"], "| d4", json.dumps({k: RC["d4_live_window"]["estimate"].get(k) for k in ("n_anchors", "kappa_raw", "se_day_b", "lam")}), "prefix", RC["d4_live_window"]["prefix_all_equal"], flush=True)
print("DONE_t2_kappa", MODE, RC["wall_s"], "s", flush=True)
