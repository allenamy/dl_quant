"""DEPLOY-SIDE intraday confidence scaler — within-day split + DUAL causal self-gate. A position-sizing
layer, NOT a model change; composes ON TOP of ANY one-model preds (production / state-only / combo).

WHY WITHIN-DAY, NOT A ROLLING WINDOW (falsification — do not retry trailing windows): the model's
realized-IC self-persistence is a SAME-DAY-REGIME effect (a day is globally good-IC or bad-IC; morning
& afternoon share it), NOT a rolling persistence. Sub-daily block-IC -> next-block rho ~0 at every K
(K=4h -0.018, K=6h -0.055, consecutive-12h +0.019) vs within-day morning->afternoon +0.174 (drift
+0.228). A trailing-Kh window crosses the overnight boundary and washes it out (empirically hurts every
regime). So: size each day's afternoon by THAT day's morning realized IC (causal — morning labels
closed by the split, i.e. <=t-600s).

DUAL SELF-GATE (conditional deploy; causal, self-referential — the model's OWN errors, not H2-refuted
static descriptors): enable the scaler for a day only when BOTH
  (i) trailing-15d mean daily IC < 0.05  (model currently WEAK — where the scaler helps), AND
  (ii) trailing-30d rank-corr(morning IC, afternoon IC) > 0  (the persistence is currently live).
This fully protects strong months (gate off, delta=0.000), keeps the drift gain (~2x), and halves the
2026-05 residual (the one drift month where morning->afternoon persistence is absent).

Composes on any preds: --preds a backtest CSV (timestamp_ms,y_pred_raw,y_true_ret_bps,month) OR a dir
of wf_<month>/fold_0/ema_test_preds.npz (Pearson is scale-invariant, so normalized npz preds are fine).

Run LOCAL:
  python multi_asset/eval/intraday_scaler.py --preds exports/final_l01/y600_backtest_dataset.csv
"""
from __future__ import annotations
import numpy as np, pandas as pd, argparse, glob, os
from scipy.stats import pearsonr, spearmanr

SEC = 1000; HZ = 600 * SEC; DAY = 86400 * SEC
DRIFT = ["2026_01", "2026_02", "2026_03", "2026_04", "2026_05"]
STRONG = ["2025_10", "2025_11"]; NORMAL = ["2025_08", "2025_09", "2025_12"]
MONTHS = ["2025_08", "2025_09", "2025_10", "2025_11", "2025_12"] + DRIFT


def load_df(source):
    """CSV backtest OR a dir of wf_<month>/fold_0/ema_test_preds.npz -> [timestamp_ms,y_pred_raw,y_true_ret_bps,month]."""
    if source.endswith(".csv"):
        d = pd.read_csv(source)
        return d[["timestamp_ms", "y_pred_raw", "y_true_ret_bps", "month"]]
    rows = []
    for f in sorted(glob.glob(os.path.join(source, "wf_*/fold_0/ema_test_preds.npz"))):
        mk = f.split("wf_")[1][:7]
        z = np.load(f, allow_pickle=True); pr = z["predictions"]
        q = (pr[:, 1] if pr.ndim == 2 else pr); y = z["targets"]; ts = z["timestamps"].astype(np.int64)
        ts = ts // 1000 if ts[0] > 3_000_000_000_000 else ts     # us -> ms
        m = z["mask"].astype(bool) if "mask" in z.files else np.ones(len(y), bool)
        rows.append(pd.DataFrame({"timestamp_ms": ts[m], "y_pred_raw": q[m], "y_true_ret_bps": y[m], "month": mk}))
    return pd.concat(rows, ignore_index=True)


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


def build_days(df, split_h=12):
    df = df[df.y_true_ret_bps != 0].reset_index(drop=True)
    ts = df.timestamp_ms.values.astype(np.int64); y = df.y_true_ret_bps.values.astype(float)
    q = df.y_pred_raw.values.astype(float); mo = df.month.values
    tod = (ts // SEC) % 86400; day = ts // DAY; cut = split_h * 3600
    rows = []
    for d in np.unique(day):
        m = np.where((day == d) & (tod <= cut - 600))[0]
        a = np.where((day == d) & (tod >= cut))[0]
        aall = np.where(day == d)[0]
        mic = _ic(ts, q, y, m); aic = _ic(ts, q, y, a); fic = _ic(ts, q, y, aall)
        if np.isfinite(mic) and np.isfinite(aic):
            rows.append((int(d), mo[m[0]], mic, aic, fic))
    return pd.DataFrame(rows, columns=["day", "month", "mic", "aic", "fic"]).sort_values("day").reset_index(drop=True)


def wmean(ic, w):
    ic = np.asarray(ic); w = np.asarray(w); ok = np.isfinite(ic) & np.isfinite(w)
    return float(np.sum(w[ok] * ic[ok]) / np.sum(w[ok])) if ok.any() else np.nan


def dual_gate(R, gate_days=15, ic_thr=0.05, rho_days=30):
    """Causal per-day enable: (trailing-Nd mean daily IC < thr) AND (trailing-Md morning->afternoon rho > 0)."""
    day = R.day.values; g = np.zeros(len(R), bool)
    for i in range(len(R)):
        p = R.iloc[:i]
        pic = p[p.day >= day[i] - gate_days]
        gi = (len(pic) >= 5) and (np.nanmean(pic.fic.values) < ic_thr)
        prho = p[p.day >= day[i] - rho_days]
        gr = False
        if len(prho) >= 10:
            rr = spearmanr(prho.mic.values, prho.aic.values)[0]
            gr = bool(np.isfinite(rr) and rr > 0)
        g[i] = gi and gr
    return g


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preds", default="exports/final_l01/y600_backtest_dataset.csv")
    a = ap.parse_args()
    R = build_days(load_df(a.preds))
    gate = dual_gate(R)
    w = np.where(gate, np.clip(0.5 + 3 * R.mic.values, 0, 1.5), 1.0)
    mon = R.month.values; aic = R.aic.values
    print(f"preds={a.preds}  days={len(R)}")
    print(f"\n=== FINAL per-month DEPLOY LIFT (afternoon per-day-CLEAN IC; base -> dual-self-gated scaler) ===")
    print(f"{'month':8s} {'base':>9s} {'scaled':>9s} {'delta':>9s} {'gate%':>6s}")
    for mk in MONTHS:
        idx = mon == mk
        if idx.sum() < 8:
            continue
        b = float(np.nanmean(aic[idx])); s = wmean(aic[idx], w[idx])
        print(f"{mk:8s} {b:+9.4f} {s:+9.4f} {s-b:+9.4f} {np.mean(gate[idx]):6.0%}")
    print("regime:")
    for nm, ms in [("drift", DRIFT), ("strong", STRONG), ("normal", NORMAL)]:
        idx = np.isin(mon, ms); b = float(np.nanmean(aic[idx])); s = wmean(aic[idx], w[idx])
        print(f"  {nm:6s}: base {b:+.4f} -> scaled {s:+.4f}  delta {s-b:+.4f}")
    print("DONE_INTRADAY_SCALER.")


if __name__ == "__main__":
    main()
