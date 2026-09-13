#!/usr/bin/env python3
"""materiality_probe.py — PREREG_parity_materiality_2026-09-13 §1-§7, read-only, CPU.

Answers: is the G-P2 residual of the production-code replay economically material?
  dg(A) = 1e4 * sum_i (w_replay_i - w_live_i) * r_i / G_live,  bps/anchor/unit gross (judge caliber).

TWO BOOK PAIRS (PREREG §1.1):
  PRIMARY  "deployed" : replay state/target_live_combo/<A>.json  vs  WS state/target_live/<A>.json
                        -> combo_stage.py:270/348  combo_raw = 0.55*sm_kc + 0.45*sm_fc, full float.
                           This is the file the executor (~/dl_quant_live) reads at N+23.
  SECONDARY "execcal" : replay state/target_combo/<A>.json       vs  WS state/target_combo/<A>.json
                        -> combo_stage.py:271/273  combo = exec_reshape(combo_raw), round(.,8).
                           This is the pair the RESULT_parity_phase1 "14 names / 1.13e-4" facts come from.
  The frozen §5 verdict is read off the PRIMARY pair; the SECONDARY is a declared robustness check.

Caliber binding (E-0904-F), PREREG §1.2:
  r_i(A) = SUM over the 48 rows in (A, A+4h] of rolling.npz['data'][:, i, 0] ("ret5",
  5m simple returns HARD-CLIPPED to +-0.30 by shadow_loop_v3.py:150/253), density gate
  >=46 finite rows else NaN, NaN -> 0 in the dot product.  This is verbatim the producer's
  own settlement formula shadow_loop_v3.py:428-433.  It is NOT the accounting canon
  y4s = prod(1+r)-1 over UNCLIPPED returns (meta_newprod_v4.npz, pod2, out of reach here).

Writes ONLY into parity_replay_2026-09-12/receipts/.  Never writes to ~/wide_shadow or
~/dl_quant_live; no network; no API; no process control.

Launch:  python3 -B materiality_probe.py "<comma-separated env whitelist>"
"""
import os, sys, json, time, hashlib

# ---------------------------------------------------------------- env discipline (E-0826-D)
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "launch with a non-empty env whitelist as argv[1]"
BANNED = ('CAL', 'JUDGE', 'UPLIFT', 'PANEL', 'LOOK', 'WRULE', 'LEGS', 'PHI', 'FSEED', 'W3FIX',
          'FTRIM', 'UMASK', 'SLOW', 'FPRED', 'MEMBERS_TOPN', 'COSTB', 'SLEEVE', 'KMOD', 'SEAT',
          'RNSM', 'LTRIM', 'CDAMP', 'FUNDSCALE', 'FEMAT', 'TRADE_TOPN', 'REF_SKIP', 'OMP', 'MKL',
          'R18', 'SMA', 'SBAND', 'FTPOS', 'OUT_TAG', 'REPLAY', 'WIDE_SHADOW', 'COMBO')
EXTRA = sorted(k for k in os.environ if k not in WHITE)
assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
BAN = sorted(k for k in os.environ if k.startswith(BANNED))
assert BAN == [], ("CALIBER FLAG PRESENT", BAN)
ENV = dict(env_whitelist=sorted(WHITE), env_actual={k: os.environ[k] for k in sorted(os.environ)},
           launch_cmdline=" ".join(sys.argv))

import numpy as np
ENV.update(python=sys.version.split()[0], numpy=np.__version__)

# ---------------------------------------------------------------- paths + frozen shas
WS = "/Users/haosiyu/wide_shadow"
R = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/parity_replay_2026-09-12"
RH = R + "/replay_home"
DOC = "/Users/haosiyu/Desktop/quant_research/docs/PREREG_parity_materiality_2026-09-13.md"
PREREG_SHA = "eb9f5e412f0c333642e2676771b41a1e6a5623542418ee00688fa30d53090b02"
CHAIN_RECEIPT = R + "/receipts/PARITY_phase1_chain_full_1788624000_1789200000.json"


def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def statsig(p):
    s = os.stat(os.path.realpath(p))
    return dict(size=s.st_size, mtime_ns=s.st_mtime_ns)


assert sha(DOC) == PREREG_SHA, ("PREREG SHA MISMATCH — judged criteria are not the frozen ones",
                                sha(DOC), PREREG_SHA)
SELF_SHA = sha(os.path.abspath(__file__))

# ---------------------------------------------------------------- frozen constants (PREREG §4/§5)
NB = 2000
RNG_BASE = 20260905
JUDGE_RES_BPS = 0.23                      # r18_judge.py:31, PREREG_r18 line 59
EFF_LO, EFF_HI = 0.02, 0.60
FIT_STRICT_MEAN = EFF_LO / 10.0           # 0.002
FIT_MEAN = EFF_LO / 3.0                   # 0.0066667
FIT_STRICT_MAX = EFF_LO / 3.0             # 0.0066667
UNFIT_MEAN = EFF_HI / 3.0                 # 0.2
SIGMA_G_REF = 0.6341957 * np.sqrt(2190.0) / 1.29122344   # ~22.98 bps, archived C0_s42 W_ALPHA
NOISE_BAR = 0.1 * SIGMA_G_REF
CLIP_ABS = float(np.float16(0.30))        # 0.300048828125
DENSITY_MIN = 46                          # shadow_loop_v3.py:432
STEP, H4 = 300, 14400

A0, A1 = 1788624000, 1789200000
ANCHORS = list(range(A0, A1 + 1, H4))
assert len(ANCHORS) == 41, len(ANCHORS)
POSCTRL = [1789214400, 1789228800, 1789243200]

PAIRS = {
    "deployed": dict(replay=RH + "/state/target_live_combo/%d.json",
                     live=WS + "/state/target_live/%d.json",
                     receipt_key="target_live_Linf",
                     note="combo_raw (full float); the file the executor reads"),
    "execcal": dict(replay=RH + "/state/target_combo/%d.json",
                    live=WS + "/state/target_combo/%d.json",
                    receipt_key="target_combo_Linf",
                    note="exec_reshape(combo_raw), round(.,8); source of the published 14-name fact"),
}

# ---------------------------------------------------------------- inputs + G-M3
CFG_P = WS + "/shadow_bundle/config.json"
ROLL_P = WS + "/state/rolling.npz"
roll_sha_before, roll_stat_before = sha(ROLL_P), statsig(ROLL_P)
cfg = json.load(open(CFG_P))
SYMS = list(cfg["symbols_panel"])
NWD = len(SYMS)
assert NWD == 829, NWD
SYM_IDX = {s: j for j, s in enumerate(SYMS)}

Z = np.load(ROLL_P)
CTS = np.asarray(Z["ts"], np.int64)
CD = Z["data"]
assert CD.shape == (len(CTS), NWD, 7), CD.shape
ROW_OF = {int(t): i for i, t in enumerate(CTS)}
roll_sha_after, roll_stat_after = sha(ROLL_P), statsig(ROLL_P)
GM3 = dict(sha_before=roll_sha_before, sha_after=roll_sha_after,
           stat_before=roll_stat_before, stat_after=roll_stat_after,
           PASS=bool(roll_sha_before == roll_sha_after and roll_stat_before == roll_stat_after),
           cache_first_ts=int(CTS[0]), cache_last_ts=int(CTS[-1]), cache_rows=int(len(CTS)))
assert GM3["PASS"], GM3


# ---------------------------------------------------------------- books / returns
def book(p):
    return {k: float(v) for k, v in json.load(open(p))["weights"].items()}


def wpair(pair, A):
    P = PAIRS[pair]
    return book(P["replay"] % A), book(P["live"] % A)


def linf(wr, wl):
    keys = set(wr) | set(wl)
    return max(abs(wr.get(k, 0.0) - wl.get(k, 0.0)) for k in keys) if keys else 0.0


def rows_after(A):
    pi, ai = ROW_OF.get(A), ROW_OF.get(A + H4)
    if pi is None or ai is None:
        return None
    assert ai - pi == H4 // STEP, (A, pi, ai)
    return (pi + 1, ai + 1)


def retvec(A):
    rr = rows_after(A)
    if rr is None:
        return None, None, None
    lo, hi = rr
    seg = CD[lo:hi, :, 0].astype(np.float64)
    fin = np.isfinite(seg)
    nfin = fin.sum(0)
    y4P = np.where(fin, seg, 0.0).sum(0)
    y4C = np.expm1(np.log1p(np.where(fin, seg, 0.0)).sum(0))
    bad = nfin < DENSITY_MIN
    y4P[bad] = np.nan
    y4C[bad] = np.nan
    return y4P, y4C, dict(rows=(int(CTS[lo]), int(CTS[hi - 1])), n_rows=int(hi - lo),
                          n_finite_names=int((~bad).sum()))


def vec(w):
    v = np.zeros(NWD, np.float64)
    miss = []
    for k, x in w.items():
        j = SYM_IDX.get(k)
        if j is None:
            miss.append(k)
        else:
            v[j] = x
    return v, miss


# ---------------------------------------------------------------- G-M1 integrity gate (both pairs)
CH = json.load(open(CHAIN_RECEIPT))
REC = {int(a["anchor"]): a for a in CH["anchors"]}
gm1 = {}
for pair, P in PAIRS.items():
    worst = 0.0
    rowsg = []
    for A in ANCHORS:
        wr, wl = wpair(pair, A)
        got = linf(wr, wl)
        exp = float(REC[A]["combo"][P["receipt_key"]])
        rel = abs(got - exp) / max(exp, 1e-300)
        worst = max(worst, rel)
        rowsg.append(dict(anchor=A, recomputed=got, receipt=exp, rel=rel))
    gm1[pair] = dict(n=len(rowsg), worst_rel=worst, PASS=bool(worst <= 1e-12),
                     receipt_key=P["receipt_key"],
                     worst_anchor=max(rowsg, key=lambda x: x["rel"]))
GM1 = dict(per_pair=gm1, receipt=os.path.basename(CHAIN_RECEIPT),
           receipt_sha256=sha(CHAIN_RECEIPT),
           PASS=bool(all(v["PASS"] for v in gm1.values())))
assert GM1["PASS"], ("G-M1 RED: on-disk replay outputs are not the ones the receipt describes", GM1)

# ---------------------------------------------------------------- G-M0 clip inertness
lo0, hi0 = ROW_OF[A0] + 1, ROW_OF[A1 + H4] + 1
segall = CD[lo0:hi0, :, 0].astype(np.float64)
hit = np.isfinite(segall) & (np.abs(segall) >= CLIP_ABS)
hit_j = sorted(int(j) for j in np.unique(np.nonzero(hit)[1]))
GM0 = dict(window_rows=(int(CTS[lo0]), int(CTS[hi0 - 1])), n_rows=int(hi0 - lo0),
           n_cells_scanned=int(np.isfinite(segall).sum()), clip_abs=CLIP_ABS,
           n_cells_at_clip=int(hit.sum()), n_names_at_clip=len(hit_j),
           names_at_clip=[SYMS[j] for j in hit_j],
           global_min=float(np.nanmin(segall)), global_max=float(np.nanmax(segall)),
           PASS=bool(hit.sum() == 0))

# ---------------------------------------------------------------- positive control (F2)
POS = []
for A in POSCTRL:
    e = dict(anchor=A, iso=time.strftime("%Y-%m-%d %HZ", time.gmtime(A)), pairs={})
    y4P, _, meta = retvec(A)
    for pair in PAIRS:
        wr, wl = wpair(pair, A)
        keys = sorted(set(wr) | set(wl))
        dws = [wr.get(k, 0.0) - wl.get(k, 0.0) for k in keys]
        ent = dict(n_keys=len(keys), dw_all_exactly_zero=bool(all(d == 0.0 for d in dws)),
                   dw_Linf=float(max(abs(d) for d in dws)) if dws else 0.0)
        if y4P is None:
            ent.update(dg=None, returns_available=False,
                       note="forward window (A, A+4h] is NOT in the cache; dg is identically zero "
                            "because every dw is exactly 0.0, but it is not measured against a real r")
        else:
            vr, _ = vec(wr)
            vl, _ = vec(wl)
            r = np.nan_to_num(y4P, nan=0.0)
            val = 1e4 * float((vr - vl) @ r) / float(np.abs(vl).sum())
            ent.update(dg=val, returns_available=True, dg_is_exactly_zero=bool(val == 0.0),
                       ret_window=meta["rows"])
        e["pairs"][pair] = ent
    POS.append(e)
bad = [(e["anchor"], p, v) for e in POS for p, v in e["pairs"].items()
       if (not v["dw_all_exactly_zero"]) or (v.get("returns_available") and not v["dg_is_exactly_zero"])]
assert not bad, ("F2 POSITIVE CONTROL FAILED — pipeline is wrong, main-window numbers withheld", bad)

# ------------------------------------------- G-M5 red capability: dg must NOT be a constant-zero map
# The positive control above is dg == 0.  On its own that is also what a broken dot product returns.
# So inject two perturbations of KNOWN size into the replay book and require the measured dg to equal
# the closed-form answer.  (a) pure scale (1+eps)*w_live -> dg must be exactly eps*g_live;
# (b) single held name +delta -> dg must be 1e4*delta*r_i/G.  Nothing here feeds the verdict.
GM5 = {"cases": []}
for A in (ANCHORS[0], ANCHORS[len(ANCHORS) // 2], ANCHORS[-1]):
    y4P, _, _ = retvec(A)
    r = np.nan_to_num(y4P, nan=0.0)
    _, wl = wpair("deployed", A)
    vl, _ = vec(wl)
    G = float(np.abs(vl).sum())
    g_live = 1e4 * float(vl @ r) / G
    eps = 1e-4
    got_a = 1e4 * float(((1 + eps) * vl - vl) @ r) / G
    exp_a = eps * g_live
    held = np.nonzero(vl)[0]
    j = int(held[int(np.argmax(np.abs(r[held])))])      # the held name with the largest |r|
    delta = 1e-4
    pert = vl.copy()
    pert[j] += delta
    got_b = 1e4 * float((pert - vl) @ r) / G
    exp_b = 1e4 * delta * float(r[j]) / G
    GM5["cases"].append(dict(
        anchor=A, iso=time.strftime("%Y-%m-%d %HZ", time.gmtime(A)), g_live=g_live,
        scale=dict(eps=eps, measured=got_a, closed_form=exp_a,
                   rel=abs(got_a - exp_a) / max(abs(exp_a), 1e-300), nonzero=bool(got_a != 0.0)),
        single_name=dict(name=SYMS[j], r_i=float(r[j]), delta=delta, measured=got_b,
                         closed_form=exp_b, rel=abs(got_b - exp_b) / max(abs(exp_b), 1e-300),
                         nonzero=bool(got_b != 0.0))))
# Tolerances.  The single-name case is exact arithmetic -> 1e-12.  The scale case forms
# (1+eps)*w - w, which cancels ~4 decimal digits for eps=1e-4; its float64 floor is about
# eps^-1 * 2^-53 ~ 1.1e-12, so 1e-12 would fail on cancellation alone.  1e-9 sits three orders
# above that floor and still catches any structural error.  Achieved values are in the receipt.
GM5["tol"] = dict(scale_rel=1e-9, single_name_rel=1e-12,
                  why_scale_looser="(1+eps)*w-w cancels ~4 digits; float64 floor ~ eps^-1*2^-53 ~ 1.1e-12")
GM5["PASS"] = bool(all(c["scale"]["nonzero"] and c["single_name"]["nonzero"] and
                       c["scale"]["rel"] <= 1e-9 and c["single_name"]["rel"] <= 1e-12
                       for c in GM5["cases"]))
assert GM5["PASS"], ("G-M5 RED-CAPABILITY FAILED — dg does not respond to a known perturbation", GM5)


# ---------------------------------------------------------------- bootstrap (PREREG §3)
def boot(d, day, off=0):
    dd = {}
    for k in range(len(d)):
        dd.setdefault(day[k], []).append(k)
    keys = sorted(dd)
    tot = np.array([d[dd[k]].sum() for k in keys])
    cnt = np.array([len(dd[k]) for k in keys], float)
    nd = len(keys)
    r = np.stack([np.random.default_rng([RNG_BASE, off + k]).integers(0, nd, nd) for k in range(NB)])
    ms = tot[r].sum(1) / cnt[r].sum(1)
    return dict(ci95=[float(np.percentile(ms, 2.5)), float(np.percentile(ms, 97.5))],
                se=float(ms.std(ddof=1)), n_days=nd, day_counts={k: int(len(dd[k])) for k in keys})


def boot_iid(d, off=0):
    n = len(d)
    r = np.stack([np.random.default_rng([RNG_BASE, off + k]).integers(0, n, n) for k in range(NB)])
    ms = d[r].mean(1)
    return dict(ci95=[float(np.percentile(ms, 2.5)), float(np.percentile(ms, 97.5))],
                se=float(ms.std(ddof=1)), n=n)


def verdict_of(U_mean, U_max, S_rms):
    if U_mean <= FIT_STRICT_MEAN and U_max <= FIT_STRICT_MAX:
        v = "FIT-STRICT"
    elif U_mean <= FIT_MEAN:
        v = "FIT"
    elif U_mean <= UNFIT_MEAN:
        v = "PARTIALLY-FIT"
    else:
        v = "UNFIT"
    return v, bool(S_rms > NOISE_BAR)


DAY = np.array([time.strftime("%Y%m%d", time.gmtime(A)) for A in ANCHORS])

# ---------------------------------------------------------------- main loop, per pair
RESULTS = {}
for pair in PAIRS:
    rows, track = [], {}
    for A in ANCHORS:
        wr, wl = wpair(pair, A)
        vr, miss_r = vec(wr)
        vl, miss_l = vec(wl)
        y4P, y4C, meta = retvec(A)
        assert y4P is not None, A
        rP, rC = np.nan_to_num(y4P, nan=0.0), np.nan_to_num(y4C, nan=0.0)
        dw = vr - vl
        G, Gr = float(np.abs(vl).sum()), float(np.abs(vr).sum())
        dg = 1e4 * float(dw @ rP) / G
        g_live = 1e4 * float(vl @ rP) / G
        beta = float((vr @ vl) / (vl @ vl))
        e = dw - (beta - 1.0) * vl
        nanmask = ~np.isfinite(y4P)
        held = (vl != 0) | (vr != 0)
        sup = np.nonzero(held)[0]
        a, b = vr[sup], vl[sup]
        ra = np.argsort(np.argsort(a)).astype(float)
        rb = np.argsort(np.argsort(b)).astype(float)
        for j in np.nonzero(dw)[0]:
            track[int(j)] = max(track.get(int(j), 0.0), abs(float(dw[j])))
        rows.append(dict(anchor=A, iso=time.strftime("%Y-%m-%d %HZ", time.gmtime(A)),
                         dg=dg, dg_raw=1e4 * float(dw @ rP), dg_compounded=1e4 * float(dw @ rC) / G,
                         g_live=g_live, g_replay=1e4 * float(vr @ rP) / Gr,
                         gross_live=G, gross_replay=Gr, gross_frac=(Gr - G) / G,
                         L1=float(np.abs(dw).sum()), L1_frac=float(np.abs(dw).sum()) / G,
                         Linf=float(np.abs(dw).max()), n_dw_nonzero=int((dw != 0).sum()),
                         n_only_replay=len(set(wr) - set(wl)), n_only_live=len(set(wl) - set(wr)),
                         n_names_replay=len(wr), n_names_live=len(wl),
                         miss_from_axis=(miss_r, miss_l),
                         beta=beta, dg_scale=(beta - 1.0) * g_live,
                         dg_cross=1e4 * float(e @ rP) / G,
                         spearman=float(np.corrcoef(ra, rb)[0, 1]),
                         pearson=float(np.corrcoef(a, b)[0, 1]),
                         ret_window=meta["rows"], n_finite_ret=meta["n_finite_names"],
                         unmeasured_abs_dw=float(np.abs(dw[nanmask & held]).sum()),
                         _dw=dw, _r=rP))
    S = sorted([j for j, v in track.items() if v > 1e-6])
    SN = [SYMS[j] for j in S]
    m_ = np.zeros(NWD, bool)
    m_[S] = True
    for rw in rows:
        dw, r = rw.pop("_dw"), rw.pop("_r")
        G = rw["gross_live"]
        rw["dg_S"] = 1e4 * float((dw * m_) @ r) / G
        rw["dg_notS"] = 1e4 * float((dw * ~m_) @ r) / G
        rw["L1_S_frac"] = float(np.abs(dw[m_]).sum() / max(np.abs(dw).sum(), 1e-300))

    DG = np.array([rw["dg"] for rw in rows])
    DGC = np.array([rw["dg_compounded"] for rw in rows])
    B, B9, BI = boot(DG, DAY, 0), boot(DG, DAY, 9 * NB), boot_iid(DG, 0)
    BC = boot(DGC, DAY, 0)
    m = float(DG.mean())
    Hw = (B["ci95"][1] - B["ci95"][0]) / 2.0
    U_mean = abs(m) + Hw
    U_max = float(np.abs(DG).max())
    S_rms = float(np.sqrt((DG ** 2).mean()))
    v, nf = verdict_of(U_mean, U_max, S_rms)
    worst_anchor = max(rows, key=lambda rw: abs(rw["dg"]))

    def rat(num, den):
        """robust share: ratio-of-sums (primary) + median of per-anchor ratios (PREREG §7.1 literal)."""
        pa = [abs(rw[num]) / max(abs(rw[den]), 1e-300) for rw in rows]
        return dict(ratio_of_sums=float(sum(abs(rw[num]) for rw in rows) /
                                        max(sum(abs(rw[den]) for rw in rows), 1e-300)),
                    median_per_anchor=float(np.median(pa)),
                    mean_per_anchor_UNSTABLE=float(np.mean(pa)),
                    p90_per_anchor=float(np.percentile(pa, 90)))

    RESULTS[pair] = dict(
        note=PAIRS[pair]["note"],
        verdict=dict(verdict=v, noise_clause_violated=nf, mean_dg=m, ci95=B["ci95"], half_width=Hw,
                     U_mean=U_mean, U_max=U_max, S_rms=S_rms, X_fit_3x=3.0 * U_mean,
                     X_fit_10x=10.0 * U_mean, ratio_to_judge_resolution=U_mean / JUDGE_RES_BPS,
                     F1_triggered=bool(U_mean > UNFIT_MEAN),
                     worst_anchor=dict(anchor=worst_anchor["anchor"], iso=worst_anchor["iso"],
                                       dg=worst_anchor["dg"], Linf=worst_anchor["Linf"],
                                       g_live=worst_anchor["g_live"])),
        estimator=dict(block_bootstrap=B, block_bootstrap_k9=B9, iid_bootstrap=BI,
                       naive_se=float(DG.std(ddof=1) / np.sqrt(len(DG))),
                       compounded_caliber_block_bootstrap=BC, mean_dg_compounded=float(DGC.mean()),
                       caliber_spread_mean_abs=float(np.abs(DG - DGC).mean()),
                       caliber_spread_max_abs=float(np.abs(DG - DGC).max())),
        decomposition=dict(
            affected_names=SN, affected_n=len(SN),
            ever_nonzero_dw_n=len(track),
            share_of_dg_from_affected=rat("dg_S", "dg"),
            share_of_dg_cross_sectional=rat("dg_cross", "dg"),
            share_of_dg_scale=rat("dg_scale", "dg"),
            mean_L1_affected_frac=float(np.mean([rw["L1_S_frac"] for rw in rows])),
            mean_dg_S=float(np.mean([rw["dg_S"] for rw in rows])),
            mean_dg_notS=float(np.mean([rw["dg_notS"] for rw in rows])),
            mean_beta=float(np.mean([rw["beta"] for rw in rows])),
            beta_minus1_range=[float(min(rw["beta"] for rw in rows) - 1),
                               float(max(rw["beta"] for rw in rows) - 1)],
            mean_abs_dg_scale=float(np.mean([abs(rw["dg_scale"]) for rw in rows])),
            mean_abs_dg_cross=float(np.mean([abs(rw["dg_cross"]) for rw in rows])),
            spearman_min=float(min(rw["spearman"] for rw in rows)),
            spearman_max=float(max(rw["spearman"] for rw in rows)),
            pearson_min=float(min(rw["pearson"] for rw in rows)),
            L1_frac_mean=float(np.mean([rw["L1_frac"] for rw in rows])),
            L1_frac_max=float(max(rw["L1_frac"] for rw in rows)),
            gross_frac_absmax=float(max(abs(rw["gross_frac"]) for rw in rows)),
            n_only_replay_max=int(max(rw["n_only_replay"] for rw in rows)),
            n_only_live_max=int(max(rw["n_only_live"] for rw in rows)),
            unmeasured_abs_dw_max=float(max(rw["unmeasured_abs_dw"] for rw in rows)),
            g_live_mean=float(np.mean([rw["g_live"] for rw in rows])),
            g_live_std=float(np.std([rw["g_live"] for rw in rows], ddof=1)),
        ),
        per_anchor=rows,
    )

# ------------------------------------------- turnover / cost channel bound (supplementary)
# PREREG §9.8 declares the execution layer out of scope, so the frozen §5 verdict is read off the
# RETURN channel alone.  But "out of scope" should be bounded, not merely asserted: the two books
# would also trade slightly differently.  Per-anchor turnover uses each book's OWN previous anchor
# and the LIVE gross as the common denominator, so d_tau is a clean difference.  Cost rate 3.52
# bps per unit INTENDED turnover, CI [0.32, 6.64] (turnover_cost_reaudit_2026-08-21).  The first
# chain anchor has no replay predecessor, so this channel covers anchors 2..41 (n=40).
COST_RATES = dict(central=3.52, upper_ci=6.64)
COST = {}
for pair in PAIRS:
    rows = RESULTS[pair]["per_anchor"]
    byA = {rw["anchor"]: rw for rw in rows}
    dtau, anch = [], []
    for A in ANCHORS[1:]:
        wr, wl = wpair(pair, A)
        pr, pl = wpair(pair, A - H4)
        vr, _ = vec(wr)
        vl, _ = vec(wl)
        qr, _ = vec(pr)
        ql, _ = vec(pl)
        G = byA[A]["gross_live"]
        dtau.append((float(np.abs(vr - qr).sum()) - float(np.abs(vl - ql).sum())) / G)
        anch.append(A)
    dtau = np.array(dtau)
    day2 = np.array([time.strftime("%Y%m%d", time.gmtime(A)) for A in anch])
    ent = dict(n=len(dtau), mean_dtau=float(dtau.mean()), max_abs_dtau=float(np.abs(dtau).max()),
               rates=COST_RATES, per_rate={})
    for rn, rate in COST_RATES.items():
        dgt = np.array([byA[A]["dg"] for A in anch]) - rate * dtau
        b = boot(dgt, day2, 0)
        mm = float(dgt.mean())
        hh = (b["ci95"][1] - b["ci95"][0]) / 2.0
        um = abs(mm) + hh
        v, nf = verdict_of(um, float(np.abs(dgt).max()), float(np.sqrt((dgt ** 2).mean())))
        ent["per_rate"][rn] = dict(cost_bps_per_unit_turnover=rate, mean_dcost=float(rate * dtau.mean()),
                                   max_abs_dcost=float(rate * np.abs(dtau).max()),
                                   mean_dg_total=mm, ci95=b["ci95"], U_mean=um,
                                   U_max=float(np.abs(dgt).max()), verdict_if_judged_here=v)
    COST[pair] = ent

# ---------------------------------------------------------------- G-M4 (clip x dw interaction)
gm4 = []
if GM0["n_cells_at_clip"] > 0:
    for A in ANCHORS:
        rr = rows_after(A)
        sub = CD[rr[0]:rr[1], :, 0].astype(np.float64)
        h = np.isfinite(sub) & (np.abs(sub) >= CLIP_ABS)
        js = sorted(int(j) for j in np.unique(np.nonzero(h)[1]))
        if not js:
            continue
        ent = dict(anchor=A, iso=time.strftime("%Y-%m-%d %HZ", time.gmtime(A)),
                   names_at_clip=[SYMS[j] for j in js], with_nonzero_dw={})
        for pair in PAIRS:
            wr, wl = wpair(pair, A)
            vr, _ = vec(wr)
            vl, _ = vec(wl)
            dwv = vr - vl
            ent["with_nonzero_dw"][pair] = [SYMS[j] for j in js if dwv[j] != 0.0]
            ent.setdefault("held_in_live", {})[pair] = [SYMS[j] for j in js if vl[j] != 0.0]
        gm4.append(ent)
GM4 = dict(F4_triggered=bool(any(any(v) for g in gm4 for v in g["with_nonzero_dw"].values())),
           per_anchor=gm4)

# ---------------------------------------------------------------- receipt
OUT = dict(
    device="materiality_probe.py", self_sha256=SELF_SHA,
    prereg=dict(path=DOC, sha256=PREREG_SHA),
    utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), env=ENV,
    inputs=dict(
        rolling_npz=dict(path=ROLL_P, sha256=roll_sha_after, **GM3),
        bundle_config=dict(path=CFG_P, sha256=sha(CFG_P), n_symbols_panel=NWD,
                           n_symbols_live=len(cfg["symbols_live"])),
        chain_receipt=dict(path=CHAIN_RECEIPT, sha256=GM1["receipt_sha256"]),
        pairs={k: dict(replay=v["replay"], live=v["live"], note=v["note"]) for k, v in PAIRS.items()},
        caliber="y4P = SUM of +-0.30-clipped 5m simple returns over (A,A+4h], density>=46/48, "
                "NaN->0 in dot product; shadow_loop_v3.py:428-433. NOT the accounting canon "
                "y4s = prod(1+r)-1 over unclipped returns (meta_newprod_v4.npz, pod2, unavailable).",
    ),
    gates=dict(G_M0_clip_inertness=GM0, G_M1_integrity=GM1, G_M3_cache_invariance=GM3, G_M4=GM4,
               G_M5_red_capability=GM5),
    positive_control=POS,
    window=dict(anchors=len(ANCHORS), first=A0, last=A1,
                iso_first=time.strftime("%Y-%m-%d %HZ", time.gmtime(A0)),
                iso_last=time.strftime("%Y-%m-%d %HZ", time.gmtime(A1)),
                utc_day_blocks=RESULTS["deployed"]["estimator"]["block_bootstrap"]["n_days"],
                day_counts=RESULTS["deployed"]["estimator"]["block_bootstrap"]["day_counts"]),
    thresholds=dict(FIT_STRICT_MEAN=FIT_STRICT_MEAN, FIT_STRICT_MAX=FIT_STRICT_MAX,
                    FIT_MEAN=FIT_MEAN, UNFIT_MEAN=UNFIT_MEAN, NOISE_BAR=float(NOISE_BAR),
                    SIGMA_G_REF=float(SIGMA_G_REF), JUDGE_RES_BPS=JUDGE_RES_BPS,
                    EFF_LO=EFF_LO, EFF_HI=EFF_HI),
    primary_pair="deployed",
    turnover_cost_channel=COST,
    results=RESULTS,
)
OP = R + "/receipts/MATERIALITY_dg_%d_%d.json" % (A0, A1)
with open(OP, "w") as f:
    json.dump(OUT, f, indent=1, default=float)
brief = {p: dict(verdict=RESULTS[p]["verdict"]["verdict"], U_mean=RESULTS[p]["verdict"]["U_mean"],
                 U_max=RESULTS[p]["verdict"]["U_max"], mean_dg=RESULTS[p]["verdict"]["mean_dg"],
                 ci95=RESULTS[p]["verdict"]["ci95"], X_fit=RESULTS[p]["verdict"]["X_fit_3x"],
                 affected_n=RESULTS[p]["decomposition"]["affected_n"]) for p in PAIRS}
print(json.dumps(dict(gates=dict(G_M0_PASS=GM0["PASS"], G_M1_PASS=GM1["PASS"],
                                 G_M3_PASS=GM3["PASS"], G_M4_F4_triggered=GM4["F4_triggered"],
                                 G_M5_PASS=GM5["PASS"]),
                      posctrl=[(e["anchor"], {p: (v["dw_all_exactly_zero"], v.get("dg"))
                                              for p, v in e["pairs"].items()}) for e in POS],
                      brief=brief, receipt=OP), indent=1, default=float))
print("RECEIPT_SHA256", sha(OP))
