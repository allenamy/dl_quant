"""Full-window performance smoke — the gate the lead requested after batch-1's two perf pits
(null non-vectorized; ts_rank/decay .rolling().apply()). BEFORE any batch or new operator enters the
campaign, this must pass a wall-clock ceiling measured on the FULL 48168-row timeline x the real anchor
set (NOT the anchor-subset a correctness smoke uses — that understated per-formula cost ~5x).

Reports: (1) per-operator micro-bench on the full (48168,140) panel; (2) end-to-end stage0 timing for a
batch — total wall-clock + per-formula p50/p90/max + the eval-vs-score(bootstrap) split for the slowest.
Gate: per-formula p90 <= P90_CEILING_S and total <= TOTAL_CEILING_S (tune once 28-core parallel lands).

Usage: python perf_smoke.py [batch_file] [horizon=4]
"""
import sys, time
import numpy as np

FAC = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/factory"
sys.path.insert(0, FAC)
import dsl
import pipeline as P
from pipeline import _xsec_ranks, _rowwise_rankcorr, stats

P90_CEILING_S = 12.0            # per-formula stage0 cost ceiling (serial; revisit after parallelization)
TOTAL_CEILING_S = 1200.0        # whole-batch stage0 ceiling (serial)


def bench_ops(ctx):
    A = ctx["mom_24h"]; B = ctx["rvol_72h"]
    cases = [
        ("ts_rank", lambda: dsl.ts_rank(A, 72)),
        ("decay_linear", lambda: dsl.decay_linear(A, 72)),
        ("ts_max", lambda: dsl.ts_max(A, 72)),
        ("ts_std", lambda: dsl.ts_std(A, 72)),
        ("ts_zscore", lambda: dsl.ts_zscore(A, 72)),
        ("ts_corr", lambda: dsl.ts_corr(A, B, 72)),
        ("ema", lambda: dsl.ema(A, 72)),
        ("xsec_z", lambda: dsl.xsec_z(A)),
        ("xsec_rank", lambda: dsl.xsec_rank(A)),
    ]
    print(f"[perf] per-op micro-bench on full panel {A.shape}:", flush=True)
    for name, fn in cases:
        t0 = time.time(); fn(); dt = time.time() - t0
        print(f"    {name:14s} {dt:6.2f}s", flush=True)


def bench_stage0(formulas, C):
    tr = _xsec_ranks(C["target"], C)
    day_w = C["day"][C["rows"]]; year_w = C["year"][C["rows"]]
    rng = np.random.default_rng(0)
    per = []
    print(f"[perf] stage0 end-to-end on {len(C['rows'])} anchors, full timeline:", flush=True)
    t_all = time.time()
    for f in formulas:
        t0 = time.time()
        try:
            root = dsl.parse(f)
            factor = dsl.evaluate(root, C["ctx"])
        except Exception:
            per.append((f, time.time() - t0, np.nan, np.nan)); continue
        t_eval = time.time() - t0
        t1 = time.time()
        ic = _rowwise_rankcorr(_xsec_ranks(factor, C), tr)
        ok = np.isfinite(ic)
        _ = stats(ic[ok], day_w[ok], year_w[ok], rng)          # includes 2000-draw bootstrap
        t_score = time.time() - t1
        per.append((f, t_eval + t_score, t_eval, t_score))
    total = time.time() - t_all
    costs = np.array([p[1] for p in per])
    p50, p90, mx = np.percentile(costs, 50), np.percentile(costs, 90), costs.max()
    print(f"    total={total:.1f}s | per-formula p50={p50:.2f}s p90={p90:.2f}s max={mx:.2f}s", flush=True)
    slow = sorted(per, key=lambda p: -p[1])[:5]
    print("    slowest (formula | total | eval | score+boot):", flush=True)
    for f, tot, te, tsc in slow:
        print(f"      {tot:6.2f}s  eval={te:5.2f}s score={tsc:5.2f}s  {f[:60]}", flush=True)
    gate = (p90 <= P90_CEILING_S) and (total <= TOTAL_CEILING_S)
    print(f"[perf] GATE {'PASS' if gate else 'FAIL'} "
          f"(p90 {p90:.1f}<={P90_CEILING_S} & total {total:.0f}<={TOTAL_CEILING_S:.0f})", flush=True)
    return gate


def main():
    batch = sys.argv[1] if len(sys.argv) > 1 else FAC + "/proposals/batch_001.txt"
    horizon = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    C = P.load_context(horizon=horizon, subsample=1)
    bench_ops(C["ctx"])
    import run_campaign as RC
    items = RC.parse_batch(batch)
    formulas = [f for _, _, f in items]
    ok = bench_stage0(formulas, C)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
