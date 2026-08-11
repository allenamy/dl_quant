"""Equivalence oracle for the 28-core stage0 parallelization: with the SAME per-formula rng, n_jobs=1
and n_jobs=24 must produce byte-identical survivors + per-formula ledger rows (p/fdr_q/survived/cause).
This is the lead's 'BH after collecting all p-values = numerically unchanged' claim, made testable."""
import sys
import numpy as np

FAC = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/factory"
sys.path.insert(0, FAC)
import pipeline as P

FORMULAS = [
    "neg(mul(xsec_z(lturnover_24h), xsec_z(max_ret_24h)))",       # non-monotone (id101)
    "neg(xsec_z(ts_max(abs(ret_1h), 24)))",                       # temporal + xsec
    "where(gt(xsec_z(rvol_24h), xsec_z(rvol_72h)), s2, king)",    # leg router
    "xsec_z(ts_delta(funding_ema, 8))",
    "xsec_z(ts_zscore(funding_ema, 72))",
    "mul(xsec_z(mom_168h), neg(xsec_z(rvol_72h)))",
    "neg(xsec_z(power(ret_24h, 3)))",
    "xsec_rank(ts_rank(funding_ema, 72))",
    "decay_linear(rvol_24h, 24)",
    "add(xsec_z(mom_24h), xsec_z(mom_72h))",
    "sub(xsec_rank(dvol_24h), xsec_rank(dvol_72h))",
    "neg(xsec_z(ts_max(rvol_6h, 42)))",
]


class FakeLedger:
    def __init__(self):
        self.rows = []

    def append_stage0(self, f, md5, depth, nops, inc_ic, fdr_q, survived, death_cause):
        self.rows.append((f, None if inc_ic is None else round(inc_ic, 10), fdr_q, bool(survived), death_cause))

    def append_stage1(self, *a, **k):
        pass

    def M(self):
        return len(self.rows)


def survset(survs):
    return sorted(s[0] for s in survs)


def main():
    import random
    C = P.load_context(4, subsample=4)

    # (a) n_jobs 1 vs 24 byte-identical (parallel determinism)
    lg1 = FakeLedger(); s1 = P.stage0(FORMULAS, C, lg1, n_jobs=1)
    lg24 = FakeLedger(); s24 = P.stage0(FORMULAS, C, lg24, n_jobs=24)
    assert survset(s1) == survset(s24), f"survivor set mismatch:\n 1={survset(s1)}\n24={survset(s24)}"
    assert sorted(lg1.rows) == sorted(lg24.rows), "ledger rows differ between n_jobs=1 and n_jobs=24"
    print(f"PASS (a) n_jobs=1 == n_jobs=24 byte-identical | {len(s1)} survivors, {len(lg1.rows)} scored")

    # (c) batch-reorder byte-identical -> proves the per-formula rng is keyed on CONTENT (ast_md5),
    #     not batch position; a position key would change every formula's CI/z under reorder.
    shuffled = FORMULAS[:]; random.Random(20260720).shuffle(shuffled)
    assert shuffled != FORMULAS, "shuffle was a no-op"
    lgS = FakeLedger(); sS = P.stage0(shuffled, C, lgS, n_jobs=1)
    assert survset(s1) == survset(sS), "reorder changed survivors -> rng key is POSITION not content!"
    assert sorted(lg1.rows) == sorted(lgS.rows), "reorder changed ledger rows -> rng key is POSITION not content!"
    print(f"PASS (c) batch-reorder byte-identical | rng keyed on ast_md5, not position")


if __name__ == "__main__":
    main()
