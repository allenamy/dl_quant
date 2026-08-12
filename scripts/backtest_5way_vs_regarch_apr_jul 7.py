"""Full backtest 2025-04-01 → 2025-07-29 for two candidates:
  (1) 5-way ensemble REG_arch+P3+A+V5 (R40/P20/A15/V25) — production CSV
  (2) REG_arch standalone (single best component, per morning brief P=+0.0646)

Metrics:
  - Pearson, Spearman, R², β slope (y on ŷ trading slope), DirAcc
  - Trading view: top decile spread, hit-rate by quintile, daily IC-IR
  - Calibration view: 10-bin E[ŷ|y] plot (monotonic + zero bias at origin)

Live-calibration comparison:
  - Raw q50 (no demean)
  - Live causal EMA-demean (production hygiene, matches v5_alpha0_huber)
"""
from __future__ import annotations
import csv
import math
import datetime as dt
import pathlib
import numpy as np

ROOT = pathlib.Path(__file__).parent.parent
EXPORTS = ROOT / "exports"
CSV_5WAY = EXPORTS / "v5push_5way_ensemble_reg_arch" / "y600_predictions_5way_R40_P20_A15_V25.csv"
REG_ARCH_DIR = EXPORTS / "reg_arch_standalone_eval"

DATE_START = dt.datetime(2025, 4, 1, tzinfo=dt.timezone.utc)
DATE_END = dt.datetime(2025, 7, 29, tzinfo=dt.timezone.utc)

EMA_ALPHA = 0.01
WARMUP = 50


def causal_ema_demean(q_bps: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Causal EMA-demean: subtract lag-1 EMA of prior preds from current pred.
    Returns (demeaned, ema_state). First WARMUP samples zeroed."""
    n = len(q_bps)
    ema = np.zeros(n)
    cur = 0.0
    for i in range(n):
        if i > 0:
            cur = EMA_ALPHA * q_bps[i - 1] + (1.0 - EMA_ALPHA) * cur
        ema[i] = cur
    out = q_bps - ema
    out[:WARMUP] = 0.0
    return out, ema


def metrics(y: np.ndarray, yhat: np.ndarray) -> dict:
    n = len(y)
    if n < 32:
        return {"n": n}
    my, mp = y.mean(), yhat.mean()
    dy, dp = y - my, yhat - mp
    sxx = (dy * dy).sum()
    syy = (dp * dp).sum()
    sxy = (dy * dp).sum()
    P = sxy / math.sqrt(sxx * syy)
    beta = sxy / syy  # y on ŷ (trading slope)
    R2 = sxy * sxy / (sxx * syy)  # = P² (for centered)
    sig_y = math.sqrt(sxx / n)
    sig_yhat = math.sqrt(syy / n)
    DA = float(((y > 0) == (yhat > 0)).mean())
    # Tail DA
    tail = np.abs(y) > sig_y
    DA_tail = float(((y[tail] > 0) == (yhat[tail] > 0)).mean()) if tail.sum() else float("nan")
    # Spearman
    ry = y.argsort().argsort().astype(np.float64)
    rp = yhat.argsort().argsort().astype(np.float64)
    mry, mrp = ry.mean(), rp.mean()
    S = ((ry - mry) * (rp - mrp)).sum() / math.sqrt(
        ((ry - mry) ** 2).sum() * ((rp - mrp) ** 2).sum()
    )
    return {
        "n": n,
        "pearson": P, "spearman": S, "r_squared": R2, "beta": beta,
        "sigma_yhat_over_y": sig_yhat / sig_y,
        "DA_pool": DA, "DA_tail": DA_tail,
    }


def trading_view(y: np.ndarray, yhat: np.ndarray, n_quintiles: int = 5) -> dict:
    """Quintile spreads + top-decile."""
    n = len(y)
    if n < 100:
        return {"n": n}
    order = np.argsort(yhat)
    y_sorted = y[order]
    q_size = n // n_quintiles
    quint_mean_y = []
    quint_dir = []
    for q in range(n_quintiles):
        lo = q * q_size
        hi = (q + 1) * q_size if q < n_quintiles - 1 else n
        chunk = y_sorted[lo:hi]
        quint_mean_y.append(float(chunk.mean()))
        quint_dir.append(float((chunk > 0).mean()) if q == n_quintiles - 1
                         else float((chunk < 0).mean()) if q == 0 else float((chunk > 0).mean()))
    top_dec_lo = int(0.9 * n)
    bot_dec_hi = int(0.1 * n)
    top_decile = float(y_sorted[top_dec_lo:].mean())
    bot_decile = float(y_sorted[:bot_dec_hi].mean())
    top_spread = top_decile - bot_decile
    return {
        "quintile_mean_y": quint_mean_y,
        "quintile_long_hitrate": quint_dir,
        "top_decile_y": top_decile,
        "bot_decile_y": bot_decile,
        "top_minus_bot_decile_bps": top_spread,
    }


def calibration_bin_plot(y: np.ndarray, yhat: np.ndarray, n_bins: int = 10) -> dict:
    """E[ŷ|y_bin] across deciles. Monotonic + zero crossing near origin = good."""
    n = len(y)
    # bin by y deciles
    edges = np.quantile(y, np.linspace(0, 1, n_bins + 1))
    edges[0] -= 1e-9
    edges[-1] += 1e-9
    bins = []
    for i in range(n_bins):
        m = (y > edges[i]) & (y <= edges[i + 1])
        if m.sum() == 0:
            bins.append({"y_center": float("nan"), "yhat_mean": float("nan"),
                         "y_mean": float("nan"), "n": 0})
            continue
        bins.append({
            "y_center": float((edges[i] + edges[i + 1]) / 2),
            "y_mean": float(y[m].mean()),
            "yhat_mean": float(yhat[m].mean()),
            "n": int(m.sum()),
        })
    # Monotonicity check (yhat_mean must be non-decreasing across y_bins)
    yhat_means = [b["yhat_mean"] for b in bins if not math.isnan(b["yhat_mean"])]
    n_inc = sum(1 for i in range(1, len(yhat_means)) if yhat_means[i] >= yhat_means[i - 1])
    monotonic_ratio = n_inc / max(1, len(yhat_means) - 1)
    # Bias at zero: |yhat_mean - 0| for the bin spanning y=0
    bias_at_origin = float("nan")
    for b in bins:
        if not math.isnan(b["y_center"]) and abs(b["y_mean"]) < 1.0:  # bin nearest zero
            bias_at_origin = b["yhat_mean"]
            break
    return {
        "bins": bins,
        "monotonic_ratio": monotonic_ratio,
        "yhat_mean_at_origin_bin": bias_at_origin,
    }


def daily_ic_ir(y: np.ndarray, yhat: np.ndarray, dates: np.ndarray) -> dict:
    """Per-day Spearman IC then mean/std → IR."""
    unique_days = np.unique(dates)
    ics = []
    for d in unique_days:
        m = dates == d
        if m.sum() < 10:
            continue
        yd, yhd = y[m], yhat[m]
        ry = yd.argsort().argsort().astype(np.float64)
        rp = yhd.argsort().argsort().astype(np.float64)
        mry, mrp = ry.mean(), rp.mean()
        denom = math.sqrt(((ry - mry) ** 2).sum() * ((rp - mrp) ** 2).sum())
        if denom < 1e-12:
            continue
        ic = ((ry - mry) * (rp - mrp)).sum() / denom
        ics.append(ic)
    if not ics:
        return {"n_days": 0}
    a = np.array(ics)
    return {
        "n_days": len(ics),
        "ic_mean": float(a.mean()),
        "ic_std": float(a.std()),
        "ic_ir": float(a.mean() / (a.std() + 1e-9)),
        "pct_positive_days": float((a > 0).mean()),
    }


def load_5way():
    rows = []
    with open(CSV_5WAY) as f:
        r = csv.DictReader(f)
        for row in r:
            if int(row["mask"]) == 0:
                continue
            ts = dt.datetime.fromisoformat(row["datetime_utc"].replace("Z", "+00:00"))
            if ts < DATE_START or ts >= DATE_END:
                continue
            rows.append({
                "ts": ts,
                "y_bps": float(row["y_true_bps"]),
                "q50_raw_bps": float(row["y_pred_q50_bps"]),
                "q50_live_bps": float(row["y_pred_q50_bps_live"]),
                "warmup": row["warmup"].lower() == "true",
            })
    # sort
    rows.sort(key=lambda r: r["ts"])
    return rows


def load_reg_arch_standalone():
    """Load REG_arch per-fold preds, denormalize to bps, attach timestamps."""
    rows = []
    for fold in (0, 1, 2):
        path = REG_ARCH_DIR / f"fold_{fold}_test_preds.npz"
        z = np.load(path, allow_pickle=True)
        pred = z["predictions"]
        y_z = z["targets"].reshape(-1)
        mask = z["mask"].reshape(-1).astype(bool)
        ts = z["timestamps"]
        sy = float(z["y_sigma"])
        ymed = float(z["y_median"])
        # Denormalize z-score → log-return → bps (multiply by 1e4 since y in log-ret)
        q50 = pred[:, 1] * sy + ymed
        y = y_z * sy + ymed
        # bps
        q50_bps = q50 * 1e4
        y_bps = y * 1e4
        order = np.argsort(ts)
        ts_o = ts[order]
        q50_o = q50_bps[order]
        y_o = y_bps[order]
        m_o = mask[order]
        for i in range(len(ts_o)):
            if not m_o[i]:
                continue
            try:
                dtobj = dt.datetime.fromtimestamp(int(ts_o[i]) / 1e6, tz=dt.timezone.utc)
            except (OverflowError, OSError, ValueError):
                continue
            if dtobj < DATE_START or dtobj >= DATE_END:
                continue
            rows.append({
                "ts": dtobj, "y_bps": float(y_o[i]),
                "q50_raw_bps": float(q50_o[i]), "fold": fold,
            })
    rows.sort(key=lambda r: r["ts"])
    # Apply causal EMA-demean for live-cal column
    q50_arr = np.array([r["q50_raw_bps"] for r in rows])
    demeaned, ema = causal_ema_demean(q50_arr)
    for i, r in enumerate(rows):
        r["q50_live_bps"] = float(demeaned[i])
        r["warmup"] = i < WARMUP
    return rows


def report(name: str, rows: list, drop_warmup: bool):
    if drop_warmup:
        rows = [r for r in rows if not r["warmup"]]
    if not rows:
        print(f"  {name}: NO DATA in range")
        return
    y = np.array([r["y_bps"] for r in rows])
    yhat_raw = np.array([r["q50_raw_bps"] for r in rows])
    yhat_live = np.array([r["q50_live_bps"] for r in rows])
    dates = np.array([r["ts"].date() for r in rows])

    print(f"\n=== {name} (n={len(rows)}, drop_warmup={drop_warmup}) ===")
    for label, yhat in [("RAW (no live-cal)", yhat_raw), ("LIVE (causal EMA-demean)", yhat_live)]:
        m = metrics(y, yhat)
        tv = trading_view(y, yhat)
        cv = calibration_bin_plot(y, yhat)
        dic = daily_ic_ir(y, yhat, dates)
        print(f"\n  [{label}]")
        print(f"    P={m['pearson']:+.4f}  S={m['spearman']:+.4f}  R²={m['r_squared']:.4f}")
        print(f"    β(y on ŷ)={m['beta']:+.3f}  σŷ/σy={m['sigma_yhat_over_y']:.3f}")
        print(f"    DA pool={m['DA_pool']:.4f}  DA|y|>σ={m['DA_tail']:.4f}")
        print(f"    bias_at_origin_bin ŷ_mean={cv['yhat_mean_at_origin_bin']:+.3f} bps  monotonic_ratio={cv['monotonic_ratio']:.2f}")
        print(f"    top-bot decile y spread={tv['top_minus_bot_decile_bps']:+.3f} bps  top_decile_y={tv['top_decile_y']:+.3f}  bot={tv['bot_decile_y']:+.3f}")
        print(f"    daily IC mean={dic['ic_mean']:+.4f} std={dic['ic_std']:.4f} IR={dic['ic_ir']:+.3f} pct+={dic['pct_positive_days']:.3f} n_days={dic['n_days']}")
        print(f"    bin plot (y_decile → ŷ_mean):")
        for i, b in enumerate(cv["bins"]):
            if math.isnan(b["y_center"]): continue
            print(f"      bin{i:>2d}  y_mean={b['y_mean']:+7.2f}  ŷ_mean={b['yhat_mean']:+7.3f}  n={b['n']:>5d}")


def main():
    print(f"Date range: {DATE_START.date()} → {DATE_END.date()}")
    print(f"5-way CSV: {CSV_5WAY}")
    print(f"REG_arch dir: {REG_ARCH_DIR}")

    rows_5way = load_5way()
    print(f"\nLoaded 5-way: {len(rows_5way)} rows in date range")
    report("5-way ENSEMBLE (REG_arch 40 + P3 20 + A 15 + V5 25)", rows_5way, drop_warmup=True)

    rows_reg = load_reg_arch_standalone()
    print(f"\nLoaded REG_arch standalone: {len(rows_reg)} rows in date range")
    report("REG_arch STANDALONE (single best, FiLM γ+β multi-stage)", rows_reg, drop_warmup=True)


if __name__ == "__main__":
    main()
