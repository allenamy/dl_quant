"""P1 inversion diagnosis: val_rankIC came out -0.23 (systematic inversion). Check the
smoothed-target wiring: (1) smoothed vs raw target correlation (should be +0.7-0.9),
(2) residualized-smoothed vs residualized-raw (the funding-orthogonalized loss target),
(3) target scale / resid_sigma (huber blew to 2.02). Reuses the exact trainer smoothing +
residual path.
Run: PYTHONPATH=. python multi_asset/eval/p1_smooth_diag.py
"""
from __future__ import annotations
import numpy as np
from scipy.stats import spearmanr
from multi_asset.data.seq_panel_dataset import SeqPanelData, SYMBOLS
from multi_asset.train.train_temporal_spatial import _time_ema_Y


def xsec_resid(Y, CL):
    """per-ts cross-sectional demean over valid clean assets -> residual (NaN elsewhere)."""
    R = np.full_like(Y, np.nan)
    for t in range(Y.shape[0]):
        v = CL[t] & np.isfinite(Y[t])
        if v.sum() >= 5:
            R[t, v] = Y[t, v] - Y[t, v].mean()
    return R


def main():
    data = SeqPanelData(target_horizon=3600)
    Yraw = data.Y.copy()
    Ysm = _time_ema_Y(Yraw, 20)
    CL = data.CL
    # sample clean rows to keep it quick
    clean_rows = np.where(CL.any(1))[0]
    print(f"panel T={Yraw.shape[0]} clean rows={len(clean_rows)}")

    # (1) smoothed vs raw — per-asset time-series + cross-sectional
    print("\n(1) SMOOTHED vs RAW target correlation (expect +0.7-0.9 if EMA is trailing-causal):")
    pa = []
    for si in range(len(SYMBOLS)):
        c = clean_rows
        m = np.isfinite(Yraw[c, si]) & np.isfinite(Ysm[c, si])
        if m.sum() > 100:
            pa.append(spearmanr(Yraw[c, si][m], Ysm[c, si][m])[0])
    print(f"  per-asset time-series Spearman(raw, smoothed): mean {np.mean(pa):+.3f}  range [{min(pa):+.2f},{max(pa):+.2f}]")
    xs = []
    for t in clean_rows[::7]:
        v = CL[t] & np.isfinite(Yraw[t]) & np.isfinite(Ysm[t])
        if v.sum() >= 5:
            xs.append(spearmanr(Yraw[t, v], Ysm[t, v])[0])
    print(f"  cross-sectional Spearman(raw, smoothed) per-ts: mean {np.nanmean(xs):+.3f}")

    # (2) residualized-smoothed vs residualized-raw (the loss target caliber)
    Rraw = xsec_resid(Yraw, CL); Rsm = xsec_resid(Ysm, CL)
    xs2 = []
    for t in clean_rows[::7]:
        v = CL[t] & np.isfinite(Rraw[t]) & np.isfinite(Rsm[t])
        if v.sum() >= 5:
            xs2.append(spearmanr(Rraw[t, v], Rsm[t, v])[0])
    print(f"\n(2) cross-sectional Spearman(resid-raw, resid-smoothed) per-ts: mean {np.nanmean(xs2):+.3f}")
    print("   (if NEGATIVE -> training on smoothed makes the model anti-correlated with raw = the inversion)")

    # (3) scale: MAD-sigma raw vs smoothed (huber blew up)
    def mad(x):
        x = x[np.isfinite(x)]
        return float(np.median(np.abs(x - np.median(x))) * 1.4826) if x.size else np.nan
    print(f"\n(3) resid MAD-sigma  raw={mad(Rraw):.5f}  smoothed={mad(Rsm):.5f}  "
          f"ratio={mad(Rraw)/mad(Rsm):.2f}x")
    print(f"   raw |resid| p99={np.nanpercentile(np.abs(Rraw),99):.5f}  "
          f"smoothed |resid| p99={np.nanpercentile(np.abs(Rsm),99):.5f}")


if __name__ == "__main__":
    main()
