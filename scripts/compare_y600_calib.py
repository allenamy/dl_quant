"""Compare V4 y_600 calibrated training vs V4 production single-checkpoint baseline.

Baseline = `block_b_run` (V4 + composite val gate, LIVE best-epoch model). This is
the apples-to-apples reference for Track A:
  - same architecture (V4 DualPathLOBModelV3)
  - same val gate (composite 0.5*P + 0.5*S)
  - LIVE single-checkpoint output (NOT a post-hoc rank/SWA blend)

Why NOT `final_stack`: that directory contains rank-transformed blend predictions
(mean=0, std~0.85, β~0.15 by construction). Comparing single-ckpt calibrated ŷ
against a post-hoc transformed reference inflates apparent calibration "uplift"
and confuses the β interpretation.

Per-fold and pooled metrics are reported for:
  - BASELINE LIVE  : block_b_run/fold_*/test_preds.npz
  - TRACK-A LIVE   : baseline_calib/fold_*/test_preds.npz
  - TRACK-A EMA    : baseline_calib/fold_*/ema_test_preds.npz

Pre-declared gate (must hold on POOLED clean stride-10):
  1. Spearman >= baseline - 0.005  (do not regress rank IC)
  2. Pearson  >= baseline - 0.005  (do not regress amplitude IC)
  3. |β - 1| <= 0.30               (calibration target — direct trade)
  4. σ_ŷ/σ_y >= 0.020              (raw single-ckpt floor; CLAUDE.md anti-pattern
                                    #11 retraction note: 0.04 is normal for V4)

Stretch goal: P or S +10% over baseline AND |β-1| <= 0.15.
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
from scipy.stats import pearsonr, spearmanr

BASELINE_DIR = pathlib.Path("experiments/y600_push/block_b_run")
CALIB_DIR = pathlib.Path("experiments/y600_calib/baseline_calib")


def _q50(d: np.lib.npyio.NpzFile) -> np.ndarray:
    p = d["predictions"]
    return p[:, 1] if p.ndim == 2 and p.shape[-1] >= 2 else p.squeeze()


def load_clean(npz_path: pathlib.Path):
    """Return (yp, y) after canonical clean filter (stride-10 BEFORE mask)."""
    d = np.load(npz_path)
    yp, y, m = _q50(d), d["targets"].squeeze(), d["mask"].astype(bool).squeeze()
    yp_s, y_s, m_s = yp[::10], y[::10], m[::10]
    return yp_s[m_s], y_s[m_s]


def fold_metrics(yp: np.ndarray, y: np.ndarray) -> dict:
    if len(y) < 30:
        return {"n": int(len(y)), "p": float("nan"), "s": float("nan"),
                "beta": float("nan"), "sigma_ratio": float("nan")}
    p_val = pearsonr(yp, y)[0]
    s_val = spearmanr(yp, y)[0]
    beta = float(np.cov(yp, y, ddof=0)[0, 1] / (np.var(yp) + 1e-12))
    sr = float(yp.std() / (y.std() + 1e-12))
    return {"n": int(len(y)), "p": float(p_val), "s": float(s_val),
            "beta": float(beta), "sigma_ratio": float(sr)}


def collect(exp_dir: pathlib.Path, preds_name: str = "test_preds.npz"):
    """Per-fold + pooled metrics for one experiment dir."""
    folds: dict[str, dict] = {}
    pool_yp, pool_y = [], []
    for f in range(3):
        p = exp_dir / f"fold_{f}" / preds_name
        if not p.exists():
            folds[f"fold_{f}"] = {"missing": str(p)}
            continue
        yp, y = load_clean(p)
        folds[f"fold_{f}"] = fold_metrics(yp, y)
        pool_yp.append(yp); pool_y.append(y)
    pooled = (fold_metrics(np.concatenate(pool_yp), np.concatenate(pool_y))
              if pool_yp else {"n": 0})
    return {"folds": folds, "pooled": pooled}


def fmt_row(name: str, m: dict, ref: dict | None = None) -> str:
    if "missing" in m or m.get("n", 0) < 30:
        return f"  {name:<28} | (no data)"
    line = (f"  {name:<28} | N={m['n']:>5}  P={m['p']:+.4f}  S={m['s']:+.4f}  "
            f"β={m['beta']:+.4f}  σŷ/σy={m['sigma_ratio']:.4f}")
    if ref is not None and ref.get("n", 0) >= 30:
        line += (f"  | ΔP {m['p'] - ref['p']:+.4f}  ΔS {m['s'] - ref['s']:+.4f}"
                 f"  Δβ {m['beta'] - ref['beta']:+.4f}")
    return line


def gate_decision(cal: dict, ref: dict) -> dict:
    """Apply pre-declared gates to POOLED clean metrics."""
    if cal.get("n", 0) < 30 or ref.get("n", 0) < 30:
        return {"overall": "INSUFFICIENT_DATA"}
    g = {
        "no_S_regression":  cal["s"]               >= ref["s"] - 0.005,
        "no_P_regression":  cal["p"]               >= ref["p"] - 0.005,
        "beta_close_to_1":  abs(cal["beta"] - 1.0) <= 0.30,
        "no_var_collapse":  cal["sigma_ratio"]     >= 0.020,
    }
    g["overall"] = "PASS" if all(g.values()) else "FAIL"
    g["stretch_P_uplift"] = cal["p"] >= ref["p"] * 1.10
    g["stretch_S_uplift"] = cal["s"] >= ref["s"] * 1.10
    g["stretch_beta_tight"] = abs(cal["beta"] - 1.0) <= 0.15
    return g


def main():
    if not BASELINE_DIR.exists():
        sys.exit(f"baseline missing: {BASELINE_DIR}")

    base = collect(BASELINE_DIR, "test_preds.npz")
    cal_live = collect(CALIB_DIR, "test_preds.npz")
    cal_ema = collect(CALIB_DIR, "ema_test_preds.npz")

    print("\n========== V4 y_600 Calibration — Track A vs Production Baseline ==========")
    print("\nPER-FOLD (clean stride-10):")
    for f in [0, 1, 2]:
        key = f"fold_{f}"
        print(f"\n  --- {key} ---")
        print(fmt_row("V4 baseline (block_b LIVE)", base["folds"].get(key, {})))
        print(fmt_row("Track-A V1 LIVE",            cal_live["folds"].get(key, {}),
                      base["folds"].get(key, {})))
        print(fmt_row("Track-A V1 EMA",             cal_ema["folds"].get(key, {}),
                      base["folds"].get(key, {})))

    print("\n\nPOOLED (clean stride-10, all 3 folds):")
    print(fmt_row("V4 baseline (block_b LIVE)", base["pooled"]))
    print(fmt_row("Track-A V1 LIVE",            cal_live["pooled"], base["pooled"]))
    print(fmt_row("Track-A V1 EMA",             cal_ema["pooled"],  base["pooled"]))

    print("\n\nGATE DECISION (POOLED, against block_b_run baseline):")
    for label, cal in [("Track-A V1 LIVE", cal_live["pooled"]),
                       ("Track-A V1 EMA",  cal_ema["pooled"])]:
        print(f"\n  {label}:")
        g = gate_decision(cal, base["pooled"])
        for k, v in g.items():
            tag = ("PASS" if v is True else "FAIL" if v is False else str(v))
            print(f"    {k:<22}  {tag}")

    out = {
        "baseline_block_b": base,
        "track_a_v1_live": cal_live,
        "track_a_v1_ema": cal_ema,
        "gate_live": gate_decision(cal_live["pooled"], base["pooled"]),
        "gate_ema": gate_decision(cal_ema["pooled"], base["pooled"]),
    }
    out_path = pathlib.Path("experiments/y600_calib/baseline_calib/compare_vs_block_b.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\nWrote: {out_path}")


if __name__ == "__main__":
    main()
