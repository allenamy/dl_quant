#!/usr/bin/env python3
"""Phase D Stage 1 — Feature probe for long-horizon viability.

Question: Can we lift IC at longer horizons (y_300, y_600) by adding
multi-scale aggregated features to the existing last-timestep feature set?

Method:
  - Load V4 NPZ per day, compute multi-scale aggregates in-memory
  - Keep only last timestep of original X, concatenate with new aggregates
  - Run Ridge on matched 3-fold walk-forward (700d/30d/90d, stride=60)
  - Compare 3 feature sets × 3 horizons × 3 folds

GATE:
  - PASS: y_600 IC with multi-scale ≥ 0.05 → proceed to Stage 2 NPZ rebuild
  - FAIL: y_600 IC < 0.03 → stop, long horizon fundamentally harder
  - MARGINAL: 0.03-0.05 → report to user

Zero modification to V4 code. New features computed in-memory.
No NPZ regeneration. Uses only existing data.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr
from sklearn.linear_model import Ridge

# ---------------------------------------------------------------------------
# Feature index mapping (verified from NPZ features field)
# ---------------------------------------------------------------------------
# Indices correspond to features list in docs/PROJECT_OVERVIEW.md sec 4.2
FEAT_IDX = {
    "log_return_1s": 0,
    "log_return_5s": 1,
    "log_return_30s": 2,
    "spread_bps": 3,
    "spread_change": 4,
    "obi_L1": 5,
    "obi_L5": 6,
    "obi_L10": 7,
    "realized_vol_60s": 19,
    "realized_vol_300s": 20,
    "bid_slope_L10": 22,
    "ask_slope_L10": 23,
    "net_trade_flow_1s": 45,
    "cumulative_net_flow_30s": 47,
    "cumulative_net_flow_300s": 48,
    "vwap_return_1s": 50,
    "microprice_dev_bps": 52,
    "vpin_60s": 54,
    "vpin_300s": 55,
    "book_pressure_imbalance": 56,
}


# ---------------------------------------------------------------------------
# Multi-scale feature computation
# ---------------------------------------------------------------------------

def compute_multiscale_features(X_day: np.ndarray) -> Tuple[np.ndarray, List[str]]:
    """Compute multi-scale aggregates from X_day (N, L=600, F=64).

    All aggregates use data strictly BEFORE the prediction target
    (X[:, 0:L] is [t-600s, t], target is return from t to t+horizon).

    Returns
    -------
    new_feat : (N, K) ndarray
    names    : list of feature names
    """
    N, L, F = X_day.shape
    assert L == 600, f"Expected L=600, got {L}"

    log_ret_1s = X_day[:, :, FEAT_IDX["log_return_1s"]]       # (N, 600)
    log_ret_5s = X_day[:, :, FEAT_IDX["log_return_5s"]]
    log_ret_30s = X_day[:, :, FEAT_IDX["log_return_30s"]]
    spread = X_day[:, :, FEAT_IDX["spread_bps"]]
    obi5 = X_day[:, :, FEAT_IDX["obi_L5"]]
    obi1 = X_day[:, :, FEAT_IDX["obi_L1"]]
    net_flow = X_day[:, :, FEAT_IDX["net_trade_flow_1s"]]
    microprice = X_day[:, :, FEAT_IDX["microprice_dev_bps"]]
    vpin300 = X_day[:, :, FEAT_IDX["vpin_300s"]]

    feats = {}

    # 5-min aggregates (last 300s of window)
    feats["return_5m"] = log_ret_1s[:, -300:].sum(axis=1).astype(np.float32)
    feats["vol_5m"] = (log_ret_1s[:, -300:].std(axis=1) * np.sqrt(300)).astype(np.float32)
    feats["obi5_5m_mean"] = obi5[:, -300:].mean(axis=1).astype(np.float32)
    feats["spread_5m_mean"] = spread[:, -300:].mean(axis=1).astype(np.float32)
    feats["spread_5m_std"] = spread[:, -300:].std(axis=1).astype(np.float32)
    feats["net_flow_5m_sum"] = net_flow[:, -300:].sum(axis=1).astype(np.float32)
    feats["microprice_5m_mean"] = microprice[:, -300:].mean(axis=1).astype(np.float32)

    # 10-min aggregates (full 600s window)
    feats["return_10m"] = log_ret_1s[:, :].sum(axis=1).astype(np.float32)
    feats["vol_10m"] = (log_ret_1s[:, :].std(axis=1) * np.sqrt(600)).astype(np.float32)
    feats["obi5_10m_mean"] = obi5[:, :].mean(axis=1).astype(np.float32)
    feats["obi1_10m_mean"] = obi1[:, :].mean(axis=1).astype(np.float32)
    feats["net_flow_10m_sum"] = net_flow[:, :].sum(axis=1).astype(np.float32)
    feats["vpin_10m_mean"] = vpin300[:, :].mean(axis=1).astype(np.float32)

    # Cross-scale momentum / volatility ratios
    eps = 1e-8
    feats["momentum_ratio_5vs10"] = (feats["return_5m"] / (feats["return_10m"] + eps)).astype(np.float32)
    feats["vol_ratio_5vs10"] = (feats["vol_5m"] / (feats["vol_10m"] + eps)).astype(np.float32)

    # Momentum acceleration (recent half vs older half of window)
    older_half = log_ret_1s[:, :300].sum(axis=1).astype(np.float32)
    recent_half = log_ret_1s[:, 300:].sum(axis=1).astype(np.float32)
    feats["momentum_accel"] = recent_half - older_half

    # Autocorrelation proxy: (recent return × older return) sign
    feats["return_sign_agreement_5m_vs_older"] = (np.sign(older_half) * np.sign(recent_half)).astype(np.float32)

    # Flow persistence (sign of 5m flow vs 10m flow)
    flow_5m = feats["net_flow_5m_sum"]
    flow_10m = feats["net_flow_10m_sum"]
    feats["flow_sign_agreement"] = (np.sign(flow_5m) * np.sign(flow_10m)).astype(np.float32)

    names = list(feats.keys())
    values = np.stack([feats[k] for k in names], axis=1)
    # Sanitize (division by near-zero can produce inf)
    values = np.nan_to_num(values, nan=0.0, posinf=0.0, neginf=0.0)
    # Clip momentum_ratio and vol_ratio to prevent extremes
    for i, name in enumerate(names):
        if "ratio" in name:
            values[:, i] = np.clip(values[:, i], -10, 10)
    return values.astype(np.float32), names


def compute_session_features(timestamps: np.ndarray) -> Tuple[np.ndarray, List[str]]:
    """Session-level features from timestamps (microseconds)."""
    ts_sec = (timestamps // 1_000_000).astype(np.int64) if timestamps[0] > 1e14 else timestamps.astype(np.int64)
    hour = (ts_sec % 86400) // 3600  # 0-23
    dow = (ts_sec // 86400 + 4) % 7  # 0=Monday

    feats = np.stack([
        np.sin(2 * np.pi * dow / 7).astype(np.float32),
        np.cos(2 * np.pi * dow / 7).astype(np.float32),
        # Is it Asia hours (00-08 UTC)?
        ((hour >= 0) & (hour < 8)).astype(np.float32),
        # EU hours (07-15 UTC)?
        ((hour >= 7) & (hour < 15)).astype(np.float32),
        # US hours (14-21 UTC)?
        ((hour >= 14) & (hour < 21)).astype(np.float32),
    ], axis=1)
    names = ["dow_sin", "dow_cos", "asia_hours", "eu_hours", "us_hours"]
    return feats, names


# ---------------------------------------------------------------------------
# Data loading (day-by-day to avoid OOM)
# ---------------------------------------------------------------------------

def load_days_with_enrichment(
    npz_dir: pathlib.Path,
    days: List[str],
    horizons: List[int],
) -> Tuple[np.ndarray, Dict[int, np.ndarray], Dict[int, np.ndarray], List[str]]:
    """Load enriched features + per-horizon y/mask day-by-day (single pass over NPZ).

    Returns:
      X_enriched         : (N, 64 + 17 + 5)
      ys_by_horizon      : {h: (N,)} for each horizon
      masks_by_horizon   : {h: (N,)} for each horizon
      feature_names      : list of 86 names
    """
    xs_original, xs_multiscale, xs_session = [], [], []
    ys_by_h = {h: [] for h in horizons}
    ms_by_h = {h: [] for h in horizons}
    feature_names_ms: List[str] = []
    feature_names_sess: List[str] = []

    for day in days:
        path = npz_dir / f"{day}.npz"
        if not path.exists():
            continue
        npz = np.load(str(path), allow_pickle=True)
        X_day = npz["X"].astype(np.float32)  # (N, 600, 64)
        if X_day.shape[1] != 600:
            raise ValueError(f"{day}: expected L=600, got {X_day.shape[1]}")

        xs_original.append(X_day[:, -1, :])
        ms, names_ms = compute_multiscale_features(X_day)
        xs_multiscale.append(ms)
        if not feature_names_ms:
            feature_names_ms = names_ms

        ts_day = npz["timestamps"] if "timestamps" in npz.files else np.zeros(len(X_day), dtype=np.int64)
        sess, names_sess = compute_session_features(ts_day)
        xs_session.append(sess)
        if not feature_names_sess:
            feature_names_sess = names_sess

        for h in horizons:
            hk = f"y_{h}"
            mk = f"y_mask_{h}"
            if hk not in npz.files:
                raise KeyError(f"{day}: missing {hk}")
            ys_by_h[h].append(npz[hk].astype(np.float32))
            ms_by_h[h].append(npz[mk].astype(np.float32))

    X_orig = np.concatenate(xs_original, axis=0)
    X_ms = np.concatenate(xs_multiscale, axis=0)
    X_sess = np.concatenate(xs_session, axis=0)

    X_orig = np.nan_to_num(X_orig, nan=0.0, posinf=0.0, neginf=0.0)
    X_ms = np.nan_to_num(X_ms, nan=0.0, posinf=0.0, neginf=0.0)
    X_sess = np.nan_to_num(X_sess, nan=0.0, posinf=0.0, neginf=0.0)

    X_enriched = np.concatenate([X_orig, X_ms, X_sess], axis=1)

    ys_out = {}
    masks_out = {}
    for h in horizons:
        y_arr = np.concatenate(ys_by_h[h], axis=0)
        m_arr = np.concatenate(ms_by_h[h], axis=0)
        y_arr = np.nan_to_num(y_arr, nan=0.0, posinf=0.0, neginf=0.0)
        y_arr[m_arr == 0] = 0.0
        ys_out[h] = y_arr
        masks_out[h] = m_arr

    feature_names_orig = [f"orig_{i}" for i in range(X_orig.shape[1])]
    feature_names = feature_names_orig + feature_names_ms + feature_names_sess
    return X_enriched, ys_out, masks_out, feature_names


# ---------------------------------------------------------------------------
# Ridge runner
# ---------------------------------------------------------------------------

def normalize_train_test(X_train, X_test, y_train):
    """Z-score features by train stats; MAD-scale target."""
    mu = X_train.mean(axis=0)
    sigma = X_train.std(axis=0)
    sigma = np.where(sigma < 1e-8, 1.0, sigma)
    X_train_n = (X_train - mu) / sigma
    X_test_n = (X_test - mu) / sigma

    y_median = np.median(y_train)
    y_mad = np.median(np.abs(y_train - y_median))
    y_mad_sigma = max(y_mad * 1.4826, 1e-8)
    y_train_n = (y_train - y_median) / y_mad_sigma
    return X_train_n, X_test_n, y_train_n, y_median, y_mad_sigma


def run_ridge(X_train, y_train, mask_train, X_test, y_test, mask_test, alpha=1.0):
    """Train Ridge, evaluate on test. Returns metrics dict."""
    # Filter by mask
    tr = mask_train.astype(bool)
    te = mask_test.astype(bool)

    X_train_n, X_test_n, y_train_n, ymed, ysig = normalize_train_test(
        X_train[tr], X_test[te], y_train[tr],
    )
    y_test_n = (y_test[te] - ymed) / ysig

    model = Ridge(alpha=alpha)
    model.fit(X_train_n, y_train_n)
    pred = model.predict(X_test_n)

    return {
        "pearson": float(pearsonr(pred, y_test_n)[0]),
        "spearman": float(spearmanr(pred, y_test_n)[0]),
        "dir_acc": float((np.sign(pred) == np.sign(y_test_n)).mean()),
        "n": int(len(pred)),
        "y_mad_sigma": float(ysig),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_folds(days: List[str], train_d: int, val_d: int, test_d: int, stride_d: int):
    """Strict temporal walk-forward."""
    window = train_d + val_d + test_d
    folds = []
    start = 0
    while start + window <= len(days):
        folds.append({
            "train": days[start:start + train_d],
            "val": days[start + train_d:start + train_d + val_d],
            "test": days[start + train_d + val_d:start + window],
        })
        start += stride_d
    return folds


def discover_days(npz_dir: pathlib.Path) -> List[str]:
    return sorted([f.stem for f in npz_dir.glob("*.npz")])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--npz-dir", type=pathlib.Path, default=pathlib.Path("data/npz_v4"))
    parser.add_argument("--output-dir", type=pathlib.Path,
                        default=pathlib.Path("experiments/phase_d/stage1_probe"))
    parser.add_argument("--horizons", type=int, nargs="+", default=[180, 300, 600])
    parser.add_argument("--train-days", type=int, default=700)
    parser.add_argument("--val-days", type=int, default=30)
    parser.add_argument("--test-days", type=int, default=90)
    parser.add_argument("--fold-stride", type=int, default=60)
    parser.add_argument("--max-folds", type=int, default=3)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    days = discover_days(args.npz_dir)
    folds = build_folds(days, args.train_days, args.val_days, args.test_days, args.fold_stride)
    if args.max_folds:
        folds = folds[:args.max_folds]
    print(f"[stage1] Discovered {len(days)} days, {len(folds)} walk-forward folds")

    # Load once per fold; evaluate at each horizon with 3 feature sets
    all_results = []

    for fold_idx, fold in enumerate(folds):
        print(f"\n[stage1] Fold {fold_idx}: train {len(fold['train'])}d, test {len(fold['test'])}d")
        print(f"[stage1]   Loading train days once (across all horizons)...")
        X_train, ys_train, ms_train, _ = load_days_with_enrichment(
            args.npz_dir, fold["train"], args.horizons,
        )
        print(f"[stage1]   Loading test days once...")
        X_test, ys_test, ms_test, _ = load_days_with_enrichment(
            args.npz_dir, fold["test"], args.horizons,
        )

        n_orig = 64
        n_ms = 18    # verified: count of feats dict entries in compute_multiscale_features
        n_sess = 5
        assert X_train.shape[1] == n_orig + n_ms + n_sess, (
            f"Expected {n_orig+n_ms+n_sess} features, got {X_train.shape[1]}"
        )

        sets_train = {
            "orig_64": X_train[:, :n_orig],
            "orig+ms+sess": X_train,
            "ms+sess_only": X_train[:, n_orig:],
        }
        sets_test_x = {
            "orig_64": X_test[:, :n_orig],
            "orig+ms+sess": X_test,
            "ms+sess_only": X_test[:, n_orig:],
        }

        for horizon in args.horizons:
            y_train = ys_train[horizon]; mask_train = ms_train[horizon]
            y_test = ys_test[horizon]; mask_test = ms_test[horizon]

            for fset_name in sets_train:
                res = run_ridge(
                    sets_train[fset_name], y_train, mask_train,
                    sets_test_x[fset_name], y_test, mask_test,
                    alpha=1.0,
                )
                res.update({
                    "fold": fold_idx,
                    "horizon": horizon,
                    "feature_set": fset_name,
                    "n_features": sets_train[fset_name].shape[1],
                })
                all_results.append(res)
                print(f"[stage1]   y_{horizon:<4} {fset_name:15s} ({res['n_features']:2d} feat): "
                      f"Pearson={res['pearson']:+.4f}  Spearman={res['spearman']:+.4f}  "
                      f"DirAcc={res['dir_acc']:.4f}  N={res['n']:,}")

    df = pd.DataFrame(all_results)
    df.to_csv(args.output_dir / "ridge_results.csv", index=False)

    # Summary: pooled across folds per (horizon, feature_set)
    print("\n" + "=" * 90)
    print("POOLED (mean across folds)")
    print("=" * 90)
    print(f"{'Horizon':>10} | {'Feature Set':>18} | {'Pearson':>10} | {'Spearman':>10} | {'N_feat':>7}")
    print("-" * 80)
    pooled = df.groupby(["horizon", "feature_set"]).agg(
        pearson_mean=("pearson", "mean"),
        pearson_std=("pearson", "std"),
        spearman_mean=("spearman", "mean"),
        dir_acc_mean=("dir_acc", "mean"),
        n_features=("n_features", "first"),
    ).reset_index()

    for _, row in pooled.iterrows():
        print(f"y_{int(row['horizon']):>7}  | {row['feature_set']:>18} | {row['pearson_mean']:>+10.4f} | "
              f"{row['spearman_mean']:>+10.4f} | {int(row['n_features']):>7}")

    pooled.to_csv(args.output_dir / "pooled_summary.csv", index=False)

    # --- GATE decision ---
    print("\n" + "=" * 90)
    print("GATE DECISION")
    print("=" * 90)
    y600_enriched = pooled[(pooled["horizon"] == 600) & (pooled["feature_set"] == "orig+ms+sess")]
    y600_baseline = pooled[(pooled["horizon"] == 600) & (pooled["feature_set"] == "orig_64")]

    if len(y600_enriched) and len(y600_baseline):
        p_enr = y600_enriched.iloc[0]["pearson_mean"]
        p_base = y600_baseline.iloc[0]["pearson_mean"]
        print(f"y_600 Pearson — baseline (orig_64): {p_base:+.4f}")
        print(f"y_600 Pearson — enriched (+multi-scale+session): {p_enr:+.4f}")
        print(f"Lift from enrichment: {p_enr - p_base:+.4f}")
        if p_enr >= 0.05:
            verdict = "✅ PASS — proceed to Stage 2 (NPZ rebuild)"
        elif p_enr < 0.03:
            verdict = "❌ FAIL — long horizon fundamentally harder; stop here"
        else:
            verdict = "🟡 MARGINAL — 0.03-0.05 zone; discuss with user"
        print(f"\n{verdict}")
    else:
        verdict = "insufficient data"

    summary = {
        "gate_verdict": verdict,
        "pooled": pooled.to_dict(orient="records"),
        "params": {
            "horizons": args.horizons,
            "n_folds": len(folds),
            "train_days": args.train_days,
        },
    }
    with open(args.output_dir / "gate_verdict.json", "w") as f:
        json.dump(summary, f, indent=2, default=float)

    print(f"\n✓ Results: {args.output_dir}/")


if __name__ == "__main__":
    main()
