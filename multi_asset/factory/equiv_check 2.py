"""Full-window-scale equivalence cross-check for the vectorized max-null (lead's finishing requirement).

The 438-anchor subsample already matched (rc95 0.0120 vs 0.0123). This re-checks at full-window SCALE
(numerical stability of the vectorized large-matrix rank-corr: rank ties / float precision) by running
the fast null AND the slow per-anchor null on the SAME actual survivors + the SAME anchor set, and
comparing the max-null quantiles. Uses a full-window subsample (every 4th anchor ~2185) so the slow
null is tractable; that is ~5x the earlier 438 and exercises the large-matrix path.
"""
import json
import sys
import time

import numpy as np

sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/factory")
import dsl
import pipeline as P
from ledger import Ledger, LEDGER

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"


def slow_maxnull(facs, C, rng, null_r):
    tg = C["target"]; rows = C["rows"]
    day_of = {int(t): int(C["day"][t]) for t in rows}
    tmask = {int(t): (C["member"][t] & C["CL"][t] & np.isfinite(tg[t])) for t in rows}
    d2r = {}; [d2r.setdefault(int(C["day"][t]), int(t)) for t in rows]
    ud = np.array(sorted(d2r)); mn = []
    for _ in range(null_r):
        dm = dict(zip(ud, rng.permutation(ud))); best = -np.inf
        for factor in facs:
            ics = []
            for t in rows:
                ti = int(t); tt = d2r[dm[day_of[ti]]]
                cb = np.where(tmask[ti] & tmask[tt] & np.isfinite(factor[ti]))[0]
                if cb.size >= 8:
                    ics.append(P._ric(factor[ti, cb], tg[tt, cb]))
            if ics:
                best = max(best, float(np.nanmean(ics)))
        mn.append(best)
    return mn


def main():
    lg = Ledger(LEDGER)
    survivors = [r["formula_str"] for r in lg._rows if r.get("verdict") == "TRIAGE_SURVIVOR"][:5]
    if not survivors:
        survivors = ["xsec_z(mom_24h)", "xsec_rank(ret_24h)", "sub(king,s2)",
                     "xsec_z(ts_delta(funding_ema,8))", "neg(xsec_rank(rvol_72h))"]
    C = P.load_context(4, subsample=4)                     # ~2185 anchors = full-window scale
    print(f"[equiv] {len(survivors)} survivors, {len(C['rows'])} anchors (full-window-scale subsample)", flush=True)
    facs = [dsl.evaluate(dsl.parse(f), C["ctx"]) for f in survivors]
    t0 = time.time(); fast = P._maxnull_fast(facs, C, np.random.default_rng(7), 200); tf = time.time() - t0
    t0 = time.time(); slow = slow_maxnull(facs, C, np.random.default_rng(7), 200); ts = time.time() - t0
    qs = [50, 90, 95, 99]
    fq = {q: round(float(np.nanpercentile(fast, q)), 5) for q in qs}
    sq = {q: round(float(np.nanpercentile(slow, q)), 5) for q in qs}
    max_abs = max(abs(fq[q] - sq[q]) for q in qs)
    rc = qs[2]  # 95
    rel95 = abs(fq[rc] - sq[rc]) / (abs(sq[rc]) + 1e-9)
    rep = dict(anchors=len(C["rows"]), n_survivors=len(facs), n_null=200,
               fast_quantiles=fq, slow_quantiles=sq, max_abs_quantile_diff=round(max_abs, 6),
               rel_diff_at_rc95=round(rel95, 4), fast_sec=round(tf, 2), slow_sec=round(ts, 2),
               speedup=round(ts / max(tf, 1e-6), 1),
               PASS=bool(rel95 < 0.15 and max_abs < 0.003),
               note="full-window-scale equivalence of vectorized vs per-anchor max-null; verdict uses fast.")
    json.dump(rep, open(MA + "/exports/eda/factory_null_equivalence.json", "w"), indent=1)
    print(f"[equiv] fast q {fq}  ({tf:.1f}s)\n[equiv] slow q {sq}  ({ts:.1f}s)", flush=True)
    print(f"[equiv] max|Δq|={max_abs:.6f} rel@95={rel95:.4f} speedup={rep['speedup']}x -> {'PASS' if rep['PASS'] else 'REVIEW'}", flush=True)


if __name__ == "__main__":
    main()
