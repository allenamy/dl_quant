"""Offline retro-selection test for the causal REGIME-STATE router (team-lead
2026-07-04). Route on WHAT THE MARKET IS (positioning tt_level), NOT on model
recent performance (trailing-IC falsified: doesn't persist overnight, H4).

Router indicator: causal trailing tt_level (top-trader long/short, state idx 11)
over a pre-registered lookback. Rule: strong/trending (net-long tt_level) ->
Run1-bugfix; deleveraging/drift (net-short / low tt_level) -> Run2-state.

Decisive gate: does the CAUSAL indicator retro-select the better model per month
WITHOUT peeking? Oracle = whichever of Run1/Run2 has higher deploy that month.
If the causal tt_level ranking disagrees with the oracle on the months we have,
the boundary is not causally routable -> report the oracle-vs-causal gap and stop.
"""
from __future__ import annotations
import glob, os
import numpy as np

HZ = 600_000_000
DAY = 86_400_000_000
STATE_TT = 11  # tt_level index in the 18-d state overlay

MONTHS = {
    "2025-10": ("d1_2025_10_run1", "d1_2025_10_run2"),
    "2026-01": ("d1_2026_01_run1", "d1_2026_01_run2"),
    "2026-04": ("d1_2026_04_run1", "d1_2026_04_run2"),
}
EXP = "experiments/d1gate"
STATE_DIR = "data/npz_v2arch_state"


def _pear(a, b):
    a = a - a.mean(); b = b - b.mean(); d = np.sqrt((a*a).sum()*(b*b).sum())
    return float((a*b).sum()/d) if d > 0 else 0.0


def _nonoverlap(ts):
    idx = np.argsort(ts, kind="stable"); keep=[]; last=None
    for i in idx:
        if last is None or ts[i]-last >= HZ:
            keep.append(i); last=ts[i]
    return np.array(keep, dtype=int)


def _demean_1h(pred, ts):
    W = 3600*1_000_000; out = np.empty_like(pred, dtype=np.float64); day = ts//DAY
    for d in np.unique(day):
        idx = np.where(day==d)[0]; order = idx[np.argsort(ts[idx], kind="stable")]
        tso = ts[order].astype(np.int64); po = pred[order].astype(np.float64)
        cs = np.concatenate([[0.0], np.cumsum(po)])
        lo = np.searchsorted(tso, tso-W, side="left"); hi = np.searchsorted(tso, tso, side="right")
        out[order] = po - (cs[hi]-cs[lo])/np.maximum(hi-lo, 1)
    return out


def per_day_deploy(run):
    """Return {utc_day:int -> deploy cd} for a raw-y preds dir."""
    z = np.load(f"{EXP}/{run}/fold_0/ema_test_preds.npz", allow_pickle=True)
    pr = z["predictions"]; q = (pr[:,1] if pr.ndim==2 else pr).astype(np.float64)
    y = z["targets"].astype(np.float64);  y = y[:,-1] if y.ndim==2 else y
    ts = z["timestamps"].astype(np.int64)
    m = z["mask"].astype(bool) if "mask" in z.files else np.ones(len(q), bool)
    m = m[:,-1] if m.ndim==2 else m
    q, y, ts = q[m], y[m], ts[m]
    sig = float(np.load(f"{EXP}/{run}/fold_0/norm_params.npz")["y_sigma"])
    pdm = _demean_1h(sig*q, ts)
    day = ts//DAY; out={}
    for d in np.unique(day):
        idx = np.where(day==d)[0]; sub = idx[_nonoverlap(ts[idx])]
        if len(sub) > 20 and pdm[sub].std() > 1e-12:
            out[int(d)] = _pear(pdm[sub], y[sub])
    return out


def daily_ttlevel(month):
    """Daily-mean tt_level for every state-cache day (causal series for trailing)."""
    out = {}
    for f in sorted(glob.glob(f"{STATE_DIR}/*.npz")):
        d = os.path.basename(f)[:-4]
        if not d[0].isdigit():
            continue
        z = np.load(f, allow_pickle=True)
        st = z["state"]; ts = z["timestamps"].astype(np.int64)
        out[int(ts[0]//DAY)] = (d, float(np.nanmean(st[:, STATE_TT])))
    return out


def main():
    tt_all = daily_ttlevel(None)   # {utc_day -> (datestr, tt_level)}
    days_sorted = sorted(tt_all.keys())
    tt_series = np.array([tt_all[d][1] for d in days_sorted])
    day_index = {d: i for i, d in enumerate(days_sorted)}
    print("==== OFFLINE ROUTER RETRO-SELECTION (causal tt_level idx 11) ====")
    rows = []
    for mon, (r1, r2) in MONTHS.items():
        d1 = per_day_deploy(r1); d2 = per_day_deploy(r2)
        common = sorted(set(d1) & set(d2))
        m1 = float(np.mean([d1[d] for d in common])); m2 = float(np.mean([d2[d] for d in common]))
        oracle = "Run1" if m1 >= m2 else "Run2"
        # causal trailing tt_level: 15d mean STRICTLY BEFORE each test day, then month-mean
        LB = 15; tts = []
        for d in common:
            if d in day_index:
                i = day_index[d]; w = tt_series[max(0, i-LB):i]  # strictly before d
                if len(w): tts.append(float(np.mean(w)))
        tt_causal = float(np.mean(tts)) if tts else float("nan")
        tt_contemp = float(np.mean([tt_all[d][1] for d in common if d in tt_all]))
        rows.append((mon, m1, m2, oracle, tt_causal, tt_contemp))
        print(f"  {mon}: Run1_deploy={m1:+.4f}  Run2_deploy={m2:+.4f}  ORACLE={oracle}  "
              f"tt_causal(15d-prior)={tt_causal:+.3f}  tt_contemp={tt_contemp:+.3f}")
    # Does tt_level rank the oracle? (higher tt -> Run1-better expected)
    print("\n  SEPARATION CHECK: sort months by causal tt_level, see if it splits Run1- vs Run2-oracle")
    for mon, m1, m2, oracle, ttc, _ in sorted(rows, key=lambda r: -r[4]):
        print(f"    tt_causal={ttc:+.3f}  {mon}  oracle={oracle}  (Δdeploy Run1-Run2={m1-m2:+.4f})")
    print("DONE_ROUTER_BACKTEST.")


if __name__ == "__main__":
    main()
