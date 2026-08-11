"""Apply the funding settlement-interval dimension fix to a DL panel's channels.

BACKGROUND: `FUND_EMA` stored the EMA of the PER-SETTLEMENT-PERIOD funding rate while 4h- and
8h-settled coins coexist. A 4h coin with identical ANNUALISED carry shows half the per-period rate.
The engine rank-centres funding cross-sectionally, and rank-centring removes INDIVIDUAL scale but
NOT a GROUP-level location shift -> the 4h cohort sits systematically on one side.
Fix: rate * (8 / interval_h_OF_THAT_ROW), applied BEFORE the EMA (per-row, because ~29 coins
migrated 8h<->4h mid-history and a single post-EMA factor is wrong across the migration window).

SOURCE OF TRUTH: 0C's `exports/eda/funding_ema_normfix.npz::FN`, already on this panel's exact
(ts, symbols) grid. 0B's independent implementation agrees with it to corr 0.999999999998 /
mean|diff| 3.8e-12, so rather than maintain two implementations that can drift, this consumes FN
and re-verifies the agreement (--verify) instead.

TWO CHANNELS carry the artifact at IDENTICAL strength (0C measured -0.3837 vs -0.3837; a rank
transform passes a group shift through unchanged, neither amplifying nor diluting it):
    ch  0  funding_ema   the raw factor
    ch 28  xsr_fund      centered pct-rank OF funding_ema (build_wide_dl.py L80-91)
xsr_fund is derived from funding_ema in the same script, so fixing the source should fix both --
but that is an assumption about the build graph, so `assert_funding_dim.py` checks it.

SCOPE (lead + 0C ruling 2026-07-25): fix the FACTOR, do NOT retrain the DL. YR residual targets
were residualised against the un-normalised funding column -- a recorded caveat, no look-ahead or
leakage, deferred to the next retrain cycle. The engine reads CH and never YR.

Usage:
    python multi_asset/data/apply_funding_fix.py --panel <in.npz> --out <out.npz>
    python multi_asset/data/apply_funding_fix.py --verify        # 0B recompute vs 0C FN
"""
from __future__ import annotations
import argparse, os
import numpy as np
import pandas as pd

REPO = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
MA = REPO + "/multi_asset"
WIDE = REPO + "/data/wide"
NORMFIX = MA + "/exports/eda/funding_ema_normfix.npz"
FUND_CH, XSR_CH = "funding_ema", "xsr_fund"


def recompute(ts, symbols, verbose=False):
    """0B's independent implementation (kept only as the cross-check for --verify).

    Deliberate difference from 0C's reference: a non-finite/non-positive interval is filled with the
    8h default rather than dropping that settlement, so production never silently loses a funding
    observation. Such rows are vanishingly rare -- the two agree to ~4e-12.
    """
    ts = np.asarray(ts, np.int64)
    F = np.full((len(ts), len(symbols)), np.nan)
    for j, s in enumerate(symbols):
        p = f"{WIDE}/{s}_funding.csv"
        if not os.path.exists(p):
            continue
        d = pd.read_csv(p)
        if "funding_interval_h" not in d or len(d) < 3:
            continue
        d = d.sort_values("fundingTime_ms")
        iv = pd.to_numeric(d["funding_interval_h"], errors="coerce").to_numpy()
        rate = pd.to_numeric(d["fundingRate"], errors="coerce").to_numpy()
        iv = np.where(np.isfinite(iv) & (iv > 0), iv, 8.0)
        span = max(2, int(round(24.0 / max(float(np.median(iv)), 1.0))))
        ema = pd.Series(rate * (8.0 / iv)).ewm(span=span, adjust=False).mean().to_numpy()
        fts = d["fundingTime_ms"].to_numpy().astype(np.int64)
        idx = np.searchsorted(fts, ts, side="right") - 1
        ok = idx >= 0
        F[ok, j] = ema[idx[ok]]
    return F


def load_corrected(ts, symbols, verbose=True):
    """0C's FN, realigned onto (ts, symbols); falls back to recompute if unavailable."""
    if not os.path.exists(NORMFIX):
        if verbose:
            print("[fundfix] funding_ema_normfix.npz absent -> recomputing locally", flush=True)
        return recompute(ts, symbols)
    z = np.load(NORMFIX, allow_pickle=True)
    zts = z["ts"].astype(np.int64)
    zsym = [str(s) for s in z["symbols"]]
    FN = z["FN"].astype(np.float64)
    if np.array_equal(zts, np.asarray(ts, np.int64)) and zsym == list(symbols):
        if verbose:
            print(f"[fundfix] using 0C FN directly (grids identical, {FN.shape})", flush=True)
        return FN
    # realign (the live panel is a superset/tail-extension of the frozen grid)
    out = np.full((len(ts), len(symbols)), np.nan)
    tpos = {int(t): i for i, t in enumerate(zts)}
    rows = np.array([tpos.get(int(t), -1) for t in ts])
    cols = np.array([zsym.index(s) if s in zsym else -1 for s in symbols])
    rok, cok = rows >= 0, cols >= 0
    if rok.any() and cok.any():
        out[np.ix_(rok, cok)] = FN[np.ix_(rows[rok], cols[cok])]
    if verbose:
        print(f"[fundfix] realigned 0C FN onto panel grid: {rok.sum()}/{len(ts)} rows, "
              f"{cok.sum()}/{len(symbols)} symbols matched", flush=True)
    # anything the frozen FN cannot cover (live tail) is filled from the local recompute
    miss = ~np.isfinite(out) & rok[:, None] & cok[None, :]
    if miss.any():
        loc = recompute(ts, symbols)
        out = np.where(np.isfinite(out), out, loc)
        if verbose:
            print(f"[fundfix] filled {int(miss.sum())} cells (live tail) from local recompute",
                  flush=True)
    else:
        out = np.where(np.isfinite(out), out, recompute(ts, symbols))
    return out


def _xsr(A):
    """centered pct-rank over all finite coins per row — identical to build_wide_dl.py L80-87."""
    R = np.full_like(A, np.nan, np.float32)
    for t in range(A.shape[0]):
        v = np.isfinite(A[t])
        if v.sum() >= 8:
            r = np.argsort(np.argsort(A[t, v])).astype(np.float32)
            R[t, v] = r / (v.sum() - 1) - 0.5
    return R


def apply_to_panel(in_path, out_path, verbose=True):
    """Rewrite ONLY funding_ema and xsr_fund; every other array is carried over unchanged."""
    W = np.load(in_path, allow_pickle=True)
    ch = [str(c) for c in W["ch_names"]]
    for c in (FUND_CH, XSR_CH):
        if c not in ch:
            raise KeyError(f"{c} not in panel {in_path}")
    ts = W["ts"].astype(np.int64)
    symbols = [str(s) for s in W["symbols"]]
    FE = load_corrected(ts, symbols, verbose=verbose)

    CH = W["CH"].copy()
    i_f, i_x = ch.index(FUND_CH), ch.index(XSR_CH)
    old = CH[:, :, i_f].copy()
    CH[:, :, i_f] = np.nan_to_num(FE, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
    CH[:, :, i_x] = np.nan_to_num(_xsr(FE), nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)

    out = {k: W[k] for k in W.files}
    out["CH"] = CH
    with open(out_path, "wb") as f:
        np.savez(f, **out)
    if verbose:
        m = (old != 0) & (CH[:, :, i_f] != 0)
        print(f"[fundfix] {os.path.basename(in_path)} -> {os.path.basename(out_path)}", flush=True)
        print(f"[fundfix] replaced ch{i_f} {FUND_CH} + ch{i_x} {XSR_CH}; "
              f"{len(W.files)} arrays carried over", flush=True)
        print(f"[fundfix] corr(old,new) on shared non-zero cells = "
              f"{np.corrcoef(old[m], CH[:, :, i_f][m])[0,1]:.6f}", flush=True)
    return out_path


def verify(verbose=True):
    W = np.load(MA + "/exports/wide_dl_full.npz", allow_pickle=True)
    ts = W["ts"].astype(np.int64); syms = [str(s) for s in W["symbols"]]
    mine = recompute(ts, syms)
    z = np.load(NORMFIX, allow_pickle=True)
    other = z["FN"].astype(np.float64)
    both = np.isfinite(mine) & np.isfinite(other)
    c = float(np.corrcoef(mine[both], other[both])[0, 1])
    md = float(np.abs(mine[both] - other[both]).mean())
    only_mine = int((np.isfinite(mine) & ~np.isfinite(other)).sum())
    only_0c = int((~np.isfinite(mine) & np.isfinite(other)).sum())
    print(f"[verify] 0B recompute vs 0C FN: corr={c:.12f} mean|diff|={md:.3e} "
          f"shared={int(both.sum()):,} only-0B={only_mine} only-0C={only_0c}", flush=True)
    print(f"[verify] {'AGREE (interchangeable)' if c > 0.999999 and md < 1e-8 else 'DISAGREE'}",
          flush=True)
    return c, md


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default=MA + "/exports/wide_dl_full.npz")
    ap.add_argument("--out", default=MA + "/exports/wide_dl_full_fundfix.npz")
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    if a.verify:
        verify()
    else:
        apply_to_panel(a.panel, a.out)
