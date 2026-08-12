#!/usr/bin/env python3
"""Phase C comprehensive backtest — V4+XGB ensemble.

Executes the Phase C evaluation plan described in
`docs/superpowers/specs/2026-04-18-phase-c-backtest-design.md`.

Stages:
  1. Load ensemble predictions (from scripts/ensemble_v4_xgb.py output)
  2. Run backtest under 3 τ regimes (always-trade, in-sample τ*, walk-forward τ*)
  3. 7 metric categories + bootstrap CIs
  4. 4 stress scenarios
  5. Generate ~20 figures + report
"""
from __future__ import annotations

import argparse
import json
import pathlib
from typing import Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr

import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from src.evaluation.backtest_engine import (
    CostModel, ExecutionConfig, BacktestResult,
    run_backtest, calibrate_tau_on_val, block_bootstrap_metrics,
)

plt.rcParams.update({
    "figure.dpi": 100, "savefig.dpi": 140, "savefig.bbox": "tight",
    "font.size": 10, "axes.grid": True, "grid.alpha": 0.3,
})

SAMPLE_INTERVAL_SEC = 60  # NPZ stride=60


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_ensemble_folds(
    ensemble_dir: pathlib.Path,
    baseline_dir: pathlib.Path,
    folds: List[int],
) -> Dict[int, Dict]:
    """Load ensemble predictions + XGB norm_y_sigma for bps conversion."""
    out = {}
    for f in folds:
        e = np.load(str(ensemble_dir / f"fold_{f}.npz"))
        xgb = np.load(str(baseline_dir / f"fold_{f}_XGBoost_preds.npz"))

        # Ensemble signal (z-scored, in target z-score space)
        signal = e["predictions"].astype(np.float64)
        targets_z = e["targets"].astype(np.float64)
        mask = e["mask"].astype(bool)
        timestamps = e["timestamps"].astype(np.int64)

        # V4 quantiles for confidence computation
        v4_q10 = e["v4_q10"].astype(np.float64)
        v4_q50 = e["v4_q50"].astype(np.float64)
        v4_q90 = e["v4_q90"].astype(np.float64)

        # Convert z-score targets → bps
        # norm_y_sigma is the train-set MAD sigma used for z-scoring
        norm_y_sigma = float(xgb["norm_y_sigma"])
        returns_bps = targets_z * norm_y_sigma * 1e4

        # Confidence: V4's IQR-normalized |q50|
        iqr = np.maximum(v4_q90 - v4_q10, 1e-8)
        confidence = np.abs(v4_q50) / iqr

        out[f] = {
            "signal": signal,
            "returns_bps": returns_bps,
            "mask": mask,
            "timestamps": timestamps,
            "confidence": confidence,
            "v4_q10": v4_q10, "v4_q50": v4_q50, "v4_q90": v4_q90,
            "norm_y_sigma": norm_y_sigma,
        }
    return out


# ---------------------------------------------------------------------------
# Main driver
# ---------------------------------------------------------------------------

def run_phase_c(
    ensemble_dir: pathlib.Path,
    baseline_dir: pathlib.Path,
    output_dir: pathlib.Path,
    folds: List[int] = [0, 1, 2],
) -> Dict:
    """Full Phase C pipeline. Returns metrics dict."""
    output_dir.mkdir(parents=True, exist_ok=True)
    fig_dir = output_dir / "figures"; fig_dir.mkdir(exist_ok=True)
    tables_dir = output_dir / "tables"; tables_dir.mkdir(exist_ok=True)

    data = load_ensemble_folds(ensemble_dir, baseline_dir, folds)
    # VERIFIED Binance Futures regular-user fees: maker 0.02%, taker 0.05%
    cost_model = CostModel.binance_regular()
    cost_model_bnb = CostModel.binance_bnb_discount()

    # ---------------------------------------------------------------------
    # Stage 2a: 3 backtest regimes per fold
    # ---------------------------------------------------------------------
    results = {"per_fold": {}, "pooled": {}}

    # Walk-forward τ*: calibrate on fold 0, apply to folds 1+2
    tau_wf_map = {}
    if 0 in data:
        d0 = data[0]
        tau_wf, sweep0 = calibrate_tau_on_val(
            d0["signal"], d0["returns_bps"], d0["mask"],
            val_confidence=d0["confidence"],
            sample_interval_sec=SAMPLE_INTERVAL_SEC,
            cost_model=cost_model,
        )
        tau_wf_map[0] = 0.0  # fold 0 has no prior data — use always-trade
        for f in folds[1:]:
            tau_wf_map[f] = tau_wf
        print(f"[phase_c] Walk-forward τ* (from fold 0 test): {tau_wf:.4f}")
    else:
        for f in folds: tau_wf_map[f] = 0.0

    for f in folds:
        d = data[f]
        fold_out = {}

        # Regime 1: τ=0 always trade (honest baseline)
        r_always = run_backtest(
            signal=d["signal"], returns_bps=d["returns_bps"], mask=d["mask"],
            confidence=d["confidence"], sample_interval_sec=SAMPLE_INTERVAL_SEC,
            cost_model=cost_model,
            exec_cfg=ExecutionConfig(position_mode="always_on"),
        )
        fold_out["always_trade"] = _result_to_dict(r_always)

        # Regime 2: τ*-in-sample (upper bound; clearly labeled as optimistic)
        tau_in, sweep = calibrate_tau_on_val(
            d["signal"], d["returns_bps"], d["mask"],
            val_confidence=d["confidence"],
            sample_interval_sec=SAMPLE_INTERVAL_SEC,
            cost_model=cost_model,
        )
        r_in = run_backtest(
            signal=d["signal"], returns_bps=d["returns_bps"], mask=d["mask"],
            confidence=d["confidence"], sample_interval_sec=SAMPLE_INTERVAL_SEC,
            cost_model=cost_model,
            exec_cfg=ExecutionConfig(position_mode="confidence_gated", tau=tau_in),
        )
        fold_out["tau_in_sample"] = _result_to_dict(r_in, tau=tau_in)
        fold_out["tau_sweep"] = sweep

        # Regime 3: τ walk-forward (proper, no lookahead for folds 1+2)
        tau_wf_fold = tau_wf_map[f]
        r_wf = run_backtest(
            signal=d["signal"], returns_bps=d["returns_bps"], mask=d["mask"],
            confidence=d["confidence"], sample_interval_sec=SAMPLE_INTERVAL_SEC,
            cost_model=cost_model,
            exec_cfg=ExecutionConfig(position_mode="confidence_gated", tau=tau_wf_fold),
        )
        fold_out["tau_walk_forward"] = _result_to_dict(r_wf, tau=tau_wf_fold)

        results["per_fold"][f] = fold_out
        print(f"[phase_c] Fold {f}: always_trade Sharpe={r_always.sharpe_ann:.2f}, "
              f"τ*-IS Sharpe={r_in.sharpe_ann:.2f} (τ={tau_in:.3f}), "
              f"τ*-WF Sharpe={r_wf.sharpe_ann:.2f} (τ={tau_wf_fold:.3f})")

    # Pooled across folds
    pooled_results = _pooled_backtest(data, folds, cost_model, tau_wf_map)
    results["pooled"] = pooled_results

    # ---------------------------------------------------------------------
    # Bootstrap CIs (on pooled walk-forward)
    # ---------------------------------------------------------------------
    pooled_net = pooled_results["tau_walk_forward"]["net_series"]
    pooled_mask = np.ones(len(pooled_net), dtype=bool)
    ci = block_bootstrap_metrics(
        pooled_net, pooled_mask, SAMPLE_INTERVAL_SEC,
        block_len=60, n_resample=1000,
    )
    results["bootstrap_ci"] = ci
    print(f"[phase_c] Bootstrap CIs: Sharpe {ci.get('sharpe_ann', ('nan',)*3)}")

    # ---------------------------------------------------------------------
    # Stage 3: 7 metric categories
    # ---------------------------------------------------------------------
    results["categories"] = _compute_all_metrics(data, pooled_results, SAMPLE_INTERVAL_SEC)

    # ---------------------------------------------------------------------
    # Stage 4: 4 stress scenarios
    # ---------------------------------------------------------------------
    results["stress_tests"] = _run_stress_tests(data, folds, cost_model, tau_wf_map)

    # ---------------------------------------------------------------------
    # Generate figures
    # ---------------------------------------------------------------------
    _generate_figures(data, results, pooled_results, fig_dir)

    # ---------------------------------------------------------------------
    # Save outputs
    # ---------------------------------------------------------------------
    _save_summary_tables(results, tables_dir)

    with open(output_dir / "metrics.json", "w") as fp:
        json.dump(_json_safe(results), fp, indent=2, default=float)

    # Generate report
    _write_report(results, output_dir)

    print(f"\n✓ Phase C complete. See {output_dir}/REPORT.md")
    return results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _result_to_dict(r: BacktestResult, tau: Optional[float] = None) -> Dict:
    d = {
        "gross_pnl_bps": r.gross_pnl_bps,
        "cost_bps": r.cost_bps,
        "net_pnl_bps": r.net_pnl_bps,
        "trade_rate": r.trade_rate,
        "sharpe_ann": r.sharpe_ann,
        "sortino_ann": r.sortino_ann,
        "max_dd_bps": r.max_dd_bps,
        "calmar": r.calmar,
        "cvar_95_bps": r.cvar_95,
        "win_rate": r.win_rate,
        "turnover": r.turnover,
    }
    if tau is not None: d["tau"] = tau
    return d


def _pooled_backtest(
    data: Dict, folds: List[int], cost_model: CostModel, tau_wf_map: Dict
) -> Dict:
    """Run backtest on concatenated test sets."""
    all_signal, all_ret, all_mask, all_conf, all_ts = [], [], [], [], []
    all_positions_wf = []
    for f in folds:
        d = data[f]
        all_signal.append(d["signal"]); all_ret.append(d["returns_bps"])
        all_mask.append(d["mask"]); all_conf.append(d["confidence"])
        all_ts.append(d["timestamps"])

    signal = np.concatenate(all_signal)
    returns = np.concatenate(all_ret)
    mask = np.concatenate(all_mask)
    conf = np.concatenate(all_conf)
    ts = np.concatenate(all_ts)

    # Always-trade pooled
    r_always = run_backtest(
        signal=signal, returns_bps=returns, mask=mask,
        confidence=conf, sample_interval_sec=SAMPLE_INTERVAL_SEC,
        cost_model=cost_model, exec_cfg=ExecutionConfig(position_mode="always_on"),
    )

    # τ-walk-forward — use fold-specific τ
    pos_wf = np.zeros(len(signal), dtype=np.float32)
    trade_wf = np.zeros(len(signal), dtype=np.int8)
    offset = 0
    for f in folds:
        d = data[f]
        n = len(d["signal"])
        tau = tau_wf_map[f]
        take = d["mask"] & (d["confidence"] >= tau)
        pos_wf[offset:offset+n][take] = np.sign(d["signal"])[take]
        trade_wf[offset:offset+n][take] = 1
        offset += n

    # Run full backtest with per-fold τ applied
    from src.evaluation.backtest_engine import _per_sample_pnl
    sig_delay_steps = 1
    net_wf, cost_wf = _per_sample_pnl(pos_wf, returns, trade_wf, cost_model, sig_delay_steps)
    # Apply funding
    funding_per = cost_model.funding_rate_bps_per_day * SAMPLE_INTERVAL_SEC / 86400.0
    net_wf = net_wf - np.abs(pos_wf) * funding_per

    from src.evaluation.backtest_engine import _sharpe_ann, _sortino_ann
    sharpe_wf = _sharpe_ann(net_wf[mask], SAMPLE_INTERVAL_SEC, lags=5)
    sortino_wf = _sortino_ann(net_wf[mask], SAMPLE_INTERVAL_SEC)
    gross_wf = float(np.sum(pos_wf * returns * mask))
    net_total_wf = float(np.sum(net_wf * mask))
    total_cost_wf = gross_wf - net_total_wf
    trade_rate_wf = float(np.mean(trade_wf))
    eq = np.cumsum(net_wf * mask)
    peak = np.maximum.accumulate(eq) if len(eq) > 0 else eq
    dd_wf = eq - peak
    max_dd_wf = float(dd_wf.min()) if len(dd_wf) > 0 else 0.0
    calmar_wf = net_total_wf / abs(max_dd_wf) if max_dd_wf < 0 else float("inf")
    traded = net_wf[trade_wf.astype(bool)]
    cvar_wf = float(np.percentile(traded, 5)) if len(traded) > 0 else 0.0
    win_wf = float((traded > 0).mean()) if len(traded) > 0 else 0.0
    turnover_wf = float(np.mean(np.abs(np.diff(pos_wf, prepend=0))))

    return {
        "always_trade": _result_to_dict(r_always),
        "tau_walk_forward": {
            "gross_pnl_bps": gross_wf,
            "cost_bps": total_cost_wf,
            "net_pnl_bps": net_total_wf,
            "trade_rate": trade_rate_wf,
            "sharpe_ann": sharpe_wf,
            "sortino_ann": sortino_wf,
            "max_dd_bps": max_dd_wf,
            "calmar": calmar_wf,
            "cvar_95_bps": cvar_wf,
            "win_rate": win_wf,
            "turnover": turnover_wf,
            "net_series": net_wf.astype(np.float32),
            "position_series": pos_wf,
            "equity_series": eq.astype(np.float32),
            "timestamps": ts,
            "mask": mask,
            "returns_bps": returns,
            "signal": signal,
            "confidence": conf,
        },
    }


def _compute_all_metrics(data: Dict, pooled: Dict, sample_int: int) -> Dict:
    """Compute metrics across 7 categories."""
    wf = pooled["tau_walk_forward"]
    signal = wf["signal"]; returns = wf["returns_bps"]
    mask = wf["mask"]; conf = wf["confidence"]
    net = wf["net_series"]; pos = wf["position_series"]; ts = wf["timestamps"]

    p_v = signal[mask]; y_v = returns[mask]

    # Category 1: Signal quality
    cat1 = {
        "pooled_pearson": float(pearsonr(p_v, y_v)[0]),
        "pooled_spearman": float(spearmanr(p_v, y_v)[0]),
        "direction_accuracy": float((np.sign(p_v) == np.sign(y_v)).mean()),
        "ic_stability_days": _daily_ic_stats(signal, returns, mask, ts),
    }

    # Category 2: Execution
    cat2 = {
        "total_samples": int(mask.sum()),
        "trade_rate_wf": wf["trade_rate"],
        "total_cost_bps": wf["cost_bps"],
        "avg_cost_per_trade_bps": wf["cost_bps"] / max(1, np.sum(np.abs(np.diff(pos, prepend=0))>0)),
        "turnover": wf["turnover"],
    }

    # Category 3: Returns
    cat3 = {
        "gross_pnl_bps": wf["gross_pnl_bps"],
        "net_pnl_bps": wf["net_pnl_bps"],
        "sharpe_ann": wf["sharpe_ann"],
        "sortino_ann": wf["sortino_ann"],
        "calmar": wf["calmar"],
    }

    # Category 4: Risk
    cat4 = {
        "max_drawdown_bps": wf["max_dd_bps"],
        "cvar_95_bps": wf["cvar_95_bps"],
        "win_rate": wf["win_rate"],
        "loss_rate": 1 - wf["win_rate"],
    }

    # Category 5: Regime breakdown
    cat5 = _regime_analysis(signal, returns, mask, ts, sample_int)

    # Category 6: Position
    cat6 = {
        "avg_position": float(np.abs(pos).mean()),
        "max_position": float(np.abs(pos).max()),
        "position_std": float(pos.std()),
    }

    # Category 7: Statistical — see bootstrap_ci (already computed separately)
    return {"cat1_signal": cat1, "cat2_execution": cat2, "cat3_returns": cat3,
            "cat4_risk": cat4, "cat5_regime": cat5, "cat6_position": cat6}


def _daily_ic_stats(signal, returns, mask, ts, min_n_per_day=60) -> Dict:
    """Per-day IC."""
    ts_sec = (ts // 1_000_000) if np.median(ts) > 1e14 else ts
    day_idx = (ts_sec // 86400).astype(int)
    p = signal[mask]; y = returns[mask]; d = day_idx[mask]
    ics = []
    for day in np.unique(d):
        sel = d == day
        if sel.sum() < min_n_per_day: continue
        try:
            ic = float(spearmanr(p[sel], y[sel])[0])
            if np.isfinite(ic): ics.append(ic)
        except Exception: pass
    if not ics: return {"n_days": 0, "mean_ic": float("nan"), "ic_ir": float("nan"), "pct_positive": 0.0}
    ics = np.array(ics)
    return {
        "n_days": len(ics),
        "mean_ic": float(ics.mean()),
        "std_ic": float(ics.std()),
        "ic_ir": float(ics.mean() / (ics.std() + 1e-12)),
        "pct_positive": float((ics > 0).mean()),
    }


def _regime_analysis(signal, returns, mask, ts, sample_int) -> Dict:
    """IC by hour, month, vol regime."""
    ts_sec = (ts // 1_000_000) if np.median(ts) > 1e14 else ts
    hour = ((ts_sec % 86400) // 3600).astype(int)

    p = signal[mask]; y = returns[mask]; h = hour[mask]; t = ts_sec[mask]

    # Hour
    hour_ic = {}
    for hr in range(24):
        sel = h == hr
        if sel.sum() < 30: continue
        hour_ic[str(hr)] = float(spearmanr(p[sel], y[sel])[0])

    # Month
    dt = pd.to_datetime(t, unit="s")
    month = dt.strftime("%Y-%m")
    df = pd.DataFrame({"p": p, "y": y, "m": month})
    monthly = df.groupby("m").apply(
        lambda g: float(spearmanr(g["p"], g["y"])[0]) if len(g) > 50 else float("nan")
    ).to_dict()

    # Vol regime — proxy from |y| rolling window
    abs_y = np.abs(y)
    vol_marker = pd.Series(abs_y).rolling(60, min_periods=10).mean().shift(1).bfill().fillna(0).values
    v_lo, v_hi = np.nanpercentile(vol_marker, [33.33, 66.67])
    vol_ic = {
        "low_vol": float(spearmanr(p[vol_marker < v_lo], y[vol_marker < v_lo])[0]) if (vol_marker < v_lo).sum() > 30 else float("nan"),
        "mid_vol": float(spearmanr(p[(vol_marker >= v_lo) & (vol_marker < v_hi)], y[(vol_marker >= v_lo) & (vol_marker < v_hi)])[0]) if ((vol_marker >= v_lo) & (vol_marker < v_hi)).sum() > 30 else float("nan"),
        "high_vol": float(spearmanr(p[vol_marker >= v_hi], y[vol_marker >= v_hi])[0]) if (vol_marker >= v_hi).sum() > 30 else float("nan"),
    }

    return {"hour_ic": hour_ic, "monthly_ic": monthly, "vol_regime_ic": vol_ic}


def _run_stress_tests(data: Dict, folds: List[int], cost_model: CostModel, tau_wf_map: Dict) -> Dict:
    """Isolate stress scenarios from test data."""
    stress = {}

    # Collect all data for stress analysis
    all_ret, all_ts, all_sig, all_mask, all_conf = [], [], [], [], []
    all_taus = []
    for f in folds:
        d = data[f]
        all_ret.append(d["returns_bps"]); all_ts.append(d["timestamps"])
        all_sig.append(d["signal"]); all_mask.append(d["mask"]); all_conf.append(d["confidence"])
        all_taus.extend([tau_wf_map[f]] * len(d["signal"]))

    ret = np.concatenate(all_ret); ts = np.concatenate(all_ts)
    sig = np.concatenate(all_sig); msk = np.concatenate(all_mask); conf = np.concatenate(all_conf)
    taus = np.array(all_taus)

    ts_sec = (ts // 1_000_000) if np.median(ts) > 1e14 else ts
    dt = pd.to_datetime(ts_sec, unit="s")

    # Scenario 1: highest-vol month
    abs_y = np.abs(ret)
    month_str = dt.strftime("%Y-%m")
    month_vol = pd.DataFrame({"v": abs_y, "m": month_str}).groupby("m")["v"].mean()
    if len(month_vol) > 0:
        max_month = month_vol.idxmax()
        sel = (month_str == max_month)
        stress["highest_vol_month"] = _stress_backtest(
            sig[sel], ret[sel], msk[sel], conf[sel], taus[sel], cost_model,
            label=f"highest-vol month ({max_month})",
        )

    # Scenario 2: Asia handoff 03-06 UTC
    hour = ((ts_sec % 86400) // 3600).astype(int)
    asia_sel = (hour >= 3) & (hour < 6)
    stress["asia_handoff_03_06_utc"] = _stress_backtest(
        sig[asia_sel], ret[asia_sel], msk[asia_sel], conf[asia_sel], taus[asia_sel], cost_model,
        label="Asia handoff 03-06 UTC",
    )

    # Scenario 3: regime transition days (|cumulative 4h return| crosses)
    # Simpler: days with sign flip in rolling 4h trend
    trend_4h = pd.Series(ret).rolling(4 * 60, min_periods=30).mean().shift(1).fillna(0).values
    sign_flip = (np.sign(trend_4h[:-1]) != np.sign(trend_4h[1:]))
    # Mark samples within 30 min of a sign flip
    flip_nearby = np.zeros(len(ret), dtype=bool)
    for i in np.where(sign_flip)[0]:
        flip_nearby[max(0, i - 30):min(len(ret), i + 30)] = True
    stress["regime_transition"] = _stress_backtest(
        sig[flip_nearby], ret[flip_nearby], msk[flip_nearby], conf[flip_nearby],
        taus[flip_nearby], cost_model, label="regime transition windows",
    )

    # Scenario 4: top 1% tail return events (large |return| samples)
    abs_ret_thresh = np.percentile(abs_y[msk], 99)
    tail_sel = abs_y >= abs_ret_thresh
    stress["tail_events_top_1pct"] = _stress_backtest(
        sig[tail_sel], ret[tail_sel], msk[tail_sel], conf[tail_sel], taus[tail_sel], cost_model,
        label="top 1% tail return events",
    )

    return stress


def _stress_backtest(sig, ret, msk, conf, taus, cost_model, label=""):
    """Run backtest on stress subset using τ-walk-forward."""
    if len(sig) < 50:
        return {"label": label, "n": len(sig), "skipped": "too few samples"}
    # Use mean τ across this subset (taus is per-sample due to fold structure)
    tau_avg = float(np.mean(taus))
    cfg = ExecutionConfig(position_mode="confidence_gated", tau=tau_avg)
    r = run_backtest(
        signal=sig, returns_bps=ret, mask=msk, confidence=conf,
        sample_interval_sec=SAMPLE_INTERVAL_SEC, cost_model=cost_model, exec_cfg=cfg,
    )
    d = _result_to_dict(r, tau=tau_avg)
    d["n"] = int(len(sig))
    d["label"] = label
    return d


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------

def _generate_figures(data: Dict, results: Dict, pooled: Dict, fig_dir: pathlib.Path):
    """Generate all plots."""
    wf = pooled["tau_walk_forward"]
    net = wf["net_series"]; pos = wf["position_series"]; ts = wf["timestamps"]; mask = wf["mask"]

    # 01: Signal quality (Pearson/Spearman bar)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    cat1 = results["categories"]["cat1_signal"]
    xs = ["Pearson", "Spearman", "DirAcc"]
    vals = [cat1["pooled_pearson"], cat1["pooled_spearman"], cat1["direction_accuracy"]]
    ax.bar(xs, vals, color=["#4C72B0", "#DD8452", "#55A868"])
    ax.axhline(0.12, color="red", linestyle="--", alpha=0.5, label="spec bar 0.12")
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_title(f"V4+XGB Ensemble — Signal Quality (Pooled 3-fold)")
    ax.legend()
    for i, v in enumerate(vals): ax.text(i, v, f"{v:.4f}", ha="center", va="bottom")
    plt.savefig(fig_dir / "01_signal_quality.png"); plt.close()

    # 02: Daily IC over time
    fig, ax = plt.subplots(figsize=(12, 4.5))
    ts_sec = (ts // 1_000_000) if np.median(ts) > 1e14 else ts
    day = (ts_sec // 86400).astype(int)
    sig = wf["signal"]; ret = wf["returns_bps"]
    df = pd.DataFrame({"p": sig[mask], "y": ret[mask], "d": day[mask]})
    daily = df.groupby("d").apply(lambda g: spearmanr(g["p"], g["y"])[0] if len(g) > 60 else np.nan).dropna()
    days_rel = daily.index.values - daily.index.values.min()
    ax.plot(days_rel, daily.values, color="#4C72B0", alpha=0.4, linewidth=1, label="daily IC")
    if len(daily) >= 7:
        ax.plot(days_rel, pd.Series(daily.values).rolling(7, center=True).mean(), "k--", linewidth=2, label="7d rolling")
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_xlabel("Days into test period"); ax.set_ylabel("Spearman IC")
    ax.set_title("Daily Spearman IC (V4+XGB Ensemble, Walk-forward)")
    ax.legend()
    plt.savefig(fig_dir / "02_daily_ic.png"); plt.close()

    # 03: Equity curve (cumulative net P&L)
    fig, ax = plt.subplots(figsize=(12, 5))
    equity = wf["equity_series"]
    ax.plot(equity, color="#4C72B0", linewidth=1.5)
    ax.fill_between(range(len(equity)), equity, 0,
                     where=(equity >= 0), color="#4C72B0", alpha=0.1, interpolate=True)
    ax.fill_between(range(len(equity)), equity, 0,
                     where=(equity < 0), color="#C44E52", alpha=0.1, interpolate=True)
    ax.set_title(f"Cumulative Net P&L (bps) — Pooled 3-fold Walk-forward\nTotal: {wf['net_pnl_bps']:.1f} bps / {len(equity):,} samples")
    ax.set_xlabel("Sample (time-ordered)"); ax.set_ylabel("Cumulative Net P&L (bps)")
    ax.axhline(0, color="black", linewidth=0.5)
    plt.savefig(fig_dir / "03_equity_curve.png"); plt.close()

    # 04: Drawdown underwater
    fig, ax = plt.subplots(figsize=(12, 4))
    peak = np.maximum.accumulate(equity)
    dd = equity - peak
    ax.fill_between(range(len(dd)), dd, 0, color="#C44E52", alpha=0.5)
    ax.set_title(f"Drawdown — Max DD: {dd.min():.1f} bps")
    ax.set_xlabel("Sample"); ax.set_ylabel("Drawdown from peak (bps)")
    plt.savefig(fig_dir / "04_drawdown.png"); plt.close()

    # 05: Returns distribution
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
    net_filt = net[mask]
    axes[0].hist(net_filt, bins=100, color="#4C72B0", alpha=0.7)
    axes[0].axvline(0, color="black", linewidth=0.5)
    axes[0].axvline(np.percentile(net_filt, 5), color="red", linestyle="--", label="5th pct (CVaR 95%)")
    axes[0].axvline(np.percentile(net_filt, 95), color="green", linestyle="--", label="95th pct")
    axes[0].set_title("Per-sample Net P&L Distribution (bps)")
    axes[0].legend(); axes[0].set_xlabel("Net P&L (bps)"); axes[0].set_ylabel("Count")

    # Q-Q plot for normality check
    from scipy.stats import probplot
    probplot(net_filt[np.abs(net_filt) < np.percentile(np.abs(net_filt), 99)], plot=axes[1])
    axes[1].set_title("Q-Q Plot (excl. top 1% tails)")
    plt.tight_layout()
    plt.savefig(fig_dir / "05_returns_dist.png"); plt.close()

    # 06: Regime heatmap (hour × vol regime)
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
    hour_ic = results["categories"]["cat5_regime"]["hour_ic"]
    hours = sorted([int(k) for k in hour_ic.keys()])
    vals = [hour_ic[str(h)] for h in hours]
    axes[0].bar(hours, vals, color=["#4C72B0" if v > 0 else "#C44E52" for v in vals])
    axes[0].axhline(0, color="black", linewidth=0.5)
    axes[0].set_xlabel("Hour (UTC)"); axes[0].set_ylabel("Spearman IC")
    axes[0].set_title("IC by Hour of Day")

    # Monthly IC bar
    monthly = results["categories"]["cat5_regime"]["monthly_ic"]
    months = sorted(monthly.keys())
    mvals = [monthly[m] for m in months]
    axes[1].bar(range(len(months)), mvals, color=["#4C72B0" if v > 0 else "#C44E52" for v in mvals])
    axes[1].axhline(0, color="black", linewidth=0.5)
    axes[1].set_xticks(range(len(months))); axes[1].set_xticklabels(months, rotation=45)
    axes[1].set_title("IC by Month")
    plt.tight_layout()
    plt.savefig(fig_dir / "06_regime_breakdown.png"); plt.close()

    # 07: Position sizing over time
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(pos, color="#4C72B0", linewidth=0.3, alpha=0.6)
    ax.set_title(f"Position Over Time (mean |pos|={np.abs(pos).mean():.3f}, turnover={wf['turnover']:.3f})")
    ax.set_xlabel("Sample"); ax.set_ylabel("Position (-1 to +1)")
    plt.savefig(fig_dir / "07_position_over_time.png"); plt.close()

    # 08: Confidence calibration
    fig, ax = plt.subplots(figsize=(9, 5))
    conf = wf["confidence"][mask]
    signal = wf["signal"][mask]
    ret = wf["returns_bps"][mask]
    # Sort into 10 confidence buckets
    bucket_edges = np.quantile(conf, np.linspace(0, 1, 11))
    bucket_ic = []
    bucket_labels = []
    for i in range(10):
        sel = (conf >= bucket_edges[i]) & (conf < bucket_edges[i+1])
        if sel.sum() >= 30:
            ic = spearmanr(signal[sel], ret[sel])[0]
            bucket_ic.append(ic)
            bucket_labels.append(f"D{i+1}")
    ax.bar(range(len(bucket_ic)), bucket_ic, color="#4C72B0")
    ax.set_xticks(range(len(bucket_ic))); ax.set_xticklabels(bucket_labels)
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_title("IC by Confidence Decile (D1 = lowest, D10 = highest)")
    ax.set_ylabel("Spearman IC")
    plt.savefig(fig_dir / "08_confidence_calibration.png"); plt.close()

    # 09: τ sweep curve
    fig, ax = plt.subplots(figsize=(10, 5))
    sweep = results["per_fold"][0]["tau_sweep"]
    df_sweep = pd.DataFrame(sweep)
    ax.plot(df_sweep["trade_rate"], df_sweep["sharpe_ann"], marker="o", color="#4C72B0")
    idx_max = df_sweep["sharpe_ann"].idxmax()
    ax.scatter([df_sweep.iloc[idx_max]["trade_rate"]], [df_sweep.iloc[idx_max]["sharpe_ann"]],
                s=200, color="red", zorder=5, label=f"τ*={df_sweep.iloc[idx_max]['tau']:.3f}")
    ax.set_xlabel("Trade Rate"); ax.set_ylabel("Annualized Sharpe")
    ax.set_title(f"Fold 0 — τ Sweep (used to set walk-forward τ* for folds 1, 2)")
    ax.axhline(0, color="black", linewidth=0.5); ax.legend()
    plt.savefig(fig_dir / "09_tau_sweep.png"); plt.close()

    # 10: Bootstrap Sharpe CI
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ci = results.get("bootstrap_ci", {})
    if "sharpe_ann" in ci:
        mean_sh, lo_sh, hi_sh = ci["sharpe_ann"]
        ax.barh([0], [mean_sh], xerr=[[mean_sh - lo_sh], [hi_sh - mean_sh]],
                 height=0.5, capsize=10, color="#4C72B0")
        ax.set_yticks([0]); ax.set_yticklabels(["Sharpe (HAC)"])
        ax.set_title(f"Bootstrap 95% CI: Sharpe = {mean_sh:.2f} [{lo_sh:.2f}, {hi_sh:.2f}]")
        ax.axvline(0, color="black", linewidth=0.5)
    plt.savefig(fig_dir / "10_bootstrap_sharpe.png"); plt.close()

    # 11: Rolling Sharpe (60-sample rolling window)
    fig, ax = plt.subplots(figsize=(12, 4))
    net_mask = net[mask]
    rolling_mean = pd.Series(net_mask).rolling(1000, min_periods=100).mean()
    rolling_std = pd.Series(net_mask).rolling(1000, min_periods=100).std()
    rolling_sharpe = rolling_mean / (rolling_std + 1e-12) * np.sqrt(31_536_000 / 60)
    ax.plot(rolling_sharpe, color="#4C72B0")
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_title("Rolling 1000-sample Sharpe (annualized)")
    plt.savefig(fig_dir / "11_rolling_sharpe.png"); plt.close()

    # 12: Monthly P&L bar
    fig, ax = plt.subplots(figsize=(12, 4.5))
    dt_full = pd.to_datetime(ts_sec[mask], unit="s")
    monthly_pnl = pd.DataFrame({"pnl": net_mask, "m": dt_full.strftime("%Y-%m")}).groupby("m")["pnl"].sum()
    months = sorted(monthly_pnl.index.tolist())
    pnls = [monthly_pnl[m] for m in months]
    ax.bar(range(len(months)), pnls, color=["#4C72B0" if p > 0 else "#C44E52" for p in pnls])
    ax.set_xticks(range(len(months))); ax.set_xticklabels(months, rotation=45)
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_ylabel("Net P&L (bps)"); ax.set_title("Monthly Net P&L (Walk-forward τ)")
    plt.savefig(fig_dir / "12_monthly_pnl.png"); plt.close()

    # 13-16: Stress scenarios
    stress = results["stress_tests"]
    scenarios = list(stress.keys())
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    for i, key in enumerate(scenarios[:4]):
        ax = axes[i // 2][i % 2]
        s = stress[key]
        if "skipped" in s or s.get("n", 0) < 50:
            ax.text(0.5, 0.5, f"{s.get('label', key)}\n{s.get('skipped', 'too few')}", ha="center", va="center", transform=ax.transAxes)
            continue
        metrics = ["sharpe_ann", "max_dd_bps", "trade_rate", "win_rate"]
        vals = [s.get(m, 0) for m in metrics]
        ax.bar(range(len(metrics)), vals, color=["#4C72B0", "#C44E52", "#55A868", "#DD8452"])
        ax.set_xticks(range(len(metrics))); ax.set_xticklabels(["Sharpe", "MaxDD", "TradeRate", "WinRate"], rotation=20)
        ax.axhline(0, color="black", linewidth=0.5)
        ax.set_title(f"{s.get('label', key)}\nN={s.get('n', 0):,}")
    plt.tight_layout()
    plt.savefig(fig_dir / "13_stress_scenarios.png"); plt.close()

    # 17: Per-fold contribution to P&L
    fig, ax = plt.subplots(figsize=(10, 4.5))
    fold_pnl = []
    fold_labels = []
    offset = 0
    for f in sorted(pooled["tau_walk_forward"].get("mask", mask).dtype.kind if False else [0, 1, 2]):
        d = data[f]
        n = len(d["signal"])
        fold_net = net[offset:offset+n]
        fold_mask = mask[offset:offset+n]
        fold_pnl.append(float((fold_net * fold_mask).sum()))
        fold_labels.append(f"Fold {f}")
        offset += n
    ax.bar(fold_labels, fold_pnl, color=["#4C72B0", "#55A868", "#DD8452"])
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_title("Net P&L by Fold")
    for i, v in enumerate(fold_pnl): ax.text(i, v, f"{v:.1f}", ha="center", va="bottom" if v > 0 else "top")
    ax.set_ylabel("Net P&L (bps)")
    plt.savefig(fig_dir / "17_pnl_by_fold.png"); plt.close()

    # 18: Ensemble vs single-model comparison (IC bar)
    fig, ax = plt.subplots(figsize=(9, 5))
    ens_sum = json.load(open("experiments/phase_c/ensemble_preds/ensemble_summary.json")) if (pathlib.Path("experiments/phase_c/ensemble_preds/ensemble_summary.json")).exists() else None
    if ens_sum and "pooled" in ens_sum:
        p = ens_sum["pooled"]
        models = ["V4", "XGBoost", "EW_ensemble"]
        pears = [p[m]["pearson"] for m in models]
        spears = [p[m]["spearman"] for m in models]
        x = np.arange(len(models)); width = 0.35
        ax.bar(x - width/2, pears, width, label="Pearson", color="#4C72B0")
        ax.bar(x + width/2, spears, width, label="Spearman", color="#DD8452")
        ax.set_xticks(x); ax.set_xticklabels(models)
        ax.axhline(0.12, color="red", linestyle="--", alpha=0.5, label="spec bar")
        ax.set_ylabel("IC"); ax.set_title("V4 vs XGBoost vs Ensemble — IC Comparison")
        ax.legend()
    plt.savefig(fig_dir / "18_ensemble_vs_single.png"); plt.close()

    # 19: Win/Loss distribution by day
    fig, ax = plt.subplots(figsize=(10, 5))
    daily_pnl = pd.DataFrame({"pnl": net_mask, "d": day[mask]}).groupby("d")["pnl"].sum()
    ax.hist(daily_pnl, bins=50, color="#4C72B0", alpha=0.7)
    ax.axvline(0, color="black", linewidth=0.5)
    ax.set_title(f"Daily Net P&L Distribution (N={len(daily_pnl)} days, mean={daily_pnl.mean():.2f} bps)")
    ax.set_xlabel("Daily Net P&L (bps)"); ax.set_ylabel("Count")
    plt.savefig(fig_dir / "19_daily_pnl_dist.png"); plt.close()

    # 20: τ sensitivity across folds
    fig, ax = plt.subplots(figsize=(10, 5))
    colors = ["#4C72B0", "#DD8452", "#55A868"]
    for i, f in enumerate([0, 1, 2]):
        if f not in results["per_fold"]: continue
        sweep = results["per_fold"][f].get("tau_sweep", [])
        if sweep:
            df_s = pd.DataFrame(sweep)
            ax.plot(df_s["trade_rate"], df_s["sharpe_ann"], marker="o", label=f"Fold {f}", color=colors[i])
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_xlabel("Trade Rate"); ax.set_ylabel("Sharpe (ann)")
    ax.set_title("τ Sensitivity Across Folds")
    ax.legend()
    plt.savefig(fig_dir / "20_tau_sensitivity.png"); plt.close()


def _save_summary_tables(results: Dict, tables_dir: pathlib.Path):
    """CSV summary tables."""
    # Per-fold summary
    rows = []
    for fold, fold_d in results["per_fold"].items():
        for regime in ["always_trade", "tau_in_sample", "tau_walk_forward"]:
            r = fold_d[regime]
            row = {"fold": fold, "regime": regime}
            for k in ["sharpe_ann", "sortino_ann", "net_pnl_bps", "max_dd_bps",
                     "trade_rate", "win_rate", "calmar", "turnover", "tau"]:
                row[k] = r.get(k, np.nan)
            rows.append(row)
    pd.DataFrame(rows).to_csv(tables_dir / "per_fold_summary.csv", index=False)

    # Stress tests
    stress_rows = []
    for k, s in results["stress_tests"].items():
        row = {"scenario": k, "label": s.get("label", "")}
        for metric in ["sharpe_ann", "net_pnl_bps", "max_dd_bps", "trade_rate", "win_rate", "n"]:
            row[metric] = s.get(metric, np.nan)
        stress_rows.append(row)
    pd.DataFrame(stress_rows).to_csv(tables_dir / "stress_scenarios.csv", index=False)


def _write_report(results: Dict, output_dir: pathlib.Path):
    """Markdown report."""
    lines = []
    lines.append("# Phase C — V4+XGBoost Ensemble Comprehensive Backtest Report\n")
    lines.append("> **Generated by** `scripts/phase_c_eval.py` · **Spec:** `docs/superpowers/specs/2026-04-18-phase-c-backtest-design.md`\n")

    # Executive summary
    lines.append("## Executive Summary\n")
    wf = results["pooled"]["tau_walk_forward"]
    always = results["pooled"]["always_trade"]
    ci = results.get("bootstrap_ci", {})
    sh_ci = ci.get("sharpe_ann", ("nan", "nan", "nan"))
    dd_ci = ci.get("max_dd_bps", ("nan", "nan", "nan"))

    lines.append("| Regime | Sharpe (ann) | Net P&L (bps) | Max DD (bps) | Trade Rate | Win Rate |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    lines.append(f"| Always trade | {always['sharpe_ann']:.2f} | {always['net_pnl_bps']:.1f} | {always['max_dd_bps']:.1f} | 100% | {always['win_rate']:.2%} |")
    lines.append(f"| τ walk-forward | {wf['sharpe_ann']:.2f} | {wf['net_pnl_bps']:.1f} | {wf['max_dd_bps']:.1f} | {wf['trade_rate']:.2%} | {wf['win_rate']:.2%} |")
    lines.append("")

    if isinstance(sh_ci[0], (int, float)) and np.isfinite(sh_ci[0]):
        lines.append(f"**Bootstrap 95% CI:** Sharpe [{sh_ci[1]:.2f}, {sh_ci[2]:.2f}], Max DD [{dd_ci[1]:.1f}, {dd_ci[2]:.1f}] bps\n")

    # 7 metric categories
    lines.append("## Metric Categories\n")

    # Cat 1
    lines.append("### 1. Signal Quality\n")
    cat1 = results["categories"]["cat1_signal"]
    lines.append(f"- **Pooled Pearson**: {cat1['pooled_pearson']:.4f}")
    lines.append(f"- **Pooled Spearman**: {cat1['pooled_spearman']:.4f}")
    lines.append(f"- **Direction Accuracy**: {cat1['direction_accuracy']:.4f}")
    lines.append(f"- **Daily IC-IR**: {cat1['ic_stability_days'].get('ic_ir', 'n/a'):.3f} ({cat1['ic_stability_days'].get('n_days', 0)} days)")
    lines.append(f"- **% Days Positive**: {cat1['ic_stability_days'].get('pct_positive', 0):.1%}\n")
    lines.append("![Signal Quality](figures/01_signal_quality.png)\n")
    lines.append("![Daily IC](figures/02_daily_ic.png)\n")

    lines.append("### 2-3. Execution & Returns\n")
    cat2 = results["categories"]["cat2_execution"]; cat3 = results["categories"]["cat3_returns"]
    lines.append(f"- **Trade rate (walk-forward)**: {cat2['trade_rate_wf']:.2%}")
    lines.append(f"- **Gross P&L**: {cat3['gross_pnl_bps']:.1f} bps; **Net**: {cat3['net_pnl_bps']:.1f}; **Cost**: {cat2['total_cost_bps']:.1f}")
    lines.append(f"- **Sharpe**: {cat3['sharpe_ann']:.2f}, **Sortino**: {cat3['sortino_ann']:.2f}, **Calmar**: {cat3['calmar']:.2f}\n")
    lines.append("![Equity](figures/03_equity_curve.png)\n")
    lines.append("![Drawdown](figures/04_drawdown.png)\n")
    lines.append("![Returns dist](figures/05_returns_dist.png)\n")

    lines.append("### 4. Risk\n")
    cat4 = results["categories"]["cat4_risk"]
    lines.append(f"- **Max DD**: {cat4['max_drawdown_bps']:.1f} bps")
    lines.append(f"- **CVaR-95%**: {cat4['cvar_95_bps']:.2f} bps")
    lines.append(f"- **Win rate**: {cat4['win_rate']:.2%}\n")

    lines.append("### 5. Regime Breakdown\n")
    lines.append("![Regime](figures/06_regime_breakdown.png)\n")

    lines.append("### 6. Position Management\n")
    cat6 = results["categories"]["cat6_position"]
    lines.append(f"- **Avg |position|**: {cat6['avg_position']:.3f}")
    lines.append(f"- **Turnover**: {wf['turnover']:.3f}\n")
    lines.append("![Position](figures/07_position_over_time.png)\n")
    lines.append("![Calibration](figures/08_confidence_calibration.png)\n")

    lines.append("### 7. Statistical Robustness\n")
    if "sharpe_ann" in ci:
        sh = ci["sharpe_ann"]
        lines.append(f"- **Sharpe bootstrap CI**: [{sh[1]:.2f}, {sh[2]:.2f}] (mean {sh[0]:.2f})")
    lines.append("![Bootstrap Sharpe](figures/10_bootstrap_sharpe.png)\n")
    lines.append("![Rolling Sharpe](figures/11_rolling_sharpe.png)\n")
    lines.append("![Tau sweep](figures/09_tau_sweep.png)\n")
    lines.append("![Tau sensitivity](figures/20_tau_sensitivity.png)\n")

    # Stress tests
    lines.append("## Stress Scenarios\n")
    lines.append("![Stress scenarios](figures/13_stress_scenarios.png)\n")
    lines.append("| Scenario | N | Sharpe | Net P&L (bps) | Max DD (bps) | Win Rate |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for k, s in results["stress_tests"].items():
        if "skipped" in s: continue
        lines.append(f"| {s.get('label', k)} | {s.get('n', 0):,} | {s.get('sharpe_ann', 0):.2f} | {s.get('net_pnl_bps', 0):.1f} | {s.get('max_dd_bps', 0):.1f} | {s.get('win_rate', 0):.2%} |")
    lines.append("")

    # Ensemble comparison
    lines.append("## Ensemble vs Single-Model Comparison\n")
    lines.append("![Ensemble vs single](figures/18_ensemble_vs_single.png)\n")
    lines.append("![PnL by fold](figures/17_pnl_by_fold.png)\n")
    lines.append("![Monthly PnL](figures/12_monthly_pnl.png)\n")
    lines.append("![Daily PnL dist](figures/19_daily_pnl_dist.png)\n")

    with open(output_dir / "REPORT.md", "w") as f:
        f.write("\n".join(lines))


def _json_safe(obj):
    """Recursively convert numpy types to Python native for JSON."""
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(x) for x in obj]
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.integer,)): return int(obj)
    if isinstance(obj, (np.floating,)): return float(obj)
    if isinstance(obj, np.bool_): return bool(obj)
    return obj


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ensemble-dir", type=pathlib.Path,
                        default=pathlib.Path("experiments/phase_c/ensemble_preds"))
    parser.add_argument("--baseline-dir", type=pathlib.Path,
                        default=pathlib.Path("experiments/baselines_v4_matched_preds"))
    parser.add_argument("--output-dir", type=pathlib.Path,
                        default=pathlib.Path("experiments/phase_c"))
    parser.add_argument("--folds", type=int, nargs="+", default=[0, 1, 2])
    args = parser.parse_args()

    run_phase_c(args.ensemble_dir, args.baseline_dir, args.output_dir, args.folds)


if __name__ == "__main__":
    main()
