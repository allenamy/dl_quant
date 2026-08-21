"""Phase-0b — SLOW/PERSISTENT cross-sectional price factors on the 14-asset panel (180s grid).

> **created:** 2026-07-08 | **Session:** multi-asset-v2 phase-0b (0B) | **状态:** in-progress

Motivation: the fast-microstructure 1h xsec baseline was NO-GO (feature decay + cost dominance,
NOT horizon). This builds the COMMODITIZED slow-factor baseline (multi-hour momentum/reversal/
vol/beta) — the baseline our innovative factors must beat later. All factors CAUSAL (trailing ≤t).

Grid: reuse the panel_cache 180s ts (near-continuous across 487 days, 0.21% day gaps). Every
lookback is an exact 180s multiple, so trailing returns land on exact ts (searchsorted-by-ts,
gap-safe). Raw mid+volume are loaded via bar_loader (cached to mid_panel.npz; ~1h once).

FACTORS (all per-asset, RAW; the xsec_ridge_h harness xsec-z's them per ts):
  mom_{4,8,24,72,168}h   trailing logret (searchsorted, exact wall-clock)
  rev_{1,3}h             = − trailing logret
  rvol_{24,72}h          rolling std of 180s logret (realized vol)
  dvol_{24,72}h          rolling std of min(logret,0) (downside/semi vol)
  beta_{24,72}h          rolling cov(ret, btc_ret)/var(btc_ret)
  resmom_24h             mom_24h − beta_24h·btc_mom_24h (beta-neutral residual momentum)
  lturnover_24h          log rolling-mean trade volume (turnover / illiquidity proxy)

Output: slow_factor_cache/<sym>.npz {X (nT,F) raw factors, ts, day, factor_names}.
"""
from __future__ import annotations
import argparse, os, os.path as p, sys, time
import numpy as np, pandas as pd

sys.path.insert(0, p.dirname(p.dirname(p.dirname(p.abspath(__file__)))))
from multi_asset.data.bar_loader import load_day_panel  # noqa: E402
from multi_asset.data.build_multihorizon_targets import SYMBOLS, list_days, WIN_START, WIN_END  # noqa: E402

ROOT = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports"
PC = ROOT + "/panel_cache"
MIDCACHE = ROOT + "/mid_panel.npz"
OUT = ROOT + "/slow_factor_cache"
NS = 1_000_000_000
STRIDE = 180
H = 3600  # 1 hour in seconds
MOM = [4, 8, 24, 72, 168]; REV = [1, 3]; VOLW = [24, 72]; BETAW = [24, 72]


def build_mid_panel():
    """Global-fill MID + VOLUME (nT,nS) at the common panel ts, across all days. Cached."""
    if p.exists(MIDCACHE):
        z = np.load(MIDCACHE, allow_pickle=True)
        return z["ts"].astype(np.int64), z["day"].astype(np.int64), z["MID"], z["VOL"]
    per = {s: np.load(p.join(PC, f"{s}.npz")) for s in SYMBOLS}
    common = np.array(sorted(set.intersection(*[set(per[s]["ts"].astype(np.int64).tolist()) for s in SYMBOLS])), dtype=np.int64)
    cset = common  # sorted
    nT, nS = len(common), len(SYMBOLS)
    DAY = np.zeros(nT, np.int64)
    d0 = per[SYMBOLS[0]]; idx0 = {int(t): i for i, t in enumerate(d0["ts"].astype(np.int64))}
    dyc = d0["day"].astype(np.int64)
    for i, t in enumerate(common):
        DAY[i] = dyc[idx0[int(t)]]
    MID = np.full((nT, nS), np.nan, np.float64); VOL = np.full((nT, nS), np.nan, np.float64)
    days = list_days(WIN_START, WIN_END); t0 = time.time()
    for di, d in enumerate(days):
        try:
            dp = load_day_panel(d, SYMBOLS)
        except Exception as e:
            print(f"  [warn] {d}: {e}", flush=True); continue
        dts = dp.ts.astype(np.int64); mi = dp.cols.index("mid")
        try:
            qb = dp.cols.index("tdQtyBuy"); qs = dp.cols.index("tdQtySell")
        except ValueError:
            qb = qs = None
        pos = np.searchsorted(dts, cset)
        ok = (pos < len(dts)) & (dts[np.clip(pos, 0, len(dts) - 1)] == cset)
        rows = np.where(ok)[0]; cols = pos[rows]
        for si, s in enumerate(SYMBOLS):
            arr = dp.data[s]
            MID[rows, si] = arr[cols, mi]
            if qb is not None:
                VOL[rows, si] = arr[cols, qb] + arr[cols, qs]
        if (di + 1) % 50 == 0 or di == len(days) - 1:
            print(f"  mid [{di+1}/{len(days)}] {d} {(time.time()-t0)/60:.1f}min filled={np.isfinite(MID).mean():.3f}", flush=True)
    np.savez(MIDCACHE, ts=common, day=DAY, MID=MID.astype(np.float32), VOL=VOL.astype(np.float32))
    print(f"[mid] cached -> {MIDCACHE}", flush=True)
    return common, DAY, MID.astype(np.float32), VOL.astype(np.float32)


def _mom(logmid_col, ts, H_sec):
    """Trailing logret over H_sec, exact wall-clock via searchsorted (gap-safe). (nT,)"""
    tgt = ts - H_sec * NS
    j = np.searchsorted(ts, tgt)
    jj = np.clip(j, 0, len(ts) - 1)
    m = logmid_col - logmid_col[jj]
    tol = 2 * STRIDE * NS
    ok = (j < len(ts)) & (j >= 0) & (np.abs(ts[jj] - tgt) < tol)
    m[~ok] = np.nan
    return m


def build():
    ts, day, MID, VOL = build_mid_panel()
    nT, nS = MID.shape
    logmid = np.log(np.where(MID > 0, MID, np.nan)).astype(np.float64)
    ret1 = np.full((nT, nS), np.nan)
    ret1[1:] = logmid[1:] - logmid[:-1]           # per-step 180s logret (day gaps -> big jump, mask below)
    # mask cross-day-gap returns (ts jump > 2*stride) as NaN
    gap = np.full(nT, False); gap[1:] = (ts[1:] - ts[:-1]) > 2 * STRIDE * NS
    ret1[gap] = np.nan
    btc_ret = ret1[:, 0]
    btc_mom = {w: _mom(logmid[:, 0], ts, w * H) for w in BETAW}

    names, cols = [], []
    for w in MOM:
        names.append(f"mom_{w}h"); cols.append(np.column_stack([_mom(logmid[:, si], ts, w * H) for si in range(nS)]))
    for w in REV:
        names.append(f"rev_{w}h"); cols.append(np.column_stack([-_mom(logmid[:, si], ts, w * H) for si in range(nS)]))
    # rolling helpers (window in steps; pandas ignores ts gaps -> negligible at 0.21%)
    def roll(fn, w_steps):
        return np.column_stack([fn(pd.Series(ret1[:, si]), w_steps).values for si in range(nS)])
    for w in VOLW:
        ws = w * H // STRIDE
        names.append(f"rvol_{w}h"); cols.append(roll(lambda s, k: s.rolling(k, min_periods=k // 2).std(), ws))
        names.append(f"dvol_{w}h")
        cols.append(np.column_stack([pd.Series(np.minimum(ret1[:, si], 0.0)).rolling(ws, min_periods=ws // 2).std().values for si in range(nS)]))
    for w in BETAW:
        ws = w * H // STRIDE
        b = np.full((nT, nS), np.nan)
        bser = pd.Series(btc_ret)
        var_b = bser.rolling(ws, min_periods=ws // 2).var().values
        for si in range(nS):
            cov = pd.Series(ret1[:, si]).rolling(ws, min_periods=ws // 2).cov(bser).values
            b[:, si] = cov / np.where(np.abs(var_b) > 1e-18, var_b, np.nan)
        names.append(f"beta_{w}h"); cols.append(b)
        if w == 24:
            beta24 = b
    # residual momentum 24h: mom_24h - beta_24h * btc_mom_24h
    rm = np.column_stack([_mom(logmid[:, si], ts, 24 * H) for si in range(nS)]) - beta24 * btc_mom[24][:, None]
    names.append("resmom_24h"); cols.append(rm)
    # log turnover 24h
    ws = 24 * H // STRIDE
    tv = np.column_stack([pd.Series(VOL[:, si]).rolling(ws, min_periods=ws // 2).mean().values for si in range(nS)])
    names.append("lturnover_24h"); cols.append(np.log(np.where(tv > 0, tv, np.nan)))

    Xf = np.stack(cols, axis=-1).astype(np.float32)   # (nT, nS, F)
    os.makedirs(OUT, exist_ok=True)
    for si, s in enumerate(SYMBOLS):
        np.savez(p.join(OUT, f"{s}.npz"), X=Xf[:, si, :], ts=ts, day=day,
                 factor_names=np.array(names, dtype=object))
    fin = np.isfinite(Xf).mean(axis=(0, 1))
    print(f"[slow] {len(names)} factors, nT={nT} nS={nS} -> {OUT}")
    for k, nm in enumerate(names):
        print(f"   {nm:14s} finite={fin[k]:.3f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--midonly", action="store_true")
    a = ap.parse_args()
    if a.midonly:
        build_mid_panel()
    else:
        build()
