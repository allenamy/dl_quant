"""Magnitude-THRESHOLD (conviction) backtest — the cost-efficient strategy.

Instead of a full-turnover rank long-short (which flips all 14 every period and is
swamped by cost), trade SELECTIVELY: enter an asset only when its predicted RESIDUAL
magnitude clears a threshold (high conviction it will out/under-perform the cross-
section), HOLD with hysteresis (exit only when conviction decays below a lower band or
the sign flips). Sparse trading -> low turnover -> can beat the fee. This is the cross-
sectional analog of the single-asset tail strategy; it RELIES on residual MAGNITUDE
calibration (Huber + pinball), which is why magnitude prediction matters even though
per-asset Pearson is capped.

Per-asset hysteresis state machine over the clean600 prediction series; positions
equal-weighted over the ACTIVE set each period, optionally demeaned for market-
neutrality; net of per-side cost on |delta weight|. Sweeps the entry threshold.

Usage: python3 multi_asset/eval/backtest_threshold.py --tag R1_residual_saved [--cost_bps 2.0]
"""
from __future__ import annotations

import argparse
import glob
import json
import os.path as p

import numpy as np

EXPORT = ("/mnt/storage/private/work_hsy/quant_research_multi_asset/"
          "multi_asset/exports/train")
SEC_PER_YEAR = 365 * 24 * 3600
HORIZON = 600


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--cost_bps", type=float, default=2.0)
    ap.add_argument("--neutral", action="store_true", help="demean positions (market-neutral)")
    args = ap.parse_args()
    d = p.join(EXPORT, args.tag)
    ref = np.load(p.join(d, "panel_ref.npz"), allow_pickle=True)
    ts, Y, CL = ref["ts"], ref["Y"], ref["CL"]
    T, S = Y.shape
    pred = np.full((T, S), np.nan, np.float32)
    for f in sorted(glob.glob(p.join(d, "fold_*_preds.npz"))):
        z = np.load(f); rows = z["te_rows"]; pred[rows] = z["pred"][rows]
    # the rank-dominated loss compresses prediction magnitude (sigma_yhat/sigma_y~0.04),
    # so threshold on the prediction's OWN z-scale (conviction = how extreme the model is).
    mu, sd = np.nanmean(pred), np.nanstd(pred)
    print(f"[bt] pred raw std={sd:.5f} -> z-scoring for threshold (tau in pred-std units)")
    pred = (pred - mu) / (sd + 1e-12)
    # test rows in TIME order
    rows = np.array([t for t in range(T)
                     if np.isfinite(pred[t]).any() and (CL[t] & np.isfinite(Y[t])).sum() >= 5])
    rows = rows[np.argsort(ts[rows])]
    per_yr = SEC_PER_YEAR / HORIZON
    ann = np.sqrt(per_yr)

    def run(tau_in, exit_frac=0.5):
        tau_out = tau_in * exit_frac
        state = np.zeros(S)                                  # current per-asset position
        prev_w = np.zeros(S)
        rets, turns, exposure, n_pos = [], [], [], []
        for t in rows:
            valid = CL[t] & np.isfinite(pred[t]) & np.isfinite(Y[t])
            pp = np.where(valid, pred[t], 0.0)
            for i in range(S):
                if not valid[i]:
                    state[i] = 0.0; continue
                pv = pp[i]
                if state[i] == 0.0:
                    if pv > tau_in: state[i] = 1.0
                    elif pv < -tau_in: state[i] = -1.0
                else:
                    if abs(pv) < tau_out or np.sign(pv) != np.sign(state[i]):
                        state[i] = 0.0
                        if pv > tau_in: state[i] = 1.0
                        elif pv < -tau_in: state[i] = -1.0
            act = np.abs(state) > 0
            k = act.sum()
            if k == 0:
                w = np.zeros(S)
            else:
                w = state.copy()
                if args.neutral:
                    w[act] = w[act] - w[act].mean()          # market-neutral
                s = np.abs(w).sum()
                w = w / s * 2.0 if s > 0 else w               # |book| normalized
            yk = np.nan_to_num(Y[t], nan=0.0)
            turn = float(np.abs(w - prev_w).sum())
            gross = float((w * yk).sum())
            rets.append(gross - turn * (args.cost_bps * 1e-4))
            turns.append(turn); exposure.append(float(w.sum())); n_pos.append(int(k))
            prev_w = w
        rets = np.array(rets)
        sharpe = float(rets.mean()/rets.std()*ann) if rets.std() > 0 else float("nan")
        gross_only = np.array([0.0])  # not separately tracked here
        return dict(net_sharpe=round(sharpe, 3),
                    net_ann_bps=round(float(rets.mean()*per_yr*1e4), 1),
                    avg_turnover=round(float(np.mean(turns)), 3),
                    avg_n_positions=round(float(np.mean(n_pos)), 2),
                    avg_gross_exposure=round(float(np.mean(np.abs(exposure))), 3),
                    trade_rate=round(float(np.mean(np.array(turns) > 1e-6)), 3))

    sweep = {tau: run(tau) for tau in (0.5, 1.0, 1.5, 2.0, 2.5, 3.0)}
    best = max(sweep, key=lambda tau: sweep[tau]["net_sharpe"])
    out = dict(tag=args.tag, cost_bps=args.cost_bps, neutral=args.neutral,
               n_periods=int(len(rows)), threshold_sweep=sweep,
               best_threshold=best, best=sweep[best])
    print(json.dumps(out, indent=2))
    json.dump(out, open(p.join(d, "backtest_threshold.json"), "w"), indent=2)
    print(f"saved -> {p.join(d, 'backtest_threshold.json')}")


if __name__ == "__main__":
    main()
