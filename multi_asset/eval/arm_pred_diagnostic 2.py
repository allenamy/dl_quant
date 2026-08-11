"""Zero-GPU decision harness for a training-distribution ARM's saved preds: is a high cd-CLEAN a
real WIN or a day/multi-hour LEVEL-calibration ARTIFACT? (Stage-1 arm gate, DENSE-sign-disagreement.)

Given an ARM preds.npz and a BASELINE preds.npz (same fold/test window), reports:
 (1)+(2) production deploy contract: causal trailing demean of the arm preds at several windows
         (1h = the backtest CSV's y_pred_demeaned contract; 12h/24h to bound the frequency band),
         WITH the baseline under the SAME demean as the decisive control — a healthy signal loses a
         modest fraction and stays +/healthy; an artifact collapses (cd -> ~0) because its edge lives
         in the >1h prediction band that the deploy demean removes.
 (3)     value-blend 0.5*arm + 0.5*baseline in RAW units (denorm each q by its own y_sigma/median),
         raw + under the 1h demean.
 (4)     per-day cd-CLEAN IC distribution: %positive days + leave-top-k-days-out (concentration).

Calibers match final_deliverable_l01.py exactly (raw q, mask applied, per-day-CLEAN = greedy >=600s
non-overlap within UTC day, per-day Pearson averaged; DENSE = plain Pearson; beta = cov(y,q)/var(q)).

Run LOCAL (zero GPU):
  python multi_asset/eval/arm_pred_diagnostic.py \
    --arm      experiments/arms/spec_2026_01/fold_0/ema_test_preds.npz \
    --baseline experiments/d1gate/d1_2026_01_run1/fold_0/ema_test_preds.npz
"""
from __future__ import annotations
import numpy as np, argparse
from collections import deque
from scipy.stats import pearsonr

SEC = 1_000_000            # timestamps are microseconds in these npz
HZ = 600 * SEC
DAY = 86400 * SEC


def load(path):
    z = np.load(path, allow_pickle=True); pr = z["predictions"]
    q = (pr[:, 1] if pr.ndim == 2 else pr).astype(np.float64)
    y = z["targets"].astype(np.float64); ts = z["timestamps"].astype(np.int64)
    m = z["mask"].astype(bool) if "mask" in z.files else np.ones(len(y), bool)
    ysig = float(z["y_sigma"]) if "y_sigma" in z.files else 1.0
    ymed = float(z["y_median"]) if "y_median" in z.files else 0.0
    o = np.argsort(ts)
    return q[o][m[o]], y[o][m[o]], ts[o][m[o]], ysig, ymed


def _clean_idx(t):
    o = np.argsort(t); keep = []; last = -1e18
    for i in o:
        if t[i] - last >= HZ:
            keep.append(i); last = t[i]
    return np.array(keep, int)


def cd_days(q, y, t):
    dk = t // DAY; rs = []
    for d in np.unique(dk):
        idx = np.where(dk == d)[0]; k = _clean_idx(t[idx])
        if len(k) > 20:
            qk = q[idx][k]; yk = y[idx][k]
            if qk.std() > 1e-12 and yk.std() > 1e-12:
                r = pearsonr(qk, yk)[0]
                if np.isfinite(r):
                    rs.append(r)
    return np.array(rs)


def cd(q, y, t):
    r = cd_days(q, y, t); return float(np.mean(r)) if len(r) else np.nan


def dense(q, y): return float(pearsonr(q, y)[0])
def beta(q, y): return float(np.cov(y, q)[0, 1] / q.var())
def sig(q, y): return float(q.std() / y.std())


def causal_demean(q, ts, win_s):
    win = win_s * SEC; o = np.argsort(ts); t = ts[o]; qs = q[o]
    out = np.empty_like(qs); dq = deque(); cs = 0.0
    for i in range(len(qs)):
        dq.append((t[i], qs[i])); cs += qs[i]
        while dq and dq[0][0] < t[i] - win:
            cs -= dq.popleft()[1]
        out[i] = qs[i] - cs / len(dq)
    r = np.empty_like(out); r[o] = out; return r


def _row(tag, q, y, t):
    print(f"  {tag:38s} cd-CLEAN={cd(q,y,t):+.4f}  DENSE={dense(q,y):+.4f}  beta={beta(q,y):+.3f}  sigma={sig(q,y):.3f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--wins", type=int, nargs="+", default=[3600, 43200, 86400])
    ap.add_argument("--blend-w", type=float, default=0.5)
    a = ap.parse_args()
    qa, ya, ta, sa, ma = load(a.arm)
    qb0, yb0, tb0, sb, mb = load(a.baseline)
    print(f"arm={a.arm}\nbaseline={a.baseline}\nn_arm={len(qa)} n_base={len(qb0)}")

    print("\n=== raw calibers ===")
    _row("BASELINE (raw)", qb0, yb0, tb0)
    _row("ARM (raw)", qa, ya, ta)
    arm_raw = cd(qa, ya, ta)

    print("\n=== (1)+(2) deploy-contract causal demean (arm vs baseline control) ===")
    for w in a.wins:
        _row(f"ARM + demean {w}s", causal_demean(qa, ta, w), ya, ta)
    base_raw = cd(qb0, yb0, tb0)
    _row(f"BASELINE + demean {a.wins[0]}s (control)", causal_demean(qb0, tb0, a.wins[0]), yb0, tb0)
    arm_dm = cd(causal_demean(qa, ta, a.wins[0]), ya, ta)
    base_dm = cd(causal_demean(qb0, tb0, a.wins[0]), yb0, tb0)
    arm_keep = arm_dm / arm_raw if arm_raw > 1e-9 else float("nan")
    base_keep = base_dm / base_raw if base_raw > 1e-9 else float("nan")
    print(f"  cd retained under {a.wins[0]}s demean:  ARM {100*arm_keep:.0f}%   BASELINE {100*base_keep:.0f}%"
          f"   (artifact <=> arm collapses while baseline holds)")

    print("\n=== (3) value-blend 0.5*arm + 0.5*baseline (raw units) ===")
    common = np.intersect1d(ta, tb0)
    ia = {t: i for i, t in enumerate(ta)}; ib = {t: i for i, t in enumerate(tb0)}
    isa = np.array([ia[t] for t in common]); isb = np.array([ib[t] for t in common])
    qar = qa[isa] * sa + ma; qbr = qb0[isb] * sb + mb; yr = ya[isa] * sa + ma; tc = ta[isa]
    qbl = (1 - a.blend_w) * qbr + a.blend_w * qar
    _row("BLEND raw", qbl, yr, tc)
    _row(f"BLEND + demean {a.wins[0]}s", causal_demean(qbl, tc, a.wins[0]), yr, tc)

    print("\n=== (4) per-day cd-CLEAN IC distribution (arm) ===")
    r = cd_days(qa, ya, ta); order = np.argsort(r)[::-1]
    print(f"  n_days={len(r)}  mean={r.mean():+.4f}  %positive={100*np.mean(r>0):.0f}%")
    print(f"  top-5={np.round(r[order[:5]],3).tolist()}  bot-5={np.round(r[order[-5:]],3).tolist()}")
    for k in (3, 5):
        print(f"  leave-top-{k}-days-out mean={r[order[k:]].mean():+.4f}")

    print("\n=== VERDICT HEURISTIC ===")
    dense_disagree = np.sign(dense(qa, ya)) != np.sign(arm_raw)
    collapses = np.isfinite(arm_keep) and np.isfinite(base_keep) and arm_keep < 0.5 * base_keep
    flag = "ARTIFACT" if (dense_disagree and collapses) else ("REVIEW" if (dense_disagree or collapses) else "clean")
    print(f"  DENSE-sign-disagreement={dense_disagree}  arm-collapses-vs-baseline={collapses}  => {flag}")
    print("DONE_ARM_DIAGNOSTIC.")


if __name__ == "__main__":
    main()
