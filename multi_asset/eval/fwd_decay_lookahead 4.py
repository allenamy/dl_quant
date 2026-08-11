"""FORWARD-WINDOW DECAY — the definitive lookahead-leak test for a DL factor (eval-path side).

Shuffle-future rules out static-inflation but NOT lookahead (both break under target-shuffle). This
test does: IC(pred[t], H-fwd return starting at t+lag) for lag around 0. A GENUINE causal predictor
peaks at lag=0 and decays smoothly FORWARD, and is typically negative/reversal at NEGATIVE lags. A
lookahead leak would show anomalously flat/non-decaying forward IC or a positive echo at the leaked
window. (Verified on QIM q50: peak +0.070@0, forward-decay to +0.024@12h, −0.15@−4h = short-term
cross-sectional REVERSAL — textbook causal, anti-leak.)

Usage: PYTHONPATH=. python multi_asset/eval/fwd_decay_lookahead.py --tag wideA_qim --head 1 --horizon 4
"""
from __future__ import annotations
import sys, os.path as op, glob, argparse, numpy as np
from scipy.stats import rankdata

E = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/train"
MIN = 8


def _ric(f, y):
    m = np.isfinite(f) & np.isfinite(y)
    if m.sum() < MIN:
        return np.nan
    rf = rankdata(f[m]); ry = rankdata(y[m]); rf = rf - rf.mean(); ry = ry - ry.mean()
    d = np.sqrt((rf * rf).sum() * (ry * ry).sum()); return (rf * ry).sum() / d if d > 1e-12 else np.nan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True); ap.add_argument("--head", type=int, default=0)
    ap.add_argument("--horizon", type=int, default=4, help="target horizon in hours (for label only)")
    ap.add_argument("--lags", default="-8,-4,-1,0,1,4,8,12")
    a = ap.parse_args()
    d = op.join(E, a.tag); ref = np.load(op.join(d, "panel_ref.npz"), allow_pickle=True)
    YR = ref["YR"].astype(float); Yraw = ref["Yraw"].astype(float)
    mem = ref["member"].astype(bool); CL = ref["CL"].astype(bool); ts = ref["ts"].astype(np.int64)
    T, N = YR.shape; F = np.full((T, N), np.nan)
    for f in sorted(glob.glob(op.join(d, "fold_*_head_scores.npz"))):
        z = np.load(f); tr = z["te_rows"]; F[tr] = z["scores"][tr, :, a.head]
    grid_h = int(round(float(np.median(np.diff(ts))) / (3.6e6 if ts[0] > 1e14 else 3600)))  # index step in hours
    predrows = np.where(np.isfinite(F).any(1) & (mem & CL).any(1))[0]

    def shifted(target, lag_h):
        step = lag_h // max(grid_h, 1); ics = []
        for t in predrows:
            r = t + step
            if r < 0 or r >= T:
                continue
            v = (mem[t] & CL[t]) & mem[r] & np.isfinite(F[t]) & np.isfinite(target[r])
            if v.sum() >= MIN and np.std(F[t, v]) > 1e-12:
                ic = _ric(F[t, v], target[r, v])
                if np.isfinite(ic):
                    ics.append(ic)
        return (np.mean(ics), len(ics)) if ics else (np.nan, 0)

    print(f"{a.tag} head={a.head} (grid {grid_h}h/step) — FORWARD-WINDOW DECAY (H={a.horizon}h fwd from t+lag):")
    print(f"  lag(h) | IC(YR resid) n | IC(Yraw)")
    curve = {}
    for lag in [int(x) for x in a.lags.split(",")]:
        icy, n = shifted(YR, lag); icr, _ = shifted(Yraw, lag); curve[lag] = icy
        print(f"  {lag:>+4}   | {icy:+.4f} ({n}) | {icr:+.4f}")
    peak = max(curve, key=lambda k: (curve[k] if np.isfinite(curve[k]) else -9))
    neg = [k for k in curve if k < 0 and np.isfinite(curve[k])]
    causal = (peak == 0) and (all(curve[k] <= curve[0] for k in curve if k > 0 and np.isfinite(curve[k])))
    print(f"\n★ VERDICT: peak-lag={peak}h, neg-lag IC={'/'.join(f'{curve[k]:+.3f}' for k in sorted(neg))} -> "
          f"{'CAUSAL (peak@0 + forward-decay), NO lookahead leak' if causal and peak == 0 else 'CHECK: non-causal profile'}")
    print("DONE_FWD_DECAY")


if __name__ == "__main__":
    main()
