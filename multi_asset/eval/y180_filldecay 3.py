"""y180 RE-PRICE Part B — the DECISIVE physics check: FILL-WINDOW DECAY.

A 3-min (180s) signal lives INSIDE the 5s-5min adverse-selection window. Passive fills take ~30-60s;
entering that late on a 180s signal eats a large fraction of the alpha (unlike the 60-min M0, whose
alpha outlives the adverse-selection window). Estimate: what % of the y180 cs-rank-IC survives an
entry delay of lag ∈ {0,30,60,120}s? Using 1s mid from the day panels: IC(pred_t, ret[t+lag → t+lag+180]).

If IC decays sharply in the first 30-60s → NO (can't fill fast enough passively without eating it),
regardless of the cheap-cost Part-A pass. If it survives (≥~60-70% at 60s) → revival candidate.

Usage: PYTHONPATH=. python multi_asset/eval/y180_filldecay.py --tag R1_y180 --days 30
"""
from __future__ import annotations
import sys, os.path as op, glob, argparse, numpy as np
sys.path.insert(0, op.abspath(op.join(op.dirname(__file__), "..", "..")))
from scipy.stats import rankdata
from multi_asset.data.bar_loader import load_day_panel

EXPORT = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/train"
SYMBOLS = ["bnfbtc", "bnfeth", "bnfsol", "bnfbnb", "bnfxrp", "bnfdog", "bnfada",
           "bnflink", "bnfbch", "bnftrx", "bnfltc", "bnfdot", "bnffil", "bnfetc"]
LAGS = [0, 30, 60, 120]
H = 180
MIN = 5


def load_pred(tag):
    d = op.join(EXPORT, tag); ref = np.load(op.join(d, "panel_ref.npz"), allow_pickle=True)
    ts, day, CL = ref["ts"].astype(np.int64), ref["day"], ref["CL"].astype(bool)
    T, S = CL.shape; pred = np.full((T, S), np.nan, np.float32)
    for f in sorted(glob.glob(op.join(d, "fold_*_preds.npz"))):
        z = np.load(f); rows = z["te_rows"]; pred[rows] = z["pred"][rows]
    return ts, day, CL, pred


def _ric(f, y):
    m = np.isfinite(f) & np.isfinite(y)
    if m.sum() < MIN:
        return np.nan
    rf = rankdata(f[m]); ry = rankdata(y[m]); rf = rf - rf.mean(); ry = ry - ry.mean()
    d = np.sqrt((rf * rf).sum() * (ry * ry).sum()); return float((rf * ry).sum() / d) if d > 1e-12 else np.nan


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--tag", default="R1_y180"); ap.add_argument("--days", type=int, default=30)
    a = ap.parse_args()
    ts, day, CL, pred = load_pred(a.tag)
    cl_days = np.unique(day[CL.any(1)])
    step = max(1, len(cl_days) // a.days); sample = cl_days[::step][:a.days]
    print(f"[filldecay] tag={a.tag} | {len(sample)} days sampled | lags {LAGS}s | horizon {H}s", flush=True)

    ics = {lag: [] for lag in LAGS}
    for d in sample:
        try:
            dp = load_day_panel(int(d), SYMBOLS)
        except Exception as e:
            continue
        mids = {}
        for s in SYMBOLS:
            try:
                mids[s] = dp.data[s][:, dp.cols.index("mid")].astype(np.float64)
            except Exception:
                mids[s] = None
        dts = dp.ts.astype(np.int64)
        drows = np.where((day == d) & CL.any(1))[0]
        for t in drows:
            v = CL[t] & np.isfinite(pred[t])
            if v.sum() < MIN:
                continue
            bi = int(np.searchsorted(dts, ts[t]))
            if bi <= 0 or bi >= len(dts):
                continue
            for lag in LAGS:
                pv = []; rv = []
                for si in np.where(v)[0]:
                    m = mids[SYMBOLS[si]]
                    if m is None or bi + lag + H >= len(m) or not (m[bi + lag] > 0):
                        continue
                    ret = (m[bi + lag + H] - m[bi + lag]) / m[bi + lag] * 1e4
                    pv.append(pred[t, si]); rv.append(ret)
                if len(pv) >= MIN:
                    ic = _ric(np.array(pv), np.array(rv))
                    if np.isfinite(ic):
                        ics[lag].append(ic)

    print(f"\n{'lag(s)':>6} {'mean-IC':>9} {'n_ts':>7} {'% of lag0':>10}")
    ic0 = np.mean(ics[0]) if ics[0] else np.nan
    for lag in LAGS:
        m = np.mean(ics[lag]) if ics[lag] else np.nan
        pct = m / ic0 * 100 if (np.isfinite(ic0) and ic0 != 0) else np.nan
        print(f"{lag:>6} {m:>+9.4f} {len(ics[lag]):>7} {pct:>9.0f}%")
    surv60 = (np.mean(ics[60]) / ic0 * 100) if (ics[60] and np.isfinite(ic0) and ic0 != 0) else np.nan
    print(f"\n★ FILL-DECAY: {surv60:.0f}% of the y180 alpha survives a 60s passive-fill delay "
          f"({'SURVIVES → revival candidate' if surv60 >= 60 else 'DECAYS → the 3-min-inside-adverse-selection killer'})")
    print("DONE_Y180_FILLDECAY")


if __name__ == "__main__":
    main()
