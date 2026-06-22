"""Add X_long (60s-pooled 4h long-context) to the 2023+ npzv4_dual overlay cache.

> **created:** 2026-06-23 | **Session:** v2-dual-source-arch (2023+ levers) | **状态:** in-progress

WHY
---
The long-context γ-FiLM lever needs an ``X_long`` (N,240,10) per-window 4h context.
mid_cache has no 2023 days, so we cannot reuse build_v2arch_npz._build_long (which
sourced per-second mids). Instead we RECONSTRUCT the per-second spot/perp return
series from the overlay's OWN data: npz_v4 ``log_return_1s`` (feat 0) gives the SPOT
per-second return inside each 600s window, and the joined npz_perp ``log_return_1s``
gives PERP. Consecutive windows (stride 180, overlap 420) tile the day — stitching
each window's last ``stride`` new seconds reconstructs a continuous per-second series
(verified: w0 tail == w1 head, atol 1e-4). We pool that to 60s bins and, for each
window, take the 240 bins STRICTLY BEFORE the bin containing t (leak-safe, exactly
the original mechanism). Prior-day tail is stitched on the LEFT for a warm 4h start.

The 10 channels match build_v2arch_npz._build_long EXACTLY (so the model's long_c_in=10
and the FiLM contract are unchanged):
  [spot_ret, spot_rvol, spot_obi, spot_spr(=vol proxy), spot_vol,
   perp_ret, perp_rvol, perp_obi, perp_spr(=vol proxy), basis_bps]
basis_bps is reconstructed from the cross block channel ``x_mpdev_diff`` (the bounded
perp−spot microprice-dev differential, our 2023-safe basis-LEVEL proxy).

OUTPUT: rewrites each data/npzv4_dual/<day>.npz IN PLACE adding ``X_long`` (and
``long_names``); all other keys preserved verbatim. Idempotent (skips days that
already have X_long unless --force).
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import os.path as p
import time

import numpy as np

_REPO = p.dirname(p.dirname(p.dirname(p.abspath(__file__))))
NPZV4_DIR = "/mnt/storage/private/work_hsy/quant_research/data/npz_v4"
PERP_DIR = p.join(_REPO, "data", "npz_perp")
DUAL_DIR = p.join(_REPO, "data", "npzv4_dual")

INPUT_LEN = 600
LONG_POOL_S = 60
LONG_STEPS = 240          # 4h
US = 1_000_000
EPS = 1e-8
SHIFT_TOL_US = 11 * US

J_RET1S = 0
LONG_NAMES = [
    "l_spot_ret", "l_spot_rvol", "l_spot_obi", "l_spot_spr", "l_spot_vol",
    "l_perp_ret", "l_perp_rvol", "l_perp_obi", "l_perp_spr", "l_basis",
]


def _reconstruct_persec(ts_sec: np.ndarray, ret_win: np.ndarray):
    """Reconstruct a continuous per-second return series from overlapping windows.

    ts_sec : (N,) window cutoff seconds (sorted). ret_win : (N,600) per-second
    log_return inside each window ([t-599..t]). Returns (sec_grid, ret_grid):
    sec_grid the union of all covered seconds, ret_grid the per-second return
    (later windows overwrite earlier — identical on overlap by construction)."""
    N = ts_sec.size
    # earliest covered second .. latest
    lo = int(ts_sec[0]) - (INPUT_LEN - 1)
    hi = int(ts_sec[-1])
    T = hi - lo + 1
    grid = np.zeros(T, dtype=np.float64)
    filled = np.zeros(T, dtype=bool)
    offs = np.arange(-(INPUT_LEN - 1), 1)        # (600,)
    for i in range(N):
        secs = int(ts_sec[i]) + offs              # (600,)
        idx = secs - lo
        good = (idx >= 0) & (idx < T)
        grid[idx[good]] = ret_win[i][good]
        filled[idx[good]] = True
    base_sec = lo + np.arange(T)
    return base_sec[filled], grid[filled]


def _binagg(x, inv, nb, how):
    out = np.zeros(nb)
    if how == "sum":
        np.add.at(out, inv, x)
    elif how == "std":
        m = np.zeros(nb); cnt = np.zeros(nb)
        np.add.at(cnt, inv, 1.0); np.add.at(m, inv, x); m = m / np.where(cnt > 0, cnt, 1.0)
        v = np.zeros(nb); np.add.at(v, inv, (x - m[inv]) ** 2)
        out = np.sqrt(v / np.where(cnt > 0, cnt, 1.0))
    return out


def _build_long(sec_s, sret, sec_p, pret, sec_b, basis, pred_secs, prev=None):
    """(N,240,10) 60s-pooled 4h long-context; bins strictly before t's bin."""
    if prev is not None:
        (ps_s, psr), (ps_p, ppr), (ps_b, pba) = prev
        def _stitch(a_sec, a_val, b_sec, b_val):
            keep = a_sec < b_sec[0] if b_sec.size else np.ones(a_sec.size, bool)
            return (np.concatenate([a_sec[keep], b_sec]),
                    np.concatenate([a_val[keep], b_val]))
        sec_s, sret = _stitch(ps_s, psr, sec_s, sret)
        sec_p, pret = _stitch(ps_p, ppr, sec_p, pret)
        sec_b, basis = _stitch(ps_b, pba, sec_b, basis)

    sret = np.clip(sret, -0.02, 0.02); pret = np.clip(pret, -0.02, 0.02)
    # common bin grid over the union of seconds
    allsec = np.union1d(np.union1d(sec_s, sec_p), sec_b)
    binid_all = (allsec // LONG_POOL_S)
    uniq = np.unique(binid_all); nb = uniq.size
    binpos = {int(b): i for i, b in enumerate(uniq)}

    def _agg(sec, val, how):
        inv = np.array([binpos[int(s // LONG_POOL_S)] for s in sec], dtype=np.int64)
        return _binagg(val, inv, nb, how)

    bin_sret = np.clip(_agg(sec_s, sret, "sum"), -0.05, 0.05)
    bin_srv = _agg(sec_s, sret, "std")
    bin_pret = np.clip(_agg(sec_p, pret, "sum"), -0.05, 0.05)
    bin_prv = _agg(sec_p, pret, "std")
    bin_basis = _agg(sec_b, basis, "sum") / np.maximum(
        _binagg(np.ones(sec_b.size), np.array([binpos[int(s // LONG_POOL_S)] for s in sec_b]), nb, "sum"), 1.0)
    bin_sobi = np.tanh(bin_sret / (bin_srv + EPS))
    bin_pobi = np.tanh(bin_pret / (bin_prv + EPS))
    bin_svol = np.log1p(_agg(sec_s, np.abs(sret), "sum") * 1e4)
    bin_pvol = np.log1p(_agg(sec_p, np.abs(pret), "sum") * 1e4)

    bin_feats = np.column_stack([
        bin_sret, bin_srv, bin_sobi, bin_svol, bin_svol,
        bin_pret, bin_prv, bin_pobi, bin_pvol, bin_basis,
    ])
    bin_feats = np.nan_to_num(bin_feats, nan=0.0, posinf=0.0, neginf=0.0)

    N = pred_secs.size
    Xlong = np.zeros((N, LONG_STEPS, 10), dtype=np.float32)
    bin_of_pred = pred_secs // LONG_POOL_S
    for wi in range(N):
        last_complete = int(bin_of_pred[wi]) - 1
        seg = np.zeros((LONG_STEPS, 10), dtype=np.float32)
        for k in range(LONG_STEPS):
            b = last_complete - (LONG_STEPS - 1 - k)
            j = binpos.get(int(b), -1)
            if j >= 0:
                seg[k] = bin_feats[j]
        Xlong[wi] = seg
    return Xlong


def _series_for_day(day):
    """Return (ts_sec, sret_grid_sec, pret_grid_sec, basis_sec) for a day, or None."""
    v4fp = p.join(NPZV4_DIR, f"{day}.npz"); ppfp = p.join(PERP_DIR, f"{day}.npz")
    dfp = p.join(DUAL_DIR, f"{day}.npz")
    if not (p.exists(v4fp) and p.exists(ppfp) and p.exists(dfp)):
        return None
    v4 = np.load(v4fp, allow_pickle=True); pp = np.load(ppfp, allow_pickle=True)
    dl = np.load(dfp, allow_pickle=True)
    tv = v4["timestamps"].astype(np.int64); tp = pp["timestamps"].astype(np.int64)
    # constant per-day offset (perp − v4)
    near = [int(tp[np.argmin(np.abs(tp - t))] - t) for t in tv[:min(50, len(tv))]]
    vals, cnts = np.unique(np.array(near), return_counts=True)
    off = int(vals[np.argmax(cnts)])
    target = tv + off
    idx = np.clip(np.searchsorted(tp, target), 0, len(tp) - 1)
    exact = (tp[idx] == target)
    # the dual cache kept exactly-matched v4 windows; align to it
    td = dl["timestamps"].astype(np.int64)
    keepv = np.isin(tv, td)
    tv = tv[keepv]; sret_win = v4["X"][keepv][:, :, J_RET1S].astype(np.float64)
    pidx = idx[keepv]; pret_win = pp["X"][pidx][:, :, J_RET1S].astype(np.float64)
    ts_sec = tv // US
    sec_s, sret = _reconstruct_persec(ts_sec, sret_win)
    sec_p, pret = _reconstruct_persec(ts_sec, pret_win)
    # basis per-window scalar (cross ch1 x_mpdev_diff) broadcast to its window secs
    basis_win = dl["X"][:, :, 64 + 1].astype(np.float64)   # x_mpdev_diff
    sec_b, basis = _reconstruct_persec(td // US, basis_win)
    return ts_sec, (sec_s, sret), (sec_p, pret), (sec_b, basis)


def _prev_day(day):
    return (dt.date.fromisoformat(day) - dt.timedelta(days=1)).isoformat()


def build_day(day, force=False):
    dfp = p.join(DUAL_DIR, f"{day}.npz")
    if not p.exists(dfp):
        return "missing"
    dl = dict(np.load(dfp, allow_pickle=True))
    if "X_long" in dl and not force:
        return "skip"
    cur = _series_for_day(day)
    if cur is None:
        return "no-series"
    ts_sec, S, P, B = cur
    prev = None
    pcur = _series_for_day(_prev_day(day))
    if pcur is not None:
        prev = (pcur[1], pcur[2], pcur[3])
    pred_secs = dl["timestamps"].astype(np.int64) // US
    Xlong = _build_long(S[0], S[1], P[0], P[1], B[0], B[1], pred_secs, prev)
    if Xlong.shape[0] != dl["X"].shape[0]:
        return f"len-mismatch {Xlong.shape[0]} vs {dl['X'].shape[0]}"
    dl["X_long"] = Xlong.astype(np.float32)
    dl["long_names"] = np.array(LONG_NAMES, dtype=object)
    np.savez(dfp, **dl)
    return "built"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", nargs="*", default=None)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    if args.all:
        days = sorted(f[:-4] for f in os.listdir(DUAL_DIR)
                      if f.endswith(".npz") and f[0].isdigit())
    else:
        days = args.days
    if not days:
        ap.error("pass --days or --all")
    print(f"[xlong] {len(days)} day(s)", flush=True)
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
    print(f"[xlong] DONE {counts} in {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
