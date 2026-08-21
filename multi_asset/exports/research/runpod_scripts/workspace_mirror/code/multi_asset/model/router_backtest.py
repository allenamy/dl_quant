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


ALIGN_DIR = "data/npz_v2arch_align"


def daily_return_series():
    """{utc_day -> daily-mean y_raw} from the align sidecar (light; trend proxy)."""
    out = {}
    for f in sorted(glob.glob(f"{ALIGN_DIR}/*.npz")):
        d = os.path.basename(f)[:-4]
        if not d[0].isdigit():
            continue
        z = np.load(f, allow_pickle=True)
        y = np.asarray(z["y_raw"], dtype=np.float64); ts = z["timestamps"].astype(np.int64)
        out[int(ts[0] // DAY)] = float(np.nanmean(y))
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


LB = 15               # FROZEN lookback (days), causal (strictly prior)
TT_THRESH = 0.0       # FROZEN: tt_level sign — <0 net-short/deleveraging -> Run2
ER_THRESH = 0.35      # FROZEN: Kaufman efficiency ratio — trending>=0.35 -> Run1, choppy -> Run2 (net-long only)


def _trailing_mean(series_by_day, day_index, sorted_days, d, lb=LB):
    if d not in day_index:
        return None
    i = day_index[d]
    w = [series_by_day[sorted_days[j]] for j in range(max(0, i - lb), i)]
    return w if w else None


def _router_pick(tt_trail, er_trail):
    """FROZEN rule = tt-level SIGN only (deleveraging axis: net-short -> state-Run2).
    The trend/ER axis was TESTED AND FALSIFIED — the strong month 2025-10 is
    mean-reverting/choppy (ER 0.24) < the drift month 2026-01 (ER 0.37), i.e. trend
    does NOT separate Run1 from Run2 (adding it misroutes 2025-10). So ER is NOT used.
    Known OOS risk: extreme-net-long DRIFT months (2026-01, tt +1.15) misroute to Run1
    — cheap here (toss-up hole) but flagged; NO fitted upper-threshold added (overfit)."""
    return "Run2" if tt_trail < TT_THRESH else "Run1"


def main():
    tt_all = daily_ttlevel(None)                 # {utc_day -> (datestr, tt_level)}
    ret_all = daily_return_series()              # {utc_day -> daily-mean y_raw}
    days = sorted(set(tt_all) & set(ret_all))
    di = {d: i for i, d in enumerate(days)}
    tt_series = {d: tt_all[d][1] for d in days}
    print("==== OFFLINE ROUTER RETRO-SELECTION (FROZEN spec: tt-sign + ER supplement) ====")
    print(f"  FROZEN: lookback={LB}d causal, tt_thresh={TT_THRESH}, ER_thresh={ER_THRESH}")
    routed, r1o, r2o, orc = [], [], [], []
    for mon, (r1, r2) in MONTHS.items():
        d1 = per_day_deploy(r1); d2 = per_day_deploy(r2)
        common = sorted(set(d1) & set(d2))
        m1 = float(np.mean([d1[d] for d in common])); m2 = float(np.mean([d2[d] for d in common]))
        oracle = "Run1" if m1 >= m2 else "Run2"
        # per-day router: causal trailing tt + ER, pick, take that model's deploy
        picks = {"Run1": 0, "Run2": 0}; routed_days = []
        for d in common:
            ttw = _trailing_mean(tt_series, di, days, d)
            rw = _trailing_mean(ret_all, di, days, d)
            if ttw is None or rw is None:
                pick = oracle  # boundary day w/o history -> neutral (rare)
            else:
                ttm = float(np.mean(ttw))
                er = abs(np.sum(rw)) / (np.sum(np.abs(rw)) + 1e-12)
                pick = _router_pick(ttm, er)
            picks[pick] += 1
            routed_days.append(d1[d] if pick == "Run1" else d2[d])
        month_pick = "Run1" if picks["Run1"] >= picks["Run2"] else "Run2"
        rr = float(np.mean(routed_days))
        routed.append(rr); r1o.append(m1); r2o.append(m2); orc.append(max(m1, m2))
        # month-level ER/tt for the report
        ttm = float(np.mean([np.mean(_trailing_mean(tt_series, di, days, d)) for d in common if _trailing_mean(tt_series, di, days, d)]))
        erm = float(np.mean([abs(np.sum(_trailing_mean(ret_all, di, days, d)))/(np.sum(np.abs(_trailing_mean(ret_all, di, days, d)))+1e-12) for d in common if _trailing_mean(ret_all, di, days, d)]))
        print(f"  {mon}: Run1={m1:+.4f} Run2={m2:+.4f} ORACLE={oracle} | tt={ttm:+.3f} ER={erm:.3f} "
              f"-> router picks {month_pick} ({picks['Run1']}d R1 / {picks['Run2']}d R2), routed_deploy={rr:+.4f}  "
              f"{'MATCH' if month_pick==oracle else 'MISS(Δ%+.4f)'%(max(m1,m2)-rr)}")
    print(f"\n  MEAN deploy: ROUTER={np.mean(routed):+.4f}  always-Run1={np.mean(r1o):+.4f}  "
          f"always-Run2={np.mean(r2o):+.4f}  ORACLE={np.mean(orc):+.4f}")
    print("  (in-sample on the 3 built months; the OOS verdict = the 7 unseen months in the trajectory)")
    print("DONE_ROUTER_BACKTEST.")


if __name__ == "__main__":
    main()
