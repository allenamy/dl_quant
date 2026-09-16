#!/usr/bin/env python3
"""fm_uni01_inverse_pairs.py -- UNI-01 (lead raised to P1): turn the leveraged-inverse-pair mechanism from INFERRED
into MEASURED. pod2, READ-ONLY, CPU only, no GPU, no network, no venue. Computes NO book P&L.

The claim under test (FACT_TABLE_MODEL section 4.2(a), currently INFERRED): SOXL/SOXS (3x long/short semis) and
TQQQ/SQQQ (3x long/short Nasdaq-100) are both training members. Because the book is a CROSS-SECTIONAL RANK, two names
whose returns are near-exact negatives occupy opposite ends of the ranking on every anchor the underlying moves -- BY
CONSTRUCTION, not because of signal. A rank-neutral book then systematically holds one long and the other short, which
is a levered directional bet rather than cross-sectional alpha, and since both legs are 3x they do not net to zero.

Readings, exactly as the lead specified:
  (1) per-anchor score-rank correlation of each pair, across anchors
  (2) realised-return correlation of each pair, across anchors
  (3) how often the pair sits on OPPOSITE legs (sign of the demeaned rank z)
  (4) (1)-(3) restricted to anchors where BOTH are actually members, plus the pair's share of gross on those anchors
  (5) counterfactual: drop the non-crypto names from the member sets and report the rank displacement of the names
      that remain

CONTROLS, because "the pair is correlated" means nothing without a scale:
  - NULL pairs: randomly drawn CRYPTO pairs, same readings, same anchors. This is what "no structural dependence"
    looks like on this estimator.
  - A same-underlying non-inverse reference (QQQ vs SPY, and TQQQ vs QQQ) to separate "same underlying" from
    "inverse of each other".

CALIBER / LAYER DISCIPLINE (FIXPROGRAM section 19): every number here is at the RAW SCORE / RANK-z layer on king OOF
predictions. It is NOT a book-layer effect and must not be quoted as one. Gross share is |z|/sum|z|, the natural rank-z
analogue of a weight, not a traded weight. The king OOF itself carries the forward-availability mask (AUDIT_DATA D3:
predictions exist only where the forward label is finite), which is declared, not corrected here.

Usage: FM_UNI_OUT=<receipt.json> python3 fm_uni01_inverse_pairs.py
"""
import os, sys, json, time, hashlib
import numpy as np
from scipy.stats import rankdata, spearmanr, pearsonr

T0 = time.time()
OUT = os.environ["FM_UNI_OUT"]
KMETA = "/workspace/data/wide_fea_v4_meta.npz"
KPRED = "/workspace/review_scratch/king_v4/SLOW_v4.npy"
CACHE = "/workspace/data/dlnative_5m_wide829_f16_ext.npz"
VENUE = "/workspace/fx_model/devices/venue_class_20260908.json"
EXPECT = {KMETA: "12ea42c4557093f10f954f648db9239f4dd8283ea365ba299f31bd81e7e5ab51",
          VENUE: "fa9196a34ce920287041604af4c9c4b1be37468ac75339ef100e42607c71f2ae"}
PAIRS = [("SOXLUSDT", "SOXSUSDT"), ("TQQQUSDT", "SQQQUSDT")]
REFS = [("QQQUSDT", "SPYUSDT"), ("TQQQUSDT", "QQQUSDT")]
N_NULL = 40
RNG = np.random.RandomState(20260916)


def log(*a):
    print("[%7.1fs]" % (time.time() - T0), *a, flush=True)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""):
            h.update(b)
    return h.hexdigest()


def xz(v):
    """member-internal rank z in [-0.5, 0.5], the convention the legs/book use (pod_dlw_targets_raw.py xz)."""
    ok = np.isfinite(v)
    out = np.full(len(v), np.nan)
    n = int(ok.sum())
    if n >= 10:
        r = rankdata(v[ok])
        out[ok] = (r - (n + 1) / 2) / max(n - 1, 1)
    return out


def series_stats(za, zb, ya, yb, gsa, tag):
    """(1) score-rank correlation, (2) realised-return correlation, (3) opposite-leg rate, (4) gross share."""
    ok = np.isfinite(za) & np.isfinite(zb)
    oky = ok & np.isfinite(ya) & np.isfinite(yb)
    d = {"tag": tag, "n_anchors_both_members": int(ok.sum()), "n_anchors_both_labels": int(oky.sum())}
    if ok.sum() >= 30:
        d["score_rank_spearman"] = float(spearmanr(za[ok], zb[ok]).correlation)
        d["score_rank_pearson"] = float(pearsonr(za[ok], zb[ok])[0])
        opp = (np.sign(za[ok]) * np.sign(zb[ok])) < 0
        d["opposite_leg_rate"] = float(opp.mean())
        d["gross_share_median"] = float(np.nanmedian(gsa[ok]))
        d["gross_share_mean"] = float(np.nanmean(gsa[ok]))
    if oky.sum() >= 30:
        d["realised_return_spearman"] = float(spearmanr(ya[oky], yb[oky]).correlation)
        d["realised_return_pearson"] = float(pearsonr(ya[oky], yb[oky])[0])
    return d


def main():
    rc = {"device": os.path.basename(__file__), "self_sha256": sha(os.path.abspath(__file__)),
          "utc_start": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
          "python": sys.version.split()[0], "numpy": np.__version__,
          "layer": "RAW SCORE / RANK-z on king OOF. NOT a book-layer effect; gross share is |z|/sum|z|, not a traded weight.",
          "declared_limitation": "king OOF exists only where the forward label is finite (AUDIT_DATA D3); that mask is "
                                 "declared, not corrected. No P&L is computed.",
          "inputs": {}}
    for p, want in EXPECT.items():
        got = sha(p)
        rc["inputs"][p] = got
        assert got == want, ("INPUT SHA MISMATCH", p, got, want)
    rc["inputs"][KPRED] = sha(KPRED)
    log("input shas asserted")

    M = np.load(KMETA, allow_pickle=True)
    E_ts = M["E_ts"].astype(np.int64)
    MS = M["members"]
    Y4 = M["y4"]
    P = np.load(KPRED)
    syms = [str(s) for s in np.load(CACHE, allow_pickle=True)["symbols"]]
    CLS = json.load(open(VENUE))
    NW = len(syms)
    assert P.shape[0] == len(E_ts) and P.shape[1] == NW, (P.shape, len(E_ts), NW)
    idx = {s: i for i, s in enumerate(syms)}
    yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
    is_2026 = yrs == 2026
    rc["axis"] = {"anchors": int(len(E_ts)), "anchors_2026": int(is_2026.sum()), "NW": NW,
                  "first": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(E_ts[0]))),
                  "last": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(E_ts[-1])))}

    def is_crypto(s):
        c = CLS.get(s)
        return True if c is None else (c.get("underlyingType") in ("COIN", "INDEX"))
    noncrypto = sorted([s for s in syms if not is_crypto(s)])
    rc["noncrypto_on_axis"] = len(noncrypto)
    log("axis %d anchors, %d non-crypto symbols on axis" % (len(E_ts), len(noncrypto)))

    # ---- per-anchor rank z on the OOF scores, restricted to that anchor's members ----
    Z = np.full((len(E_ts), NW), np.nan)
    GROSS = np.zeros(len(E_ts))
    for i in range(len(E_ts)):
        m = MS[i]
        z = xz(P[i, m])
        Z[i, m] = z
        GROSS[i] = np.nansum(np.abs(z))
    log("rank z built")

    want = set(s for p in PAIRS + REFS for s in p)
    rc["symbol_membership_2026"] = {}
    for s in sorted(want):
        j = idx.get(s)
        rc["symbol_membership_2026"][s] = {"on_axis": j is not None,
                                           "member_anchors_2026": int(np.isfinite(Z[is_2026, j]).sum()) if j is not None else 0,
                                           "class": (CLS.get(s) or {}).get("underlyingType")}

    def one(a, b, tag, mask):
        ja, jb = idx.get(a), idx.get(b)
        if ja is None or jb is None:
            return {"tag": tag, "skipped": "symbol absent from the axis"}
        za, zb = Z[mask, ja], Z[mask, jb]
        ya, yb = Y4[mask, ja], Y4[mask, jb]
        gs = (np.abs(za) + np.abs(zb)) / np.where(GROSS[mask] > 0, GROSS[mask], np.nan)
        return series_stats(za, zb, ya, yb, gs, tag)

    rc["R1_R4_pairs_2026"] = [one(a, b, "%s|%s" % (a, b), is_2026) for a, b in PAIRS]
    rc["R1_R4_pairs_all_years"] = [one(a, b, "%s|%s" % (a, b), np.ones(len(E_ts), bool)) for a, b in PAIRS]
    rc["reference_same_underlying_not_inverse"] = [one(a, b, "%s|%s" % (a, b), is_2026) for a, b in REFS]

    # ---- CONTROL: random crypto pairs on the same anchors ----
    cry = [s for s in syms if is_crypto(s)]
    nulls = []
    for _ in range(N_NULL):
        a, b = RNG.choice(len(cry), 2, replace=False)
        r = one(cry[a], cry[b], "null", is_2026)
        if "score_rank_spearman" in r:
            nulls.append(r)
    def q(k):
        v = [x[k] for x in nulls if k in x]
        return {"n": len(v), "median": float(np.median(v)), "p5": float(np.percentile(v, 5)),
                "p95": float(np.percentile(v, 95)), "min": float(np.min(v)), "max": float(np.max(v))} if v else None
    rc["NULL_random_crypto_pairs_2026"] = {"n_pairs": len(nulls),
                                           "score_rank_spearman": q("score_rank_spearman"),
                                           "realised_return_spearman": q("realised_return_spearman"),
                                           "opposite_leg_rate": q("opposite_leg_rate"),
                                           "gross_share_median": q("gross_share_median"),
                                           "note": "this is what NO structural dependence looks like on this estimator"}
    log("pairs + nulls done")

    # ---- (5) counterfactual: drop non-crypto from the member sets, re-rank the survivors ----
    ncset = set(idx[s] for s in noncrypto if s in idx)
    disp_rank, disp_z, per_anchor = [], [], []
    a2026 = np.where(is_2026)[0]
    for i in a2026:
        m = MS[i]
        keep = np.array([c for c in m if c not in ncset], dtype=np.int64)
        if len(keep) < 50 or len(keep) == len(m):
            continue
        z_all = xz(P[i, m])
        z_cf = xz(P[i, keep])
        pos_all = {int(c): k for k, c in enumerate(m)}
        ra = rankdata(np.where(np.isfinite(P[i, m]), P[i, m], np.nan))
        rb = rankdata(np.where(np.isfinite(P[i, keep]), P[i, keep], np.nan))
        # compare the SAME surviving names under the two rankings, in normalised rank units
        na, nb = len(m), len(keep)
        for k, c in enumerate(keep):
            pa = (ra[pos_all[int(c)]] - 1) / max(na - 1, 1)
            pb = (rb[k] - 1) / max(nb - 1, 1)
            disp_rank.append(abs(pa - pb))
        za_ = z_all[[pos_all[int(c)] for c in keep]]
        disp_z.append(np.nanmax(np.abs(za_ - z_cf)))
        per_anchor.append({"removed": int(len(m) - len(keep)), "kept": int(len(keep))})
    dr = np.array(disp_rank) if disp_rank else np.array([np.nan])
    rc["R5_counterfactual_drop_noncrypto"] = {
        "anchors_affected": len(per_anchor),
        "mean_names_removed_per_anchor": float(np.mean([p["removed"] for p in per_anchor])) if per_anchor else None,
        "normalised_rank_displacement": {"median": float(np.nanmedian(dr)), "p95": float(np.nanpercentile(dr, 95)),
                                         "max": float(np.nanmax(dr)), "n_cells": int(len(dr))},
        "max_abs_z_shift_per_anchor_median": float(np.nanmedian(disp_z)) if disp_z else None,
        "LAYER": "raw z / rank layer ONLY -- must not be quoted as a book-layer effect (FIXPROGRAM section 19)"}
    log("counterfactual done")

    rc["utc_end"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    rc["wall_s"] = round(time.time() - T0, 1)
    os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
    json.dump(rc, open(OUT, "w"), indent=1, default=float)
    for r in rc["R1_R4_pairs_2026"]:
        print("PAIR %-22s n=%4s score_rho=%-9s ret_rho=%-9s opp_leg=%-7s gross=%s"
              % (r.get("tag"), r.get("n_anchors_both_members"),
                 round(r.get("score_rank_spearman", float("nan")), 4), round(r.get("realised_return_spearman", float("nan")), 4),
                 round(r.get("opposite_leg_rate", float("nan")), 4), round(r.get("gross_share_median", float("nan")), 5)), flush=True)
    n = rc["NULL_random_crypto_pairs_2026"]
    print("NULL crypto pairs: score_rho median %s [p5 %s, p95 %s] | ret_rho median %s | opp_leg median %s"
          % (n["score_rank_spearman"]["median"], n["score_rank_spearman"]["p5"], n["score_rank_spearman"]["p95"],
             n["realised_return_spearman"]["median"], n["opposite_leg_rate"]["median"]), flush=True)
    print("DONE wall=%.1fs -> %s" % (rc["wall_s"], OUT), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
