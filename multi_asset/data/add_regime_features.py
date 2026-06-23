"""Add causal REGIME features to npz_v2arch (FRONT B lever 3) -> npz_v2arch_rg.

> **created:** 2026-06-23 | **Session:** v2-dual-source-arch (FRONT B regime) | **状态:** in-progress

MECHANISM (why this should help the 2026 CHOPPY regime)
-------------------------------------------------------
The deeper-perp dp32 lever decays on 2026 choppy (~0.025-0.03 vs strong 0.08): the model
can't tell which regime it is in, so a single static mapping under-fits the weak regime.
Causal regime indicators let the FiLM-multistage / regime_bias_head ADAPT the prediction
to the current regime (ADDITIVE bias, NOT gating — gating overfit in prior single-asset work).

3 causal regime features (per window, all <=t), appended to regime_prior (6 -> 9, d_prior=9):
  vol_pct       rolling realized-vol PERCENTILE (current 300s rvol vs trailing 4h distribution)
                -> "how volatile is now vs recently" (choppy = low pct)
  trend_strength rolling |cum return over 300s| / rolling rvol_300  -> trending vs mean-reverting
  basis_regime   rolling basis-vol percentile (basis turbulence vs trailing) from x_basis_bps
All computed from the reconstructed per-second series (same machinery as add_basis_dynamics),
leak-safe, then sampled at each window cutoff t. Non-destructive: writes npz_v2arch_rg.

OUTPUT: data/npz_v2arch_rg/<day>.npz = npz_v2arch copy with regime_prior extended 6->9.
Model: set d_prior=9 (regime_bias_head MLP auto-sizes). X/X_long/raw books unchanged.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import os.path as p

import numpy as np

_REPO = p.dirname(p.dirname(p.dirname(p.abspath(__file__))))
V2_DIR = p.join(_REPO, "data", "npz_v2arch")
OUT_DIR = p.join(_REPO, "data", "npz_v2arch_rg")
NPZV4_DIR = "/mnt/storage/private/work_hsy/quant_research/data/npz_v4"  # not used; v2arch self-contained
INPUT_LEN = 600
US = 1_000_000
EPS = 1e-8
# v2arch X column indices (88 = spot64 + ptrade16 + cross8); spot log_return_1s = 0
J_RET1S = 0
J_RVOL300 = 20            # realized_vol_300s in the spot-64 block
CROSS_BASIS = 64 + 1      # x_basis_bps (cross block starts at 64+16=80? -> see note)
REGIME_NAMES = ["rg_vol_pct", "rg_trend_strength", "rg_basis_regime"]


def _roll_pct(x, win):
    """Causal rolling percentile of x_i within the trailing `win` window (fraction <=x_i)."""
    n = x.size
    out = np.zeros(n)
    for i in range(n):
        lo = max(0, i - win + 1)
        w = x[lo:i + 1]
        out[i] = (w <= x[i]).mean() if w.size else 0.5
    return out


def _roll_std(x, win):
    n = x.size
    cs = np.concatenate([[0.0], np.cumsum(x)]); cs2 = np.concatenate([[0.0], np.cumsum(x * x)])
    i = np.arange(n); lo = np.maximum(0, i - win + 1); cnt = (i - lo + 1).astype(np.float64)
    m = (cs[i + 1] - cs[lo]) / cnt
    v = np.maximum((cs2[i + 1] - cs2[lo]) / cnt - m * m, 0.0)
    return np.sqrt(v)


def _roll_sum(x, win):
    n = x.size
    cs = np.concatenate([[0.0], np.cumsum(x)]); i = np.arange(n); lo = np.maximum(0, i - win + 1)
    return cs[i + 1] - cs[lo]


def _reconstruct(ts_sec, win_arr):
    N = ts_sec.size
    lo = int(ts_sec[0]) - (INPUT_LEN - 1); hi = int(ts_sec[-1]); T = hi - lo + 1
    grid = np.zeros(T); filled = np.zeros(T, bool); offs = np.arange(-(INPUT_LEN - 1), 1)
    for i in range(N):
        idx = int(ts_sec[i]) + offs - lo; good = (idx >= 0) & (idx < T)
        grid[idx[good]] = win_arr[i][good]; filled[idx[good]] = True
    base = lo + np.arange(T)
    return base[filled], grid[filled]


def _day_series(day):
    fp = p.join(V2_DIR, f"{day}.npz")
    if not p.exists(fp):
        return None
    d = np.load(fp, allow_pickle=True)
    ts = d["timestamps"].astype(np.int64); ts_sec = ts // US
    sret_w = d["X"][:, :, J_RET1S].astype(np.float64)
    # basis per-second: cross block x_basis_bps. cross starts after spot64+ptrade16 = col 80.
    cn = list(d["cross_names"]) if "cross_names" in d.files else []
    bcol = 80 + cn.index("x_basis_bps") if "x_basis_bps" in cn else None
    basis_w = d["X"][:, :, bcol].astype(np.float64) if bcol is not None else np.zeros_like(sret_w)
    secg, sret = _reconstruct(ts_sec, sret_w)
    _, basis = _reconstruct(ts_sec, basis_w)
    return ts_sec, secg, sret, basis


def _build_regime(secg, sret, basis, pred_secs):
    """3 causal regime features sampled at each window cutoff t."""
    rvol300 = _roll_std(sret, 300)
    cumret300 = _roll_sum(sret, 300)
    vol_pct = _roll_pct(rvol300, 4 * 3600)                       # vs trailing 4h
    trend = np.abs(cumret300) / (rvol300 * np.sqrt(300) + EPS)   # trend strength
    basis_vol = _roll_std(np.diff(np.concatenate([[basis[0]], basis])), 300)
    basis_regime = _roll_pct(basis_vol, 4 * 3600)
    per = np.column_stack([
        np.clip(vol_pct, 0, 1) - 0.5,
        np.clip(np.tanh(trend), -1, 1),
        np.clip(basis_regime, 0, 1) - 0.5,
    ])
    per = np.nan_to_num(per, nan=0.0, posinf=0.0, neginf=0.0)
    # sample <=t
    j = np.searchsorted(secg, pred_secs, side="right") - 1
    valid = j >= 0; j = np.clip(j, 0, secg.size - 1)
    out = per[j]; out[~valid] = 0.0
    return out.astype(np.float32)


def build_day(day, force=False):
    fp = p.join(V2_DIR, f"{day}.npz"); op = p.join(OUT_DIR, f"{day}.npz")
    if not p.exists(fp):
        return "missing"
    if p.exists(op) and not force:
        return "skip"
    d = dict(np.load(fp, allow_pickle=True))
    cur = _day_series(day)
    if cur is None:
        return "no-series"
    ts_sec, secg, sret, basis = cur
    # prior-day stitch for warm 4h percentile windows
    pday = (dt.date.fromisoformat(day) - dt.timedelta(days=1)).isoformat()
    pc = _day_series(pday)
    if pc is not None:
        _, ps, psr, pba = pc; keep = ps < secg[0]
        secg = np.concatenate([ps[keep], secg]); sret = np.concatenate([psr[keep], sret])
        basis = np.concatenate([pba[keep], basis])
    pred_secs = d["timestamps"].astype(np.int64) // US
    rg = _build_regime(secg, sret, basis, pred_secs)            # (N,3)
    if rg.shape[0] != d["regime_prior"].shape[0]:
        return f"len-mismatch {rg.shape[0]} vs {d['regime_prior'].shape[0]}"
    d["regime_prior"] = np.concatenate([d["regime_prior"].astype(np.float32), rg], axis=-1)  # 6->9
    d["regime_names_ext"] = np.array(REGIME_NAMES, dtype=object)
    os.makedirs(OUT_DIR, exist_ok=True)
    np.savez(op, **d)
    return "built"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", nargs="*", default=None)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    days = sorted(f[:-4] for f in os.listdir(V2_DIR) if f.endswith(".npz") and f[0].isdigit()) if args.all else args.days
    if not days:
        ap.error("pass --days or --all")
    import time
    print(f"[regime] {len(days)} day(s)", flush=True)
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
    print(f"[regime] DONE {counts} in {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
