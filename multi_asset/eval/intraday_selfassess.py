"""WITHIN-DAY SELF-ASSESSMENT: does the model's MORNING realized IC causally predict its AFTERNOON IC
the same day, and can a causal intraday confidence-scaler exploit it? (frontier lever, zero GPU.)

Orthogonal to H2 (static day-descriptors failed to predict day-IC): this uses the model's OWN realized
morning errors — a causal, same-day signal. Split each UTC day; MORNING rows are label-closed by the
split (t_tod <= split - 600s, respecting the y_600 lag) so the afternoon scaler uses only <=t info.

Reports: rank-corr(morning IC, afternoon IC) pooled + per-month + per-regime; and a causal scaler
(gate: size afternoon only if morning IC>0; soft: w=clip(0.5+3*morning_IC,0,1.5)) — per-day-CLEAN
afternoon IC lift + pooled afternoon lift + leave-top-days-out.

Run LOCAL:
  python multi_asset/eval/intraday_selfassess.py --csv exports/final_l01/y600_backtest_dataset.csv --split 12
"""
from __future__ import annotations
import numpy as np, pandas as pd, argparse
from scipy.stats import pearsonr, spearmanr

SEC = 1000; HZ = 600 * SEC; DAY = 86400 * SEC
DRIFT = ["2026_01", "2026_02", "2026_03", "2026_04", "2026_05"]
STRONG = ["2025_10", "2025_11"]; NORMAL = ["2025_08", "2025_09", "2025_12"]


def _nono(t):
    o = np.argsort(t); k = []; last = -1e18
    for i in o:
        if t[i] - last >= HZ:
            k.append(i); last = t[i]
    return np.array(k, int)


def _ic(ts, q, y, idx, minrows=15, minpairs=12):
    if len(idx) < minrows:
        return np.nan, None, None
    k = _nono(ts[idx])
    if len(k) < minpairs:
        return np.nan, None, None
    qq = q[idx][k]; yy = y[idx][k]
    r = pearsonr(qq, yy)[0] if (qq.std() > 1e-9 and yy.std() > 1e-9) else np.nan
    return r, qq, yy


def build(df, split_h):
    ts = df.timestamp_ms.values.astype(np.int64); y = df.y_true_ret_bps.values.astype(float)
    q = df.y_pred_raw.values.astype(float); mo = df.month.values
    tod = (ts // SEC) % 86400; day = ts // DAY
    cut = split_h * 3600
    rows = []
    for d in np.unique(day):
        m = np.where((day == d) & (tod <= cut - 600))[0]     # morning, label-closed by split
        a = np.where((day == d) & (tod >= cut))[0]
        mic, _, _ = _ic(ts, q, y, m); aic, aq, ay = _ic(ts, q, y, a)
        if np.isfinite(mic) and np.isfinite(aic):
            rows.append((int(d), mo[m[0]], mic, aic, aq, ay))
    return pd.DataFrame(rows, columns=["day", "month", "mic", "aic", "aq", "ay"])


def scaler(sub):
    base = sub.aic.mean()
    keep = sub[sub.mic > 0]; gate = keep.aic.mean(); frac = len(keep) / len(sub)
    w = np.clip(0.5 + 3 * sub.mic.values, 0, 1.5); soft = np.average(sub.aic.values, weights=w)
    aqs = np.concatenate([w[i] * sub.aq.values[i] for i in range(len(sub))])
    ays = np.concatenate(list(sub.ay.values)); aqu = np.concatenate(list(sub.aq.values))
    pu = pearsonr(aqu, ays)[0]; ps = pearsonr(aqs, ays)[0]
    return base, gate, frac, soft, pu, ps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="exports/final_l01/y600_backtest_dataset.csv")
    ap.add_argument("--split", type=float, default=12, help="UTC hour to split morning/afternoon")
    a = ap.parse_args()
    df = pd.read_csv(a.csv); df = df[df.y_true_ret_bps != 0].reset_index(drop=True)
    R = build(df, a.split)
    rho, p = spearmanr(R.mic, R.aic)
    print(f"=== PERSISTENCE (split={a.split}h, morning label-closed; n={len(R)} days) ===")
    print(f"rank-corr(morning IC, afternoon IC) POOLED = {rho:+.3f} (p={p:.3f})  Pearson={pearsonr(R.mic,R.aic)[0]:+.3f}  [gate 0.15]")
    for name, ms in [("strong", STRONG), ("normal", NORMAL), ("drift", DRIFT)]:
        g = R[R.month.isin(ms)]
        if len(g) > 5:
            print(f"  regime {name:6s}: rho={spearmanr(g.mic,g.aic)[0]:+.3f} n={len(g)}")
    for mk, g in R.groupby("month"):
        if len(g) >= 8:
            print(f"    {mk}: rho={spearmanr(g.mic,g.aic)[0]:+.3f} n={len(g)}")
    print(f"\n=== CAUSAL INTRADAY SCALER (afternoon sizing = f(morning IC)) ===")
    print(f"{'set':8s} {'uncond':>8s} {'gate>0':>8s} {'%kept':>6s} {'soft':>8s} | {'pool_u':>8s} {'pool_s':>8s} {'Δpool':>8s}")
    for name, sub in [("ALL", R), ("DRIFT", R[R.month.isin(DRIFT)])] + [(mk, g) for mk, g in R.groupby("month") if len(g) >= 8]:
        b, gt, fr, sf, pu, ps = scaler(sub)
        print(f"{name:8s} {b:+8.4f} {gt:+8.4f} {fr:6.0%} {sf:+8.4f} | {pu:+8.4f} {ps:+8.4f} {ps-pu:+8.4f}")
    sub = R[R.month.isin(DRIFT)]; order = np.argsort(sub.aic.values)[::-1]
    lift = sub[sub.mic > 0].aic.mean() - sub.aic.mean()
    d3 = sub.iloc[order[3:]]; lift3 = d3[d3.mic > 0].aic.mean() - d3.aic.mean()
    print(f"\nDRIFT gate lift={lift:+.4f}  leave-top-3-days-out={lift3:+.4f} (concentration check)")
    print("DONE_INTRADAY_SELFASSESS.")


if __name__ == "__main__":
    main()
