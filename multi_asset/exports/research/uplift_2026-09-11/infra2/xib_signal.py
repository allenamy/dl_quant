"""INFRA2 BITWISE SIGNAL BUILDER for the FEMAT fund-leg injection path (round 2, 2026-09-11).

THE DEFECT (measured, diag_parity.py): the round-1 builder ranked with np.argsort(np.argsort(v))
= ORDINAL ranks. The device (w10_health.py xz(), lines 122-125) ranks with scipy.stats.rankdata
= AVERAGE ranks. f_fund_ema_v1 has ties on 9031 of 10039 panel rows (98820 excess tied cells), so
the two engines disagree on ~90% of rows; re-ranking an ORDINAL vector does NOT reproduce re-ranking
the raw values. Every one of the 8580 differing anchors sits on a tied panel row. float32 storage
contributed ZERO rank collisions (that hypothesis is refuted, not assumed).

THE FIX: rank with the DEVICE'S OWN function. xz(xz(v)) == xz(v) bitwise, because rankdata depends
only on the order-and-ties structure, which xz preserves exactly. Storage is float64 so the npz round
trip is the identity (the device does np.asarray(mat, dtype=float)).
"""
import numpy as np
from scipy.stats import rankdata


def xz(v):
    """VERBATIM from w10_health.py lines 122-125 (the device's cross-sectional rank)."""
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    if ok.sum() >= 10: out[ok] = rankdata(v[ok]) / max(ok.sum() - 1, 1) - 0.5
    return out


def RZ(M, mask=None):
    """Row-wise device-identical rank. mask (bool, same shape) forces NaN where False."""
    M = np.asarray(M, float)
    if mask is not None: M = np.where(mask, M, np.nan)
    out = np.full(M.shape, np.nan)
    for i in range(M.shape[0]): out[i] = xz(M[i])
    return out


def blend(*parts):
    """sum(w_i * Z_i). NaN in ANY part -> NaN (a name must be scored on every component, so the
    finite mask of the blend equals the intersection; for the parity arm there is one part and the
    mask is therefore identical to the device's own)."""
    out = np.zeros(parts[0][1].shape); ok = np.ones(parts[0][1].shape, bool)
    for w, Z in parts:
        Z = np.asarray(Z, float)
        out = out + w * np.nan_to_num(Z, nan=0.0); ok &= np.isfinite(Z)
    return np.where(ok, out, np.nan)


def save(path, symbols, ts, mat):
    """float64 on disk: the device upcasts with np.asarray(..., dtype=float), so f64 in == f64 used."""
    np.savez(path, symbols=symbols, ts=np.asarray(ts, np.int64), mat=np.asarray(mat, np.float64))
    return path
