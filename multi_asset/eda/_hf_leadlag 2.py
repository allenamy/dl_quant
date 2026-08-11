#!/usr/bin/env python
"""HF BTC->alt lead-lag measurement (closing-the-loop number, not a gate).

Per alt j != BTC, strictly causal:
  Predictor : BTC past log-return over w in {30, 60, 300}s ending at t.
  Targets   : alt j forward log-return over h in {180, 600}s from t,
              plus beta-neutral version (minus beta_j * BTC forward h-return,
              beta_j from prior-day 1s OLS of alt returns on BTC returns).
  Stats     : Spearman pooled across ~30 stratified days (stride 10s),
              cross-alt median + top-3 mean; AND the incremental (partial)
              Spearman after regressing out alt j's OWN past w-return,
              compared to the own-history baseline Spearman.

Data: share 1s bars via multi_asset/data/bar_loader.py path schema (mid only;
mid is not a QTY column so no scaling applies — semantics identical to
load_day_panel, just skips the 56 unused columns for speed).

Output: /tmp/hf_leadlag.json
Run:    CPU only, designed for < 40 min wall.
"""
from __future__ import annotations

import json
import os.path as p
import sys
import time
from datetime import date, timedelta

import h5py
import numpy as np

sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
from multi_asset.data.bar_loader import _BAR_PATH, _day_file  # noqa: E402

try:
    from scipy.stats import rankdata as _rankdata
except Exception:  # pragma: no cover - fallback if scipy missing
    def _rankdata(a):
        order = np.argsort(a, kind="mergesort")
        ranks = np.empty(len(a), dtype=np.float64)
        ranks[order] = np.arange(1, len(a) + 1, dtype=np.float64)
        return ranks  # ordinal ranks; ties ~never occur in continuous returns

SYMS = ["bnfbtc", "bnfeth", "bnfsol", "bnfbnb", "bnfxrp", "bnfdog", "bnfada",
        "bnflink", "bnfbch", "bnftrx", "bnfltc", "bnfdot", "bnffil", "bnfetc"]
BTC = "bnfbtc"
ALTS = [s for s in SYMS if s != BTC]
WS = [30, 60, 300]
HS = [180, 600]
STRIDE = 10
MAX_W = max(WS)
MAX_H = max(HS)
OUT_JSON = "/tmp/hf_leadlag.json"


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def date_int(d: date) -> int:
    return d.year * 10000 + d.month * 100 + d.day


def day_exists(di: int) -> bool:
    return p.exists(_day_file(_BAR_PATH, di))


def pick_days() -> list[tuple[int, int]]:
    """~30 (prior_day, day) pairs stratified across 2024-06..2025-09.

    Two anchor days per month (10th, 22nd); walk forward up to 6 days if the
    file (or its prior day, needed for beta) is missing.
    """
    months = []
    y, m = 2024, 6
    while (y, m) <= (2025, 9):
        months.append((y, m))
        m += 1
        if m == 13:
            y, m = y + 1, 1
    pairs = []
    for (y, m) in months:
        for anchor in (10, 22):
            for k in range(6):
                d = date(y, m, anchor) + timedelta(days=k)
                di, pi = date_int(d), date_int(d - timedelta(days=1))
                if day_exists(di) and day_exists(pi):
                    pairs.append((pi, di))
                    break
    # dedupe on sample day, keep order
    seen, out = set(), []
    for pi, di in pairs:
        if di not in seen:
            seen.add(di)
            out.append((pi, di))
    return out


def load_log_mids(di: int) -> dict[str, np.ndarray] | None:
    """log(mid) per symbol for one day; None if any symbol missing."""
    path = _day_file(_BAR_PATH, di)
    out = {}
    with h5py.File(path, "r") as f:
        for s in SYMS:
            key = f"mid_{s}"
            if key not in f:
                return None
            mid = f[key][:].astype(np.float64)
            lm = np.full_like(mid, np.nan)
            ok = np.isfinite(mid) & (mid > 0)
            lm[ok] = np.log(mid[ok])
            out[s] = lm
    return out


def prior_day_betas(logm_prior: dict[str, np.ndarray]) -> dict[str, float]:
    """beta_j from prior-day 1s OLS: r_alt = beta * r_btc."""
    rb = np.diff(logm_prior[BTC])
    betas = {}
    for s in ALTS:
        ra = np.diff(logm_prior[s])
        mask = np.isfinite(rb) & np.isfinite(ra)
        if mask.sum() < 1000:
            betas[s] = 0.0
            continue
        x, yv = rb[mask], ra[mask]
        vx = np.dot(x, x) - len(x) * x.mean() ** 2
        betas[s] = 0.0 if vx <= 0 else float(
            (np.dot(x, yv) - len(x) * x.mean() * yv.mean()) / vx)
    return betas


def pearson(a: np.ndarray, b: np.ndarray) -> float:
    a = a - a.mean()
    b = b - b.mean()
    den = np.sqrt(np.dot(a, a) * np.dot(b, b))
    return 0.0 if den == 0 else float(np.dot(a, b) / den)


def spearman(a: np.ndarray, b: np.ndarray) -> float:
    return pearson(_rankdata(a), _rankdata(b))


def partial_spearman(x: np.ndarray, y: np.ndarray, z: np.ndarray) -> float:
    """Spearman partial corr of (x, y) controlling z: rank-transform all,
    residualize x and y on z by OLS, Pearson of residuals."""
    xr, yr, zr = _rankdata(x), _rankdata(y), _rankdata(z)
    zr = zr - zr.mean()
    vz = np.dot(zr, zr)
    if vz == 0:
        return spearman(x, y)
    xr = xr - xr.mean() - (np.dot(xr - xr.mean(), zr) / vz) * zr
    yr = yr - yr.mean() - (np.dot(yr - yr.mean(), zr) / vz) * zr
    return pearson(xr, yr)


def main() -> None:
    t0 = time.time()
    pairs = pick_days()
    log(f"selected {len(pairs)} sample days: {[d for _, d in pairs]}")

    # acc[alt][(w,h)] -> dict of lists of per-day arrays
    acc = {s: {(w, h): {"x": [], "own": [], "y": [], "yneu": []}
               for w in WS for h in HS} for s in ALTS}

    for i, (pi, di) in enumerate(pairs):
        logm_prior = load_log_mids(pi)
        logm = load_log_mids(di)
        if logm_prior is None or logm is None:
            log(f"day {di}: missing symbol dataset, skipped")
            continue
        betas = prior_day_betas(logm_prior)
        lb = logm[BTC]
        T = len(lb)
        t_idx = np.arange(MAX_W, T - MAX_H, STRIDE)
        x_w = {w: lb[t_idx] - lb[t_idx - w] for w in WS}          # causal: ends at t
        btc_fwd = {h: lb[t_idx + h] - lb[t_idx] for h in HS}
        for s in ALTS:
            la = logm[s]
            own_w = {w: la[t_idx] - la[t_idx - w] for w in WS}
            y_h = {h: la[t_idx + h] - la[t_idx] for h in HS}
            for w in WS:
                for h in HS:
                    yneu = y_h[h] - betas[s] * btc_fwd[h]
                    a = acc[s][(w, h)]
                    a["x"].append(x_w[w])
                    a["own"].append(own_w[w])
                    a["y"].append(y_h[h])
                    a["yneu"].append(yneu)
        log(f"[{i + 1}/{len(pairs)}] day {di} done "
            f"(beta_eth={betas.get('bnfeth', float('nan')):.3f}, "
            f"n_t={len(t_idx)})")

    cells = {}
    for w in WS:
        for h in HS:
            per_alt = {k: {} for k in
                       ("raw", "beta_neutral", "own_baseline",
                        "incr_raw", "incr_neutral")}
            n_samples = {}
            for s in ALTS:
                a = acc[s][(w, h)]
                if not a["x"]:
                    continue
                x = np.concatenate(a["x"])
                own = np.concatenate(a["own"])
                yv = np.concatenate(a["y"])
                yn = np.concatenate(a["yneu"])
                mask = (np.isfinite(x) & np.isfinite(own)
                        & np.isfinite(yv) & np.isfinite(yn))
                x, own, yv, yn = x[mask], own[mask], yv[mask], yn[mask]
                n_samples[s] = int(len(x))
                if len(x) < 5000:
                    continue
                per_alt["raw"][s] = spearman(x, yv)
                per_alt["beta_neutral"][s] = spearman(x, yn)
                per_alt["own_baseline"][s] = spearman(own, yv)
                per_alt["incr_raw"][s] = partial_spearman(x, yv, own)
                per_alt["incr_neutral"][s] = partial_spearman(x, yn, own)
            cell = {"n_samples": n_samples}
            for k, d in per_alt.items():
                vals = sorted(d.values(), reverse=True)
                cell[k] = {
                    "per_alt": {s: round(v, 5) for s, v in d.items()},
                    "median": round(float(np.median(list(d.values()))), 5)
                              if d else None,
                    "top3_mean": round(float(np.mean(vals[:3])), 5)
                                 if len(vals) >= 3 else None,
                    "top3_alts": [s for s, _ in sorted(
                        d.items(), key=lambda kv: -kv[1])[:3]],
                }
            cells[f"w{w}_h{h}"] = cell
            log(f"cell w={w} h={h}: raw_med={cell['raw']['median']} "
                f"neu_med={cell['beta_neutral']['median']} "
                f"own_med={cell['own_baseline']['median']} "
                f"incr_raw_med={cell['incr_raw']['median']} "
                f"incr_neu_med={cell['incr_neutral']['median']}")

    result = {
        "meta": {
            "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "days": [d for _, d in pairs],
            "n_days": len(pairs),
            "stride_s": STRIDE,
            "windows_s": WS,
            "horizons_s": HS,
            "alts": ALTS,
            "method": ("pooled Spearman per alt across days; incremental = "
                       "partial Spearman controlling alt's own past w-return "
                       "(rank-OLS residualization); beta from prior-day 1s OLS"),
            "runtime_s": round(time.time() - t0, 1),
        },
        "cells": cells,
    }
    with open(OUT_JSON, "w") as f:
        json.dump(result, f, indent=2)
    log(f"DONE in {result['meta']['runtime_s']}s -> {OUT_JSON}")


if __name__ == "__main__":
    main()
