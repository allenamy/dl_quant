#!/usr/bin/env python3
"""materiality_probe_v2.py — PREREG_parity_materiality_2026-09-13 + AMENDMENT 1.  Read-only, CPU.

SUPERSEDES devices/materiality_probe.py (sha 371c3b7b...), which pinned the pre-amendment PREREG
sha and therefore no longer runs against the amended document by design.  Its receipt
receipts/MATERIALITY_dg_1788624000_1789200000.json is kept, labelled SUPERSEDED.

Four corrections from the independent reviewer (0158f5d1), all accepted (AMENDMENT 1):

 A1.1 NORMALISATION.  The executor normalises EACH book by ITS OWN gross:
        live/external_book.py:489  gn = float(ext.get("gross_in") or ext["gross_norm"])
                                   return [w_i / gn ...]
        scheduler/anchor_loop.py:1636/1763 -> signal/legs.py:340-342 only multiply by gross.
      so  dg(A) = 1e4 * sum_i ( w_r,i/G_r - w_l,i/G_l ) * r_i        NOT  sum(w_r-w_l)/G_l.
      G_X = the file's own sum|w| (== its gross_norm field, asserted).  The executor's real
      denominator is gross_in (IN-UNIVERSE sum, external_book.py:363/390) which needs the venue
      universe of that anchor and CANNOT be reproduced offline -- declared, not silently swapped.
 A1.3 UNCERTAINTY.  A percentile interval is not centred on the mean, so |m|+halfwidth is not a
      bound on it.  U = max(|ci95_lo|, |ci95_hi|).
 A1.4 INTEGRITY.  Per-file SHA256 of every book file read, each checked against the producer's own
      .json.sha256 sidecar, plus the symbol axis sha and a sha of each anchor's r-vector bytes.
      L infinity is kept ONLY as a parity statistic, never as the integrity proof (G-M6 shows why).
 A1.6 SCOPE.  The deliverable is a BASELINE cached-price residual measurement for THIS window.
      It is NOT an instrument-fitness certificate: baseline error e(theta0) does not bound the
      paired error e(theta1)-e(theta0).  The "conservative upper bound for paired designs" claim
      is WITHDRAWN.  No candidate promotion, no net-P&L, no risk reading is licensed.

Caliber (E-0904-F), unchanged: r_i(A) = SUM over the 48 rows in (A, A+4h] of
rolling.npz['data'][:,i,0] ("ret5", 5m simple returns HARD-CLIPPED to +-0.30 by
shadow_loop_v3.py:150/253), density gate >=46 finite else NaN, NaN->0.  This is verbatim the
producer's settlement formula shadow_loop_v3.py:428-433.  It is NOT the accounting canon
y4s = prod(1+r)-1 over UNCLIPPED returns (meta_newprod_v4.npz, pod2, out of reach here).
It is a PRICE return: no funding/carry, no cost, no execution clock, no fills.

Writes ONLY into parity_replay_2026-09-12/receipts/.  Never writes to ~/wide_shadow or
~/dl_quant_live; no network; no API; no process control.

Launch:  python3 -B materiality_probe_v2.py "<comma-separated env whitelist>"
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

WS = "/Users/haosiyu/wide_shadow"
R = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/parity_replay_2026-09-12"
RH = R + "/replay_home"
DOC = "/Users/haosiyu/Desktop/quant_research/docs/PREREG_parity_materiality_2026-09-13.md"
PREREG_SHA = "bb5263bf62c75e65856a6a7b9ec6d1dfa04c576e7495c0e9a03a0834a4bb9e66"   # post-AMENDMENT 1
PREREG_SHA_PRE_AMEND = "eb9f5e412f0c333642e2676771b41a1e6a5623542418ee00688fa30d53090b02"
SUPERSEDED = dict(device="devices/materiality_probe.py",
                  device_sha256="371c3b7bddbd66925a26a95ab89359d5e46a7bf01c8a491b67a3bc551fc05cf7",
                  receipt="receipts/MATERIALITY_dg_1788624000_1789200000.json",
                  receipt_sha256="e421eb13494a9ed96fd66352d73d714dea5b6536ac833019330b48cd8ef92af9")
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

# ---------------------------------------------------------------- frozen constants
NB, RNG_BASE = 2000, 20260905
JUDGE_RES_BPS = 0.23
EFF_LO, EFF_HI = 0.02, 0.60
SCALE_FAR = EFF_LO / 3.0          # 0.0066667  "far below the 0.02-0.6 scale"
SCALE_COMPARABLE = EFF_HI / 3.0   # 0.2        "comparable to" / above
STRICT_REF = EFF_LO / 10.0        # 0.002      reported for the record (AMENDMENT 1 A1.3)
SIGMA_G_REF = 0.6341957 * np.sqrt(2190.0) / 1.29122344
NOISE_BAR = 0.1 * SIGMA_G_REF
CLIP_ABS = float(np.float16(0.30))
DENSITY_MIN, STEP, H4 = 46, 300, 14400

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

# ---------------------------------------------------------------- inputs
CFG_P, ROLL_P = WS + "/shadow_bundle/config.json", WS + "/state/rolling.npz"
roll_sha_before, roll_stat_before = sha(ROLL_P), statsig(ROLL_P)
cfg = json.load(open(CFG_P))
SYMS = list(cfg["symbols_panel"])
NWD = len(SYMS)
assert NWD == 829, NWD
SYM_IDX = {s: j for j, s in enumerate(SYMS)}
CFG_SHA = sha(CFG_P)
AXIS_SHA = hashlib.sha256("\n".join(SYMS).encode()).hexdigest()

Z = np.load(ROLL_P)
CTS = np.asarray(Z["ts"], np.int64)
CD = Z["data"]
assert CD.shape == (len(CTS), NWD, 7), CD.shape
ROW_OF = {int(t): i for i, t in enumerate(CTS)}
roll_sha_after, roll_stat_after = sha(ROLL_P), statsig(ROLL_P)
GM3 = dict(sha_before=roll_sha_before, sha_after=roll_sha_after, stat_before=roll_stat_before,
           stat_after=roll_stat_after,
           PASS=bool(roll_sha_before == roll_sha_after and roll_stat_before == roll_stat_after),
           cache_first_ts=int(CTS[0]), cache_last_ts=int(CTS[-1]), cache_rows=int(len(CTS)))
assert GM3["PASS"], GM3

# ---------------------------------------------------------------- G-M1' per-file SHA integrity
FILESHA = {}
SIDECAR = {"checked": 0, "missing": [], "mismatch": []}


def book(p):
    """Load a book file, record its byte sha, and verify it against the producer's sidecar."""
    rp = os.path.realpath(p)
    if rp not in FILESHA:
        FILESHA[rp] = sha(rp)
        sc = rp + ".sha256"
        if os.path.exists(sc):
            want = open(sc).read().split()[0].strip()
            SIDECAR["checked"] += 1
            if want != FILESHA[rp]:
                SIDECAR["mismatch"].append(dict(path=rp, sidecar=want, actual=FILESHA[rp]))
        else:
            SIDECAR["missing"].append(rp)
    d = json.load(open(rp))
    w = {k: float(v) for k, v in d["weights"].items()}
    G = float(sum(abs(v) for v in w.values()))
    gn = d.get("gross_norm", d.get("gross"))
    return w, G, (None if gn is None else float(gn))


def wpair(pair, A):
    P = PAIRS[pair]
    return book(P["replay"] % A), book(P["live"] % A)


def vec(w):
    v = np.zeros(NWD, np.float64)
    miss = [k for k in w if k not in SYM_IDX]
    for k, x in w.items():
        if k in SYM_IDX:
            v[SYM_IDX[k]] = x
    return v, miss


def rows_after(A):
    pi, ai = ROW_OF.get(A), ROW_OF.get(A + H4)
    if pi is None or ai is None:
        return None
    assert ai - pi == H4 // STEP, (A, pi, ai)
    return (pi + 1, ai + 1)


RVEC = {}


def retvec(A):
    if A in RVEC:
        return RVEC[A]
    rr = rows_after(A)
    if rr is None:
        RVEC[A] = (None, None, None)
        return RVEC[A]
    lo, hi = rr
    seg = CD[lo:hi, :, 0].astype(np.float64)
    fin = np.isfinite(seg)
    nfin = fin.sum(0)
    y4P = np.where(fin, seg, 0.0).sum(0)
    y4C = np.expm1(np.log1p(np.where(fin, seg, 0.0)).sum(0))
    bad = nfin < DENSITY_MIN
    y4P[bad] = np.nan
    y4C[bad] = np.nan
    # A1.4: bind the return slice itself, not just the files
    meta = dict(rows=(int(CTS[lo]), int(CTS[hi - 1])), n_rows=int(hi - lo),
                n_finite_names=int((~bad).sum()),
                r_sha256=hashlib.sha256(np.nan_to_num(y4P, nan=0.0).tobytes()).hexdigest(),
                n_ts_contiguous=bool(np.all(np.diff(CTS[lo:hi]) == STEP)))
    RVEC[A] = (y4P, y4C, meta)
    return RVEC[A]


# ---------------------------------------------------------------- the metric (A1.1)
def dg_of(vr, Gr, vl, Gl, r):
    """1e4 * sum_i ( w_r,i/G_r - w_l,i/G_l ) * r_i   — each book by its OWN gross."""
    return 1e4 * float((vr / Gr - vl / Gl) @ r)


def linf(wr, wl):
    keys = set(wr) | set(wl)
    return max(abs(wr.get(k, 0.0) - wl.get(k, 0.0)) for k in keys) if keys else 0.0


# ---------------------------------------------------------------- bootstrap
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
    lo, hi = float(np.percentile(ms, 2.5)), float(np.percentile(ms, 97.5))
    return dict(ci95=[lo, hi], U_endpoint=max(abs(lo), abs(hi)),   # A1.3
                se=float(ms.std(ddof=1)), n_days=nd,
                day_counts={k: int(len(dd[k])) for k in keys})


def boot_iid(d, off=0):
    n = len(d)
    r = np.stack([np.random.default_rng([RNG_BASE, off + k]).integers(0, n, n) for k in range(NB)])
    ms = d[r].mean(1)
    lo, hi = float(np.percentile(ms, 2.5)), float(np.percentile(ms, 97.5))
    return dict(ci95=[lo, hi], U_endpoint=max(abs(lo), abs(hi)), se=float(ms.std(ddof=1)), n=n)


def scale_word(U):
    """AMENDMENT 1 A1.6 — a SCALE STATEMENT about this window, not a fitness certificate."""
    if U <= SCALE_FAR:
        return "BASELINE-RESIDUAL-FAR-BELOW-0.02-0.6-SCALE"
    if U <= SCALE_COMPARABLE:
        return "BASELINE-RESIDUAL-COMPARABLE-TO-0.02-0.6-SCALE"
    return "BASELINE-RESIDUAL-ABOVE-0.02-0.6-SCALE"


DAY = np.array([time.strftime("%Y%m%d", time.gmtime(A)) for A in ANCHORS])

# ---------------------------------------------------------------- positive control (F2)
POS = []
for A in POSCTRL:
    e = dict(anchor=A, iso=time.strftime("%Y-%m-%d %HZ", time.gmtime(A)), pairs={})
    y4P, _, meta = retvec(A)
    for pair in PAIRS:
        (wr, Gr, gnr), (wl, Gl, gnl) = wpair(pair, A)
        keys = sorted(set(wr) | set(wl))
        dws = [wr.get(k, 0.0) - wl.get(k, 0.0) for k in keys]
        ent = dict(n_keys=len(keys), dw_all_exactly_zero=bool(all(d == 0.0 for d in dws)),
                   dw_Linf=float(max(abs(d) for d in dws)) if dws else 0.0,
                   gross_replay=Gr, gross_live=Gl, gross_exactly_equal=bool(Gr == Gl))
        if y4P is None:
            ent.update(dg=None, returns_available=False)
        else:
            vr, _ = vec(wr)
            vl, _ = vec(wl)
            val = dg_of(vr, Gr, vl, Gl, np.nan_to_num(y4P, nan=0.0))
            ent.update(dg=val, returns_available=True, dg_is_exactly_zero=bool(val == 0.0),
                       ret_window=meta["rows"])
        e["pairs"][pair] = ent
    POS.append(e)
bad = [(e["anchor"], p, v) for e in POS for p, v in e["pairs"].items()
       if (not v["dw_all_exactly_zero"]) or (v.get("returns_available") and not v["dg_is_exactly_zero"])]
assert not bad, ("F2 POSITIVE CONTROL FAILED — pipeline is wrong, main-window numbers withheld", bad)

# ---------------------------------------------------------------- G-M5 (A1.5) invariance + red
GM5 = {"cases": []}
for A in (ANCHORS[0], ANCHORS[len(ANCHORS) // 2], ANCHORS[-1]):
    y4P, _, _ = retvec(A)
    r = np.nan_to_num(y4P, nan=0.0)
    (wr, Gr, _), (wl, Gl, _) = wpair("deployed", A)
    vr, _ = vec(wr)
    vl, _ = vec(wl)
    base = dg_of(vr, Gr, vl, Gl, r)
    # (a) INVARIANCE: scaling the whole replay book must be a no-op under the correct normalisation
    c = 1.0001
    got_a = dg_of(c * vr, c * Gr, vl, Gl, r)
    # (b) RED: single held name +delta, closed form recomputed from scalars
    held = np.nonzero(vr)[0]
    j = int(held[int(np.argmax(np.abs(r[held])))])
    delta = 1e-4
    pert = vr.copy()
    pert[j] += delta
    Grp = Gr + (abs(vr[j] + delta) - abs(vr[j]))
    got_b = dg_of(pert, Grp, vl, Gl, r)
    exp_b = 1e4 * ((float(vr @ r) + delta * float(r[j])) / Grp - float(vl @ r) / Gl)
    GM5["cases"].append(dict(
        anchor=A, iso=time.strftime("%Y-%m-%d %HZ", time.gmtime(A)), dg_base=base,
        invariance=dict(c=c, dg_scaled=got_a, abs_change=abs(got_a - base),
                        ok=bool(abs(got_a - base) <= 1e-12 * max(1.0, abs(base)))),
        red=dict(name=SYMS[j], r_i=float(r[j]), delta=delta, measured=got_b, closed_form=exp_b,
                 rel=abs(got_b - exp_b) / max(abs(exp_b), 1e-300),
                 moved=bool(got_b != base))))
GM5["PASS"] = bool(all(c["invariance"]["ok"] and c["red"]["moved"] and c["red"]["rel"] <= 1e-12
                       for c in GM5["cases"]))
assert GM5["PASS"], ("G-M5 FAILED (invariance under scaling / red response to a known kick)", GM5)

# ---------------------------------------------------------------- G-M6 (A1.4) L-infinity blindness
# Reviewer 0158f5d1's counterexample, reproduced as a standing gate: mutating a NON-MAXIMAL
# residual name in memory leaves Linf bit-identical while dg moves.  Proves Linf cannot serve as
# the integrity proof.  No file is modified; the mutation lives in a numpy copy.
GM6 = {"anchor": 1788782400, "mutated_name": "DOODUSDT"}
_A = GM6["anchor"]
y4P, _, _ = retvec(_A)
_r = np.nan_to_num(y4P, nan=0.0)
(wr, Gr, _), (wl, Gl, _) = wpair("deployed", _A)
_vr, _ = vec(wr)
_vl, _ = vec(wl)
_L0 = float(np.abs(_vr - _vl).max())
_j = SYM_IDX[GM6["mutated_name"]]
# "set dw to 0.9 x Linf" does not pin the SIGN, so run both and record both.  The reviewer's
# published value +0.12333468 is the MINUS branch; reconciled here rather than left as a mismatch.
GM6.update(Linf_before=_L0, dw_original=float(_vr[_j] - _vl[_j]),
           dg_old_formula_before=1e4 * float((_vr - _vl) @ _r) / Gl,
           dg_new_formula_before=dg_of(_vr, Gr, _vl, Gl, _r), branches={})
for _sgn, _lab in ((+1.0, "plus_0p9_Linf"), (-1.0, "minus_0p9_Linf")):
    _v2 = _vr.copy()
    _v2[_j] = _vl[_j] + _sgn * 0.9 * _L0            # NON-maximal residual => Linf untouched
    _L1 = float(np.abs(_v2 - _vl).max())
    GM6["branches"][_lab] = dict(
        Linf_after=_L1, Linf_bit_identical=bool(_L0 == _L1),
        dg_old_formula_after=1e4 * float((_v2 - _vl) @ _r) / Gl,
        dg_new_formula_after=dg_of(_v2, float(np.abs(_v2).sum()), _vl, Gl, _r))
GM6["reviewer_published_old_formula_after"] = 0.12333468
GM6["reviewer_branch"] = "minus_0p9_Linf"
GM6["reviewer_value_reproduced"] = bool(
    abs(GM6["branches"]["minus_0p9_Linf"]["dg_old_formula_after"] - 0.12333468) < 5e-9)
GM6["dg_moved"] = bool(all(b["dg_new_formula_after"] != GM6["dg_new_formula_before"]
                           for b in GM6["branches"].values()))
GM6["PASS"] = bool(all(b["Linf_bit_identical"] for b in GM6["branches"].values())
                   and GM6["dg_moved"] and GM6["reviewer_value_reproduced"])
GM6["lesson"] = ("Linf is bit-identical while dg moves => Linf is a parity statistic, not an "
                 "integrity proof; integrity is the per-file SHA256 set in gates.G_M1_integrity.")
assert GM6["PASS"], ("G-M6 FAILED to reproduce the Linf-blindness counterexample", GM6)

# ---------------------------------------------------------------- G-M0 clip inertness
lo0, hi0 = ROW_OF[A0] + 1, ROW_OF[A1 + H4] + 1
segall = CD[lo0:hi0, :, 0].astype(np.float64)
hitm = np.isfinite(segall) & (np.abs(segall) >= CLIP_ABS)
hit_j = sorted(int(j) for j in np.unique(np.nonzero(hitm)[1]))
GM0 = dict(window_rows=(int(CTS[lo0]), int(CTS[hi0 - 1])), n_rows=int(hi0 - lo0),
           n_cells_scanned=int(np.isfinite(segall).sum()), clip_abs=CLIP_ABS,
           n_cells_at_clip=int(hitm.sum()), n_names_at_clip=len(hit_j),
           names_at_clip=[SYMS[j] for j in hit_j],
           global_min=float(np.nanmin(segall)), global_max=float(np.nanmax(segall)),
           PASS=bool(hitm.sum() == 0))

# ---------------------------------------------------------------- main loop
GROSSFIELD = {}
RESULTS = {}
for pair in PAIRS:
    rows, track = [], {}
    for A in ANCHORS:
        (wr, Gr, gnr), (wl, Gl, gnl) = wpair(pair, A)
        vr, miss_r = vec(wr)
        vl, miss_l = vec(wl)
        # The denominator is ALWAYS the sum we compute from the file's own weights (that is what
        # external_book.py:363 does).  The stored field is only cross-checked:
        #   target_live  writes gross_norm = float(sum(abs(v)))          -> must match exactly
        #   target_combo writes gross      = round(sum(abs(combo)), 6)   -> matches to the rounding
        # (and its weights are themselves round(.,8)), so its tolerance is 5e-7 + 8dp slack.
        _tol = 1e-15 * max(1.0, Gl) if pair == "deployed" else 1e-6
        assert gnl is None or abs(gnl - Gl) <= _tol, (pair, A, gnl, Gl)
        GROSSFIELD.setdefault(pair, []).append(abs(gnl - Gl) if gnl is not None else 0.0)
        y4P, y4C, meta = retvec(A)
        rP, rC = np.nan_to_num(y4P, nan=0.0), np.nan_to_num(y4C, nan=0.0)
        dw = vr - vl
        dg = dg_of(vr, Gr, vl, Gl, rP)
        g_live = 1e4 * float(vl @ rP) / Gl
        g_repl = 1e4 * float(vr @ rP) / Gr
        # normalised books: this is what the executor actually turns into notionals
        ur, ul = vr / Gr, vl / Gl
        du = ur - ul
        beta = float((ur @ ul) / (ul @ ul))
        e = du - (beta - 1.0) * ul
        nanmask = ~np.isfinite(y4P)
        held = (vl != 0) | (vr != 0)
        sup = np.nonzero(held)[0]
        ra = np.argsort(np.argsort(ur[sup])).astype(float)
        rb = np.argsort(np.argsort(ul[sup])).astype(float)
        for j in np.nonzero(du)[0]:
            track[int(j)] = max(track.get(int(j), 0.0), abs(float(dw[j])))
        rows.append(dict(anchor=A, iso=time.strftime("%Y-%m-%d %HZ", time.gmtime(A)), dg=dg,
                         dg_old_formula=1e4 * float(dw @ rP) / Gl,
                         dg_compounded=dg_of(vr, Gr, vl, Gl, rC),
                         g_live=g_live, g_replay=g_repl, gross_live=Gl, gross_replay=Gr,
                         gross_frac=(Gr - Gl) / Gl, Linf_raw=float(np.abs(dw).max()),
                         L1_norm=float(np.abs(du).sum()), Linf_norm=float(np.abs(du).max()),
                         n_du_nonzero=int((du != 0).sum()),
                         n_only_replay=len(set(wr) - set(wl)), n_only_live=len(set(wl) - set(wr)),
                         n_names_replay=len(wr), n_names_live=len(wl),
                         miss_from_axis=(miss_r, miss_l), beta=beta,
                         dg_scale=(beta - 1.0) * g_live, dg_cross=1e4 * float(e @ rP),
                         spearman=float(np.corrcoef(ra, rb)[0, 1]),
                         pearson=float(np.corrcoef(ur[sup], ul[sup])[0, 1]),
                         ret_window=meta["rows"], r_sha256=meta["r_sha256"],
                         n_ts_contiguous=meta["n_ts_contiguous"], n_finite_ret=meta["n_finite_names"],
                         unmeasured_abs_du=float(np.abs(du[nanmask & held]).sum()),
                         _du=du, _r=rP))
    S = sorted([j for j, v in track.items() if v > 1e-6])
    SN = [SYMS[j] for j in S]
    msk = np.zeros(NWD, bool)
    msk[S] = True
    for rw in rows:
        du, r = rw.pop("_du"), rw.pop("_r")
        rw["dg_S"] = 1e4 * float((du * msk) @ r)
        rw["dg_notS"] = 1e4 * float((du * ~msk) @ r)
        rw["L1_S_frac"] = float(np.abs(du[msk]).sum() / max(np.abs(du).sum(), 1e-300))

    DG = np.array([rw["dg"] for rw in rows])
    DGO = np.array([rw["dg_old_formula"] for rw in rows])
    DGC = np.array([rw["dg_compounded"] for rw in rows])
    B, B9, BI, BC = boot(DG, DAY, 0), boot(DG, DAY, 9 * NB), boot_iid(DG, 0), boot(DGC, DAY, 0)
    BO = boot(DGO, DAY, 0)
    m = float(DG.mean())
    U = B["U_endpoint"]
    U_max = float(np.abs(DG).max())
    S_rms = float(np.sqrt((DG ** 2).mean()))
    worst = max(rows, key=lambda rw: abs(rw["dg"]))

    def rat(num, den):
        pa = [abs(rw[num]) / max(abs(rw[den]), 1e-300) for rw in rows]
        return dict(ratio_of_sums=float(sum(abs(rw[num]) for rw in rows) /
                                        max(sum(abs(rw[den]) for rw in rows), 1e-300)),
                    median_per_anchor=float(np.median(pa)),
                    mean_per_anchor_UNSTABLE=float(np.mean(pa)))

    RESULTS[pair] = dict(
        note=PAIRS[pair]["note"],
        reading=dict(scale_statement=scale_word(U), mean_dg=m, ci95=B["ci95"],
                     U_endpoint=U, U_max_sample=U_max, S_rms=S_rms,
                     ratio_to_judge_resolution=U / JUDGE_RES_BPS,
                     strict_ref_0p002_met=bool(U <= STRICT_REF),
                     noise_clause_violated=bool(S_rms > NOISE_BAR),
                     worst_anchor=dict(anchor=worst["anchor"], iso=worst["iso"], dg=worst["dg"],
                                       Linf_raw=worst["Linf_raw"], g_live=worst["g_live"]),
                     n_anchors_abs_dg_gt_EFF_LO=int((np.abs(DG) > EFF_LO).sum()),
                     n_anchors_abs_dg_gt_SCALE_FAR=int((np.abs(DG) > SCALE_FAR).sum())),
        superseded_old_formula=dict(mean=float(DGO.mean()), ci95=BO["ci95"],
                                    U_endpoint=BO["U_endpoint"],
                                    U_max_sample=float(np.abs(DGO).max()),
                                    strict_ref_0p002_met=bool(BO["U_endpoint"] <= STRICT_REF),
                                    correction_mean=float((DG - DGO).mean()),
                                    correction_max_abs=float(np.abs(DG - DGO).max())),
        estimator=dict(block_bootstrap=B, block_bootstrap_k9=B9, iid_bootstrap=BI,
                       naive_se=float(DG.std(ddof=1) / np.sqrt(len(DG))),
                       compounded_caliber=BC, mean_dg_compounded=float(DGC.mean()),
                       caliber_spread_mean_abs=float(np.abs(DG - DGC).mean()),
                       caliber_spread_max_abs=float(np.abs(DG - DGC).max())),
        decomposition=dict(
            affected_names=SN, affected_n=len(SN), ever_nonzero_du_n=len(track),
            share_of_dg_from_affected=rat("dg_S", "dg"),
            share_of_dg_cross_sectional=rat("dg_cross", "dg"),
            share_of_dg_scale=rat("dg_scale", "dg"),
            mean_L1_affected_frac=float(np.mean([rw["L1_S_frac"] for rw in rows])),
            mean_beta=float(np.mean([rw["beta"] for rw in rows])),
            beta_minus1_range=[float(min(rw["beta"] for rw in rows) - 1),
                               float(max(rw["beta"] for rw in rows) - 1)],
            mean_abs_dg_scale=float(np.mean([abs(rw["dg_scale"]) for rw in rows])),
            mean_abs_dg_cross=float(np.mean([abs(rw["dg_cross"]) for rw in rows])),
            spearman_min=float(min(rw["spearman"] for rw in rows)),
            spearman_max=float(max(rw["spearman"] for rw in rows)),
            pearson_min=float(min(rw["pearson"] for rw in rows)),
            L1_norm_mean=float(np.mean([rw["L1_norm"] for rw in rows])),
            L1_norm_max=float(max(rw["L1_norm"] for rw in rows)),
            gross_frac_absmax=float(max(abs(rw["gross_frac"]) for rw in rows)),
            n_only_replay_max=int(max(rw["n_only_replay"] for rw in rows)),
            n_only_live_max=int(max(rw["n_only_live"] for rw in rows)),
            unmeasured_abs_du_max=float(max(rw["unmeasured_abs_du"] for rw in rows)),
            all_windows_48_contiguous=bool(all(rw["n_ts_contiguous"] for rw in rows)),
            g_live_mean=float(np.mean([rw["g_live"] for rw in rows])),
            g_live_std=float(np.std([rw["g_live"] for rw in rows], ddof=1)),
            gross_field_vs_computed_max=float(max(GROSSFIELD.get(pair, [0.0])))),
        per_anchor=rows)

# ---------------------------------------------------------------- turnover SENSITIVITY (A1.7)
COST_RATES = dict(central=3.52, upper_ci=6.64)
COST = {}
for pair in PAIRS:
    byA = {rw["anchor"]: rw for rw in RESULTS[pair]["per_anchor"]}
    dtau, anch = [], []
    for A in ANCHORS[1:]:
        (wr, Gr, _), (wl, Gl, _) = wpair(pair, A)
        (pr, Gpr, _), (pl, Gpl, _) = wpair(pair, A - H4)
        vr, _ = vec(wr)
        vl, _ = vec(wl)
        qr, _ = vec(pr)
        ql, _ = vec(pl)
        dtau.append(float(np.abs(vr / Gr - qr / Gpr).sum()) - float(np.abs(vl / Gl - ql / Gpl).sum()))
        anch.append(A)
    dtau = np.array(dtau)
    day2 = np.array([time.strftime("%Y%m%d", time.gmtime(A)) for A in anch])
    ent = dict(n=len(dtau), mean_dtau=float(dtau.mean()), max_abs_dtau=float(np.abs(dtau).max()),
               label="SUPPLEMENTARY SENSITIVITY ONLY (AMENDMENT 1 A1.7) — two fixed linear rates, "
                     "40 anchors, no venue universe / fill clock / impact non-linearity / funding; "
                     "NOT an execution-cost error bound", per_rate={})
    for rn, rate in COST_RATES.items():
        dgt = np.array([byA[A]["dg"] for A in anch]) - rate * dtau
        b = boot(dgt, day2, 0)
        ent["per_rate"][rn] = dict(cost_bps_per_unit_turnover=rate,
                                   mean_dcost=float(rate * dtau.mean()),
                                   mean_dg_total=float(dgt.mean()), ci95=b["ci95"],
                                   U_endpoint=b["U_endpoint"],
                                   scale_statement=scale_word(b["U_endpoint"]))
    COST[pair] = ent

# ---------------------------------------------------------------- G-M4 clip x dw
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
                   names_at_clip=[SYMS[j] for j in js], with_nonzero_dw={}, held_in_live={})
        for pair in PAIRS:
            (wr, Gr, _), (wl, Gl, _) = wpair(pair, A)
            vr, _ = vec(wr)
            vl, _ = vec(wl)
            d_ = vr / Gr - vl / Gl
            ent["with_nonzero_dw"][pair] = [SYMS[j] for j in js if d_[j] != 0.0]
            ent["held_in_live"][pair] = [SYMS[j] for j in js if vl[j] != 0.0]
        gm4.append(ent)
GM4 = dict(F4_triggered=bool(any(any(v) for g in gm4 for v in g["with_nonzero_dw"].values())),
           per_anchor=gm4)

# ---------------------------------------------------------------- G-M1' assembly
CH = json.load(open(CHAIN_RECEIPT))
REC = {int(a["anchor"]): a for a in CH["anchors"]}
parity = {}
for pair, P in PAIRS.items():
    worst_rel = 0.0
    for A in ANCHORS:
        (wr, _, _), (wl, _, _) = wpair(pair, A)
        got = linf(wr, wl)
        exp = float(REC[A]["combo"][P["receipt_key"]])
        worst_rel = max(worst_rel, abs(got - exp) / max(exp, 1e-300))
    parity[pair] = dict(worst_rel_vs_frozen_receipt=worst_rel, agrees=bool(worst_rel <= 1e-12))
GM1 = dict(
    kind="per-file SHA256 (AMENDMENT 1 A1.4)", n_files=len(FILESHA),
    sidecar_checked=SIDECAR["checked"], sidecar_missing=SIDECAR["missing"],
    sidecar_mismatch=SIDECAR["mismatch"], file_sha256=FILESHA,
    symbol_axis_sha256=AXIS_SHA, bundle_config_sha256=CFG_SHA,
    r_vector_sha256={str(A): retvec(A)[2]["r_sha256"] for A in ANCHORS},
    linf_parity_statistic_NOT_integrity=parity,
    # Only target_live/ and target_live_combo/ carry producer-written .json.sha256 sidecars;
    # target_combo/ carries none anywhere (0 of 107 live, 0 of 44 replay).  So the PRIMARY
    # ("deployed") pair has an INDEPENDENT witness on both sides, while the SECONDARY ("execcal")
    # pair's only binding is the sha recorded in THIS receipt: it pins future reruns but has no
    # external witness.  Stated, not silently equated.  The gate requires zero MISMATCHES.
    witness=dict(
        deployed="both sides have producer-written sidecars; all verified",
        execcal="NO sidecars exist for target_combo; bound only by the sha256 recorded here"),
    n_files_without_witness=len(SIDECAR["missing"]),
    PASS=bool(not SIDECAR["mismatch"]))
assert GM1["PASS"], ("G-M1' RED: a book file disagrees with its producer-written .json.sha256 "
                     "sidecar", GM1["sidecar_mismatch"])

# ---------------------------------------------------------------- receipt
OUT = dict(
    device="materiality_probe_v2.py", self_sha256=SELF_SHA,
    supersedes=SUPERSEDED,
    prereg=dict(path=DOC, sha256=PREREG_SHA, sha256_pre_amendment=PREREG_SHA_PRE_AMEND,
                amendment="AMENDMENT 1 (normalisation / CI endpoints / per-file integrity / scope demotion)"),
    utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), env=ENV,
    metric="dg = 1e4 * sum_i ( w_r,i/G_r - w_l,i/G_l ) * r_i   (each book by its OWN gross)",
    metric_source="live/external_book.py:363,390,489 + scheduler/anchor_loop.py:1636,1763 + signal/legs.py:340-342",
    executor_tree_head="918559f903b9c73b5a263605de5ce8e967266dfb",
    declared_gaps=["G is the file's own sum|w| (== gross_norm); the executor's real denominator is "
                   "gross_in = the IN-UNIVERSE sum, which needs that anchor's venue universe and is "
                   "NOT reproducible offline",
                   "r is a cached PRICE return: no funding/carry, no cost, no execution clock, no fills",
                   "no venue filtering, positions, caps, withheld names, sizing, halts or NAV"],
    inputs=dict(rolling_npz=dict(path=ROLL_P, sha256=roll_sha_after, **GM3),
                bundle_config=dict(path=CFG_P, sha256=CFG_SHA, n_symbols_panel=NWD),
                chain_receipt=dict(path=CHAIN_RECEIPT, sha256=sha(CHAIN_RECEIPT)),
                pairs={k: dict(replay=v["replay"], live=v["live"], note=v["note"])
                       for k, v in PAIRS.items()},
                caliber="y4P = SUM of +-0.30-clipped 5m simple returns over (A,A+4h], density>=46/48, "
                        "NaN->0; shadow_loop_v3.py:428-433. NOT the accounting canon "
                        "y4s = prod(1+r)-1 over unclipped returns (meta_newprod_v4.npz, pod2)."),
    gates=dict(G_M0_clip_inertness=GM0, G_M1_integrity=GM1, G_M3_cache_invariance=GM3, G_M4=GM4,
               G_M5_invariance_and_red=GM5, G_M6_linf_blindness=GM6),
    positive_control=POS,
    window=dict(anchors=len(ANCHORS), first=A0, last=A1,
                iso_first=time.strftime("%Y-%m-%d %HZ", time.gmtime(A0)),
                iso_last=time.strftime("%Y-%m-%d %HZ", time.gmtime(A1)),
                utc_day_blocks=RESULTS["deployed"]["estimator"]["block_bootstrap"]["n_days"],
                day_counts=RESULTS["deployed"]["estimator"]["block_bootstrap"]["day_counts"]),
    scale_thresholds=dict(SCALE_FAR=SCALE_FAR, SCALE_COMPARABLE=SCALE_COMPARABLE,
                          STRICT_REF=STRICT_REF, NOISE_BAR=float(NOISE_BAR),
                          SIGMA_G_REF=float(SIGMA_G_REF), JUDGE_RES_BPS=JUDGE_RES_BPS,
                          EFF_LO=EFF_LO, EFF_HI=EFF_HI),
    does_not_license=["candidate promotion (baseline error e(t0) does not bound paired error "
                      "e(t1)-e(t0); the 'conservative upper bound for paired designs' claim is WITHDRAWN)",
                      "any net-P&L statement (price only: no funding, no cost, no execution clock)",
                      "any risk reading (halt frequency, tail loss, maxDD, single-anchor action)",
                      "extrapolation to other windows or regimes (41 anchors, 8 UTC day blocks, one regime)",
                      "retiring the historical G-P2 FAIL, or the 829x40d G2-A contract"],
    primary_pair="deployed", turnover_cost_sensitivity=COST, results=RESULTS)
OP = R + "/receipts/MATERIALITY_v2_dg_%d_%d.json" % (A0, A1)
with open(OP, "w") as f:
    json.dump(OUT, f, indent=1, default=float)
brief = {p: dict(scale_statement=RESULTS[p]["reading"]["scale_statement"],
                 mean_dg=RESULTS[p]["reading"]["mean_dg"], ci95=RESULTS[p]["reading"]["ci95"],
                 U_endpoint=RESULTS[p]["reading"]["U_endpoint"],
                 U_max_sample=RESULTS[p]["reading"]["U_max_sample"],
                 strict_ref_met=RESULTS[p]["reading"]["strict_ref_0p002_met"],
                 old_formula=RESULTS[p]["superseded_old_formula"]) for p in PAIRS}
print(json.dumps(dict(gates=dict(G_M0_PASS=GM0["PASS"], G_M1_PASS=GM1["PASS"],
                                 G_M1_sidecars=GM1["sidecar_checked"], G_M3_PASS=GM3["PASS"],
                                 G_M4_F4=GM4["F4_triggered"], G_M5_PASS=GM5["PASS"],
                                 G_M6_PASS=GM6["PASS"]),
                      posctrl=[(e["anchor"], {p: (v["dw_all_exactly_zero"], v.get("dg"))
                                              for p, v in e["pairs"].items()}) for e in POS],
                      brief=brief, receipt=OP), indent=1, default=float))
print("RECEIPT_SHA256", sha(OP))
