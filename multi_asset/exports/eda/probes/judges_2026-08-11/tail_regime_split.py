"""Strong-month vs pooled vs drift TAIL decomposition (lead's exact question: is the fat tail
taker-viable in STRONG months but NOT pooled?). Imports the audited engine; independent round-trip
(conservative max-cost). Strong/drift split is PRE-REGISTERED from the regime-dependence memory
(2025-09/10/11 = trending/strong; 2026-01..05 = drift), NOT fit to outcome."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
from multi_asset.eval.taker_backtest import (load_preds, nonoverlap_grid, decision_center,
                                             calibrate_offtest, DAY, MONTHS)

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
STRONG = ["2025_09", "2025_10", "2025_11"]          # trending (2025_08 = calib warmup, ê=0)
DRIFT  = ["2026_01", "2026_02", "2026_03", "2026_04", "2026_05"]
TAKER = 1.7; RT = 2 * TAKER; W = 12
FRACS = (0.10, 0.05, 0.02, 0.01)

df = load_preds(f"{MA}/exports/run1_commonY.csv")
G = nonoverlap_grid(df)
ts = G.ts.values.astype(np.int64); y = G.y.values; p = G.p.values; mon = G.month.values
eh = calibrate_offtest(p - decision_center(p, W), y, mon)
cal = eh != 0.0; ae = np.abs(eh); day = ts // DAY
yrs = max((ts.max() - ts.min()) / (365.25 * DAY), 1e-9)


def tail_on(mask_group, f, seed=0, nboot=3000):
    """top-f of |ê| WITHIN the group (pooled-within-group cutoff). Independent round-trips."""
    g = mask_group & cal
    if g.sum() < 20:
        return None
    thr = float(np.quantile(ae[g], 1.0 - f))
    sel = g & (ae >= thr)
    n = int(sel.sum())
    if n == 0:
        return None
    sgn = np.sign(eh[sel]); yy = y[sel]; gk = sgn * yy
    gross = float(gk.sum()); per_side = gross / (2 * n); net = gross - RT * n
    hit = float(np.mean(sgn == np.sign(yy)))
    # day-block bootstrap of net
    ds = pd.Series(gk - RT).groupby(day[sel]).sum().values; nd = len(ds)
    rng = np.random.default_rng(seed)
    boots = np.array([ds[rng.integers(0, nd, nd)].sum() for _ in range(nboot)]) if nd > 1 else np.array([net])
    return dict(n=n, per_side=per_side, clears=per_side > TAKER, net=net, hit=hit,
                bpos=float(np.mean(boots > 0)))


def block(name, mask):
    print(f"\n=== {name}  ({int((mask & cal).sum())} calibrated periods) ===")
    print(f"{'top-f':>7s} {'#tr':>5s} {'per_side':>8s} {'clears1.7':>9s} {'net_bps':>9s} {'hit':>5s} {'boot>0':>7s}")
    for f in FRACS:
        r = tail_on(mask, f)
        if r is None:
            print(f"{f*100:6.1f}%   (too few)"); continue
        print(f"{f*100:6.1f}% {r['n']:5d} {r['per_side']:8.3f} {'YES' if r['clears'] else 'no':>9s} "
              f"{r['net']:9.1f} {r['hit']:5.3f} {r['bpos']:7.2f}")


all_mask = np.ones(len(mon), bool)
strong_mask = np.isin(mon, STRONG)
drift_mask = np.isin(mon, DRIFT)
block("POOLED (all months)", all_mask)
block("STRONG (2025-09/10/11, pre-registered trending)", strong_mask)
block("DRIFT (2026-01..05, pre-registered)", drift_mask)

# per-month fat-tail (each month's OWN top-5%) — which months' fat tails clear 1.7?
print("\n=== PER-MONTH fat tail (each month's own top-5% |ê|): which clear taker 1.7? ===")
print(f"{'month':>8s} {'#tr':>5s} {'per_side':>8s} {'clears':>6s} {'net':>8s} {'hit':>5s}   regime")
for mk in MONTHS:
    r = tail_on(mon == mk, 0.05)
    reg = "STRONG" if mk in STRONG else ("drift" if mk in DRIFT else "warmup/trans")
    if r is None:
        print(f"{mk:>8s}   (too few / warmup)                          {reg}"); continue
    print(f"{mk:>8s} {r['n']:5d} {r['per_side']:8.3f} {'YES' if r['clears'] else 'no':>6s} "
          f"{r['net']:8.1f} {r['hit']:5.3f}   {reg}")
