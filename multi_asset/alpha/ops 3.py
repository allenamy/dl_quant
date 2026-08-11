#!/usr/bin/env python3
"""Operator toolkit for the Alpha-101 / GTJA-191 formula sweep (causal, panel = (nT, nS)).

> **created:** 2026-07-08 | **Session:** multi-asset-v2 phase-0b→A (0B) | **状态:** in-progress

All time-series ops act along axis 0 (time, 180s bars) per asset column and are STRICTLY CAUSAL
(trailing window ≤t; warmup → NaN). Cross-sectional ops act along axis 1 (assets) per timestamp.
Windows are in BARS; the formula layer passes hours×H (H=20 bars/hour) so every construct is SLOW
(≥1h) — we know sub-10min constructs die at 1h. Fast C backends: bottleneck (move_*) + pandas
rolling (corr/cov/rank). Cross-day-gap rolling contamination is ~0.21% (same as build_slow_factors).
"""
from __future__ import annotations
import numpy as np, pandas as pd, bottleneck as bn

H = 20  # 180s bars per hour


def _mc(d):
    return max(2, d // 2)


# ---- time-series (per asset, trailing d bars, causal) ----
def delay(A, d):
    out = np.full_like(A, np.nan)
    if d < len(A):
        out[d:] = A[:-d]
    return out


def delta(A, d):
    return A - delay(A, d)


def ts_sum(A, d):   return bn.move_sum(A, d, min_count=_mc(d), axis=0)
def ts_mean(A, d):  return bn.move_mean(A, d, min_count=_mc(d), axis=0)
def ts_std(A, d):   return bn.move_std(A, d, min_count=_mc(d), axis=0)
def ts_min(A, d):   return bn.move_min(A, d, min_count=_mc(d), axis=0)
def ts_max(A, d):   return bn.move_max(A, d, min_count=_mc(d), axis=0)
def ts_argmax(A, d): return bn.move_argmax(A, d, min_count=_mc(d), axis=0).astype(float)  # 0 = most recent bar
def ts_argmin(A, d): return bn.move_argmin(A, d, min_count=_mc(d), axis=0).astype(float)
def ts_rank(A, d):   return bn.move_rank(A, d, min_count=_mc(d), axis=0)                  # rank of last in window, [-1,1]


def product(A, d):
    return pd.DataFrame(A).rolling(d, min_periods=_mc(d)).apply(np.prod, raw=True).values


def decay_linear(A, d):
    """Linearly weighted trailing mean, most-recent weight = d (WorldQuant convention)."""
    w = np.arange(d, 0, -1, dtype=float); w /= w.sum()
    out = np.full_like(A, np.nan)
    Af = np.nan_to_num(A, nan=0.0)
    for j in range(A.shape[1]):
        c = np.convolve(Af[:, j], w, mode="full")[:len(A)]
        out[:, j] = c
    out[:d - 1] = np.nan
    return out


# ---- cross-sectional (per timestamp, across assets) ----
def rank(A):
    """Cross-sectional rank across assets per ts, pct in (0,1], NaN-safe."""
    return pd.DataFrame(A).rank(axis=1, pct=True).values


def scale(A, k=1.0):
    s = np.nansum(np.abs(A), axis=1, keepdims=True)
    return A * k / np.where(s > 0, s, np.nan)


def indneutralize(A, *_):
    """No industry field on 14 mega-caps → xsec-demean (best available neutralization)."""
    mu = np.nanmean(A, axis=1, keepdims=True)
    return A - mu


# ---- pairwise / elementwise ----
def correlation(A, B, d):
    return pd.DataFrame(A).rolling(d, min_periods=_mc(d)).corr(pd.DataFrame(B)).values


def covariance(A, B, d):
    return pd.DataFrame(A).rolling(d, min_periods=_mc(d)).cov(pd.DataFrame(B)).values


def sign(A):   return np.sign(A)
def log(A):    return np.log(np.where(A > 0, A, np.nan))
def absv(A):   return np.abs(A)
def signedpower(A, a): return np.sign(A) * np.abs(A) ** a
def mind(A, B): return np.minimum(A, B)
def maxd(A, B): return np.maximum(A, B)


def adv(vol, vwap, d):
    """Average dollar volume over d bars (the ADV{d} the formulas reference)."""
    return ts_mean(vol * vwap, d)
