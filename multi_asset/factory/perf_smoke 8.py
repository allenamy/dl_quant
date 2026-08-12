"""Full-window performance smoke — the gate the lead requested after batch-1's perf pits (null
non-vectorized; ts_rank/decay .rolling().apply()). A new operator or a new batch must pass this
BEFORE entering a campaign. Two checks, both on the FULL 48168-row timeline x 8741 anchors:

  (1) per-operator micro-bench — each temporal/xsec op on the full (48168,140) panel must be under
      PER_OP_CEILING_S. Catches a single pathologically slow new operator (batch-1's ts_rank was one).
  (2) whole-batch parallel wall-clock — run_batch(n_jobs) over the batch (stage0 + stage1) must be
      under TOTAL_CEILING_S. Catches a batch that is collectively too heavy even parallelized.

Wall-clock reference (batch_001, 100 formulas, 24 cores, 2026-07-20): ~120s (LOAD 4 + STAGE0 61 +
STAGE1 54). Ceilings are set with headroom; tighten as the operator set stabilizes.

Usage: python perf_smoke.py [batch_file] [horizon=4] [n_jobs=24]
"""
import os, sys, time
import numpy as np

FAC = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/factory"
sys.path.insert(0, FAC)
import dsl
import pipeline as P

PER_OP_CEILING_S = 30.0        # any single operator on the full panel
TOTAL_CEILING_S = 300.0        # whole batch, stage0 + stage1, parallel


def bench_ops(C):
    ctx = C["ctx"]; A = ctx["mom_24h"]; B = ctx["rvol_72h"]
    cases = [("ts_rank", lambda: dsl.ts_rank(A, 72)), ("decay_linear", lambda: dsl.decay_linear(A, 72)),
             ("ts_max", lambda: dsl.ts_max(A, 72)), ("ts_std", lambda: dsl.ts_std(A, 72)),
             ("ts_zscore", lambda: dsl.ts_zscore(A, 72)), ("ts_corr", lambda: dsl.ts_corr(A, B, 72)),
             ("ema", lambda: dsl.ema(A, 72)), ("xsec_z", lambda: dsl.xsec_z(A)),
             ("xsec_rank", lambda: dsl.xsec_rank(A)), ("_xsec_ranks(score)", lambda: P._xsec_ranks(A, C))]
    print(f"[perf] (1) per-op micro-bench on full panel {A.shape} (ceiling {PER_OP_CEILING_S}s):", flush=True)
    worst = 0.0
    for name, fn in cases:
        t0 = time.time(); fn(); dt = time.time() - t0
        worst = max(worst, dt)
        print(f"    {name:20s} {dt:6.2f}s {'  <-- OVER CEILING' if dt > PER_OP_CEILING_S else ''}", flush=True)
    return worst <= PER_OP_CEILING_S


def main():
    batch = sys.argv[1] if len(sys.argv) > 1 else FAC + "/proposals/batch_001.txt"
    horizon = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    n_jobs = int(sys.argv[3]) if len(sys.argv) > 3 else 24
    import run_campaign as RC
    formulas = [f for _, _, f in RC.parse_batch(batch)]
    t0 = time.time(); C = P.load_context(horizon=horizon, subsample=1); t_load = time.time() - t0
    print(f"[perf] load_context {t_load:.1f}s | {len(formulas)} formulas | {len(C['rows'])} anchors", flush=True)
    ops_ok = bench_ops(C)

    print(f"[perf] (2) whole-batch parallel wall-clock (n_jobs={n_jobs}, ceiling {TOTAL_CEILING_S}s):", flush=True)
    lg_path = "/tmp/perf_smoke_ledger.jsonl"
    os.path.exists(lg_path) and os.remove(lg_path)
    t0 = time.time()
    res = P.run_batch(formulas, horizon=horizon, ledger_path=lg_path, C=C, n_jobs=n_jobs)
    total = time.time() - t0
    print(f"    total={total:.1f}s (+load {t_load:.1f}s) | {res['n_stage0_survivors']} survivors "
          f"{len(res['candidates'])} candidates", flush=True)
    total_ok = total <= TOTAL_CEILING_S
    gate = ops_ok and total_ok
    print(f"[perf] GATE {'PASS' if gate else 'FAIL'} "
          f"(per-op {'ok' if ops_ok else 'OVER'} & total {total:.0f}<={TOTAL_CEILING_S:.0f} "
          f"{'ok' if total_ok else 'OVER'})", flush=True)
    sys.exit(0 if gate else 1)


if __name__ == "__main__":
    main()
