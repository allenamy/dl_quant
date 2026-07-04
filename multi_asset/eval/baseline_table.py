"""Canonical 10-month baseline table (0A caliber) from the mask-fixed production CSV,
+ the identical per-day-CLEAN scorer for trajectory npz folds. ONE caliber for both
=> the Δ (fold - baseline) is real, not a caliber artifact (team-lead 2026-07-04).

0A recipe (honest_aggregate_causal.py): mask-fix (rows already dropped in the CSV) +
per-day-CLEAN = mean of per-UTC-day Pearson on greedy-non-overlap >=600s rows with
>20 clean rows/day; DENSE = pooled Pearson. Validated to reproduce BASE 2025-10=0.0815
/ 2026-04=0.0308.
"""
from __future__ import annotations
import csv as _csv
import numpy as np

CSV = "exports/final_l01/y600_backtest_dataset.csv"
HZ_MS = 600 * 1000
DAY_MS = 86400 * 1000
HZ_US = 600 * 1_000_000
DAY_US = 86_400_000_000


def _pear(a, b):
    a = a - a.mean(); b = b - b.mean(); d = np.sqrt((a * a).sum() * (b * b).sum())
    return float((a * b).sum() / d) if d > 0 else float("nan")


def _clean(ts, hz):
    o = np.argsort(ts, kind="stable"); keep = []; last = -1e30
    for i in o:
        if ts[i] - last >= hz:
            keep.append(i); last = ts[i]
    return np.array(keep, dtype=int)


def _cd_dense(q, y, ts, hz, day):
    q = q.astype(np.float64); y = y.astype(np.float64)
    dense = _pear(q, y)
    dk = ts // day; rs = []
    for d in np.unique(dk):
        m = np.where(dk == d)[0]; k = m[_clean(ts[m], hz)]
        if len(k) > 20 and q[k].std() > 1e-12:
            r = _pear(q[k], y[k])
            if np.isfinite(r):
                rs.append(r)
    return (float(np.mean(rs)) if rs else float("nan")), dense


def baselines_from_csv(path=CSV):
    """{month_key(e.g. 2025_08) -> (cd_clean, dense)} from the canonical CSV (raw pred vs raw y)."""
    rows = {}
    with open(path) as f:
        r = _csv.DictReader(f)
        for row in r:
            m = row["month"].replace("-", "_")
            rows.setdefault(m, [[], [], []])
            rows[m][0].append(float(row["timestamp_ms"]))
            rows[m][1].append(float(row["y_pred_raw"]))
            rows[m][2].append(float(row["y_true_ret_bps"]))
    out = {}
    for m, (ts, q, y) in rows.items():
        out[m] = _cd_dense(np.array(q), np.array(y), np.array(ts), HZ_MS, DAY_MS)
    return out


def score_fold_npz(path):
    """Same caliber on a trajectory ema_test_preds.npz (raw q50 vs raw target, mask-fixed)."""
    z = np.load(path, allow_pickle=True)
    pr = z["predictions"]; q = (pr[:, 1] if pr.ndim == 2 else pr).astype(np.float64)
    y = z["targets"].astype(np.float64); y = y[:, -1] if y.ndim == 2 else y
    ts = z["timestamps"].astype(np.int64)
    if "mask" in z.files:
        m = z["mask"].astype(bool); m = m[:, -1] if m.ndim == 2 else m
        q, y, ts = q[m], y[m], ts[m]
    return _cd_dense(q, y, ts, HZ_US, DAY_US)


if __name__ == "__main__":
    b = baselines_from_csv()
    order = ["2025_08", "2025_09", "2025_10", "2025_11", "2025_12",
             "2026_01", "2026_02", "2026_03", "2026_04", "2026_05"]
    print("==== CANONICAL 10-month baseline (0A caliber, from mask-fixed CSV) ====")
    for m in order:
        if m in b:
            print(f"  {m}: cd-CLEAN={b[m][0]:+.4f}  DENSE={b[m][1]:+.4f}")
    v10 = b.get("2025_10", (float('nan'),))[0]; v04 = b.get("2026_04", (float('nan'),))[0]
    print(f"\n  VALIDATION vs BASE: 2025_10 -> {v10:+.4f} (expect +0.0815)  2026_04 -> {v04:+.4f} (expect +0.0308)")
    ok = abs(v10 - 0.0815) < 0.003 and abs(v04 - 0.0308) < 0.003
    print("  CALIBER_MATCH" if ok else "  CALIBER_MISMATCH (investigate)")
