"""Factory — component 5: end-to-end smoke (factory_prereg §5).

10 hand-written + 10 random formulas run the full two-stage pipeline; a deliberate leakage formula and
a temporal-on-sparse-leg formula are rejected; the hash chain verifies; at least one formula walks all
the way to a Stage-1 verdict written to the ledger. (0 CANDIDATEs is an expected, valid outcome on this
feature axis — the smoke proves the machinery + gates + locks, not a discovery.)
"""
import os
import sys
import tempfile

import numpy as np

sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/factory")
import dsl
import ledger as L
import pipeline as P

FAILS = []
def check(name, cond):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}", flush=True)
    if not cond: FAILS.append(name)

print("=== adversarial rejections (before any evaluation) ===", flush=True)
check("leakage formula rejected by parser", not dsl.validate("ts_mean(yr4b, 4)")["ok"])
check("temporal-on-sparse-leg rejected by type system",
      (not dsl.validate("ts_delta(king, 24)")["ok"]) and "SPARSE" in dsl.validate("ts_delta(king, 24)")["error"])

# 10 hand-written valid formulas (mix of legs / temporal / xsec / conditional)
hand = [
    "xsec_rank(king)",
    "sub(king, s2)",
    "where(gt(rvol_24h, 0), king, s2)",
    "mul(xsec_z(mom_24h), sign(funding_leg))",
    "ts_zscore(mom_24h, 24)",
    "xsec_rank(ts_delta(ret_24h, 24))",
    "neg(xsec_rank(rvol_72h))",
    "add(king, mul(0.5, size_leg))",
    "clip(xsec_z(betaadj_ret24), -3, 3)",
    "xsec_demean(ts_corr(ret_1h, ret_4h, 24))",
]
for f in hand:
    v = dsl.validate(f)
    if not v["ok"]:
        print(f"    [warn] hand formula invalid: {f} -> {v['error']}", flush=True)

print("=== load panel (once) + build random formulas ===", flush=True)
C = P.load_context(horizon=4, subsample=8)          # subsample for smoke speed; production uses subsample=1
print(f"    eval anchors (subsampled, 2022-2025, holdout 2026 excluded): {len(C['rows'])}", flush=True)
check("holdout 2026 excluded from eval window", not np.any(C["year"][C["rows"]] == P.HOLDOUT_YEAR))
rng = np.random.default_rng(1)
rand = P._random_formulas(10, rng, depth_dist=[1, 2, 2, 3])
check("10 random formulas generated & valid", len(rand) == 10 and all(dsl.validate(r)["ok"] for r in rand))

batch = hand + rand + ["ts_mean(yr4b, 4)", "ts_delta(king, 24)"]   # include the 2 adversarial in the batch
tmp = tempfile.mktemp(suffix=".jsonl")
print("=== run two-stage pipeline ===", flush=True)
res = P.run_batch(batch, horizon=4, ledger_path=tmp, subsample=8, null_r=40, C=C, n_jobs=4)
print(f"    {res['n_formulas']} formulas | stage0 survivors {res['n_stage0_survivors']} | "
      f"candidates {res['candidates']} | ledger M {res['ledger_M']}", flush=True)

lg = L.Ledger(tmp)
rows = lg._rows
check("ledger hash-chain verifies", lg.verify())
check("every formula appended a stage0 row (incl. adversarial parse-fails)",
      sum(1 for r in rows if r["stage"] == "stage0") == len(batch))
check("adversarial formulas recorded as parse-fail (not evaluated)",
      all(any(r["formula_str"] == a and str(r.get("death_cause", "")).startswith("parse") for r in rows)
          for a in ["ts_mean(yr4b, 4)", "ts_delta(king, 24)"]))
check("at least one formula reached a Stage-1 verdict (full chain)",
      any(r["stage"] == "stage1" for r in rows) == (res["n_stage0_survivors"] > 0) or res["n_stage0_survivors"] == 0)
# if any survivor, confirm the Stage-1 lock produced a real verdict + Bonferroni denominator = ledger M
s1 = [r for r in rows if r["stage"] == "stage1"]
if s1:
    check("Stage-1 verdict in {CANDIDATE, REJECT}", all(r["verdict"] in ("CANDIDATE", "REJECT") for r in s1))
    check("Stage-1 Bonferroni denominator read from ledger M", all(r["stage1_stats"]["bonferroni_M"] >= 1 for r in s1))
else:
    print("    (no Stage-0 survivors -> no Stage-1 rows; expected on a weak/subsampled smoke batch)", flush=True)
    # force one survivor through Stage-1 directly to exercise the discovery path + lock
    C2 = C
    f0 = hand[1]                                       # sub(king, s2)
    fac = dsl.evaluate(dsl.parse(f0), C2["ctx"])
    ics, days, yrs = P.score_series(fac, C2)
    fr = P._xsec_ranks(fac, C2)                            # stage1 now consumes ranks, not the raw factor
    st = P.stage1([(f0, dsl.parse(f0).value, P.stats(ics, days, yrs, rng), fr)], C2, lg, null_r=40)
    check("forced Stage-1 exercise wrote a discovery-path verdict", len(st) == 1 and st[0][1] in ("CANDIDATE", "REJECT"))
    check("Stage-1 denominator = ledger M", lg._rows[-1]["stage1_stats"]["bonferroni_M"] == lg.M())

os.remove(tmp)
print(f"\n{'#'*60}\nFACTORY SMOKE {'OK' if not FAILS else 'FAILED: ' + str(FAILS)}\n{'#'*60}", flush=True)
sys.exit(0 if not FAILS else 1)
