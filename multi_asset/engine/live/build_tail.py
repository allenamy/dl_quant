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
import os
import sys

import numpy as np
import pandas as pd

# ★ MA MUST be defined before the first line that uses it. The portability refactor (ef2ddbb) left
# `sys.path.insert(0, os.path.join(MA, ...))` ABOVE this assignment, so this module raised NameError
# at import — and `os` was not imported at all. Both were invisible to the acceptance suites because
# nothing in them executes this module's top level. See run_daily.sh: this is the FIRST step, so the
# whole daily chain died here.
MA = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # .../multi_asset

sys.path.insert(0, os.path.join(MA, "engine", "live"))
from datasource import get_source          # noqa: E402
import funding_derive as fd                # noqa: E402

PANEL_FULL = MA + "/exports/wide_panel_full.npz"       # frozen raw-input panel (has OHLCV/FUND_EMA/DVOL30)
DL_FULL = MA + "/exports/wide_dl_full.npz"
HOUR_MS = 3_600_000


def _ms(d: dt.date) -> int:
    return int(dt.datetime(d.year, d.month, d.day, tzinfo=dt.timezone.utc).timestamp() * 1000)


def build_window(source, symbols, d0: dt.date, d1: dt.date, open_month=None, fund_warmup_days=30,
                 interval_cache=None):
    """Assemble wide_panel-level raw arrays for `symbols` over [d0,d1] on the hourly grid, exactly
    per build_wide_panel.py. Returns dict of (T,N) arrays + grid. open_month='YYYY-MM' -> that month's
    funding_ema comes from the premium proxy (fundingRate archive absent for the open month).

    funding_ema is a STATEFUL EMA (ewm carries state across months), so we fetch funding/premium
    from `fund_warmup_days` BEFORE d0 to warm the EMA to its continuous-history state before the
    target grid — otherwise early-window hours mismatch the frozen panel's carried EMA state."""
    d0f = d0 - dt.timedelta(days=fund_warmup_days)
    grid = np.arange(_ms(d0), _ms(d1) + HOUR_MS, HOUR_MS, dtype=np.int64)
    gidx = {int(t): i for i, t in enumerate(grid)}
    T, N = len(grid), len(symbols)
    A = {k: np.full((T, N), np.nan) for k in ("OPEN", "HIGH", "LOW", "CLOSE", "VOL", "QVOL")}
    FUND = np.full((T, N), np.nan)
    # Fetch per coin in PARALLEL (CDN fetches are I/O-bound; serial over 140 coins hangs for many
    # minutes). Each thread writes a DISJOINT column `si`, so direct array writes are safe.
    from concurrent.futures import ThreadPoolExecutor
    import threading
    if open_month is not None:
        _om0 = dt.datetime.strptime(open_month, "%Y-%m").replace(tzinfo=dt.timezone.utc)
        _om1 = (_om0.replace(day=28) + dt.timedelta(days=10)).replace(day=1)
        om_lo, om_hi = int(_om0.timestamp() * 1000), int(_om1.timestamp() * 1000)
    prog = [0]; lock = threading.Lock()

    def _coin(args):
        si, sym = args
        kl = source.klines_1h(sym, d0, d1)
        if not kl.empty:
            tsa = kl["open_time_ms"].to_numpy(np.int64)
            keep = np.array([int(t) in gidx for t in tsa])
            rows = np.array([gidx[int(t)] for t in tsa[keep]])
            if rows.size:
                for k, col in (("OPEN", "open"), ("HIGH", "high"), ("LOW", "low"),
                               ("CLOSE", "close"), ("VOL", "volume"), ("QVOL", "quote_volume")):
                    A[k][rows, si] = kl[col].to_numpy()[keep]
        # funding_ema (24h-equiv EMA, causal ffill), warmed from d0f; interval_cache[sym] reproduces
        # the frozen full-history EMA span for coins whose funding interval changed (8h<->4h).
        fdf = source.funding(sym, d0f, d1)
        if not fdf.empty and len(fdf) >= 3:
            FUND[:, si] = fd.real_funding_ema(fdf, grid, ema_span_source_h=(interval_cache or {}).get(sym))
        # open-month proxy: fill open-month hours with the premium-index derivation (funding archive
        # is absent for the current month).
        if open_month is not None:
            need = (grid >= om_lo) & (grid < om_hi) & ~np.isfinite(FUND[:, si])
            if need.any():
                prem = source.premium_index_1h(sym, d0f, d1)
                if not prem.empty:
                    proxy = fd.derive_funding_ema(prem, grid, interval_h=(interval_cache or {}).get(sym) or 8)
                    FUND[need, si] = proxy[need]
        with lock:
            prog[0] += 1
            if prog[0] % 30 == 0:
                print(f"  [build_window] {prog[0]}/{len(symbols)} coins fetched", flush=True)

    with ThreadPoolExecutor(max_workers=24) as ex:
        list(ex.map(_coin, list(enumerate(symbols))))
    A["VWAP"] = np.where(A["VOL"] > 0, A["QVOL"] / np.where(A["VOL"] > 0, A["VOL"], np.nan), np.nan)
    A["FUND_EMA"] = FUND
    # DVOL30 = trailing-30d mean dollar-vol (exact build_wide_panel recipe)
    A["DVOL30"] = pd.DataFrame(A["QVOL"]).rolling(24 * 30, min_periods=24 * 5).mean().values
    A["grid"] = grid
    return A


def validate_overlap(source, tol_rel=1e-4, overlap_month=None, verbose=True, interval_cache=None):
    """Fresh-CDN-pull a CLOSED overlap month, rebuild wide_panel-level arrays, and compare to the
    frozen panel byte/near-value. Raw-input parity => downstream-channel parity. Returns report."""
    import os, json
    z = np.load(PANEL_FULL, allow_pickle=True)
    syms = [str(s) for s in z["symbols"]]
    ts = z["ts"].astype(np.int64)
    if overlap_month is None:
        end = pd.to_datetime(ts.max(), unit="ms", utc=True)
        overlap_month = f"{end.year:04d}-{end.month:02d}"           # last full frozen month
    m0 = dt.datetime.strptime(overlap_month, "%Y-%m").date()
    m1 = (m0.replace(day=28) + dt.timedelta(days=10)).replace(day=1) - dt.timedelta(days=1)
    if interval_cache is None:
        cpath = MA + "/exports/live/funding_intervals.json"
        interval_cache = json.load(open(cpath)) if os.path.exists(cpath) else {}
    if verbose:
        print(f"[overlap] fresh-pulling {overlap_month} ({len(syms)} syms; interval_cache {len(interval_cache)} coins) "
              f"to compare vs frozen panel", flush=True)
    W = build_window(source, syms, m0, m1, interval_cache=interval_cache)     # closed month -> exact funding
    fresh_ts = W["grid"]
    # align frozen rows for this month
    lo, hi = _ms(m0), _ms(m1) + HOUR_MS
    fr = np.where((ts >= lo) & (ts < hi))[0]
    frozen_ts = ts[fr]
    common = np.intersect1d(fresh_ts, frozen_ts)
    fi = {int(t): i for i, t in enumerate(fresh_ts)}
    fj = {int(t): i for i, t in enumerate(ts)}
    frows = np.array([fi[int(t)] for t in common]); jrows = np.array([fj[int(t)] for t in common])
    from scipy.stats import rankdata
    report = {"overlap_month": overlap_month, "n_common_hours": int(len(common)), "fields": {}}
    ok_all = True
    # CLOSE/QVOL feed price/volume channels -> require strict value-byte parity.
    # FUND_EMA feeds a RANK-weighted leg + is 1/32 model inputs; Binance changed funding-interval on
    # some alts (8h<->4h) so exact historical values are irreproducible for ~15 low-tier coins, but
    # the cross-sectional RANK (what the leg trades) is preserved. So gate FUND_EMA on rank-corr.
    for k in ("CLOSE", "QVOL", "FUND_EMA"):
        a = W[k][frows]; b = z[k].astype(np.float64)[jrows]
        m = np.isfinite(a) & np.isfinite(b)
        if m.sum() == 0:
            report["fields"][k] = {"n": 0, "match": None}; continue
        rel = np.abs(a[m] - b[m]) / (np.abs(b[m]) + 1e-12)
        frac_ok = float(np.mean(rel <= tol_rel))
        cov = float(np.mean(np.isfinite(a) == np.isfinite(b)))
        fld = {"n": int(m.sum()), "median_rel": round(float(np.median(rel)), 8),
               "p99_rel": round(float(np.percentile(rel, 99)), 8), "frac_within_tol": round(frac_ok, 5),
               "finite_coverage_parity": round(cov, 5), "criterion": "value_byte"}
        if k == "FUND_EMA":
            # (i) xsec rank-corr per hour (leg caliber) -> median >= 0.99
            rc = []
            for h in range(a.shape[0]):
                ok = np.isfinite(a[h]) & np.isfinite(b[h])
                if ok.sum() >= 8 and a[h, ok].std() > 1e-12 and b[h, ok].std() > 1e-12:
                    rc.append(np.corrcoef(rankdata(a[h, ok]), rankdata(b[h, ok]))[0, 1])
            rc_med = float(np.median(rc)) if rc else 0.0
            # (ii) per-coin time-series corr -> min >= 0.95 (a real recipe break fails; interval-changed
            # coins recover via the full-history interval cache)
            pcc = []
            for si in range(a.shape[1]):
                ok = np.isfinite(a[:, si]) & np.isfinite(b[:, si])
                if ok.sum() >= 20 and a[ok, si].std() > 1e-12 and b[ok, si].std() > 1e-12:
                    pcc.append(float(np.corrcoef(a[ok, si], b[ok, si])[0, 1]))
            pcc_min = float(np.min(pcc)) if pcc else 0.0
            fld["criterion"] = "xsec_rank_corr + per_coin_min + coverage"
            fld["xsec_rank_corr_median"] = round(rc_med, 5)
            fld["per_coin_ts_corr_min"] = round(pcc_min, 4)
            fld["per_coin_below_0.95"] = int(np.sum(np.array(pcc) < 0.95)) if pcc else None
            fld["coverage_parity"] = round(cov, 4)     # diagnostic floor 0.90 (benign 4h-vs-8h grid ffill)
            fld["match"] = bool(rc_med >= 0.99 and pcc_min >= 0.95 and cov >= 0.90)
        else:
            fld["match"] = bool(frac_ok >= 0.999 and cov >= 0.999)
        report["fields"][k] = fld
        ok_all &= fld["match"]
        if verbose:
            extra = (f"rank_corr_med={fld.get('xsec_rank_corr_median')} per_coin_min={fld.get('per_coin_ts_corr_min')} "
                     f"n<0.95={fld.get('per_coin_below_0.95')} cov={fld.get('coverage_parity')}") if k == "FUND_EMA" \
                    else f"within_tol={fld['frac_within_tol']} cov={fld['finite_coverage_parity']}"
            print(f"  {k:9s} n={fld['n']:7d} med_rel={fld['median_rel']:.2e} {extra} -> {fld['match']}", flush=True)
    report["passed"] = bool(ok_all)
    return report


def build_live_panel(source, out_panel=None, out_dl=None, verbose=True):
    """Extend the frozen wide_panel_full with the new tail (frozen_end -> latest complete CDN day),
    then run the EXISTING build_wide_dl over the extended panel -> wide_dl_live.npz (recomputes
    CH/MEMBER110/YR/CL with correct absolute row indexing). funding for the OPEN month uses the
    premium proxy (rank-consistent; see funding_derive / RUNBOOK curve A/B)."""
    z = np.load(PANEL_FULL, allow_pickle=True)
    syms = [str(s) for s in z["symbols"]]
    ts = z["ts"].astype(np.int64)
    frozen_end = int(ts.max())
    d0 = (pd.to_datetime(frozen_end, unit="ms", utc=True) + pd.Timedelta(hours=1)).date()
    d1 = source.latest_complete_date()
    if d0 > d1:
        if verbose:
            print(f"[live] no new complete days beyond frozen panel end {d0 - dt.timedelta(days=1)}", flush=True)
        return None
    open_month = f"{d1.year:04d}-{d1.month:02d}"
    import os, json
    cpath = MA + "/exports/live/funding_intervals.json"
    interval_cache = json.load(open(cpath)) if os.path.exists(cpath) else {}
    if verbose:
        print(f"[live] appending tail {d0}..{d1} (open_month={open_month}; interval_cache {len(interval_cache)} coins) "
              f"to frozen panel (end {pd.to_datetime(frozen_end, unit='ms', utc=True)})", flush=True)
    W = build_window(source, syms, d0, d1, open_month=open_month, interval_cache=interval_cache)
    new_mask = W["grid"] > frozen_end
    ng = W["grid"][new_mask]
    if ng.size == 0:
        if verbose:
            print("[live] window produced no rows strictly after frozen end", flush=True)
        return None
    ext = {"ts": np.concatenate([ts, ng]), "symbols": z["symbols"]}
    for k in ("OPEN", "HIGH", "LOW", "CLOSE", "VOL", "QVOL", "VWAP", "FUND_EMA"):
        ext[k] = np.concatenate([z[k].astype(np.float64), W[k][new_mask]], axis=0).astype(np.float32)
    ext["DVOL30"] = pd.DataFrame(ext["QVOL"].astype(np.float64)).rolling(24 * 30, min_periods=24 * 5).mean().values.astype(np.float32)
    logc = np.log(np.where(ext["CLOSE"] > 0, ext["CLOSE"], np.nan))
    Yv = np.full(ext["CLOSE"].shape, np.nan, np.float32); Yv[:-1] = (logc[1:] - logc[:-1]).astype(np.float32)
    ext["Y"] = Yv
    ext["MEMBER"] = np.zeros(ext["CLOSE"].shape, bool)     # placeholder; build_wide_dl computes MEMBER110
    out_panel = out_panel or (MA + "/exports/live/wide_panel_live.npz")
    with open(out_panel, "wb") as f:
        np.savez(f, **ext)
    if verbose:
        print(f"[live] extended wide_panel: {len(ts)} -> {len(ext['ts'])} rows (+{ng.size}) -> {out_panel}", flush=True)
    # run the existing build_wide_dl over the extended panel
    sys.path.insert(0, MA.rsplit("/multi_asset", 1)[0])
    import multi_asset.data.build_wide_dl as bwd
    out_dl = out_dl or (MA + "/exports/live/wide_dl_live.npz")
    # ★ THE CALIBER IS DECLARED HERE BECAUSE THIS IS WHERE IT IS DECIDED (0C 2026-07-29).
    # `funding_derive.real_funding_ema` does NOT normalise the settlement rate — deliberately, so
    # the live splice reproduces the caliber of the panel the frozen king/s2 heads were fitted on
    # (`exports/wide_dl_full.npz`, built 2026-07-11, never rebuilt after the 07-25 fix). The stamp
    # states that intent inside the artifact; assert_funding_dim then measures the channels and must
    # agree. If someone ever normalises this path without retraining, intent and measurement part
    # company and the build goes red — instead of the model quietly being fed a distribution it was
    # never fitted on.
    bwd.build(panel=out_panel, outpath=out_dl, caliber="as_trained",
              caliber_why=("live splice must match the training panel: funding_derive."
                           "real_funding_ema emits the un-normalised per-settlement rate on "
                           "purpose, because the frozen king/s2 fold-4 heads were fitted on it and "
                           "were NOT retrained after the 2026-07-25 settlement-interval fix"))
    return dict(new_rows=int(ng.size), extended_T=len(ext["ts"]), open_month=open_month, dl_out=out_dl,
                new_span=[str(pd.to_datetime(ng.min(), unit="ms")), str(pd.to_datetime(ng.max(), unit="ms"))])


def validate_live_vs_frozen(dl_live, dl_full=DL_FULL, verbose=True):
    """After build, confirm the extended wide_dl_live reproduces the frozen wide_dl_full on the
    historical rows (deterministic recompute must not drift), for CH + MEMBER110 + YR4/CL4."""
    L = np.load(dl_live, allow_pickle=True); F = np.load(dl_full, allow_pickle=True)
    Tf = F["ts"].shape[0]
    rep = {}
    for k in ("CH", "MEMBER110", "YR4", "CL4"):
        a = L[k][:Tf]; b = F[k]
        if a.dtype == bool:
            rep[k] = round(float(np.mean(a == b)), 6)
        else:
            m = np.isfinite(a) & np.isfinite(b)
            rep[k] = round(float(np.mean(np.abs(a[m] - b[m]) <= 1e-4 * (np.abs(b[m]) + 1e-9))), 6) if m.any() else None
    ok = all((v is None) or v >= 0.999 for v in rep.values())
    if verbose:
        print(f"[live] historical-recompute parity vs frozen: {rep} -> {'OK' if ok else 'DRIFT'}", flush=True)
    return dict(parity=rep, passed=bool(ok))


if __name__ == "__main__":
    import argparse, json
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate-overlap", action="store_true")
    ap.add_argument("--build", action="store_true", help="build the extended wide_dl_live.npz")
    ap.add_argument("--build-cache", action="store_true", help="build the full-history funding-interval cache")
    ap.add_argument("--month", default=None, help="overlap month YYYY-MM (default: last frozen month)")
    ap.add_argument("--source", default="cdn")
    ap.add_argument("--out", default=MA + "/exports/live/overlap_validation.json")
    a = ap.parse_args()
    src = get_source(a.source)
    if a.build_cache:
        z = np.load(PANEL_FULL, allow_pickle=True); syms = [str(s) for s in z["symbols"]]
        cpath = MA + "/exports/live/funding_intervals.json"
        cache = fd.build_interval_cache(src, syms, out=cpath)
        from collections import Counter
        print(f"[cache] built {len(cache)}/{len(syms)} coins -> {cpath}; interval histogram {dict(Counter(cache.values()))}", flush=True)
        sys.exit(0)
    if a.validate_overlap:
        rep = validate_overlap(src, overlap_month=a.month)
        json.dump(rep, open(a.out, "w"), indent=1)
        print("PASSED" if rep["passed"] else "FAILED", "-> SAVED " + a.out, flush=True)
        sys.exit(0 if rep["passed"] else 1)
    if a.build:
        res = build_live_panel(src)
        if res:
            print(json.dumps(res, indent=1), flush=True)
            v = validate_live_vs_frozen(res["dl_out"])
            json.dump({"build": res, "parity": v}, open(MA + "/exports/live/build_live_report.json", "w"), indent=1)
            sys.exit(0 if v["passed"] else 1)
