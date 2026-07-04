"""DEPLOY-SIDE intraday confidence scaler — WITHIN-DAY split form + causal self-gating. Position-sizing
layer, NOT a model change; composes ON TOP of any one-model prediction.

WHY WITHIN-DAY, NOT A ROLLING WINDOW: the model's realized-IC self-persistence is a SAME-DAY-REGIME
effect (morning & afternoon IC share the day's overall predictability), NOT a rolling persistence.
Evidence (sub-daily block IC -> next block IC): K=4h rho -0.018, K=6h -0.055, consecutive-12h +0.019
-- all ~0, vs the within-day morning->afternoon rho +0.174 (drift +0.228). A continuous trailing-Kh
window crosses the overnight boundary and washes the signal out (empirically it HURTS every regime).
So the operative form is the within-day split: size each day's afternoon by that day's morning
realized IC (causal: morning labels closed by the split, so it's <=t-600s).

SELF-GATING (conditional deploy): the scaler helps weak/drift days but hurts already-strong days.
Gate it ON only when the model's recent realized performance is WEAK (trailing-Nd mean daily IC below
a threshold) -- causal, self-referential (uses the model's own past errors, not static descriptors,
so it is not the H2-refuted day-descriptor gate). Verify it keeps the drift gain and removes the
strong-month damage.

Run LOCAL:
  python multi_asset/eval/intraday_scaler.py --csv exports/final_l01/y600_backtest_dataset.csv
"""
from __future__ import annotations
import numpy as np, pandas as pd, argparse
from scipy.stats import pearsonr, spearmanr

SEC = 1000; HZ = 600 * SEC; DAY = 86400 * SEC; HOUR = 3600 * SEC
DRIFT = ["2026_01", "2026_02", "2026_03", "2026_04", "2026_05"]
STRONG = ["2025_10", "2025_11"]; NORMAL = ["2025_08", "2025_09", "2025_12"]
MONTHS = ["2025_08", "2025_09", "2025_10", "2025_11", "2025_12"] + DRIFT


def _nono(t):
    o = np.argsort(t); k = []; last = -1e18
    for i in o:
        if t[i] - last >= HZ:
            k.append(i); last = t[i]
    return np.array(k, int)


def _ic(ts, q, y, idx, minr=15, minp=12):
    if len(idx) < minr:
        return np.nan
    k = _nono(ts[idx])
    if len(k) < minp:
        return np.nan
    qq = q[idx][k]; yy = y[idx][k]
    return pearsonr(qq, yy)[0] if (qq.std() > 1e-9 and yy.std() > 1e-9) else np.nan


def build_days(csv, split_h=12):
    df = pd.read_csv(csv); df = df[df.y_true_ret_bps != 0].reset_index(drop=True)
    ts = df.timestamp_ms.values.astype(np.int64); y = df.y_true_ret_bps.values.astype(float)
    q = df.y_pred_raw.values.astype(float); mo = df.month.values
    tod = (ts // SEC) % 86400; day = ts // DAY; cut = split_h * 3600
    rows = []
    for d in np.unique(day):
        m = np.where((day == d) & (tod <= cut - 600))[0]        # morning, label-closed by split
        a = np.where((day == d) & (tod >= cut))[0]
        aall = np.where((day == d) & (tod >= 0))[0]              # full-day (for base regime IC)
        mic = _ic(ts, q, y, m); aic = _ic(ts, q, y, a); fic = _ic(ts, q, y, aall)
        if np.isfinite(mic) and np.isfinite(aic):
            rows.append((int(d), mo[m[0]], mic, aic, fic))
    return pd.DataFrame(rows, columns=["day", "month", "mic", "aic", "fic"]).sort_values("day").reset_index(drop=True)


def wmean(ic, w):
    w = np.asarray(w); ok = np.isfinite(ic) & np.isfinite(w)
    return float(np.sum(w[ok] * ic[ok]) / np.sum(w[ok])) if ok.any() else np.nan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="exports/final_l01/y600_backtest_dataset.csv")
    ap.add_argument("--gate-days", type=int, default=15)
    ap.add_argument("--gate-thr", type=float, default=0.05, help="apply scaler when trailing mean daily IC < thr")
    a = ap.parse_args()
    R = build_days(a.csv)
    print(f"days with both halves: {len(R)}")

    # causal self-gate: trailing-Nd mean full-day IC (strictly prior days) < thr  => model is weak => apply
    gate = np.zeros(len(R), bool)
    for i in range(len(R)):
        prior = R.iloc[:i]; prior = prior[prior.day >= R.day[i] - a.gate_days]
        if len(prior) >= 5:
            gate[i] = np.nanmean(prior.fic.values) < a.gate_thr
    # soft confidence weight from same-day morning IC (causal)
    wsoft = np.clip(0.5 + 3 * R.mic.values, 0, 1.5)
    w_ungated = wsoft
    w_gated = np.where(gate, wsoft, 1.0)                          # pass-through where model is currently strong

    print(f"\n{'month':8s} {'base_aft':>9s} {'ungated':>9s} {'Δ':>8s} | {'selfgate':>9s} {'Δ':>8s} {'%gate-on':>9s}")
    for mk in MONTHS:
        s = R[R.month == mk]
        if len(s) < 8:
            continue
        idx = R.month.values == mk
        base = float(np.nanmean(R.aic.values[idx]))
        ung = wmean(R.aic.values[idx], w_ungated[idx])
        sg = wmean(R.aic.values[idx], w_gated[idx])
        print(f"{mk:8s} {base:+9.4f} {ung:+9.4f} {ung-base:+8.4f} | {sg:+9.4f} {sg-base:+8.4f} {np.mean(gate[idx]):9.0%}")

    def agg(ms, w):
        idx = np.isin(R.month.values, ms)
        base = float(np.nanmean(R.aic.values[idx])); sc = wmean(R.aic.values[idx], w[idx])
        return base, sc, sc - base
    print("\n=== REGIME SUMMARY (afternoon per-day IC, weighted-mean = confidence-sized book) ===")
    for name, ms in [("drift", DRIFT), ("strong", STRONG), ("normal", NORMAL)]:
        b_u, s_u, d_u = agg(ms, w_ungated); b_g, s_g, d_g = agg(ms, w_gated)
        print(f"  {name:6s}: base {b_u:+.4f} | ungated Δ{d_u:+.4f} | SELF-GATED Δ{d_g:+.4f}")
    print("GOAL: self-gated keeps drift Δ>0 and pushes strong Δ toward 0 (removes strong-month damage).")
    print("DONE_INTRADAY_SCALER.")


if __name__ == "__main__":
    main()
