#!/usr/bin/env python3
"""t2_live_addendum.py — PROGRAM AMENDMENT 2 (commit 83579437) reporting addendum for T2: did the estimated κ*(t) react to the
live-window regime (carry drag ≈ 2.86× the full-cycle mean with a zero price edge)? Reporting only: the frozen T2 rule and
verdicts are untouched; nothing here was pre-registered (labelled POST-HOC DESCRIPTIVE in the RESULT).
Computes, on the r6 extension tree (x0910; prefix bitwise equal to the incumbent, September umask = 2026-08-31 00Z row carried forward):
  R0  reproduction gate: the §2 estimator (functions copied verbatim from devices/t2_kappa.py) re-run on the extension tree must
      reproduce the registered 2026-07-01 and 2026-08-01 refits BITWISE (scalar, σ cut points, σ bins); else STOP.
  R1  κ used by each arm on the replayed live anchors (from the registered path file).
  R2  refits that contain live-window data: 2026-09-01 (registered axis and extension axis) and 2026-09-11 00Z (extension axis, all
      live anchors), plus the same 09-11 fit with the live anchors left out, and the live anchors' share of the carry-variance moment.
  R3  the live window's own estimate against every earlier non-overlapping block of the same length (91 valid anchors).
  R4  σ_fund level of the live window against those blocks, and its bins under the 2026-08-01 cut points.
  R5  carry levels: A0 executed-book carry_ex/gt on the 30 replayed live anchors vs its W_ALPHA mean, and the fund leg's unit-gross
      rank-book carry (the SEATNET quantity) on the live window vs its W_ALPHA mean (reproduced bitwise against the ARM-SK artifact first).
CPU only; read-only inputs; writes receipts/RECEIPT_T2_live_addendum.json.
Launch: env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root /workspace/venv/bin/python devices/t2_live_addendum.py PATH,HOME,LC_CTYPE
"""
import os, sys, json, time, hashlib, calendar
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "launch with a non-empty env whitelist as argv[1]"
BANNED = ('CAL', 'JUDGE', 'UPLIFT', 'PANEL', 'LOOK', 'WRULE', 'LEGS', 'PHI', 'FSEED', 'W3FIX', 'FTRIM', 'UMASK', 'SLOW', 'FPRED', 'MEMBERS_TOPN', 'COSTB', 'SLEEVE', 'KMOD', 'SEAT', 'RNSM', 'LTRIM', 'CDAMP', 'FUNDSCALE', 'FEMAT', 'TRADE_TOPN', 'REF_SKIP', 'PYTHON', 'OMP', 'MKL', 'R15', 'R18', 'SMA', 'SBAND', 'FTPOS', 'OUT_TAG', 'T2')
EXTRA = sorted(k for k in os.environ if k not in WHITE); assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
BAN = sorted(k for k in os.environ if k.startswith(BANNED)); assert BAN == [], ("CALIBER FLAG PRESENT", BAN)
ENV = dict(env_whitelist=sorted(WHITE), env_actual={k: os.environ[k] for k in sorted(os.environ)}, launch_cmdline=" ".join(sys.argv))
import numpy as np
from scipy.stats import rankdata
ENV.update(python=sys.version.split()[0], numpy=np.__version__)
T0 = time.time()
T2 = "/workspace/uplift_r2_2026-09-13/T2"
PREREG_SHA = "981293b02b2ddae6574fa6dcf8db9b09a65cfa9f122a8b72d7e604ad5ec87eca"; KAPPA_DEV_SHA = "23b5af6b05f6ebb382599cc3b0f4fa54f0fcd42726fca643706c795c514c48fd"
def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def sh(cmd):
    import subprocess
    try: return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.STDOUT).strip()
    except Exception as e: return "ERR %s" % e
assert sha(T2 + "/PREREG_T2_carry_net_sizing_2026-09-13.md") == PREREG_SHA and sha(T2 + "/devices/t2_kappa.py") == KAPPA_DEV_SHA
GPU0 = sh("nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader"); PID0 = sh("ps -o pid,stat -p 333197,339489 | tail -n +2"); LOAD0 = open("/proc/loadavg").read().split()[:3]
KR = json.load(open(T2 + "/receipts/RECEIPT_T2_kappa_main.json")); KP_MAIN = KR["path_outputs"]["main"]["path"]; assert sha(KP_MAIN) == KR["path_outputs"]["main"]["sha256"]
UMASK = "/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz"; assert sha(UMASK) == "47d87b5165b695a7d9b340134a189dd6a2165c837bab35808b699ffac3f7f1b5"
X_META = "/workspace/uplift_2026-09-11/r6/out/meta_newprod_v4_x0910.npz"; assert sha(X_META) == "a8eb359701c71acfe853a295eb055bdbb04e1c29b6534ccdf23aeaff69907245"
X_PANEL = "/workspace/uplift_2026-09-11/r6/out/wide_panel_4h_v2ext_x0910.npz"; assert sha(X_PANEL) == "042478f7d8e9f9476341a2acb310828fcf1f5d4a855c2ad0105a08e78f604549"
EMB = 8 * 3600; MIN_BIN = 180; WINS = 0.20; NMIN = 80
LIVE_LO = calendar.timegm((2026, 8, 26, 0, 0, 0)); UB = calendar.timegm((2026, 8, 30, 20, 0, 0)); T0701 = calendar.timegm((2026, 7, 1, 0, 0, 0)); T0801 = calendar.timegm((2026, 8, 1, 0, 0, 0))
T0901 = calendar.timegm((2026, 9, 1, 0, 0, 0)); T0911 = calendar.timegm((2026, 9, 11, 0, 0, 0))
# ------------------------------------------------------------------ copied verbatim from devices/t2_kappa.py (sha asserted above)
def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    if ok.sum() >= 10: out[ok] = rankdata(v[ok]) / max(ok.sum() - 1, 1) - 0.5
    return out
def load_tree(meta_p, panel_p, carry_forward_umask=False):
    MT = np.load(meta_p, allow_pickle=True); E = MT["E_ts"].astype(np.int64); Y = MT["y4"]; Q = MT["qvk"]
    nA = len(E); mem = np.empty(nA, dtype=object)
    for i in range(nA):
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
def sigma_rows(FN, IV):
    IVf = np.where(np.isfinite(IV) & (IV > 0), IV, 8.0); RN8 = np.nan_to_num(FN, nan=0.0) * (8.0 / IVf)
    out = np.full(FN.shape[0], np.nan)
    for j in range(FN.shape[0]):
        f = np.isfinite(FN[j])
        if f.sum() > 50: out[j] = float(np.std(RN8[j][f])) * 1e4
    return out
def mom(cols, y):
    k = len(cols); Sxx = np.empty((k, k)); Sxy = np.empty(k)
    for a in range(k):
        Sxy[a] = np.sum(cols[a] * y)
        for b in range(a, k):
            Sxx[a, b] = Sxx[b, a] = np.sum(cols[a] * cols[b])
    return Sxx, Sxy
def inv_small(M):
    if M.shape[0] == 2:
        a, b, c, d = M[0, 0], M[0, 1], M[1, 0], M[1, 1]; det = a * d - b * c
        return np.array([[d, -b], [-c, a]]) / det
    a, b, c = M[0]; d, e, f = M[1]; g, h, i = M[2]
    A_ = e * i - f * h; B_ = -(d * i - f * g); C_ = d * h - e * g; D_ = -(b * i - c * h); E_ = a * i - c * g; F_ = -(a * h - b * g); G_ = b * f - c * e; H_ = -(a * f - c * d); I_ = a * e - b * d
    det = a * A_ + b * B_ + c * C_
    return np.array([[A_, D_, G_], [B_, E_, H_], [C_, F_, I_]]) / det
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
        c = (np.nan_to_num(fn, nan=0.0) * (4.0 / IVf[j, m]))[ok].astype(np.float64)
        z = fz[ok]; yr = y[ok].astype(np.float64); yw = np.clip(yr, -WINS, WINS)
        z = z - z.mean(); cd = c - c.mean(); ywd = yw - yw.mean(); yrd = yr - yr.mean()
        cp = np.maximum(c, 0.0); cm = np.minimum(c, 0.0); cpd = cp - cp.mean(); cmd = cm - cm.mean()
        A["valid"][i] = True; A["n"][i] = n
        A["Sxx"][i], A["Sxy"][i] = mom([z, cd], ywd); A["Sxy_raw"][i] = mom([z, cd], yrd)[1]; A["S3xx"][i], A["S3xy"][i] = mom([z, cpd, cmd], ywd)
    return A
def cluster_fit(Sxx, Sxy, clus):
    k = Sxy.shape[1]; Ax = np.zeros((k, k)); s = np.zeros(k)
    for r in range(Sxx.shape[0]): Ax += Sxx[r]; s += Sxy[r]
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
# ------------------------------------------------------------------ extension tree
tx = load_tree(X_META, X_PANEL, carry_forward_umask=True); E = tx["E"]; nA = len(E)
Ax = aggregates(tx); sig_row = sigma_rows(tx["FN"], tx["IV"])
day = (E // 86400).astype(np.int64); week = ((E // 86400 + 3) // 7).astype(np.int64)
sig_anchor = np.array([sig_row[Ax["j"][i]] if Ax["j"][i] >= 0 else np.nan for i in range(nA)])
valid_idx = np.nonzero(Ax["valid"])[0]
def fit_at(T, exclude_from=None):
    w = valid_idx[E[valid_idx] <= T - EMB]
    if exclude_from is not None: w = w[E[w] < exclude_from]
    sc = estimate(Ax, E, w, day, week)
    f2 = cluster_fit(Ax["S3xx"][w], Ax["S3xy"][w], day[w]); sc["d2_side"] = dict(kappa_plus_raw=1.0 - float(f2[0][1]), kappa_minus_raw=1.0 - float(f2[0][2]), se_day_b_plus=float(f2[1][1]), se_day_b_minus=float(f2[1][2])) if f2 else None
    wf = w[np.isfinite(sig_anchor[w])]; q1, q2 = np.quantile(sig_anchor[wf], [1.0 / 3.0, 2.0 / 3.0]); bn = np.where(sig_anchor[wf] <= q1, 0, np.where(sig_anchor[wf] <= q2, 1, 2))
    sc["sigma"] = dict(q1=float(q1), q2=float(q2), bins=[estimate(Ax, E, wf[bn == b_], day, week) for b_ in range(3)])
    sc["T_iso"] = time.strftime("%Y-%m-%d %HZ", time.gmtime(int(T))); sc["last_anchor_used"] = time.strftime("%Y-%m-%d %HZ", time.gmtime(int(E[w[-1]]))); sc["n_live_anchors_in_window"] = int((E[w] >= LIVE_LO).sum())
    sc["live_share"] = dict(anchors=float((E[w] >= LIVE_LO).mean()), obs=float(Ax["n"][w][E[w] >= LIVE_LO].sum() / max(Ax["n"][w].sum(), 1)),
                            carry_variance_moment=float(Ax["Sxx"][w][E[w] >= LIVE_LO][:, 1, 1].sum() / Ax["Sxx"][w][:, 1, 1].sum()),
                            fund_score_variance_moment=float(Ax["Sxx"][w][E[w] >= LIVE_LO][:, 0, 0].sum() / Ax["Sxx"][w][:, 0, 0].sum()))
    return sc
RC = dict(self_sha256=sha(os.path.abspath(__file__)), prereg_sha256=PREREG_SHA, program_amendment="PROGRAM_uplift_r2_2026-09-13.md AMENDMENT 2, commit 83579437", label="POST-HOC DESCRIPTIVE reporting addendum; frozen T2 rule and verdicts unchanged",
          env=ENV, inputs=dict(x_meta=X_META, x_panel=X_PANEL, umask=UMASK, kpath_main=KP_MAIN), umask_carry_forward_panel_rows=int(tx["umask_carry_forward_rows"]))
# R0 reproduction gate
REG = {e["T"]: e for e in KR["refits"]}
R0 = {}
for T in (T0701, T0801):
    a = fit_at(T); r = REG[T]
    keys = ("lam", "b", "kappa_raw", "kappa", "lam_plus", "se_day_b", "se_week_b", "se_day_lam", "n_anchors", "n_obs")
    same = {k: bool(a[k] == r[k]) for k in keys}
    same["sigma_q1"] = bool(a["sigma"]["q1"] == r["sigma"]["q1"]); same["sigma_q2"] = bool(a["sigma"]["q2"] == r["sigma"]["q2"])
    same["sigma_bins_kappa_raw"] = bool(all(ba["kappa_raw"] == bb["kappa_raw"] and ba["n_anchors"] == bb["n_anchors"] for ba, bb in zip(a["sigma"]["bins"], r["sigma"]["bins"])))
    R0[a["T_iso"]] = dict(bitwise=same, PASS=bool(all(same.values())), kappa_raw_ext=a["kappa_raw"], kappa_raw_registered=r["kappa_raw"])
RC["R0_reproduction"] = R0; RC["R0_PASS"] = bool(all(v["PASS"] for v in R0.values()))
print("R0", json.dumps({k: v["PASS"] for k, v in R0.items()}), flush=True)
if not RC["R0_PASS"]:
    json.dump(RC, open(T2 + "/receipts/RECEIPT_T2_live_addendum.json", "w"), indent=1, default=float); print("STOP: extension tree does not reproduce the registered refits"); sys.exit(3)
# R1 κ used on the replayed live anchors (registered path)
KP = np.load(KP_MAIN, allow_pickle=True); Ek = KP["E_ts"].astype(np.int64); lv = (Ek >= LIVE_LO) & (Ek <= UB)
RC["R1_used_on_replayed_live_anchors"] = dict(n=int(lv.sum()), refit_ts=sorted(set(time.strftime("%Y-%m-%d", time.gmtime(int(t))) for t in KP["refit_ts"][lv] if np.isfinite(t))),
    scalar=dict(kappa=sorted(set(float(x) for x in KP["kappa_scalar"][lv])), lam=sorted(set(float(x) for x in KP["lam_scalar"][lv]))),
    sigma=dict(bins={int(b): int((KP["bin_sigma"][lv] == b).sum()) for b in (0, 1, 2)}, kappa_by_bin={int(b): sorted(set(float(x) for x in KP["kappa_sigma"][lv & (KP["bin_sigma"] == b)])) for b in (0, 1, 2)},
               lam_by_bin={int(b): sorted(set(float(x) for x in KP["lam_sigma"][lv & (KP["bin_sigma"] == b)])) for b in (0, 1, 2)}, q1=sorted(set(float(x) for x in KP["q1"][lv])), q2=sorted(set(float(x) for x in KP["q2"][lv]))),
    note="the 2026-08-01 refit uses anchors up to 2026-07-31 16Z: the κ the arms used in the live window contains no live-window data by construction")
# R2 refits containing live data
R2 = dict(registered_2026_09_01=dict(**{k: REG[T0901][k] for k in ("kappa_raw", "kappa", "lam", "se_day_b", "n_anchors")}, sigma_bins_kappa_raw=[b["kappa_raw"] for b in REG[T0901]["sigma"]["bins"]], d2_side=REG[T0901].get("d2_side")),
          ext_2026_08_01=fit_at(T0801), ext_2026_09_01=fit_at(T0901), ext_2026_09_11=fit_at(T0911), ext_2026_09_11_without_live=fit_at(T0911, exclude_from=LIVE_LO))
R2["delta_kappa_raw_from_adding_live_window"] = R2["ext_2026_09_11"]["kappa_raw"] - R2["ext_2026_09_11_without_live"]["kappa_raw"]
R2["delta_kappa_raw_0801_to_0911"] = R2["ext_2026_09_11"]["kappa_raw"] - R2["ext_2026_08_01"]["kappa_raw"]
RC["R2_refits_with_live_data"] = R2
# R3 live-window-only estimate vs earlier non-overlapping 91-valid-anchor blocks (ending at the last valid anchor)
live_valid = valid_idx[E[valid_idx] >= LIVE_LO]; L = len(live_valid)
blocks = []
end = len(valid_idx)
while end - L >= 0:
    blk = valid_idx[end - L:end]; e = estimate(Ax, E, blk, day, week)
    blocks.append(dict(first=time.strftime("%Y-%m-%d %HZ", time.gmtime(int(E[blk[0]]))), last=time.strftime("%Y-%m-%d %HZ", time.gmtime(int(E[blk[-1]]))), kappa_raw=e.get("kappa_raw"), b=e.get("b"), lam=e.get("lam"), se_day_b=e.get("se_day_b"),
                       sigma_mean=float(np.nanmean(sig_anchor[blk])), carry_abs_moment_per_obs=float(Ax["Sxx"][blk][:, 1, 1].sum() / max(Ax["n"][blk].sum(), 1)), first_ts=int(E[blk[0]])))
    end -= L
live_blk = blocks[0]; hist = [b for b in blocks[1:] if b["kappa_raw"] is not None]
assert live_blk["first"].startswith("2026-08-26"), live_blk
def pct(v, arr): arr = np.asarray(arr, float); return float((arr < v).mean() * 100.0)
h24 = [b for b in hist if b["first_ts"] >= calendar.timegm((2024, 1, 1, 0, 0, 0))]
RC["R3_live_block_vs_history"] = dict(block_len_valid_anchors=L, live=live_blk, n_hist_blocks=len(hist), n_hist_blocks_2024on=len(h24),
    kappa_raw_percentile_all=pct(live_blk["kappa_raw"], [b["kappa_raw"] for b in hist]), kappa_raw_percentile_2024on=pct(live_blk["kappa_raw"], [b["kappa_raw"] for b in h24]),
    hist_kappa_raw_quantiles_all=[float(x) for x in np.quantile([b["kappa_raw"] for b in hist], [0.05, 0.25, 0.5, 0.75, 0.95])],
    hist_kappa_raw_quantiles_2024on=[float(x) for x in np.quantile([b["kappa_raw"] for b in h24], [0.05, 0.25, 0.5, 0.75, 0.95])],
    lam_percentile_all=pct(live_blk["lam"], [b["lam"] for b in hist]), lam_percentile_2024on=pct(live_blk["lam"], [b["lam"] for b in h24]),
    sigma_mean_percentile_all=pct(live_blk["sigma_mean"], [b["sigma_mean"] for b in hist]), sigma_mean_percentile_2024on=pct(live_blk["sigma_mean"], [b["sigma_mean"] for b in h24]),
    carry_moment_percentile_all=pct(live_blk["carry_abs_moment_per_obs"], [b["carry_abs_moment_per_obs"] for b in hist]), carry_moment_percentile_2024on=pct(live_blk["carry_abs_moment_per_obs"], [b["carry_abs_moment_per_obs"] for b in h24]),
    blocks=blocks)
# R4 σ bins of the live anchors under the 2026-08-01 cut points
q1, q2 = R2["ext_2026_08_01"]["sigma"]["q1"], R2["ext_2026_08_01"]["sigma"]["q2"]; ls = sig_anchor[live_valid]
RC["R4_live_sigma"] = dict(q1_0801=q1, q2_0801=q2, n=int(len(ls)), bins_0801={0: int((ls <= q1).sum()), 1: int(((ls > q1) & (ls <= q2)).sum()), 2: int((ls > q2).sum())}, sigma_mean=float(np.nanmean(ls)), sigma_median=float(np.nanmedian(ls)))
# R5 carry levels
def recload(tag):
    Z = np.load(T2 + "/arms/%s.npz" % tag, allow_pickle=True); C = [str(c) for c in Z["cols"]]; r = np.asarray(Z["d30_n2_c42_rec"], float); ts = r[:, C.index("ts")].astype(np.int64); gt = r[:, C.index("gross_total")]
    return Z, ts, r[:, C.index("carry_ex")] / gt, r[:, C.index("pnl_ex")] / gt, r[:, C.index("net_ex")] / gt
R5 = {}
for s in ("42", "2027"):
    Z, ts, car, pnl, g = recload("GP_A0_s%s" % s); wa = ts <= UB; wa[:900] = False; lvr = (ts >= LIVE_LO) & (ts <= UB); assert lvr.sum() == 30 and wa.sum() == 9138
    R5["A0_s" + s] = dict(carry_W_ALPHA=float(car[wa].mean()), carry_live30=float(car[lvr].mean()), carry_ratio_live_to_W_ALPHA=float(car[lvr].mean() / car[wa].mean()), pnl_W_ALPHA=float(pnl[wa].mean()), pnl_live30=float(pnl[lvr].mean()), g_live30=float(g[lvr].mean()))
# fund-leg rank-book carry (SEATNET quantity): reproduce ARM-SK's stored T2C_fund on the replay axis, then extend to 2026-09-10
Zs = np.load(T2 + "/arms/SK_A0_s42.npz", allow_pickle=True); lts = Zs["legs_ts"].astype(np.int64); t2c = np.asarray(Zs["T2C_fund"], float); assert len(lts) == len(t2c)
IVf = np.where(np.isfinite(tx["IV"]) & (tx["IV"] > 0), tx["IV"], 8.0)
def fund_rankbook_carry(i):
    j = tx["prow"].get(int(E[i]))
    if j is None: return None
    m = tx["mem"][i]; mk = tx["urow"].get(j)
    if mk is not None: m = m[mk[m]]
    ok = np.isfinite(tx["Y"][i, m])
    z = np.nan_to_num(xz(tx["FE"][j, :])[m]); z = np.where(ok, z, 0.0); z -= z[ok].mean() if ok.sum() else 0
    g = np.abs(z).sum()
    return float((z / g * np.nan_to_num(tx["FN"][j, m], nan=0.0) * (4.0 / IVf[j, m])).sum() * 1e4) if g > 1e-9 else 0.0
imap = {int(t): i for i, t in enumerate(E)}
rep = np.array([fund_rankbook_carry(imap[int(t)]) for t in lts]); same = bool(np.array_equal(rep, t2c))
# NB: the replay device's legs() reads the incumbent umask directly (no carry-forward); on the replay axis (ts <= 2026-08-31 00Z) the rows are identical
ext_idx = [i for i in range(nA) if int(E[i]) in tx["prow"] and int(E[i]) > int(lts[-1])]
ext_c = np.array([fund_rankbook_carry(i) for i in ext_idx]); ext_t = E[np.array(ext_idx, np.int64)]
wa_mask = np.zeros(len(lts), bool); wa_mask[900:] = True; wa_mask &= lts <= UB
all_t = np.concatenate([lts, ext_t]); all_c = np.concatenate([t2c, ext_c]); live_m = all_t >= LIVE_LO
R5["fund_rank_book_carry"] = dict(reproduces_ARM_SK_T2C_fund_bitwise=same, n_replay_axis=int(len(lts)), n_extension_rows=int(len(ext_idx)), W_ALPHA_mean=float(t2c[wa_mask].mean()),
                                  live_window_mean=float(all_c[live_m].mean()), live_window_n=int(live_m.sum()), ratio_live_to_W_ALPHA=float(all_c[live_m].mean() / t2c[wa_mask].mean()),
                                  replayed_live30_mean=float(t2c[(lts >= LIVE_LO) & (lts <= UB)].mean()), last=time.strftime("%Y-%m-%d %HZ", time.gmtime(int(all_t[-1]))),
                                  note="leg rank book (unit gross, before blending, EMA and FTRIM), not the executed book; a different object from the executed-book carry in AMENDMENT 2")
RC["R5_carry_levels"] = R5
GPU1 = sh("nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader"); PID1 = sh("ps -o pid,stat -p 333197,339489 | tail -n +2")
RC.update(gpu_before=GPU0, gpu_after=GPU1, protected_pids_before=PID0, protected_pids_after=PID1, loadavg_before=LOAD0, wall_s=round(time.time() - T0, 1), built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
json.dump(RC, open(T2 + "/receipts/RECEIPT_T2_live_addendum.json", "w"), indent=1, default=float)
r2 = RC["R2_refits_with_live_data"]; r3 = RC["R3_live_block_vs_history"]
print("R1", json.dumps(RC["R1_used_on_replayed_live_anchors"]["scalar"]), json.dumps(RC["R1_used_on_replayed_live_anchors"]["sigma"]["bins"]), json.dumps(RC["R1_used_on_replayed_live_anchors"]["sigma"]["kappa_by_bin"]))
for k in ("ext_2026_08_01", "ext_2026_09_01", "ext_2026_09_11", "ext_2026_09_11_without_live"):
    e = r2[k]; print("R2", k, "kraw %.4f ci %s lam %.2e n %d live_in %d live_share carry-moment %.4f obs %.4f | sigma bins kraw %s" % (e["kappa_raw"], [round(x, 3) for x in e["kappa_raw_ci95_day"]], e["lam"], e["n_anchors"], e["n_live_anchors_in_window"], e["live_share"]["carry_variance_moment"], e["live_share"]["obs"], [round(b["kappa_raw"], 3) for b in e["sigma"]["bins"]]))
print("R2 registered 09-01", json.dumps(r2["registered_2026_09_01"]), "| delta from live", r2["delta_kappa_raw_from_adding_live_window"], "| 0801->0911", r2["delta_kappa_raw_0801_to_0911"])
print("R3 live", json.dumps({k: r3["live"][k] for k in ("first", "last", "kappa_raw", "lam", "se_day_b", "sigma_mean", "carry_abs_moment_per_obs")}), "pct all/2024on kraw %.1f/%.1f lam %.1f/%.1f sigma %.1f/%.1f carrymom %.1f/%.1f" % (r3["kappa_raw_percentile_all"], r3["kappa_raw_percentile_2024on"], r3["lam_percentile_all"], r3["lam_percentile_2024on"], r3["sigma_mean_percentile_all"], r3["sigma_mean_percentile_2024on"], r3["carry_moment_percentile_all"], r3["carry_moment_percentile_2024on"]), "hist q", [round(x, 3) for x in r3["hist_kappa_raw_quantiles_2024on"]], "n", r3["n_hist_blocks"], r3["n_hist_blocks_2024on"])
print("R4", json.dumps(RC["R4_live_sigma"])); print("R5", json.dumps(R5))
print("DONE_t2_live_addendum", RC["wall_s"], "s")
