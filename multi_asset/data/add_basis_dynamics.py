"""Add X_basis (comprehensive basis-DYNAMICS block) to the 2023+ npzv4_dual cache.

> **created:** 2026-06-23 | **Session:** v2-dual-source-arch (basis dynamics) | **状态:** in-progress

MECHANISM (why this should add perp signal)
-------------------------------------------
perp is a spot DERIVATIVE; the basis (perp_mid − spot_mid) governs how much of a
predicted spot move the perp realizes (measured corr(pred, basis) ≈ −0.5). The
existing cross channels are INSTANTANEOUS diffs → inert. The alpha is in the basis
DYNAMICS: distance-from-equilibrium (z-score) predicts mean-reversion; drift/momentum
predicts continuation; lead-lag says who moves first. This block builds those, all
leak-safe (≤t) and per-step so RevIN/per-channel-norm handles scaling.

DATA NOTE (no mids pre-2024)
----------------------------
npz_v4/npz_perp carry no mid LEVEL, and mid_cache starts 2024-01. But the basis
CHANGE = perp_ret − spot_ret is EXACTLY reconstructable from the two log_return_1s
series (validated corr 1.0 vs real mid_cache basis-change). We reconstruct a per-
second RELATIVE basis level = cumsum(perp_ret − spot_ret) anchored at the day start
(prior-day tail stitched for a warm anchor). The ABSOLUTE level offset is lost, but
every DYNAMICS feature here (EMA, z-score-vs-rolling-mean, vol, momentum, AR1,
lead-lag) is invariant to a constant level offset OR uses a short rolling window
that subtracts it — so they are valid 2023+ uniformly.

CHANNELS (X_basis, 10) — all per-step (B,600,10), ≤t, raw (dataset normalizes):
  0 basis_rel       relative basis level (cumsum perp-spot ret, bps), de-meaned per window
  1 basis_ema_fast  EMA_60 of basis_rel − basis_rel (fast deviation)
  2 basis_ema_slow  EMA_300 of basis_rel − basis_rel (slow drift)
  3 basis_z         (basis_rel − roll_mean_300) / roll_std_300  ← equilibrium distance (reversion)
  4 basis_vol       rolling std_60 of basis CHANGE (basis turbulence)
  5 basis_mom_60    basis_rel − basis_rel[-60]   (60s basis momentum)
  6 basis_mom_300   basis_rel − basis_rel[-300]  (300s basis drift)
  7 basis_ar1_120   rolling AR1 of basis CHANGE over 120s (reversion strength: AR1<0 = mean-revert)
  8 leadlag_5       rolling corr(perp_ret_t, spot_ret_{t-k}) − corr(spot_ret_t, perp_ret_{t-k}), k=1..5 (who leads)
  9 arb_pressure    perp_obi_L5 − spot_obi_L5 (book-pressure differential = basis push), clipped

All causal: every value at step p uses only data ≤ second p.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import os.path as p

import numpy as np

_REPO = p.dirname(p.dirname(p.dirname(p.abspath(__file__))))
NPZV4_DIR = "/mnt/storage/private/work_hsy/quant_research/data/npz_v4"
PERP_DIR = p.join(_REPO, "data", "npz_perp")
DUAL_DIR = p.join(_REPO, "data", "npzv4_dual")

INPUT_LEN = 600
US = 1_000_000
EPS = 1e-8
J_RET1S = 0
J_OBI_L5 = 6

BASIS_NAMES = [
    "basis_rel", "basis_ema_fast", "basis_ema_slow", "basis_z", "basis_vol",
    "basis_mom_60", "basis_mom_300", "basis_ar1_120", "leadlag_5", "arb_pressure",
]


def _ema(x, span):
    a = 2.0 / (span + 1.0)
    out = np.empty_like(x)
    acc = x[0]
    for i in range(x.size):
        acc = a * x[i] + (1 - a) * acc
        out[i] = acc
    return out


def _roll_mean_std(x, win):
    """Trailing rolling mean/std SHIFT(0) (uses x[i-win+1..i], causal)."""
    n = x.size
    cs = np.concatenate([[0.0], np.cumsum(x)])
    cs2 = np.concatenate([[0.0], np.cumsum(x * x)])
    i = np.arange(n)
    lo = np.maximum(0, i - win + 1)
    cnt = (i - lo + 1).astype(np.float64)
    s1 = cs[i + 1] - cs[lo]
    s2 = cs2[i + 1] - cs2[lo]
    mean = s1 / cnt
    var = np.maximum(s2 / cnt - mean * mean, 0.0)
    return mean, np.sqrt(var)


def _roll_ar1(dx, win):
    """Rolling AR1 of series dx over `win` (corr of dx_t with dx_{t-1})."""
    n = dx.size
    a = dx.copy()
    b = np.concatenate([[0.0], dx[:-1]])     # lag-1
    # rolling corr via rolling sums
    def _rs(z):
        cs = np.concatenate([[0.0], np.cumsum(z)])
        i = np.arange(n); lo = np.maximum(0, i - win + 1)
        return cs[i + 1] - cs[lo], (i - lo + 1).astype(np.float64)
    sa, cnt = _rs(a); sb, _ = _rs(b)
    saa, _ = _rs(a * a); sbb, _ = _rs(b * b); sab, _ = _rs(a * b)
    ma = sa / cnt; mb = sb / cnt
    cov = sab / cnt - ma * mb
    va = np.maximum(saa / cnt - ma * ma, EPS); vb = np.maximum(sbb / cnt - mb * mb, EPS)
    return cov / np.sqrt(va * vb)


def _build_basis(pret, sret, p_obi, s_obi, pred_secs, sec_grid):
    """Build per-window X_basis (N,600,10) from per-second perp/spot returns + obi,
    sampling the causal per-second basis-dynamics at each window second."""
    # per-second relative basis level (bps) = cumsum(perp_ret - spot_ret)*1e4
    chg = (pret - sret) * 1e4
    basis_rel = np.cumsum(chg)
    ema_f = _ema(basis_rel, 60)
    ema_s = _ema(basis_rel, 300)
    rmean, rstd = _roll_mean_std(basis_rel, 300)
    basis_z = (basis_rel - rmean) / np.where(rstd > EPS, rstd, 1.0)
    _, basis_vol = _roll_mean_std(chg, 60)
    mom60 = basis_rel - np.concatenate([np.full(60, basis_rel[0]), basis_rel[:-60]]) if basis_rel.size > 60 else np.zeros_like(basis_rel)
    mom300 = basis_rel - np.concatenate([np.full(300, basis_rel[0]), basis_rel[:-300]]) if basis_rel.size > 300 else np.zeros_like(basis_rel)
    ar1 = _roll_ar1(chg, 120)
    # lead-lag: corr(perp_t, spot_{t-1..5}) - corr(spot_t, perp_{t-1..5}) rolling 120
    def _rollcorr(a, b, win):
        n = a.size
        def _rs(z):
            cs = np.concatenate([[0.0], np.cumsum(z)]); i = np.arange(n); lo = np.maximum(0, i - win + 1)
            return cs[i + 1] - cs[lo], (i - lo + 1).astype(np.float64)
        sa, cnt = _rs(a); sb, _ = _rs(b); saa, _ = _rs(a * a); sbb, _ = _rs(b * b); sab, _ = _rs(a * b)
        ma = sa / cnt; mb = sb / cnt
        cov = sab / cnt - ma * mb
        va = np.maximum(saa / cnt - ma * ma, EPS); vb = np.maximum(sbb / cnt - mb * mb, EPS)
        return cov / np.sqrt(va * vb)
    leadlag = np.zeros_like(basis_rel)
    for k in range(1, 6):
        ps = np.concatenate([np.zeros(k), sret[:-k]])   # spot lagged k
        sp = np.concatenate([np.zeros(k), pret[:-k]])   # perp lagged k
        leadlag += _rollcorr(pret, ps, 120) - _rollcorr(sret, sp, 120)
    leadlag /= 5.0
    arb = np.clip(p_obi - s_obi, -2.0, 2.0)

    chans = [basis_rel - rmean, ema_f - basis_rel, ema_s - basis_rel, basis_z,
             basis_vol, mom60, mom300, ar1, leadlag, arb]
    pers = np.column_stack([np.nan_to_num(c, nan=0.0, posinf=0.0, neginf=0.0) for c in chans])  # (T,10)

    # sample at each window second via ≤t lookup on sec_grid
    N = pred_secs.size
    offs = np.arange(-(INPUT_LEN - 1), 1, dtype=np.int64)
    win_secs = pred_secs[:, None] + offs[None, :]    # (N,600)
    j = np.searchsorted(sec_grid, win_secs.reshape(-1), side="right") - 1
    valid = j >= 0
    j = np.clip(j, 0, sec_grid.size - 1)
    Xb = pers[j].reshape(N, INPUT_LEN, 10)
    Xb[~valid.reshape(N, INPUT_LEN)] = 0.0
    return Xb.astype(np.float32)


def _reconstruct(ts_sec, win_arr):
    """Reconstruct per-second series from overlapping windows (same as X_long)."""
    N = ts_sec.size
    lo = int(ts_sec[0]) - (INPUT_LEN - 1); hi = int(ts_sec[-1]); T = hi - lo + 1
    grid = np.zeros(T); filled = np.zeros(T, bool)
    offs = np.arange(-(INPUT_LEN - 1), 1)
    for i in range(N):
        idx = int(ts_sec[i]) + offs - lo
        good = (idx >= 0) & (idx < T)
        grid[idx[good]] = win_arr[i][good]; filled[idx[good]] = True
    base = lo + np.arange(T)
    return base[filled], grid[filled]


def _day_series(day):
    v4fp = p.join(NPZV4_DIR, f"{day}.npz"); ppfp = p.join(PERP_DIR, f"{day}.npz"); dfp = p.join(DUAL_DIR, f"{day}.npz")
    if not (p.exists(v4fp) and p.exists(ppfp) and p.exists(dfp)):
        return None
    v4 = np.load(v4fp, allow_pickle=True); pp = np.load(ppfp, allow_pickle=True); dl = np.load(dfp, allow_pickle=True)
    tv = v4["timestamps"].astype(np.int64); tp = pp["timestamps"].astype(np.int64)
    near = [int(tp[np.argmin(np.abs(tp - t))] - t) for t in tv[:min(50, len(tv))]]
    vals, cnts = np.unique(np.array(near), return_counts=True); off = int(vals[np.argmax(cnts)])
    target = tv + off; idx = np.clip(np.searchsorted(tp, target), 0, len(tp) - 1); exact = (tp[idx] == target)
    td = dl["timestamps"].astype(np.int64); keepv = np.isin(tv, td)
    tv = tv[keepv]; pidx = idx[keepv]
    sret_w = v4["X"][keepv][:, :, J_RET1S].astype(np.float64); pret_w = pp["X"][pidx][:, :, J_RET1S].astype(np.float64)
    sobi_w = v4["X"][keepv][:, :, J_OBI_L5].astype(np.float64); pobi_w = pp["X"][pidx][:, :, J_OBI_L5].astype(np.float64)
    ts_sec = tv // US
    secg, sret = _reconstruct(ts_sec, sret_w)
    _, pret = _reconstruct(ts_sec, pret_w)
    _, sobi = _reconstruct(ts_sec, sobi_w)
    _, pobi = _reconstruct(ts_sec, pobi_w)
    return ts_sec, secg, pret, sret, pobi, sobi


def build_day(day, force=False):
    dfp = p.join(DUAL_DIR, f"{day}.npz")
    if not p.exists(dfp):
        return "missing"
    dl = dict(np.load(dfp, allow_pickle=True))
    if "X_basis" in dl and not force:
        return "skip"
    cur = _day_series(day)
    if cur is None:
        return "no-series"
    ts_sec, secg, pret, sret, pobi, sobi = cur
    # prior-day stitch for a warm basis anchor + rolling windows
    pday = (dt.date.fromisoformat(day) - dt.timedelta(days=1)).isoformat()
    pc = _day_series(pday)
    if pc is not None:
        _, psecg, ppret, psret, ppobi, psobi = pc
        keep = psecg < secg[0]
        secg = np.concatenate([psecg[keep], secg]); pret = np.concatenate([ppret[keep], pret])
        sret = np.concatenate([psret[keep], sret]); pobi = np.concatenate([ppobi[keep], pobi]); sobi = np.concatenate([psobi[keep], sobi])
    pred_secs = dl["timestamps"].astype(np.int64) // US
    Xb = _build_basis(pret, sret, pobi, sobi, pred_secs, secg)
    if Xb.shape[0] != dl["X"].shape[0]:
        return f"len-mismatch {Xb.shape[0]} vs {dl['X'].shape[0]}"
    dl["X_basis"] = Xb
    dl["basis_names"] = np.array(BASIS_NAMES, dtype=object)
    np.savez(dfp, **dl)
    return "built"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", nargs="*", default=None)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    days = sorted(f[:-4] for f in os.listdir(DUAL_DIR) if f.endswith(".npz") and f[0].isdigit()) if args.all else args.days
    if not days:
        ap.error("pass --days or --all")
    import time
    print(f"[basis] {len(days)} day(s)", flush=True)
    t0 = time.time(); counts = {}
    for i, day in enumerate(days):
        try:
            r = build_day(day, force=args.force)
        except Exception as e:  # noqa: BLE001
            r = f"error:{type(e).__name__}:{e}"
        k = r if r in ("built", "skip") else (r.split()[0] if r else "unk")
        counts[k] = counts.get(k, 0) + 1
        if r not in ("built", "skip"):
            print(f"  {day}: {r}", flush=True)
        if (i + 1) % 100 == 0 or i + 1 == len(days):
            print(f"  [{i+1}/{len(days)}] {counts} ({time.time()-t0:.0f}s)", flush=True)
    print(f"[basis] DONE {counts} in {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
