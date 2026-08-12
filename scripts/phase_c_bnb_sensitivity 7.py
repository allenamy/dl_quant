#!/usr/bin/env python3
"""Quick sensitivity: rerun Phase C pooled backtest with BNB-discount fees."""
import pathlib, json, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import numpy as np
from src.evaluation.backtest_engine import CostModel, ExecutionConfig, run_backtest, calibrate_tau_on_val

ENSEMBLE_DIR = pathlib.Path("experiments/phase_c/ensemble_preds")
BASELINE_DIR = pathlib.Path("experiments/baselines_v4_matched_preds")
SAMPLE_INT = 60

def main():
    # Load ensemble preds for all folds
    folds = [0, 1, 2]
    all_s, all_r, all_m, all_c = [], [], [], []
    for f in folds:
        e = np.load(str(ENSEMBLE_DIR / f"fold_{f}.npz"))
        xgb = np.load(str(BASELINE_DIR / f"fold_{f}_XGBoost_preds.npz"))
        sig_y = float(xgb["norm_y_sigma"])
        sig = e["predictions"].astype(np.float64)
        ret_bps = e["targets"].astype(np.float64) * sig_y * 1e4
        msk = e["mask"].astype(bool)
        iqr = np.maximum(e["v4_q90"] - e["v4_q10"], 1e-8)
        conf = np.abs(e["v4_q50"]) / iqr
        all_s.append(sig); all_r.append(ret_bps); all_m.append(msk); all_c.append(conf)
    signal = np.concatenate(all_s); returns = np.concatenate(all_r)
    mask = np.concatenate(all_m); conf = np.concatenate(all_c)

    print(f"\n{'Scenario':>25} | {'Sharpe':>10} | {'Net P&L (bps)':>14} | {'Max DD':>12} | {'Trade Rate':>12}")
    print("-" * 90)

    scenarios = [
        ("Binance regular (2/5 bps)", CostModel.binance_regular()),
        ("Binance + BNB 9折 (1.8/4.5)", CostModel.binance_bnb_discount()),
        ("Aggressive maker-only (1.5/X)", CostModel(maker_fee_bps=1.5, taker_fee_bps=4.5, slippage_bps=1.0, maker_fill_prob=0.8)),
        ("Optimistic (1/2 bps)", CostModel(maker_fee_bps=1.0, taker_fee_bps=2.0, slippage_bps=0.5, maker_fill_prob=0.7)),
    ]

    summary = []
    for name, cm in scenarios:
        # Recalibrate τ* on fold 0 for each cost model
        d0_sig = all_s[0]; d0_r = all_r[0]; d0_m = all_m[0]; d0_c = all_c[0]
        tau_wf, sweep = calibrate_tau_on_val(
            d0_sig, d0_r, d0_m, d0_c, SAMPLE_INT, cost_model=cm,
        )
        # Apply to full pooled (fold 0 uses τ=0, folds 1+2 use tau_wf) — simplified
        cfg = ExecutionConfig(position_mode="confidence_gated", tau=tau_wf)
        r = run_backtest(
            signal=signal, returns_bps=returns, mask=mask, confidence=conf,
            sample_interval_sec=SAMPLE_INT, cost_model=cm, exec_cfg=cfg,
        )
        print(f"{name:>25} | {r.sharpe_ann:>10.2f} | {r.net_pnl_bps:>14.1f} | {r.max_dd_bps:>12.1f} | {r.trade_rate:>12.2%}")
        summary.append({
            "scenario": name,
            "cost_model": {"maker_bps": cm.maker_fee_bps, "taker_bps": cm.taker_fee_bps, "slippage_bps": cm.slippage_bps},
            "tau_wf": tau_wf,
            "sharpe_ann": r.sharpe_ann,
            "net_pnl_bps": r.net_pnl_bps,
            "max_dd_bps": r.max_dd_bps,
            "trade_rate": r.trade_rate,
            "win_rate": r.win_rate,
        })

    with open("experiments/phase_c/cost_sensitivity.json", "w") as f:
        json.dump(summary, f, indent=2, default=float)
    print(f"\n✓ Saved to experiments/phase_c/cost_sensitivity.json")


if __name__ == "__main__":
    main()
