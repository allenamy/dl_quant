"""TURNOVER-MATCHED NULL INSTRUMENT  (round 3, 2026-09-11, session b9646a9e)

WHY THIS EXISTS
---------------
Rounds 1-2 judged sleeves against a PER-ANCHOR PERMUTATION placebo: at every anchor the
feature's values were shuffled across names.  That destroys the feature's temporal
persistence as well as its cross-sectional information, so the null book re-sorts itself
every anchor and pays 2.6-7.7x the real arm's trading cost.  Its negative net is therefore
mostly a CHURN-COST artifact.  Three independent round-2 families found this.  Any sleeve
verdict that leaned on it is biased IN FAVOUR OF THE REAL ARM by an unknown amount.

WHAT A NULL MUST PRESERVE
-------------------------
The null has to differ from the real arm in ONE thing only: the correspondence between the
feature and the forward outcome.  Everything that prices the book must be held fixed:
  (1) the per-anchor set of names that carry a value  (=> same rank base, same tradeable set)
  (2) the per-anchor cross-sectional distribution of values (=> same weight profile, same gross)
  (3) each name's temporal smoothness (=> same rank persistence => SAME TURNOVER => same cost)

THE FAMILIES
------------
R  RELABEL-BIJECTION.  At each anchor, hold the available-name set fixed and re-attach the
   anchor's own values to those names through a bijection induced by ONE fixed random key
   kappa (identical at every anchor).  (1) and (2) hold EXACTLY (it is a permutation of the
   row restricted to the available set).  (3) holds because name c's null series is, at
   every anchor where the available set is unchanged, one single other name's real series.

RO RELABEL-ORBIT.  Same idea, more locally stable under listings/delistings: a fixed
   single-cycle permutation p on the 829 columns; name c receives the value of the first
   name in the orbit p(c), p^2(c), ... that is available at that anchor.  (1) holds EXACTLY;
   (2) holds up to donor re-use; (3) holds and is MORE stable than R because a listing
   change perturbs only the names whose own donor changed, not every name's partner.

T  PER-NAME ROTATION (the phase-randomised / block-bootstrap family).  Each name's feature
   series is rotated circularly ALONG ITS OWN observed timeline by a fixed fraction of its
   own history.  (1) holds EXACTLY (a name has values at exactly the anchors it really did);
   the name's own value multiset holds EXACTLY; its autocorrelation holds exactly except at
   one seam.  (2) holds only approximately (the cross-section is de-synchronised), which is
   why R and T are reported side by side: they fail differently, so agreement is evidence.

P  PER-ANCHOR PERMUTATION -- the LEGACY, DEFECTIVE null.  Kept as a positive control so the
   size of the round-1/2 bias can be read off directly in the same table.

C  COST-MATCHING is not a matrix transform; it is applied at read time by the judge, which
   reports for every arm BOTH the gross column (pnl_ex/gross_total, cost-free) and the net
   column (g = net_ex/gross_total), plus a turnover-rescaled net
        g_cm = g + (cost_ex/gross_total) * (1 - turnover_real/turnover_null)
   so a null that still churns more than the real arm is priced as if it churned the same.

WHERE THE NULL IS APPLIED
-------------------------
To the RAW feature, BEFORE rank / lag / EMA / orthogonalisation.  The arm's own downstream
pipeline is then re-run bit-for-bit on the nulled raw feature, so the null stays orthogonal
to the fund leg exactly as the real arm is, and is lagged/smoothed exactly as the real arm is.
Applying a null to the already-masked, already-orthogonalised matrix is WRONG: for
f_amihud_24h a fixed column permutation of the masked matrix retains only 45.8% of the
base-mask cells (measured), i.e. it silently halves the book's breadth.

RANK CONVENTION: scipy.stats.rankdata (AVERAGE ranks), the device's own xz().  NEVER
np.argsort(np.argsort(.)) -- f_fund_ema_v1 is tied on 9031 of 10039 rows and ordinal ranking
manufactures order inside tie blocks (caliber pin, 2026-09-11).
"""
import numpy as np
from scipy.stats import rankdata

SEED_ROOT = 20260911


# ---------------------------------------------------------------- null families
def null_relabel(X, seed):
    """Family R: availability-exact bijective relabelling under one fixed key."""
    rng = np.random.default_rng([SEED_ROOT, 31337, int(seed)])
    kappa = rng.permutation(X.shape[1]).astype(np.int64)
    O = np.full(X.shape, np.nan)
    for i in range(X.shape[0]):
        A = np.flatnonzero(np.isfinite(X[i]))
        if len(A) < 2:
            O[i] = X[i]
            continue
        Bp = A[np.argsort(kappa[A], kind="stable")]   # same set, fixed-key order
        O[i, A] = X[i, Bp]
    return O


def null_relabel_orbit(X, seed):
    """Family RO: availability-exact orbit relabelling under one fixed single-cycle map."""
    rng = np.random.default_rng([SEED_ROOT, 51515, int(seed)])
    m = X.shape[1]
    cyc = rng.permutation(m).astype(np.int64)          # cyc[0]->cyc[1]->...->cyc[0]
    nxt = np.empty(m, np.int64)
    nxt[cyc] = np.roll(cyc, -1)
    O = np.full(X.shape, np.nan)
    for i in range(X.shape[0]):
        ok = np.isfinite(X[i])
        if ok.sum() < 2:
            O[i] = X[i]
            continue
        d = nxt.copy()                                  # donor after 1 step
        # walk the orbit until every column's donor is available (at most m steps; the
        # available set is non-empty so this always terminates)
        bad = ~ok[d]
        steps = 0
        while bad.any() and steps < m:
            d[bad] = nxt[d[bad]]
            bad = ~ok[d]
            steps += 1
        O[i, ok] = X[i, d[ok]]
    return O


def null_rotate(X, frac):
    """Family T: per-name circular rotation along the name's OWN observed timeline."""
    O = np.full(X.shape, np.nan)
    for c in range(X.shape[1]):
        idx = np.flatnonzero(np.isfinite(X[:, c]))
        k = len(idx)
        if k < 24:
            O[idx, c] = X[idx, c]
            continue
        s = int(round(float(frac) * k)) % k
        if s < 12:                       # never let the rotation land inside the 4h horizon
            s = max(12, k // 3)
        O[idx, c] = X[idx[(np.arange(k) - s) % k], c]
    return O


def null_permute_anchor(X, seed):
    """Legacy DEFECTIVE null: independent shuffle of each anchor's available values."""
    rng = np.random.default_rng([SEED_ROOT, 90909, int(seed)])
    O = np.full(X.shape, np.nan)
    for i in range(X.shape[0]):
        ok = np.isfinite(X[i])
        if ok.sum() < 2:
            O[i] = X[i]
            continue
        v = X[i, ok].copy()
        rng.shuffle(v)
        O[i, ok] = v
    return O


NULLS = {
    "R1": lambda X: null_relabel(X, 1),
    "R2": lambda X: null_relabel(X, 2),
    "R3": lambda X: null_relabel(X, 3),
    "O1": lambda X: null_relabel_orbit(X, 1),
    "O2": lambda X: null_relabel_orbit(X, 2),
    "T1": lambda X: null_rotate(X, 0.37),
    "T2": lambda X: null_rotate(X, 0.53),
    "T3": lambda X: null_rotate(X, 0.71),
    "P1": lambda X: null_permute_anchor(X, 1),
}
FAMILY_OF = {"R1": "R", "R2": "R", "R3": "R", "O1": "RO", "O2": "RO",
             "T1": "T", "T2": "T", "T3": "T", "P1": "P_legacy_defective"}


# ---------------------------------------------------------------- diagnostics
def availability_receipt(X, Xn):
    """A null is only admissible if it did not change WHICH names carry a value."""
    a, b = np.isfinite(X), np.isfinite(Xn)
    return {"avail_identical": bool(np.array_equal(a, b)),
            "cells_real": int(a.sum()),
            "cells_null_kept_of_real": float((a & b).sum() / max(a.sum(), 1)),
            "row_multiset_identical_frac": _multiset_frac(X, Xn)}


def _multiset_frac(X, Xn):
    same = 0
    tot = 0
    for i in range(0, X.shape[0], 37):            # 1-in-37 subsample; this is a diagnostic
        a = np.sort(X[i][np.isfinite(X[i])])
        b = np.sort(Xn[i][np.isfinite(Xn[i])])
        tot += 1
        if len(a) == len(b) and np.allclose(a, b, rtol=0, atol=0, equal_nan=True):
            same += 1
    return float(same / max(tot, 1))


# ---------------------------------------------------------------- pipeline pieces
def make_rz(base_mask):
    def rz(M):
        out = np.full(M.shape, np.nan)
        for i in range(M.shape[0]):
            v = M[i]
            ok = np.isfinite(v)
            n = int(ok.sum())
            if n >= 10:
                out[i, ok] = (rankdata(v[ok]) - 1.0) / max(n - 1, 1) - 0.5
        return out
    return rz


def make_orth(ZF):
    def orth(Z):
        R = np.full(Z.shape, np.nan)
        for i in range(Z.shape[0]):
            ok = np.isfinite(Z[i]) & np.isfinite(ZF[i])
            if ok.sum() < 10:
                continue
            x = ZF[i][ok]
            y = Z[i][ok]
            vx = float((x * x).sum())
            b = float((x * y).sum() / vx) if vx > 1e-12 else 0.0
            R[i][ok] = y - b * x
        return R
    return orth


def lag1(Z, base_mask):
    L = np.full_like(Z, np.nan)
    L[1:] = Z[:-1]
    return np.where(base_mask, L, np.nan)


def ema(M, hl):
    """Causal EMA over anchors of the RAW feature, NaN-safe, per-name state."""
    a = 1.0 - 0.5 ** (1.0 / hl)
    O = np.full(M.shape, np.nan)
    s = np.full(M.shape[1], np.nan)
    for i in range(M.shape[0]):
        v = M[i]
        ok = np.isfinite(v)
        s = np.where(np.isfinite(s) & ok, s + a * (v - s), np.where(ok, v, s))
        O[i] = s
    return O
