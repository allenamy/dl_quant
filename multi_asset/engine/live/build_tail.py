"""Live shadow — incremental panel tail builder (windowed splice) + overlap validation.

> **创建:** 2026-07-19 JST | **Session:** fable multi-asset-v2 (0B live shadow) | **状态:** v1 | **作废条件:** 面板 builder 口径 / 通道定义变更

The historical per-coin CSVs were cleaned up post-build, so we can't full-rebuild. Instead:
build a fresh ROLLING WINDOW from the CDN (klines + funding/premium), assemble the wide_panel-level
raw arrays (OHLCV/VWAP/FUND_EMA/DVOL30) for the 140 FROZEN symbols on the hourly grid, and SPLICE the
genuinely-new rows onto the frozen `wide_panel_full.npz`; then run the EXISTING `build_wide_dl.build`
over the extended panel (deterministic — recomputes CH / MEMBER110 / YR / CL with correct absolute
row indexing) -> `wide_dl_live.npz`.

The window deliberately OVERLAPS the frozen panel by >=`overlap_days` so we can BYTE-VALIDATE that a
fresh CDN pull reproduces the frozen caliber (`validate_overlap`) before trusting the new tail —
this is the lead's "重叠窗校验". Raw-input parity (CLOSE/QVOL/FUND_EMA) in the overlap is the load-
bearing check: build_wide_dl is deterministic, so matching raw inputs guarantee matching channels.

funding_ema for the OPEN (current) month: the CDN fundingRate archive is monthly-only, so we fill the
open-month channel with the premium-index proxy (funding_derive; ~0.8 corr — good enough as 1/32 model
INPUT channels, NOT good enough to TRADE) and flag those anchors; the funding LEG degrade + month-end
reconcile lives in the signal loop (see RUNBOOK / lead ruling c1|c2).
"""
from __future__ import annotations

import datetime as dt
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/engine/live")
from datasource import get_source          # noqa: E402
import funding_derive as fd                # noqa: E402

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
PANEL_FULL = MA + "/exports/wide_panel_full.npz"       # frozen raw-input panel (has OHLCV/FUND_EMA/DVOL30)
DL_FULL = MA + "/exports/wide_dl_full.npz"
HOUR_MS = 3_600_000


def _ms(d: dt.date) -> int:
    return int(dt.datetime(d.year, d.month, d.day, tzinfo=dt.timezone.utc).timestamp() * 1000)


def build_window(source, symbols, d0: dt.date, d1: dt.date, open_month=None):
    """Assemble wide_panel-level raw arrays for `symbols` over [d0,d1] on the hourly grid, exactly
    per build_wide_panel.py. Returns dict of (T,N) arrays + grid. open_month='YYYY-MM' -> that month's
    funding_ema comes from the premium proxy (fundingRate archive absent for the open month)."""
    grid = np.arange(_ms(d0), _ms(d1) + HOUR_MS, HOUR_MS, dtype=np.int64)
    gidx = {int(t): i for i, t in enumerate(grid)}
    T, N = len(grid), len(symbols)
    A = {k: np.full((T, N), np.nan) for k in ("OPEN", "HIGH", "LOW", "CLOSE", "VOL", "QVOL")}
    FUND = np.full((T, N), np.nan)
    for si, sym in enumerate(symbols):
        kl = source.klines_1h(sym, d0, d1)
        if not kl.empty:
            ts = kl["open_time_ms"].to_numpy(np.int64)
            keep = np.array([int(t) in gidx for t in ts])
            rows = np.array([gidx[int(t)] for t in ts[keep]])
            if rows.size:
                for k, col in (("OPEN", "open"), ("HIGH", "high"), ("LOW", "low"),
                               ("CLOSE", "close"), ("VOL", "volume"), ("QVOL", "quote_volume")):
                    A[k][rows, si] = kl[col].to_numpy()[keep]
        # funding_ema (24h-equiv EMA, causal ffill) — panel recipe
        fdf = source.funding(sym, d0, d1)
        if not fdf.empty and len(fdf) >= 3:
            FUND[:, si] = fd.real_funding_ema(fdf, grid)
        # open-month proxy: fill any grid hours in the open month from premium index
        if open_month is not None:
            om0 = dt.datetime.strptime(open_month, "%Y-%m").replace(tzinfo=dt.timezone.utc)
            om1 = (om0.replace(day=28) + dt.timedelta(days=10)).replace(day=1)
            om_lo, om_hi = int(om0.timestamp() * 1000), int(om1.timestamp() * 1000)
            need = (grid >= om_lo) & (grid < om_hi) & ~np.isfinite(FUND[:, si])
            if need.any():
                prem = source.premium_index_1h(sym, om0.date(), d1)
                if not prem.empty:
                    proxy = fd.derive_funding_ema(prem, grid, interval_h=8)
                    FUND[need, si] = proxy[need]
    A["VWAP"] = np.where(A["VOL"] > 0, A["QVOL"] / np.where(A["VOL"] > 0, A["VOL"], np.nan), np.nan)
    A["FUND_EMA"] = FUND
    # DVOL30 = trailing-30d mean dollar-vol (exact build_wide_panel recipe)
    A["DVOL30"] = pd.DataFrame(A["QVOL"]).rolling(24 * 30, min_periods=24 * 5).mean().values
    A["grid"] = grid
    return A


def validate_overlap(source, tol_rel=1e-4, overlap_month=None, verbose=True):
    """Fresh-CDN-pull a CLOSED overlap month, rebuild wide_panel-level arrays, and compare to the
    frozen panel byte/near-value. Raw-input parity => downstream-channel parity. Returns report."""
    z = np.load(PANEL_FULL, allow_pickle=True)
    syms = [str(s) for s in z["symbols"]]
    ts = z["ts"].astype(np.int64)
    if overlap_month is None:
        end = pd.to_datetime(ts.max(), unit="ms", utc=True)
        overlap_month = f"{end.year:04d}-{end.month:02d}"           # last full frozen month
    m0 = dt.datetime.strptime(overlap_month, "%Y-%m").date()
    m1 = (m0.replace(day=28) + dt.timedelta(days=10)).replace(day=1) - dt.timedelta(days=1)
    if verbose:
        print(f"[overlap] fresh-pulling {overlap_month} ({len(syms)} syms) to compare vs frozen panel", flush=True)
    W = build_window(source, syms, m0, m1)                          # closed month -> exact funding
    fresh_ts = W["grid"]
    # align frozen rows for this month
    lo, hi = _ms(m0), _ms(m1) + HOUR_MS
    fr = np.where((ts >= lo) & (ts < hi))[0]
    frozen_ts = ts[fr]
    common = np.intersect1d(fresh_ts, frozen_ts)
    fi = {int(t): i for i, t in enumerate(fresh_ts)}
    fj = {int(t): i for i, t in enumerate(ts)}
    frows = np.array([fi[int(t)] for t in common]); jrows = np.array([fj[int(t)] for t in common])
    report = {"overlap_month": overlap_month, "n_common_hours": int(len(common)), "fields": {}}
    ok_all = True
    for k in ("CLOSE", "QVOL", "FUND_EMA"):
        a = W[k][frows]; b = z[k].astype(np.float64)[jrows]
        m = np.isfinite(a) & np.isfinite(b)
        if m.sum() == 0:
            report["fields"][k] = {"n": 0, "match": None}; continue
        rel = np.abs(a[m] - b[m]) / (np.abs(b[m]) + 1e-12)
        frac_ok = float(np.mean(rel <= tol_rel))
        # coverage parity: finite-cell agreement
        cov = float(np.mean(np.isfinite(a) == np.isfinite(b)))
        fld = {"n": int(m.sum()), "median_rel": round(float(np.median(rel)), 8),
               "p99_rel": round(float(np.percentile(rel, 99)), 8), "frac_within_tol": round(frac_ok, 5),
               "finite_coverage_parity": round(cov, 5), "match": bool(frac_ok >= 0.999 and cov >= 0.999)}
        report["fields"][k] = fld
        ok_all &= fld["match"]
        if verbose:
            print(f"  {k:9s} n={fld['n']:7d} med_rel={fld['median_rel']:.2e} p99={fld['p99_rel']:.2e} "
                  f"within_tol={fld['frac_within_tol']} cov_parity={fld['finite_coverage_parity']} -> {fld['match']}", flush=True)
    report["passed"] = bool(ok_all)
    return report


if __name__ == "__main__":
    import argparse, json
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate-overlap", action="store_true")
    ap.add_argument("--month", default=None, help="overlap month YYYY-MM (default: last frozen month)")
    ap.add_argument("--source", default="cdn")
    ap.add_argument("--out", default=MA + "/exports/live/overlap_validation.json")
    a = ap.parse_args()
    src = get_source(a.source)
    if a.validate_overlap:
        rep = validate_overlap(src, overlap_month=a.month)
        json.dump(rep, open(a.out, "w"), indent=1)
        print("PASSED" if rep["passed"] else "FAILED", "-> SAVED " + a.out, flush=True)
        sys.exit(0 if rep["passed"] else 1)
