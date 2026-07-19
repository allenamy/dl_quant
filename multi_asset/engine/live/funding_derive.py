"""Live shadow — derive funding_ema from premiumIndexKlines for the OPEN month.

> **创建:** 2026-07-19 JST | **Session:** fable multi-asset-v2 (0B live shadow) | **状态:** v1 | **作废条件:** funding_ema 口径变更, 或验证门 corr<0.95 触发降级

WHY: on the CDN the `fundingRate` archive is monthly-only — the current (open) month is absent
until it closes. The funding leg is 0.30 of the book, so a T+1 shadow can't wait ~30 days. Binance's
funding rate is itself computed FROM the premium index:
    funding_rate = avg(premium_index over the interval) + clamp(interest - avg_premium, ±0.05%)
so deriving it from premiumIndexKlines (daily-archived, T+1) is one step upstream of the same
information — not an ad-hoc approximation.

GATE (0C/lead pre-reg): before go-live, backtest the derivation on CLOSED months that have BOTH
archives; per-coin corr(derived funding_ema, real funding_ema) must be **>= 0.95** (funding_ema
caliber). When the monthly archive later publishes, auto-reconcile + alert. If the gate fails ->
degrade to the funding-leg-downweight fallback (RUNBOOK), NOT stale carry-forward.

The funding_ema recipe MUST match build_wide_panel.py exactly: EMA(span=round(24/interval_h),
adjust=False) of the settlement-time rate series, causal-ffilled to the hourly grid.
"""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

INTEREST = 0.0001      # 0.01% per 8h interval (USDT-margined default)
CLAMP = 0.0005         # ±0.05%
HOUR_MS = 3_600_000


def funding_settlement_times(t0_ms: int, t1_ms: int, interval_h: int = 8) -> np.ndarray:
    """UTC settlement stamps (…00/08/16 for 8h) covering [t0,t1]."""
    step = interval_h * HOUR_MS
    first = (t0_ms // step) * step
    return np.arange(first, t1_ms + step, step, dtype=np.int64)


def derive_funding_rate(premium_1h: pd.DataFrame, settle_ms: np.ndarray, interval_h: int = 8,
                        interest: float = INTEREST, clamp: float = CLAMP) -> np.ndarray:
    """funding rate at each settlement time = avg hourly premium-index close over the preceding
    interval window + clamp(interest - avg, ±clamp). premium_1h: [open_time_ms, close]."""
    p = premium_1h.dropna(subset=["close"]).sort_values("open_time_ms")
    t = p["open_time_ms"].to_numpy(np.int64)
    c = p["close"].to_numpy(np.float64)
    win = interval_h * HOUR_MS
    out = np.full(len(settle_ms), np.nan)
    for i, s in enumerate(settle_ms):
        m = (t > s - win) & (t <= s)                       # hourly closes in (s-interval, s]
        if m.any():
            avg_p = float(c[m].mean())
            out[i] = avg_p + float(np.clip(interest - avg_p, -clamp, clamp))
    return out


def funding_ema_on_grid(settle_ms: np.ndarray, rate: np.ndarray, grid_ms: np.ndarray,
                        interval_h: int = 8) -> np.ndarray:
    """EMA(span=round(24/interval_h), adjust=False) of the rate series, causal-ffilled to grid_ms
    — byte-for-byte the build_wide_panel.py FUND_EMA recipe."""
    ok = np.isfinite(rate)
    st, rt = settle_ms[ok], rate[ok]
    if len(rt) < 3:
        return np.full(len(grid_ms), np.nan)
    span = max(2, int(round(24.0 / max(interval_h, 1.0))))
    ema = pd.Series(rt).ewm(span=span, adjust=False).mean().to_numpy()
    idx = np.searchsorted(st, grid_ms, side="right") - 1
    out = np.full(len(grid_ms), np.nan)
    good = idx >= 0
    out[good] = ema[idx[good]]
    return out


def derive_funding_ema(premium_1h: pd.DataFrame, grid_ms: np.ndarray, interval_h: int = 8) -> np.ndarray:
    """Full derivation: premium index -> settlement-time rates -> funding_ema on grid_ms."""
    if premium_1h.empty:
        return np.full(len(grid_ms), np.nan)
    t = premium_1h["open_time_ms"].to_numpy(np.int64)
    settle = funding_settlement_times(int(t.min()), int(t.max()), interval_h)
    rate = derive_funding_rate(premium_1h, settle, interval_h)
    return funding_ema_on_grid(settle, rate, grid_ms, interval_h)


def real_funding_ema(funding_df: pd.DataFrame, grid_ms: np.ndarray) -> np.ndarray:
    """The panel's real funding_ema from a fundingRate archive frame (same recipe)."""
    if funding_df.empty or len(funding_df) < 3:
        return np.full(len(grid_ms), np.nan)
    fd = funding_df.sort_values("fundingTime_ms")
    ih = float(np.median(fd["funding_interval_h"].to_numpy())) if "funding_interval_h" in fd else 8.0
    settle = fd["fundingTime_ms"].to_numpy(np.int64)
    rate = pd.to_numeric(fd["fundingRate"], errors="coerce").to_numpy(np.float64)
    return funding_ema_on_grid(settle, rate, grid_ms, int(round(ih)))


def _hourly_grid(ym: str) -> np.ndarray:
    d0 = dt.datetime.strptime(ym, "%Y-%m").replace(tzinfo=dt.timezone.utc)
    d1 = (d0.replace(day=28) + dt.timedelta(days=10)).replace(day=1)
    t0 = int(d0.timestamp() * 1000); t1 = int(d1.timestamp() * 1000)
    return np.arange(t0, t1, HOUR_MS, dtype=np.int64)


def validate(source, syms, months, min_corr=0.95, min_abs_std=1e-9):
    """Per-coin corr(derived, real) funding_ema over CLOSED months. Returns a report dict + PASS."""
    per = []
    for sym in syms:
        cvals = []
        for ym in months:
            grid = _hourly_grid(ym)
            ym_d0 = dt.datetime.strptime(ym, "%Y-%m").date()
            ym_d1 = (ym_d0.replace(day=28) + dt.timedelta(days=10)).replace(day=1) - dt.timedelta(days=1)
            fund = source.funding(sym, ym_d0, ym_d1)
            prem = source.premium_index_1h(sym, ym_d0, ym_d1)
            if fund.empty or prem.empty:
                continue
            real = real_funding_ema(fund, grid)
            der = derive_funding_ema(prem, grid, interval_h=int(round(
                float(np.median(fund["funding_interval_h"].to_numpy())))) if "funding_interval_h" in fund else 8)
            ok = np.isfinite(real) & np.isfinite(der)
            if ok.sum() > 50 and real[ok].std() > min_abs_std and der[ok].std() > min_abs_std:
                c = float(np.corrcoef(real[ok], der[ok])[0, 1])
                mae = float(np.mean(np.abs(real[ok] - der[ok])))
                cvals.append((ym, c, mae))
        if cvals:
            cc = float(np.mean([c for _, c, _ in cvals]))
            mm = float(np.mean([m for _, _, m in cvals]))
            per.append(dict(sym=sym, corr=round(cc, 4), mae_bps=round(mm * 1e4, 3), n_months=len(cvals)))
    corrs = np.array([p["corr"] for p in per]) if per else np.array([])
    passed = bool(len(corrs) and np.median(corrs) >= min_corr and np.mean(corrs >= min_corr) >= 0.90)
    return dict(n_syms=len(per), median_corr=round(float(np.median(corrs)), 4) if len(corrs) else None,
                min_corr=round(float(corrs.min()), 4) if len(corrs) else None,
                frac_ge_gate=round(float(np.mean(corrs >= min_corr)), 3) if len(corrs) else None,
                gate=min_corr, passed=passed, per_coin=sorted(per, key=lambda x: x["corr"]))
