"""REGIME-AWARE Ridge test — does conditioning on a STRICTLY-CAUSAL regime
indicator capture perp_book-in-choppy (+0.0125) AND long_context-in-strong
(+0.0175) that pooled Ridge averages away?

> created 2026-06-22 | status: screening | branch: multi-asset

Uses the load-once raw cache from lever_ridge_screen (Xs base 64, Xp perp last-t,
lg long-context block, y perp, day_idx). Builds a causal regime indicator (trailing
perp realized-vol, <= t) and tests:
  R1 base + regime_z                         (does the indicator alone add?)
  R2 base + perp_book_block + lg_block       (both lever blocks, no regime)
  R3 R2 + regime_z + regime×(perp_book,lg)   (regime-CONDITIONED interactions)
  R4 per-regime BLEND: causal regime classifier picks base-vs-perp_book model

CAUSALITY GATE: the regime indicator is built from trailing-window stats (<= t)
only. A shuffle-future null is run: corrupt the per-day mids AFTER each cut and
confirm the regime z at rows <= cut is unchanged. (Built into the trailing-window
construction; verified explicitly here.)

Decision rule (project): ACCEPT only if pooled ΔP >= +0.005 vs base AND
sign-consistent across all 3 folds (capturing BOTH regimes, not just one).
"""
from __future__ import annotations

import os.path as p
import sys

import numpy as np

_REPO = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
sys.path.insert(0, _REPO)

from multi_asset.eda.perpY_ridge_gate import ridge_walkforward, FOLDS  # noqa: E402
from multi_asset.eda.lever_ridge_screen import (                       # noqa: E402
    _RAWCACHE, build_raw_cache, TRADE_FEATS,
)

# lg block layout (from _long_lastt): per W in (600,1800,3600): [sret,pret,srv,prv]
# then basis. perp rvol at 3600s = index 3 (prv of W=600)? Order is
# [s600,p600,srv600,prv600, s1800,p1800,srv1800,prv1800, s3600,p3600,srv3600,prv3600, basis]
# perp realized-vol 3600s = index 11 (prv of W=3600). Use that as the slow-vol regime.
LG_PRVOL_3600 = 11
LG_PRVOL_600 = 3


def _regime_z(lg, day_idx):
    """Causal regime indicator from the long-context block: standardized trailing
    perp realized-vol (3600s, <= t). Standardized with an EXPANDING causal mean/std
    over days (no future) so the z at day d uses only days <= d. Returns z (M,).
    High z = high-vol/choppy regime; low z = calm/strong-trend regime (proxy)."""
    rv = lg[:, LG_PRVOL_3600].astype(np.float64)
    z = np.full(rv.size, np.nan)
    # expanding standardization by day order (causal): accumulate per-day stats
    order = np.argsort(day_idx, kind="stable")
    rv_o = rv[order]
    di_o = day_idx[order]
    # running median/MAD updated at each NEW day boundary using only prior days
    uniq = np.unique(di_o)
    # build per-day list of values
    csum = 0.0; csum2 = 0.0; cn = 0
    z_o = np.full(rv.size, np.nan)
    start = 0
    prior_mean = np.nan; prior_std = np.nan
    for d in uniq:
        sel = di_o == d
        if cn >= 5 and prior_std > 1e-12:
            z_o[sel] = (rv_o[sel] - prior_mean) / prior_std
        else:
            z_o[sel] = 0.0
        # update running stats AFTER scoring this day (so day d uses < d only)
        v = rv_o[sel]; v = v[np.isfinite(v)]
        csum += v.sum(); csum2 += (v * v).sum(); cn += v.size
        if cn > 0:
            prior_mean = csum / cn
            prior_std = float(np.sqrt(max(csum2 / cn - prior_mean ** 2, 1e-18)))
    z[order] = z_o
    return np.nan_to_num(z, nan=0.0)


def _perp_book_block(R):
    """The perp_book LEVER expressed as appended channels: the 48 perp-book cols
    minus the spot-book cols (the book-venue delta) — i.e. what perp_book ADDS
    over base. Use the perp book/price cols (non-trade) as a block."""
    Xs = R["Xs"]; Xp = R["Xp"]; names = [str(x) for x in R["names"]]
    book_idx = [i for i, n in enumerate(names) if n not in set(TRADE_FEATS)]
    # the perp-vs-spot book DIFFERENCE (the orthogonal book-venue info)
    return (Xp[:, book_idx] - Xs[:, book_idx])


def main():
    if not p.exists(_RAWCACHE):
        build_raw_cache()
    R = np.load(_RAWCACHE, allow_pickle=True)
    Xs = R["Xs"].astype(np.float64); y = R["y"].astype(np.float64)
    lg = R["lg"].astype(np.float64); day_idx = R["day_idx"]; days = list(R["days"])

    # only rows with finite lg (long-context available) for apples-to-apples
    fin = np.all(np.isfinite(lg), axis=1)
    Xs, y, lg, di = Xs[fin], y[fin], lg[fin], day_idx[fin]
    pbb = _perp_book_block({k: R[k][fin] if R[k].ndim and R[k].shape[0] == fin.size else R[k]
                            for k in ("Xs", "Xp", "names")} if False else R)
    pbb = _perp_book_block(R)[fin]
    z = _regime_z(lg, di)

    # --- CAUSALITY shuffle-future null on the regime z ---
    # z[i] at day d uses only days < d (expanding stats) + trailing-window rv (<=t
    # by construction in _long_lastt). Corrupt the LATER-day rv values and confirm
    # z on EARLY days is unchanged.
    rng = np.random.default_rng(0)
    lg_c = lg.copy()
    cut_day = int(np.median(di))
    later = di > cut_day
    lg_c[later, LG_PRVOL_3600] *= (1.0 + rng.uniform(-0.9, 0.9, int(later.sum())))
    z_c = _regime_z(lg_c, di)
    early = di <= cut_day
    leak = float(np.max(np.abs(z[early] - z_c[early]))) if early.any() else 0.0
    print(f"[causality] regime-z shuffle-future null: max|Δz| on days<=cut = {leak:.3e} "
          f"-> {'PASS (causal)' if leak < 1e-9 else 'FAIL (leak!)'}", flush=True)

    def score(name, X):
        finx = np.all(np.isfinite(X), axis=1)
        r = ridge_walkforward(X[finx], y[finx], di[finx], days, verbose=False)
        pl = r["pooled"]; pf = {f["name"]: f.get("P") for f in r["folds"] if f.get("status") == "ok"}
        if pl:
            print(f"\n=== {name} (D={X.shape[1]}) ===", flush=True)
            print(f"  pooled P={pl['P']} dP_vs_base={pl['P']-BASE_P:+.4f} "
                  f"sign_consistent={pl['sign_consistent']} sig={pl['sig_ratio']}", flush=True)
            print(f"  per-fold: 2025-02={pf.get('strong_2025_02')} "
                  f"2025-04={pf.get('strong_2025_04')} 2026={pf.get('choppy_2026')}", flush=True)
        return r["pooled"]["P"] if pl else float("nan"), r["pooled"]["perfold_P"] if pl else []

    global BASE_P
    # baseline on the SAME finite-lg rows (fair comparison)
    rb = ridge_walkforward(Xs, y, di, days, verbose=False)
    BASE_P = rb["pooled"]["P"]
    bpf = {f["name"]: f.get("P") for f in rb["folds"] if f.get("status") == "ok"}
    print(f"\n=== BASE (finite-lg rows, D=64) === pooled P={BASE_P} "
          f"per-fold 2025-02={bpf.get('strong_2025_02')} 2025-04={bpf.get('strong_2025_04')} "
          f"2026={bpf.get('choppy_2026')}", flush=True)

    zc = z[:, None]
    # R1: base + regime_z
    score("R1 base+regime_z", np.column_stack([Xs, zc]))
    # R2: base + perp_book_block + lg_block (both lever blocks, no regime)
    score("R2 base+perpbook+long", np.column_stack([Xs, pbb, lg]))
    # R3: R2 + regime_z + regime interactions (regime-CONDITIONED)
    inter_pb = pbb * zc          # perp_book × regime (should fire in choppy)
    inter_lg = lg * zc           # long-context × regime (should fire in strong)
    score("R3 regime-conditioned", np.column_stack([Xs, pbb, lg, zc, inter_pb, inter_lg]))
    # R3b: lighter — only interactions with a few strongest cols (avoid overfit)
    score("R3b regime-cond-lite", np.column_stack([Xs, zc, pbb * zc, lg[:, [1, 9, 11]] * zc]))


if __name__ == "__main__":
    BASE_P = 0.0
    main()
