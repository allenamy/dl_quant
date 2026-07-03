"""ALIGN-arm scorer — mechanical-inflation-aware (team-lead 2026-07-03).

The demeaned target y_align = y_600 - m has a BUILT-IN mechanical component: a model
that merely outputs ~ -m scores corr(-m, y_600-m) ~ sigma_m/sigma_{y_align} > 0 for
FREE, with ZERO raw-y value. So val metrics are inflated and val-selection may pick
the most-artifact epoch. This scorer judges the ALIGN prediction against RAW y_600
two ways (per-day-CLEAN), plus the output-vs-m scale check:

  RAW-A  corr(sigma*q50 + m, y_600)   -- the add-back caliber (anti-#18)
  RAW-B  corr(sigma*q50,     y_600)   -- prediction WITHOUT add-back; the -m artifact
                                         is ~uncorrelated with future y_600, so this
                                         ISOLATES the genuine 10-min residual alpha.
  sigma(sigma*q50) vs sigma_m         -- if the output is dominated by reproducing -m,
                                         the genuinely-predictive residual is tiny.

DECISIVE judge stays the deploy caliber (arm_pred_diagnostic.py: 1h-demean the
prediction) which is immune by construction. Baseline = the Run1 run for the month.

Usage: python multi_asset/model/score_align.py --arm-preds <align/fold_0/ema_test_preds.npz> \
         --norm <align/fold_0/norm_params.npz> --align-dir data/npz_v2arch_align \
         [--base-preds <d1_20XX_run1/fold_0/ema_test_preds.npz>]
"""
from __future__ import annotations

import argparse
import glob
import os
import numpy as np

HZ = 600_000_000
DAY = 86_400_000_000


def _pear(a, b):
    a = a - a.mean(); b = b - b.mean(); d = np.sqrt((a * a).sum() * (b * b).sum())
    return float((a * b).sum() / d) if d > 0 else 0.0


def _nonoverlap(ts):
    idx = np.argsort(ts, kind="stable"); keep = []; last = None
    for i in idx:
        if last is None or ts[i] - last >= HZ:
            keep.append(i); last = ts[i]
    return np.array(keep, dtype=int)


def _cd(sig, y, ts):
    day = ts // DAY; rs = []
    for d in np.unique(day):
        m = np.where(day == d)[0]; sub = m[_nonoverlap(ts[m])]
        if len(sub) > 20 and sig[sub].std() > 1e-12:
            rs.append(_pear(sig[sub], y[sub]))
    return (float(np.mean(rs)) if rs else float("nan")), len(rs)


def _clean_idx(ts):
    """Global per-day greedy non-overlap index set (the CLEAN caliber rows)."""
    day = ts // DAY; keep = []
    for d in np.unique(day):
        m = np.where(day == d)[0]; keep.append(m[_nonoverlap(ts[m])])
    return np.concatenate(keep) if keep else np.array([], dtype=int)


def _health(sig, y, ts):
    """Deploy-caliber health on the pooled CLEAN rows: β = cov(y,ŷ)/var(ŷ),
    σŷ/σy, and the POOLED (DENSE) Pearson. A per-day-cd positive but pooled/DENSE
    negative = spec-artifact sign-divergence (per-day-concentrated, non-aggregating).
    Gates: β∈[0.5,1.8], σ-ratio≥0.02, DENSE same-sign as per-day."""
    ci = _clean_idx(ts)
    if len(ci) < 20:
        return float("nan"), float("nan"), float("nan")
    q = sig[ci].astype(np.float64); yy = y[ci].astype(np.float64)
    qc = q - q.mean(); v = float((qc * qc).sum())
    beta = float((qc * (yy - yy.mean())).sum() / v) if v > 0 else float("nan")
    sr = float(q.std() / (yy.std() + 1e-12))
    dense = _pear(q, yy)
    return beta, sr, dense


def _demean_1h(pred, ts):
    """Causal 1h trailing demean of the PREDICTION: p_dm(t) = p(t) - mean(p, (t-3600s, t]).
    Removes any residual slow band so the deploy caliber can't be slow-band-inflated.
    Windowed within each UTC day (no cross-midnight leak)."""
    W = 3600 * 1_000_000  # 3600s in microseconds
    out = np.empty_like(pred, dtype=np.float64)
    day = ts // DAY
    for d in np.unique(day):
        idx = np.where(day == d)[0]
        order = idx[np.argsort(ts[idx], kind="stable")]
        tso = ts[order].astype(np.int64); po = pred[order].astype(np.float64)
        csum = np.concatenate([[0.0], np.cumsum(po)])
        lo = np.searchsorted(tso, tso - W, side="left")   # first t' > t-3600s
        hi = np.searchsorted(tso, tso, side="right")      # includes t itself
        cnt = np.maximum(hi - lo, 1)
        mean = (csum[hi] - csum[lo]) / cnt
        out[order] = po - mean
    return out


def load_preds(p):
    z = np.load(p, allow_pickle=True); pr = z["predictions"]
    q = (pr[:, 1] if pr.ndim == 2 else pr).astype(np.float64)
    ts = z["timestamps"].astype(np.int64)
    mask = z["mask"].astype(bool) if "mask" in z.files else np.ones(len(q), bool)
    return q, ts, mask


def sidecar_map(align_dir, days):
    """ts -> (m, y_raw) over the given day set."""
    T, M, Y = [], [], []
    for d in days:
        f = os.path.join(align_dir, f"{d}.npz")
        if not os.path.exists(f):
            continue
        z = np.load(f, allow_pickle=True)
        T.append(z["timestamps"].astype(np.int64)); M.append(z["m"].astype(np.float64)); Y.append(z["y_raw"].astype(np.float64))
    T = np.concatenate(T); M = np.concatenate(M); Y = np.concatenate(Y)
    order = np.argsort(T); return T[order], M[order], Y[order]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm-preds", required=True)
    ap.add_argument("--norm", required=True)
    ap.add_argument("--align-dir", default="data/npz_v2arch_align")
    ap.add_argument("--base-preds")
    a = ap.parse_args()

    q, ts, mask = load_preds(a.arm_preds)
    nz = np.load(a.norm); sigma = float(nz["y_sigma"])
    # match sidecar m / y_raw by timestamp over the whole cache (test days subset)
    all_days = [os.path.basename(f)[:-4] for f in sorted(glob.glob(f"{a.align_dir}/*.npz"))]
    ST, SM, SY = sidecar_map(a.align_dir, all_days)
    pos = np.searchsorted(ST, ts)
    ok = (pos < len(ST)) & (ST[np.clip(pos, 0, len(ST) - 1)] == ts)
    if not ok.all():
        print(f"[score_align] WARN {int((~ok).sum())}/{len(ts)} ts unmatched in sidecar")
    m = SM[np.clip(pos, 0, len(ST) - 1)]; y_raw = SY[np.clip(pos, 0, len(ST) - 1)]
    keep = mask & ok
    q, ts, m, y_raw = q[keep], ts[keep], m[keep], y_raw[keep]

    pred = sigma * q                                    # denormalised prediction (up to global median)
    cdA, nd = _cd(pred + m, y_raw, ts)                  # RAW-A: add-back caliber
    cdB, _ = _cd(pred, y_raw, ts)                       # RAW-B: artifact-free residual alpha
    pred_dm = _demean_1h(pred, ts)
    cdD, _ = _cd(pred_dm, y_raw, ts)                     # DEPLOY: 1h-demean the pred, vs raw y (slow-band-immune)
    betaD, srD, denseD = _health(pred_dm, y_raw, ts)    # deploy-caliber health (β band + σ-ratio + DENSE-sign gates)
    sig_out = float(pred.std()); sig_m = float(m.std())
    print(f"==== ALIGN {os.path.basename(os.path.dirname(os.path.dirname(a.arm_preds)))} vs RAW y_600 (days={nd}) ====")
    print(f"  RAW-A  corr(sigma*q50 + m,       y)  cd-CLEAN = {cdA:+.4f}   (add-back / anti-#18)")
    print(f"  RAW-B  corr(sigma*q50,           y)  cd-CLEAN = {cdB:+.4f}   (artifact-free residual alpha)")
    print(f"  DEPLOY corr(1h-demean(sigma*q50),y)  cd-CLEAN = {cdD:+.4f}   DENSE = {denseD:+.4f}   (decisive; slow-band-immune)")
    signdiv = (cdD > 0) != (denseD > 0)
    gate = "OK" if (0.5 <= betaD <= 1.8 and srD >= 0.02 and not signdiv) else "HEALTH-FLAG"
    flag = "  <== per-day/DENSE SIGN-DIVERGENCE (spec-artifact pattern)" if signdiv else ""
    print(f"  DEPLOY health: beta = {betaD:+.3f} (band [0.5,1.8])   sigma_hat/sigma_y = {srD:.3f} (>=0.02)   -> {gate}{flag}")
    print(f"  sigma(sigma*q50) = {sig_out:.5f}   sigma_m = {sig_m:.5f}   ratio out/m = {sig_out/max(sig_m,1e-12):.2f}")
    if a.base_preds and os.path.exists(a.base_preds):
        qb, tb, mb = load_preds(a.base_preds)
        posb = np.searchsorted(ST, tb); okb = (posb < len(ST)) & (ST[np.clip(posb, 0, len(ST)-1)] == tb)
        yb = SY[np.clip(posb, 0, len(ST)-1)]; kb = mb & okb
        pb = sigma * qb[kb]
        pb_dm = _demean_1h(pb, tb[kb])
        cdbase, _ = _cd(pb, yb[kb], tb[kb])              # Run1 raw caliber (no m; Run1 predicts raw y)
        cdbD, _ = _cd(pb_dm, yb[kb], tb[kb])             # Run1 deploy (same 1h-demean operator)
        betabD, srbD, densebD = _health(pb_dm, yb[kb], tb[kb])
        print(f"  BASELINE RAW    corr(sigma*q50, y)          cd-CLEAN = {cdbase:+.4f}")
        print(f"  BASELINE DEPLOY corr(1h-demean(sigma*q50),y) cd-CLEAN = {cdbD:+.4f} DENSE={densebD:+.4f} beta={betabD:+.3f} sr={srbD:.3f}")
        print(f"  -> RAW-B(align)-Run1raw = {cdB - cdbase:+.4f}   DEPLOY(align)-Run1deploy = {cdD - cdbD:+.4f}")
    print("DONE_SCORE_ALIGN.")


if __name__ == "__main__":
    main()
