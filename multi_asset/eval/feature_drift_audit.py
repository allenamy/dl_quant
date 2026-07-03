"""Feature-drift audit (Phase-1 gap #7): per-channel train->test distribution shift on the MODEL'S
input view (train-z-normalized, clipped ±10), for the 88 X channels of npz_v2arch, per fold.

Measures, per channel per fold:
  - PSI(train, test) on train-z values (10 bins on train deciles) — how OOD the test month is.
  - %-clipped-at-±10 in the test month (drift pushing features past the static clip).
  - univariate Spearman(channel_last_ts, y) on the test month (clean rows) — is the channel
    predictive, and does its predictiveness drift?

Uses the exact model train stats from the fold's norm_params.npz (x_mean/x_std) when present
(the d1/production folds share npz_v2arch + 450d so their stats coincide); else recomputes from a
sample of train days. Samples the LAST timestep of each window (the "current" state) to avoid
intra-window autocorrelation and keep it CPU-cheap.

Run on SERVER:
  conda run -n hsy_v5push python multi_asset/eval/feature_drift_audit.py \
    --folds 2025-08-10:experiments/... 2025-10-10:experiments/d1gate/d1_2025_10_run1 \
            2026-01-10:experiments/d1gate/d1_2026_01_run1 2026-04-10:experiments/d1gate/d1_2026_04_run2 \
    --out exports/feature_drift_audit.csv
"""
from __future__ import annotations
import numpy as np, glob, os, argparse
from scipy.stats import spearmanr

NPZ_DIR = "data/npz_v2arch"
TRAIN_DAYS, VAL_DAYS, EMB = 450, 45, 1
NSPOT = 64
PT_NAMES = ['pt_buy_volume_1s','pt_sell_volume_1s','pt_net_trade_flow_1s','pt_trade_imbalance_1s',
            'pt_cumulative_net_flow_30s','pt_cumulative_net_flow_300s','pt_trade_intensity_30s',
            'pt_vwap_return_1s','pt_kyle_lambda_30s','pt_vpin_60s','pt_vpin_300s','pt_price_impact_30s',
            'pt_net_flow_x_spread','pt_net_flow_x_vol','pt_net_flow_rank_1h','pt_large_trade_arrival_60s']
CROSS_NAMES = ['x_mid_ratio_log','x_basis_bps','x_spread_ratio_log','x_depth_ratio_log',
               'x_obi_diff','x_mpdev_diff','x_rvol_ratio_log','x_tradeflow_ratio']


def chan_name(i):
    if i < NSPOT: return f"spot_{i:02d}"
    if i < NSPOT + 16: return PT_NAMES[i - NSPOT]
    return CROSS_NAMES[i - NSPOT - 16]


def all_days():
    return sorted(os.path.basename(f)[:-4] for f in glob.glob(f"{NPZ_DIR}/*.npz")
                  if os.path.basename(f)[0].isdigit())


def fold_days(days, test_start):
    ti = days.index(test_start)
    test = days[ti:ti + 28]
    ve = ti - EMB; vs = ve - VAL_DAYS; te = vs - EMB; ts = max(0, te - TRAIN_DAYS)
    return days[ts:te], test


def sample_last_ts(day_list, max_days=None, y_too=False):
    """Stack the last-timestep (t=-1) feature row of every window across the given days."""
    if max_days and len(day_list) > max_days:
        idx = np.linspace(0, len(day_list) - 1, max_days).astype(int)
        day_list = [day_list[i] for i in idx]
    Xs, Ys, Ts = [], [], []
    for d in day_list:
        fp = f"{NPZ_DIR}/{d}.npz"
        if not os.path.exists(fp): continue
        z = np.load(fp, allow_pickle=True)
        X = z["X"][:, -1, :].astype(np.float64)           # (N,88) last timestep
        m = z["y_mask_600"].astype(bool) if "y_mask_600" in z.files else np.ones(len(X), bool)
        Xs.append(X[m])
        if y_too:
            Ys.append(z["y_600"][m].astype(np.float64)); Ts.append(z["timestamps"][m].astype(np.int64))
    X = np.concatenate(Xs) if Xs else np.zeros((0, 88))
    if y_too:
        return X, np.concatenate(Ys), np.concatenate(Ts)
    return X


def psi(train_z, test_z, bins=10):
    edges = np.quantile(train_z, np.linspace(0, 1, bins + 1)); edges[0] = -np.inf; edges[-1] = np.inf
    tr = np.histogram(train_z, edges)[0] / max(len(train_z), 1)
    te = np.histogram(test_z, edges)[0] / max(len(test_z), 1)
    tr = np.clip(tr, 1e-4, None); te = np.clip(te, 1e-4, None)
    return float(np.sum((te - tr) * np.log(te / tr)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--folds", nargs="+", required=True, help="test_start:fold_dir (fold_dir for norm_params)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--train-sample-days", type=int, default=40)
    a = ap.parse_args()
    days = all_days()
    rows = []
    for spec in a.folds:
        test_start, fold_dir = spec.split(":", 1)
        mo = test_start[:7].replace("-", "_")
        tr_days, te_days = fold_days(days, test_start)
        # train stats: prefer saved norm_params (exact model view)
        npf = os.path.join(fold_dir, "fold_0", "norm_params.npz")
        if os.path.exists(npf):
            z = np.load(npf); xm, xs = z["x_mean"].astype(np.float64), z["x_std"].astype(np.float64)
            src = "saved"
        else:
            Xtr0 = sample_last_ts(tr_days, max_days=a.train_sample_days)
            xm, xs = Xtr0.mean(0), Xtr0.std(0); src = "recomp"
        xs = np.where(xs < 1e-9, 1.0, xs)
        Xtr = sample_last_ts(tr_days, max_days=a.train_sample_days)
        Xte, yte, tte = sample_last_ts(te_days, y_too=True)
        Ztr = np.clip((Xtr - xm) / xs, -10, 10)
        Zte_unclip = (Xte - xm) / xs
        Zte = np.clip(Zte_unclip, -10, 10)
        print(f"[{mo}] train {tr_days[0]}..{tr_days[-1]} ({len(tr_days)}d, stats={src}) "
              f"test {te_days[0]}..{te_days[-1]} n_tr={len(Xtr)} n_te={len(Xte)}", flush=True)
        for c in range(88):
            ps = psi(Ztr[:, c], Zte[:, c])
            clip = float(np.mean(np.abs(Zte_unclip[:, c]) >= 10))
            sp = spearmanr(Xte[:, c], yte).statistic
            rows.append((mo, c, chan_name(c), round(ps, 4), round(clip, 4),
                         round(float(sp) if np.isfinite(sp) else 0.0, 4)))
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    import csv
    with open(a.out, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["month", "chan_idx", "chan_name", "psi", "pct_clipped", "spearman_y"])
        w.writerows(rows)
    print(f"WROTE {a.out} ({len(rows)} rows)")
    print("DONE_FEATURE_DRIFT.")


if __name__ == "__main__":
    main()
